"""Anonymous, privacy-preserving rate limiting for public data endpoints."""

import logging
from time import time

from fastapi import HTTPException, Request

import config
from client_identity import resolve_client_key
from firebase_security import enforce_app_check
from logging_config import get_logger, log_event
from rate_limit_store import FirestoreTokenBucketStore, InMemoryTokenBucketStore


logger = get_logger("rate_limit")


def _new_store(capacity, refill_seconds):
    store_type = (
        FirestoreTokenBucketStore
        if config.RATE_LIMIT_BACKEND == "firestore"
        else InMemoryTokenBucketStore
    )
    return store_type(
        capacity=capacity,
        refill_seconds=refill_seconds,
        state_ttl_seconds=config.TOKEN_BUCKET_STATE_TTL_SECONDS,
    )


class AnonymousRateLimiter:
    """Combine a shared limiter with a wider process-local safety guard."""

    def __init__(
        self,
        store=None,
        *,
        capacity=None,
        refill_seconds=None,
        local_guard_capacity=None,
        local_guard_refill_seconds=None,
        key_prefix="",
        fail_open=True,
    ) -> None:
        capacity = capacity or config.TOKEN_BUCKET_CAPACITY
        refill_seconds = refill_seconds or config.TOKEN_BUCKET_REFILL_SECONDS
        self.store = store or _new_store(capacity, refill_seconds)
        self.local_guard = InMemoryTokenBucketStore(
            capacity=local_guard_capacity or config.LOCAL_GUARD_CAPACITY,
            refill_seconds=(
                local_guard_refill_seconds or config.LOCAL_GUARD_REFILL_SECONDS
            ),
            state_ttl_seconds=config.TOKEN_BUCKET_STATE_TTL_SECONDS,
        )
        self.key_prefix = key_prefix
        self.fail_open = fail_open

    def enforce(self, request: Request) -> None:
        enforce_app_check(request)
        self.enforce_key(self.key_prefix + resolve_client_key(request))

    def enforce_key(self, client_key: str) -> None:
        """Consume a pre-sanitized key without re-reading request identity."""
        now = time()

        guard_decision = self.local_guard.consume(client_key, now)
        if not guard_decision.allowed:
            self._reject(guard_decision.retry_after, source="local_guard")

        try:
            decision = self.store.consume(client_key, now)
        except Exception as exc:
            # The already-consumed local guard keeps a bounded fallback when
            # Firestore is temporarily unavailable.
            log_event(
                logger,
                logging.ERROR,
                "rate_limit.store_unavailable",
                error_type=type(exc).__name__,
            )
            if self.fail_open:
                return
            raise HTTPException(
                status_code=503,
                detail="Request protection is temporarily unavailable.",
                headers={"Retry-After": "60"},
            ) from None

        if not decision.allowed:
            self._reject(decision.retry_after, source="shared_bucket")

    @staticmethod
    def _reject(retry_after: int, source: str) -> None:
        log_event(
            logger,
            logging.WARNING,
            "rate_limit.rejected",
            source=source,
            retry_after_seconds=retry_after,
        )
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    def reset(self) -> None:
        for store in (self.store, self.local_guard):
            reset = getattr(store, "reset", None)
            if reset:
                reset()


rate_limiter = AnonymousRateLimiter()


def enforce_rate_limit(request: Request) -> None:
    rate_limiter.enforce(request)
