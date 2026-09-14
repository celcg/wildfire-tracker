"""Application service for the isolated hourly analytics ingestion."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from time import perf_counter

from fastapi import HTTPException

import config
from bigquery_repository import (
    BigQueryHistoryRepository,
    BigQueryStorageLimitExceeded,
)
from fire_data import DATA_STALE_ATTR, fetch_fires
from historical_models import build_ingestion_batch, detection_id, snapshot_hour
from incident_clustering import cluster_fires
from logging_config import get_logger, log_event


logger = get_logger("historical_ingest")


@dataclass(frozen=True)
class IngestionResult:
    status: str
    snapshot_at: str
    detections_processed: int
    cluster_snapshots_processed: int
    clusters_merged: int


@lru_cache(maxsize=1)
def get_history_repository() -> BigQueryHistoryRepository:
    return BigQueryHistoryRepository()


def _incident_detection_ids(incidents) -> list[str]:
    return [
        detection_id(
            latitude=detection.latitude,
            longitude=detection.longitude,
            acq_date=detection.acq_date,
            acq_time=detection.acq_time,
            satellite=detection.satellite,
        )
        for incident in incidents.incidents
        for detection in incident.detections
    ]


def ingest_fire_history(
    repository: BigQueryHistoryRepository | None = None,
) -> IngestionResult:
    """Persist one fresh 24-hour view without affecting public read routes."""
    if not config.BIGQUERY_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Historical ingestion is disabled",
        )

    started_at = perf_counter()
    fires = fetch_fires(days=1, force_refresh=True)
    if bool(fires.attrs.get(DATA_STALE_ATTR, False)):
        log_event(logger, logging.WARNING, "history.skipped_stale_data")
        raise HTTPException(
            status_code=503,
            detail="Fresh NASA data is required for historical ingestion",
        )

    incidents = cluster_fires(fires, days=1)
    snapshot_at = snapshot_hour()
    detection_ids = _incident_detection_ids(incidents)
    if not detection_ids:
        log_event(logger, logging.INFO, "history.no_detections")
        return IngestionResult(
            status="no_data",
            snapshot_at=snapshot_at.isoformat().replace("+00:00", "Z"),
            detections_processed=0,
            cluster_snapshots_processed=0,
            clusters_merged=0,
        )

    try:
        history = repository or get_history_repository()
        existing = history.existing_assignments(
            detection_ids,
            min(
                date.fromisoformat(detection.acq_date)
                for incident in incidents.incidents
                for detection in incident.detections
            ),
        )
        batch = build_ingestion_batch(
            fires,
            incidents,
            existing,
            at=snapshot_at,
        )
        history.write_batch(batch)
    except BigQueryStorageLimitExceeded:
        log_event(logger, logging.ERROR, "history.storage_guard_reached")
        raise HTTPException(
            status_code=507,
            detail="Historical storage safety threshold reached",
        ) from None
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "history.write_failed",
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Historical ingestion temporarily failed",
        ) from None

    result = IngestionResult(
        status="ingested",
        snapshot_at=snapshot_at.isoformat().replace("+00:00", "Z"),
        detections_processed=len(batch.detections),
        cluster_snapshots_processed=len(batch.clusters),
        clusters_merged=len(batch.merged_cluster_ids),
    )
    log_event(
        logger,
        logging.INFO,
        "history.write_succeeded",
        detections_processed=result.detections_processed,
        cluster_snapshots_processed=result.cluster_snapshots_processed,
        clusters_merged=result.clusters_merged,
        duration_ms=round((perf_counter() - started_at) * 1000, 2),
    )
    return result
