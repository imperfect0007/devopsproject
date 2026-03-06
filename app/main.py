from fastapi import FastAPI, Response
from sqlalchemy import create_engine, text
import os
from prometheus_client import Counter, generate_latest, Histogram
import socket
import time

app = FastAPI()

REQUEST_COUNT = Counter("app_requests_total", "Total requests")

@app.middleware("http")
async def counter_requests(request, call_next):
    REQUEST_COUNT.inc()
    response = await call_next(request)
    return response


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")


REQUEST_LATENCY = Histogram("request_latency_seconds", "Request latency")

@app.middleware("http")
async def measure_latency(request, call_next):
    start = time.time()
    response = await call_next(request)
    REQUEST_LATENCY.observe(time.time() - start)
    return response


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(DATABASE_URL)


@app.get("/")
def home():
    return {"message": "App Running 🚀", "host": socket.gethostname()}


@app.get("/health")
def health():
    return {"status": "OK"}


@app.get("/db-check")
def db_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"db_status": "Connected ✅"}
    except Exception as e:
        return {"db_status": "Failed ❌", "error": str(e)}