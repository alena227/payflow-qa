"""Тестовый оракул: считает, какой ДОЛЖНА быть комиссия и конвертация по требованиям.

Оракул — это независимый источник правильного ответа. Мы не берем формулы из кода
приложения (иначе вместе с кодом скопировали бы и его баги), а пишем их заново
по docs/requirements.md (REQ-TRF-03, REQ-TRF-04).

Курс берем из того же файла, которым заглушка WireMock отвечает приложению,
чтобы тест и приложение гарантированно использовали один курс.
"""
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

_RATE_FILE = Path(__file__).resolve().parents[2] / "infra" / "wiremock" / "mappings" / "rates-usd-rub.json"
USD_RUB = Decimal(json.loads(_RATE_FILE.read_text(encoding="utf-8"))["response"]["jsonBody"]["rate"])

CENT = Decimal("0.01")
FEE_MIN_RUB = Decimal("10")
FEE_MAX_RUB = Decimal("500")
DAILY_LIMIT_RUB = Decimal("300000")


def round_money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def to_rub(amount: Decimal, currency: str) -> Decimal:
    return amount if currency == "RUB" else amount * USD_RUB


def expected_fee(amount: str, currency: str) -> Decimal:
    """1% от суммы в рублях, не меньше 10 и не больше 500 ₽, в валюте счета, HALF_UP до копеек."""
    fee_rub = min(max(to_rub(Decimal(amount), currency) * Decimal("0.01"), FEE_MIN_RUB), FEE_MAX_RUB)
    fee = fee_rub if currency == "RUB" else fee_rub / USD_RUB
    return round_money(fee)


def expected_amount_to(amount: str, cur_from: str, cur_to: str) -> Decimal:
    a = Decimal(amount)
    if cur_from == cur_to:
        return a
    if cur_from == "USD":
        return round_money(a * USD_RUB)
    return round_money(a / USD_RUB)
