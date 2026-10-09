"""Build the complete cell/day target panel from normalized detections."""

from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd


REQUIRED_COLUMNS = frozenset({"h3_cell", "target_date", "confidence"})
CONFIDENCE_ALIASES = {
    "n": "nominal",
    "nominal": "nominal",
    "h": "high",
    "high": "high",
    "l": "low",
    "low": "low",
}


def build_label_panel(
    detections: pd.DataFrame,
    *,
    h3_cells: Iterable[str],
    start_date: date,
    end_date: date,
    accepted_confidence: frozenset[str],
    excluded_dates: Iterable[date] = (),
) -> pd.DataFrame:
    """Return one deterministic row per configured cell and UTC date."""
    missing = REQUIRED_COLUMNS - set(detections.columns)
    if missing:
        raise ValueError(f"Detections are missing columns: {sorted(missing)}")
    if start_date > end_date:
        raise ValueError("start_date must not be after end_date")

    cells = sorted(set(h3_cells))
    if not cells or any(not isinstance(cell, str) or not cell for cell in cells):
        raise ValueError("h3_cells must contain non-empty strings")
    if "detection_id" in detections and detections["detection_id"].duplicated().any():
        raise ValueError("detection_id must be unique before aggregation")

    normalized = detections.copy()
    parsed_dates = pd.to_datetime(normalized["target_date"], errors="coerce").dt.date
    if parsed_dates.isna().any() or normalized["h3_cell"].isna().any():
        raise ValueError("Detection cell and target_date are required")
    normalized["target_date"] = parsed_dates

    unknown_cells = set(normalized["h3_cell"]) - set(cells)
    if unknown_cells:
        raise ValueError("Detections contain cells outside the configured grid")
    outside_period = (
        (normalized["target_date"] < start_date)
        | (normalized["target_date"] > end_date)
    )
    if outside_period.any():
        raise ValueError("Detections contain dates outside the configured period")

    confidence = (
        normalized["confidence"]
        .astype("string")
        .str.strip()
        .str.lower()
        .map(CONFIDENCE_ALIASES)
        .fillna("unknown")
    )
    accepted = normalized.loc[confidence.isin(accepted_confidence)]
    counts = accepted.groupby(["target_date", "h3_cell"]).size()

    index = pd.MultiIndex.from_product(
        [pd.date_range(start_date, end_date, freq="D").date, cells],
        names=["target_date", "h3_cell"],
    )
    panel = counts.reindex(index, fill_value=0).rename("detection_count").reset_index()
    panel["detection_count"] = panel["detection_count"].astype("Int32")
    panel["label_detection"] = (panel["detection_count"] > 0).astype("Int8")
    panel["label_status"] = "available"

    excluded = set(excluded_dates)
    invalid_exclusions = excluded - set(index.levels[0])
    if invalid_exclusions:
        raise ValueError("Excluded dates must be inside the configured period")
    excluded_rows = panel["target_date"].isin(excluded)
    panel.loc[excluded_rows, ["detection_count", "label_detection"]] = pd.NA
    panel.loc[excluded_rows, "label_status"] = "excluded_source_period"

    return panel.sort_values(["target_date", "h3_cell"], ignore_index=True)
