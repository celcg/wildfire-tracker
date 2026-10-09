import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import h3
import pandas as pd
from shapely.geometry import Point, Polygon, mapping

from wildfire_risk.h3_grid import (
    assign_h3_cells,
    build_h3_grid,
    load_geojson_boundary,
)


class H3GridTest(unittest.TestCase):
    def test_builds_intersecting_cells_with_points_inside_boundary(self):
        boundary = Polygon(
            [(-8.8, 42.0), (-8.4, 42.0), (-8.4, 42.4), (-8.8, 42.4)]
        )

        cells = build_h3_grid(boundary, resolution=5)

        self.assertGreater(len(cells), 0)
        self.assertEqual(
            [cell.h3_cell for cell in cells],
            sorted(cell.h3_cell for cell in cells),
        )
        for cell in cells:
            self.assertEqual(h3.get_resolution(cell.h3_cell), 5)
            self.assertGreater(cell.galicia_area_km2, 0)
            self.assertGreater(cell.galicia_fraction, 0)
            self.assertLessEqual(cell.galicia_fraction, 1.000001)
            self.assertTrue(
                boundary.covers(
                    Point(cell.weather_longitude, cell.weather_latitude)
                )
            )

    def test_keeps_a_tiny_boundary_even_when_polyfill_has_no_center(self):
        boundary = Polygon(
            [
                (-8.600, 42.100),
                (-8.595, 42.100),
                (-8.595, 42.105),
                (-8.600, 42.105),
            ]
        )

        cells = build_h3_grid(
            boundary,
            resolution=5,
            minimum_intersection_km2=0,
        )

        self.assertGreaterEqual(len(cells), 1)

    def test_loads_feature_collection_and_assigns_detection_cells(self):
        polygon = Polygon(
            [(-8.8, 42.0), (-8.4, 42.0), (-8.4, 42.4), (-8.8, 42.4)]
        )
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "boundary.geojson"
            path.write_text(
                json.dumps(
                    {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "properties": {},
                                "geometry": mapping(polygon),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            boundary = load_geojson_boundary(path)

        assigned = assign_h3_cells(
            pd.DataFrame([{"latitude": 42.1, "longitude": -8.6}]),
            resolution=5,
        )

        self.assertTrue(boundary.equals(polygon))
        self.assertEqual(
            assigned.iloc[0]["h3_cell"],
            h3.latlng_to_cell(42.1, -8.6, 5),
        )


if __name__ == "__main__":
    unittest.main()
