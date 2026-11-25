"""Целостность данных в PostgreSQL. Требования REQ-DATA-01..03, REQ-TRF-03, REQ-TRF-09; тест-кейсы TC-024, TC-049, TC-050.

Схема каждого теста: сделать операции через API -> проверить базу SQL-запросом.
CTE (WITH ... AS (...)) — именованный подзапрос: большой запрос собирается из понятных шагов,
как переменные в коде.
"""
from decimal import Decimal

import pytest

pytestmark = pytest.mark.money

# Баланс счета = все зачисления − все списания (сумма + комиссия) + комиссии, пришедшие на счет.
# Возвращает только РАСХОЖДЕНИЯ, поэтому ожидаемый результат — пустой список.
BALANCE_MISMATCH_SQL = """
WITH movements AS (
    SELECT to_account_id AS account_id, amount_to AS delta
    FROM transactions
    UNION ALL
    SELECT from_account_id, -(amount + fee)
    FROM transactions WHERE from_account_id IS NOT NULL
    UNION ALL
    SELECT fee_account_id, fee
    FROM transactions WHERE fee_account_id IS NOT NULL
),
calculated AS (
    SELECT account_id, SUM(delta) AS calc_balance
    FROM movements
    GROUP BY account_id
)
SELECT a.id, a.currency, a.balance, COALESCE(c.calc_balance, 0) AS calc_balance
FROM accounts a
LEFT JOIN calculated c ON c.account_id = a.id
WHERE a.id = ANY(%(ids)s)
  AND a.balance <> COALESCE(c.calc_balance, 0)
"""

# Комиссия по требованию, посчитанная прямо в SQL. ROUND в PostgreSQL для numeric
# округляет половину «от нуля», для положительных сумм это ROUND_HALF_UP.
WRONG_FEE_SQL = """
WITH transfers AS (
    SELECT id, amount, currency, fee,
           CASE WHEN currency = 'RUB' THEN amount ELSE amount * rate END AS amount_rub,
           COALESCE(rate, 1) AS rate
    FROM transactions
    WHERE type = 'transfer' AND from_account_id = ANY(%(ids)s)
),
expected AS (
    SELECT id, fee,
           ROUND(
               LEAST(GREATEST(amount_rub * 0.01, 10), 500)
               / CASE WHEN currency = 'RUB' THEN 1 ELSE rate END,
               2) AS expected_fee
    FROM transfers
)
SELECT id, fee, expected_fee FROM expected WHERE fee <> expected_fee
"""


@pytest.fixture
def active_user(make_user, recipient):
    """Пользователь, который сделал разные переводы: RUB->RUB, USD->RUB, RUB->USD, себе."""
    user = make_user(rub="100000", usd="1000")
    for from_id, to_id, amount in [
        (user.rub, recipient.rub, "1250.50"),
        (user.usd, recipient.rub, "10.01"),
        (user.rub, recipient.usd, "1000"),
        (user.usd, user.rub, "0.07"),
        (user.rub, recipient.rub, "60000"),
    ]:
        r = user.client.transfer(from_id, to_id, amount)
        assert r.status_code == 201, f"setup: transfer failed {r.text}"
    return user


def test_balances_match_transaction_history(db, active_user, recipient):
    """TC-049: баланс каждого счета сходится с историей операций"""
    ids = [active_user.rub, active_user.usd, recipient.rub, recipient.usd]
    mismatches = db.execute(BALANCE_MISMATCH_SQL, {"ids": ids}).fetchall()
    assert mismatches == []


def test_fees_calculated_correctly(db, active_user):
    """REQ-TRF-03: комиссия каждой операции совпадает с формулой, посчитанной в SQL"""
    wrong = db.execute(WRONG_FEE_SQL, {"ids": [active_user.rub, active_user.usd]}).fetchall()
    assert wrong == []


def test_no_negative_balances(db, active_user):
    """TC-050 / REQ-DATA-02: проверяем всю базу, а не только своих пользователей"""
    negative = db.execute("SELECT id, balance FROM accounts WHERE balance < 0").fetchall()
    assert negative == []


def test_money_columns_are_numeric(db):
    """TC-050 / REQ-DATA-03: деньги в NUMERIC, не в float"""
    rows = db.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_name IN ('accounts', 'transactions')
          AND column_name IN ('balance', 'amount', 'fee', 'amount_to', 'amount_rub')
    """).fetchall()
    assert len(rows) == 5
    assert {r["data_type"] for r in rows} == {"numeric"}


def test_fee_goes_to_system_account(db, make_user, recipient):
    """TC-024 / REQ-TRF-09: комиссия зачисляется на системный счет в валюте списания"""
    system_rub_sql = """
        SELECT a.balance FROM accounts a JOIN users u ON u.id = a.user_id
        WHERE u.is_system AND a.currency = 'RUB'
    """
    user = make_user(rub="10000")
    before = db.execute(system_rub_sql).fetchone()["balance"]
    r = user.client.transfer(user.rub, recipient.rub, "5000")
    after = db.execute(system_rub_sql).fetchone()["balance"]
    assert after - before == Decimal(r.json()["fee"]) == Decimal("50.00")
