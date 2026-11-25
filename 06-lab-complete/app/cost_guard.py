"""Shared UTC daily/monthly cost accounting for the mock LLM."""
from datetime import datetime, timezone
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006

def budget_keys() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return "day14:cost:day:" + now.strftime("%Y-%m-%d"), "day14:cost:month:" + now.strftime("%Y-%m")

def check_budget() -> None:
    daily, monthly = (float(value or 0) for value in r.mget(budget_keys()))
    if daily >= settings.daily_budget_usd or monthly >= settings.monthly_budget_usd:
        raise HTTPException(status_code=402, detail="LLM budget exceeded")

def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = input_tokens / 1000 * PRICE_INPUT_PER_1K + output_tokens / 1000 * PRICE_OUTPUT_PER_1K
    daily_key, monthly_key = budget_keys()
    with r.pipeline(transaction=True) as pipe:
        pipe.incrbyfloat(daily_key, cost)
        pipe.expire(daily_key, 2 * 86400)
        pipe.incrbyfloat(monthly_key, cost)
        pipe.expire(monthly_key, 32 * 86400)
        pipe.execute()
    return cost
