import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .db import init_db, pool
from .external import ExternalServiceError
from .logging_setup import request_id_var, setup_logging
from .routers import accounts, auth, transfers

setup_logging()
log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("api started")
    yield
    pool.close()


app = FastAPI(title="PayFlow API", version="0.2.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transfers.router)


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


@app.exception_handler(ExternalServiceError)
async def external_error_handler(request: Request, exc: ExternalServiceError):
    log.error("external service error", extra={"extra_fields": {"service": exc.service, "reason": exc.reason}})
    return JSONResponse({"detail": f"{exc.service} service {exc.reason}"}, status_code=503)


@app.get("/health", tags=["service"])
def health():
    """Жив ли сервис и доступна ли база."""
    try:
        with pool.connection(timeout=2) as conn:
            conn.execute("SELECT 1")
        db = "ok"
    except Exception as e:  # noqa: BLE001
        log.error("db check failed: %s", e)
        db = "down"
    status = "ok" if db == "ok" else "degraded"
    return JSONResponse({"status": status, "db": db}, status_code=200 if db == "ok" else 503)
