"""Регистрация, вход, JWT, блокировка входа. Требования REQ-AUTH-01..06, тест-кейсы TC-001..009."""
import base64
import json

import pytest

from conftest import PASSWORD, unique_email
from helpers.api import ApiClient


def jwt_payload(token: str) -> dict:
    """Декодировать среднюю часть JWT (payload). Подпись тут не проверяем — только читаем содержимое."""
    part = token.split(".")[1]
    part += "=" * (-len(part) % 4)  # base64 требует длину, кратную 4
    return json.loads(base64.urlsafe_b64decode(part))


@pytest.mark.smoke
def test_health(anon):
    r = anon.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "ok"}


# ---------------- регистрация ----------------

@pytest.mark.smoke
def test_register_creates_user_with_two_empty_accounts(anon):
    """TC-001"""
    email = unique_email()
    r = anon.register(email, PASSWORD)
    assert r.status_code == 201
    assert r.json()["email"] == email

    anon.login(email, PASSWORD)
    accounts = anon.accounts()
    assert set(accounts) == {"RUB", "USD"}
    assert all(a["balance"] == "0.00" for a in accounts.values())


def test_register_duplicate_email_case_insensitive(anon):
    """TC-002: email хранится в нижнем регистре, поэтому ALICE@ и alice@ — один и тот же"""
    email = unique_email()
    assert anon.register(email, PASSWORD).status_code == 201
    r = anon.register(email.upper(), PASSWORD)
    assert r.status_code == 409
    assert r.json()["detail"] == "email already registered"


@pytest.mark.parametrize(
    "length, expected_status",
    [(7, 422), (8, 201), (64, 201), (65, 422)],
    ids=["7-too-short", "8-min", "64-max", "65-too-long"],
)
def test_register_password_length_boundaries(anon, length, expected_status):
    """TC-003: граничные значения длины пароля 8..64"""
    r = anon.register(unique_email(), "a" * length)
    assert r.status_code == expected_status


@pytest.mark.parametrize("email", ["alice", "alice@", "@example.com", ""])
def test_register_invalid_email(anon, email):
    """TC-004"""
    assert anon.register(email, PASSWORD).status_code == 422


# ---------------- вход и JWT ----------------

@pytest.mark.smoke
def test_login_returns_valid_jwt(make_user):
    """TC-005: токен HS256, есть sub/iat/exp, живет 30 минут"""
    user = make_user()
    r = ApiClient().login(user.email, PASSWORD)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"

    token = body["access_token"]
    header = json.loads(base64.urlsafe_b64decode(token.split(".")[0] + "=="))
    payload = jwt_payload(token)
    assert header["alg"] == "HS256"
    assert {"sub", "iat", "exp"} <= payload.keys()
    assert payload["exp"] - payload["iat"] == 30 * 60


@pytest.mark.parametrize("case", ["wrong-password", "unknown-email"])
def test_login_failure_has_same_message(make_user, case):
    """TC-006: одинаковый ответ — нельзя по ответу понять, существует ли email"""
    user = make_user()
    email, password = (user.email, "wrong-pass") if case == "wrong-password" else (unique_email(), PASSWORD)
    r = ApiClient().login(email, password)
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid credentials"


@pytest.mark.parametrize("token", [None, "abc.def.ghi"], ids=["no-token", "garbage-token"])
def test_protected_endpoint_requires_valid_token(token):
    """TC-007"""
    assert ApiClient(token=token).get("/accounts").status_code == 401


def test_login_locked_after_5_failed_attempts(make_user):
    """TC-008: 5 неудач подряд -> даже верный пароль дает 429"""
    user = make_user()
    client = ApiClient()
    for _ in range(5):
        assert client.login(user.email, "wrong-pass").status_code == 401
    r = client.login(user.email, PASSWORD)
    assert r.status_code == 429


def test_successful_login_resets_failed_counter(make_user):
    """TC-009: 4 неудачи + успех + 4 неудачи -> блокировки нет"""
    user = make_user()
    client = ApiClient()
    for _ in range(4):
        client.login(user.email, "wrong-pass")
    assert client.login(user.email, PASSWORD).status_code == 200
    for _ in range(4):
        client.login(user.email, "wrong-pass")
    assert client.login(user.email, PASSWORD).status_code == 200
