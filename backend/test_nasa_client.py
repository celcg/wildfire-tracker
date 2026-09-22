import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests

import config
from nasa_client import NasaPayloadError, NasaPayloadTooLarge, fetch_nasa_csv


def response_with(payload: bytes, content_type: str = "text/csv") -> Mock:
    response = Mock()
    response.headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(payload)),
    }
    response.iter_content.return_value = [payload]
    return response


class NasaClientTest(unittest.TestCase):
    @patch("nasa_client.requests.get", side_effect=requests.Timeout("timed out"))
    def test_propagates_transport_timeout_without_retrying(self, get):
        with self.assertRaises(requests.Timeout):
            fetch_nasa_csv("https://example.invalid/data.csv")

        get.assert_called_once()

    @patch("nasa_client.requests.get")
    def test_fetches_with_bounded_streaming_and_closes_response(self, get):
        response = response_with(b"latitude,longitude\n42.1,-8.6\n")
        get.return_value = response

        result = fetch_nasa_csv("https://example.invalid/data.csv")

        self.assertEqual(len(result), 1)
        get.assert_called_once_with(
            "https://example.invalid/data.csv",
            stream=True,
            timeout=(
                config.NASA_CONNECT_TIMEOUT_SECONDS,
                config.NASA_READ_TIMEOUT_SECONDS,
            ),
            headers={"Accept": "text/csv", "Accept-Encoding": "identity"},
        )
        response.close.assert_called_once()

    @patch("nasa_client.requests.get")
    def test_rejects_unexpected_content_type_and_closes_response(self, get):
        response = response_with(b"<html>failure</html>", "text/html")
        get.return_value = response

        with self.assertRaisesRegex(NasaPayloadError, "content type"):
            fetch_nasa_csv("https://example.invalid/data.csv")

        response.close.assert_called_once()

    @patch("nasa_client.requests.get")
    def test_rejects_declared_oversized_payload(self, get):
        response = response_with(b"small")
        response.headers["Content-Length"] = str(config.NASA_MAX_RESPONSE_BYTES + 1)
        get.return_value = response

        with self.assertRaises(NasaPayloadTooLarge):
            fetch_nasa_csv("https://example.invalid/data.csv")

        response.iter_content.assert_not_called()
        response.close.assert_called_once()

    @patch("nasa_client.requests.get")
    def test_rejects_stream_that_exceeds_byte_limit(self, get):
        response = response_with(b"")
        response.headers.pop("Content-Length")
        response.iter_content.return_value = [b"1234", b"5678"]
        get.return_value = response

        with patch.object(config, "NASA_MAX_RESPONSE_BYTES", 7):
            with self.assertRaises(NasaPayloadTooLarge):
                fetch_nasa_csv("https://example.invalid/data.csv")

        response.close.assert_called_once()

    @patch("nasa_client.requests.get")
    def test_rejects_empty_or_malformed_csv(self, get):
        empty_response = response_with(b"")
        malformed_response = response_with(b"\xff\xfe\xfd")
        get.side_effect = [empty_response, malformed_response]

        with self.assertRaisesRegex(NasaPayloadError, "empty payload"):
            fetch_nasa_csv("https://example.invalid/empty.csv")
        with self.assertRaisesRegex(NasaPayloadError, "malformed CSV"):
            fetch_nasa_csv("https://example.invalid/malformed.csv")

        empty_response.close.assert_called_once()
        malformed_response.close.assert_called_once()

    @patch("nasa_client.requests.get")
    def test_rejects_more_than_the_configured_row_limit(self, get):
        response = response_with(b"latitude\n42.1\n42.2\n")
        get.return_value = response

        with patch.object(config, "NASA_MAX_ROWS", 1):
            with self.assertRaisesRegex(NasaPayloadTooLarge, "row limit"):
                fetch_nasa_csv("https://example.invalid/data.csv")

        response.close.assert_called_once()

    @patch("nasa_client.requests.get")
    def test_closes_response_when_http_status_is_rejected(self, get):
        response = response_with(b"failure")
        response.raise_for_status.side_effect = requests.HTTPError("upstream URL")
        get.return_value = response

        with self.assertRaises(requests.HTTPError):
            fetch_nasa_csv("https://example.invalid/data.csv")

        response.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
