import unittest
from unittest.mock import patch

import pandas as pd

import main
from incident_clustering import cluster_fires, haversine_km


def fire(
    latitude,
    longitude,
    date,
    time,
    frp,
    confidence="n",
    satellite="N20",
):
    return {
        "latitude": latitude,
        "longitude": longitude,
        "acq_date": date,
        "acq_time": time,
        "frp": frp,
        "confidence": confidence,
        "satellite": satellite,
    }


class IncidentClusteringTest(unittest.TestCase):
    def test_haversine_distance_is_geographically_plausible(self):
        # Madrid to Toledo is approximately 67 km in a straight line.
        distance = haversine_km(40.4168, -3.7038, 39.8628, -4.0273)
        self.assertAlmostEqual(distance, 67, delta=2)

    def test_nearby_detections_within_time_window_form_one_incident(self):
        fires = pd.DataFrame(
            [
                fire(42.100, -8.600, "2026-09-10", 900, 8),
                fire(42.115, -8.590, "2026-09-10", 1100, 12, "h"),
            ]
        )

        result = cluster_fires(fires, days=1)

        self.assertEqual(result.incident_count, 1)
        self.assertEqual(result.incidents[0].detection_count, 2)
        self.assertEqual(result.incidents[0].total_frp_mw, 20)
        self.assertEqual(result.incidents[0].severity, "moderate")

    def test_spatially_distant_detections_remain_separate(self):
        fires = pd.DataFrame(
            [
                fire(40.4168, -3.7038, "2026-09-10", 900, 5),
                fire(41.3874, 2.1686, "2026-09-10", 930, 5),
            ]
        )

        result = cluster_fires(fires, days=1)

        self.assertEqual(result.incident_count, 2)

    def test_temporally_distant_detections_remain_separate(self):
        fires = pd.DataFrame(
            [
                fire(42.100, -8.600, "2026-09-10", 100, 5),
                fire(42.101, -8.601, "2026-09-10", 1400, 5),
            ]
        )

        result = cluster_fires(fires, days=1)

        self.assertEqual(result.incident_count, 2)

    def test_connected_points_form_a_cluster_transitively(self):
        fires = pd.DataFrame(
            [
                fire(42.00, -8.60, "2026-09-10", 900, 5),
                fire(42.015, -8.60, "2026-09-10", 1000, 5),
                fire(42.030, -8.60, "2026-09-10", 1100, 5),
            ]
        )

        result = cluster_fires(fires, days=1)

        self.assertEqual(result.incident_count, 1)
        self.assertEqual(result.incidents[0].detection_count, 3)

    def test_detections_more_than_two_kilometres_apart_remain_separate(self):
        fires = pd.DataFrame(
            [
                fire(42.000, -8.600, "2026-09-10", 900, 5),
                fire(42.020, -8.600, "2026-09-10", 930, 5),
            ]
        )

        result = cluster_fires(fires, days=1)

        self.assertEqual(result.incident_count, 2)

    def test_response_preserves_original_valid_detections(self):
        fires = pd.DataFrame(
            [
                fire(42.100, -8.600, "2026-09-10", 900, 8),
                fire(42.110, -8.590, "2026-09-10", 930, 12, "h"),
            ]
        )

        result = cluster_fires(fires, days=1)

        detections = result.incidents[0].detections
        self.assertEqual(len(detections), 2)
        self.assertEqual(detections[1].confidence, "h")
        self.assertEqual(detections[0].acq_time, "0900")

    def test_every_incident_has_a_real_observation_envelope(self):
        fires = pd.DataFrame(
            [fire(42.100, -8.600, "2026-09-10", 900, 8)]
        )

        incident = cluster_fires(fires, days=1).incidents[0]

        self.assertGreaterEqual(len(incident.boundary), 8)
        self.assertTrue(
            any(point.latitude != 42.100 for point in incident.boundary)
        )

    def test_incident_id_does_not_depend_on_input_order(self):
        rows = [
            fire(42.100, -8.600, "2026-09-10", 900, 5),
            fire(42.101, -8.601, "2026-09-10", 1000, 8),
        ]

        first = cluster_fires(pd.DataFrame(rows), days=1)
        second = cluster_fires(pd.DataFrame(reversed(rows)), days=1)

        self.assertEqual(first.incidents[0].id, second.incidents[0].id)

    def test_simultaneous_detections_have_stable_trend(self):
        fires = pd.DataFrame(
            [
                fire(42.100, -8.600, "2026-09-10", 900, 2),
                fire(42.101, -8.601, "2026-09-10", 900, 5),
                fire(42.102, -8.602, "2026-09-10", 900, 20),
            ]
        )

        incident = cluster_fires(fires, days=1).incidents[0]

        self.assertEqual(incident.duration_hours, 0)
        self.assertEqual(incident.trend, "stable")

    def test_missing_frp_remains_visible_as_low_intensity(self):
        fires = pd.DataFrame(
            [fire(42.100, -8.600, "2026-09-10", 900, None)]
        )

        incident = cluster_fires(fires, days=1).incidents[0]

        self.assertEqual(incident.total_frp_mw, 0)
        self.assertEqual(incident.severity, "low")

    @patch("main.fetch_fires")
    def test_incidents_endpoint_uses_requested_window(self, fetch_fires):
        fetch_fires.return_value = pd.DataFrame(
            [fire(42.100, -8.600, "2026-09-10", 900, 5)]
        )

        response = main.incidents(days=3)

        fetch_fires.assert_called_once_with(3, force_refresh=False)
        self.assertEqual(response.days, 3)
        self.assertEqual(response.incident_count, 1)

    @patch("main.fetch_fires")
    def test_incident_refresh_bypasses_fire_cache(self, fetch_fires):
        fetch_fires.return_value = pd.DataFrame(
            [fire(42.100, -8.600, "2026-09-10", 900, 5)]
        )

        main.incidents(days=1, refresh=True)

        fetch_fires.assert_called_once_with(1, force_refresh=True)


if __name__ == "__main__":
    unittest.main()
