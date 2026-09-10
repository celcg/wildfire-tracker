import os
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from typing import Annotated

import pandas as pd

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://project-d66d4e5f-ee28-4c77-845.web.app",
        "https://project-d66d4e5f-ee28-4c77-845.firebaseapp.com",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)

NASA_KEY = os.getenv("NASA_KEY")
CACHE_TTL_SECONDS = 15 * 60
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60
FIRE_COLUMNS = [
    "latitude",
    "longitude",
    "confidence",
    "acq_date",
    "acq_time",
    "satellite",
    "frp",
]
fire_cache = {}
fire_cache_lock = Lock()
request_history = defaultdict(deque)
request_history_lock = Lock()


def enforce_rate_limit(request: Request):
    client_host = request.client.host if request.client else "unknown"
    now = monotonic()

    with request_history_lock:
        timestamps = request_history[client_host]
        while timestamps and now - timestamps[0] >= RATE_LIMIT_WINDOW_SECONDS:
            timestamps.popleft()

        if len(timestamps) >= RATE_LIMIT_REQUESTS:
            retry_after = max(
                1,
                int(RATE_LIMIT_WINDOW_SECONDS - (now - timestamps[0])) + 1,
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)


def fetch_fires(days: int, force_refresh: bool = False) -> pd.DataFrame:
    if not NASA_KEY:
        raise HTTPException(status_code=503, detail="NASA_KEY is not configured")

    now = monotonic()
    with fire_cache_lock:
        cached = fire_cache.get(days)
        if cached and not force_refresh and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1].copy()

    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{NASA_KEY}/"
        "VIIRS_NOAA20_NRT/"
        "-10,35,5,44/"
        f"{days}"
    )

    try:
        fires = pd.read_csv(url)[FIRE_COLUMNS]
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="NASA FIRMS data is temporarily unavailable",
        ) from exc

    with fire_cache_lock:
        fire_cache[days] = (monotonic(), fires.copy())

    return fires


@app.get("/")
def home():
    return {"message": "Wildfire API working"}


@app.get("/fires", dependencies=[Depends(enforce_rate_limit)])
def fires(
    days: Annotated[int, Query(ge=1, le=10)] = 1,
    refresh: bool = False,
):
    return fetch_fires(days, force_refresh=refresh).to_dict(orient="records")


@app.get("/stats", dependencies=[Depends(enforce_rate_limit)])
def stats(days: Annotated[int, Query(ge=1, le=10)] = 1):
    df = fetch_fires(days)
    frp = pd.to_numeric(df["frp"], errors="coerce").dropna()

    return {
        "days": days,
        "total_detections": len(df),
        "average_frp": round(float(frp.mean()), 2) if not frp.empty else 0,
        "maximum_frp": round(float(frp.max()), 2) if not frp.empty else 0,
        "detections_by_satellite": df["satellite"].value_counts().to_dict(),
    }
