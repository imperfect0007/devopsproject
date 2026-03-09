from fastapi import FastAPI, Request, Response
from sqlalchemy import create_engine, text
import os
from prometheus_client import Counter, generate_latest, Histogram
import socket
import time
import logging
import json
import sys


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


logging.basicConfig(level=logging.INFO, stream=sys.stdout)
for handler in logging.root.handlers:
    handler.setFormatter(JSONFormatter())

logger = logging.getLogger("app")

app = FastAPI()

REQUEST_COUNT = Counter("app_requests_total", "Total requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("request_latency_seconds", "Request latency", ["method", "path"])


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    path = request.url.path
    method = request.method
    status = response.status_code

    REQUEST_COUNT.labels(method=method, path=path, status=status).inc()
    REQUEST_LATENCY.labels(method=method, path=path).observe(duration)

    if path != "/health" and path != "/metrics":
        logger.info(
            "request completed",
            extra={
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": round(duration * 1000, 2),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

    return response


@app.on_event("startup")
async def startup_event():
    logger.info("Application starting on host %s", socket.gethostname())


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(DATABASE_URL)


@app.get("/")
def home():
    return {"message": "App Running", "host": socket.gethostname()}


@app.get("/health")
def health():
    return {"status": "OK"}


@app.get("/db-check")
def db_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database health check passed")
        return {"db_status": "Connected"}
    except Exception as e:
        logger.error("Database check failed: %s", str(e), exc_info=True)
        return {"db_status": "Failed"}
