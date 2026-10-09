from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd
import pyarrow.parquet as pq

from wildfire_risk.dataset import build_dataset, write_dataset_parquet
from wildfire_risk.settings import Periods
from wildfire_risk.weather_client import DAILY_VARIABLES


CELLS = ["851111111111111", "852222222222222"]
PERIODS = Periods(
    train_start=date(2024, 1, 1),
    train_end=date(2024, 1, 3),
    validation_start=date(2024, 1, 4),
    validation_end=date(2024, 1, 6),
    test_start=date(2024, 1, 7),
    test_end=date(2024, 1, 10),
)


def frames():
    dates = pd.date_range("2024-01-01", "2024-01-10").date
    labels = pd.DataFrame(
        [
            {
                "h3_cell": cell,
                "target_date": target_date,
                "detection_count": 0,
                "label_detection": 0,
                "label_status": "available",
            }
            for target_date in dates
            for cell in CELLS
        ]
    )
    grid = pd.DataFrame(
        [
            {
                "h3_cell": cell,
                "h3_resolution": 5,
                "cell_area_km2": 250.0,
                "galicia_area_km2": 200.0,
                "galicia_fraction": 0.8,
                "weather_latitude": 42.1,
                "weather_longitude": -8.6,
            }
            for cell in CELLS
        ]
    )
    weather_rows = []
    for day, target_date in enumerate(dates, start=1):
        for cell in CELLS:
            weather_rows.append(
                {
                    "h3_cell": cell,
                    "target_date": target_date,
                    "temperature_2m_max": 20 + day,
                    "relative_humidity_2m_min": 40 + day,
                    "relative_humidity_2m_mean": 60 + day,
                    "wind_speed_10m_max": 5 + day,
                    "precipitation_sum": float(day),
                    "source_model": "era5_seamless",
                }
            )
    return labels, grid, pd.DataFrame(weather_rows)


class DatasetTest(unittest.TestCase):
    def test_builds_features_without_same_day_leakage(self):
        labels, grid, weather = frames()
        dataset = build_dataset(labels, grid, weather, periods=PERIODS)

        self.assertEqual(len(dataset), 20)
        target = dataset[
            (dataset["h3_cell"] == CELLS[0])
            & (dataset["target_date"] == date(2024, 1, 8))
        ].iloc[0]
        self.assertEqual(target["precipitation_sum"], 8.0)
        self.assertEqual(target["precipitation_sum_lag1"], 7.0)
        self.assertEqual(target["precipitation_sum_7d_lag1"], 28.0)
        self.assertEqual(target["precipitation_valid_days_7d_lag1"], 7)
        self.assertEqual(target["split"], "test")

        first = dataset[
            (dataset["h3_cell"] == CELLS[0])
            & (dataset["target_date"] == date(2024, 1, 1))
        ].iloc[0]
        self.assertTrue(pd.isna(first["precipitation_sum_lag1"]))
        self.assertEqual(first["precipitation_valid_days_7d_lag1"], 0)

    def test_preserves_cardinality_and_marks_missing_weather(self):
        labels, grid, weather = frames()
        missing_key = (
            (weather["h3_cell"] == CELLS[1])
            & (weather["target_date"] == date(2024, 1, 5))
        )
        weather = weather.loc[~missing_key]

        dataset = build_dataset(labels, grid, weather, periods=PERIODS)
        missing = dataset[
            (dataset["h3_cell"] == CELLS[1])
            & (dataset["target_date"] == date(2024, 1, 5))
        ].iloc[0]

        self.assertEqual(len(dataset), len(labels))
        self.assertEqual(missing["weather_status"], "missing")
        self.assertEqual(missing["weather_valid_variables"], 0)
        self.assertTrue(
            all(pd.isna(missing[variable]) for variable in DAILY_VARIABLES)
        )

    def test_writes_zstandard_parquet_with_metadata_atomically(self):
        labels, grid, weather = frames()
        dataset = build_dataset(labels, grid, weather, periods=PERIODS)

        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "nested" / "dataset.parquet"
            write_dataset_parquet(
                dataset,
                path,
                metadata={"schema_version": 1, "h3_resolution": 5},
            )
            parquet_metadata = pq.read_metadata(path)
            arrow_metadata = pq.read_schema(path).metadata

            self.assertEqual(parquet_metadata.num_rows, len(dataset))
            self.assertEqual(
                json.loads(arrow_metadata[b"wildfire_risk.schema_version"]),
                1,
            )
            self.assertEqual(
                parquet_metadata.row_group(0).column(0).compression,
                "ZSTD",
            )
            self.assertFalse(path.with_suffix(".parquet.tmp").exists())


if __name__ == "__main__":
    unittest.main()
