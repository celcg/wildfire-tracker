import re
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request

import config
from client_identity import resolve_client_key
from firebase_security import enforce_app_check
from rate_limit import AnonymousRateLimiter
from rate_limit_store import InMemoryTokenBucketStore


FIRST_ID = "019b4dc8-e75a-4d97-b0c2-98780b891f28"


def request_with_headers(**headers: str) -> Request:
    return Request(
        {
            "type": "http",
            "client": ("192.0.2.1", 1234),
            "headers": [
                (name.replace("_", "-").encode("ascii"), value.encode("ascii"))
                for name, value in headers.items()
            ],
            "method": "GET",
            "path": "/fires",
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "http_version": "1.1",
        }
    )


class ClientIdentityTest(unittest.TestCase):
    def test_uuid_is_replaced_by_a_secret_hmac_key(self):
        request = request_with_headers(x_client_id=FIRST_ID)

        with patch.object(config, "CLIENT_ID_HASH_SECRET", "test-hmac-secret"):
            client_key = resolve_client_key(request)

        self.assertRegex(client_key, re.compile(r"^[0-9a-f]{64}$"))
        self.assertNotIn(FIRST_ID, client_key)

    def test_noncanonical_or_invalid_uuid_is_rejected(self):
        for candidate in (
            "invalid",
            FIRST_ID.upper(),
            "00000000-0000-0000-0000-000000000000",
            "",
        ):
            with self.subTest(candidate=candidate):
                with patch.object(config, "CLIENT_ID_REQUIRED", True):
                    with self.assertRaises(HTTPException) as raised:
                        resolve_client_key(
                            request_with_headers(x_client_id=candidate)
                        )
                self.assertEqual(raised.exception.status_code, 400)

    def test_rollout_mode_maps_a_missing_id_to_one_private_legacy_key(self):
        request = request_with_headers()

        with patch.object(config, "CLIENT_ID_REQUIRED", False):
            with patch.object(config, "CLIENT_ID_HASH_SECRET", "test-hmac-secret"):
                client_key = resolve_client_key(request)

        self.assertRegex(client_key, re.compile(r"^[0-9a-f]{64}$"))
        self.assertNotIn("legacy-client", client_key)


class AppCheckTest(unittest.TestCase):
    def test_local_mode_does_not_require_app_check(self):
        with patch.object(config, "APP_CHECK_REQUIRED", False):
            enforce_app_check(request_with_headers())

    def test_cloud_mode_rejects_a_missing_token(self):
        with patch.object(config, "APP_CHECK_REQUIRED", True):
            with self.assertRaises(HTTPException) as raised:
                enforce_app_check(request_with_headers())

        self.assertEqual(raised.exception.status_code, 403)

    def test_valid_token_is_verified_without_logging_its_value(self):
        request = request_with_headers(x_firebase_appcheck="attested-token")
        with patch.object(config, "APP_CHECK_REQUIRED", True):
            with patch("firebase_security._verify_token") as verify_token:
                enforce_app_check(request)

        verify_token.assert_called_once_with("attested-token")

    def test_rejected_token_is_not_written_to_logs(self):
        request = request_with_headers(x_firebase_appcheck="sensitive-token")
        with patch.object(config, "APP_CHECK_REQUIRED", True):
            with patch(
                "firebase_security._verify_token",
                side_effect=ValueError("sensitive-token"),
            ):
                with patch("firebase_security.log_event") as logged_event:
                    with self.assertRaises(HTTPException):
                        enforce_app_check(request)

        self.assertNotIn("sensitive-token", repr(logged_event.call_args))


class SharedTokenBucketTest(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryTokenBucketStore(
            capacity=5,
            refill_seconds=12,
            state_ttl_seconds=86_400,
        )
        self.first_instance = AnonymousRateLimiter(self.store)
        self.second_instance = AnonymousRateLimiter(self.store)
        self.request = request_with_headers(x_client_id=FIRST_ID)

    def test_instances_share_one_five_token_capacity(self):
        with patch("rate_limit.time", return_value=100):
            for _ in range(3):
                self.first_instance.enforce(self.request)
            for _ in range(2):
                self.second_instance.enforce(self.request)

            with self.assertRaises(HTTPException) as raised:
                self.second_instance.enforce(self.request)

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.headers["Retry-After"], "12")

    def test_one_token_is_restored_after_twelve_seconds(self):
        with patch("rate_limit.time", return_value=100):
            for _ in range(5):
                self.first_instance.enforce(self.request)

        with patch("rate_limit.time", return_value=112):
            self.second_instance.enforce(self.request)


if __name__ == "__main__":
    unittest.main()
