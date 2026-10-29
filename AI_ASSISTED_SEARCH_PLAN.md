# AI-Assisted Fire Search Task Plan

## Goal

Let users ask controlled natural-language questions such as “persistent fires
near Galicia since yesterday” while keeping the model away from SQL, arbitrary
tools, secrets, and unrestricted data access.

## Chosen approach

Use Gemini Flash-Lite through Vertex AI as a bounded query interpreter. FastAPI
sends the question plus an explicit JSON schema; the model may return only
supported filter fields. Existing application code validates and executes those
filters against already-authorized wildfire data.

The model does not query NASA, BigQuery, Firestore, or the public internet. It
does not generate SQL and does not answer emergency or safety questions.

## Controlled filter contract

The first version supports only:

- relative or absolute observation dates within the API's allowed window;
- layer: detections or clusters;
- place or bounded region resolved by an approved geocoding boundary;
- minimum severity, confidence, FRP, or persistence when those values exist;
- a supported sort order and result limit.

FastAPI rejects unknown fields, invalid ranges, excessive limits, model prose,
and locations that cannot be resolved safely. The frontend always displays the
interpreted filters so the user can correct or clear them.

## Request flow

1. React sends the question to a dedicated FastAPI endpoint using the existing
   App Check, anonymous client ID, request ID, and rate-limit protections.
2. FastAPI validates length and characters, then calls Vertex AI with a strict
   response schema and low output-token limit.
3. FastAPI parses and validates the returned filter object.
4. Existing deterministic filter code applies it to permitted data.
5. React shows both the results and a plain-language filter summary.

## Files

- `frontend/src/components/FireSearch.jsx` (new)
- `frontend/src/services/fireApi.js`
- `frontend/src/domain/fireSearch.js` (new deterministic presentation helpers)
- `backend/ai_search.py` (new model adapter and validation boundary)
- `backend/main.py`
- `backend/config.py`
- focused frontend/backend tests
- `README.md`, `architecture.md`, and privacy documentation when implemented

## Security, privacy, and cost controls

- Maximum question length, request timeout, output tokens, and result count.
- Separate, stricter rate limit for AI requests.
- No coordinates, visitor identifiers, full detection payloads, logs, or secrets
  in the prompt. Send only the minimum vocabulary/context needed to parse it.
- Prompt and response are treated as untrusted input and neutralized in logs.
- Fixed Vertex model, region, quota, budget alert, and maximum instance settings.
- No automatic retry storm; deterministic fallback offers ordinary filters.
- UI states clearly that interpretation is automated and may be wrong.

## Evaluation before release

Create a versioned bilingual test set covering dates, regions, severity,
ambiguity, unsupported requests, prompt injection, malformed output, and abusive
payloads. Measure valid-schema rate, filter accuracy, false matches, latency,
and cost per request. Human review is required for failure categories.

## Acceptance criteria

- Every model output passes deterministic schema and range validation.
- The model has no free SQL, database, network, or tool access.
- Invalid or unavailable AI output never blocks manual filtering or the map.
- Tests demonstrate safe rejection of prompt injection and excessive payloads.
- A documented monthly usage ceiling fits the approved Google Cloud budget
  before Vertex AI is enabled or deployed.

## Deferred

Embeddings, vector databases, conversational memory, autonomous agents, and
generated emergency advice are outside the first version.
