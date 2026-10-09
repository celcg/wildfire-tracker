from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from wildfire_risk.firms_archive import (
    normalize_firms_csv,
    normalize_firms_frame,
)
from wildfire_risk.manifests import build_firms_manifest


def fire(**changes):
    row = {
        "latitude": 42.1,
        "longitude": -8.6,
        "acq_date": "2024-08-01",
        "acq_time": 35,
        "satellite": "N",
        "instrument": "VIIRS",
        "confidence": "n",
        "version": "2.0",
        "frp": 5.0,
    }
    row.update(changes)
    return row


class FirmsArchiveTest(unittest.TestCase):
    def test_normalizes_standard_snpp_rows_and_reports_exclusions(self):
        rows = [
            fire(frp=5.0),
            fire(frp=4.0),
            fire(latitude=42.2, confidence="l"),
            fire(latitude=100),
            fire(latitude=42.3, acq_time=2460),
            fire(latitude=42.4, satellite="N20"),
            fire(latitude=42.5, confidence="?"),
            fire(latitude=42.6, frp=-1),
            fire(latitude=42.7, version="2.0NRT"),
        ]

        normalized, report = normalize_firms_frame(
            pd.DataFrame(rows),
            source_product="VIIRS_SNPP_375M_STANDARD",
        )

        self.assertEqual(len(normalized), 3)
        by_latitude = normalized.set_index("latitude")
        self.assertEqual(by_latitude.loc[42.1, "confidence"], "nominal")
        self.assertEqual(by_latitude.loc[42.2, "confidence"], "low")
        self.assertEqual(by_latitude.loc[42.1, "frp_mw"], 4.0)
        self.assertTrue(pd.isna(by_latitude.loc[42.6, "frp_mw"]))
        self.assertEqual(report.received_rows, 9)
        self.assertEqual(report.accepted_rows, 3)
        self.assertEqual(report.dropped_rows, 6)
        self.assertEqual(report.duplicates_removed, 1)
        self.assertEqual(report.conflicting_duplicates, 1)
        self.assertEqual(report.invalid_coordinates, 1)
        self.assertEqual(report.invalid_timestamps, 1)
        self.assertEqual(report.invalid_platform, 1)
        self.assertEqual(report.invalid_confidence, 1)
        self.assertEqual(report.invalid_frp, 1)
        self.assertEqual(report.non_standard_version, 1)

    def test_csv_manifest_hashes_file_and_removes_url_credentials(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "snpp_2024.csv"
            pd.DataFrame([fire()]).to_csv(path, index=False)
            _, report = normalize_firms_csv(
                path,
                source_product="VIIRS_SNPP_375M_STANDARD",
            )

            manifest = build_firms_manifest(
                path,
                source_product="VIIRS_SNPP_375M_STANDARD",
                year=2024,
                source_url="https://example.test/archive.csv?token=secret",
                downloaded_at=datetime(2026, 10, 9, 12, tzinfo=timezone.utc),
                report=report,
            )

        self.assertEqual(manifest["source_url"], "https://example.test/archive.csv")
        self.assertEqual(len(manifest["sha256"]), 64)
        self.assertEqual(manifest["normalization"]["accepted_rows"], 1)

    def test_rejects_missing_required_columns(self):
        with self.assertRaisesRegex(ValueError, "missing columns"):
            normalize_firms_frame(
                pd.DataFrame([{"latitude": 42.1}]),
                source_product="VIIRS_SNPP_375M_STANDARD",
            )


if __name__ == "__main__":
    unittest.main()
