import logging
import os
import time
import uuid

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .logging_setup import request_id_var, setup_logging

setup_logging()
log = logging.getLogger("api")

DATABASE_URL = os.environ["DATABASE_URL"]

app = FastAPI(title="PayFlow API", version="0.1.0")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    # Берем X-Request-ID от клиента или генерируем свой — по нему потом ищем запрос в логах.
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    token = request_id_var.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled error")
        response = JSONResponse({"detail": "internal error", "request_id": rid}, status_code=500)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Request-ID"] = rid
    log.info(
        "request",
        extra={"extra_fields": {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        }},
    )
    request_id_var.reset(token)
    return response


@app.get("/health", tags=["service"])
def health():
    """Жив ли сервис и доступна ли база."""
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        db = "ok"
    except Exception as e:  # noqa: BLE001
        log.error("db check failed: %s", e)
        db = "down"
    status = "ok" if db == "ok" else "degraded"
    return JSONResponse({"status": status, "db": db}, status_code=200 if db == "ok" else 503)
