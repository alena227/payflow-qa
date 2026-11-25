"""Валидация запроса перевода и права на счета. Требования REQ-TRF-01, REQ-TRF-02, тест-кейсы TC-033..035."""
import pytest

INVALID_AMOUNTS = ["0", "-100", "0.001", "1000000.01", "abc", "", None]


@pytest.mark.parametrize("amount", INVALID_AMOUNTS, ids=lambda a: repr(a))
def test_invalid_amount_rejected(user, recipient, amount):
    """TC-033"""
    before = user.client.balance("RUB")
    r = user.client.transfer(user.rub, recipient.rub, amount)
    assert r.status_code == 422
    assert user.client.balance("RUB") == before


def test_minimal_amount_accepted(user, recipient):
    """TC-033: 0.01 — минимальная валидная сумма"""
    assert user.client.transfer(user.rub, recipient.rub, "0.01").status_code == 201


def test_transfer_to_same_account(user):
    """TC-034"""
    r = user.client.transfer(user.rub, user.rub, "10")
    assert r.status_code == 422
    assert r.json()["detail"] == "cannot transfer to the same account"


def test_transfer_to_nonexistent_account(user):
    """TC-034"""
    r = user.client.transfer(user.rub, 999_999_999, "10")
    assert r.status_code == 404
    assert r.json()["detail"] == "destination account not found"


def test_transfer_to_system_fee_account(user):
    """TC-034: счет комиссий (id 1 — создается первым) недоступен для переводов"""
    assert user.client.transfer(user.rub, 1, "10").status_code == 404


@pytest.mark.security
def test_transfer_from_foreign_account(user, recipient):
    """TC-035: нельзя переводить с чужого счета"""
    r = user.client.transfer(recipient.rub, user.rub, "10")
    assert r.status_code == 404
    assert r.json()["detail"] == "source account not found"
