"""Общие фикстуры pytest.

Фикстура — функция, которая готовит данные для теста. Тест просто указывает ее имя
в параметрах: def test_x(user): ...  — и pytest сам вызовет фикстуру и передаст результат.

Главный принцип: КАЖДЫЙ тест создает себе СВОЕГО пользователя с уникальным email.
Поэтому тесты не мешают друг другу (лимиты, блокировки, балансы) и не зависят
от порядка запуска и от .\\infra\\reset.ps1.
"""
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from helpers.api import API_URL, ApiClient

PASSWORD = "Secret123!"


@dataclass
class User:
    email: str
    password: str
    client: ApiClient                                   # клиент уже с токеном этого пользователя
    accounts: dict[str, int] = field(default_factory=dict)  # {"RUB": 12, "USD": 13}

    @property
    def rub(self) -> int:
        return self.accounts["RUB"]

    @property
    def usd(self) -> int:
        return self.accounts["USD"]


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


def create_user(rub: str = "0", usd: str = "0", prefix: str = "user") -> User:
    """Регистрирует пользователя, логинит, при необходимости пополняет счета."""
    client = ApiClient(API_URL)
    email = unique_email(prefix)
    r = client.register(email, PASSWORD)
    assert r.status_code == 201, f"setup: register failed {r.status_code} {r.text}"
    r = client.login(email, PASSWORD)
    assert r.status_code == 200, f"setup: login failed {r.status_code} {r.text}"
    accounts = {cur: a["id"] for cur, a in client.accounts().items()}
    for cur, amount in (("RUB", rub), ("USD", usd)):
        left = Decimal(amount)
        while left > 0:  # topup принимает не больше 1 000 000 за раз
            chunk = min(left, Decimal("1000000"))
            r = client.topup(accounts[cur], str(chunk))
            assert r.status_code == 201, f"setup: topup failed {r.status_code} {r.text}"
            left -= chunk
    return User(email, PASSWORD, client, accounts)


@pytest.fixture(scope="session", autouse=True)
def stand_is_up():
    """Перед всеми тестами: стенд доступен. Иначе сразу понятная ошибка вместо 100 одинаковых падений."""
    try:
        r = ApiClient().get("/health", timeout=5)
    except Exception as e:  # noqa: BLE001
        pytest.exit(f"PayFlow API недоступен на {API_URL}: {e}. Запусти docker compose up -d", returncode=2)
    if r.status_code != 200:
        pytest.exit(f"/health вернул {r.status_code}: {r.text}", returncode=2)


@pytest.fixture
def anon() -> ApiClient:
    """Клиент без токена."""
    return ApiClient()


@pytest.fixture
def make_user():
    """Фабрика: make_user(rub="5000") — когда в тесте нужны особые балансы или несколько пользователей."""
    return create_user


@pytest.fixture
def user() -> User:
    """Пользователь со стандартными деньгами: 100 000 ₽ и 1 000 $."""
    return create_user(rub="100000", usd="1000")


@pytest.fixture(scope="session")
def recipient() -> User:
    """Получатель переводов. scope="session" — один на весь прогон: он только принимает деньги."""
    return create_user(prefix="recipient")
