"""Rate limiting engine for compute and LLM intensive endpoints (NFR-SEC-004).

Implements a thread-safe sliding window rate limiter that tracks request timestamps
per client (authenticated user ID, token subject, or IP address).
Returns HTTP 429 Too Many Requests when limits are exceeded, compliant with RFC 6585.
"""

import asyncio
import time
import threading
import uuid
from typing import Dict, List, Optional, Tuple
from fastapi import Request, Depends

from backend.app.core.config import get_settings
from backend.app.core.errors import RateLimitExceededError
from backend.app.core.logging import logger
from backend.app.db.models import User
from backend.app.core.security import get_current_user
from backend.app.core.cache import redis_manager

settings = get_settings()

REDIS_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, 0, now_ms - window_ms)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local retry_ms = window_ms
  if oldest[2] then retry_ms = math.max(1, tonumber(oldest[2]) + window_ms - now_ms) end
  return {0, count, math.ceil(retry_ms / 1000)}
end
redis.call('ZADD', key, now_ms, member)
redis.call('PEXPIRE', key, window_ms)
return {1, count + 1, 0}
"""


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window rate limiter."""

    def __init__(self):
        self._lock = threading.Lock()
        self._requests: Dict[str, List[float]] = {}

    def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int, int]:
        """Checks if a request under `key` is allowed within the sliding window.

        Returns:
            Tuple of (allowed: bool, current_count: int, retry_after: int)
        """
        now = time.time()
        window_start = now - window_seconds

        # Atomic Redis sorted-set window shares limits across pods. Tests and
        # Redis outages use the in-process fallback below.
        if settings.ENVIRONMENT.lower() != "testing":
            client = redis_manager.get_client()
            if client is not None:
                try:
                    result = client.eval(
                        REDIS_SLIDING_WINDOW_SCRIPT,
                        1,
                        f"uka:rate-limit:{key}",
                        int(now * 1000),
                        int(window_seconds * 1000),
                        int(limit),
                        uuid.uuid4().hex,
                    )
                    return bool(int(result[0])), int(result[1]), int(result[2])
                except Exception as exc:
                    logger.warning("Redis rate-limit check failed; using local fallback: %s", exc)

        with self._lock:
            # Retrieve or initialize list of timestamps
            timestamps = self._requests.get(key, [])

            # Filter out timestamps outside the active window
            valid_timestamps = [ts for ts in timestamps if ts > window_start]

            if len(valid_timestamps) >= limit:
                # Calculate remaining seconds until oldest request expires
                oldest_ts = valid_timestamps[0]
                retry_after = max(1, int(oldest_ts + window_seconds - now) + 1)
                self._requests[key] = valid_timestamps
                return False, len(valid_timestamps), retry_after

            # Append current request timestamp and save
            valid_timestamps.append(now)
            self._requests[key] = valid_timestamps
            return True, len(valid_timestamps), 0

    def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window_seconds: int = 60,
        scope: str = "llm",
    ) -> None:
        """Validates rate limit for `key` and raises RateLimitExceededError if breached."""
        if not settings.RATE_LIMIT_ENABLED:
            return

        effective_limit = limit if limit is not None else settings.RATE_LIMIT_LLM_RPM
        scoped_key = f"{scope}:{key}"

        allowed, count, retry_after = self.is_allowed(
            key=scoped_key,
            limit=effective_limit,
            window_seconds=window_seconds,
        )

        if not allowed:
            logger.warning(
                "[RATE_LIMIT] Client '%s' exceeded %s limit (%d reqs in %ds window). Retry after %ds.",
                key,
                scope,
                count,
                window_seconds,
                retry_after,
            )
            raise RateLimitExceededError(
                message=f"Rate limit exceeded. Maximum {effective_limit} requests allowed per minute. Please retry in {retry_after} seconds.",
                details={
                    "scope": scope,
                    "limit_per_minute": effective_limit,
                    "retry_after": retry_after,
                },
                retry_after=retry_after,
            )

    def reset(self) -> None:
        """Clears all stored rate limiting counters (primarily for testing)."""
        with self._lock:
            self._requests.clear()


rate_limiter = SlidingWindowRateLimiter()


async def check_auth_rate_limit(request: Request) -> None:
    """Rate limit unauthenticated OIDC token/login endpoints by peer IP."""
    client_key = request.client.host if request.client else "unknown"
    auth_limit = getattr(settings, "RATE_LIMIT_AUTH_RPM", 10)
    await asyncio.to_thread(
        rate_limiter.check_rate_limit,
        key=client_key,
        limit=auth_limit,
        window_seconds=60,
        scope="auth",
    )


async def check_llm_rate_limit(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> None:
    """FastAPI route dependency that enforces per-user LLM query rate limits."""
    # Key on authenticated user ID; fall back to client IP address
    client_key = str(current_user.id) if current_user else (request.client.host if request.client else "unknown")
    await asyncio.to_thread(
        rate_limiter.check_rate_limit,
        key=client_key,
        limit=settings.RATE_LIMIT_LLM_RPM,
        window_seconds=60,
        scope="llm",
    )
