"""Pure transformations for the hourly BigQuery history snapshot."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Mapping

import pandas as pd

import config
from schemas import FireDetection, FireIncident, IncidentCollection


@dataclass(frozen=True)
class DetectionRecord:
    detection_id: str
    cluster_id: str
    cluster_snapshot_at: datetime
    observed_at: datetime
    observation_date: str
    latitude: float
    longitude: float
    satellite: str
    confidence: str
    frp_mw: float
    source_dataset: str


@dataclass(frozen=True)
class ClusterSnapshotRecord:
    cluster_id: str
    snapshot_at: datetime
    snapshot_date: str
    center_latitude: float
    center_longitude: float
    boundary_geojson: str
    member_detection_ids: tuple[str, ...]
    detection_count: int
    total_frp_mw: float
    maximum_frp_mw: float
    first_detected_at: datetime
    last_detected_at: datetime
    confidence: str
    trend: str
    severity: str
    status: str = "active"
    merged_into_cluster_id: str | None = None
    source_dataset: str = config.NASA_DATASET


@dataclass(frozen=True)
class IngestionBatch:
    snapshot_at: datetime
    detections: tuple[DetectionRecord, ...]
    clusters: tuple[ClusterSnapshotRecord, ...]
    merged_cluster_ids: tuple[str, ...]

    def detections_json(self) -> str:
        return json.dumps(
            [_json_record(record) for record in self.detections],
            separators=(",", ":"),
        )

    def clusters_json(self) -> str:
        return json.dumps(
            [_json_record(record) for record in self.clusters],
            separators=(",", ":"),
        )


def _json_record(record: object) -> dict:
    values = asdict(record)
    for key, value in values.items():
        if isinstance(value, datetime):
            values[key] = value.isoformat().replace("+00:00", "Z")
        elif isinstance(value, tuple):
            values[key] = list(value)
    return values


def snapshot_hour(moment: datetime | None = None) -> datetime:
    """Use one key per UTC hour so Scheduler retries remain idempotent."""
    current = moment or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def _acquisition_time(value: object) -> str:
    try:
        return str(int(float(value))).zfill(4)
    except (TypeError, ValueError):
        return str(value).zfill(4)


def detection_observed_at(acq_date: object, acq_time: object) -> datetime:
    parsed = pd.to_datetime(
        f"{acq_date} {_acquisition_time(acq_time)}",
        format="%Y-%m-%d %H%M",
        utc=True,
        errors="raise",
    )
    return parsed.to_pydatetime()


def detection_id(
    *,
    latitude: float,
    longitude: float,
    acq_date: object,
    acq_time: object,
    satellite: object,
    source_dataset: str = config.NASA_DATASET,
) -> str:
    """Identify a physical source observation independently of mutable fields."""
    observed_at = detection_observed_at(acq_date, acq_time)
    identity = "|".join(
        (
            source_dataset,
            str(satellite).strip(),
            observed_at.isoformat(),
            f"{float(latitude):.5f}",
            f"{float(longitude):.5f}",
        )
    )
    return sha256(identity.encode("utf-8")).hexdigest()


def _fire_detection_id(detection: FireDetection) -> str:
    return detection_id(
        latitude=detection.latitude,
        longitude=detection.longitude,
        acq_date=detection.acq_date,
        acq_time=detection.acq_time,
        satellite=detection.satellite,
    )


def _new_cluster_id(detections: list[tuple[str, FireDetection]]) -> str:
    anchor_id, _ = min(
        detections,
        key=lambda item: (
            detection_observed_at(item[1].acq_date, item[1].acq_time),
            item[0],
        ),
    )
    return f"cluster-{sha256(anchor_id.encode('ascii')).hexdigest()[:16]}"


def _canonical_cluster_id(
    members: list[tuple[str, FireDetection]],
    existing_assignments: Mapping[str, str],
    consumed_cluster_ids: set[str],
) -> tuple[str, set[str], set[str]]:
    assigned = {
        detection_key: existing_assignments[detection_key]
        for detection_key, _ in members
        if detection_key in existing_assignments
    }
    available_ids = set(assigned.values()) - consumed_cluster_ids
    if not available_ids:
        return _new_cluster_id(members), set(), set()

    # The cluster containing the earliest known observation wins a merge. The
    # ID tie-breaker makes the outcome deterministic for simultaneous passes.
    candidates = [
        (detection_key, cluster_id)
        for detection_key, cluster_id in assigned.items()
        if cluster_id in available_ids
    ]
    detections_by_id = dict(members)
    canonical = min(
        candidates,
        key=lambda item: (
            detection_observed_at(
                detections_by_id[item[0]].acq_date,
                detections_by_id[item[0]].acq_time,
            ),
            item[1],
        ),
    )[1]
    merged = available_ids - {canonical}
    return canonical, merged, available_ids


def _boundary_geojson(incident: FireIncident) -> str:
    coordinates = [
        [point.longitude, point.latitude] for point in incident.boundary
    ]
    if coordinates and coordinates[0] != coordinates[-1]:
        coordinates.append(coordinates[0])
    return json.dumps(
        {"type": "Polygon", "coordinates": [coordinates]},
        separators=(",", ":"),
    )


def _cluster_snapshot(
    incident: FireIncident,
    cluster_id: str,
    member_ids: tuple[str, ...],
    at: datetime,
    *,
    status: str = "active",
    merged_into: str | None = None,
) -> ClusterSnapshotRecord:
    return ClusterSnapshotRecord(
        cluster_id=cluster_id,
        snapshot_at=at,
        snapshot_date=at.date().isoformat(),
        center_latitude=incident.center.latitude,
        center_longitude=incident.center.longitude,
        boundary_geojson=_boundary_geojson(incident),
        member_detection_ids=member_ids,
        detection_count=len(member_ids),
        total_frp_mw=incident.total_frp_mw if status == "active" else 0,
        maximum_frp_mw=incident.maximum_frp_mw if status == "active" else 0,
        first_detected_at=incident.first_detected_at,
        last_detected_at=incident.last_detected_at,
        confidence=incident.confidence,
        trend=incident.trend,
        severity=incident.severity,
        status=status,
        merged_into_cluster_id=merged_into,
    )


def build_ingestion_batch(
    fires: pd.DataFrame,
    incidents: IncidentCollection,
    existing_assignments: Mapping[str, str],
    *,
    at: datetime | None = None,
) -> IngestionBatch:
    """Build deduplicated facts and hourly cluster snapshots without I/O."""
    at = snapshot_hour(at)
    source_rows: dict[str, object] = {}
    for row in fires.itertuples():
        key = detection_id(
            latitude=float(row.latitude),
            longitude=float(row.longitude),
            acq_date=row.acq_date,
            acq_time=row.acq_time,
            satellite=row.satellite,
        )
        source_rows.setdefault(key, row)

    records: dict[str, DetectionRecord] = {}
    snapshots: list[ClusterSnapshotRecord] = []
    merged_ids: set[str] = set()

    consumed_cluster_ids: set[str] = set()
    # Resolve older components first. If a historical cluster splits after its
    # bridge ages out of the 24-hour window, only one component may retain the
    # previous ID; this preserves the composite snapshot primary key.
    ordered_incidents = sorted(
        incidents.incidents,
        key=lambda incident: (incident.first_detected_at, incident.id),
    )
    for incident in ordered_incidents:
        members_by_id = {
            _fire_detection_id(detection): detection
            for detection in incident.detections
        }
        members = sorted(members_by_id.items())
        cluster_id, merged, consumed = _canonical_cluster_id(
            members,
            existing_assignments,
            consumed_cluster_ids,
        )
        consumed_cluster_ids.update(consumed)
        member_ids = tuple(key for key, _ in members)
        snapshots.append(_cluster_snapshot(incident, cluster_id, member_ids, at))

        for merged_id in sorted(merged):
            snapshots.append(
                _cluster_snapshot(
                    incident,
                    merged_id,
                    (),
                    at,
                    status="merged",
                    merged_into=cluster_id,
                )
            )
        merged_ids.update(merged)

        for key, detection in members:
            row = source_rows[key]
            observed_at = detection_observed_at(row.acq_date, row.acq_time)
            frp = pd.to_numeric(row.frp, errors="coerce")
            frp = 0.0 if pd.isna(frp) else max(0.0, float(frp))
            records[key] = DetectionRecord(
                detection_id=key,
                cluster_id=cluster_id,
                cluster_snapshot_at=at,
                observed_at=observed_at,
                observation_date=observed_at.date().isoformat(),
                latitude=float(row.latitude),
                longitude=float(row.longitude),
                satellite=str(row.satellite),
                confidence=str(row.confidence),
                frp_mw=frp,
                source_dataset=config.NASA_DATASET,
            )

    return IngestionBatch(
        snapshot_at=at,
        detections=tuple(records[key] for key in sorted(records)),
        clusters=tuple(snapshots),
        merged_cluster_ids=tuple(sorted(merged_ids)),
    )
