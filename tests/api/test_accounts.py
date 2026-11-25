"""Счета и пополнение. Требования REQ-ACC-01..04, тест-кейсы TC-015..018."""
import re
from decimal import Decimal

import pytest

MONEY = re.compile(r"^\d+\.\d{2}$")  # деньги в API — строка с ровно двумя знаками после точки


@pytest.mark.smoke
def test_list_accounts_returns_only_own_accounts(user, recipient):
    """TC-015"""
    accounts = user.client.get("/accounts").json()
    ids = {a["id"] for a in accounts}
    assert ids == {user.rub, user.usd}
    assert recipient.rub not in ids
    assert {a["currency"]: a["balance"] for a in accounts} == {"RUB": "100000.00", "USD": "1000.00"}
    assert all(isinstance(a["balance"], str) and MONEY.match(a["balance"]) for a in accounts)


def test_get_own_account(user):
    """TC-016"""
    r = user.client.get(f"/accounts/{user.rub}")
    assert r.status_code == 200
    assert r.json() == {"id": user.rub, "currency": "RUB", "balance": "100000.00"}


@pytest.mark.parametrize("amount", ["0.01", "1000000"])
def test_topup_valid_amounts(make_user, amount):
    """TC-017: граничные валидные суммы; проверяем не только ответ, но и последствия (баланс, история)"""
    user = make_user()
    r = user.client.topup(user.rub, amount)
    assert r.status_code == 201
    assert r.json()["type"] == "topup"
    assert user.client.balance("RUB") == Decimal(amount)
    history = user.client.get("/transactions").json()
    assert history[0]["id"] == r.json()["id"]


@pytest.mark.parametrize("amount", ["0", "-1", "1000000.01", "1.001"])
def test_topup_invalid_amounts_rejected(user, amount):
    """TC-017: невалидные суммы -> 422, баланс не меняется"""
    before = user.client.balance("RUB")
    assert user.client.topup(user.rub, amount).status_code == 422
    assert user.client.balance("RUB") == before


@pytest.mark.security
def test_topup_foreign_account_forbidden(user, recipient):
    """TC-018"""
    r = user.client.topup(recipient.rub, "100")
    assert r.status_code == 404
