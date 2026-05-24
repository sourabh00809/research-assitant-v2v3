from __future__ import annotations

import time
from collections import defaultdict, deque

from .config import settings


_LOCAL_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


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
