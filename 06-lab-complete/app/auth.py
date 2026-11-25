"""API-key dependency: never log credentials."""
import secrets
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(key: str | None = Security(api_key_header)) -> str:
    if not key or not settings.agent_api_key or not secrets.compare_digest(
        key.encode("utf-8"), settings.agent_api_key.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    return key
