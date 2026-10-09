"""Small provenance manifests for immutable source files."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .firms_archive import FirmsNormalizationReport


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_firms_manifest(
    path: str | Path,
    *,
    source_product: str,
    year: int,
    source_url: str,
    downloaded_at: datetime,
    report: FirmsNormalizationReport,
) -> dict[str, object]:
    if downloaded_at.tzinfo is None:
        raise ValueError("downloaded_at must include a timezone")

    source_path = Path(path)
    url = urlsplit(source_url)
    sanitized_url = urlunsplit((url.scheme, url.netloc, url.path, "", ""))
    downloaded_utc = downloaded_at.astimezone(timezone.utc)
    return {
        "source_product": source_product,
        "year": year,
        "source_url": sanitized_url,
        "downloaded_at": downloaded_utc.isoformat().replace("+00:00", "Z"),
        "filename": source_path.name,
        "size_bytes": source_path.stat().st_size,
        "sha256": file_sha256(source_path),
        "status": "complete",
        "normalization": asdict(report),
    }
