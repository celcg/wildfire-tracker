"""NASA FIRMS access and the process-local fire-data cache."""

from threading import Lock
from time import monotonic

import pandas as pd
from fastapi import HTTPException

import config


# A lock makes the cache safe when FastAPI serves synchronous routes in threads.
_fire_cache: dict[int, tuple[float, pd.DataFrame]] = {}
_fire_cache_lock = Lock()
# Cache checks alone cannot prevent a burst of simultaneous misses. This lock
# coalesces those misses so only the first request reaches NASA.
_nasa_fetch_lock = Lock()
_last_nasa_attempt: dict[int, float] = {}

DATA_STALE_ATTR = "data_stale"
DATA_AGE_SECONDS_ATTR = "data_age_seconds"


def clear_fire_cache() -> None:
    """Reset process-local data; primarily useful for isolated tests."""
    with _nasa_fetch_lock:
        with _fire_cache_lock:
            _fire_cache.clear()
        _last_nasa_attempt.clear()


def _with_cache_metadata(
    fires: pd.DataFrame,
    age_seconds: float,
    is_stale: bool,
) -> pd.DataFrame:
    """Attach transport metadata to a copy without changing the fire schema."""
    result = fires.copy()
    result.attrs[DATA_STALE_ATTR] = is_stale
    result.attrs[DATA_AGE_SECONDS_ATTR] = max(0, int(age_seconds))
    return result


def _get_cached_fires(days: int, now: float) -> pd.DataFrame | None:
    """Return cached data even when stale so it remains available as fallback."""
    with _fire_cache_lock:
        cached = _fire_cache.get(days)

        if not cached:
            return None

        cached_at, fires = cached
        age_seconds = max(0, now - cached_at)
        is_stale = age_seconds >= config.CACHE_TTL_SECONDS
        return _with_cache_metadata(fires, age_seconds, is_stale)


def _store_fires(days: int, fires: pd.DataFrame, cached_at: float) -> None:
    with _fire_cache_lock:
        _fire_cache[days] = (cached_at, fires.copy())


def _is_fresh(fires: pd.DataFrame | None) -> bool:
    return fires is not None and not fires.attrs[DATA_STALE_ATTR]


def _retry_after(last_attempt: float, now: float) -> int:
    elapsed = max(0, now - last_attempt)
    return max(1, int(config.CACHE_TTL_SECONDS - elapsed) + 1)


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
    """Fetch detections without querying NASA more than once per cache window.

    ``force_refresh`` bypasses browser-held data at the HTTP boundary, but it
    deliberately does not bypass this server-side NASA protection interval.
    """
    if not config.NASA_KEY:
        raise HTTPException(status_code=503, detail="NASA_KEY is not configured")

    cached_fires = _get_cached_fires(days, monotonic())
    if _is_fresh(cached_fires):
        return cached_fires

    # Recheck after acquiring the lock: another request may have populated the
    # cache while this request was waiting.
    with _nasa_fetch_lock:
        now = monotonic()
        cached_fires = _get_cached_fires(days, now)
        if _is_fresh(cached_fires):
            return cached_fires

        last_attempt = _last_nasa_attempt.get(days)
        if (
            last_attempt is not None
            and now - last_attempt < config.CACHE_TTL_SECONDS
        ):
            if cached_fires is not None:
                return cached_fires
            raise HTTPException(
                status_code=503,
                detail="NASA FIRMS refresh is temporarily throttled",
                headers={"Retry-After": str(_retry_after(last_attempt, now))},
            )

        # Record attempts, not only successes, so an upstream outage cannot
        # turn a burst of refresh clicks into repeated NASA requests.
        _last_nasa_attempt[days] = now

        try:
            fires = pd.read_csv(_build_firms_url(days))[config.FIRE_COLUMNS]
        except Exception as exc:
            if cached_fires is not None:
                return cached_fires
            # Never expose the upstream URL because it contains the NASA API key.
            raise HTTPException(
                status_code=502,
                detail="NASA FIRMS data is temporarily unavailable",
            ) from exc

        _store_fires(days, fires, now)
        return _with_cache_metadata(fires, age_seconds=0, is_stale=False)


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
