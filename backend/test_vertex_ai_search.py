import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ai_search import SearchContractError, build_model_request
from vertex_ai_search import VertexSearchGenerator, _create_client


class FakeModels:
    def __init__(self, text, usage_metadata=None):
        self.text = text
        self.usage_metadata = usage_metadata
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            text=self.text,
            usage_metadata=self.usage_metadata,
        )


class VertexSearchGeneratorTest(unittest.TestCase):
    def test_sends_only_the_question_instruction_and_closed_schema(self):
        models = FakeModels('{"status":"unsupported"}')
        client = SimpleNamespace(models=models)
        generator = VertexSearchGenerator(client=client)
        request = build_model_request("Focos persistentes en Galicia")

        output = generator(request)

        self.assertEqual(output, '{"status":"unsupported"}')
        call = models.calls[0]
        self.assertEqual(call["model"], "gemini-3.5-flash-lite")
        self.assertEqual(call["contents"], request.question)
        self.assertEqual(
            call["config"].response_mime_type,
            "application/json",
        )
        self.assertEqual(
            call["config"].response_json_schema,
            request.response_schema,
        )
        self.assertIsNone(call["config"].tools)

    def test_rejects_an_empty_model_response(self):
        generator = VertexSearchGenerator(
            client=SimpleNamespace(models=FakeModels(None))
        )

        with self.assertRaises(SearchContractError):
            generator(build_model_request("Focos de hoy"))

    def test_aggregates_only_numeric_token_metadata(self):
        usage = SimpleNamespace(
            prompt_token_count=120,
            cached_content_token_count=20,
            tool_use_prompt_token_count=0,
            candidates_token_count=30,
            thoughts_token_count=10,
            total_token_count=160,
        )
        generator = VertexSearchGenerator(
            client=SimpleNamespace(
                models=FakeModels('{"status":"unsupported"}', usage)
            )
        )

        generator(build_model_request("Focos de hoy"))

        self.assertEqual(
            generator.usage.snapshot(),
            {
                "request_count": 1,
                "prompt_tokens": 120,
                "cached_prompt_tokens": 20,
                "tool_prompt_tokens": 0,
                "candidate_tokens": 30,
                "thought_tokens": 10,
                "total_tokens": 160,
                "billable_input_tokens": 100,
                "billable_output_tokens": 40,
            },
        )

    def test_client_creation_requires_feature_flag_and_project(self):
        with patch("config.AI_SEARCH_ENABLED", False):
            with self.assertRaises(SearchContractError):
                _create_client()

        with patch("config.AI_SEARCH_ENABLED", True):
            with patch("config.AI_SEARCH_PROJECT_ID", ""):
                with self.assertRaises(SearchContractError):
                    _create_client()

    @patch("vertex_ai_search.genai.Client")
    def test_client_has_one_attempt_and_a_bounded_timeout(self, client):
        with patch("config.AI_SEARCH_ENABLED", True):
            with patch("config.AI_SEARCH_PROJECT_ID", "safe-project"):
                _create_client()

        options = client.call_args.kwargs["http_options"]
        self.assertEqual(options.api_version, "v1")
        self.assertEqual(options.timeout, 5_000)
        self.assertEqual(options.retry_options.attempts, 1)


if __name__ == "__main__":
    unittest.main()
