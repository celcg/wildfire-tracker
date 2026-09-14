"""OIDC authentication for the private Cloud Scheduler ingestion route."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request

import config
from logging_config import get_logger, log_event


logger = get_logger("scheduler_auth")


def _bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=401,
            detail="Scheduler authentication is required",
        )
    return token.strip()


def _verify_google_token(token: str) -> dict:
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2 import id_token

    return id_token.verify_oauth2_token(
        token,
        GoogleRequest(),
        audience=config.SCHEDULER_AUDIENCE,
    )


def enforce_scheduler_auth(request: Request) -> None:
    """Accept only Google's signed token for the configured scheduler account."""
    if not config.SCHEDULER_AUDIENCE or not config.SCHEDULER_SERVICE_ACCOUNT:
        raise HTTPException(
            status_code=503,
            detail="Historical ingestion authentication is not configured",
        )

    token = _bearer_token(request)
    try:
        claims = _verify_google_token(token)
        email = claims.get("email")
        email_verified = claims.get("email_verified")
        if email != config.SCHEDULER_SERVICE_ACCOUNT or email_verified is not True:
            raise ValueError("Unexpected scheduler identity")
    except Exception as exc:
        log_event(
            logger,
            logging.WARNING,
            "scheduler_auth.rejected",
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid scheduler authentication",
        ) from None

