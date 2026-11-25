"""Environment configuration shared by every worker."""
import math
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv(override=False)

@dataclass(frozen=True)
class Settings:
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", ""))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")))
    daily_budget_usd: float = field(default_factory=lambda: float(os.getenv("DAILY_BUDGET_USD", "1")))
    monthly_budget_usd: float = field(default_factory=lambda: float(os.getenv("MONTHLY_BUDGET_USD", "10")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    def __post_init__(self):
        if not 1 <= self.port <= 65535 or self.rate_limit_per_minute < 1:
            raise ValueError("PORT and RATE_LIMIT_PER_MINUTE must be positive and valid")
        if any(not math.isfinite(x) or x < 0 for x in (self.daily_budget_usd, self.monthly_budget_usd)):
            raise ValueError("Budgets must be finite, non-negative numbers")
        if self.environment == "production" and not self.agent_api_key:
            raise ValueError("AGENT_API_KEY is required in production")

settings = Settings()
