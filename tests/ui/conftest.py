"""Фикстуры для UI-тестов на Playwright.

Playwright управляет настоящим браузером. Ключевые понятия:
- page    — одна вкладка браузера, через неё кликаем и проверяем;
- locator — «указатель» на элемент по селектору; page.get_by_test_id("x") ищет元 element
  с атрибутом data-testid="x" (их я проставила в app/web/public/index.html);
- expect  — умное ожидание: не падает сразу, а ждёт до 5 c, пока условие выполнится
  (UI обновляется не мгновенно).

Пользователей создаём через API (фикстуры из корневого conftest), а в браузере только логинимся:
так тест быстрее и не зависит от формы регистрации.
"""
import os

import pytest

WEB_URL = os.getenv("PAYFLOW_WEB", "http://localhost:8090")


@pytest.fixture
def ui_user(make_user):
    """Пользователь с деньгами для UI-входа: 100 000 ₽ и 1 000 $."""
    return make_user(rub="100000", usd="1000")


def login(page, email: str, password: str, web_url: str = WEB_URL) -> None:
    """Пройти форму входа в вебе."""
    page.goto(web_url)
    page.get_by_test_id("login-email").fill(email)
    page.get_by_test_id("login-password").fill(password)
    page.get_by_test_id("login-submit").click()


@pytest.fixture
def web_url() -> str:
    return WEB_URL
