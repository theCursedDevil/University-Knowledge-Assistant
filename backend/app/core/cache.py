"""Redis read-through caching and distributed locking module (C-CACHE).

Implements:
1. CacheClient: Read-through caching with configurable TTLs (FR-CACHE-001, FR-CACHE-003)
   for document listings, details, and admin dashboard statistics, with automated post-write invalidation.
2. DistributedLock: Safe token-based distributed locking with atomic acquire (SET NX PX),
   safe expiration, reliable atomic Lua release, and contention handling (FR-CACHE-002).
"""

import json
import time
import uuid
import asyncio
import threading
from typing import Any, Dict, List, Optional
from contextlib import contextmanager, asynccontextmanager

from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.core.errors import LockContentionError

try:
    import redis
except ImportError:
    redis = None  # type: ignore

settings = get_settings()

# Atomic Lua release script: releases the lock ONLY if the current value matches the client's token.
# Prevents a slow client from releasing another client's lock if its own lock expired.
LUA_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# Atomic Lua extend script: extends the lock TTL ONLY if the current value matches the client's token.
LUA_EXTEND_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("pexpire", KEYS[1], ARGV[2])
else
    return 0
end
"""


class RedisManager:
    """Manages Redis connection pooling and health checks."""

    _instance: Optional["RedisManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._client: Optional[Any] = None
        self._release_script: Optional[Any] = None
        self._extend_script: Optional[Any] = None
        self._init_client()

    @classmethod
    def get_instance(cls) -> "RedisManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _init_client(self) -> None:
        """Initializes Redis client with connection pooling."""
        if redis is None:
            logger.warning("[REDIS] 'redis' package not installed; running in fallback mode.")
            self._client = None
            return

        try:
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=2.0,
            )
            # Ping test
            client.ping()
            self._client = client
            self._release_script = client.register_script(LUA_RELEASE_SCRIPT)
            self._extend_script = client.register_script(LUA_EXTEND_SCRIPT)
            logger.info(
                "[REDIS] Successfully connected to Redis at %s:%s (db=%s).",
                settings.REDIS_HOST,
                settings.REDIS_PORT,
                settings.REDIS_DB,
            )
        except Exception as exc:
            logger.warning("[REDIS] Could not connect to Redis at %s:%s (%s); operating in fallback mode.", settings.REDIS_HOST, settings.REDIS_PORT, exc)
            self._client = None

    def get_client(self) -> Optional[Any]:
        """Returns the Redis client or None if unreachable."""
        if self._client is None:
            self._init_client()
        return self._client

    def is_healthy(self) -> bool:
        """Checks if Redis is currently responsive."""
        client = self.get_client()
        if client is None:
            return False
        try:
            return bool(client.ping())
        except Exception:
            return False

    @property
    def release_script(self) -> Optional[Any]:
        return self._release_script

    @property
    def extend_script(self) -> Optional[Any]:
        return self._extend_script


redis_manager = RedisManager.get_instance()


class CacheClient:
    """Read-through caching client for FastAPI read queries (FR-CACHE-001, FR-CACHE-003)."""

    def __init__(self, manager: RedisManager = redis_manager):
        self._manager = manager
        # In-memory fallback dictionary for test isolation or when Redis is offline: key -> (value, expire_timestamp)
        self._fallback_cache: Dict[str, tuple[Any, float]] = {}
        self._fallback_lock = threading.Lock()

    def build_document_list_key(
        self,
        role: str,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> str:
        """Constructs standardized cache key for role-filtered document list."""
        cat_key = category.strip() if category and category.strip() else "all"
        return f"cache:documents:list:{role}:{cat_key}:{skip}:{limit}"

    def build_document_detail_key(self, document_id: str) -> str:
        """Constructs standardized cache key for single document metadata."""
        return f"cache:documents:detail:{document_id}"

    def build_admin_stats_key(self) -> str:
        """Constructs standardized cache key for admin dashboard analytics."""
        return "cache:admin:stats"

    def get(self, key: str) -> Optional[Any]:
        """Retrieves and deserializes cached value if key exists and has not expired."""
        if not settings.CACHE_ENABLED:
            return None

        client = self._manager.get_client()
        if client:
            try:
                raw = client.get(key)
                if raw is not None:
                    return json.loads(raw)
                return None
            except Exception as exc:
                logger.warning("[CACHE] Redis get failed for key '%s': %s", key, exc)

        # Fallback check
        with self._fallback_lock:
            if key in self._fallback_cache:
                val, exp = self._fallback_cache[key]
                if time.time() < exp:
                    return val
                del self._fallback_cache[key]
        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Serializes and stores value under key with expiration TTL in seconds."""
        if not settings.CACHE_ENABLED:
            return False

        effective_ttl = ttl if ttl is not None else settings.CACHE_DEFAULT_TTL_SECONDS
        if effective_ttl <= 0:
            return False

        client = self._manager.get_client()
        serialized = json.dumps(value, default=str)

        if client:
            try:
                client.set(key, serialized, ex=effective_ttl)
                return True
            except Exception as exc:
                logger.warning("[CACHE] Redis set failed for key '%s': %s", key, exc)

        # Fallback store
        with self._fallback_lock:
            self._fallback_cache[key] = (value, time.time() + effective_ttl)
        return True

    def delete(self, key: str) -> bool:
        """Deletes single cache key."""
        client = self._manager.get_client()
        if client:
            try:
                client.delete(key)
            except Exception as exc:
                logger.warning("[CACHE] Redis delete failed for key '%s': %s", key, exc)

        with self._fallback_lock:
            self._fallback_cache.pop(key, None)
        return True

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidates all cache keys matching the prefix."""
        count = 0
        client = self._manager.get_client()
        if client:
            try:
                keys = list(client.scan_iter(match=f"{prefix}*", count=100))
                if keys:
                    count = client.delete(*keys)
            except Exception as exc:
                logger.warning("[CACHE] Redis prefix invalidation failed for '%s*': %s", prefix, exc)

        with self._fallback_lock:
            matching = [k for k in self._fallback_cache if k.startswith(prefix)]
            for k in matching:
                self._fallback_cache.pop(k, None)
            count += len(matching)
        return count

    def invalidate_document_caches(self, document_id: Optional[str] = None) -> None:
        """Proactively purges cached document lists, single document details, and admin stats.

        Called immediately after document upload, metadata update, deletion, or status change.
        """
        # Invalidate all document listing variations across roles/categories
        self.invalidate_prefix("cache:documents:list:")
        # Invalidate specific document detail if provided
        if document_id:
            self.delete(self.build_document_detail_key(document_id))
        # Invalidate admin stats
        self.delete(self.build_admin_stats_key())
        logger.debug("[CACHE] Invalidated document caches (doc_id=%s).", document_id)

    def invalidate_admin_stats(self) -> None:
        """Invalidates the admin dashboard statistics cache."""
        self.delete(self.build_admin_stats_key())

    def clear_all(self) -> None:
        """Flushes all application cache keys (used primarily in test teardown)."""
        self.invalidate_prefix("cache:")


cache_client = CacheClient()


class DistributedLock:
    """Safe token-based Redis distributed lock (C-CACHE, FR-CACHE-002).

    Attributes:
        resource: Logical resource identifier (e.g. 'document:uuid' or 'ingestion:uuid').
        expire_seconds: Safety TTL to prevent deadlocks if the holder crashes.
        timeout_seconds: Maximum time to wait when contending for an existing lock.
        retry_interval: Seconds to wait between polling attempts.
    """

    # In-memory fallback dictionary for lock coordination if Redis is unavailable:
    # resource -> (token, expire_timestamp, threading.Lock)
    _fallback_locks: Dict[str, tuple[str, float, threading.Lock]] = {}
    _fallback_meta_lock = threading.Lock()

    def __init__(
        self,
        resource: str,
        expire_seconds: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
        retry_interval: float = 0.05,
        manager: RedisManager = redis_manager,
    ):
        self.resource = resource
        self.lock_key = f"lock:{resource}"
        self.expire_seconds = (
            expire_seconds if expire_seconds is not None else settings.LOCK_DEFAULT_EXPIRE_SECONDS
        )
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.LOCK_DEFAULT_TIMEOUT_SECONDS
        )
        self.retry_interval = retry_interval
        self._manager = manager
        self.token: Optional[str] = None
        self._is_acquired: bool = False

    def is_locked(self) -> bool:
        """Returns True if the lock key is currently held."""
        client = self._manager.get_client()
        if client:
            try:
                return bool(client.exists(self.lock_key))
            except Exception as exc:
                logger.warning("[LOCK] Redis exists check failed: %s", exc)

        with self._fallback_meta_lock:
            if self.resource in self._fallback_locks:
                _, exp, _ = self._fallback_locks[self.resource]
                if time.time() < exp:
                    return True
                del self._fallback_locks[self.resource]
        return False

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Synchronously attempts to acquire the lock.

        Uses atomic SET NX PX to ensure mutual exclusion and automatic expiration.
        Polls until acquired or until timeout is exceeded.
        """
        effective_timeout = timeout if timeout is not None else self.timeout_seconds
        start_time = time.monotonic()
        client = self._manager.get_client()
        token = str(uuid.uuid4())
        expire_ms = int(self.expire_seconds * 1000)

        while True:
            if client:
                try:
                    # Atomic SET key token NX PX expire_ms
                    acquired = client.set(self.lock_key, token, nx=True, px=expire_ms)
                    if acquired:
                        self.token = token
                        self._is_acquired = True
                        logger.debug("[LOCK] Acquired '%s' with token %s (TTL: %ss)", self.lock_key, token, self.expire_seconds)
                        return True
                except Exception as exc:
                    logger.warning("[LOCK] Redis set NX failed for '%s': %s", self.lock_key, exc)
            else:
                # In-memory fallback locking
                with self._fallback_meta_lock:
                    now = time.time()
                    if self.resource not in self._fallback_locks or now >= self._fallback_locks[self.resource][1]:
                        t_lock = threading.Lock()
                        self._fallback_locks[self.resource] = (token, now + self.expire_seconds, t_lock)
                        self.token = token
                        self._is_acquired = True
                        return True

            elapsed = time.monotonic() - start_time
            if elapsed >= effective_timeout:
                logger.warning(
                    "[LOCK] Contention on resource '%s' (timeout %ss exceeded)",
                    self.resource,
                    effective_timeout,
                )
                raise LockContentionError(resource=self.resource, timeout=effective_timeout)

            # Wait before next retry
            time.sleep(self.retry_interval)

    async def acquire_async(self, timeout: Optional[float] = None) -> bool:
        """Asynchronously attempts to acquire the lock without blocking the event loop."""
        effective_timeout = timeout if timeout is not None else self.timeout_seconds
        start_time = time.monotonic()
        client = self._manager.get_client()
        token = str(uuid.uuid4())
        expire_ms = int(self.expire_seconds * 1000)

        while True:
            if client:
                try:
                    acquired = client.set(self.lock_key, token, nx=True, px=expire_ms)
                    if acquired:
                        self.token = token
                        self._is_acquired = True
                        logger.debug("[LOCK] Acquired async '%s' with token %s", self.lock_key, token)
                        return True
                except Exception as exc:
                    logger.warning("[LOCK] Redis async set NX failed for '%s': %s", self.lock_key, exc)
            else:
                with self._fallback_meta_lock:
                    now = time.time()
                    if self.resource not in self._fallback_locks or now >= self._fallback_locks[self.resource][1]:
                        t_lock = threading.Lock()
                        self._fallback_locks[self.resource] = (token, now + self.expire_seconds, t_lock)
                        self.token = token
                        self._is_acquired = True
                        return True

            elapsed = time.monotonic() - start_time
            if elapsed >= effective_timeout:
                logger.warning(
                    "[LOCK] Contention on resource '%s' (async timeout %ss exceeded)",
                    self.resource,
                    effective_timeout,
                )
                raise LockContentionError(resource=self.resource, timeout=effective_timeout)

            await asyncio.sleep(self.retry_interval)

    def release(self) -> bool:
        """Safely releases the lock using atomic Lua token verification.

        Only deletes the key if the token stored in Redis matches our token.
        """
        if not self._is_acquired or not self.token:
            return False

        client = self._manager.get_client()
        released = False

        if client and self._manager.release_script:
            try:
                res = self._manager.release_script(keys=[self.lock_key], args=[self.token])
                released = bool(res == 1)
                logger.debug("[LOCK] Released '%s' (token: %s, result: %s)", self.lock_key, self.token, released)
            except Exception as exc:
                logger.warning("[LOCK] Redis Lua release failed for '%s': %s", self.lock_key, exc)
        else:
            with self._fallback_meta_lock:
                if self.resource in self._fallback_locks:
                    stored_token, _, _ = self._fallback_locks[self.resource]
                    if stored_token == self.token:
                        del self._fallback_locks[self.resource]
                        released = True

        self._is_acquired = False
        self.token = None
        return released

    async def release_async(self) -> bool:
        """Asynchronously releases the lock."""
        # Redis release via Lua is a single fast round-trip
        return self.release()


@contextmanager
def distributed_lock(
    resource: str,
    expire_seconds: Optional[float] = None,
    timeout_seconds: Optional[float] = None,
):
    """Synchronous context manager for distributed locking.

    Example:
        with distributed_lock(f"document:{doc_id}", expire_seconds=30.0, timeout_seconds=5.0):
            # Critical section
            perform_work()
    """
    lock = DistributedLock(
        resource=resource,
        expire_seconds=expire_seconds,
        timeout_seconds=timeout_seconds,
    )
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()


@asynccontextmanager
async def async_distributed_lock(
    resource: str,
    expire_seconds: Optional[float] = None,
    timeout_seconds: Optional[float] = None,
):
    """Asynchronous context manager for distributed locking.

    Example:
        async with async_distributed_lock(f"document:{doc_id}", expire_seconds=30.0, timeout_seconds=5.0):
            # Critical section
            await perform_async_work()
    """
    lock = DistributedLock(
        resource=resource,
        expire_seconds=expire_seconds,
        timeout_seconds=timeout_seconds,
    )
    await lock.acquire_async()
    try:
        yield lock
    finally:
        await lock.release_async()
