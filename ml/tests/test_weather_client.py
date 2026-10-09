from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import parse_qs, urlsplit

import h3
import pandas as pd

from wildfire_risk.weather_client import (
    DAILY_VARIABLES,
    EXPECTED_UNITS,
    download_weather_period,
    normalize_weather_response,
    weather_request_url,
)


CELL = h3.latlng_to_cell(42.1, -8.6, 5)


def weather_payload(*, dates=None) -> bytes:
    dates = dates or ["2024-01-01", "2024-01-02"]
    daily = {"time": dates}
    for index, variable in enumerate(DAILY_VARIABLES):
        daily[variable] = [float(index + day) for day in range(len(dates))]
    return json.dumps(
        {
            "latitude": 42.1,
            "longitude": -8.6,
            "elevation": 321.0,
            "utc_offset_seconds": 0,
            "timezone": "GMT",
            "daily_units": {"time": "iso8601", **EXPECTED_UNITS},
            "daily": daily,
        }
    ).encode()


class FakeResponse:
    status = 200

    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        return False

    def read(self) -> bytes:
        return self.payload


class WeatherClientTest(unittest.TestCase):
    def test_builds_explicit_era5_seamless_request(self):
        url = weather_request_url(
            latitude=42.1,
            longitude=-8.6,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        query = parse_qs(urlsplit(url).query)

        self.assertEqual(query["models"], ["era5_seamless"])
        self.assertEqual(query["timezone"], ["GMT"])
        self.assertEqual(query["cell_selection"], ["land"])
        self.assertEqual(query["wind_speed_unit"], ["ms"])
        self.assertEqual(query["daily"], [",".join(DAILY_VARIABLES)])

    def test_normalizes_exact_daily_coverage_and_units(self):
        frame = normalize_weather_response(
            weather_payload(),
            h3_cell=CELL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
        )

        self.assertEqual(frame["target_date"].tolist(), [
            date(2024, 1, 1),
            date(2024, 1, 2),
        ])
        self.assertTrue(
            all(
                dtype == pd.Float64Dtype()
                for dtype in frame[list(DAILY_VARIABLES)].dtypes
            )
        )
        self.assertEqual(
            frame["source_model"].unique().tolist(),
            ["era5_seamless"],
        )
        self.assertEqual(frame["source_elevation_m"].iloc[0], 321.0)

    def test_rejects_incomplete_daily_coverage(self):
        with self.assertRaisesRegex(ValueError, "requested dates"):
            normalize_weather_response(
                weather_payload(dates=["2024-01-01"]),
                h3_cell=CELL,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 2),
            )

    def test_downloads_atomically_then_uses_valid_cache(self):
        payload = weather_payload()
        calls = 0

        def opener(url, *, timeout):
            nonlocal calls
            calls += 1
            self.assertEqual(timeout, 15)
            return FakeResponse(payload)

        with TemporaryDirectory() as temporary_directory:
            arguments = {
                "h3_cell": CELL,
                "latitude": 42.1,
                "longitude": -8.6,
                "start_date": date(2024, 1, 1),
                "end_date": date(2024, 1, 2),
                "output_directory": Path(temporary_directory),
                "timeout_seconds": 15,
                "opener": opener,
            }
            downloaded = download_weather_period(**arguments)
            cached = download_weather_period(**arguments)

            self.assertFalse(downloaded.cached)
            self.assertTrue(cached.cached)
            self.assertEqual(downloaded.frame.to_dict(), cached.frame.to_dict())
            self.assertFalse(downloaded.path.with_suffix(".json.tmp").exists())

        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
