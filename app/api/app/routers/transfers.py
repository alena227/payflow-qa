"""Переводы.

Порядок:
1. проверяем счета (свой источник, существующий получатель);
2. если участвует USD — берем курс из сервиса курсов;
3. считаем комиссию, сумму к зачислению и рублевый эквивалент;
4. спрашиваем антифрод;
5. в ОДНОЙ транзакции БД с блокировками (SELECT ... FOR UPDATE):
   проверяем суточный лимит и баланс, списываем, зачисляем, пишем операцию.
Внешние HTTP-вызовы делаем ДО блокировок, чтобы не держать строки БД во время сетевого ожидания.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from .. import money
from ..db import pool
from ..external import antifraud_allows, get_usd_rub_rate
from ..schemas import TransactionOut, TransferIn
from ..security import current_user
from .accounts import TX_COLUMNS

router = APIRouter(prefix="/transfers", tags=["transfers"])
log = logging.getLogger("api.transfers")


@router.post("", response_model=TransactionOut, status_code=201)
def create_transfer(body: TransferIn, user: dict = Depends(current_user)):
    if body.from_account_id == body.to_account_id:
        raise HTTPException(422, "cannot transfer to the same account")

    with pool.connection() as conn:
        src = conn.execute(
            "SELECT id, user_id, currency FROM accounts WHERE id = %s", (body.from_account_id,)
        ).fetchone()
        dst = conn.execute(
            """SELECT a.id, a.currency, u.is_system FROM accounts a JOIN users u ON u.id = a.user_id
               WHERE a.id = %s""",
            (body.to_account_id,),
        ).fetchone()
    if not src or src["user_id"] != user["id"]:
        raise HTTPException(404, "source account not found")
    if not dst or dst["is_system"]:
        raise HTTPException(404, "destination account not found")

    cur_from, cur_to = src["currency"], dst["currency"]
    rate = get_usd_rub_rate() if "USD" in (cur_from, cur_to) else None

    amount = body.amount
    fee = money.calc_fee(amount, cur_from, rate)
    amount_to = money.convert(amount, cur_from, cur_to, rate)
    amount_rub = money.q(money.to_rub(amount, cur_from, rate))

    if not antifraud_allows(user["id"], amount_rub):
        log.warning("transfer rejected by antifraud", extra={"extra_fields": {"amount_rub": str(amount_rub)}})
        raise HTTPException(403, "transfer rejected by antifraud")

    with pool.connection() as conn:
        # блокируем пользователя: два параллельных перевода не обойдут суточный лимит
        conn.execute("SELECT id FROM users WHERE id = %s FOR UPDATE", (user["id"],))
        spent_today = conn.execute(
            """SELECT COALESCE(SUM(t.amount_rub), 0) AS s
               FROM transactions t JOIN accounts a ON a.id = t.from_account_id
               WHERE a.user_id = %s AND t.type = 'transfer'
                 AND t.created_at >= date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'""",
            (user["id"],),
        ).fetchone()["s"]
        if spent_today + amount_rub > money.DAILY_LIMIT_RUB:
            raise HTTPException(422, "daily transfer limit exceeded")

        fee_acc_id = conn.execute(
            """SELECT a.id FROM accounts a JOIN users u ON u.id = a.user_id
               WHERE u.is_system AND a.currency = %s""",
            (cur_from,),
        ).fetchone()["id"]

        # блокируем все три счета в порядке id — так не будет взаимных блокировок (deadlock)
        locked = {
            r["id"]: r
            for r in conn.execute(
                "SELECT id, balance FROM accounts WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
                ([src["id"], dst["id"], fee_acc_id],),
            ).fetchall()
        }
        if locked[src["id"]]["balance"] < amount + fee:
            raise HTTPException(422, "insufficient funds")

        conn.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (amount + fee, src["id"]))
        conn.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (amount_to, dst["id"]))
        conn.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (fee, fee_acc_id))
        tx = conn.execute(
            f"""INSERT INTO transactions AS t
                  (type, from_account_id, to_account_id, amount, currency, fee, fee_account_id,
                   rate, amount_to, currency_to, amount_rub)
                VALUES ('transfer', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING {TX_COLUMNS}""",
            (src["id"], dst["id"], amount, cur_from, fee, fee_acc_id, rate, amount_to, cur_to, amount_rub),
        ).fetchone()

    log.info(
        "transfer completed",
        extra={"extra_fields": {
            "tx_id": str(tx["id"]), "from": src["id"], "to": dst["id"],
            "amount": str(amount), "currency": cur_from, "fee": str(fee),
        }},
    )
    return tx
