CREATE SCHEMA IF NOT EXISTS `{{BIGQUERY_DATASET}}`
OPTIONS(location = "europe-west1");

CREATE TABLE IF NOT EXISTS `{{CLUSTERS_TABLE}}` (
  cluster_id STRING NOT NULL,
  snapshot_at TIMESTAMP NOT NULL,
  snapshot_date DATE NOT NULL,
  center GEOGRAPHY NOT NULL,
  boundary GEOGRAPHY NOT NULL,
  member_detection_ids ARRAY<STRING>,
  detection_count INT64 NOT NULL,
  total_frp_mw FLOAT64 NOT NULL,
  maximum_frp_mw FLOAT64 NOT NULL,
  first_detected_at TIMESTAMP NOT NULL,
  last_detected_at TIMESTAMP NOT NULL,
  confidence STRING NOT NULL,
  trend STRING NOT NULL,
  severity STRING NOT NULL,
  status STRING NOT NULL,
  merged_into_cluster_id STRING,
  source_dataset STRING NOT NULL,
  PRIMARY KEY (cluster_id, snapshot_at) NOT ENFORCED
)
PARTITION BY snapshot_date
CLUSTER BY cluster_id, severity
OPTIONS (
  partition_expiration_days = 365,
  require_partition_filter = TRUE,
  description = "Hourly snapshots of explainable wildfire detection clusters"
);

CREATE TABLE IF NOT EXISTS `{{DETECTIONS_TABLE}}` (
  detection_id STRING NOT NULL,
  cluster_id STRING NOT NULL,
  cluster_snapshot_at TIMESTAMP NOT NULL,
  observed_at TIMESTAMP NOT NULL,
  observation_date DATE NOT NULL,
  latitude FLOAT64 NOT NULL,
  longitude FLOAT64 NOT NULL,
  position GEOGRAPHY NOT NULL,
  satellite STRING NOT NULL,
  confidence STRING NOT NULL,
  frp_mw FLOAT64,
  quality_flags ARRAY<STRING>,
  source_dataset STRING NOT NULL,
  first_ingested_at TIMESTAMP NOT NULL,
  last_ingested_at TIMESTAMP NOT NULL,
  PRIMARY KEY (detection_id) NOT ENFORCED,
  CONSTRAINT detection_cluster_fk
    FOREIGN KEY (cluster_id, cluster_snapshot_at)
    REFERENCES `{{CLUSTERS_TABLE}}`
      (cluster_id, snapshot_at) NOT ENFORCED
)
PARTITION BY observation_date
CLUSTER BY cluster_id, satellite
OPTIONS (
  partition_expiration_days = 365,
  require_partition_filter = TRUE,
  description = "Deduplicated NASA FIRMS detections with their latest cluster snapshot"
);
