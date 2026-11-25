"""События Kafka и notifier. Требования REQ-EVT-01..04, REQ-HIST-02, REQ-NFR-01; тест-кейсы TC-043..048.

Нужен доступ к Kafka с ноутбука: localhost:19092 (поднимается вместе со стендом).
"""
import json
import time
from decimal import Decimal
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from helpers.kafka import TopicWatcher, produce, unique_marker

SCHEMA_FILE = Path(__file__).resolve().parents[2] / "app" / "notifier" / "transaction_event.schema.json"
validator = Draft202012Validator(json.loads(SCHEMA_FILE.read_text(encoding="utf-8")))


def wait_for(predicate, timeout: float = 10.0, interval: float = 0.5):
    """Ждать, пока predicate() вернет что-то «истинное». Асинхронные системы (Kafka -> notifier)
    нельзя проверять сразу после действия: нужно подождать с таймаутом, а не делать sleep наугад."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(interval)
    return predicate()


def transfer_and_collect(user, from_id, to_id, amount):
    """Сделать перевод и собрать все события с key = tx_id."""
    watcher = TopicWatcher("transactions")           # встали в конец топика ДО перевода
    r = user.client.transfer(from_id, to_id, amount)
    assert r.status_code == 201, r.text
    tx = r.json()
    events = watcher.collect(lambda m: m.key == tx["id"])
    return r, tx, events


TRANSFER_KINDS = [
    pytest.param("RUB", "RUB", "100", id="RUB-RUB"),
    pytest.param("USD", "RUB", "10.01", id="USD-RUB"),
    pytest.param("RUB", "USD", "1000", id="RUB-USD"),
]


@pytest.mark.parametrize("cur_from, cur_to, amount", TRANSFER_KINDS)
def test_exactly_one_event_per_transfer(user, recipient, cur_from, cur_to, amount):
    """TC-044 / REQ-EVT-01"""
    _, _, events = transfer_and_collect(user, user.accounts[cur_from], recipient.accounts[cur_to], amount)
    assert len(events) == 1, f"ожидали 1 событие, получили {len(events)}"


@pytest.mark.parametrize("cur_from, cur_to, amount", TRANSFER_KINDS)
def test_event_matches_schema(user, recipient, cur_from, cur_to, amount):
    """TC-045 / REQ-EVT-02: контракт события"""
    _, _, events = transfer_and_collect(user, user.accounts[cur_from], recipient.accounts[cur_to], amount)
    assert events, "событие не пришло"
    errors = [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in validator.iter_errors(events[0].json())]
    assert errors == []


def test_event_data_matches_api_and_db(db, user, recipient):
    """TC-045: данные события = ответ API = строка в БД; request_id сквозной"""
    r, tx, events = transfer_and_collect(user, user.usd, recipient.rub, "10.01")
    assert events, "событие не пришло"
    event, headers = events[0].json(), events[0].headers

    row = db.execute("SELECT * FROM transactions WHERE id = %s", (tx["id"],)).fetchone()
    for field in ("amount", "fee", "amount_to"):
        assert Decimal(str(event[field])) == Decimal(tx[field]) == row[field], field
    assert Decimal(event["rate"]) == row["rate"]
    assert (event["from_account_id"], event["to_account_id"]) == (user.usd, recipient.rub)
    assert event["tx_id"] == tx["id"]
    assert headers.get("request_id") == r.headers["X-Request-ID"]


def test_notifications_for_sender_and_receiver(make_user):
    """TC-043 / REQ-HIST-02: notifier создает уведомления обоим участникам"""
    sender, receiver = make_user(rub="5000"), make_user()
    r = sender.client.transfer(sender.rub, receiver.rub, "1000")
    tx_id = r.json()["id"]

    def notification_of(client):
        return [n for n in client.get("/notifications").json() if n["tx_id"] == tx_id]

    sent = wait_for(lambda: notification_of(sender.client))
    received = wait_for(lambda: notification_of(receiver.client))
    assert [n["kind"] for n in sent] == ["debit"]
    assert [n["kind"] for n in received] == ["credit"]
    assert "1000.00 RUB" in sent[0]["message"]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(lambda m: f"not a json {m}".encode(), id="invalid-json"),
        pytest.param(lambda m: json.dumps({"event_id": m}).encode(), id="schema-violation"),
    ],
)
def test_bad_message_goes_to_dlq(payload):
    """TC-046, TC-047 / REQ-EVT-04: битое сообщение -> transactions.dlq с заголовком error"""
    marker = unique_marker()                 # уникальная метка, чтобы найти именно наше сообщение
    value = payload(marker)
    dlq = TopicWatcher("transactions.dlq")
    produce("transactions", value, key=marker.encode())
    found = dlq.collect(lambda m: m.key == marker, timeout=15)
    assert len(found) == 1, "сообщение не попало в DLQ"
    assert found[0].raw_value == value
    assert found[0].headers.get("error")


def test_notifier_keeps_working_after_bad_message(make_user):
    """TC-046: после битого сообщения notifier обрабатывает следующие"""
    produce("transactions", b"garbage " + unique_marker().encode())
    sender, receiver = make_user(rub="5000"), make_user()
    tx_id = sender.client.transfer(sender.rub, receiver.rub, "100").json()["id"]
    got = wait_for(lambda: [n for n in receiver.client.get("/notifications").json() if n["tx_id"] == tx_id])
    assert got, "уведомление не пришло — notifier, возможно, завис"


def test_redelivered_event_does_not_duplicate_notifications(db, user, recipient):
    """TC-048 / REQ-EVT-03: повторная доставка того же события не создает дублей"""
    _, tx, events = transfer_and_collect(user, user.rub, recipient.rub, "100")
    assert events, "событие не пришло"
    event_id = events[0].json()["event_id"]
    count_sql = "SELECT count(*) AS n FROM notifications WHERE event_id = %s"
    wait_for(lambda: db.execute(count_sql, (event_id,)).fetchone()["n"] == 2)

    produce("transactions", events[0].raw_value, key=tx["id"].encode())   # «доставили» еще раз
    time.sleep(3)
    assert db.execute(count_sql, (event_id,)).fetchone()["n"] == 2
