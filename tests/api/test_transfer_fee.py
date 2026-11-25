"""Комиссия за перевод. Требование REQ-TRF-03, тест-кейсы TC-019..024.

Ожидаемую комиссию считает оракул helpers.money.expected_fee — по требованиям, а не по коду приложения.
parametrize запускает один и тот же тест для каждой суммы: в отчете это отдельные тесты,
и сразу видно, на какой именно сумме сломалось.
"""
from decimal import Decimal

import pytest

from helpers.money import expected_fee

pytestmark = pytest.mark.money  # маркер на весь файл: pytest -m money


@pytest.mark.smoke
def test_transfer_rub_happy_path(user, recipient):
    """TC-019: ответ + оба баланса"""
    recipient_before = recipient.client.balance("RUB")
    r = user.client.transfer(user.rub, recipient.rub, "5000")
    assert r.status_code == 201
    body = r.json()
    assert (body["fee"], body["amount_to"], body["rate"]) == ("50.00", "5000.00", None)
    assert user.client.balance("RUB") == Decimal("94950.00")  # 100000 - 5000 - 50
    assert recipient.client.balance("RUB") == recipient_before + Decimal("5000.00")


RUB_AMOUNTS = [
    # граница минимума 10 ₽ (1% = 10 при сумме 1000)
    "0.01", "999.99", "1000.00", "1000.01", "1100.00",
    # округление ROUND_HALF_UP
    "1234.56", "1250.50", "1234.40",
    # граница максимума 500 ₽ (1% = 500 при сумме 50 000)
    "49999.99", "50000.00", "50000.01", "50500.00", "75000.00",
]


@pytest.mark.parametrize("amount", RUB_AMOUNTS)
def test_fee_rub(make_user, recipient, amount):
    """TC-020, TC-021, TC-022"""
    user = make_user(rub="100000")
    r = user.client.transfer(user.rub, recipient.rub, amount)
    assert r.status_code == 201, r.text
    assert Decimal(r.json()["fee"]) == expected_fee(amount, "RUB")


@pytest.mark.parametrize("amount", ["10.00", "100.00", "700.00"])
def test_fee_usd_converted_by_rate(make_user, recipient, amount):
    """TC-023: границы 10/500 ₽ пересчитываются в доллары по курсу"""
    user = make_user(usd="1000")
    r = user.client.transfer(user.usd, recipient.usd, amount)
    assert r.status_code == 201, r.text
    assert Decimal(r.json()["fee"]) == expected_fee(amount, "USD")


def test_fee_is_debited_on_top_of_amount(make_user, recipient):
    """Баланс уменьшается на сумму + комиссию, а не только на сумму"""
    user = make_user(rub="10000")
    r = user.client.transfer(user.rub, recipient.rub, "1234.56")
    fee = Decimal(r.json()["fee"])
    assert user.client.balance("RUB") == Decimal("10000") - Decimal("1234.56") - fee
