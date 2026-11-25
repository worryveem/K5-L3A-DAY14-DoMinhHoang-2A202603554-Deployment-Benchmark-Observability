"""Atomic Redis sliding-window limiter shared by all workers."""
import hashlib
import math
import uuid
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

# Redis time avoids clock skew; Lua makes check-and-record atomic.
WINDOW_SCRIPT = """
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - 60)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return tostring(tonumber(oldest[2]) + 60 - now)
end
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('EXPIRE', KEYS[1], 61)
return '0'
"""

def check_rate_limit(key: str) -> None:
    redis_key = "day14:rate:" + hashlib.sha256(key.encode()).hexdigest()
    retry = float(r.eval(WINDOW_SCRIPT, 1, redis_key,
                         settings.rate_limit_per_minute, uuid.uuid4().hex))
    if retry > 0:
        raise HTTPException(status_code=429, detail="Rate limit exceeded",
                            headers={"Retry-After": str(max(1, math.ceil(retry)))})
