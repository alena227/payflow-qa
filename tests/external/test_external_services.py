"""Поведение при сбоях внешних сервисов (курсы, антифрод). Требование REQ-TRF-07; тест-кейсы TC-037..040.

Фикстура `stub` добавляет в WireMock правило с высшим приоритетом и сама удаляет его после теста.
В каждом тесте проверяем две вещи: правильный код ответа И что деньги не сдвинулись.
"""
import time
from decimal import Decimal

import pytest

RATES = "/rates/USD/RUB"
ANTIFRAUD = "/antifraud/check"


def balances(user) -> dict[str, Decimal]:
    return {cur: Decimal(a["balance"]) for cur, a in user.client.accounts().items()}


# ---------------- антифрод: штатные сценарии из файлов заглушек ----------------

def test_antifraud_deny(user, recipient):
    """TC-037: сумма 77777.00 ₽ -> антифрод отказывает"""
    before = balances(user)
    r = user.client.transfer(user.rub, recipient.rub, "77777.00")
    assert r.status_code == 403
    assert r.json()["detail"] == "transfer rejected by antifraud"
    assert balances(user) == before


def test_antifraud_timeout(user, recipient):
    """TC-038: антифрод отвечает через 5 c, api ждет не дольше ~2 c"""
    before = balances(user)
    start = time.monotonic()
    r = user.client.transfer(user.rub, recipient.rub, "66666.00")
    elapsed = time.monotonic() - start
    assert r.status_code == 503
    assert r.json()["detail"] == "antifraud service timeout"
    assert elapsed < 4, f"api ждал {elapsed:.1f} c — таймаут не сработал"
    assert balances(user) == before


def test_antifraud_server_error(stub, user, recipient):
    """Антифрод вернул 500 -> 503, перевод не выполнен"""
    stub("POST", ANTIFRAUD, status=500)
    before = balances(user)
    assert user.client.transfer(user.rub, recipient.rub, "100").status_code == 503
    assert balances(user) == before


# ---------------- сервис курсов ----------------

def test_rates_unavailable(stub, user, recipient):
    """TC-039: курсы недоступны -> переводы с конвертацией 503, рублевые работают"""
    stub("GET", RATES, status=500)
    before = balances(user)
    r = user.client.transfer(user.usd, recipient.rub, "10")
    assert r.status_code == 503
    assert r.json()["detail"] == "rates service unavailable"
    assert balances(user) == before
    assert user.client.transfer(user.rub, recipient.rub, "10").status_code == 201


@pytest.mark.parametrize(
    "body",
    [{"rate": "abc"}, {"rate": "0"}, {"rate": "-1"}, {"base": "USD"}, {"rate": None}],
    ids=["not-a-number", "zero", "negative", "missing-field", "null"],
)
def test_rates_invalid_response(stub, user, recipient, body):
    """TC-040: некорректный курс нельзя использовать для расчета денег"""
    stub("GET", RATES, json_body=body)
    before = balances(user)
    assert user.client.transfer(user.usd, recipient.rub, "10").status_code == 503
    assert balances(user) == before


def test_rates_timeout(stub, user, recipient):
    """Курсы отвечают через 5 c -> 503 по таймауту"""
    stub("GET", RATES, json_body={"rate": "92.4750"}, delay_ms=5000)
    before = balances(user)
    r = user.client.transfer(user.usd, recipient.rub, "10")
    assert r.status_code == 503
    assert r.json()["detail"] == "rates service timeout"
    assert balances(user) == before


def test_new_rate_is_applied(stub, user, recipient):
    """Курс берется из сервиса при каждом переводе, а не кешируется навсегда"""
    stub("GET", RATES, json_body={"rate": "100.0000"})
    r = user.client.transfer(user.usd, recipient.rub, "10")
    assert r.status_code == 201
    assert r.json()["amount_to"] == "1000.00"
