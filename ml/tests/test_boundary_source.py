import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from shapely.geometry import Polygon, mapping

from wildfire_risk.boundary_source import (
    BoundarySource,
    load_boundary_source,
    validate_boundary_file,
)
from wildfire_risk.manifests import file_sha256


class BoundarySourceTest(unittest.TestCase):
    def test_loads_source_and_validates_identity_hash_and_geometry(self):
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            boundary_path = directory / "galicia.geojson"
            boundary_path.write_text(
                json.dumps(
                    {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "properties": {
                                    "NUTS_ID": "ES11",
                                    "NUTS_NAME": "Galicia",
                                    "LEVL_CODE": 2,
                                },
                                "geometry": mapping(
                                    Polygon(
                                        [
                                            (-8.8, 42.0),
                                            (-8.4, 42.0),
                                            (-8.4, 42.4),
                                            (-8.8, 42.4),
                                        ]
                                    )
                                ),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            config_path = directory / "sources.toml"
            config_path.write_text(
                """
[galicia_boundary]
provider = "test"
dataset = "test boundary"
version = "2024"
nuts_id = "ES11"
level = 2
url = "https://example.test/galicia.geojson"
license_url = "https://example.test/license"
copyright_notice = "test attribution"
filename = "galicia.geojson"
sha256 = "{sha256}"
""".strip().format(sha256=file_sha256(boundary_path)),
                encoding="utf-8",
            )

            report = validate_boundary_file(
                boundary_path,
                load_boundary_source(config_path),
            )

        self.assertEqual(report["nuts_id"], "ES11")
        self.assertEqual(report["geometry_type"], "Polygon")
        self.assertGreater(report["area_km2"], 0)

    def test_rejects_a_changed_boundary_file(self):
        with TemporaryDirectory() as temporary_directory:
            boundary_path = Path(temporary_directory) / "galicia.geojson"
            boundary_path.write_text("{}", encoding="utf-8")
            source = BoundarySource(
                provider="test",
                dataset="test",
                version="2024",
                nuts_id="ES11",
                level=2,
                url="https://example.test/galicia.geojson",
                license_url="https://example.test/license",
                copyright_notice="test attribution",
                filename="galicia.geojson",
                sha256="0" * 64,
            )

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                validate_boundary_file(boundary_path, source)


if __name__ == "__main__":
    unittest.main()
