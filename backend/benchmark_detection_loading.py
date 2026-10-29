"""Reproducible local benchmarks for the implemented request optimizations."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from math import ceil
from statistics import median
from time import perf_counter, sleep
from unittest.mock import patch

import pandas as pd

import config
import fire_data
import incident_data
from fire_data import FIRE_SNAPSHOT_ATTR


def synthetic_fires(count: int, *, current_date: bool = False) -> pd.DataFrame:
    """Create deterministic non-production detections across twenty clusters."""
    date = pd.Timestamp.now(tz="UTC").date().isoformat() if current_date else "2026-01-01"
    rows = []
    for index in range(count):
        cluster = index % 20
        member = index // 20
        if current_date:
            latitude = 42.0 + (index % 5) * 0.001
            longitude = -8.0 + (index // 5) * 0.001
        else:
            latitude = 36.5 + (cluster // 5) * 1.5 + (member % 5) * 0.001
            longitude = -8.5 + (cluster % 5) * 2.0 + (member % 7) * 0.001
        rows.append(
            {
                "latitude": latitude,
                "longitude": longitude,
                "confidence": "n",
                "acq_date": date,
                "acq_time": (member % 24) * 100,
                "satellite": "N20",
                "frp": 5.0 + (index % 10),
            }
        )
    return pd.DataFrame(rows)


def _time_ms(operation) -> float:
    started_at = perf_counter()
    operation()
    return (perf_counter() - started_at) * 1000


def _summary(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)
    p95_index = max(0, ceil(0.95 * len(ordered)) - 1)
    return {
        "median_ms": round(median(ordered), 3),
        "p95_ms": round(ordered[p95_index], 3),
    }


def benchmark_incident_cache(count: int, iterations: int) -> dict:
    fires = synthetic_fires(count)
    cold_samples = []
    cached_samples = []
    original_disabled = incident_data.logger.disabled
    incident_data.logger.disabled = True
    try:
        for snapshot_id in range(1, iterations + 1):
            incident_data.clear_incident_cache()
            fires.attrs[FIRE_SNAPSHOT_ATTR] = snapshot_id
            cold_samples.append(
                _time_ms(lambda: incident_data.derive_incidents(fires, days=1))
            )

        incident_data.clear_incident_cache()
        fires.attrs[FIRE_SNAPSHOT_ATTR] = iterations + 1
        expected = incident_data.derive_incidents(fires, days=1)
        for _ in range(iterations):
            cached_samples.append(
                _time_ms(lambda: incident_data.derive_incidents(fires, days=1))
            )
        cached = incident_data.derive_incidents(fires, days=1)
    finally:
        incident_data.logger.disabled = original_disabled

    cold = _summary(cold_samples)
    warm = _summary(cached_samples)
    return {
        "synthetic_detection_count": count,
        "iterations": iterations,
        "cold": cold,
        "cached": warm,
        "median_speedup": round(cold["median_ms"] / max(warm["median_ms"], 0.001), 2),
        "same_cached_collection": cached is expected,
    }


def benchmark_window_coordination(iterations: int, delay_seconds: float) -> dict:
    source = synthetic_fires(20, current_date=True)

    def delayed_source(_url):
        sleep(delay_seconds)
        return source

    def sequential():
        fire_data.clear_fire_cache()
        fire_data.fetch_fires(1)
        fire_data.fetch_fires(3)

    def parallel():
        fire_data.clear_fire_cache()
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(fire_data.fetch_fires, (1, 3)))

    sequential_samples = []
    parallel_samples = []
    with patch.object(config, "NASA_KEY", "benchmark-key"):
        with patch("fire_data.fetch_nasa_csv", side_effect=delayed_source):
            with patch("fire_data.log_event"):
                for _ in range(iterations):
                    sequential_samples.append(_time_ms(sequential))
                    parallel_samples.append(_time_ms(parallel))

    sequential_result = _summary(sequential_samples)
    parallel_result = _summary(parallel_samples)
    return {
        "simulated_nasa_delay_ms": round(delay_seconds * 1000, 1),
        "iterations": iterations,
        "sequential": sequential_result,
        "per_window_parallel": parallel_result,
        "median_speedup": round(
            sequential_result["median_ms"]
            / max(parallel_result["median_ms"], 0.001),
            2,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=400)
    parser.add_argument("--iterations", type=int, default=7)
    args = parser.parse_args()
    if args.count < 1 or args.iterations < 2:
        parser.error("count must be positive and iterations must be at least 2")

    print(
        json.dumps(
            {
                "incident_cache": benchmark_incident_cache(
                    args.count,
                    args.iterations,
                ),
                "window_coordination": benchmark_window_coordination(
                    args.iterations,
                    delay_seconds=0.05,
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
