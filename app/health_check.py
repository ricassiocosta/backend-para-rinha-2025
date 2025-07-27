import asyncio
import uuid
import redis
import orjson

from redis import Redis
from datetime import datetime

from app.config import get_settings
from app.client import get_health

settings = get_settings()

_CACHE_KEY = "gateway_status"
_REDIS_KEY = "leader_lock"
_LOCK_TTL = 5000  # 5 seconds
_RENEW_INTERVAL = 3  # 3 seconds

redis = redis.from_url(settings.redis_url, decode_responses=False)

class PaymentGatewayHealthService:
    def __init__(self, redis_client: Redis, lock_key: str, lock_ttl: int):
        self.redis = redis_client
        self.lock_key = lock_key
        self.lock_ttl = lock_ttl
        self.instance_id = str(uuid.uuid4())
        self._is_leader = False

    def try_acquire_lock(self):
        return self.redis.set(
            self.lock_key,
            self.instance_id,
            nx=True,
            px=self.lock_ttl
        )

    def is_still_leader(self):
        val = self.redis.get(self.lock_key)
        return val and val.decode() == self.instance_id

    def renew_lock(self):
        if self.is_still_leader():
            self.redis.pexpire(self.lock_key, self.lock_ttl)

    async def start(self):
        while True:
            if not self._is_leader:
                acquired = self.try_acquire_lock()
                if acquired:
                    self._is_leader = True
                    asyncio.create_task(self.health_check_loop())
            else:
                self.renew_lock()
            await asyncio.sleep(_RENEW_INTERVAL)

    async def health_check_loop(self):
        while self._is_leader:
            default_health, fallback_health = await asyncio.gather(
                get_health(settings.pp_default),
                get_health(settings.pp_fallback)
            )

            checked_at = datetime.now().timestamp()
            if default_health["failing"]:
                cache_obj = {"data": (settings.pp_fallback, "fallback"), "ts": checked_at}
                redis.set(_CACHE_KEY, orjson.dumps(cache_obj))
            
            elif default_health["minResponseTime"] < 120:
                cache_obj = {"data": (settings.pp_default, "default"), "ts": checked_at}
                redis.set(_CACHE_KEY, orjson.dumps(cache_obj))

            elif not fallback_health["failing"] and fallback_health["minResponseTime"] < (default_health["minResponseTime"] * 2):
                cache_obj = {"data": (settings.pp_fallback, "fallback"), "ts": checked_at}
                redis.set(_CACHE_KEY, orjson.dumps(cache_obj))

            else:
                cache_obj = {"data": (settings.pp_default, "default"), "ts": checked_at}
                redis.set(_CACHE_KEY, orjson.dumps(cache_obj))

            await asyncio.sleep(5)
            if not self.is_still_leader():
                self._is_leader = False
                break

async def gateway_health_check_service():
    ps = PaymentGatewayHealthService(redis, _REDIS_KEY, _LOCK_TTL)
    await ps.start()
