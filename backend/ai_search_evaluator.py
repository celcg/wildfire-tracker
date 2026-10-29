"""Deterministic metrics for the versioned AI search evaluation set."""

import json
from dataclasses import asdict, dataclass
from math import ceil
from pathlib import Path
from time import perf_counter

from ai_search import (
    FireSearchInterpretation,
    InterpretationGenerator,
    SearchContractError,
    interpret_question,
)


DEFAULT_DATASET_PATH = Path(__file__).with_name("ai_search_evaluation.json")


@dataclass(frozen=True)
class EvaluationFailure:
    """Privacy-safe diagnostics for a versioned, synthetic evaluation case."""

    case_id: str
    reason: str
    expected_status: str
    actual_status: str | None
    differing_fields: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationSummary:
    total_cases: int
    valid_schema_cases: int
    exact_match_cases: int
    rejection_cases: int
    correct_rejection_cases: int
    false_accept_cases: int
    median_latency_ms: float
    p95_latency_ms: float
    failed_cases: tuple[EvaluationFailure, ...]

    def to_dict(self) -> dict:
        values = asdict(self)
        denominator = self.total_cases or 1
        rejection_denominator = self.rejection_cases or 1
        values.update(
            valid_schema_rate=round(self.valid_schema_cases / denominator, 4),
            exact_match_rate=round(self.exact_match_cases / denominator, 4),
            safe_rejection_rate=round(
                self.correct_rejection_cases / rejection_denominator,
                4,
            ),
        )
        return values


def _percentile(samples: list[float], percentile: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    index = max(0, ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def load_evaluation_cases(path: Path = DEFAULT_DATASET_PATH) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != 1 or not isinstance(payload.get("cases"), list):
        raise ValueError("Unsupported AI search evaluation dataset")
    return payload["cases"]


def _differing_fields(
    expected: FireSearchInterpretation,
    actual: FireSearchInterpretation,
) -> tuple[str, ...]:
    """Name mismatched contract fields without printing prompts or model values."""
    differences: list[str] = []
    if expected.status != actual.status:
        differences.append("status")

    expected_filters = expected.filters.model_dump() if expected.filters else None
    actual_filters = actual.filters.model_dump() if actual.filters else None
    if expected_filters is None or actual_filters is None:
        if expected_filters != actual_filters:
            differences.append("filters")
        return tuple(differences)

    for field in sorted(expected_filters.keys() | actual_filters.keys()):
        if expected_filters.get(field) != actual_filters.get(field):
            differences.append(f"filters.{field}")
    return tuple(differences)


def evaluate_interpreter(
    generate: InterpretationGenerator,
    cases: list[dict] | None = None,
) -> EvaluationSummary:
    """Measure schema validity, exact filters, safe rejection and latency."""
    selected_cases = cases if cases is not None else load_evaluation_cases()
    valid_schema = 0
    exact_matches = 0
    rejection_cases = 0
    correct_rejections = 0
    false_accepts = 0
    latencies: list[float] = []
    failures: list[EvaluationFailure] = []

    for index, case in enumerate(selected_cases):
        case_id = str(case.get("id") or f"case-{index + 1}")
        expected = FireSearchInterpretation.model_validate(case["expected"])
        if expected.status != "filters":
            rejection_cases += 1

        started_at = perf_counter()
        try:
            actual = interpret_question(case["question"], generate)
        except (SearchContractError, TimeoutError, RuntimeError):
            actual = None
        latencies.append((perf_counter() - started_at) * 1000)

        if actual is None:
            failures.append(
                EvaluationFailure(
                    case_id=case_id,
                    reason="response_contract_error",
                    expected_status=expected.status,
                    actual_status=None,
                    differing_fields=("response_contract",),
                )
            )
            continue
        valid_schema += 1
        if actual == expected:
            exact_matches += 1
        else:
            failures.append(
                EvaluationFailure(
                    case_id=case_id,
                    reason="interpretation_mismatch",
                    expected_status=expected.status,
                    actual_status=actual.status,
                    differing_fields=_differing_fields(expected, actual),
                )
            )
        if expected.status != "filters":
            if actual.status == expected.status:
                correct_rejections += 1
            elif actual.status == "filters":
                false_accepts += 1

    ordered = sorted(latencies)
    median = ordered[len(ordered) // 2] if ordered else 0.0
    return EvaluationSummary(
        total_cases=len(selected_cases),
        valid_schema_cases=valid_schema,
        exact_match_cases=exact_matches,
        rejection_cases=rejection_cases,
        correct_rejection_cases=correct_rejections,
        false_accept_cases=false_accepts,
        median_latency_ms=round(median, 3),
        p95_latency_ms=round(_percentile(latencies, 0.95), 3),
        failed_cases=tuple(failures),
    )
