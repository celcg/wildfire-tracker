SELECT detection_id, cluster_id
FROM `{{DETECTIONS_TABLE}}`
WHERE observation_date >= @window_start
  AND detection_id IN UNNEST(@detection_ids)
