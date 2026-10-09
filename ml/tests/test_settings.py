from datetime import date
from pathlib import Path
import unittest

from wildfire_risk.settings import load_settings


CONFIG = Path(__file__).parents[1] / "config" / "experiment.toml"


class SettingsTest(unittest.TestCase):
    def test_loads_contiguous_utc_periods(self):
        settings = load_settings(CONFIG)

        self.assertEqual(settings.h3_resolution, 5)
        self.assertEqual(settings.timezone, "UTC")
        self.assertEqual(settings.accepted_confidence, {"nominal", "high"})
        self.assertEqual(settings.periods.split_for(date(2023, 12, 31)), "train")
        self.assertEqual(
            settings.periods.split_for(date(2024, 1, 1)), "validation"
        )
        self.assertEqual(settings.periods.split_for(date(2025, 1, 1)), "test")


if __name__ == "__main__":
    unittest.main()
