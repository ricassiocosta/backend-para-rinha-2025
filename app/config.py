import os
from functools import lru_cache

class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    database_url: str = os.getenv("DATABASE_URL")
    pp_default: str = os.getenv("PAYMENT_PROCESSOR_URL_DEFAULT")
    pp_fallback: str = os.getenv("PAYMENT_PROCESSOR_URL_FALLBACK")
    health_cache_ttl: int = 5
    worker_batch_size: int = 100
    pp_max_timeout_allowed: int = 300

@lru_cache
def get_settings() -> Settings:
    return Settings()
