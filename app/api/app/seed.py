"""Сброс стенда: очищает все таблицы и создает тестовых пользователей с балансами.

Запуск:  docker compose exec api python -m app.seed
Пароль у всех тестовых пользователей: Passw0rd!
Балансы создаются через операции topup, чтобы история сходилась с балансами.
"""
from decimal import Decimal

from .db import init_db, pool
from .security import hash_password

TEST_PASSWORD = "Passw0rd!"
TEST_USERS = {
    "alice@example.com": {"RUB": Decimal("100000.00"), "USD": Decimal("1000.00")},
    "bob@example.com": {"RUB": Decimal("50000.00"), "USD": Decimal("0")},
    "carol@example.com": {"RUB": Decimal("0"), "USD": Decimal("0")},
}


def reset() -> None:
    init_db()
    with pool.connection() as conn:
        conn.execute("TRUNCATE transactions, accounts, users RESTART IDENTITY CASCADE")
    init_db()  # заново создает системного пользователя и счета комиссий

    pwd_hash = hash_password(TEST_PASSWORD)
    with pool.connection() as conn:
        for email, balances in TEST_USERS.items():
            uid = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id", (email, pwd_hash)
            ).fetchone()["id"]
            for currency, amount in balances.items():
                acc_id = conn.execute(
                    "INSERT INTO accounts (user_id, currency, balance) VALUES (%s, %s, %s) RETURNING id",
                    (uid, currency, amount),
                ).fetchone()["id"]
                if amount > 0:
                    conn.execute(
                        """INSERT INTO transactions (type, to_account_id, amount, currency, amount_to, currency_to)
                           VALUES ('topup', %s, %s, %s, %s, %s)""",
                        (acc_id, amount, currency, amount, currency),
                    )
    print("Стенд сброшен. Пользователи:", ", ".join(TEST_USERS), "| пароль:", TEST_PASSWORD)


if __name__ == "__main__":
    reset()
