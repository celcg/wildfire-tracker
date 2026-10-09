"""Validate and normalize archived VIIRS S-NPP CSV rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import math
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = (
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "frp",
)
CONFIDENCE = {"l": "low", "n": "nominal", "h": "high"}
OUTPUT_COLUMNS = (
    "detection_id",
    "observed_at_utc",
    "target_date",
    "latitude",
    "longitude",
    "satellite",
    "instrument",
    "confidence",
    "frp_mw",
    "source_product",
    "source_version",
    "quality_flags",
)


@dataclass(frozen=True)
class FirmsNormalizationReport:
    received_rows: int
    accepted_rows: int
    dropped_rows: int
    duplicates_removed: int
    conflicting_duplicates: int
    invalid_coordinates: int
    invalid_timestamps: int
    invalid_platform: int
    invalid_confidence: int
    invalid_frp: int
    non_standard_version: int


def _finite_float(value: object) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Expected a finite number")
    return number


def _observed_at(acq_date: object, acq_time: object) -> datetime:
    numeric_time = _finite_float(acq_time)
    if not numeric_time.is_integer():
        raise ValueError("Acquisition time must be an integer")
    time_text = str(int(numeric_time)).zfill(4)
    if len(time_text) != 4:
        raise ValueError("Acquisition time must have four digits")
    observed = datetime.strptime(
        f"{acq_date} {time_text}", "%Y-%m-%d %H%M"
    )
    return observed.replace(tzinfo=timezone.utc)


def _detection_id(
    source_product: str,
    satellite: str,
    observed_at: datetime,
    latitude: float,
    longitude: float,
) -> str:
    identity = "|".join(
        (
            source_product,
            satellite,
            observed_at.isoformat(),
            f"{latitude:.5f}",
            f"{longitude:.5f}",
        )
    )
    return sha256(identity.encode("utf-8")).hexdigest()


def normalize_firms_frame(
    fires: pd.DataFrame,
    *,
    source_product: str,
    satellite_code: str = "N",
) -> tuple[pd.DataFrame, FirmsNormalizationReport]:
    missing = set(REQUIRED_COLUMNS) - set(fires.columns)
    if missing:
        raise ValueError(f"FIRMS CSV is missing columns: {sorted(missing)}")

    counts = {
        "duplicates_removed": 0,
        "conflicting_duplicates": 0,
        "invalid_coordinates": 0,
        "invalid_timestamps": 0,
        "invalid_platform": 0,
        "invalid_confidence": 0,
        "invalid_frp": 0,
        "non_standard_version": 0,
    }
    by_id: dict[str, tuple[tuple[str, str, str], dict[str, object]]] = {}

    for row in fires.loc[:, list(REQUIRED_COLUMNS)].itertuples(index=False):
        try:
            latitude = _finite_float(row.latitude)
            longitude = _finite_float(row.longitude)
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError("Coordinates outside Earth")
        except (TypeError, ValueError):
            counts["invalid_coordinates"] += 1
            continue

        try:
            observed_at = _observed_at(row.acq_date, row.acq_time)
        except (TypeError, ValueError):
            counts["invalid_timestamps"] += 1
            continue

        satellite = str(row.satellite).strip().upper()
        instrument = str(row.instrument).strip().upper()
        if satellite != satellite_code.upper() or instrument != "VIIRS":
            counts["invalid_platform"] += 1
            continue

        confidence = CONFIDENCE.get(str(row.confidence).strip().lower())
        if confidence is None:
            counts["invalid_confidence"] += 1
            continue

        version = str(row.version).strip()
        if not version or version.lower() == "nan" or version.upper().endswith(
            ("NRT", "RT", "URT")
        ):
            counts["non_standard_version"] += 1
            continue

        flags: tuple[str, ...] = ()
        try:
            frp = _finite_float(row.frp)
            if frp < 0:
                raise ValueError("FRP cannot be negative")
        except (TypeError, ValueError):
            frp = None
            flags = ("frp_invalid",)
            counts["invalid_frp"] += 1

        detection_id = _detection_id(
            source_product, satellite, observed_at, latitude, longitude
        )
        normalized = {
            "detection_id": detection_id,
            "observed_at_utc": observed_at,
            "target_date": observed_at.date(),
            "latitude": latitude,
            "longitude": longitude,
            "satellite": satellite,
            "instrument": instrument,
            "confidence": confidence,
            "frp_mw": frp,
            "source_product": source_product,
            "source_version": version,
            "quality_flags": flags,
        }
        sort_key = (confidence, "" if frp is None else f"{frp:.12g}", version)
        previous = by_id.get(detection_id)
        if previous is not None:
            counts["duplicates_removed"] += 1
            if previous[1] != normalized:
                counts["conflicting_duplicates"] += 1
            by_id[detection_id] = min(
                previous, (sort_key, normalized), key=lambda value: value[0]
            )
        else:
            by_id[detection_id] = (sort_key, normalized)

    normalized_frame = pd.DataFrame(
        [value[1] for value in by_id.values()],
        columns=OUTPUT_COLUMNS,
    ).sort_values(["observed_at_utc", "detection_id"], ignore_index=True)
    if not normalized_frame.empty:
        normalized_frame["frp_mw"] = normalized_frame["frp_mw"].astype("Float64")

    accepted_rows = len(normalized_frame)
    report = FirmsNormalizationReport(
        received_rows=len(fires),
        accepted_rows=accepted_rows,
        dropped_rows=len(fires) - accepted_rows,
        **counts,
    )
    return normalized_frame, report


def normalize_firms_csv(
    path: str | Path,
    *,
    source_product: str,
    satellite_code: str = "N",
) -> tuple[pd.DataFrame, FirmsNormalizationReport]:
    return normalize_firms_frame(
        pd.read_csv(path),
        source_product=source_product,
        satellite_code=satellite_code,
    )
