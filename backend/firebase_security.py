"""Firebase App Check verification for the public custom API."""

import logging
from threading import Lock

from fastapi import HTTPException, Request

import config
from logging_config import get_logger, log_event


APP_CHECK_HEADER = "X-Firebase-AppCheck"
logger = get_logger("app_check")
_firebase_lock = Lock()


def _verify_token(token: str) -> None:
    """Initialize Firebase lazily so local tools do not require credentials."""
    import firebase_admin
    from firebase_admin import app_check

    with _firebase_lock:
        try:
            firebase_admin.get_app()
        except ValueError:
            options = (
                {"projectId": config.FIRESTORE_PROJECT_ID}
                if config.FIRESTORE_PROJECT_ID
                else None
            )
            firebase_admin.initialize_app(options=options)
    app_check.verify_token(token)


def enforce_app_check(request: Request) -> None:
    """Require an attested frontend in Cloud Run while remaining local-friendly."""
    if not config.APP_CHECK_REQUIRED:
        return

    token = request.headers.get(APP_CHECK_HEADER)
    if not token:
        raise HTTPException(status_code=403, detail="App Check token is required")

    try:
        _verify_token(token)
    except Exception as exc:
        # Never include the token or exception text because SDK errors may echo
        # untrusted inputs. The exception type is sufficient for diagnostics.
        log_event(
            logger,
            logging.WARNING,
            "app_check.rejected",
            error_type=type(exc).__name__,
        )
        raise HTTPException(status_code=403, detail="Invalid App Check token") from None
