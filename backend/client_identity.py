"""Validate anonymous browser identities without retaining their raw values."""

import hashlib
import hmac
from uuid import UUID

from fastapi import HTTPException, Request

import config


CLIENT_ID_HEADER = "X-Client-ID"
LEGACY_CLIENT_NAMESPACE = b"legacy-client-without-installation-id"


def _digest(value: bytes) -> str:
    if not config.CLIENT_ID_HASH_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Client identification is not configured",
        )
    return hmac.new(
        config.CLIENT_ID_HASH_SECRET.encode("utf-8"),
        value,
        hashlib.sha256,
    ).hexdigest()


def resolve_client_key(request: Request) -> str:
    """Return a stable HMAC key for one valid, canonical installation UUID."""
    candidate = request.headers.get(CLIENT_ID_HEADER, "")
    if not candidate and not config.CLIENT_ID_REQUIRED:
        return _digest(LEGACY_CLIENT_NAMESPACE)

    try:
        client_id = UUID(candidate)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="A valid X-Client-ID header is required",
        ) from None

    if candidate != str(client_id) or client_id.version != 4:
        raise HTTPException(
            status_code=400,
            detail="X-Client-ID must be a canonical UUIDv4",
        )
    return _digest(client_id.bytes)
