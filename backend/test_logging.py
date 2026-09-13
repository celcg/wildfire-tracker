import io
import json
import logging
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from fastapi import Request, Response

import config
import main
from logging_config import (
    REQUEST_ID_HEADER,
    bind_request_id,
    configure_logging,
    get_logger,
    log_event,
    reset_request_id,
)


class LoggingConfigurationTest(unittest.TestCase):
    def tearDown(self):
        # Close temporary file handlers before TemporaryDirectory cleanup and
        # leave later tests with a harmless in-memory console handler.
        configure_logging(log_to_file=False, stream=io.StringIO())

    def test_default_rotation_budget_is_one_hundred_mib(self):
        # The active file counts toward the total alongside every retained backup.
        total_capacity = config.LOG_MAX_BYTES * (config.LOG_BACKUP_COUNT + 1)

        self.assertEqual(total_capacity, 100 * 1024 * 1024)

    def test_writes_utc_timestamps_and_rotates_bounded_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "wildfire-api.log"
            configure_logging(
                log_to_file=True,
                log_file_path=log_path,
                max_bytes=240,
                backup_count=2,
                stream=io.StringIO(),
            )
            logger = get_logger("rotation_test")

            for index in range(30):
                log_event(
                    logger,
                    logging.INFO,
                    "rotation.test",
                    sequence=index,
                    payload="bounded-message",
                )

            configure_logging(log_to_file=False, stream=io.StringIO())
            files = sorted(log_path.parent.glob("wildfire-api.log*"))
            self.assertGreaterEqual(len(files), 2)
            self.assertLessEqual(len(files), 3)
            self.assertTrue((log_path.parent / "wildfire-api.log.1").exists())
            for file in files:
                first_line = file.read_text(encoding="utf-8").splitlines()[0]
                self.assertRegex(
                    first_line,
                    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z \| INFO \|",
                )

    def test_redacts_secrets_and_neutralizes_log_injection(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "wildfire-api.log"
            with patch.object(config, "NASA_KEY", "super-secret-key"):
                configure_logging(
                    log_to_file=True,
                    log_file_path=log_path,
                    stream=io.StringIO(),
                )
                log_event(
                    get_logger("security_test"),
                    logging.WARNING,
                    "security.test",
                    untrusted="super-secret-key\r\nFORGED_LOG",
                )
                configure_logging(log_to_file=False, stream=io.StringIO())
                contents = log_path.read_text(encoding="utf-8")

            self.assertNotIn("super-secret-key", contents)
            self.assertIn("[REDACTED] FORGED_LOG", contents)
            self.assertEqual(len(contents.splitlines()), 1)

    def test_stdout_is_structured_json_with_request_context(self):
        stream = io.StringIO()
        configure_logging(log_to_file=False, stream=stream)
        request_id = "d201c173-d90f-4814-9c84-8cdd43d8f910"
        token = bind_request_id(request_id)
        try:
            log_event(
                get_logger("json_test"),
                logging.INFO,
                "cache.hit",
                days=3,
            )
        finally:
            reset_request_id(token)

        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["severity"], "INFO")
        self.assertEqual(payload["event"], "cache.hit")
        self.assertEqual(payload["request_id"], request_id)
        self.assertEqual(payload["days"], 3)
        self.assertRegex(payload["timestamp"], r"Z$")


class RequestLoggingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.stream = io.StringIO()
        configure_logging(log_to_file=False, stream=self.stream)

    def tearDown(self):
        configure_logging(log_to_file=False, stream=io.StringIO())

    @staticmethod
    def _request(request_id: str | None) -> Request:
        headers = []
        if request_id is not None:
            headers.append((b"x-request-id", request_id.encode("ascii")))
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/fires",
            "query_string": b"days=3&refresh=true&secret=ignored",
            "headers": headers,
            "client": ("192.0.2.1", 1234),
            "server": ("testserver", 80),
            "scheme": "http",
            "route": SimpleNamespace(path="/fires"),
        }
        return Request(scope)

    async def test_valid_request_id_is_returned_and_logged(self):
        request_id = "19ca6c2e-573d-4c9a-85f5-34cef837f8cb"

        async def call_next(_request):
            return Response(
                headers={
                    "X-Data-Stale": "false",
                    "X-Data-Age-Seconds": "30",
                }
            )

        response = await main.log_http_request(
            self._request(request_id),
            call_next,
        )
        payload = json.loads(self.stream.getvalue())

        self.assertEqual(response.headers[REQUEST_ID_HEADER], request_id)
        self.assertEqual(payload["request_id"], request_id)
        self.assertEqual(payload["path"], "/fires")
        self.assertEqual(payload["days"], "3")
        self.assertEqual(payload["refresh"], "true")
        self.assertNotIn("secret", payload)
        self.assertNotIn("192.0.2.1", self.stream.getvalue())

    async def test_invalid_request_id_is_replaced_with_a_uuid(self):
        async def call_next(_request):
            return Response(status_code=429)

        response = await main.log_http_request(
            self._request("bad-id"),
            call_next,
        )
        generated_id = response.headers[REQUEST_ID_HEADER]
        payload = json.loads(self.stream.getvalue())

        self.assertEqual(str(UUID(generated_id)), generated_id)
        self.assertEqual(payload["severity"], "WARNING")


class CorsLoggingContractTest(unittest.TestCase):
    def test_request_id_header_is_allowed_and_exposed(self):
        cors_middleware = next(
            middleware
            for middleware in main.app.user_middleware
            if middleware.cls.__name__ == "CORSMiddleware"
        )

        self.assertIn(REQUEST_ID_HEADER, cors_middleware.kwargs["allow_headers"])
        self.assertIn(REQUEST_ID_HEADER, cors_middleware.kwargs["expose_headers"])


if __name__ == "__main__":
    unittest.main()
