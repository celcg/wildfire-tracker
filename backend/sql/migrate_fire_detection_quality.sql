-- Run once before deploying code that writes per-detection quality metadata.
ALTER TABLE `{{DETECTIONS_TABLE}}`
ALTER COLUMN frp_mw DROP NOT NULL;

ALTER TABLE `{{DETECTIONS_TABLE}}`
ADD COLUMN IF NOT EXISTS quality_flags ARRAY<STRING>;
