"""FastAPI composition root for the Wildfire Tracker service."""

from typing import Annotated

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from config import ALLOWED_ORIGINS
from fire_data import fetch_fires, summarize_fires
from rate_limit import enforce_rate_limit


def home() -> dict[str, str]:
    """Lightweight health endpoint that does not consume the data rate limit."""
    return {"message": "Wildfire API working"}


def fires(
    days: Annotated[int, Query(ge=1, le=10)] = 1,
    refresh: bool = False,
) -> list[dict]:
    """Return recent detections for a validated observation window."""
    fire_frame = fetch_fires(days, force_refresh=refresh)
    return fire_frame.to_dict(orient="records")


def stats(days: Annotated[int, Query(ge=1, le=10)] = 1) -> dict:
    """Return a compact aggregate without duplicating data-access logic."""
    return summarize_fires(fetch_fires(days), days)


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
    return application


app = create_app()
