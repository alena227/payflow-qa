"""Помощник для TC-036: отправляет N переводов ОДНОВРЕМЕННО (в потоках) и печатает коды ответов.

Запуск из корня проекта (стенд сброшен):
    python docs/checklists/parallel_transfers.py

Только стандартная библиотека Python. Код 2FA для dave считается из известного тестового секрета.
"""
import base64
import hashlib
import hmac
import json
import struct
import threading
import time
import urllib.error
import urllib.request

API = "http://localhost:8000"
EMAIL, PASSWORD, TOTP_SECRET = "dave@example.com", "Passw0rd!", "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
FROM_ACC, TO_ACC, AMOUNT, N = 9, 3, "3000", 5


def totp(secret: str) -> str:
    """Тот же алгоритм, что в Google Authenticator (RFC 6238)."""
    key = base64.b32decode(secret)
    counter = struct.pack(">Q", int(time.time()) // 30)
    h = hmac.new(key, counter, hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return "%06d" % ((struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000)


def post(path: str, body: dict, token: str | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or "{}")


status, body = post("/auth/login", {"email": EMAIL, "password": PASSWORD, "otp": totp(TOTP_SECRET)})
assert status == 200, f"login failed: {status} {body}"
token = body["access_token"]

results = []
barrier = threading.Barrier(N)  # все потоки стартуют в один момент


def worker():
    barrier.wait()
    results.append(post("/transfers", {"from_account_id": FROM_ACC, "to_account_id": TO_ACC, "amount": AMOUNT}, token))


threads = [threading.Thread(target=worker) for _ in range(N)]
for t in threads:
    t.start()
for t in threads:
    t.join()

for code, b in sorted(results, key=lambda x: x[0]):
    print(code, b.get("detail") or f"fee {b.get('fee')}")
print("успешных:", sum(c == 201 for c, _ in results), "из", N)
