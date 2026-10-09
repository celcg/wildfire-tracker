"""Validate the pinned official Galicia boundary."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tomllib

from shapely import transform

from .h3_grid import WGS84_TO_UTM29, load_geojson_boundary
from .manifests import file_sha256


@dataclass(frozen=True)
class BoundarySource:
    provider: str
    dataset: str
    version: str
    nuts_id: str
    level: int
    url: str
    license_url: str
    copyright_notice: str
    filename: str
    sha256: str


def load_boundary_source(path: str | Path) -> BoundarySource:
    with Path(path).open("rb") as source:
        values = tomllib.load(source).get("galicia_boundary")
    if not isinstance(values, dict):
        raise ValueError("Missing [galicia_boundary] source configuration")
    try:
        return BoundarySource(**values)
    except TypeError as error:
        raise ValueError("Invalid Galicia boundary source configuration") from error


def validate_boundary_file(
    path: str | Path,
    source: BoundarySource,
) -> dict[str, object]:
    boundary_path = Path(path)
    actual_sha256 = file_sha256(boundary_path)
    if actual_sha256 != source.sha256.lower():
        raise ValueError(
            f"Boundary SHA-256 mismatch: expected {source.sha256.lower()}, "
            f"got {actual_sha256}"
        )

    with boundary_path.open(encoding="utf-8") as input_file:
        document = json.load(input_file)
    features = document.get("features", [])
    if document.get("type") != "FeatureCollection" or len(features) != 1:
        raise ValueError("Boundary must contain exactly one GeoJSON feature")

    properties = features[0].get("properties", {})
    if properties.get("NUTS_ID") != source.nuts_id:
        raise ValueError("Boundary NUTS_ID does not match source configuration")
    if int(properties.get("LEVL_CODE", -1)) != source.level:
        raise ValueError("Boundary level does not match source configuration")
    if properties.get("NUTS_NAME") != "Galicia":
        raise ValueError("Boundary feature is not Galicia")

    boundary = load_geojson_boundary(boundary_path)
    projected = transform(
        boundary,
        WGS84_TO_UTM29.transform,
        interleaved=False,
    )
    return {
        "provider": source.provider,
        "dataset": source.dataset,
        "version": source.version,
        "nuts_id": source.nuts_id,
        "filename": boundary_path.name,
        "sha256": actual_sha256,
        "geometry_type": boundary.geom_type,
        "bounds": list(boundary.bounds),
        "area_km2": projected.area / 1_000_000,
    }
