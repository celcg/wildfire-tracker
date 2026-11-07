"""Opt-in, durable fire snapshots. No route or scheduler imports this module."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from config import FIRE_COLUMNS
from fire_data import DATA_STALE_ATTR


@dataclass(frozen=True)
class PublishedFires:
    records: list[dict]
    published_at: datetime
    age: timedelta
    status: str  # fresh, stale, or expired


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("time must include a timezone")
    return value.astimezone(timezone.utc)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        try:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


class FireSnapshotStore:
    """Publish immutable JSON, then atomically switch the per-window pointer."""

    def __init__(self, directory: Path, *, fresh_for: timedelta, usable_for: timedelta):
        if fresh_for <= timedelta(0) or usable_for < fresh_for:
            raise ValueError("invalid freshness windows")
        self.directory = Path(directory)
        self.fresh_for = fresh_for
        self.usable_for = usable_for

    def _pointer(self, days: int) -> Path:
        if not 1 <= days <= 10:
            raise ValueError("days must be between 1 and 10")
        return self.directory / f"fires-{days}.json"

    def read(self, days: int, *, now: datetime) -> PublishedFires | None:
        pointer = self._pointer(days)
        try:
            metadata = json.loads(pointer.read_bytes())
        except FileNotFoundError:
            return None
        name = metadata["snapshot"]
        if not isinstance(name, str) or not name.startswith(f"fires-{days}-") or name != Path(name).name:
            raise ValueError("invalid snapshot name")
        payload = (self.directory / name).read_bytes()
        if hashlib.sha256(payload).hexdigest() != metadata["sha256"]:
            raise ValueError("snapshot checksum mismatch")
        records = json.loads(payload)
        if not isinstance(records, list):
            raise ValueError("snapshot must contain an array")
        published_at = _utc(datetime.fromisoformat(metadata["published_at"]))
        age = _utc(now) - published_at
        if age < timedelta(0):
            raise ValueError("snapshot is dated in the future")
        status = "fresh" if age < self.fresh_for else "stale" if age <= self.usable_for else "expired"
        return PublishedFires(records, published_at, age, status)

    def publish(self, days: int, *, fetch: Callable[[int], pd.DataFrame], now: datetime) -> PublishedFires:
        pointer = self._pointer(days)
        published_at = _utc(now)
        frame = fetch(days)
        if bool(frame.attrs.get(DATA_STALE_ATTR, False)):
            raise ValueError("cannot publish stale source data")
        if not set(FIRE_COLUMNS).issubset(frame.columns):
            raise ValueError("source is missing public fire columns")
        records = frame[FIRE_COLUMNS].to_dict(orient="records")
        payload = json.dumps(records, allow_nan=False, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        name = f"fires-{days}-{digest}.json"
        snapshot = self.directory / name
        if not snapshot.exists():
            _atomic_write(snapshot, payload)
        metadata = {
            "snapshot": name,
            "sha256": digest,
            "published_at": published_at.isoformat(),
        }
        _atomic_write(pointer, json.dumps(metadata, separators=(",", ":")).encode("utf-8"))
        return PublishedFires(records, published_at, timedelta(0), "fresh")

    def refresh_or_read(self, days: int, *, fetch: Callable[[int], pd.DataFrame], now: datetime) -> PublishedFires:
        """Keep the last usable publication if acquisition or publication fails."""
        try:
            return self.publish(days, fetch=fetch, now=now)
        except Exception:
            previous = self.read(days, now=now)
            if previous is None or previous.status == "expired":
                raise
            return previous
