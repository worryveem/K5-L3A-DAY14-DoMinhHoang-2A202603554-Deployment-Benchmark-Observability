"""Lazy Redis connections: liveness is independent of Redis."""
import redis
from app.config import settings

r = redis.from_url(settings.redis_url, decode_responses=True,
                   socket_connect_timeout=1, socket_timeout=1)

def redis_healthy() -> bool:
    try:
        return bool(r.ping())
    except redis.RedisError:
        return False
