from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from .config import settings

logger = logging.getLogger(__name__)

_LOCAL_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_FAILED_LOGINS: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(key: str, limit: int = 60, window_seconds: int = 60) -> dict:
    now = time.time()
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(settings.redis_url)
        bucket_key = f"rate:{key}:{int(now // window_seconds)}"
        count = client.incr(bucket_key)
        client.expire(bucket_key, window_seconds + 5)
        return {"allowed": count <= limit, "count": int(count), "limit": limit, "backend": "redis"}
    except Exception:
        bucket = _LOCAL_BUCKETS[key]
        while bucket and bucket[0] < now - window_seconds:
            bucket.popleft()
        bucket.append(now)
        return {"allowed": len(bucket) <= limit, "count": len(bucket), "limit": limit, "backend": "local"}


def record_failed_login(identifier: str) -> dict:
    now = time.time()
    attempts = _FAILED_LOGINS[identifier]
    attempts.append(now)
    attempts[:] = [t for t in attempts if t > now - 900]
    locked = len(attempts) >= 10
    if locked:
        logger.warning("account_locked identifier=%s attempts=%d", identifier[:40], len(attempts))
    return {"attempts": len(attempts), "locked": locked, "remaining_minutes": 15 - int((now - attempts[0]) / 60) if attempts and locked else 0}


def clear_failed_logins(identifier: str) -> None:
    _FAILED_LOGINS.pop(identifier, None)


def is_locked(identifier: str) -> bool:
    attempts = _FAILED_LOGINS.get(identifier, [])
    now = time.time()
    attempts[:] = [t for t in attempts if t > now - 900]
    return len(attempts) >= 10
