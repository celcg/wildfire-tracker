BEGIN TRANSACTION;

MERGE `{{CLUSTERS_TABLE}}` AS target
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

MERGE `{{DETECTIONS_TABLE}}` AS target
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
    ARRAY(
      SELECT JSON_VALUE(flag)
      FROM UNNEST(JSON_QUERY_ARRAY(item, '$.quality_flags')) AS flag
    ) AS quality_flags,
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
  quality_flags = source.quality_flags,
  last_ingested_at = @ingested_at
WHEN NOT MATCHED THEN INSERT (
  detection_id, cluster_id, cluster_snapshot_at, observed_at,
  observation_date, latitude, longitude, position, satellite,
  confidence, frp_mw, quality_flags, source_dataset, first_ingested_at,
  last_ingested_at
) VALUES (
  source.detection_id, source.cluster_id, source.cluster_snapshot_at,
  source.observed_at, source.observation_date, source.latitude,
  source.longitude, source.position, source.satellite,
  source.confidence, source.frp_mw, source.quality_flags, source.source_dataset,
  @ingested_at, @ingested_at
);

COMMIT TRANSACTION;
