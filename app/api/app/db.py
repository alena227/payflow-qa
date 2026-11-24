"""Пул соединений с PostgreSQL.

`with pool.connection() as conn:` — берет соединение из пула; при выходе из блока
делает COMMIT, а если вылетело исключение — ROLLBACK.
Строки возвращаются словарями (dict_row): row["balance"], NUMERIC приходит как Decimal.
"""
import os
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    os.environ["DATABASE_URL"],
    min_size=1,
    max_size=10,
    kwargs={"row_factory": dict_row},
    open=False,
)


def init_db() -> None:
    if pool.closed:
        pool.open(wait=True, timeout=30)
    sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with pool.connection() as conn:
        conn.execute(sql)
