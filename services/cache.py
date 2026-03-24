"""
Redis-backed cache for GitHub activity.

Uses Redis in production for cross-worker consistency and falls back to an
in-memory TTL cache in local/dev environments.
"""

import json
import logging
import os
import time
from threading import Lock
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RedisCache:
    """Cache implementation backed by Redis with in-memory fallback."""

    def __init__(self, prefix: str = "cache", default_ttl: int = 300):
        self.prefix = prefix
        self.default_ttl = default_ttl
        self._mem_store: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()
        self._redis = None

        redis_url = os.getenv("REDIS_URL", "")
        if redis_url:
            try:
                import redis
                self._redis = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
                self._redis.ping()
                logger.info("cache_backend_initialized", backend="redis")
            except Exception as e:
                logger.warning("cache_backend_fallback", backend="memory", reason=str(e))
                self._redis = None

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        redis_key = self._full_key(key)

        if self._redis is not None:
            try:
                raw = self._redis.get(redis_key)
                return json.loads(raw) if raw else None
            except Exception as e:
                logger.warning("cache_get_redis_failed", key=redis_key, error=str(e))

        with self._lock:
            entry = self._mem_store.get(redis_key)
            if not entry:
                return None
            expires_at, value = entry
            if time.time() > expires_at:
                self._mem_store.pop(redis_key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        redis_key = self._full_key(key)
        ttl_seconds = ttl if ttl is not None else self.default_ttl

        if self._redis is not None:
            try:
                return bool(self._redis.setex(redis_key, ttl_seconds, json.dumps(value)))
            except Exception as e:
                logger.warning("cache_set_redis_failed", key=redis_key, error=str(e))

        with self._lock:
            self._mem_store[redis_key] = (time.time() + ttl_seconds, value)
        return True

    def delete(self, key: str) -> bool:
        redis_key = self._full_key(key)

        if self._redis is not None:
            try:
                return bool(self._redis.delete(redis_key))
            except Exception as e:
                logger.warning("cache_delete_redis_failed", key=redis_key, error=str(e))

        with self._lock:
            return self._mem_store.pop(redis_key, None) is not None

    def clear(self) -> int:
        """Clear all keys under the configured prefix."""
        if self._redis is not None:
            try:
                cursor = 0
                total = 0
                pattern = f"{self.prefix}:*"
                while True:
                    cursor, keys = self._redis.scan(cursor=cursor, match=pattern, count=100)
                    if keys:
                        total += self._redis.delete(*keys)
                    if cursor == 0:
                        break
                return int(total)
            except Exception as e:
                logger.warning("cache_clear_redis_failed", error=str(e))

        with self._lock:
            count = len(self._mem_store)
            self._mem_store.clear()
            return count

    def cleanup_expired(self) -> int:
        """Remove expired entries from fallback memory cache (Redis handles TTL natively)."""
        if self._redis is not None:
            return 0

        now = time.time()
        removed = 0
        with self._lock:
            stale_keys = [k for k, (expires_at, _) in self._mem_store.items() if now > expires_at]
            for key in stale_keys:
                self._mem_store.pop(key, None)
                removed += 1
        return removed


# Global cache instance for GitHub activity
github_cache = RedisCache(prefix="github", default_ttl=300)


def cache_github_activity(username: str, activities: list, ttl: int = 300) -> bool:
    """
    Cache GitHub activity for a user.
    
    Args:
        username: GitHub username
        activities: List of activity data
        ttl: Cache TTL in seconds
        
    Returns:
        True if cached successfully
    """
    key = f"github_activity_{username}"
    return github_cache.set(key, activities, ttl)


def get_cached_github_activity(username: str) -> Optional[list]:
    """
    Get cached GitHub activity for a user.
    
    Args:
        username: GitHub username
        
    Returns:
        Cached activities or None
    """
    key = f"github_activity_{username}"
    return github_cache.get(key)


def invalidate_github_cache(username: str) -> bool:
    """
    Invalidate GitHub activity cache for a user.
    
    Args:
        username: GitHub username
        
    Returns:
        True if invalidated
    """
    key = f"github_activity_{username}"
    return github_cache.delete(key)
