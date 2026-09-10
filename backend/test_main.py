import unittest
from unittest.mock import patch

import pandas as pd
from fastapi import HTTPException

import main


SAMPLE_FIRES = pd.DataFrame(
    [
        {
            "latitude": 42.1,
            "longitude": -8.6,
            "confidence": "high",
            "acq_date": "2026-09-10",
            "acq_time": 1200,
            "satellite": "NOAA-20",
            "frp": 10.5,
        },
        {
            "latitude": 40.4,
            "longitude": -3.7,
            "confidence": "nominal",
            "acq_date": "2026-09-09",
            "acq_time": 930,
            "satellite": "NOAA-20",
            "frp": 20.5,
        },
    ]
)


class FireEndpointsTest(unittest.TestCase):
    def setUp(self):
        main.fire_cache.clear()
        main.request_history.clear()

    @patch("main.fetch_fires", return_value=SAMPLE_FIRES)
    def test_fires_passes_days_to_data_source(self, fetch_fires):
        response = main.fires(days=3)

        fetch_fires.assert_called_once_with(3, force_refresh=False)
        self.assertEqual(len(response), 2)

    @patch("main.fetch_fires", return_value=SAMPLE_FIRES)
    def test_manual_refresh_bypasses_server_cache(self, fetch_fires):
        main.fires(days=3, refresh=True)

        fetch_fires.assert_called_once_with(3, force_refresh=True)

    @patch("main.fetch_fires", return_value=SAMPLE_FIRES)
    def test_stats_aggregates_fire_data(self, fetch_fires):
        response = main.stats(days=1)

        fetch_fires.assert_called_once_with(1)
        self.assertEqual(response["total_detections"], 2)
        self.assertEqual(response["average_frp"], 15.5)
        self.assertEqual(response["maximum_frp"], 20.5)
        self.assertEqual(response["detections_by_satellite"], {"NOAA-20": 2})

    @patch("main.fetch_fires")
    def test_stats_handles_missing_frp_values(self, fetch_fires):
        fire_without_frp = SAMPLE_FIRES.copy()
        fire_without_frp["frp"] = None
        fetch_fires.return_value = fire_without_frp

        response = main.stats(days=1)

        self.assertEqual(response["average_frp"], 0)
        self.assertEqual(response["maximum_frp"], 0)

    @patch("main.pd.read_csv", side_effect=RuntimeError("upstream failure"))
    def test_upstream_errors_do_not_expose_nasa_key(self, _read_csv):
        with patch.object(main, "NASA_KEY", "test-secret-that-must-not-leak"):
            with self.assertRaises(HTTPException) as raised:
                main.fetch_fires(days=1)

        self.assertEqual(raised.exception.status_code, 502)
        self.assertNotIn("test-secret", raised.exception.detail)

    def test_server_cache_avoids_repeated_nasa_requests(self):
        with patch.object(main, "NASA_KEY", "test-key"):
            with patch("main.pd.read_csv", return_value=SAMPLE_FIRES) as read_csv:
                first = main.fetch_fires(days=1)
                second = main.fetch_fires(days=1)

        read_csv.assert_called_once()
        self.assertEqual(len(first), len(second))

    def test_rate_limit_rejects_the_eleventh_request(self):
        request = main.Request(
            {
                "type": "http",
                "client": ("192.0.2.1", 1234),
                "headers": [],
                "method": "GET",
                "path": "/fires",
                "query_string": b"",
                "scheme": "http",
                "server": ("testserver", 80),
                "http_version": "1.1",
            }
        )

        for _ in range(main.RATE_LIMIT_REQUESTS):
            main.enforce_rate_limit(request)

        with self.assertRaises(HTTPException) as raised:
            main.enforce_rate_limit(request)

        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn("Retry-After", raised.exception.headers)


if __name__ == "__main__":
    unittest.main()
