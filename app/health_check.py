import requests
from datetime import datetime
from app.config import get_settings
import redis
import orjson
import time

settings = get_settings()
redis = redis.from_url(settings.redis_url, decode_responses=False)
_CACHE_KEY = "gateway_status"

def get_health(url: str) -> dict:
    try:
        print(f"Checking health of {url} at {datetime.now()}")
        resp = requests.get(f"{url}/payments/service-health", timeout=0.5)
        data = resp.json()
    except Exception:
        data = {"failing": True, "minResponseTime": 10_000}
    return data

def update_health_status():
    while True:
        default_health = get_health(settings.pp_default)
        if not default_health["failing"] and default_health["minResponseTime"] < 120:
            cache_obj = {"data": (settings.pp_default, "default"), "ts": datetime.now().timestamp()}
            redis.set(_CACHE_KEY, orjson.dumps(cache_obj), ex=settings.health_cache_ttl)
            time.sleep(5)
            continue

        if default_health["failing"]:
            cache_obj = {"data": (settings.pp_fallback, "fallback"), "ts": datetime.now().timestamp()}
            redis.set(_CACHE_KEY, orjson.dumps(cache_obj), ex=settings.health_cache_ttl)
            time.sleep(5)
            continue

        fallback_health = get_health(settings.pp_fallback)
        if not fallback_health["failing"] and fallback_health["minResponseTime"] < (default_health["minResponseTime"] * 3):
            cache_obj = {"data": (settings.pp_fallback, "fallback"), "ts": datetime.now().timestamp()}
            redis.set(_CACHE_KEY, orjson.dumps(cache_obj), ex=settings.health_cache_ttl)
            time.sleep(5)
            continue

        cache_obj = {"data": (settings.pp_default, "default"), "ts": datetime.now().timestamp()}
        redis.set(_CACHE_KEY, orjson.dumps(cache_obj), ex=settings.health_cache_ttl)

if __name__ == "__main__":
    print("Health check service started.")
    # Initialize cache with default values
    cache_obj = {"data": (settings.pp_default, "default"), "ts": datetime.now().timestamp()}
    redis.set(_CACHE_KEY, orjson.dumps(cache_obj), ex=settings.health_cache_ttl)

    update_health_status()
