# Testing Policy

Tests are selected by risk. Most changes must not run most of the repository's
tests. Use the smallest level that can detect a realistic regression, and move
to a broader level only when the change crosses an important boundary.

No test level may consume NASA quota or write to Firestore or BigQuery.

## Levels

### Level 0: Inspection Only

Use for comments, documentation, spelling, formatting, and non-executable copy.

Required checks:

- Review the affected files.
- Run `git diff --check`.
- Run a formatter or documentation check only when the changed file has one.

Do not run application tests merely because a file changed.

### Level 1: Focused Test

Use for a localized minor fix in one function, component, or configuration
value. Run the single relevant test case or test file. If no useful automated
test exists, perform and report one focused static or manual check.

Examples:

```powershell
# From backend/
.\.venv\Scripts\python.exe -m unittest test_main.FireEndpointsTest.test_fires_passes_days_to_data_source -v
```

```bash
# From frontend/
node --test src/services/fireApi.test.js
```

Do not run unrelated files for a local fix.

### Level 2: Smoke Validation

Use for ordinary code pull requests and changes spanning a few related files.
This is the default GitHub validation level and intentionally exercises only a
small set of critical paths.

```powershell
# From backend/
.\.venv\Scripts\python.exe run_smoke_tests.py
```

On Linux and macOS, replace `.\.venv\Scripts\python.exe` with
`./.venv/bin/python` in backend commands.

```bash
# From frontend/
npm run test:smoke
npm run lint
```

`.github/workflows/validate.yml` runs this level on pull requests and pushes to
`main`. The backend smoke suite contains 10 representative tests; the frontend
smoke suite contains the API URL, API request, and request-security test files.

### Level 3: Extended Targeted Validation

Use for important changes whose blast radius is wider than smoke coverage but
still belongs to identifiable subsystems. Run all relevant test files, not the
entire application suite.

Backend examples:

- Public API route, response contract, middleware, authentication, or CORS.
- NASA transport, validation, caching, backoff, stale-data, or rate limiting.
- Clustering semantics, historical identity, BigQuery SQL, schema, or migration.
- A refactor spanning two or more backend boundaries.

Frontend examples:

- Shared request, cache, identity, App Check, or freshness behavior.
- Layer/window/refresh orchestration or broad state-management changes.
- A refactor spanning several frontend features.

Example commands:

```powershell
# From backend/
.\.venv\Scripts\python.exe -m unittest test_main test_nasa_client test_fire_data_validation -v
```

```bash
# From frontend/
node --test src/services/fireApi.test.js src/services/cacheStorage.test.js
npm run test:components
npm run lint
```

Select files from the inventory below. Add `npm run build` only when frontend
bundling or build configuration is affected.

### Level 4: Full Validation

Run a complete application suite only for very important changes:

- A release candidate or production deployment.
- Completion of a milestone.
- A coordinated API contract and frontend consumer change.
- Fundamental security, privacy, availability, or data-model changes.
- Changes to CI, runtime versions, deployment architecture, or shared release
  assumptions where both artifacts must be proven together.

Use `python -m unittest discover -v` for the complete backend and `npm test`,
`npm run lint`, and `npm run build` for the complete frontend. Run `npm run
test:e2e` as well when a milestone or acceptance criterion changes a browser
interaction or keyboard flow. Run only the
affected application's full suite for an application-specific critical change;
run both for cross-application work, milestones, and releases. A production
frontend release also runs `npm run build:production` with the approved public
configuration.

For a pull request requiring Level 4, add the `full-validation` label or start
`.github/workflows/full-validation.yml` manually. The hosted workflow runs both
applications because it is reserved for these exceptional changes.

## Test Inventory

### Backend

| Test module | Classification | Run when |
| --- | --- | --- |
| `test_main.py` | API, cache, availability | Relevant endpoint/cache test for local fixes; full file for broad public-data changes |
| `test_nasa_client.py` | External transport boundary | NASA HTTP, timeout, content, or payload-limit changes |
| `test_fire_data_validation.py` | Data validation and quality | NASA schema, normalization, deduplication, or quality changes |
| `test_incident_clustering.py` | Domain algorithm | Cluster distance, time, FRP, envelope, trend, or response changes |
| `test_rate_limit.py` | Security and abuse protection | Client identity, App Check, Firestore bucket, or fallback changes |
| `test_logging.py` | Privacy and HTTP logging | Logging, redaction, request IDs, rotation, or CORS changes |
| `test_historical_ingest.py` | Persistence and Scheduler | Historical IDs, ingestion, Scheduler auth, BigQuery SQL/schema/migration changes |

`run_smoke_tests.py` selects representative tests across these boundaries. It is
not a replacement for the relevant test file when changing a boundary itself.

### Frontend

| Test module | Classification | Run when |
| --- | --- | --- |
| `config/fireConfig.test.js` | API and map configuration | API URL, environment, windows, or map configuration changes |
| `config/firebaseConfig.test.js` | App Check configuration | Firebase or production attestation changes |
| `domain/incidentPresentation.test.js` | Cluster presentation | Cluster area visibility or incident presentation changes |
| `domain/firePresentation.test.js` | Detection presentation | Detection time, location, FRP, or confidence presentation changes |
| `services/cacheStorage.test.js` | Browser persistence | Cache version, key, TTL, serialization, or storage behavior changes |
| `services/clientIdentity.test.js` | Anonymous identity | Installation UUID generation or persistence changes |
| `services/fireApi.test.js` | HTTP contract | URLs, headers, freshness, errors, or response handling changes |
| `services/requestSecurity.test.js` | Request security | Client ID, request ID, or App Check header changes |
| `components/*.component.test.jsx` | Component interaction and accessibility | Semantic UI, keyboard behavior, focus, map/list synchronization, or primary accessibility states |
| `e2e/*.spec.js` | Browser interaction | Critical keyboard, map, or cross-component browser flows |

## Escalation Rules

- Start narrow. Escalate if the focused test fails outside the changed unit, the
  root cause crosses another boundary, or the diff becomes broader than planned.
- A failing smoke test requires the relevant test file, not automatically
  both complete suites.
- A full suite is not evidence that an external integration works; use mocks in
  tests and separate reviewed smoke procedures for deployed services.
- Record which level and commands were run in the final change summary.
