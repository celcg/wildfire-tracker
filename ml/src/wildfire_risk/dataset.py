"""Assemble and persist the deterministic cell/day modelling dataset."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Mapping

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .settings import Periods
from .weather_client import DAILY_VARIABLES


LABEL_COLUMNS = {
    "h3_cell",
    "target_date",
    "detection_count",
    "label_detection",
    "label_status",
}
GRID_COLUMNS = {
    "h3_cell",
    "h3_resolution",
    "cell_area_km2",
    "galicia_area_km2",
    "galicia_fraction",
    "weather_latitude",
    "weather_longitude",
}
WEATHER_COLUMNS = {"h3_cell", "target_date", *DAILY_VARIABLES}


def _require_columns(
    frame: pd.DataFrame,
    required: set[str],
    name: str,
) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")


def _normalize_dates(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    normalized = frame.copy()
    dates = pd.to_datetime(normalized["target_date"], errors="coerce").dt.date
    if dates.isna().any():
        raise ValueError(f"{name} contains invalid target dates")
    normalized["target_date"] = dates
    return normalized


def _require_unique(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    if frame.duplicated(columns).any():
        raise ValueError(f"{name} must be unique by {columns}")


def build_dataset(
    labels: pd.DataFrame,
    grid: pd.DataFrame,
    weather: pd.DataFrame,
    *,
    periods: Periods,
) -> pd.DataFrame:
    _require_columns(labels, LABEL_COLUMNS, "labels")
    _require_columns(grid, GRID_COLUMNS, "grid")
    _require_columns(weather, WEATHER_COLUMNS, "weather")
    labels = _normalize_dates(labels, "labels")
    weather = _normalize_dates(weather, "weather")
    _require_unique(labels, ["h3_cell", "target_date"], "labels")
    _require_unique(grid, ["h3_cell"], "grid")
    _require_unique(weather, ["h3_cell", "target_date"], "weather")

    label_keys = pd.MultiIndex.from_frame(labels[["h3_cell", "target_date"]])
    weather_keys = pd.MultiIndex.from_frame(weather[["h3_cell", "target_date"]])
    if not weather_keys.difference(label_keys).empty:
        raise ValueError("weather contains rows outside the label panel")

    dataset = labels.merge(
        grid,
        on="h3_cell",
        how="left",
        validate="many_to_one",
    )
    if dataset[list(GRID_COLUMNS - {"h3_cell"})].isna().any().any():
        raise ValueError("labels contain cells outside the grid")
    dataset = dataset.merge(
        weather,
        on=["h3_cell", "target_date"],
        how="left",
        validate="one_to_one",
    )
    if len(dataset) != len(labels):
        raise ValueError("dataset cardinality changed during joins")

    dataset = dataset.sort_values(
        ["h3_cell", "target_date"],
        ignore_index=True,
    )
    valid_weather = dataset[list(DAILY_VARIABLES)].notna().sum(axis=1)
    dataset["weather_valid_variables"] = valid_weather.astype("Int8")
    dataset["weather_status"] = "partial"
    dataset.loc[valid_weather == 0, "weather_status"] = "missing"
    dataset.loc[
        valid_weather == len(DAILY_VARIABLES),
        "weather_status",
    ] = "available"

    grouped = dataset.groupby("h3_cell", sort=False)
    for variable in DAILY_VARIABLES:
        dataset[f"{variable}_lag1"] = grouped[variable].shift(1)
    precipitation = grouped["precipitation_sum"]
    dataset["precipitation_sum_7d_lag1"] = precipitation.transform(
        lambda values: values.shift(1).rolling(7, min_periods=1).sum()
    ).astype("Float64")
    dataset["precipitation_valid_days_7d_lag1"] = precipitation.transform(
        lambda values: values.shift(1).rolling(7, min_periods=1).count()
    ).astype("Int8")

    timestamps = pd.to_datetime(dataset["target_date"])
    days_in_year = timestamps.dt.is_leap_year.map({True: 366, False: 365})
    angle = 2 * math.pi * (timestamps.dt.dayofyear - 1) / days_in_year
    dataset["season_sin"] = angle.map(math.sin)
    dataset["season_cos"] = angle.map(math.cos)
    dataset["year"] = timestamps.dt.year.astype("Int16")
    dataset["split"] = dataset["target_date"].map(periods.split_for)

    return dataset.sort_values(
        ["target_date", "h3_cell"],
        ignore_index=True,
    )


def write_dataset_parquet(
    dataset: pd.DataFrame,
    path: str | Path,
    *,
    metadata: Mapping[str, object],
) -> None:
    _require_unique(dataset, ["h3_cell", "target_date"], "dataset")
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")

    table = pa.Table.from_pandas(dataset, preserve_index=False)
    arrow_metadata = dict(table.schema.metadata or {})
    for key, value in sorted(metadata.items()):
        arrow_metadata[f"wildfire_risk.{key}".encode()] = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    table = table.replace_schema_metadata(arrow_metadata)
    try:
        pq.write_table(table, temporary_path, compression="zstd")
        written = pq.read_table(
            temporary_path,
            columns=["h3_cell", "target_date"],
        )
        if written.num_rows != len(dataset):
            raise ValueError("Written Parquet row count does not match dataset")
        written_keys = written.to_pandas()
        _require_unique(
            written_keys,
            ["h3_cell", "target_date"],
            "written dataset",
        )
        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
