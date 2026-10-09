from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from wildfire_risk.firms_archive import REQUIRED_COLUMNS
from wildfire_risk.firms_client import (
    FirmsAreaSlice,
    download_area_slice,
    map_key_from_environment,
    plan_area_slices,
)


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


class FirmsClientTest(unittest.TestCase):
    def test_reads_map_key_only_from_the_environment(self):
        self.assertEqual(
            map_key_from_environment({"FIRMS_MAP_KEY": " key "}),
            "key",
        )
        with self.assertRaisesRegex(ValueError, "FIRMS_MAP_KEY"):
            map_key_from_environment({})

    def test_plans_inclusive_five_day_slices(self):
        slices = plan_area_slices(
            date(2024, 2, 27),
            date(2024, 3, 4),
        )

        self.assertEqual(
            slices,
            [
                FirmsAreaSlice(date(2024, 2, 27), date(2024, 3, 2)),
                FirmsAreaSlice(date(2024, 3, 3), date(2024, 3, 4)),
            ],
        )

    def test_downloads_atomically_and_returns_a_secret_free_url(self):
        payload = (",".join(REQUIRED_COLUMNS) + "\n").encode()
        requested_urls: list[str] = []

        def opener(url, *, timeout):
            requested_urls.append(url)
            self.assertEqual(timeout, 12)
            return FakeResponse(payload)

        with TemporaryDirectory() as temporary_directory:
            result = download_area_slice(
                map_key="secret/key",
                api_source="VIIRS_SNPP_SP",
                bounds=(-9.3, 41.8, -6.7, 43.8),
                area_slice=FirmsAreaSlice(
                    date(2024, 1, 1),
                    date(2024, 1, 5),
                ),
                output_directory=temporary_directory,
                timeout_seconds=12,
                opener=opener,
            )

            self.assertEqual(result.path.read_bytes(), payload)
            self.assertFalse(result.cached)
            self.assertNotIn("secret", result.source_url)
            self.assertIn("[MAP_KEY]", result.source_url)
            self.assertFalse(result.path.with_suffix(".csv.tmp").exists())

        self.assertIn("secret%2Fkey", requested_urls[0])

    def test_uses_valid_cache_without_requesting_again(self):
        payload = (",".join(REQUIRED_COLUMNS) + "\n").encode()
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            path = directory / "VIIRS_SNPP_SP_2024-01-01_2024-01-01.csv"
            path.write_bytes(payload)

            result = download_area_slice(
                map_key="unused-secret",
                api_source="VIIRS_SNPP_SP",
                bounds=(-9.3, 41.8, -6.7, 43.8),
                area_slice=FirmsAreaSlice(
                    date(2024, 1, 1),
                    date(2024, 1, 1),
                ),
                output_directory=directory,
                opener=lambda *args, **kwargs: self.fail("cache was ignored"),
            )

        self.assertTrue(result.cached)

    def test_rejects_invalid_response_without_creating_a_source_file(self):
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            with self.assertRaisesRegex(ValueError, "missing columns"):
                download_area_slice(
                    map_key="secret",
                    api_source="VIIRS_SNPP_SP",
                    bounds=(-9.3, 41.8, -6.7, 43.8),
                    area_slice=FirmsAreaSlice(
                        date(2024, 1, 1),
                        date(2024, 1, 1),
                    ),
                    output_directory=directory,
                    opener=lambda *args, **kwargs: FakeResponse(b"error\n"),
                )

            self.assertEqual(list(directory.glob("*")), [])


if __name__ == "__main__":
    unittest.main()
