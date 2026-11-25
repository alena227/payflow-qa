"""Суточный лимит 300 000 ₽ и достаточность средств. Требования REQ-TRF-05, REQ-TRF-06, тест-кейсы TC-029..032.

Каждый тест — новый пользователь, поэтому «сегодня» у него еще не было переводов.
"""
from decimal import Decimal

import pytest

from helpers.money import expected_fee

pytestmark = pytest.mark.money

LIMIT_EXCEEDED = "daily transfer limit exceeded"


def test_transfer_exactly_daily_limit_allowed(make_user, recipient):
    """TC-029: ровно 300 000 — разрешено, следующая копейка — нет"""
    user = make_user(rub="400000")
    r = user.client.transfer(user.rub, recipient.rub, "300000.00")
    assert r.status_code == 201, r.text
    r = user.client.transfer(user.rub, recipient.rub, "0.01")
    assert r.status_code == 422
    assert r.json()["detail"] == LIMIT_EXCEEDED


def test_daily_limit_sums_several_transfers(make_user, recipient):
    """TC-030: 200 000 + 100 000.01 > лимита -> отказ, балансы не меняются; 200 000 + 100 000 -> ок"""
    user = make_user(rub="400000")
    assert user.client.transfer(user.rub, recipient.rub, "200000").status_code == 201
    balance = user.client.balance("RUB")
    r = user.client.transfer(user.rub, recipient.rub, "100000.01")
    assert r.status_code == 422
    assert r.json()["detail"] == LIMIT_EXCEEDED
    assert user.client.balance("RUB") == balance
    assert user.client.transfer(user.rub, recipient.rub, "100000.00").status_code == 201


def test_daily_limit_counts_usd_transfers(make_user, recipient):
    """TC-031: 3000 $ = 277 425 ₽ уже потрачено -> еще 30 000 ₽ превышают лимит"""
    user = make_user(rub="100000", usd="4000")
    assert user.client.transfer(user.usd, recipient.usd, "3000").status_code == 201
    r = user.client.transfer(user.rub, recipient.rub, "30000")
    assert r.status_code == 422
    assert r.json()["detail"] == LIMIT_EXCEEDED


@pytest.mark.parametrize(
    "balance, amount, expected_status",
    [
        ("0", "1", 422),          # пустой счет
        ("10000", "9995", 422),   # 9995 + 99.95 > 10000
        ("10000", "9900", 201),   # 9900 + 99.00 = 9999 — впритык
    ],
    ids=["empty-account", "short-by-fee", "just-enough"],
)
def test_insufficient_funds_including_fee(make_user, recipient, balance, amount, expected_status):
    """TC-032"""
    user = make_user(rub=balance)
    r = user.client.transfer(user.rub, recipient.rub, amount)
    assert r.status_code == expected_status
    if expected_status == 422:
        assert r.json()["detail"] == "insufficient funds"
        assert user.client.balance("RUB") == Decimal(balance)
    else:
        assert user.client.balance("RUB") == Decimal(balance) - Decimal(amount) - expected_fee(amount, "RUB")
