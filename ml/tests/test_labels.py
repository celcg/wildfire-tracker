from datetime import date
import unittest

import pandas as pd

from wildfire_risk.labels import build_label_panel


class LabelPanelTest(unittest.TestCase):
    def test_builds_complete_panel_and_accepts_nominal_and_high(self):
        detections = pd.DataFrame(
            [
                {"h3_cell": "cell-a", "target_date": "2024-01-01", "confidence": "n"},
                {"h3_cell": "cell-a", "target_date": "2024-01-01", "confidence": "H"},
                {"h3_cell": "cell-b", "target_date": "2024-01-02", "confidence": "low"},
            ]
        )

        result = build_label_panel(
            detections,
            h3_cells=["cell-b", "cell-a"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
            accepted_confidence=frozenset({"nominal", "high"}),
        )

        self.assertEqual(
            result[["target_date", "h3_cell"]].to_records(index=False).tolist(),
            [
                (date(2024, 1, 1), "cell-a"),
                (date(2024, 1, 1), "cell-b"),
                (date(2024, 1, 2), "cell-a"),
                (date(2024, 1, 2), "cell-b"),
            ],
        )
        self.assertEqual(result["detection_count"].tolist(), [2, 0, 0, 0])
        self.assertEqual(result["label_detection"].tolist(), [1, 0, 0, 0])

    def test_keeps_excluded_source_dates_unknown(self):
        result = build_label_panel(
            pd.DataFrame(
                columns=["h3_cell", "target_date", "confidence"]
            ),
            h3_cells=["cell-a"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
            accepted_confidence=frozenset({"nominal", "high"}),
            excluded_dates=[date(2024, 1, 2)],
        )

        excluded = result.iloc[1]
        self.assertTrue(pd.isna(excluded["detection_count"]))
        self.assertTrue(pd.isna(excluded["label_detection"]))
        self.assertEqual(excluded["label_status"], "excluded_source_period")

    def test_rejects_duplicate_detection_ids(self):
        detections = pd.DataFrame(
            [
                {
                    "detection_id": "same",
                    "h3_cell": "cell-a",
                    "target_date": "2024-01-01",
                    "confidence": "n",
                },
                {
                    "detection_id": "same",
                    "h3_cell": "cell-a",
                    "target_date": "2024-01-01",
                    "confidence": "n",
                },
            ]
        )

        with self.assertRaisesRegex(ValueError, "detection_id must be unique"):
            build_label_panel(
                detections,
                h3_cells=["cell-a"],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
                accepted_confidence=frozenset({"nominal", "high"}),
            )


if __name__ == "__main__":
    unittest.main()
