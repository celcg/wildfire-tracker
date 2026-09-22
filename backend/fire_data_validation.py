"""Schema validation and deterministic normalization for NASA FIRMS rows."""

from __future__ import annotations

import math
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd

import config


CONFIDENCE_ALIASES = {
    "l": "low",
    "low": "low",
    "n": "nominal",
    "nominal": "nominal",
    "h": "high",
    "high": "high",
}


class FireDataValidationError(RuntimeError):
    """Raised when an upstream dataset is unsafe to cache as a new snapshot."""


class FireDataRowLimitExceeded(FireDataValidationError):
    """Raised before an excessive frame reaches the quadratic clustering step."""


@dataclass(frozen=True)
class FireDataQualityReport:
    received_rows: int
    accepted_rows: int
    dropped_rows: int
    duplicates_removed: int
    conflicting_duplicates: int
    invalid_coordinates: int
    invalid_timestamps: int
    invalid_satellites: int
    invalid_frp: int
    high_frp: int
    unknown_confidence: int

    def log_fields(self) -> dict[str, int]:
        """Expose fixed aggregate fields without leaking source row contents."""
        return {
            "rows_received": self.received_rows,
            "rows_accepted": self.accepted_rows,
            "rows_dropped": self.dropped_rows,
            "duplicates_removed": self.duplicates_removed,
            "conflicting_duplicates": self.conflicting_duplicates,
            "invalid_coordinates": self.invalid_coordinates,
            "invalid_timestamps": self.invalid_timestamps,
            "invalid_satellites": self.invalid_satellites,
            "invalid_frp": self.invalid_frp,
            "high_frp": self.high_frp,
            "unknown_confidence": self.unknown_confidence,
        }


def acquisition_time_text(value: object) -> str:
    """Return a strict HHMM value instead of accepting arbitrary padded text."""
    numeric = float(value)
    if not math.isfinite(numeric) or not numeric.is_integer():
        raise ValueError("Invalid acquisition time")
    digits = str(int(numeric)).zfill(4)
    if len(digits) != 4:
        raise ValueError("Invalid acquisition time")
    hour, minute = int(digits[:2]), int(digits[2:])
    if hour > 23 or minute > 59:
        raise ValueError("Invalid acquisition time")
    return digits


def parse_observed_at(acq_date: object, acq_time: object) -> datetime:
    time_text = acquisition_time_text(acq_time)
    parsed = datetime.strptime(f"{acq_date} {time_text}", "%Y-%m-%d %H%M")
    return parsed.replace(tzinfo=timezone.utc)


def _clean_text(value: object, maximum_length: int) -> tuple[str, bool]:
    original = str(value)
    normalized = unicodedata.normalize("NFKC", original)
    cleaned = "".join(
        character
        for character in normalized
        if unicodedata.category(character)[0] != "C"
    ).strip()
    if not cleaned or len(cleaned) > maximum_length:
        raise ValueError("Invalid text field")
    return cleaned, cleaned != original


def _finite_float(value: object) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite numeric value")
    return number


def _configured_bounds() -> tuple[float, float, float, float]:
    try:
        west, south, east, north = map(float, config.IBERIAN_BOUNDS.split(","))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("IBERIAN_BOUNDS is invalid") from exc
    return west, south, east, north


def normalize_fire_data(
    fires: pd.DataFrame,
    days: int,
    *,
    now: datetime | None = None,
) -> tuple[pd.DataFrame, FireDataQualityReport]:
    """Return safe canonical rows plus aggregate, non-sensitive quality metrics."""
    missing_columns = set(config.FIRE_COLUMNS) - set(fires.columns)
    if missing_columns:
        raise FireDataValidationError("NASA payload is missing required columns")
    if len(fires) > config.NASA_MAX_ROWS:
        raise FireDataRowLimitExceeded("NASA payload exceeds the row limit")

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    earliest_time = current - timedelta(days=days)
    latest_time = current + timedelta(seconds=config.NASA_FUTURE_TOLERANCE_SECONDS)
    west, south, east, north = _configured_bounds()
    issue_counts: Counter[str] = Counter()
    normalized_by_identity: dict[tuple[object, ...], dict[str, object]] = {}

    for values in fires[config.FIRE_COLUMNS].itertuples(index=False, name=None):
        row = dict(zip(config.FIRE_COLUMNS, values))
        quality_flags: list[str] = []

        try:
            latitude = _finite_float(row["latitude"])
            longitude = _finite_float(row["longitude"])
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError("Coordinates outside Earth")
            if not (south <= latitude <= north and west <= longitude <= east):
                raise ValueError("Coordinates outside requested bounds")
        except (TypeError, ValueError):
            issue_counts["invalid_coordinates"] += 1
            continue

        try:
            observed_at = parse_observed_at(row["acq_date"], row["acq_time"])
            if observed_at < earliest_time or observed_at > latest_time:
                raise ValueError("Timestamp outside requested window")
        except (TypeError, ValueError):
            issue_counts["invalid_timestamps"] += 1
            continue

        try:
            satellite, text_changed = _clean_text(
                row["satellite"],
                config.NASA_MAX_TEXT_LENGTH,
            )
            if text_changed:
                quality_flags.append("satellite_sanitized")
        except (TypeError, ValueError):
            issue_counts["invalid_satellites"] += 1
            continue

        try:
            confidence, confidence_changed = _clean_text(
                row["confidence"],
                config.NASA_MAX_TEXT_LENGTH,
            )
            if confidence_changed:
                quality_flags.append("confidence_sanitized")
        except (TypeError, ValueError):
            confidence = "unknown"

        if confidence.lower() not in CONFIDENCE_ALIASES:
            issue_counts["unknown_confidence"] += 1
            quality_flags.append("confidence_unknown")

        try:
            frp = _finite_float(row["frp"])
            if frp < 0:
                raise ValueError("Negative FRP")
            if frp > config.NASA_HIGH_FRP_THRESHOLD_MW:
                issue_counts["high_frp"] += 1
                quality_flags.append("frp_high")
        except (TypeError, ValueError):
            frp = None
            issue_counts["invalid_frp"] += 1
            quality_flags.append("frp_invalid")

        identity = (
            round(latitude, 5),
            round(longitude, 5),
            observed_at,
            satellite,
        )
        canonical = {
            "latitude": latitude,
            "longitude": longitude,
            "confidence": confidence,
            "acq_date": observed_at.date().isoformat(),
            # pandas inferred this source column as an integer before validation;
            # retain that established public representation.
            "acq_time": int(observed_at.strftime("%H%M")),
            "satellite": satellite,
            "frp": frp,
            "quality_flags": tuple(sorted(quality_flags)),
        }
        previous = normalized_by_identity.get(identity)
        if previous is not None:
            issue_counts["duplicates_removed"] += 1
            if previous != canonical:
                issue_counts["conflicting_duplicates"] += 1
                # Lexicographic JSON-like comparison makes conflict resolution
                # independent of the order in which NASA returned duplicate rows.
                normalized_by_identity[identity] = min(
                    previous,
                    canonical,
                    key=lambda item: repr(sorted(item.items())),
                )
            continue
        normalized_by_identity[identity] = canonical

    normalized_rows = sorted(
        normalized_by_identity.values(),
        key=lambda row: (
            row["acq_date"],
            row["acq_time"],
            row["latitude"],
            row["longitude"],
            row["satellite"],
        ),
    )
    if len(fires) and not normalized_rows:
        raise FireDataValidationError("NASA payload contains no valid rows")

    columns = [*config.FIRE_COLUMNS, "quality_flags"]
    normalized = pd.DataFrame(normalized_rows, columns=columns)
    if not normalized.empty:
        # Object dtype preserves JSON null instead of leaking a non-standard NaN.
        normalized["frp"] = normalized["frp"].astype(object)
        normalized.loc[normalized["frp"].isna(), "frp"] = None

    report = FireDataQualityReport(
        received_rows=len(fires),
        accepted_rows=len(normalized),
        dropped_rows=len(fires) - len(normalized) - issue_counts["duplicates_removed"],
        duplicates_removed=issue_counts["duplicates_removed"],
        conflicting_duplicates=issue_counts["conflicting_duplicates"],
        invalid_coordinates=issue_counts["invalid_coordinates"],
        invalid_timestamps=issue_counts["invalid_timestamps"],
        invalid_satellites=issue_counts["invalid_satellites"],
        invalid_frp=issue_counts["invalid_frp"],
        high_frp=issue_counts["high_frp"],
        unknown_confidence=issue_counts["unknown_confidence"],
    )
    return normalized, report
