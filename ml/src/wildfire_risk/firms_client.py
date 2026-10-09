"""Small, secret-safe client for FIRMS standard-processing area slices."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
import io
import os
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from .firms_archive import REQUIRED_COLUMNS


FIRMS_AREA_API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


@dataclass(frozen=True)
class FirmsAreaSlice:
    start_date: date
    end_date: date

    @property
    def day_count(self) -> int:
        return (self.end_date - self.start_date).days + 1


@dataclass(frozen=True)
class FirmsDownload:
    path: Path
    source_url: str
    cached: bool
    size_bytes: int


def map_key_from_environment(
    environment: Mapping[str, str] = os.environ,
) -> str:
    map_key = environment.get("FIRMS_MAP_KEY", "").strip()
    if not map_key:
        raise ValueError("FIRMS_MAP_KEY is required")
    return map_key


def plan_area_slices(
    start_date: date,
    end_date: date,
    *,
    max_days: int = 5,
) -> list[FirmsAreaSlice]:
    if start_date > end_date:
        raise ValueError("FIRMS period start must be on or before its end")
    if not 1 <= max_days <= 5:
        raise ValueError("FIRMS Area API supports slices of 1 to 5 days")

    slices: list[FirmsAreaSlice] = []
    current = start_date
    while current <= end_date:
        slice_end = min(current + timedelta(days=max_days - 1), end_date)
        slices.append(FirmsAreaSlice(current, slice_end))
        current = slice_end + timedelta(days=1)
    return slices


def _area_text(bounds: tuple[float, float, float, float]) -> str:
    west, south, east, north = bounds
    if not (
        -180 <= west < east <= 180
        and -90 <= south < north <= 90
    ):
        raise ValueError("Invalid FIRMS area bounds")
    return ",".join(
        f"{coordinate:.6f}".rstrip("0").rstrip(".")
        for coordinate in bounds
    )


def _area_url(
    *,
    map_key: str,
    api_source: str,
    bounds: tuple[float, float, float, float],
    area_slice: FirmsAreaSlice,
) -> str:
    if not map_key.strip():
        raise ValueError("FIRMS_MAP_KEY is required")
    if api_source != "VIIRS_SNPP_SP":
        raise ValueError("Only VIIRS_SNPP_SP is supported by this experiment")
    if not 1 <= area_slice.day_count <= 5:
        raise ValueError("FIRMS Area API supports slices of 1 to 5 days")
    return (
        f"{FIRMS_AREA_API}/{quote(map_key.strip(), safe='')}/{api_source}/"
        f"{_area_text(bounds)}/{area_slice.day_count}/"
        f"{area_slice.start_date.isoformat()}"
    )


def _public_area_url(
    *,
    api_source: str,
    bounds: tuple[float, float, float, float],
    area_slice: FirmsAreaSlice,
) -> str:
    return (
        f"{FIRMS_AREA_API}/[MAP_KEY]/{api_source}/{_area_text(bounds)}/"
        f"{area_slice.day_count}/{area_slice.start_date.isoformat()}"
    )


def _validate_csv(payload: bytes) -> None:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("FIRMS response is not UTF-8 CSV") from error
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None:
        raise ValueError("FIRMS response is empty")
    missing = set(REQUIRED_COLUMNS) - set(header)
    if missing:
        raise ValueError(f"FIRMS response is missing columns: {sorted(missing)}")


def download_area_slice(
    *,
    map_key: str,
    api_source: str,
    bounds: tuple[float, float, float, float],
    area_slice: FirmsAreaSlice,
    output_directory: str | Path,
    timeout_seconds: float = 60,
    opener: Callable[..., Any] = urlopen,
) -> FirmsDownload:
    output_directory = Path(output_directory)
    filename = (
        f"{api_source}_{area_slice.start_date.isoformat()}_"
        f"{area_slice.end_date.isoformat()}.csv"
    )
    output_path = output_directory / filename
    public_url = _public_area_url(
        api_source=api_source,
        bounds=bounds,
        area_slice=area_slice,
    )
    if output_path.exists():
        payload = output_path.read_bytes()
        _validate_csv(payload)
        return FirmsDownload(output_path, public_url, True, len(payload))

    request_url = _area_url(
        map_key=map_key,
        api_source=api_source,
        bounds=bounds,
        area_slice=area_slice,
    )
    try:
        with opener(request_url, timeout=timeout_seconds) as response:
            if getattr(response, "status", 200) != 200:
                raise RuntimeError("FIRMS request returned a non-success status")
            payload = response.read()
    except (HTTPError, URLError, OSError):
        raise RuntimeError("FIRMS request failed") from None

    _validate_csv(payload)
    output_directory.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".csv.tmp")
    try:
        temporary_path.write_bytes(payload)
        temporary_path.replace(output_path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
    return FirmsDownload(output_path, public_url, False, len(payload))
