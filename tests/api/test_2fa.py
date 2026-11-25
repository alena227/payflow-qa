"""2FA (TOTP). Требования REQ-2FA-01..04, тест-кейсы TC-010..014.

Фикстура user_2fa включает 2FA у нового пользователя через API (setup -> enable) и
отдает секрет: из него pyotp считает текущий 6-значный код так же, как Google Authenticator.
"""
import pyotp
import pytest

from helpers.api import ApiClient


@pytest.fixture
def user_2fa(make_user):
    user = make_user()
    secret = user.client.post("/auth/2fa/setup").json()["secret"]
    r = user.client.post("/auth/2fa/enable", json={"code": pyotp.TOTP(secret).now()})
    assert r.status_code == 204, f"setup: enable 2fa failed {r.status_code} {r.text}"
    return user, secret


def test_enable_2fa_then_login_requires_otp(user_2fa):
    """TC-010"""
    user, _ = user_2fa
    r = ApiClient().login(user.email, user.password)
    assert r.status_code == 401
    assert r.json()["detail"] == "otp required"


def test_enable_2fa_with_wrong_code_does_not_enable(make_user):
    """TC-011"""
    user = make_user()
    user.client.post("/auth/2fa/setup")
    r = user.client.post("/auth/2fa/enable", json={"code": "000000"})
    assert r.status_code == 400
    assert ApiClient().login(user.email, user.password).status_code == 200  # 2FA так и не включилась


# Таблица решений для поля otp (TC-012). Для каждой строки: что отправляем -> какой ответ ждем.
OTP_CASES = [
    pytest.param("missing", 401, "otp required", id="otp-missing"),
    pytest.param("null", 401, "otp required", id="otp-null"),
    pytest.param("valid", 200, None, id="otp-valid"),
    pytest.param("wrong", 401, "invalid otp", id="otp-wrong"),
    pytest.param("empty", 401, "invalid otp", id="otp-empty-string"),
]


@pytest.mark.security
@pytest.mark.parametrize("otp_kind, status, detail", OTP_CASES)
def test_login_with_2fa_decision_table(user_2fa, otp_kind, status, detail):
    """TC-012"""
    user, secret = user_2fa
    client = ApiClient()
    body = {"email": user.email, "password": user.password}
    if otp_kind == "null":
        body["otp"] = None
    elif otp_kind == "valid":
        body["otp"] = pyotp.TOTP(secret).now()
    elif otp_kind == "wrong":
        body["otp"] = "123456" if pyotp.TOTP(secret).now() != "123456" else "654321"
    elif otp_kind == "empty":
        body["otp"] = ""
    r = client.post("/auth/login", json=body)
    assert r.status_code == status
    if detail:
        assert r.json()["detail"] == detail


@pytest.mark.security
def test_wrong_otp_counts_towards_lockout(user_2fa):
    """TC-013: перебор кодов 2FA упирается в блокировку"""
    user, secret = user_2fa
    client = ApiClient()
    for _ in range(5):
        client.login(user.email, user.password, otp="000000")
    r = client.login(user.email, user.password, otp=pyotp.TOTP(secret).now())
    assert r.status_code == 429


def test_disable_2fa_requires_valid_code(user_2fa):
    """TC-014"""
    user, secret = user_2fa
    assert user.client.post("/auth/2fa/disable", json={"code": "000000"}).status_code == 400
    assert user.client.post("/auth/2fa/disable", json={"code": pyotp.TOTP(secret).now()}).status_code == 204
    assert ApiClient().login(user.email, user.password).status_code == 200
