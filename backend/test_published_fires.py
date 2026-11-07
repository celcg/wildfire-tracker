"""File publication remains safe when a later acquisition fails."""

import json
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from config import FIRE_COLUMNS
from published_fires import FireSnapshotStore
from published_fires import _atomic_write


class FireSnapshotStoreTest(unittest.TestCase):
    def test_publication_fallback_and_expiry(self):
        start = datetime(2026, 10, 22, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            store = FireSnapshotStore(Path(directory), fresh_for=timedelta(hours=1), usable_for=timedelta(hours=24))
            frame = pd.DataFrame([{column: "example" for column in FIRE_COLUMNS}])
            first = store.publish(1, fetch=lambda days: frame, now=start)
            self.assertEqual(first.status, "fresh")
            self.assertEqual(store.read(1, now=start + timedelta(hours=2)).status, "stale")
            pointer_before = (Path(directory) / "fires-1.json").read_bytes()

            def broken_fetch(days):
                raise RuntimeError("upstream unavailable")

            fallback = store.refresh_or_read(1, fetch=broken_fetch, now=start + timedelta(hours=2))
            self.assertEqual(fallback.records, first.records)
            self.assertEqual(pointer_before, (Path(directory) / "fires-1.json").read_bytes())
            with self.assertRaises(RuntimeError):
                store.refresh_or_read(1, fetch=broken_fetch, now=start + timedelta(days=2))

    def test_rejects_stale_source_and_corrupted_snapshot(self):
        now = datetime(2026, 10, 22, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            store = FireSnapshotStore(Path(directory), fresh_for=timedelta(hours=1), usable_for=timedelta(hours=24))
            frame = pd.DataFrame(columns=FIRE_COLUMNS)
            frame.attrs["data_stale"] = True
            with self.assertRaises(ValueError):
                store.publish(1, fetch=lambda days: frame, now=now)
            self.assertIsNone(store.read(1, now=now))
            frame.attrs["data_stale"] = False
            store.publish(1, fetch=lambda days: frame, now=now)
            pointer = json.loads((Path(directory) / "fires-1.json").read_text())
            (Path(directory) / pointer["snapshot"]).write_text("[] ")
            with self.assertRaisesRegex(ValueError, "checksum"):
                store.read(1, now=now)

    def test_failed_pointer_publication_keeps_previous_snapshot(self):
        now = datetime(2026, 10, 22, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            store = FireSnapshotStore(Path(directory), fresh_for=timedelta(hours=1), usable_for=timedelta(hours=24))
            original = pd.DataFrame([{column: "first" for column in FIRE_COLUMNS}])
            replacement = pd.DataFrame([{column: "second" for column in FIRE_COLUMNS}])
            store.publish(1, fetch=lambda days: original, now=now)

            def fail_pointer(path, content):
                if path.name == "fires-1.json":
                    raise OSError("publication failed")
                return _atomic_write(path, content)

            with patch("published_fires._atomic_write", side_effect=fail_pointer):
                result = store.refresh_or_read(1, fetch=lambda days: replacement, now=now + timedelta(hours=2))
            self.assertEqual(result.status, "stale")
            self.assertEqual(result.records, original[FIRE_COLUMNS].to_dict(orient="records"))
