"""Fail-closed per-installation and global cost guards for AI interpretation."""

from fastapi import HTTPException, Request

import config
from client_identity import resolve_client_key
from firebase_security import enforce_app_check
from rate_limit import AnonymousRateLimiter


class AiRateLimiter:
    """Bound both individual abuse and total Vertex AI spend across instances."""

    def __init__(self, per_client_store=None, global_store=None) -> None:
        common = {
            "local_guard_capacity": config.AI_LOCAL_GUARD_CAPACITY,
            "local_guard_refill_seconds": config.AI_LOCAL_GUARD_REFILL_SECONDS,
            "fail_open": False,
        }
        self.per_client = AnonymousRateLimiter(
            per_client_store,
            capacity=config.AI_RATE_LIMIT_CAPACITY,
            refill_seconds=config.AI_RATE_LIMIT_REFILL_SECONDS,
            **common,
        )
        self.global_limit = AnonymousRateLimiter(
            global_store,
            capacity=config.AI_GLOBAL_RATE_LIMIT_CAPACITY,
            refill_seconds=config.AI_GLOBAL_RATE_LIMIT_REFILL_SECONDS,
            **common,
        )

    def enforce(self, request: Request) -> None:
        enforce_app_check(request)
        client_key = resolve_client_key(request)
        self.per_client.enforce_key("ai-client-" + client_key)
        self.global_limit.enforce_key("ai-global")

    def reset(self) -> None:
        self.per_client.reset()
        self.global_limit.reset()


ai_rate_limiter = AiRateLimiter()


def enforce_ai_request(request: Request) -> None:
    """Reject oversized bodies before a request can consume a paid model call."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > config.AI_SEARCH_MAX_REQUEST_BYTES:
                raise HTTPException(status_code=413, detail="Search request is too large.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length.") from None
    ai_rate_limiter.enforce(request)
