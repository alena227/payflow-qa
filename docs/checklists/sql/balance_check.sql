-- TC-049: баланс каждого счета должен совпадать с суммой его движений по таблице transactions.
-- Запуск:  Get-Content docs\checklists\sql\balance_check.sql | docker compose exec -T postgres psql -U payflow
-- Пустой результат (0 rows) = расхождений нет.
WITH movements AS (
    -- зачисления получателю (topup и перевод)
    SELECT to_account_id AS account_id, amount_to AS delta FROM transactions
    UNION ALL
    -- списание с отправителя: сумма + комиссия
    SELECT from_account_id, -(amount + fee) FROM transactions WHERE from_account_id IS NOT NULL
    UNION ALL
    -- комиссия на системный счет
    SELECT fee_account_id, fee FROM transactions WHERE fee_account_id IS NOT NULL
),
expected AS (
    SELECT account_id, SUM(delta) AS calc_balance FROM movements GROUP BY account_id
)
SELECT a.id, a.currency, a.balance, COALESCE(e.calc_balance, 0) AS calc_balance,
       a.balance - COALESCE(e.calc_balance, 0) AS diff
FROM accounts a
LEFT JOIN expected e ON e.account_id = a.id
WHERE a.balance <> COALESCE(e.calc_balance, 0)
ORDER BY a.id;
