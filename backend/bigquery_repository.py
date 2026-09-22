"""BigQuery persistence boundary for historical wildfire analytics."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Iterable

import config
from bigquery_sql import render_sql
from historical_models import IngestionBatch


_PROJECT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class BigQueryStorageLimitExceeded(RuntimeError):
    """Raised before writes when the configured free-tier guard is reached."""


class BigQueryPayloadTooLarge(RuntimeError):
    """Raised before submission when query parameters exceed the safe budget."""


def _validated_identifier(value: str, pattern: re.Pattern[str], label: str) -> str:
    if not pattern.fullmatch(value):
        raise ValueError(f"Invalid BigQuery {label}")
    return value


def _validate_batch_relationships(batch: IngestionBatch) -> None:
    """Enforce the logical keys that BigQuery only records as metadata."""
    cluster_keys = [
        (cluster.cluster_id, cluster.snapshot_at) for cluster in batch.clusters
    ]
    if len(cluster_keys) != len(set(cluster_keys)):
        raise ValueError("Duplicate cluster snapshot key")

    detection_ids = [record.detection_id for record in batch.detections]
    if len(detection_ids) != len(set(detection_ids)):
        raise ValueError("Duplicate detection key")

    available_clusters = set(cluster_keys)
    if any(
        (record.cluster_id, record.cluster_snapshot_at) not in available_clusters
        for record in batch.detections
    ):
        raise ValueError("Historical ingestion contains an orphan cluster reference")


class BigQueryHistoryRepository:
    """Run bounded, parameterized reads and one atomic hourly write."""

    def __init__(self, client: Any | None = None, bigquery_module: Any | None = None):
        if bigquery_module is None:
            from google.cloud import bigquery as bigquery_module

        self._bigquery = bigquery_module
        self._project = _validated_identifier(
            config.BIGQUERY_PROJECT_ID,
            _PROJECT_PATTERN,
            "project",
        )
        self._dataset = _validated_identifier(
            config.BIGQUERY_DATASET,
            _NAME_PATTERN,
            "dataset",
        )
        self._client = client or bigquery_module.Client(
            project=self._project,
            location=config.BIGQUERY_LOCATION,
        )
        prefix = f"{self._project}.{self._dataset}"
        self._detections_table = f"{prefix}.fire_detections"
        self._clusters_table = f"{prefix}.fire_clusters"

    def _query_config(self, parameters: Iterable[Any]):
        return self._bigquery.QueryJobConfig(
            query_parameters=list(parameters),
            maximum_bytes_billed=config.BIGQUERY_MAX_BYTES_BILLED,
            use_query_cache=False,
        )

    def _run(self, sql: str, parameters: Iterable[Any]):
        """Apply the same cost ceiling and regional execution to every query."""
        return self._client.query(
            sql,
            job_config=self._query_config(parameters),
            location=config.BIGQUERY_LOCATION,
        ).result()

    def storage_bytes(self) -> int:
        """Read table metadata without scanning billable table contents."""
        return sum(
            int(self._client.get_table(table).num_bytes or 0)
            for table in (self._detections_table, self._clusters_table)
        )

    def existing_assignments(
        self,
        detection_ids: Iterable[str],
        window_start: date,
    ) -> dict[str, str]:
        keys = sorted(set(detection_ids))
        if not keys:
            return {}

        sql = render_sql(
            "existing_assignments.sql",
            {"DETECTIONS_TABLE": self._detections_table},
        )
        parameters = [
            self._bigquery.ScalarQueryParameter(
                "window_start",
                "DATE",
                window_start,
            ),
            self._bigquery.ArrayQueryParameter(
                "detection_ids",
                "STRING",
                keys,
            ),
        ]
        rows = self._run(sql, parameters)
        return {row.detection_id: row.cluster_id for row in rows}

    def write_batch(self, batch: IngestionBatch) -> None:
        _validate_batch_relationships(batch)
        current_bytes = self.storage_bytes()
        if current_bytes >= config.BIGQUERY_STORAGE_GUARD_BYTES:
            raise BigQueryStorageLimitExceeded(
                "BigQuery storage safety threshold reached"
            )

        clusters_json = batch.clusters_json()
        detections_json = batch.detections_json()
        # Measure the outer JSON representation because BigQuery's 10 MB API
        # limit includes escaping added around string query parameters.
        parameter_bytes = len(
            json.dumps(
                {
                    "clusters_json": clusters_json,
                    "detections_json": detections_json,
                },
                separators=(",", ":"),
            ).encode("utf-8")
        )
        if parameter_bytes > config.BIGQUERY_PAYLOAD_MAX_BYTES:
            raise BigQueryPayloadTooLarge("BigQuery ingestion payload is too large")

        sql = render_sql(
            "history_merge.sql",
            {
                "CLUSTERS_TABLE": self._clusters_table,
                "DETECTIONS_TABLE": self._detections_table,
            },
        )
        window_start = min(
            record.observation_date for record in batch.detections
        )
        parameters = [
            self._bigquery.ScalarQueryParameter(
                "clusters_json",
                "STRING",
                clusters_json,
            ),
            self._bigquery.ScalarQueryParameter(
                "detections_json",
                "STRING",
                detections_json,
            ),
            self._bigquery.ScalarQueryParameter(
                "snapshot_date",
                "DATE",
                batch.snapshot_at.date(),
            ),
            self._bigquery.ScalarQueryParameter(
                "window_start",
                "DATE",
                date.fromisoformat(window_start),
            ),
            self._bigquery.ScalarQueryParameter(
                "ingested_at",
                "TIMESTAMP",
                batch.snapshot_at,
            ),
        ]
        self._run(sql, parameters)
