import unittest
from unittest.mock import patch

import pandas as pd

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
    @patch("main.fetch_fires", return_value=SAMPLE_FIRES)
    def test_fires_passes_days_to_data_source(self, fetch_fires):
        response = main.fires(days=3)

        fetch_fires.assert_called_once_with(3)
        self.assertEqual(len(response), 2)

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


if __name__ == "__main__":
    unittest.main()
