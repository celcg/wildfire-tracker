"""Run the bounded evaluation set against the configured Vertex AI model."""

import json

from ai_search_evaluator import evaluate_interpreter
from vertex_ai_search import get_vertex_search_generator


def main() -> None:
    generator = get_vertex_search_generator()
    summary = evaluate_interpreter(generator).to_dict()
    report = {**summary, "token_usage": generator.usage.snapshot()}
    print(json.dumps(report, indent=2))

    accepted = (
        summary["valid_schema_rate"] == 1
        and summary["exact_match_rate"] >= 0.8
        and summary["safe_rejection_rate"] == 1
        and summary["false_accept_cases"] == 0
    )
    raise SystemExit(0 if accepted else 1)


if __name__ == "__main__":
    main()
