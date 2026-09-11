"""Small process-local sliding-window limiter for public data endpoints."""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

from config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS


class SlidingWindowRateLimiter:
    """Thread-safe limiter with one timestamp queue per observed client."""

    def __init__(self, request_limit: int, window_seconds: int) -> None:
        self._request_limit = request_limit
        self._window_seconds = window_seconds
        self._request_history: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def enforce(self, request: Request) -> None:
        # Use the transport peer instead of trusting a spoofable forwarded header.
        # Behind a managed proxy this intentionally behaves as a shared bucket.
        client_host = request.client.host if request.client else "unknown"
        now = monotonic()

        with self._lock:
            timestamps = self._request_history[client_host]
            self._discard_expired(timestamps, now)

            if len(timestamps) >= self._request_limit:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(self._retry_after(timestamps, now))},
                )

            timestamps.append(now)

    def reset(self) -> None:
        """Clear all counters so tests do not share rate-limit state."""
        with self._lock:
            self._request_history.clear()

    def _discard_expired(self, timestamps: deque[float], now: float) -> None:
        while timestamps and now - timestamps[0] >= self._window_seconds:
            timestamps.popleft()

    def _retry_after(self, timestamps: deque[float], now: float) -> int:
        return max(1, int(self._window_seconds - (now - timestamps[0])) + 1)


rate_limiter = SlidingWindowRateLimiter(
    request_limit=RATE_LIMIT_REQUESTS,
    window_seconds=RATE_LIMIT_WINDOW_SECONDS,
)


def enforce_rate_limit(request: Request) -> None:
    """FastAPI dependency adapter keeps the limiter independent of route code."""
    rate_limiter.enforce(request)
