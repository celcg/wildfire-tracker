"""Google Gen AI adapter for bounded filter interpretation on Vertex AI."""

from dataclasses import dataclass, field
from functools import lru_cache
from threading import Lock

from google import genai
from google.genai import types

import config
from ai_search import ModelInterpretationRequest, SearchContractError


@dataclass
class TokenUsage:
    """Aggregate numeric billing metadata without retaining prompts or responses."""

    request_count: int = 0
    prompt_tokens: int = 0
    cached_prompt_tokens: int = 0
    tool_prompt_tokens: int = 0
    candidate_tokens: int = 0
    thought_tokens: int = 0
    total_tokens: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, metadata) -> None:
        if metadata is None:
            return

        def count(name: str) -> int:
            return int(getattr(metadata, name, None) or 0)

        with self._lock:
            self.request_count += 1
            self.prompt_tokens += count("prompt_token_count")
            self.cached_prompt_tokens += count("cached_content_token_count")
            self.tool_prompt_tokens += count("tool_use_prompt_token_count")
            self.candidate_tokens += count("candidates_token_count")
            self.thought_tokens += count("thoughts_token_count")
            self.total_tokens += count("total_token_count")

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            billable_input = (
                max(self.prompt_tokens - self.cached_prompt_tokens, 0)
                + self.tool_prompt_tokens
            )
            return {
                "request_count": self.request_count,
                "prompt_tokens": self.prompt_tokens,
                "cached_prompt_tokens": self.cached_prompt_tokens,
                "tool_prompt_tokens": self.tool_prompt_tokens,
                "candidate_tokens": self.candidate_tokens,
                "thought_tokens": self.thought_tokens,
                "total_tokens": self.total_tokens,
                "billable_input_tokens": billable_input,
                "billable_output_tokens": self.candidate_tokens
                + self.thought_tokens,
            }


class VertexSearchGenerator:
    """Generate one schema-constrained JSON interpretation without tools."""

    def __init__(self, client=None):
        self._client = client if client is not None else _create_client()
        self.usage = TokenUsage()

    def __call__(self, request: ModelInterpretationRequest) -> str:
        response = self._client.models.generate_content(
            model=config.AI_SEARCH_MODEL,
            contents=request.question,
            config=types.GenerateContentConfig(
                system_instruction=request.system_instruction,
                response_mime_type="application/json",
                response_json_schema=request.response_schema,
                max_output_tokens=config.AI_SEARCH_MAX_OUTPUT_TOKENS,
            ),
        )
        self.usage.record(getattr(response, "usage_metadata", None))
        if not isinstance(response.text, str) or not response.text:
            raise SearchContractError("Model returned no interpretation")
        return response.text


def _create_client():
    if not config.AI_SEARCH_ENABLED:
        raise SearchContractError("AI-assisted search is disabled")
    if not config.AI_SEARCH_PROJECT_ID:
        raise SearchContractError("AI search project is not configured")

    return genai.Client(
        enterprise=True,
        project=config.AI_SEARCH_PROJECT_ID,
        location=config.AI_SEARCH_LOCATION,
        http_options=types.HttpOptions(
            api_version="v1",
            timeout=int(config.AI_SEARCH_TIMEOUT_SECONDS * 1000),
            # A public search must fail fast instead of multiplying paid calls.
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


@lru_cache(maxsize=1)
def get_vertex_search_generator() -> VertexSearchGenerator:
    """Reuse the authenticated HTTP client across Cloud Run requests."""
    return VertexSearchGenerator()
