"""Тонкая обертка над requests для PayFlow API.

Зачем обертка, если есть requests? Чтобы в тестах писать по-человечески:
    alice.transfer(3, 5, "100")
вместо
    requests.post("http://localhost:8000/transfers", json={...}, headers={"Authorization": ...})

Методы возвращают обычный requests.Response: тест сам проверяет status_code и json().
Обертка НИЧЕГО не проверяет за тест — иначе можно случайно спрятать баг.
"""
import os
from decimal import Decimal

import requests

API_URL = os.getenv("PAYFLOW_API", "http://localhost:8000")


class ApiClient:
    def __init__(self, base_url: str = API_URL, token: str | None = None):
        self.base_url = base_url
        self.session = requests.Session()  # Session переиспользует соединение и общие заголовки
        if token:
            self.set_token(token)

    # ---------- низкий уровень ----------
    def set_token(self, token: str | None) -> None:
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        else:
            self.session.headers.pop("Authorization", None)

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", 15)
        return self.session.request(method, self.base_url + path, **kwargs)

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    # ---------- auth ----------
    def register(self, email: str, password: str) -> requests.Response:
        return self.post("/auth/register", json={"email": email, "password": password})

    def login(self, email: str, password: str, otp: str | None = None) -> requests.Response:
        body = {"email": email, "password": password}
        if otp is not None:
            body["otp"] = otp
        r = self.post("/auth/login", json=body)
        if r.status_code == 200:
            self.set_token(r.json()["access_token"])
        return r

    # ---------- счета и переводы ----------
    def accounts(self) -> dict[str, dict]:
        """{'RUB': {'id': 3, 'currency': 'RUB', 'balance': '100.00'}, 'USD': {...}}"""
        r = self.get("/accounts")
        r.raise_for_status()
        return {a["currency"]: a for a in r.json()}

    def balance(self, currency: str) -> Decimal:
        return Decimal(self.accounts()[currency]["balance"])

    def topup(self, account_id: int, amount: str) -> requests.Response:
        return self.post(f"/accounts/{account_id}/topup", json={"amount": amount})

    def transfer(self, from_id: int, to_id: int, amount) -> requests.Response:
        return self.post("/transfers", json={"from_account_id": from_id, "to_account_id": to_id, "amount": amount})
