"""Cache incident derivations alongside immutable fire snapshots."""

import logging
from threading import Lock
from time import perf_counter

import pandas as pd

from fire_data import FIRE_SNAPSHOT_ATTR
from incident_clustering import cluster_fires
from logging_config import get_logger, log_event
from schemas import IncidentCollection


_incident_cache: dict[int, tuple[int, IncidentCollection]] = {}
_cache_lock = Lock()
_derivation_locks: dict[int, Lock] = {}
logger = get_logger("incident_data")


def clear_incident_cache() -> None:
    """Reset process-local derivations for isolated tests."""
    with _cache_lock:
        _incident_cache.clear()
        _derivation_locks.clear()


def _cached(days: int, snapshot_id: int) -> IncidentCollection | None:
    with _cache_lock:
        cached = _incident_cache.get(days)
        if cached is None or cached[0] != snapshot_id:
            return None
        return cached[1]


def derive_incidents(fires: pd.DataFrame, days: int) -> IncidentCollection:
    """Reuse clustering only when the exact backend fire snapshot is unchanged."""
    snapshot_id = fires.attrs.get(FIRE_SNAPSHOT_ATTR)
    if not isinstance(snapshot_id, int):
        # Frames created outside fire_data (notably unit tests and ingestion)
        # have no cache identity and must never reuse an unrelated derivation.
        return cluster_fires(fires, days)

    cached = _cached(days, snapshot_id)
    if cached is not None:
        log_event(logger, logging.INFO, "incident_cache.hit", days=days)
        return cached

    with _cache_lock:
        derivation_lock = _derivation_locks.setdefault(days, Lock())

    # Coalesce simultaneous /incidents requests for the same day window. The
    # second cache check is essential because another request may have finished
    # the expensive clustering while this one waited.
    with derivation_lock:
        cached = _cached(days, snapshot_id)
        if cached is not None:
            log_event(logger, logging.INFO, "incident_cache.hit_after_wait", days=days)
            return cached

        started_at = perf_counter()
        collection = cluster_fires(fires, days)
        with _cache_lock:
            existing = _incident_cache.get(days)
            # A slow request for an older snapshot must not replace a newer
            # derivation that completed first.
            if existing is None or existing[0] <= snapshot_id:
                _incident_cache[days] = (snapshot_id, collection)
        log_event(
            logger,
            logging.INFO,
            "incident_cache.generated",
            days=days,
            detection_count=len(fires),
            incident_count=collection.incident_count,
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
        )
        return collection
