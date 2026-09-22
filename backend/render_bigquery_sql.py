"""Render reviewed BigQuery DDL for the configured project and dataset."""

from __future__ import annotations

import argparse

import config
from bigquery_sql import render_sql


SUPPORTED_RESOURCES = {
    "create_bigquery_schema.sql": ("BIGQUERY_DATASET", "CLUSTERS_TABLE", "DETECTIONS_TABLE"),
    "migrate_fire_detection_quality.sql": ("DETECTIONS_TABLE",),
}


def rendered_resource(filename: str) -> str:
    project = config.BIGQUERY_PROJECT_ID
    dataset = config.BIGQUERY_DATASET
    prefix = f"{project}.{dataset}"
    available = {
        "BIGQUERY_DATASET": prefix,
        "CLUSTERS_TABLE": f"{prefix}.fire_clusters",
        "DETECTIONS_TABLE": f"{prefix}.fire_detections",
    }
    return render_sql(
        filename,
        {token: available[token] for token in SUPPORTED_RESOURCES[filename]},
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a BigQuery schema resource using validated identifiers.",
    )
    parser.add_argument("filename", choices=sorted(SUPPORTED_RESOURCES))
    arguments = parser.parse_args()
    print(rendered_resource(arguments.filename), end="")


if __name__ == "__main__":
    main()
