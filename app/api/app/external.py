"""Клиенты внешних сервисов (в стенде их изображает WireMock).

- курсы: GET  {RATES_URL}/rates/USD/RUB      -> {"rate": "92.4750"}
- антифрод: POST {ANTIFRAUD_URL}/antifraud/check {"user_id":..,"amount_rub":".."}
            -> {"decision": "allow" | "deny"}
Таймаут, 5xx или кривой ответ -> ExternalServiceError -> API отвечает 503.
"""
import os
from decimal import Decimal, InvalidOperation

import httpx

from .logging_setup import request_id_var

RATES_URL = os.getenv("RATES_URL", "http://wiremock:8080")
ANTIFRAUD_URL = os.getenv("ANTIFRAUD_URL", "http://wiremock:8080")
TIMEOUT = float(os.getenv("EXTERNAL_TIMEOUT_SECONDS", "2"))


class ExternalServiceError(Exception):
    def __init__(self, service: str, reason: str):
        super().__init__(f"{service}: {reason}")
        self.service = service
        self.reason = reason


def _headers() -> dict:
    # пробрасываем request_id, чтобы запрос можно было найти и в логах WireMock
    return {"X-Request-ID": request_id_var.get()}


def get_usd_rub_rate() -> Decimal:
    try:
        r = httpx.get(f"{RATES_URL}/rates/USD/RUB", timeout=TIMEOUT, headers=_headers())
        r.raise_for_status()
        rate = Decimal(str(r.json()["rate"]))
    except httpx.TimeoutException:
        raise ExternalServiceError("rates", "timeout")
    except (httpx.HTTPError, KeyError, TypeError, ValueError, InvalidOperation):
        raise ExternalServiceError("rates", "unavailable")
    if not rate.is_finite() or rate <= 0:
        raise ExternalServiceError("rates", "invalid rate")
    return rate


def antifraud_allows(user_id: int, amount_rub: Decimal) -> bool:
    try:
        r = httpx.post(
            f"{ANTIFRAUD_URL}/antifraud/check",
            json={"user_id": user_id, "amount_rub": str(amount_rub)},
            timeout=TIMEOUT,
            headers=_headers(),
        )
        r.raise_for_status()
        decision = r.json()["decision"]
    except httpx.TimeoutException:
        raise ExternalServiceError("antifraud", "timeout")
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        raise ExternalServiceError("antifraud", "unavailable")
    if decision not in ("allow", "deny"):
        raise ExternalServiceError("antifraud", "unavailable")
    return decision == "allow"
