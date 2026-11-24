"""Финансовая логика. Всё в Decimal, округление до копеек/центов по ROUND_HALF_UP
(обычное «школьное»: 0.005 -> 0.01).

Правила:
- комиссия 1% от суммы перевода, но не меньше 10 RUB и не больше 500 RUB;
  для USD-счета границы пересчитываются в доллары по курсу;
- курс USD/RUB берется из сервиса курсов; RUB->USD = сумма / курс;
- суточный лимит исходящих переводов — 300 000 RUB (в рублевом эквиваленте), сутки по UTC.
"""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
FEE_RATE = Decimal("0.01")
FEE_MIN_RUB = Decimal("10")
FEE_MAX_RUB = Decimal("500")
DAILY_LIMIT_RUB = Decimal("300000")
MAX_AMOUNT = Decimal("1000000")


def q(x: Decimal) -> Decimal:
    """Округлить до 2 знаков."""
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def to_rub(amount: Decimal, currency: str, usd_rub: Decimal | None) -> Decimal:
    return amount if currency == "RUB" else amount * usd_rub


def from_rub(amount_rub: Decimal, currency: str, usd_rub: Decimal | None) -> Decimal:
    return amount_rub if currency == "RUB" else amount_rub / usd_rub


def calc_fee(amount: Decimal, currency: str, usd_rub: Decimal | None) -> Decimal:
    amount_rub = to_rub(amount, currency, usd_rub)
    fee_rub = min(max(amount_rub * FEE_RATE, FEE_MIN_RUB), FEE_MAX_RUB)
    return q(from_rub(fee_rub, currency, usd_rub))


def convert(amount: Decimal, cur_from: str, cur_to: str, usd_rub: Decimal | None) -> Decimal:
    if cur_from == cur_to:
        return amount
    if cur_from == "USD" and cur_to == "RUB":
        return q(amount * usd_rub)
    if cur_from == "RUB" and cur_to == "USD":
        return q(amount / usd_rub)
    raise ValueError(f"unsupported pair {cur_from}->{cur_to}")
