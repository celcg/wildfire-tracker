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


def _new_store():
    store_type = (
        FirestoreTokenBucketStore
        if config.RATE_LIMIT_BACKEND == "firestore"
        else InMemoryTokenBucketStore
    )
    return store_type(
        capacity=config.TOKEN_BUCKET_CAPACITY,
        refill_seconds=config.TOKEN_BUCKET_REFILL_SECONDS,
        state_ttl_seconds=config.TOKEN_BUCKET_STATE_TTL_SECONDS,
    )


class AnonymousRateLimiter:
    """Combine a shared limiter with a wider process-local safety guard."""

    def __init__(self, store=None) -> None:
        self.store = store or _new_store()
        self.local_guard = InMemoryTokenBucketStore(
            capacity=config.LOCAL_GUARD_CAPACITY,
            refill_seconds=config.LOCAL_GUARD_REFILL_SECONDS,
            state_ttl_seconds=config.TOKEN_BUCKET_STATE_TTL_SECONDS,
        )

    def enforce(self, request: Request) -> None:
        enforce_app_check(request)
        client_key = resolve_client_key(request)
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
            return

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
