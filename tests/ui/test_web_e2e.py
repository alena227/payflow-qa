"""UI e2e-сценарии (десктоп). Требования REQ-UI-01, REQ-UI-02; тест-кейсы TC-055..057.

Запуск:
    .\\.venv\\Scripts\\python.exe -m pytest tests\\ui -v
Посмотреть браузер (не headless):
    .\\.venv\\Scripts\\python.exe -m pytest tests\\ui --headed --slowmo 300
"""
import pyotp
import pytest
from playwright.sync_api import expect

from ui.web import PASSWORD, login


def test_login_shows_accounts(page, ui_user):
    """TC-055: вход → видны email, счета, формы"""
    login(page, ui_user.email, PASSWORD)
    expect(page.get_by_test_id("app-view")).to_be_visible()
    expect(page.get_by_test_id("user-email")).to_have_text(ui_user.email)
    # оба счёта отображаются
    expect(page.get_by_test_id("accounts")).to_contain_text("RUB")
    expect(page.get_by_test_id("accounts")).to_contain_text("USD")


def test_login_wrong_password_shows_error(page, make_user):
    """TC-055: неверный пароль → сообщение об ошибке, в кабинет не пускает"""
    user = make_user()
    login(page, user.email, "wrong-password")
    expect(page.get_by_test_id("login-error")).to_be_visible()
    expect(page.get_by_test_id("app-view")).to_be_hidden()


def test_login_with_2fa(page, make_user):
    """TC-056: при включённой 2FA появляется поле кода; неверный код → ошибка, верный → вход"""
    user = make_user()
    secret = user.client.post("/auth/2fa/setup").json()["secret"]
    user.client.post("/auth/2fa/enable", json={"code": pyotp.TOTP(secret).now()})

    login(page, user.email, PASSWORD)
    otp_field = page.get_by_test_id("login-otp")
    expect(otp_field).to_be_visible()  # поле кода появилось

    otp_field.fill("000000")
    page.get_by_test_id("login-submit").click()
    expect(page.get_by_test_id("login-error")).to_be_visible()

    otp_field.fill(pyotp.TOTP(secret).now())
    page.get_by_test_id("login-submit").click()
    expect(page.get_by_test_id("app-view")).to_be_visible()


def test_transfer_updates_balance_and_history(page, ui_user, recipient):
    """TC-057: перевод через UI → сообщение об успехе, баланс и история обновились"""
    login(page, ui_user.email, PASSWORD)

    page.get_by_test_id("transfer-to").fill(str(recipient.rub))
    page.get_by_test_id("transfer-amount").fill("1234,56")  # с запятой, как вводит пользователь
    page.get_by_test_id("transfer-submit").click()

    result = page.get_by_test_id("transfer-result")
    expect(result).to_be_visible()
    expect(result).to_contain_text("1 234.56")  # сумма
    expect(result).to_contain_text("12.35")     # комиссия

    # история пополнилась (ждём появления строки перевода)
    expect(page.get_by_test_id("history")).to_contain_text("1 234.56")


def test_transfer_insufficient_funds_shows_error(page, make_user, recipient):
    """TC-057: перевод больше баланса → ошибка, баланс не меняется"""
    user = make_user(rub="100")
    login(page, user.email, PASSWORD)
    page.get_by_test_id("transfer-to").fill(str(recipient.rub))
    page.get_by_test_id("transfer-amount").fill("999999")
    page.get_by_test_id("transfer-submit").click()
    expect(page.get_by_test_id("transfer-result")).to_be_visible()
    # баланс остался 100.00
    expect(page.get_by_test_id("accounts")).to_contain_text("100.00")
