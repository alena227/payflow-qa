import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from ..db import pool
from ..schemas import AccountOut, HistoryItemOut, TopupIn, TransactionOut
from ..security import current_user

router = APIRouter(tags=["accounts"])
log = logging.getLogger("api.accounts")

TX_COLUMNS = """t.id, t.type, t.from_account_id, t.to_account_id, t.amount, t.currency, t.fee,
                t.rate, t.amount_to, t.currency_to, t.status, t.created_at"""


def get_own_account(conn, account_id: int, user_id: int) -> dict:
    acc = conn.execute(
        "SELECT id, user_id, currency, balance FROM accounts WHERE id = %s", (account_id,)
    ).fetchone()
    # чужой и несуществующий счет -> одинаково 404, чтобы нельзя было перебором узнать чужие id
    if not acc or acc["user_id"] != user_id:
        raise HTTPException(404, "account not found")
    return acc


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(user: dict = Depends(current_user)):
    with pool.connection() as conn:
        return conn.execute(
            "SELECT id, currency, balance FROM accounts WHERE user_id = %s ORDER BY id", (user["id"],)
        ).fetchall()


@router.get("/accounts/{account_id}", response_model=AccountOut)
def get_account(account_id: int, user: dict = Depends(current_user)):
    with pool.connection() as conn:
        return get_own_account(conn, account_id, user["id"])


@router.post("/accounts/{account_id}/topup", response_model=TransactionOut, status_code=201)
def topup(account_id: int, body: TopupIn, user: dict = Depends(current_user)):
    """Демо-пополнение счета (в реальном банке это был бы платеж с карты)."""
    with pool.connection() as conn:
        acc = get_own_account(conn, account_id, user["id"])
        conn.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (body.amount, acc["id"]))
        tx = conn.execute(
            f"""INSERT INTO transactions AS t (type, to_account_id, amount, currency, amount_to, currency_to)
                VALUES ('topup', %s, %s, %s, %s, %s) RETURNING {TX_COLUMNS}""",
            (acc["id"], body.amount, acc["currency"], body.amount, acc["currency"]),
        ).fetchone()
    log.info("topup", extra={"extra_fields": {"tx_id": str(tx["id"]), "account_id": acc["id"]}})
    return tx


@router.get("/transactions", response_model=list[HistoryItemOut], tags=["transactions"])
def history(
    user: dict = Depends(current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """История операций текущего пользователя, новые сверху."""
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            WITH my AS (SELECT id FROM accounts WHERE user_id = %(uid)s)
            SELECT {TX_COLUMNS},
                   CASE
                     WHEN t.from_account_id IN (SELECT id FROM my)
                      AND t.to_account_id   IN (SELECT id FROM my) THEN 'self'
                     WHEN t.from_account_id IN (SELECT id FROM my) THEN 'out'
                     ELSE 'in'
                   END AS direction
            FROM transactions t
            WHERE t.from_account_id IN (SELECT id FROM my) OR t.to_account_id IN (SELECT id FROM my)
            ORDER BY t.created_at DESC, t.id
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {"uid": user["id"], "limit": limit, "offset": offset},
        ).fetchall()
    return rows
