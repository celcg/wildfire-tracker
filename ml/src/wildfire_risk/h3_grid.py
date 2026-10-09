"""Build H3 cells intersecting a supplied Galicia boundary."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import h3
import pandas as pd
from pyproj import Transformer
from shapely import transform
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


WGS84_TO_UTM29 = Transformer.from_crs(4326, 25829, always_xy=True)
UTM29_TO_WGS84 = Transformer.from_crs(25829, 4326, always_xy=True)


@dataclass(frozen=True)
class GridCell:
    h3_cell: str
    h3_resolution: int
    cell_area_km2: float
    galicia_area_km2: float
    galicia_fraction: float
    weather_latitude: float
    weather_longitude: float
    geometry: Polygon
    clipped_geometry: BaseGeometry


def load_geojson_boundary(path: str | Path) -> Polygon | MultiPolygon:
    with Path(path).open(encoding="utf-8") as source:
        document = json.load(source)

    if document.get("type") == "FeatureCollection":
        geometries = [
            shape(feature["geometry"])
            for feature in document.get("features", [])
            if feature.get("geometry")
        ]
        boundary = unary_union(geometries)
    elif document.get("type") == "Feature":
        boundary = shape(document["geometry"])
    else:
        boundary = shape(document)

    if (
        boundary.is_empty
        or not boundary.is_valid
        or not isinstance(boundary, (Polygon, MultiPolygon))
    ):
        raise ValueError("Boundary must be a valid Polygon or MultiPolygon")
    return boundary


def _cell_polygon(cell: str) -> Polygon:
    return Polygon(
        [(longitude, latitude) for latitude, longitude in h3.cell_to_boundary(cell)]
    )


def build_h3_grid(
    boundary: Polygon | MultiPolygon,
    *,
    resolution: int = 5,
    minimum_intersection_km2: float = 0.001,
) -> list[GridCell]:
    if (
        boundary.is_empty
        or not boundary.is_valid
        or not isinstance(boundary, (Polygon, MultiPolygon))
    ):
        raise ValueError("Boundary must be a valid Polygon or MultiPolygon")
    if not 0 <= resolution <= 15:
        raise ValueError("H3 resolution must be between 0 and 15")
    if minimum_intersection_km2 < 0:
        raise ValueError("Minimum intersection area cannot be negative")

    seeds = set(h3.geo_to_cells(mapping(boundary), resolution))
    if not seeds:
        seeds.add(h3.latlng_to_cell(boundary.centroid.y, boundary.centroid.x, resolution))
    candidates = set(seeds)
    for cell in seeds:
        candidates.update(h3.grid_disk(cell, 1))

    projected_boundary = transform(
        boundary, WGS84_TO_UTM29.transform, interleaved=False
    )
    cells: list[GridCell] = []
    for cell in candidates:
        polygon = _cell_polygon(cell)
        projected_polygon = transform(
            polygon, WGS84_TO_UTM29.transform, interleaved=False
        )
        clipped = projected_polygon.intersection(projected_boundary)
        galicia_area_km2 = clipped.area / 1_000_000
        if galicia_area_km2 <= minimum_intersection_km2:
            continue

        cell_area_km2 = projected_polygon.area / 1_000_000
        representative = transform(
            clipped.representative_point(),
            UTM29_TO_WGS84.transform,
            interleaved=False,
        )
        cells.append(
            GridCell(
                h3_cell=cell,
                h3_resolution=resolution,
                cell_area_km2=cell_area_km2,
                galicia_area_km2=galicia_area_km2,
                galicia_fraction=galicia_area_km2 / cell_area_km2,
                weather_latitude=representative.y,
                weather_longitude=representative.x,
                geometry=polygon,
                clipped_geometry=transform(
                    clipped, UTM29_TO_WGS84.transform, interleaved=False
                ),
            )
        )
    return sorted(cells, key=lambda cell: cell.h3_cell)


def assign_h3_cells(
    detections: pd.DataFrame,
    *,
    resolution: int,
) -> pd.DataFrame:
    required = {"latitude", "longitude"}
    missing = required - set(detections.columns)
    if missing:
        raise ValueError(f"Detections are missing columns: {sorted(missing)}")

    assigned = detections.copy()
    assigned["h3_cell"] = [
        h3.latlng_to_cell(float(latitude), float(longitude), resolution)
        for latitude, longitude in assigned[["latitude", "longitude"]].itertuples(
            index=False, name=None
        )
    ]
    return assigned
