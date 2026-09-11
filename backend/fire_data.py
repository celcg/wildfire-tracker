"""NASA FIRMS access and the process-local fire-data cache."""

from threading import Lock
from time import monotonic

import pandas as pd
from fastapi import HTTPException

import config


# A lock makes the cache safe when FastAPI serves synchronous routes in threads.
_fire_cache: dict[int, tuple[float, pd.DataFrame]] = {}
_fire_cache_lock = Lock()


def clear_fire_cache() -> None:
    """Reset process-local data; primarily useful for isolated tests."""
    with _fire_cache_lock:
        _fire_cache.clear()


def _get_cached_fires(days: int) -> pd.DataFrame | None:
    """Return a defensive copy so callers cannot mutate the shared cache."""
    with _fire_cache_lock:
        cached = _fire_cache.get(days)

        if not cached:
            return None

        cached_at, fires = cached
        if monotonic() - cached_at >= config.CACHE_TTL_SECONDS:
            del _fire_cache[days]
            return None

        return fires.copy()


def _store_fires(days: int, fires: pd.DataFrame) -> None:
    with _fire_cache_lock:
        _fire_cache[days] = (monotonic(), fires.copy())


def _build_firms_url(days: int) -> str:
    """Keep the secret server-side while constructing the documented FIRMS URL."""
    return (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{config.NASA_KEY}/"
        f"{config.NASA_DATASET}/"
        f"{config.IBERIAN_BOUNDS}/"
        f"{days}"
    )


def fetch_fires(days: int, force_refresh: bool = False) -> pd.DataFrame:
    """Fetch recent detections, reusing a valid per-window cache when possible."""
    if not config.NASA_KEY:
        raise HTTPException(status_code=503, detail="NASA_KEY is not configured")

    if not force_refresh:
        cached_fires = _get_cached_fires(days)
        if cached_fires is not None:
            return cached_fires

    try:
        fires = pd.read_csv(_build_firms_url(days))[config.FIRE_COLUMNS]
    except Exception as exc:
        # Never expose the upstream URL because it contains the NASA API key.
        raise HTTPException(
            status_code=502,
            detail="NASA FIRMS data is temporarily unavailable",
        ) from exc

    _store_fires(days, fires)
    return fires


def summarize_fires(fires: pd.DataFrame, days: int) -> dict:
    """Convert a data frame into the stable JSON shape exposed by /stats."""
    frp = pd.to_numeric(fires["frp"], errors="coerce").dropna()

    return {
        "days": days,
        "total_detections": len(fires),
        "average_frp": round(float(frp.mean()), 2) if not frp.empty else 0,
        "maximum_frp": round(float(frp.max()), 2) if not frp.empty else 0,
        "detections_by_satellite": fires["satellite"].value_counts().to_dict(),
    }
