"""Token-bucket persistence adapters for local and Cloud Run environments."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from threading import Lock
from typing import Protocol

import config


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int = 0


@dataclass
class BucketState:
    tokens: float
    last_refill: float
    expires_at: float


class RateLimitStore(Protocol):
    def consume(self, client_key: str, now: float) -> RateLimitDecision: ...


def consume_bucket(
    state: BucketState | None,
    *,
    now: float,
    capacity: int,
    refill_seconds: float,
    state_ttl_seconds: int,
) -> tuple[RateLimitDecision, BucketState | None]:
    """Apply deterministic token-bucket arithmetic independent of storage."""
    if state is None or state.expires_at <= now:
        available = float(capacity)
    else:
        elapsed = max(0.0, now - state.last_refill)
        available = min(float(capacity), state.tokens + elapsed / refill_seconds)

    if available < 1:
        retry_after = max(1, ceil((1 - available) * refill_seconds))
        return RateLimitDecision(False, retry_after), None

    return (
        RateLimitDecision(True),
        BucketState(
            tokens=available - 1,
            last_refill=now,
            expires_at=now + state_ttl_seconds,
        ),
    )


class InMemoryTokenBucketStore:
    """Thread-safe development adapter with the same behavior as Firestore."""

    def __init__(self, capacity: int, refill_seconds: float, state_ttl_seconds: int):
        self.capacity = capacity
        self.refill_seconds = refill_seconds
        self.state_ttl_seconds = state_ttl_seconds
        self._states: dict[str, BucketState] = {}
        self._lock = Lock()

    def consume(self, client_key: str, now: float) -> RateLimitDecision:
        with self._lock:
            decision, next_state = consume_bucket(
                self._states.get(client_key),
                now=now,
                capacity=self.capacity,
                refill_seconds=self.refill_seconds,
                state_ttl_seconds=self.state_ttl_seconds,
            )
            if next_state is not None:
                self._states[client_key] = next_state
            return decision

    def reset(self) -> None:
        with self._lock:
            self._states.clear()


class FirestoreTokenBucketStore:
    """Atomically share token buckets across every Cloud Run instance."""

    def __init__(self, capacity: int, refill_seconds: float, state_ttl_seconds: int):
        self.capacity = capacity
        self.refill_seconds = refill_seconds
        self.state_ttl_seconds = state_ttl_seconds
        self._client = None
        self._client_lock = Lock()

    def _get_client(self):
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    from google.cloud import firestore

                    self._client = firestore.Client(
                        project=config.FIRESTORE_PROJECT_ID or None
                    )
        return self._client

    def consume(self, client_key: str, now: float) -> RateLimitDecision:
        from google.cloud import firestore

        client = self._get_client()
        document = client.collection("rate_limits").document(client_key)
        transaction = client.transaction()

        @firestore.transactional
        def consume_in_transaction(transaction):
            snapshot = document.get(transaction=transaction)
            stored = snapshot.to_dict() if snapshot.exists else None
            state = (
                BucketState(
                    tokens=float(stored["tokens"]),
                    last_refill=float(stored["last_refill"]),
                    expires_at=float(stored["expires_at"]),
                )
                if stored
                else None
            )
            decision, next_state = consume_bucket(
                state,
                now=now,
                capacity=self.capacity,
                refill_seconds=self.refill_seconds,
                state_ttl_seconds=self.state_ttl_seconds,
            )
            if next_state is not None:
                transaction.set(
                    document,
                    {
                        "tokens": next_state.tokens,
                        "last_refill": next_state.last_refill,
                        "expires_at": next_state.expires_at,
                    },
                )
            return decision

        return consume_in_transaction(transaction)
