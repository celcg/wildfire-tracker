"""Bounded HTTP client for the untrusted NASA FIRMS CSV response."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
import requests

import config


class NasaPayloadError(RuntimeError):
    """Raised when NASA returns content that is unsafe or cannot be parsed."""


class NasaPayloadTooLarge(NasaPayloadError):
    """Raised before an oversized response can consume excessive memory."""


def _validate_content_type(response: requests.Response) -> None:
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
    if content_type and content_type not in config.NASA_ALLOWED_CONTENT_TYPES:
        raise NasaPayloadError("NASA returned an unexpected content type")


def fetch_nasa_csv(url: str) -> pd.DataFrame:
    """Download and parse a CSV while enforcing transport and memory bounds."""
    response = requests.get(
        url,
        stream=True,
        timeout=(config.NASA_CONNECT_TIMEOUT_SECONDS, config.NASA_READ_TIMEOUT_SECONDS),
        # Counting decoded bytes is simplest when the upstream sends no compression.
        headers={"Accept": "text/csv", "Accept-Encoding": "identity"},
    )
    try:
        response.raise_for_status()
        _validate_content_type(response)

        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > config.NASA_MAX_RESPONSE_BYTES:
                    raise NasaPayloadTooLarge("NASA payload exceeds the byte limit")
            except ValueError:
                # An invalid header is ignored; the streamed byte counter remains authoritative.
                pass

        payload = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            payload.extend(chunk)
            if len(payload) > config.NASA_MAX_RESPONSE_BYTES:
                raise NasaPayloadTooLarge("NASA payload exceeds the byte limit")

        if not payload:
            raise NasaPayloadError("NASA returned an empty payload")

        try:
            # Reading one extra row lets us distinguish an exact-limit response
            # from a response that would make clustering unexpectedly expensive.
            fires = pd.read_csv(
                BytesIO(payload),
                nrows=config.NASA_MAX_ROWS + 1,
            )
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
            raise NasaPayloadError("NASA returned malformed CSV") from exc

        if len(fires) > config.NASA_MAX_ROWS:
            raise NasaPayloadTooLarge("NASA payload exceeds the row limit")
        return fires
    finally:
        response.close()
