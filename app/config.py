import os

from functools import lru_cache

class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    pp_default: str = os.getenv("PAYMENT_PROCESSOR_URL_DEFAULT")
    pp_fallback: str = os.getenv("PAYMENT_PROCESSOR_URL_FALLBACK")
    health_cache_ttl: int = 5
    PENDING_QUEUE: str = "payments_pending"

@lru_cache
def get_settings() -> Settings:
    return Settings()

@lru_cache
def get_version() -> str:
    return os.getenv("VERSION", "0.1.0")