"""notifier: читает события из топика `transactions` и создает уведомления в базе.

Цикл обработки одного сообщения:
1. poll() — забрать сообщение из Kafka;
2. распарсить JSON и проверить по JSON-схеме;
   не получилось -> отправить исходное сообщение в `transactions.dlq` (dead letter queue)
   с заголовком error и закоммитить offset, чтобы не застрять на «битом» сообщении;
3. записать два уведомления (отправителю и получателю);
   повтор того же события не создаст дублей: UNIQUE (event_id, user_id, kind) + ON CONFLICT DO NOTHING;
4. commit offset — только после успешной записи в базу (at-least-once).
   Если база недоступна — откатываемся (seek) на это же сообщение и пробуем снова.
"""
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from confluent_kafka import Consumer, KafkaError, Producer, TopicPartition
from jsonschema import Draft202012Validator

BUGS = os.getenv("BUGS", "0") == "1"
TOPIC = "transactions"
DLQ_TOPIC = "transactions.dlq"
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "redpanda:9092")
DATABASE_URL = os.environ["DATABASE_URL"]

SCHEMA = json.loads((Path(__file__).parent / "transaction_event.schema.json").read_text(encoding="utf-8"))
validator = Draft202012Validator(SCHEMA)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "msg": record.getMessage(),
        }
        data.update(getattr(record, "extra_fields", {}))
        return json.dumps(data, ensure_ascii=False)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
log = logging.getLogger("notifier")

running = True


def stop(*_):
    global running
    running = False


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)


def header(msg, name: str) -> str:
    for k, v in msg.headers() or []:
        if k == name:
            return v.decode(errors="replace") if v else ""
    return "-"


def parse_event(raw: bytes) -> dict:
    event = json.loads(raw)
    errors = sorted(validator.iter_errors(event), key=lambda e: list(e.path))
    if errors:
        e = errors[0]
        path = "/".join(str(p) for p in e.path) or "<root>"
        raise ValueError(f"schema violation at {path}: {e.message}")
    return event


def send_to_dlq(producer: Producer, msg, error: str) -> None:
    headers = list(msg.headers() or []) + [
        ("error", error.encode()),
        ("source_topic", msg.topic().encode()),
        ("source_partition", str(msg.partition()).encode()),
        ("source_offset", str(msg.offset()).encode()),
    ]
    producer.produce(DLQ_TOPIC, key=msg.key(), value=msg.value(), headers=headers)
    producer.flush(5)


def save_notifications(conn, event: dict) -> int:
    amount, cur = event["amount"], event["currency"]
    rows = [
        (event["from_user_id"], "debit",
         f"Перевод {amount} {cur} на счет #{event['to_account_id']} выполнен. Комиссия {event['fee']} {cur}"),
        (event["to_user_id"], "credit",
         f"Поступление {event['amount_to']} {event['currency_to']} со счета #{event['from_account_id']}"),
    ]
    inserted = 0
    with conn.transaction():
        for user_id, kind, text in rows:
            cur_ = conn.execute(
                """INSERT INTO notifications (user_id, event_id, tx_id, kind, message)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (event_id, user_id, kind) DO NOTHING""",
                (user_id, event["event_id"], event["tx_id"], kind, text),
            )
            inserted += cur_.rowcount
    return inserted


def connect_db():
    while running:
        try:
            conn = psycopg.connect(DATABASE_URL, autocommit=True)
            conn.execute("SELECT 1 FROM notifications LIMIT 1")  # таблицу создает api при старте
            return conn
        except psycopg.Error as e:
            log.warning("waiting for database", extra={"extra_fields": {"error": str(e).strip()}})
            time.sleep(2)


def main() -> None:
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": "notifier",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    producer = Producer({"bootstrap.servers": BOOTSTRAP, "acks": "all"})
    conn = connect_db()
    consumer.subscribe([TOPIC])
    log.info("notifier started")

    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() != KafkaError._PARTITION_EOF:
                log.error("kafka error", extra={"extra_fields": {"error": str(msg.error())}})
            continue

        rid = header(msg, "request_id")
        ctx = {"request_id": rid}
        meta = {"partition": msg.partition(), "offset": msg.offset()}

        try:
            event = parse_event(msg.value())
        except json.JSONDecodeError as e:
            if BUGS:
                log.warning("skip message", extra={**ctx, "extra_fields": meta})
            else:
                log.error("invalid message -> DLQ", extra={**ctx, "extra_fields": {**meta, "error": str(e)}})
                send_to_dlq(producer, msg, f"invalid json: {e}")
            consumer.commit(message=msg, asynchronous=False)
            continue
        except (ValueError, TypeError) as e:
            log.error("invalid message -> DLQ", extra={**ctx, "extra_fields": {**meta, "error": str(e)}})
            send_to_dlq(producer, msg, str(e))
            consumer.commit(message=msg, asynchronous=False)
            continue

        try:
            inserted = save_notifications(conn, event)
        except psycopg.Error as e:
            log.error("db error, will retry", extra={**ctx, "extra_fields": {**meta, "error": str(e).strip()}})
            consumer.seek(TopicPartition(msg.topic(), msg.partition(), msg.offset()))
            time.sleep(2)
            if conn.closed:
                conn = connect_db()
            continue

        consumer.commit(message=msg, asynchronous=False)
        log.info("notifications saved", extra={**ctx, "extra_fields": {
            **meta, "tx_id": event["tx_id"], "event_id": event["event_id"], "inserted": inserted,
        }})

    consumer.close()
    log.info("notifier stopped")


if __name__ == "__main__":
    main()
