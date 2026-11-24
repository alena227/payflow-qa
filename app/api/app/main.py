import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import init_db, pool
from .events import get_producer
from .external import ExternalServiceError
from .flags import BUGS
from .logging_setup import request_id_var, setup_logging
from .routers import accounts, auth, transfers

setup_logging()
log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    get_producer()
    log.info("api started", extra={"extra_fields": {"bugs": BUGS}})
    yield
    get_producer().flush(5)
    pool.close()


app = FastAPI(title="PayFlow API", version="0.3.0", lifespan=lifespan)

# CORS: браузер разрешит JS со страницы другого origin (web на :8090) читать ответы api (:8000)
# только если api вернет Access-Control-Allow-Origin с этим origin.
if BUGS:
    app.add_middleware(CORSMiddleware, allow_origin_regex=".*", allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Request-ID"])
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:8090").split(",") if o.strip()],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

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
