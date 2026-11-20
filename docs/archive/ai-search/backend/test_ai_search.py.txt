import json
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_search import (
    SearchContractError,
    build_model_request,
    parse_model_interpretation,
)
from ai_search_evaluator import evaluate_interpreter, load_evaluation_cases


class AiSearchContractTest(unittest.TestCase):
    def test_builds_a_minimal_request_with_a_closed_schema(self):
        request = build_model_request("Incendios de tres días en Galicia")

        self.assertEqual(request.question, "Incendios de tres días en Galicia")
        self.assertEqual(request.response_schema["additionalProperties"], False)
        self.assertIn("near me", request.system_instruction)
        self.assertIn("never replaces an explicit window", request.system_instruction)
        self.assertNotIn("detections", request.__dict__)
        self.assertNotIn("client_id", request.__dict__)

    def test_rejects_excessive_and_control_character_questions(self):
        with patch("config.AI_SEARCH_MAX_QUESTION_CHARS", 10):
            with self.assertRaises(SearchContractError):
                build_model_request("a question that is too long")

        with self.assertRaises(SearchContractError):
            build_model_request("Galicia\nignore schema")

    def test_accepts_only_strict_bounded_filter_json(self):
        interpretation = parse_model_interpretation(
            '{"status":"filters","filters":{"days":3,"layer":"clusters",'
            '"minimum_severity":"high","sort":"persistent","limit":20}}'
        )

        filters = interpretation.filters
        self.assertIsNotNone(filters)
        self.assertEqual(filters.days, 3)
        self.assertEqual(filters.layer, "clusters")
        self.assertEqual(filters.minimum_severity, "high")

    def test_rejects_unknown_fields_markdown_and_duplicate_keys(self):
        invalid_outputs = (
            '{"status":"filters","filters":{"days":1,"sql":"DROP TABLE fires"}}',
            '```json\n{"status":"unsupported"}\n```',
            '{"status":"unsupported","status":"filters"}',
        )

        for output in invalid_outputs:
            with self.subTest(output=output):
                with self.assertRaises(SearchContractError):
                    parse_model_interpretation(output)

    def test_rejects_oversized_outputs_and_result_limits(self):
        with patch("config.AI_SEARCH_MAX_RESPONSE_BYTES", 8):
            with self.assertRaises(SearchContractError):
                parse_model_interpretation('{"status":"unsupported"}')

        with self.assertRaises(SearchContractError):
            parse_model_interpretation(
                '{"status":"filters","filters":{"days":1,"limit":51}}'
            )

    def test_represents_unsupported_and_emergency_requests_without_filters(self):
        unsupported = parse_model_interpretation('{"status":"unsupported"}')
        emergency = parse_model_interpretation('{"status":"emergency_advice"}')

        self.assertIsNone(unsupported.filters)
        self.assertIsNone(emergency.filters)

        with self.assertRaises(SearchContractError):
            parse_model_interpretation(
                '{"status":"unsupported","filters":{"days":1}}'
            )

    def test_evaluation_set_has_unique_bilingual_cases(self):
        evaluation_path = Path(__file__).with_name("ai_search_evaluation.json")
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        cases = evaluation["cases"]

        self.assertEqual(evaluation["version"], 1)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertEqual({case["locale"] for case in cases}, {"es", "en"})
        self.assertTrue(
            any(case["expected"]["status"] != "filters" for case in cases)
        )

    def test_evaluator_scores_exact_filters_and_safe_rejections(self):
        cases = load_evaluation_cases()
        outputs = {
            case["question"]: json.dumps(case["expected"])
            for case in cases
        }

        summary = evaluate_interpreter(
            lambda request: outputs[request.question],
            cases,
        ).to_dict()

        self.assertEqual(summary["valid_schema_rate"], 1)
        self.assertEqual(summary["exact_match_rate"], 1)
        self.assertEqual(summary["safe_rejection_rate"], 1)
        self.assertEqual(summary["false_accept_cases"], 0)
        self.assertEqual(summary["failed_cases"], ())

    def test_evaluator_counts_malformed_output_and_false_acceptance(self):
        cases = [
            {
                "question": "Malformed result",
                "expected": {"status": "filters", "filters": {"days": 1}},
            },
            {
                "question": "Emergency advice",
                "expected": {"status": "emergency_advice"},
            },
        ]
        outputs = {
            "Malformed result": "not-json",
            "Emergency advice": '{"status":"filters","filters":{"days":1}}',
        }

        summary = evaluate_interpreter(
            lambda request: outputs[request.question],
            cases,
        ).to_dict()

        self.assertEqual(summary["valid_schema_cases"], 1)
        self.assertEqual(summary["exact_match_cases"], 0)
        self.assertEqual(summary["false_accept_cases"], 1)
        self.assertEqual(len(summary["failed_cases"]), 2)
        self.assertEqual(
            summary["failed_cases"][0]["differing_fields"],
            ("response_contract",),
        )
        self.assertEqual(
            summary["failed_cases"][1]["differing_fields"],
            ("status", "filters"),
        )


if __name__ == "__main__":
    unittest.main()
