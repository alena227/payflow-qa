"""Security-тесты API. Требования REQ-AUTH-04, REQ-SEC-01..04; чек-лист docs/checklists/security.md.

Один тест написан полностью как образец (test_expired_token_rejected). Остальные — ТВОИ задания ниже.
Запуск только этого файла:
    .\\.venv\\Scripts\\python.exe -m pytest tests\\security -v

Перед началом поставь библиотеку для работы с JWT (и допиши ее в tests/requirements.txt):
    .\\.venv\\Scripts\\python.exe -m pip install PyJWT==2.10.1
"""
import datetime as dt

import jwt  # библиотека PyJWT: умеет создавать и подписывать токены
import pytest
import base64, json

from helpers.api import ApiClient
from conftest import PASSWORD, unique_email

pytestmark = pytest.mark.security

# Секрет стенда (в docker-compose: JWT_SECRET). Зная его, мы можем «честно» подписать
# любой токен — так проверяем именно логику проверки токена, а не подпись.
SECRET = "dev-secret-change-me"


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def make_token(payload: dict, key: str | None = SECRET, algorithm: str = "HS256") -> str:
    """Собрать JWT с нужным содержимым."""
    return jwt.encode(payload, key, algorithm=algorithm)


def user_id_of(user) -> int:
    return user.client.get("/auth/me").json()["id"]


# ===================== ОБРАЗЕЦ =====================

def test_expired_token_rejected(user):
    """REQ-AUTH-04: токен с exp в прошлом -> 401, даже если подпись правильная"""
    # Arrange: токен для реального пользователя, правильно подписанный, но истекший 5 минут назад
    token = make_token({
        "sub": str(user_id_of(user)),
        "iat": now() - dt.timedelta(minutes=35),
        "exp": now() - dt.timedelta(minutes=5),
    })
    # Act
    r = ApiClient(token=token).get("/auth/me")
    # Assert
    assert r.status_code == 401

def test_token_signed_with_other_secret_rejected(user):
    token = make_token(
        {"sub": str(user_id_of(user)), "exp": now() + dt.timedelta(minutes=5)},
        key="hacker-secret",
    )
    r = ApiClient(token=token).get("/auth/me")
    assert r.status_code == 401


def test_token_with_alg_none_rejected(user):
    token = make_token(
        {"sub": str(user_id_of(user)), "exp": now() + dt.timedelta(minutes=5)},
        key=None,
        algorithm="none",
    )
    r = ApiClient(token=token).get("/auth/me")
    assert r.status_code == 401


def test_token_without_exp_rejected(user):
    token = make_token({"sub": str(user_id_of(user))})  # нет поля exp
    r = ApiClient(token=token).get("/auth/me")
    assert r.status_code == 401


def test_token_for_nonexistent_user_rejected():
    token = make_token({"sub": "999999999", "exp": now() + dt.timedelta(minutes=5)})
    r = ApiClient(token=token).get("/auth/me")
    assert r.status_code == 401



def test_tampered_payload_rejected(user):
    # берём настоящий токен пользователя
    real_token = user.client.session.headers["Authorization"].split(" ")[1]
    header, payload, signature = real_token.split(".")
    # подменяем payload на {"sub": "1"}, подпись не трогаем
    fake_payload = base64.urlsafe_b64encode(json.dumps({"sub": "1"}).encode()).rstrip(b"=").decode()
    tampered = f"{header}.{fake_payload}.{signature}"
    r = ApiClient(token=tampered).get("/auth/me")
    assert r.status_code == 401


def test_cannot_read_foreign_account(user, recipient):
    r = user.client.get(f"/accounts/{recipient.rub}")
    assert r.status_code == 404
    assert "balance" not in r.text


def test_history_contains_only_own_operations(make_user, recipient):
    sender = make_user(rub="5000")
    tx_id = sender.client.transfer(sender.rub, recipient.rub, "100").json()["id"]
    # в истории recipient эта операция есть, а в истории постороннего — нет
    outsider = make_user()
    ids = [t["id"] for t in outsider.client.get("/transactions").json()]
    assert tx_id not in ids


def test_cors_allows_web_origin(anon):
    r = anon.get("/health", headers={"Origin": "http://localhost:8090"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:8090"



def test_cors_rejects_foreign_origin(anon):
    r = anon.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_cors_preflight_from_foreign_origin_rejected(anon):
    r = anon.request("OPTIONS", "/transfers", headers={
        "Origin": "https://evil.example",
        "Access-Control-Request-Method": "POST",
    })
    assert "access-control-allow-origin" not in r.headers


@pytest.mark.parametrize("payload", ["' OR 1=1--", "admin'--", '"; DROP TABLE users;--'])
def test_sql_injection_in_login_does_not_break_api(anon, payload):
    r = anon.login(payload, payload)
    assert r.status_code in (401, 422)


def test_register_ignores_extra_fields(anon):
    email = unique_email()
    r = anon.post("/auth/register", json={
        "email": email, "password": "Secret123!",
        "balance": "1000000", "is_system": True,  # лишние поля — должны игнорироваться
    })
    assert r.status_code == 201
    anon.login(email, "Secret123!")
    accounts = anon.accounts()
    assert all(a["balance"] == "0.00" for a in accounts.values())



def test_error_does_not_leak_internals(user):
    r = user.client.post("/transfers", data="{bad json",
                         headers={"Content-Type": "application/json"})
    body = r.text
    assert "Traceback" not in body
    assert "psycopg" not in body
    assert "SELECT" not in body

# ===================== ТВОИ ЗАДАНИЯ =====================
# Пиши по образцу выше: Arrange -> Act -> Assert. После каждого теста запускай файл.
# Порядок — от простого к сложному. Не подглядывай в docs/.answers.md :)
#
# JWT
# 1. test_token_signed_with_other_secret_rejected
#    make_token(..., key="hacker-secret") с валидным exp -> /auth/me -> 401
# 2. test_token_with_alg_none_rejected
#    make_token(payload, key=None, algorithm="none") -> 401
# 3. test_token_without_exp_rejected
#    payload только {"sub": ...} -> 401
# 4. test_token_for_nonexistent_user_rejected
#    sub = "999999999" -> 401
# 5. test_tampered_payload_rejected
#    возьми настоящий токен user (user.client.session.headers["Authorization"]),
#    раздели по ".", подмени середину (payload) на base64 от {"sub": "1"} и собери обратно -> 401
#    подсказка: base64.urlsafe_b64encode(json.dumps(...).encode()).rstrip(b"=").decode()
#
# IDOR (чужие данные) — нужны два пользователя: user и recipient (фикстуры уже есть)
# 6. test_cannot_read_foreign_account
#    user.client.get(f"/accounts/{recipient.rub}") -> 404, и в ответе нет баланса
# 7. test_history_contains_only_own_operations
#    recipient что-то получил от кого-то; в /transactions у user не должно быть его операций
#
# CORS (заголовки запроса передаются так: anon.get("/health", headers={"Origin": "..."}))
# 8. test_cors_allows_web_origin
#    Origin: http://localhost:8090 -> r.headers["access-control-allow-origin"] == "http://localhost:8090"
# 9. test_cors_rejects_foreign_origin
#    Origin: https://evil.example -> заголовка access-control-allow-origin нет
#    подсказка: "access-control-allow-origin" not in r.headers
# 10. test_cors_preflight_from_foreign_origin_rejected
#    anon.request("OPTIONS", "/transfers", headers={"Origin": "https://evil.example",
#                                                    "Access-Control-Request-Method": "POST"})
#    -> нет access-control-allow-origin
#
# Входные данные
# 11. test_sql_injection_in_login_does_not_break_api
#    @pytest.mark.parametrize по строкам: "' OR 1=1--", "admin'--", "\"; DROP TABLE users;--"
#    логин с такими email/паролем -> код 401 или 422, но НЕ 500 и НЕ 200
# 12. test_register_ignores_extra_fields (mass assignment)
#    POST /auth/register с лишними полями {"balance": "1000000", "is_system": true}
#    -> 201, а после входа балансы 0.00
# 13. test_error_does_not_leak_internals
#    отправь в /transfers невалидный JSON (data="{bad", headers={"Content-Type": "application/json"})
#    -> в тексте ответа нет "Traceback", "psycopg", "SELECT"
