"""Подключение к PostgreSQL стенда для SQL-проверок.

Тесты читают базу напрямую: так проверяется то, что API не показывает
(системный счет комиссий, сырые данные операций, типы колонок).
"""
import os

import psycopg
from psycopg.rows import dict_row

DB_URL = os.getenv("PAYFLOW_DB", "postgresql://payflow:payflow@localhost:5432/payflow")


def connect() -> psycopg.Connection:
    # autocommit: каждый SELECT видит свежие данные, которые только что записал api
    return psycopg.connect(DB_URL, autocommit=True, row_factory=dict_row)
