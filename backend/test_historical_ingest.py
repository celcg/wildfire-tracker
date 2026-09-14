import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pandas as pd
from fastapi import HTTPException, Request
from google.cloud import bigquery

import config
from bigquery_repository import (
    BigQueryHistoryRepository,
    BigQueryStorageLimitExceeded,
)
from historical_ingest import ingest_fire_history
from historical_models import (
    IngestionBatch,
    build_ingestion_batch,
    detection_id,
    snapshot_hour,
)
from incident_clustering import cluster_fires
from scheduler_auth import enforce_scheduler_auth


AT = datetime(2026, 9, 14, 12, 37, tzinfo=timezone.utc)


def fire(latitude, longitude, time, frp=5, date="2026-09-14"):
    return {
        "latitude": latitude,
        "longitude": longitude,
        "confidence": "n",
        "acq_date": date,
        "acq_time": time,
        "satellite": "N20",
        "frp": frp,
    }


def request_with_authorization(value="Bearer signed-token"):
    return Request(
        {
            "type": "http",
            "headers": [(b"authorization", value.encode("ascii"))],
            "method": "POST",
            "path": "/internal/ingest",
            "query_string": b"",
            "scheme": "https",
            "server": ("testserver", 443),
            "http_version": "1.1",
        }
    )


class HistoricalModelTest(unittest.TestCase):
    def test_detection_id_normalizes_equivalent_acquisition_times(self):
        common = {
            "latitude": 42.1,
            "longitude": -8.6,
            "acq_date": "2026-09-14",
            "acq_time": 900,
            "satellite": "N20",
        }
        numeric = detection_id(**common)
        common["acq_time"] = "0900"
        self.assertEqual(numeric, detection_id(**common))

    def test_snapshot_hour_makes_same_hour_retries_idempotent(self):
        self.assertEqual(
            snapshot_hour(AT),
            datetime(2026, 9, 14, 12, tzinfo=timezone.utc),
        )

    def test_single_detection_always_receives_a_cluster(self):
        fires = pd.DataFrame([fire(42.1, -8.6, 900)])
        incidents = cluster_fires(fires, days=1)

        batch = build_ingestion_batch(fires, incidents, {}, at=AT)

        self.assertEqual(len(batch.detections), 1)
        self.assertEqual(len(batch.clusters), 1)
        self.assertEqual(
            batch.detections[0].cluster_id,
            batch.clusters[0].cluster_id,
        )
        self.assertEqual(batch.clusters[0].detection_count, 1)

    def test_existing_cluster_id_survives_a_new_detection(self):
        first_fires = pd.DataFrame([fire(42.1, -8.6, 900)])
        first_batch = build_ingestion_batch(
            first_fires,
            cluster_fires(first_fires, 1),
            {},
            at=AT,
        )
        existing = {
            first_batch.detections[0].detection_id:
            first_batch.detections[0].cluster_id
        }
        expanded = pd.DataFrame(
            [fire(42.1, -8.6, 900), fire(42.101, -8.601, 1000)]
        )

        next_batch = build_ingestion_batch(
            expanded,
            cluster_fires(expanded, 1),
            existing,
            at=AT.replace(hour=13),
        )

        self.assertEqual(
            next_batch.clusters[0].cluster_id,
            first_batch.clusters[0].cluster_id,
        )

    def test_bridge_detection_merges_clusters_into_earliest_assignment(self):
        fires = pd.DataFrame(
            [
                fire(42.000, -8.600, 900),
                fire(42.015, -8.600, 1000),
                fire(42.030, -8.600, 1100),
            ]
        )
        ids = [
            detection_id(
                latitude=row["latitude"],
                longitude=row["longitude"],
                acq_date=row["acq_date"],
                acq_time=row["acq_time"],
                satellite=row["satellite"],
            )
            for row in fires.to_dict(orient="records")
        ]
        existing = {ids[0]: "cluster-old", ids[2]: "cluster-new"}

        batch = build_ingestion_batch(
            fires,
            cluster_fires(fires, 1),
            existing,
            at=AT,
        )

        active = [cluster for cluster in batch.clusters if cluster.status == "active"]
        merged = [cluster for cluster in batch.clusters if cluster.status == "merged"]
        self.assertEqual(active[0].cluster_id, "cluster-old")
        self.assertEqual(merged[0].cluster_id, "cluster-new")
        self.assertEqual(merged[0].merged_into_cluster_id, "cluster-old")
        self.assertTrue(
            all(record.cluster_id == "cluster-old" for record in batch.detections)
        )

    def test_duplicate_source_observation_is_written_once(self):
        fires = pd.DataFrame([fire(42.1, -8.6, 900)] * 2)
        batch = build_ingestion_batch(
            fires,
            cluster_fires(fires, 1),
            {},
            at=AT,
        )
        self.assertEqual(len(batch.detections), 1)
        self.assertEqual(batch.clusters[0].detection_count, 1)
        self.assertEqual(
            len(json.loads(batch.clusters_json())[0]["member_detection_ids"]),
            1,
        )

    def test_split_components_cannot_reuse_one_snapshot_primary_key(self):
        fires = pd.DataFrame(
            [fire(42.000, -8.600, 900), fire(42.050, -8.600, 1000)]
        )
        ids = [
            detection_id(
                latitude=row["latitude"],
                longitude=row["longitude"],
                acq_date=row["acq_date"],
                acq_time=row["acq_time"],
                satellite=row["satellite"],
            )
            for row in fires.to_dict(orient="records")
        ]

        batch = build_ingestion_batch(
            fires,
            cluster_fires(fires, 1),
            {ids[0]: "cluster-before-split", ids[1]: "cluster-before-split"},
            at=AT,
        )

        keys = [(item.cluster_id, item.snapshot_at) for item in batch.clusters]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("cluster-before-split", {item.cluster_id for item in batch.clusters})


class HistoricalIngestionServiceTest(unittest.TestCase):
    def test_stale_nasa_data_is_never_written(self):
        stale = pd.DataFrame([fire(42.1, -8.6, 900)])
        stale.attrs["data_stale"] = True
        repository = Mock()

        with patch.object(config, "BIGQUERY_ENABLED", True):
            with patch("historical_ingest.fetch_fires", return_value=stale):
                with self.assertRaises(HTTPException) as raised:
                    ingest_fire_history(repository)

        self.assertEqual(raised.exception.status_code, 503)
        repository.write_batch.assert_not_called()

    def test_fresh_data_is_resolved_and_written(self):
        fires = pd.DataFrame([fire(42.1, -8.6, 900)])
        fires.attrs["data_stale"] = False
        repository = Mock()
        repository.existing_assignments.return_value = {}

        with patch.object(config, "BIGQUERY_ENABLED", True):
            with patch("historical_ingest.fetch_fires", return_value=fires):
                result = ingest_fire_history(repository)

        self.assertEqual(result.status, "ingested")
        self.assertEqual(result.detections_processed, 1)
        repository.write_batch.assert_called_once()

    def test_storage_guard_returns_non_retryable_capacity_error(self):
        fires = pd.DataFrame([fire(42.1, -8.6, 900)])
        fires.attrs["data_stale"] = False
        repository = Mock()
        repository.existing_assignments.return_value = {}
        repository.write_batch.side_effect = BigQueryStorageLimitExceeded()

        with patch.object(config, "BIGQUERY_ENABLED", True):
            with patch("historical_ingest.fetch_fires", return_value=fires):
                with self.assertRaises(HTTPException) as raised:
                    ingest_fire_history(repository)

        self.assertEqual(raised.exception.status_code, 507)


class SchedulerAuthenticationTest(unittest.TestCase):
    def test_expected_verified_service_account_is_accepted(self):
        claims = {"email": "scheduler@example.test", "email_verified": True}
        with patch.object(config, "SCHEDULER_AUDIENCE", "https://api.test"):
            with patch.object(
                config,
                "SCHEDULER_SERVICE_ACCOUNT",
                "scheduler@example.test",
            ):
                with patch("scheduler_auth._verify_google_token", return_value=claims):
                    enforce_scheduler_auth(request_with_authorization())

    def test_wrong_service_account_is_rejected_without_echoing_token(self):
        claims = {"email": "attacker@example.test", "email_verified": True}
        with patch.object(config, "SCHEDULER_AUDIENCE", "https://api.test"):
            with patch.object(
                config,
                "SCHEDULER_SERVICE_ACCOUNT",
                "scheduler@example.test",
            ):
                with patch("scheduler_auth._verify_google_token", return_value=claims):
                    with self.assertRaises(HTTPException) as raised:
                        enforce_scheduler_auth(request_with_authorization("Bearer secret"))

        self.assertEqual(raised.exception.status_code, 401)
        self.assertNotIn("secret", raised.exception.detail)


class BigQueryRepositoryTest(unittest.TestCase):
    def test_storage_guard_prevents_query_submission(self):
        module = Mock()
        client = Mock()
        client.get_table.return_value.num_bytes = 5 * 1024**3
        repository = BigQueryHistoryRepository(client, module)
        fires = pd.DataFrame([fire(42.1, -8.6, 900)])
        batch = build_ingestion_batch(
            fires,
            cluster_fires(fires, 1),
            {},
            at=AT,
        )

        with self.assertRaises(BigQueryStorageLimitExceeded):
            repository.write_batch(batch)

        client.query.assert_not_called()

    def test_write_uses_parameters_and_one_transaction(self):
        fires = pd.DataFrame([fire(42.1, -8.6, 900)])
        batch = build_ingestion_batch(
            fires,
            cluster_fires(fires, 1),
            {},
            at=AT,
        )
        client = Mock()
        client.get_table.return_value.num_bytes = 0
        client.query.return_value.result.return_value = []
        repository = BigQueryHistoryRepository(client, bigquery)

        repository.write_batch(batch)

        sql = client.query.call_args.args[0]
        job_config = client.query.call_args.kwargs["job_config"]
        self.assertIn("BEGIN TRANSACTION", sql)
        self.assertIn("COMMIT TRANSACTION", sql)
        self.assertNotIn("CREATE TEMP TABLE", sql)
        self.assertIn("AS FLOAT64", sql)
        self.assertNotIn("FLOAT64(JSON_VALUE", sql)
        self.assertNotIn(batch.detections[0].detection_id, sql)
        self.assertEqual(job_config.maximum_bytes_billed, 50 * 1024 * 1024)
        self.assertEqual(len(job_config.query_parameters), 5)

    def test_orphan_relationship_is_rejected_before_bigquery(self):
        fires = pd.DataFrame([fire(42.1, -8.6, 900)])
        batch = build_ingestion_batch(
            fires,
            cluster_fires(fires, 1),
            {},
            at=AT,
        )
        invalid_detection = replace(batch.detections[0], cluster_id="missing")
        invalid_batch = IngestionBatch(
            snapshot_at=batch.snapshot_at,
            detections=(invalid_detection,),
            clusters=batch.clusters,
            merged_cluster_ids=batch.merged_cluster_ids,
        )
        client = Mock()
        repository = BigQueryHistoryRepository(client, bigquery)

        with self.assertRaisesRegex(ValueError, "orphan cluster"):
            repository.write_batch(invalid_batch)

        client.get_table.assert_not_called()
        client.query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
