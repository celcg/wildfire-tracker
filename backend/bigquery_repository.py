"""BigQuery persistence boundary for historical wildfire analytics."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Iterable

import config
from historical_models import IngestionBatch


_PROJECT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class BigQueryStorageLimitExceeded(RuntimeError):
    """Raised before writes when the configured free-tier guard is reached."""


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

        sql = f"""
            SELECT detection_id, cluster_id
            FROM `{self._detections_table}`
            WHERE observation_date >= @window_start
              AND detection_id IN UNNEST(@detection_ids)
        """
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
        rows = self._client.query(
            sql,
            job_config=self._query_config(parameters),
            location=config.BIGQUERY_LOCATION,
        ).result()
        return {row.detection_id: row.cluster_id for row in rows}

    def write_batch(self, batch: IngestionBatch) -> None:
        _validate_batch_relationships(batch)
        current_bytes = self.storage_bytes()
        if current_bytes >= config.BIGQUERY_STORAGE_GUARD_BYTES:
            raise BigQueryStorageLimitExceeded(
                "BigQuery storage safety threshold reached"
            )

        sql = f"""
        BEGIN TRANSACTION;

        MERGE `{self._clusters_table}` AS target
        USING (
          SELECT
            JSON_VALUE(item, '$.cluster_id') AS cluster_id,
            TIMESTAMP(JSON_VALUE(item, '$.snapshot_at')) AS snapshot_at,
            DATE(JSON_VALUE(item, '$.snapshot_date')) AS snapshot_date,
            ST_GEOGPOINT(
              CAST(JSON_VALUE(item, '$.center_longitude') AS FLOAT64),
              CAST(JSON_VALUE(item, '$.center_latitude') AS FLOAT64)
            ) AS center,
            ST_GEOGFROMGEOJSON(JSON_VALUE(item, '$.boundary_geojson')) AS boundary,
            ARRAY(
              SELECT JSON_VALUE(member)
              FROM UNNEST(JSON_QUERY_ARRAY(item, '$.member_detection_ids')) AS member
            ) AS member_detection_ids,
            CAST(JSON_VALUE(item, '$.detection_count') AS INT64) AS detection_count,
            CAST(JSON_VALUE(item, '$.total_frp_mw') AS FLOAT64) AS total_frp_mw,
            CAST(JSON_VALUE(item, '$.maximum_frp_mw') AS FLOAT64) AS maximum_frp_mw,
            TIMESTAMP(JSON_VALUE(item, '$.first_detected_at')) AS first_detected_at,
            TIMESTAMP(JSON_VALUE(item, '$.last_detected_at')) AS last_detected_at,
            JSON_VALUE(item, '$.confidence') AS confidence,
            JSON_VALUE(item, '$.trend') AS trend,
            JSON_VALUE(item, '$.severity') AS severity,
            JSON_VALUE(item, '$.status') AS status,
            JSON_VALUE(item, '$.merged_into_cluster_id') AS merged_into_cluster_id,
            JSON_VALUE(item, '$.source_dataset') AS source_dataset
          FROM UNNEST(JSON_QUERY_ARRAY(@clusters_json)) AS item
        ) AS source
          ON target.cluster_id = source.cluster_id
         AND target.snapshot_at = source.snapshot_at
         AND target.snapshot_date = @snapshot_date
        WHEN MATCHED THEN UPDATE SET
          center = source.center,
          boundary = source.boundary,
          member_detection_ids = source.member_detection_ids,
          detection_count = source.detection_count,
          total_frp_mw = source.total_frp_mw,
          maximum_frp_mw = source.maximum_frp_mw,
          first_detected_at = source.first_detected_at,
          last_detected_at = source.last_detected_at,
          confidence = source.confidence,
          trend = source.trend,
          severity = source.severity,
          status = source.status,
          merged_into_cluster_id = source.merged_into_cluster_id
        WHEN NOT MATCHED THEN INSERT (
          cluster_id, snapshot_at, snapshot_date, center, boundary,
          member_detection_ids, detection_count, total_frp_mw, maximum_frp_mw,
          first_detected_at, last_detected_at, confidence, trend, severity,
          status, merged_into_cluster_id, source_dataset
        ) VALUES (
          source.cluster_id, source.snapshot_at, source.snapshot_date,
          source.center, source.boundary, source.member_detection_ids,
          source.detection_count, source.total_frp_mw, source.maximum_frp_mw,
          source.first_detected_at, source.last_detected_at, source.confidence,
          source.trend, source.severity, source.status,
          source.merged_into_cluster_id, source.source_dataset
        );

        MERGE `{self._detections_table}` AS target
        USING (
          SELECT
            JSON_VALUE(item, '$.detection_id') AS detection_id,
            JSON_VALUE(item, '$.cluster_id') AS cluster_id,
            TIMESTAMP(JSON_VALUE(item, '$.cluster_snapshot_at')) AS cluster_snapshot_at,
            TIMESTAMP(JSON_VALUE(item, '$.observed_at')) AS observed_at,
            DATE(JSON_VALUE(item, '$.observation_date')) AS observation_date,
            CAST(JSON_VALUE(item, '$.latitude') AS FLOAT64) AS latitude,
            CAST(JSON_VALUE(item, '$.longitude') AS FLOAT64) AS longitude,
            ST_GEOGPOINT(
              CAST(JSON_VALUE(item, '$.longitude') AS FLOAT64),
              CAST(JSON_VALUE(item, '$.latitude') AS FLOAT64)
            ) AS position,
            JSON_VALUE(item, '$.satellite') AS satellite,
            JSON_VALUE(item, '$.confidence') AS confidence,
            CAST(JSON_VALUE(item, '$.frp_mw') AS FLOAT64) AS frp_mw,
            JSON_VALUE(item, '$.source_dataset') AS source_dataset
          FROM UNNEST(JSON_QUERY_ARRAY(@detections_json)) AS item
        ) AS source
          ON target.detection_id = source.detection_id
         AND target.observation_date >= @window_start
        WHEN MATCHED THEN UPDATE SET
          cluster_id = source.cluster_id,
          cluster_snapshot_at = source.cluster_snapshot_at,
          confidence = source.confidence,
          frp_mw = source.frp_mw,
          last_ingested_at = @ingested_at
        WHEN NOT MATCHED THEN INSERT (
          detection_id, cluster_id, cluster_snapshot_at, observed_at,
          observation_date, latitude, longitude, position, satellite,
          confidence, frp_mw, source_dataset, first_ingested_at,
          last_ingested_at
        ) VALUES (
          source.detection_id, source.cluster_id, source.cluster_snapshot_at,
          source.observed_at, source.observation_date, source.latitude,
          source.longitude, source.position, source.satellite,
          source.confidence, source.frp_mw, source.source_dataset,
          @ingested_at, @ingested_at
        );

        COMMIT TRANSACTION;
        """
        window_start = min(
            record.observation_date for record in batch.detections
        )
        parameters = [
            self._bigquery.ScalarQueryParameter(
                "clusters_json",
                "STRING",
                batch.clusters_json(),
            ),
            self._bigquery.ScalarQueryParameter(
                "detections_json",
                "STRING",
                batch.detections_json(),
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
        self._client.query(
            sql,
            job_config=self._query_config(parameters),
            location=config.BIGQUERY_LOCATION,
        ).result()
