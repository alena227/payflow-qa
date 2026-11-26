"""Хелперы UI-тестов (имя модуля уникально, чтобы не конфликтовать с conftest.py)."""
import os

PASSWORD = "Secret123!"  # тот же, что в корневом conftest.create_user
WEB_URL = os.getenv("PAYFLOW_WEB", "http://localhost:8090")


def login(page, email: str, password: str, web_url: str = WEB_URL) -> None:
    """Пройти форму входа в вебе."""
    page.goto(web_url)
    page.get_by_test_id("login-email").fill(email)
    page.get_by_test_id("login-password").fill(password)
    page.get_by_test_id("login-submit").click()
