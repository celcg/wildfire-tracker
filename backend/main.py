"""FastAPI composition root for the Wildfire Tracker service."""

import logging
from time import perf_counter
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from client_identity import CLIENT_ID_HEADER
from config import ALLOWED_ORIGINS
from firebase_security import APP_CHECK_HEADER
from fire_data import (
    DATA_AGE_SECONDS_ATTR,
    DATA_STALE_ATTR,
    fetch_fires,
    summarize_fires,
)
from incident_clustering import cluster_fires
from logging_config import (
    REQUEST_ID_HEADER,
    bind_request_id,
    configure_logging,
    get_logger,
    log_event,
    reset_request_id,
)
from rate_limit import enforce_rate_limit
from schemas import IncidentCollection


logger = get_logger("http")


def _resolve_request_id(candidate: str | None) -> str:
    """Accept canonical UUIDs only so untrusted headers cannot poison logs."""
    if candidate:
        try:
            return str(UUID(candidate))
        except (ValueError, AttributeError):
            pass
    return str(uuid4())


def _request_log_fields(request: Request, response: Response | None) -> dict:
    """Whitelist useful metadata instead of logging raw URLs or headers."""
    route = request.scope.get("route")
    fields = {
        "method": request.method,
        "path": getattr(route, "path", "unmatched"),
    }
    for parameter in ("days", "refresh"):
        if parameter in request.query_params:
            fields[parameter] = request.query_params[parameter]

    if response is not None:
        fields["status"] = response.status_code
        stale = response.headers.get("X-Data-Stale")
        age = response.headers.get("X-Data-Age-Seconds")
        if stale is not None:
            fields["data_stale"] = stale
        if age is not None:
            fields["data_age_seconds"] = age
    return fields


async def log_http_request(request: Request, call_next):
    """Correlate browser and API activity with one safe completion event."""
    request_id = _resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
    token = bind_request_id(request_id)
    started_at = perf_counter()
    response = None

    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        if response.status_code >= 500:
            level = logging.ERROR
        log_event(
            logger,
            level,
            "api.request.completed",
            **_request_log_fields(request, response),
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
        )
        return response
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "api.request.failed",
            **_request_log_fields(request, response),
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
            error_type=type(exc).__name__,
        )
        raise
    finally:
        reset_request_id(token)


def home() -> dict[str, str]:
    """Lightweight health endpoint that does not consume the data rate limit."""
    return {"message": "Wildfire API working"}


def _set_data_freshness_headers(
    response: Response | None,
    fire_frame,
) -> None:
    """Expose cache status without changing the established JSON contracts."""
    if response is None:
        return

    is_stale = bool(fire_frame.attrs.get(DATA_STALE_ATTR, False))
    age_seconds = int(fire_frame.attrs.get(DATA_AGE_SECONDS_ATTR, 0))
    response.headers["X-Data-Stale"] = str(is_stale).lower()
    response.headers["X-Data-Age-Seconds"] = str(max(0, age_seconds))


def fires(
    days: Annotated[int, Query(ge=1, le=10)] = 1,
    refresh: bool = False,
    response: Response = None,
) -> list[dict]:
    """Return recent detections for a validated observation window."""
    fire_frame = fetch_fires(days, force_refresh=refresh)
    _set_data_freshness_headers(response, fire_frame)
    return fire_frame.to_dict(orient="records")


def stats(
    days: Annotated[int, Query(ge=1, le=10)] = 1,
    response: Response = None,
) -> dict:
    """Return a compact aggregate without duplicating data-access logic."""
    fire_frame = fetch_fires(days)
    _set_data_freshness_headers(response, fire_frame)
    return summarize_fires(fire_frame, days)


def incidents(
    days: Annotated[int, Query(ge=1, le=10)] = 1,
    refresh: bool = False,
    response: Response = None,
) -> IncidentCollection:
    """Group detections into explainable possible fire areas."""
    fire_frame = fetch_fires(days, force_refresh=refresh)
    _set_data_freshness_headers(response, fire_frame)
    return cluster_fires(fire_frame, days)


def create_app() -> FastAPI:
    """Build the HTTP boundary while keeping domain services framework-light."""
    configure_logging()
    application = FastAPI(
        title="Wildfire Tracker API",
        description="Recent NASA FIRMS detections for the Iberian Peninsula.",
    )

    # CORS is intentionally an allowlist: the public API need not authorize
    # arbitrary browser origins even though it has no user credentials.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=[
            "Accept",
            "Content-Type",
            REQUEST_ID_HEADER,
            CLIENT_ID_HEADER,
            APP_CHECK_HEADER,
        ],
        expose_headers=[
            "X-Data-Stale",
            "X-Data-Age-Seconds",
            REQUEST_ID_HEADER,
        ],
    )
    application.middleware("http")(log_http_request)

    # Explicit registration keeps route functions directly unit-testable.
    application.add_api_route("/", home, methods=["GET"])
    application.add_api_route(
        "/fires",
        fires,
        methods=["GET"],
        dependencies=[Depends(enforce_rate_limit)],
    )
    application.add_api_route(
        "/stats",
        stats,
        methods=["GET"],
        dependencies=[Depends(enforce_rate_limit)],
    )
    application.add_api_route(
        "/incidents",
        incidents,
        methods=["GET"],
        response_model=IncidentCollection,
        dependencies=[Depends(enforce_rate_limit)],
    )
    return application


app = create_app()
