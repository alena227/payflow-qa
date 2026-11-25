"""Конвертация RUB<->USD. Требование REQ-TRF-04, тест-кейсы TC-025..028."""
from decimal import Decimal

import pytest

from helpers.money import USD_RUB, expected_amount_to, expected_fee

pytestmark = pytest.mark.money


@pytest.mark.parametrize(
    "amount, cur_from, cur_to",
    [
        ("10.00", "USD", "RUB"),
        ("10.01", "USD", "RUB"),   # 925.67475 -> 925.67
        ("0.07", "USD", "RUB"),    # 6.47325   -> 6.47
        ("1000.00", "RUB", "USD"),  # 10.8137  -> 10.81
        ("50.00", "RUB", "USD"),   # 0.540686  -> 0.54
    ],
)
def test_conversion_amount_to(make_user, recipient, amount, cur_from, cur_to):
    """TC-025, TC-026, TC-027"""
    user = make_user(rub="10000", usd="1000")
    r = user.client.transfer(user.accounts[cur_from], recipient.accounts[cur_to], amount)
    assert r.status_code == 201, r.text
    body = r.json()
    assert Decimal(body["rate"]) == USD_RUB
    assert body["currency_to"] == cur_to
    assert Decimal(body["amount_to"]) == expected_amount_to(amount, cur_from, cur_to)


def test_conversion_balances(make_user):
    """TC-025: деньги на счетах совпадают с тем, что вернул API (а не только ответ)"""
    sender = make_user(usd="1000")
    receiver = make_user()
    r = sender.client.transfer(sender.usd, receiver.rub, "10.01")
    assert r.status_code == 201
    assert sender.client.balance("USD") == Decimal("1000") - Decimal("10.01") - expected_fee("10.01", "USD")
    assert receiver.client.balance("RUB") == Decimal(r.json()["amount_to"])


def test_transfer_between_own_accounts(make_user):
    """TC-028: перевод себе в другой валюте, в истории direction=self"""
    user = make_user(rub="5000")
    r = user.client.transfer(user.rub, user.usd, "1000")
    assert r.status_code == 201
    assert Decimal(r.json()["amount_to"]) == expected_amount_to("1000", "RUB", "USD")
    assert user.client.get("/transactions").json()[0]["direction"] == "self"
