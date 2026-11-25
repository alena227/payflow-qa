"""Управление заглушками WireMock через его admin API (http://localhost:8089/__admin).

add_stub(...) добавляет правило с priority=1 (выше штатного) и возвращает его id.
remove_stub(id) удаляет только это правило — штатные заглушки остаются на месте.
"""
import os

import requests

WIREMOCK = os.getenv("PAYFLOW_WIREMOCK", "http://localhost:8089")


def add_stub(method: str, url_path: str, status: int = 200, json_body=None, delay_ms: int | None = None) -> str:
    response: dict = {"status": status}
    if json_body is not None:
        response["jsonBody"] = json_body
        response["headers"] = {"Content-Type": "application/json"}
    if delay_ms:
        response["fixedDelayMilliseconds"] = delay_ms
    mapping = {"priority": 1, "request": {"method": method, "urlPath": url_path}, "response": response}
    r = requests.post(f"{WIREMOCK}/__admin/mappings", json=mapping, timeout=5)
    r.raise_for_status()
    return r.json()["id"]


def remove_stub(stub_id: str) -> None:
    requests.delete(f"{WIREMOCK}/__admin/mappings/{stub_id}", timeout=5)
