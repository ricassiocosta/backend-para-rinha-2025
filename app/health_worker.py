import requests
from datetime import datetime
from app.config import get_settings
import redis
import json
import time

settings = get_settings()
redis = redis.from_url(settings.redis_url, decode_responses=True)
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
        fallback_health = get_health(settings.pp_fallback)
        if not default_health["failing"] and default_health["minResponseTime"] < 120:
            cache_obj = {"data": (settings.pp_default, "default"), "ts": datetime.now().timestamp()}
            redis.set(_CACHE_KEY, json.dumps(cache_obj), ex=settings.health_cache_ttl)
        elif fallback_health["minResponseTime"] < (default_health["minResponseTime"] * 3):
            cache_obj = {"data": (settings.pp_fallback, "fallback"), "ts": datetime.now().timestamp()}
            redis.set(_CACHE_KEY, json.dumps(cache_obj), ex=settings.health_cache_ttl)
        else:
            cache_obj = {"data": (settings.pp_default, "default"), "ts": datetime.now().timestamp()}
            redis.set(_CACHE_KEY, json.dumps(cache_obj), ex=settings.health_cache_ttl)
        time.sleep(5)

if __name__ == "__main__":
    update_health_status()
