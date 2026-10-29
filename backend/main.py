"""FastAPI composition root for the Wildfire Tracker service."""

import logging
from time import perf_counter
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from client_identity import CLIENT_ID_HEADER
from ai_rate_limit import enforce_ai_request
from ai_search import (
    FireSearchInterpretation,
    SearchQuestion,
    interpret_question,
)
from config import ALLOWED_ORIGINS, AI_SEARCH_MAX_REQUEST_BYTES, FIRE_COLUMNS
from firebase_security import APP_CHECK_HEADER
from fire_data import (
    DATA_AGE_SECONDS_ATTR,
    DATA_STALE_ATTR,
    fetch_fires,
    summarize_fires,
)
from incident_data import derive_incidents
from historical_ingest import IngestionResult, ingest_fire_history
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
from scheduler_auth import enforce_scheduler_auth
from vertex_ai_search import get_vertex_search_generator


logger = get_logger("http")


class AiSearchBodyLimitMiddleware:
    """Bound the public AI body before FastAPI allocates or parses arbitrary JSON."""

    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http" or scope.get("path") != "/search/interpret":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        declared_length = headers.get(b"content-length")
        if declared_length:
            try:
                if int(declared_length) > self.max_bytes:
                    await self._reject(scope, receive, send, 413, "Search request is too large.")
                    return
            except ValueError:
                await self._reject(scope, receive, send, 400, "Invalid Content-Length.")
                return

        # Buffering finishes before the application is called, but the buffer can
        # never exceed the configured limit. This also covers chunked requests.
        messages = []
        received_bytes = 0
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                messages.append(message)
                break
            received_bytes += len(message.get("body", b""))
            if received_bytes > self.max_bytes:
                await self._reject(scope, receive, send, 413, "Search request is too large.")
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay_receive():
            if messages:
                return messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(scope, receive, send, status_code: int, detail: str) -> None:
        response = JSONResponse({"detail": detail}, status_code=status_code)
        await response(scope, receive, send)


def _append_server_timing(
    response: Response | None,
    metric: str,
    started_at: float,
) -> None:
    """Expose aggregate stage timing without visitor or fire-location data."""
    if response is None:
        return
    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    previous = response.headers.get("Server-Timing")
    value = f"{metric};dur={duration_ms}"
    response.headers["Server-Timing"] = f"{previous}, {value}" if previous else value


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
        _append_server_timing(response, "total", started_at)
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
    data_started_at = perf_counter()
    fire_frame = fetch_fires(days, force_refresh=refresh)
    _append_server_timing(response, "data", data_started_at)
    _set_data_freshness_headers(response, fire_frame)
    # Validation may attach internal quality metadata for historical ingestion;
    # public reads retain the established detection shape.
    transform_started_at = perf_counter()
    records = fire_frame[FIRE_COLUMNS].to_dict(orient="records")
    _append_server_timing(response, "transform", transform_started_at)
    return records


def stats(
    days: Annotated[int, Query(ge=1, le=10)] = 1,
    response: Response = None,
) -> dict:
    """Return a compact aggregate without duplicating data-access logic."""
    data_started_at = perf_counter()
    fire_frame = fetch_fires(days)
    _append_server_timing(response, "data", data_started_at)
    _set_data_freshness_headers(response, fire_frame)
    transform_started_at = perf_counter()
    summary = summarize_fires(fire_frame, days)
    _append_server_timing(response, "transform", transform_started_at)
    return summary


def incidents(
    days: Annotated[int, Query(ge=1, le=10)] = 1,
    refresh: bool = False,
    response: Response = None,
) -> IncidentCollection:
    """Group detections into explainable possible fire areas."""
    data_started_at = perf_counter()
    fire_frame = fetch_fires(days, force_refresh=refresh)
    _append_server_timing(response, "data", data_started_at)
    _set_data_freshness_headers(response, fire_frame)
    derivation_started_at = perf_counter()
    collection = derive_incidents(fire_frame, days)
    _append_server_timing(response, "cluster", derivation_started_at)
    return collection


def ingest_history() -> IngestionResult:
    """Run the Scheduler-only analytics ingestion independently of public reads."""
    return ingest_fire_history()


def interpret_fire_search(payload: SearchQuestion) -> FireSearchInterpretation:
    """Translate one bounded question into filters without exposing data or tools."""
    started_at = perf_counter()
    try:
        interpretation = interpret_question(
            payload.question,
            get_vertex_search_generator(),
        )
    except Exception as exc:
        log_event(
            logger,
            logging.WARNING,
            "ai_search.failed",
            error_type=type(exc).__name__,
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
        )
        raise HTTPException(
            status_code=503,
            detail="Search interpretation is temporarily unavailable.",
            headers={"Retry-After": "60"},
        ) from None

    log_event(
        logger,
        logging.INFO,
        "ai_search.completed",
        status=interpretation.status,
        duration_ms=round((perf_counter() - started_at) * 1000, 2),
    )
    return interpretation


def create_app() -> FastAPI:
    """Build the HTTP boundary while keeping domain services framework-light."""
    configure_logging()
    application = FastAPI(
        title="Wildfire Tracker API",
        description="Recent NASA FIRMS detections for the Iberian Peninsula.",
    )

    application.add_middleware(
        AiSearchBodyLimitMiddleware,
        max_bytes=AI_SEARCH_MAX_REQUEST_BYTES,
    )

    # CORS is intentionally an allowlist: the public API need not authorize
    # arbitrary browser origins even though it has no user credentials.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
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
            "Server-Timing",
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
    application.add_api_route(
        "/search/interpret",
        interpret_fire_search,
        methods=["POST"],
        response_model=FireSearchInterpretation,
        dependencies=[Depends(enforce_ai_request)],
    )
    application.add_api_route(
        "/internal/ingest",
        ingest_history,
        methods=["POST"],
        response_model=IngestionResult,
        dependencies=[Depends(enforce_scheduler_auth)],
        include_in_schema=False,
    )
    return application


app = create_app()
