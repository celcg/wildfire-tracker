"""Validated Open-Meteo historical weather retrieval for one H3 cell."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import h3
import pandas as pd


OPEN_METEO_ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARIABLES = (
    "temperature_2m_max",
    "relative_humidity_2m_min",
    "relative_humidity_2m_mean",
    "wind_speed_10m_max",
    "precipitation_sum",
)
EXPECTED_UNITS = {
    "temperature_2m_max": "°C",
    "relative_humidity_2m_min": "%",
    "relative_humidity_2m_mean": "%",
    "wind_speed_10m_max": "m/s",
    "precipitation_sum": "mm",
}


@dataclass(frozen=True)
class WeatherDownload:
    path: Path
    source_url: str
    cached: bool
    frame: pd.DataFrame


def weather_request_url(
    *,
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
    model: str = "era5_seamless",
) -> str:
    if start_date > end_date:
        raise ValueError("Weather period start must be on or before its end")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Invalid weather coordinates")
    if model != "era5_seamless":
        raise ValueError("Weather model must be era5_seamless")
    parameters = {
        "latitude": f"{latitude:.6f}",
        "longitude": f"{longitude:.6f}",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "GMT",
        "models": model,
        "cell_selection": "land",
        "wind_speed_unit": "ms",
    }
    return f"{OPEN_METEO_ARCHIVE_API}?{urlencode(parameters)}"


def normalize_weather_response(
    payload: bytes,
    *,
    h3_cell: str,
    start_date: date,
    end_date: date,
    model: str = "era5_seamless",
) -> pd.DataFrame:
    try:
        response = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Weather response is not valid JSON") from error
    if not isinstance(response, dict) or response.get("error"):
        raise ValueError("Weather response contains an API error")
    if response.get("utc_offset_seconds") != 0:
        raise ValueError("Weather response is not in UTC")

    units = response.get("daily_units")
    if not isinstance(units, dict):
        raise ValueError("Weather response is missing daily units")
    for variable, expected_unit in EXPECTED_UNITS.items():
        if units.get(variable) != expected_unit:
            raise ValueError(f"Unexpected unit for {variable}")

    daily = response.get("daily")
    if not isinstance(daily, dict):
        raise ValueError("Weather response is missing daily data")
    expected_dates: list[date] = []
    current = start_date
    while current <= end_date:
        expected_dates.append(current)
        current += timedelta(days=1)
    returned_dates = [
        date.fromisoformat(value)
        for value in daily.get("time", [])
    ]
    if returned_dates != expected_dates:
        raise ValueError("Weather response does not cover the requested dates")

    values: dict[str, object] = {
        "h3_cell": [h3_cell] * len(expected_dates),
        "target_date": expected_dates,
    }
    for variable in DAILY_VARIABLES:
        observations = daily.get(variable)
        if not isinstance(observations, list) or len(observations) != len(
            expected_dates
        ):
            raise ValueError(f"Weather response has invalid {variable} values")
        values[variable] = observations

    frame = pd.DataFrame(values)
    for variable in DAILY_VARIABLES:
        frame[variable] = pd.to_numeric(frame[variable], errors="coerce").astype(
            "Float64"
        )
    try:
        source_latitude = float(response["latitude"])
        source_longitude = float(response["longitude"])
        source_elevation = float(response["elevation"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Weather response has invalid source coordinates") from error
    frame["source_model"] = model
    frame["source_latitude"] = source_latitude
    frame["source_longitude"] = source_longitude
    frame["source_elevation_m"] = source_elevation
    return frame


def download_weather_period(
    *,
    h3_cell: str,
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
    output_directory: str | Path,
    model: str = "era5_seamless",
    timeout_seconds: float = 60,
    opener: Callable[..., Any] = urlopen,
) -> WeatherDownload:
    if not h3.is_valid_cell(h3_cell):
        raise ValueError("Invalid H3 cell")
    source_url = weather_request_url(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        model=model,
    )
    output_directory = Path(output_directory)
    output_path = output_directory / (
        f"{h3_cell}_{start_date.isoformat()}_{end_date.isoformat()}.json"
    )
    if output_path.exists():
        payload = output_path.read_bytes()
        frame = normalize_weather_response(
            payload,
            h3_cell=h3_cell,
            start_date=start_date,
            end_date=end_date,
            model=model,
        )
        return WeatherDownload(output_path, source_url, True, frame)

    try:
        with opener(source_url, timeout=timeout_seconds) as response:
            if getattr(response, "status", 200) != 200:
                raise RuntimeError("Weather request returned a non-success status")
            payload = response.read()
    except (HTTPError, URLError, OSError):
        raise RuntimeError("Weather request failed") from None

    frame = normalize_weather_response(
        payload,
        h3_cell=h3_cell,
        start_date=start_date,
        end_date=end_date,
        model=model,
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".json.tmp")
    try:
        temporary_path.write_bytes(payload)
        temporary_path.replace(output_path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
    return WeatherDownload(output_path, source_url, False, frame)
