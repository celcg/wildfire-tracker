import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pandas as pd

import config
from fire_data_validation import (
    FireDataRowLimitExceeded,
    FireDataValidationError,
    normalize_fire_data,
)


NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


def fire(**overrides):
    values = {
        "latitude": 42.1,
        "longitude": -8.6,
        "confidence": "n",
        "acq_date": NOW.date().isoformat(),
        "acq_time": 900,
        "satellite": "N20",
        "frp": 5.5,
    }
    values.update(overrides)
    return values


class FireDataValidationTest(unittest.TestCase):
    def test_normalizes_fields_and_reports_non_sensitive_quality_counts(self):
        source = pd.DataFrame(
            [
                fire(
                    confidence="H",
                    satellite="N20\x00",
                    frp=config.NASA_HIGH_FRP_THRESHOLD_MW + 1,
                ),
                fire(
                    latitude=41.9,
                    confidence="unexpected",
                    frp="not-a-number",
                ),
            ]
        )

        result, quality = normalize_fire_data(source, days=1, now=NOW)

        high_frp = result.loc[result["latitude"] == 42.1].iloc[0]
        invalid_frp = result.loc[result["latitude"] == 41.9].iloc[0]
        self.assertEqual(high_frp["acq_time"], 900)
        self.assertEqual(high_frp["satellite"], "N20")
        self.assertEqual(high_frp["confidence"], "H")
        self.assertIn("satellite_sanitized", high_frp["quality_flags"])
        self.assertIn("frp_high", high_frp["quality_flags"])
        self.assertEqual(invalid_frp["confidence"], "unexpected")
        self.assertIsNone(invalid_frp["frp"])
        self.assertEqual(quality.received_rows, 2)
        self.assertEqual(quality.accepted_rows, 2)
        self.assertEqual(quality.high_frp, 1)
        self.assertEqual(quality.invalid_frp, 1)
        self.assertEqual(quality.unknown_confidence, 1)
        self.assertNotIn("latitude", quality.log_fields())

    def test_drops_invalid_coordinates_timestamps_and_satellites(self):
        source = pd.DataFrame(
            [
                fire(),
                fire(latitude=90),
                fire(acq_time=2460),
                fire(satellite="\x00\n"),
                fire(
                    latitude=41.8,
                    acq_date=(NOW.date() - timedelta(days=2)).isoformat(),
                ),
            ]
        )

        result, quality = normalize_fire_data(source, days=1, now=NOW)

        self.assertEqual(len(result), 1)
        self.assertEqual(quality.invalid_coordinates, 1)
        self.assertEqual(quality.invalid_timestamps, 2)
        self.assertEqual(quality.invalid_satellites, 1)
        self.assertEqual(quality.dropped_rows, 4)

    def test_uses_a_rolling_window_across_utc_midnight(self):
        shortly_after_midnight = datetime(
            2026,
            9,
            22,
            0,
            30,
            tzinfo=timezone.utc,
        )
        source = pd.DataFrame(
            [
                fire(acq_date="2026-09-21", acq_time=100),
                fire(latitude=41.9, acq_date="2026-09-20", acq_time=2300),
            ]
        )

        result, quality = normalize_fire_data(
            source,
            days=1,
            now=shortly_after_midnight,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["acq_date"], "2026-09-21")
        self.assertEqual(quality.invalid_timestamps, 1)

    def test_duplicate_resolution_is_deterministic_and_counted(self):
        first = fire(confidence="h", frp=20)
        second = fire(confidence="l", frp=10)

        forward, forward_quality = normalize_fire_data(
            pd.DataFrame([first, second]),
            days=1,
            now=NOW,
        )
        reverse, reverse_quality = normalize_fire_data(
            pd.DataFrame([second, first]),
            days=1,
            now=NOW,
        )

        pd.testing.assert_frame_equal(forward, reverse)
        self.assertEqual(forward_quality.duplicates_removed, 1)
        self.assertEqual(forward_quality.conflicting_duplicates, 1)
        self.assertEqual(reverse_quality.duplicates_removed, 1)

    def test_rejects_missing_columns_row_overflow_and_fully_invalid_payload(self):
        with self.assertRaisesRegex(FireDataValidationError, "required columns"):
            normalize_fire_data(pd.DataFrame([{"latitude": 42.1}]), 1, now=NOW)

        with patch.object(config, "NASA_MAX_ROWS", 1):
            with self.assertRaises(FireDataRowLimitExceeded):
                normalize_fire_data(pd.DataFrame([fire(), fire()]), 1, now=NOW)

        with self.assertRaisesRegex(FireDataValidationError, "no valid rows"):
            normalize_fire_data(
                pd.DataFrame([fire(longitude=180)]),
                1,
                now=NOW,
            )

    def test_rejects_non_finite_coordinates_and_accepts_null_frp(self):
        source = pd.DataFrame(
            [
                fire(latitude=float("nan")),
                fire(latitude=41.9, longitude=float("inf")),
                fire(latitude=41.8, frp=None),
            ]
        )

        result, quality = normalize_fire_data(source, days=1, now=NOW)

        self.assertEqual(len(result), 1)
        self.assertIsNone(result.iloc[0]["frp"])
        self.assertEqual(quality.invalid_coordinates, 2)
        self.assertEqual(quality.invalid_frp, 1)


if __name__ == "__main__":
    unittest.main()
