import unittest

from benchmark_detection_loading import (
    benchmark_incident_cache,
    benchmark_window_coordination,
    synthetic_fires,
)


class DetectionLoadingBenchmarkTest(unittest.TestCase):
    def test_synthetic_dataset_is_deterministic_and_contains_no_real_source_data(self):
        first = synthetic_fires(25)
        second = synthetic_fires(25)

        self.assertTrue(first.equals(second))
        self.assertEqual(len(first), 25)
        self.assertEqual(set(first["satellite"]), {"N20"})

    def test_benchmarks_report_comparable_results_without_timing_thresholds(self):
        cache_result = benchmark_incident_cache(count=20, iterations=2)
        coordination_result = benchmark_window_coordination(
            iterations=2,
            delay_seconds=0.005,
        )

        self.assertTrue(cache_result["same_cached_collection"])
        self.assertGreater(cache_result["cold"]["median_ms"], 0)
        self.assertGreater(cache_result["cached"]["median_ms"], 0)
        self.assertGreater(coordination_result["sequential"]["median_ms"], 0)
        self.assertGreater(
            coordination_result["per_window_parallel"]["median_ms"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
