-- Схема PayFlow. Выполняется при старте api (идемпотентно: IF NOT EXISTS / ON CONFLICT).
-- Деньги: NUMERIC(18,2) — точная десятичная арифметика, никаких float.

CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    totp_secret   TEXT,
    is_system     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS accounts (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id),
    currency   CHAR(3) NOT NULL CHECK (currency IN ('RUB', 'USD')),
    balance    NUMERIC(18, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, currency)
);

-- Одна строка = одна операция.
--   topup:    from_account_id = NULL, деньги появляются на to_account_id
--   transfer: со счета from списывается amount + fee (в валюте from),
--             на to зачисляется amount_to (в валюте currency_to),
--             fee зачисляется на системный счет комиссий fee_account_id
CREATE TABLE IF NOT EXISTS transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type            TEXT NOT NULL CHECK (type IN ('topup', 'transfer')),
    from_account_id BIGINT REFERENCES accounts(id),
    to_account_id   BIGINT NOT NULL REFERENCES accounts(id),
    amount          NUMERIC(18, 2) NOT NULL,
    currency        CHAR(3) NOT NULL,
    fee             NUMERIC(18, 2) NOT NULL DEFAULT 0,
    fee_account_id  BIGINT REFERENCES accounts(id),
    rate            NUMERIC(18, 6),
    amount_to       NUMERIC(18, 2) NOT NULL,
    currency_to     CHAR(3) NOT NULL,
    amount_rub      NUMERIC(18, 2),
    status          TEXT NOT NULL DEFAULT 'completed',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2FA и защита от перебора пароля (ALTER — чтобы обновить уже существующую базу)
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled  BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_logins INT NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until  TIMESTAMPTZ;

-- Уведомления пишет сервис notifier по событиям из Kafka.
-- UNIQUE защищает от дублей, если одно и то же событие прочитано повторно.
CREATE TABLE IF NOT EXISTS notifications (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id),
    event_id   UUID NOT NULL,
    tx_id      UUID NOT NULL,
    kind       TEXT NOT NULL CHECK (kind IN ('debit', 'credit')),
    message    TEXT NOT NULL,
    is_read    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (event_id, user_id, kind)
);
CREATE INDEX IF NOT EXISTS ix_notifications_user ON notifications (user_id, created_at);

CREATE INDEX IF NOT EXISTS ix_tx_from ON transactions (from_account_id, created_at);
CREATE INDEX IF NOT EXISTS ix_tx_to   ON transactions (to_account_id, created_at);

-- Системный пользователь, на чьи счета падают комиссии. Войти под ним нельзя.
INSERT INTO users (email, password_hash, is_system)
VALUES ('system@payflow.local', '!', TRUE)
ON CONFLICT (email) DO NOTHING;

INSERT INTO accounts (user_id, currency)
SELECT u.id, v.c FROM users u, (VALUES ('RUB'), ('USD')) AS v(c)
WHERE u.email = 'system@payflow.local'
ON CONFLICT (user_id, currency) DO NOTHING;
