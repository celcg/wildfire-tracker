"""FastAPI composition root for the Wildfire Tracker service."""

from typing import Annotated

from fastapi import Depends, FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from config import ALLOWED_ORIGINS
from fire_data import (
    DATA_AGE_SECONDS_ATTR,
    DATA_STALE_ATTR,
    fetch_fires,
    summarize_fires,
)
from incident_clustering import cluster_fires
from rate_limit import enforce_rate_limit
from schemas import IncidentCollection


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
        allow_headers=["Accept", "Content-Type"],
        expose_headers=["X-Data-Stale", "X-Data-Age-Seconds"],
    )

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
