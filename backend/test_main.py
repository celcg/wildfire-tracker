import unittest
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from unittest.mock import patch

import pandas as pd
from fastapi import HTTPException, Request, Response

import main
import config
import fire_data
from rate_limit import rate_limiter


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
        # Reset process-local adapters so every test starts from a clean boundary.
        fire_data.clear_fire_cache()
        rate_limiter.reset()

    @patch("main.fetch_fires", return_value=SAMPLE_FIRES)
    def test_fires_passes_days_to_data_source(self, fetch_fires):
        response = main.fires(days=3)

        fetch_fires.assert_called_once_with(3, force_refresh=False)
        self.assertEqual(len(response), 2)

    @patch("main.fetch_fires")
    def test_fires_exposes_stale_cache_metadata(self, fetch_fires):
        stale_fires = SAMPLE_FIRES.copy()
        stale_fires.attrs["data_stale"] = True
        stale_fires.attrs["data_age_seconds"] = 10_800
        fetch_fires.return_value = stale_fires
        response = Response()

        main.fires(days=1, response=response)

        self.assertEqual(response.headers["X-Data-Stale"], "true")
        self.assertEqual(response.headers["X-Data-Age-Seconds"], "10800")

    @patch("main.fetch_fires", return_value=SAMPLE_FIRES)
    def test_manual_refresh_requests_a_controlled_server_refresh(self, fetch_fires):
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

    @patch("fire_data.pd.read_csv", side_effect=RuntimeError("upstream failure"))
    def test_upstream_errors_do_not_expose_nasa_key(self, _read_csv):
        with patch.object(config, "NASA_KEY", "test-secret-that-must-not-leak"):
            with self.assertRaises(HTTPException) as raised:
                fire_data.fetch_fires(days=1)

        self.assertEqual(raised.exception.status_code, 502)
        self.assertNotIn("test-secret", raised.exception.detail)

    def test_server_cache_avoids_repeated_nasa_requests(self):
        with patch.object(config, "NASA_KEY", "test-key"):
            with patch("fire_data.pd.read_csv", return_value=SAMPLE_FIRES) as read_csv:
                with patch("fire_data.log_event") as logged_event:
                    first = fire_data.fetch_fires(days=1)
                    second = fire_data.fetch_fires(days=1)

        read_csv.assert_called_once()
        self.assertEqual(len(first), len(second))
        events = [call.args[2] for call in logged_event.call_args_list]
        self.assertIn("cache.miss", events)
        self.assertIn("nasa.fetch_succeeded", events)
        self.assertIn("cache.hit", events)

    def test_manual_refresh_respects_nasa_refresh_interval(self):
        with patch.object(config, "NASA_KEY", "test-key"):
            with patch("fire_data.pd.read_csv", return_value=SAMPLE_FIRES) as read_csv:
                fire_data.fetch_fires(days=1)
                fire_data.fetch_fires(days=1, force_refresh=True)

        read_csv.assert_called_once()

    def test_concurrent_refreshes_share_one_nasa_request(self):
        def delayed_response(_url):
            sleep(0.05)
            return SAMPLE_FIRES

        with patch.object(config, "NASA_KEY", "test-key"):
            with patch("fire_data.pd.read_csv", side_effect=delayed_response) as read_csv:
                with ThreadPoolExecutor(max_workers=6) as executor:
                    results = list(
                        executor.map(
                            lambda _index: fire_data.fetch_fires(
                                days=1,
                                force_refresh=True,
                            ),
                            range(6),
                        )
                    )

        read_csv.assert_called_once()
        self.assertTrue(all(len(result) == len(SAMPLE_FIRES) for result in results))

    def test_nasa_data_can_refresh_after_one_hour(self):
        with patch.object(config, "NASA_KEY", "test-key"):
            with patch("fire_data.monotonic", side_effect=[0, 0, 3600, 3600]):
                with patch("fire_data.pd.read_csv", return_value=SAMPLE_FIRES) as read_csv:
                    fire_data.fetch_fires(days=1)
                    fire_data.fetch_fires(days=1)

        self.assertEqual(read_csv.call_count, 2)

    def test_expired_data_is_returned_when_nasa_is_unavailable(self):
        with patch.object(config, "NASA_KEY", "test-key"):
            with patch(
                "fire_data.monotonic",
                side_effect=[0, 0, 3600, 3600, 3601, 3601],
            ):
                with patch(
                    "fire_data.pd.read_csv",
                    side_effect=[SAMPLE_FIRES, RuntimeError("NASA unavailable")],
                ) as read_csv:
                    fire_data.fetch_fires(days=1)
                    stale_fires = fire_data.fetch_fires(days=1)
                    repeated_stale_fires = fire_data.fetch_fires(days=1)

        self.assertEqual(read_csv.call_count, 2)
        self.assertEqual(len(stale_fires), len(SAMPLE_FIRES))
        self.assertTrue(stale_fires.attrs["data_stale"])
        self.assertGreaterEqual(stale_fires.attrs["data_age_seconds"], 0)
        self.assertTrue(repeated_stale_fires.attrs["data_stale"])

    def test_empty_cache_retries_nasa_after_initial_backoff(self):
        with patch.object(config, "NASA_KEY", "test-key"):
            with patch.object(
                config,
                "NASA_BACKOFF_INITIAL_SECONDS",
                60,
                create=True,
            ):
                with patch.object(
                    config,
                    "NASA_BACKOFF_MAX_SECONDS",
                    15 * 60,
                    create=True,
                ):
                    with patch(
                        "fire_data.monotonic",
                        side_effect=[0, 0, 30, 30, 60, 60],
                    ):
                        with patch(
                            "fire_data.pd.read_csv",
                            side_effect=RuntimeError("NASA unavailable"),
                        ) as read_csv:
                            with self.assertRaises(HTTPException) as first:
                                fire_data.fetch_fires(days=1)
                            with self.assertRaises(HTTPException) as throttled:
                                fire_data.fetch_fires(days=1)
                            with self.assertRaises(HTTPException) as retried:
                                fire_data.fetch_fires(days=1)

        self.assertEqual(first.exception.status_code, 502)
        self.assertEqual(throttled.exception.status_code, 503)
        self.assertEqual(throttled.exception.headers["Retry-After"], "31")
        self.assertEqual(retried.exception.status_code, 502)
        self.assertEqual(retried.exception.headers["Retry-After"], "120")
        self.assertEqual(read_csv.call_count, 2)

    def test_empty_cache_backoff_doubles_until_the_configured_cap(self):
        with patch.object(config, "NASA_KEY", "test-key"):
            with patch.object(config, "NASA_BACKOFF_INITIAL_SECONDS", 10):
                with patch.object(config, "NASA_BACKOFF_MAX_SECONDS", 25):
                    with patch(
                        "fire_data.monotonic",
                        side_effect=[0, 0, 10, 10, 30, 30, 55, 55],
                    ):
                        with patch(
                            "fire_data.pd.read_csv",
                            side_effect=RuntimeError("NASA unavailable"),
                        ) as read_csv:
                            retry_delays = []
                            for _attempt in range(4):
                                with self.assertRaises(HTTPException) as failure:
                                    fire_data.fetch_fires(days=1)
                                retry_delays.append(
                                    int(failure.exception.headers["Retry-After"])
                                )

        self.assertEqual(retry_delays, [10, 20, 25, 25])
        self.assertEqual(read_csv.call_count, 4)

    def test_successful_cold_retry_resets_failure_backoff(self):
        with patch.object(config, "NASA_KEY", "test-key"):
            with patch("fire_data.monotonic", side_effect=[0, 0, 60, 60]):
                with patch(
                    "fire_data.pd.read_csv",
                    side_effect=[RuntimeError("NASA unavailable"), SAMPLE_FIRES],
                ) as read_csv:
                    with self.assertRaises(HTTPException):
                        fire_data.fetch_fires(days=1)
                    recovered = fire_data.fetch_fires(days=1)

        self.assertEqual(read_csv.call_count, 2)
        self.assertEqual(len(recovered), len(SAMPLE_FIRES))
        self.assertNotIn(1, fire_data._nasa_failure_backoff)

    def test_rate_limit_rejects_the_eleventh_request(self):
        request = Request(
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

        with patch("rate_limit.log_event") as logged_event:
            for _ in range(config.RATE_LIMIT_REQUESTS):
                main.enforce_rate_limit(request)

            with self.assertRaises(HTTPException) as raised:
                main.enforce_rate_limit(request)

        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn("Retry-After", raised.exception.headers)
        self.assertEqual(logged_event.call_args.args[2], "rate_limit.rejected")

    def test_rate_limit_uses_transport_host_not_source_port(self):
        def request_from(host: str, port: int) -> Request:
            return Request(
                {
                    "type": "http",
                    "client": (host, port),
                    "headers": [],
                    "method": "GET",
                    "path": "/fires",
                    "query_string": b"",
                    "scheme": "http",
                    "server": ("testserver", 80),
                    "http_version": "1.1",
                }
            )

        for port in range(config.RATE_LIMIT_REQUESTS):
            main.enforce_rate_limit(request_from("192.0.2.1", 10_000 + port))

        with self.assertRaises(HTTPException):
            main.enforce_rate_limit(request_from("192.0.2.1", 20_000))

        # A different observed host receives an independent bucket.
        main.enforce_rate_limit(request_from("198.51.100.8", 20_000))


if __name__ == "__main__":
    unittest.main()
