import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request

import config
from ai_rate_limit import AiRateLimiter, enforce_ai_request
from rate_limit_store import InMemoryTokenBucketStore


FIRST_ID = "019b4dc8-e75a-4d97-b0c2-98780b891f28"
SECOND_ID = "8ab903b2-b125-4933-8e3f-1cb076be4fb9"


def request_for(client_id=FIRST_ID, content_length="40") -> Request:
    return Request(
        {
            "type": "http",
            "client": ("192.0.2.1", 1234),
            "headers": [
                (b"x-client-id", client_id.encode("ascii")),
                (b"content-length", content_length.encode("ascii")),
            ],
            "method": "POST",
            "path": "/search/interpret",
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "http_version": "1.1",
        }
    )


def store(capacity, refill=1_000_000):
    return InMemoryTokenBucketStore(capacity, refill, 86_400)


class BrokenStore:
    def consume(self, _client_key, _now):
        raise RuntimeError("Firestore unavailable")


class AiRateLimitTest(unittest.TestCase):
    def test_client_bucket_is_separate_and_stricter(self):
        limiter = AiRateLimiter(
            per_client_store=store(3),
            global_store=store(60),
        )

        with patch("rate_limit.time", return_value=100):
            for _ in range(3):
                limiter.enforce(request_for())
            with self.assertRaises(HTTPException) as raised:
                limiter.enforce(request_for())

        self.assertEqual(raised.exception.status_code, 429)

    def test_global_bucket_is_shared_across_client_ids(self):
        limiter = AiRateLimiter(
            per_client_store=store(10),
            global_store=store(1),
        )

        with patch("rate_limit.time", return_value=100):
            limiter.enforce(request_for(FIRST_ID))
            with self.assertRaises(HTTPException) as raised:
                limiter.enforce(request_for(SECOND_ID))

        self.assertEqual(raised.exception.status_code, 429)

    def test_firestore_failure_fails_closed_before_vertex(self):
        limiter = AiRateLimiter(
            per_client_store=BrokenStore(),
            global_store=store(60),
        )

        with self.assertRaises(HTTPException) as raised:
            limiter.enforce(request_for())

        self.assertEqual(raised.exception.status_code, 503)

    def test_oversized_request_is_rejected_before_rate_limit(self):
        oversized = str(config.AI_SEARCH_MAX_REQUEST_BYTES + 1)
        with self.assertRaises(HTTPException) as raised:
            enforce_ai_request(request_for(content_length=oversized))

        self.assertEqual(raised.exception.status_code, 413)


if __name__ == "__main__":
    unittest.main()
