"""Production lab agent: authentication, shared guards and JSON logs."""
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import redis
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname, "event": record.getMessage(),
            **getattr(record, "fields", {}),
        }, ensure_ascii=False)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("production_agent")
logger.handlers = [handler]
logger.setLevel(settings.log_level)
logger.propagate = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"fields": {"environment": settings.environment}})
    yield
    # Uvicorn drains in-flight requests before this lifespan shutdown stage.
    r.close()
    logger.info("shutdown_complete")

app = FastAPI(title="Production AI Agent", lifespan=lifespan)

@app.middleware("http")
async def observe_request(request: Request, call_next):
    started = time.perf_counter()
    request_id = uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info("http_request", extra={"fields": {
        "request_id": request_id, "method": request.method,
        "path": request.url.path, "status": response.status_code,
        "ms": round((time.perf_counter() - started) * 1000, 2),
    }})
    return response

@app.exception_handler(redis.RedisError)
async def redis_unavailable(request: Request, exc: redis.RedisError):
    logger.error("redis_unavailable")
    return JSONResponse(status_code=503, content={"detail": "State service unavailable"})

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error("request_failed")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str | None = Field(default=None, max_length=128)

    @field_validator("question")
    @classmethod
    def nonblank_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value

@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}

@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="State service unavailable")
    return {"ready": True}

@app.post("/ask")
def ask(body: AskRequest, key: str = Depends(verify_api_key)):
    check_rate_limit(key)
    check_budget()
    answer = llm_ask(body.question)
    # This mock returns text, so usage is explicitly an estimate.
    cost = record_cost(max(1, len(body.question) // 4), max(1, len(answer) // 4))
    return {"question": body.question, "answer": answer,
            "usage": {"estimated": True, "cost_usd": cost}}
