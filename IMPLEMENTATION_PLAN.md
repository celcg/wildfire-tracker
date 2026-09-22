# Wildfire Tracker Implementation Plan

Last updated: 2026-09-22

## Purpose

This document is the implementation guide and living roadmap for Wildfire
Tracker. It translates the current project assessment into small, verifiable
tasks while preserving the system's security, availability, privacy, and data
interpretation contracts.

The plan is ordered deliberately. Stabilize the current baseline before adding
features, improve the core live-data experience before exposing historical
analytics, and measure performance before changing the clustering architecture.

## How To Maintain This Plan

A change is **major** when it adds or materially changes a user-visible feature,
API route or response, data model or migration, external integration, security
or privacy behavior, cache or availability behavior, deployment architecture,
or a milestone's scope.

Every major implementation change must update this file in the same change:

- Update `Current Focus` if the active work or blocker changed.
- Check completed tasks only after implementation and the proportionate
  verification described below are complete.
- Add newly discovered work to the appropriate milestone instead of leaving it
  only in an issue, commit message, or code comment.
- Update acceptance criteria when the agreed behavior changes.
- Record significant architectural or product decisions in `Decision Log`.
- Add one dated entry to `Plan Change Log` summarizing the plan update.
- Do not mark a milestone complete while any acceptance criterion is unmet.

Small fixes, dependency patches without behavior changes, comments, formatting,
and test-only refactors do not require a plan update unless they alter scope or
reveal new roadmap work.

## Proportionate Verification

`TESTING.md` is the source of truth for test classification, commands, and
escalation. Verification must use the narrowest justified level:

- Level 0, inspection only, for documentation and non-executable changes.
- Level 1, one focused test, for a localized minor fix.
- Level 2, the small smoke suites, for ordinary code changes and pull requests.
- Level 3, all relevant test files but not the complete suite, for important
  subsystem changes whose blast radius exceeds smoke coverage.
- Level 4, complete suites, only for very important changes, milestone
  completion, release candidates, and production releases; run both
  applications only when the scope crosses them.

A failing focused or smoke test first escalates to its relevant test file or
application, not automatically to every repository test. A task's explicit
verification section takes precedence. Record the level and commands used in
the final change summary.

## Status Legend

- `[ ]` Not started
- `[x]` Completed and verified
- `In progress` Work currently underway
- `Blocked` Cannot proceed until the stated dependency is resolved
- `Deferred` Intentionally moved out of the current roadmap

## Current Focus

**Next: Milestone 1, improve the core map experience.**

Milestone 0 is implemented and verified locally. NASA transport, validation,
SQL rendering, BigQuery persistence, and public response compatibility now have
aligned tests; clean backend and frontend installs pass their complete checks.
The initial GitHub workflow intentionally has no dependency cache. Enable caches
only after its first hosted run succeeds once the changes are committed.

Current risks carried into later milestones:

- NASA connect/read timeouts do not provide a strict end-to-end streaming
  deadline; Milestone 3 tracks that bounded-download improvement.
- BigQuery DDL must be rendered and reviewed for the configured project and
  dataset before execution; tests never execute external warehouse operations.
- `AGENTS.md` is intentionally local and ignored; this versioned plan remains
  the shared source of roadmap truth.

## Non-Negotiable Contracts

All milestones must preserve these constraints unless an explicit, reviewed
decision updates both the implementation and this plan.

- Public live-map reads must not depend on BigQuery availability.
- Cluster boundaries remain buffered observation envelopes, not confirmed fire
  incidents or measured burned-area perimeters.
- Existing public JSON shapes remain backward compatible unless a versioned
  migration is planned.
- `refresh=true` may bypass the browser cache but never the server-side NASA
  protection interval.
- Expired successful data remains available as stale data when NASA refreshes
  fail, and its approximate age stays visible in the frontend.
- Raw installation IDs, IP addresses, coordinates, payloads, secrets, and
  upstream exception messages or URLs must not enter logs.
- Tests must not consume NASA quota or write to Firestore or BigQuery.
- Historical ingestion continues to require fresh one-day data, authenticated
  Scheduler OIDC, idempotent hourly snapshots, relationship validation, bounded
  queries and payloads, and atomic writes.
- Wind-provider failure or quota exhaustion must never prevent live or stale
  fire observations from loading, and wind must not be presented as a fire-
  spread forecast.

## Milestone Overview

| Milestone | Outcome | Status |
| --- | --- | --- |
| 0. Stable baseline | Green, reproducible, automated validation | Completed locally |
| 1. Core map experience | Accessible, filterable, resilient live-data UI | Not started |
| 2. Historical intelligence | Useful trends without coupling the live map to BigQuery | Not started |
| 3. Performance and scale | Measured improvements to clustering, payloads, and rendering | Not started |
| 4. Wind context overlay | Current wind direction at each active focus without unbounded API traffic | Not started |
| 5. Production operations | Repeatable deployment, monitoring, and recovery | Not started |
| 6. GitHub Actions delivery | Keyless, guarded, independently deployable applications | Not started |

## Milestone 0: Stable Baseline

### 0.1 Finish The Active Backend Refactor

- [x] Inventory each modified and untracked backend file and define the intended
  final boundary between NASA transport, validation, SQL rendering, and the
  BigQuery repository.
- [x] Reconcile `test_historical_ingest.py` with the public helper boundary in
  `bigquery_sql.py`; remove stale imports or restore a single intentional API.
- [x] Update cache and failure tests to mock `nasa_client.fetch_nasa_csv` or the
  HTTP client at the correct boundary, never the real NASA endpoint.
- [x] Add focused NASA transport tests for timeout, invalid content type,
  response-size limit, malformed or empty CSV, and response cleanup.
- [x] Add focused validation tests for invalid coordinates, dates, acquisition
  times, finite numeric values, duplicates, row limits, and quality reporting.
- [x] Confirm SQL templates contain only expected identifier placeholders and
  all row values remain bound query parameters.
- [x] Confirm the BigQuery storage, payload, partition, relationship, and atomic
  merge safeguards still execute before writes.
- [x] Run `git diff --check` and review the complete diff without reverting
  unrelated worktree changes.

Verification:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -v
```

Acceptance criteria:

- The complete backend suite collects and passes.
- Tests perform no external NASA, Firestore, or BigQuery operations.
- The new module boundaries are reflected in tests and the root README.
- No secret-bearing URL or upstream error detail can reach logs or responses.

### 0.2 Automate Repository Validation

- [x] Add a pull-request workflow with independent backend and frontend jobs.
- [x] Install backend dependencies and run `unittest discover -v` from
  `backend/`.
- [x] Run `npm ci`, `npm test`, `npm run lint`, and `npm run build` from
  `frontend/`.
- [x] Ensure CI uses fake configuration and mocks so it cannot contact or write
  to production services.
- [x] Change the frontend test script to discover all `*.test.js` files rather
  than maintaining a hard-coded list.
- [x] Keep the initial workflow uncached; add dependency caching only after its
  first hosted run is green.
- [x] Document required branch protection checks in the deployment runbook.

Acceptance criteria:

- Every pull request automatically validates both applications.
- Adding a test file automatically includes it in the suite.
- CI failures identify the failing application and command clearly.

### 0.3 Make Builds Reproducible

- [x] Select and document supported Python and Node versions.
- [x] Pin direct Python dependencies and create a repeatable update procedure.
- [x] Confirm the committed npm lockfile is used through `npm ci`.
- [x] Decide between a Cloud Run source build and a Dockerfile; document the
  choice and remove contradictory container wording.
- [x] Define the production startup command, timeout, concurrency, and worker
  assumptions.
- [x] Add a backend `.env.example` containing non-secret placeholders for all
  supported settings.
- [x] Add `VITE_API_URL` to `frontend/.env.example`.
- [x] Replace the generic `frontend/README.md` with application-specific setup,
  verification, environment, and deployment guidance.

Acceptance criteria:

- A clean checkout can reproduce local installs and production builds using
  only documented commands.
- Required and optional configuration is discoverable without reading source.
- No example file contains a real secret or production credential.

## Milestone 1: Core Map Experience

### 1.1 Make Data States Explicit

- [ ] Decouple manual detection refresh from `/incidents`; refresh the active
  resource without making it depend on the inactive resource's success.
- [ ] Preserve the currently visible successful dataset when a refresh fails.
- [ ] Add a map loading state and expose `aria-busy` without hiding cached data.
- [ ] Add a zero-results state that names the selected observation window and
  clarifies that no satellite detections were returned.
- [ ] Distinguish offline, rate-limit, service, and malformed-response errors.
- [ ] Parse `Retry-After` and show a retry countdown for rate-limit or cold-cache
  backoff responses.
- [ ] Expose the sanitized request ID in error details for support correlation.
- [ ] Label retrieval time separately from source-data age.
- [ ] Decide whether valid cached data should revalidate in the background and
  document the request-volume tradeoff before implementation.

Tests:

- [ ] Test refresh success and failure independently for each layer.
- [ ] Test request cancellation and stale response races.
- [ ] Test empty, loading, stale, offline, rate-limited, and malformed states.
- [ ] Test that a failed refresh does not erase visible data.

Acceptance criteria:

- Every request state has visible and accessible feedback.
- The raw detection layer remains refreshable when clustering fails.
- Error handling does not disclose sensitive upstream details.

### 1.2 Add An Accessible Data Explorer

- [ ] Define the minimum list fields for detections and clusters: observed time,
  confidence, satellite, FRP, location, persistence, and trend where available.
- [ ] Add a semantic list or table beside or below the map with a mobile layout.
- [ ] Synchronize list selection with map pan, zoom, and popup focus.
- [ ] Provide a keyboard action to return from the map to the selected row.
- [ ] Give the map an accessible name and concise keyboard instructions.
- [ ] Add a skip link to the data explorer or main map content.
- [ ] Ensure selection, confidence, FRP, and trend never rely on color alone.
- [ ] Raise supporting text sizes that are too small for comfortable reading.
- [ ] Add forced-colors styles for controls, selections, and map-adjacent data.

Tests:

- [ ] Add component tests for keyboard selection and map/list synchronization.
- [ ] Add automated accessibility checks for the primary page states.
- [ ] Add a browser smoke test for keyboard-only detection exploration.

Acceptance criteria:

- All information available in a map popup is available without using the map.
- A keyboard user can select a result and understand its map context.
- The primary flow has no serious automated accessibility violations.

### 1.3 Add Filtering And Sorting

- [ ] Define filter semantics for confidence, minimum FRP, satellite, time, and
  cluster persistence or trend.
- [ ] Implement client-side filters first while response sizes remain bounded.
- [ ] Show total results and currently visible results separately.
- [ ] Add sorting by newest, highest FRP, confidence, and persistence where
  applicable.
- [ ] Keep map points, cluster summaries, and the data explorer consistent with
  the same filtered collection.
- [ ] Provide one action to clear all filters.
- [ ] Keep unknown FRP distinct from measured zero throughout filtering and
  summaries.

Tests:

- [ ] Test every filter independently and in combination.
- [ ] Test sorting without mutating cached API arrays.
- [ ] Test unknown and malformed optional values.

Acceptance criteria:

- Filtered counts and all visible representations agree.
- Filters remain usable on narrow screens and with a keyboard.
- No filter triggers an unnecessary NASA request.

### 1.4 Improve Navigation And Sharing

- [ ] Add reset-to-Iberia and fit-to-results controls.
- [ ] Add place or coordinate search using a documented provider and usage
  policy; do not ship a third-party service without a privacy review.
- [ ] Treat browser geolocation as optional and explain permission use before
  requesting it.
- [ ] Encode observation window, layer, filters, center, zoom, and selected item
  in URL parameters.
- [ ] Restore valid shared state on load and ignore malformed parameters safely.
- [ ] Keep URL updates out of the browser history during continuous map motion.

Acceptance criteria:

- A shared URL reconstructs the same useful map view.
- Declining geolocation does not degrade the rest of the application.
- Navigation controls work on desktop, mobile, and keyboard-only flows.

## Milestone 2: Historical Intelligence

Historical features must degrade independently. A BigQuery outage may disable
history panels, but it must not prevent `/fires`, `/stats`, or `/incidents` from
serving live or stale cached NASA data.

### 2.1 Define The Historical Product Contract

- [ ] Choose the first user question to answer; recommended: compare the latest
  24 hours with the preceding 24 hours for a selected region.
- [ ] Define bounded date ranges, geographic resolution, aggregation intervals,
  and maximum response sizes.
- [ ] Document that historical clusters are analytical observation groupings,
  not confirmed events, burned areas, or forecasts.
- [ ] Decide public access, App Check, installation identity, and rate-limit
  behavior before adding routes.
- [ ] Define response models and example payloads before repository queries.

Acceptance criteria:

- API and UX contracts can be reviewed without implementation details.
- Cost and response-size limits are explicit.
- Live-map availability remains independent by design.

### 2.2 Add Bounded Historical APIs

- [ ] Add a dedicated historical repository method with partition filters,
  parameterized values, and maximum bytes billed.
- [ ] Add a service boundary that converts warehouse rows into typed domain
  responses.
- [ ] Add an explicit Pydantic response model and sanitized error handling.
- [ ] Add one historical route without changing existing route shapes.
- [ ] Return cache metadata suitable for client caching without exposing
  internal table details.
- [ ] Test date bounds, empty results, cost guards, malformed warehouse rows,
  and BigQuery outages.

Acceptance criteria:

- Queries cannot omit partition filters or exceed configured scan limits.
- Historical failures never affect public live-data endpoints.
- OpenAPI accurately describes the historical response.

### 2.3 Add Historical User Features

- [ ] Add a latest-versus-previous-24-hours comparison.
- [ ] Add “new since last visit” using a local timestamp with clear limitations.
- [ ] Add cluster persistence and FRP trend charts with accessible text values.
- [ ] Add bounded timeline playback only after static trends are validated.
- [ ] Keep uncertainty and non-forecast language adjacent to each visualization.
- [ ] Cache historical responses separately by query dimensions and version.

Acceptance criteria:

- Historical panels have useful empty, loading, stale, and unavailable states.
- Charts have equivalent text or tabular representations.
- No historical interaction causes a live-map request waterfall.

### 2.4 Review Cluster Calculation And Database Storage

Treat the current cluster lifecycle as a known design risk to review before
building user-facing history on top of it. The review must cover both the live
clustering algorithm and the historical identity/storage model rather than
optimizing either side in isolation.

- [ ] Trace one detection from NASA normalization through live clustering,
  historical ID assignment, BigQuery parameters, SQL merge, and later reads.
- [ ] Document the difference between the source-derived live incident ID and
  the historical cluster ID that survives repeated hourly snapshots.
- [ ] Verify identity behavior for retries, late-arriving detections, expanding
  clusters, split components, bridge detections, and merges between previously
  independent clusters.
- [ ] Review whether transitive single-linkage can create clusters whose total
  spatial span or lifetime is misleading despite every pairwise edge satisfying
  the configured thresholds.
- [ ] Quantify the CPU cost of recalculating the rolling 24-hour window every
  hour and identify repeated work that can be reused safely.
- [ ] Quantify BigQuery growth from hourly full cluster snapshots, repeated
  member-ID arrays, one-member clusters, boundaries, and detection-to-latest-
  snapshot references for the full retention period.
- [ ] Verify partition pruning, expiration, idempotent retries, atomicity,
  relationship validation, and storage-guard behavior against realistic and
  worst-case batches.
- [ ] Evaluate whether the current two-table snapshot model is sufficient or
  whether cluster membership, lineage, or merge/split events require a separate
  normalized table.
- [ ] Check that corrections or late data cannot leave detections pointing to a
  missing, obsolete, or semantically unrelated cluster snapshot.
- [ ] Define invariants for cluster IDs, snapshot keys, member uniqueness,
  lineage, temporal ordering, and boundary validity.
- [ ] Produce a short decision record that keeps the current model or proposes a
  migration, including query cost, storage cost, rollback, and compatibility.
- [ ] Add deterministic tests for every accepted merge, split, retry, and
  late-arrival invariant before changing production persistence.

Acceptance criteria:

- The project has measured estimates for clustering compute and one year of
  cluster storage at typical and configured maximum volumes.
- Cluster identity and lineage behavior are explicit for retries, expansion,
  merges, splits, and late data.
- Every detection-to-snapshot relationship remains valid after an atomic write.
- Any schema change has a bounded migration and rollback plan before execution.
- User-facing historical work does not rely on an unresolved cluster invariant.

## Milestone 3: Performance And Scale

### 3.1 Establish Measurements

- [ ] Record representative detection counts for each observation window.
- [ ] Benchmark NASA normalization, clustering, JSON serialization, response
  size, and frontend rendering separately.
- [ ] Add a deterministic synthetic dataset for repeatable benchmarks.
- [ ] Define budgets for API latency, response size, map interaction, and memory.
- [ ] Profile before choosing spatial indexing or rendering technology.

Acceptance criteria:

- Optimization work cites a reproducible baseline and target.
- Synthetic benchmark data contains no real visitor or secret data.

### 3.2 Reduce Backend Work

- [ ] Cache incident derivations with the corresponding immutable fire snapshot.
- [ ] Replace the global refresh lock with per-`days` coordination while
  preserving same-key request coalescing.
- [ ] Add explicit response models for `/fires` and `/stats`.
- [ ] Evaluate time buckets plus a spatial grid or tree to reduce clustering's
  worst-case pair comparisons.
- [ ] Preserve transitive clustering semantics or document and test an approved
  behavior change.
- [ ] Add cluster spatial-span and duration diagnostics for chained components.
- [ ] Add server-side bounding-box and filters only when measurements show the
  client-side approach is insufficient.
- [ ] Evaluate ETag and response compression after payload measurement.

Acceptance criteria:

- Incident requests do not recompute unchanged snapshots.
- Different day-window misses no longer block one another unnecessarily.
- Clustering results remain deterministic and explainable.

### 3.3 Scale Frontend Rendering

- [ ] Switch raw point rendering to Leaflet canvas as the lowest-complexity
  improvement and measure it.
- [ ] Add viewport-aware rendering if canvas alone misses the interaction budget.
- [ ] Evaluate low-zoom aggregation without hiding source detections at useful
  zoom levels.
- [ ] Consider WebGL only if measured volume still exceeds the defined budget.
- [ ] Keep list/table access complete even when map points are aggregated.

Acceptance criteria:

- Pan, zoom, selection, and layer changes meet the agreed performance budget on
  a representative mobile device.
- Rendering optimizations do not change data counts or accessibility behavior.

### 3.4 Coordinate Upstream Access Across Instances

- [ ] Add a true end-to-end NASA download deadline; Requests' read timeout only
  bounds socket inactivity and does not cap a continuously streaming response.
- [ ] Measure duplicate NASA requests caused by Cloud Run cold starts and
  scale-out before introducing shared coordination.
- [ ] Compare Firestore, object storage, scheduled snapshots, and Redis on cost,
  complexity, latency, and failure behavior.
- [ ] Preserve process-local stale fallback even if shared coordination fails.
- [ ] Document ownership, expiry, and recovery for any shared snapshot or lock.

Acceptance criteria:

- The selected design demonstrably reduces duplicate upstream requests.
- A shared-service outage does not empty an instance that has successful data.

## Milestone 4: Wind Context Overlay

The map will show current wind direction for every active focus. Here, an
“active focus” must be defined explicitly before implementation: the recommended
default is one representative coordinate per possible active cluster, with
isolated detections treated as one-member focuses. Resolving every focus must not
be implemented as unbounded browser-side requests. The backend may batch,
deduplicate, or spatially coalesce provider calls while preserving a result for
each displayed focus.

Wind is contextual weather data, not a fire-spread prediction. The interface
must not imply that the arrow forecasts the direction or speed of propagation.

### 4.1 Define The Wind Data Contract

- [ ] Confirm the exact definition of an active focus and how its representative
  coordinate is chosen consistently between raw detections and cluster views.
- [ ] Evaluate weather providers for Iberian coverage, update frequency, spatial
  resolution, batch-coordinate support, availability, pricing, quotas, license,
  attribution, and production terms.
- [ ] Decide whether the provider is queried once per exact coordinate, through
  a supported batch request, or through deduplicated spatial cells; every active
  focus still needs a mapped wind result or an explicit unavailable state.
- [ ] Define the maximum focuses and outbound provider calls allowed per user
  request and the behavior when a dataset exceeds that limit.
- [ ] Define “current” using the provider observation/model timestamp, cache age,
  and a maximum acceptable stale interval rather than browser retrieval time.
- [ ] Specify wind speed units and the meteorological direction convention.
  Document whether the rendered arrow points toward movement while the numeric
  bearing reports the direction the wind comes from.
- [ ] Define a typed response containing focus identity, sampled coordinate,
  speed, direction, provider timestamp, freshness, and availability without
  changing existing fire or incident response shapes.
- [ ] Complete privacy and threat review for sending fire coordinates to the
  selected provider and document attribution requirements.

Acceptance criteria:

- Provider choice, quota budget, coordinate strategy, attribution, and failure
  behavior are documented before integration begins.
- Direction semantics are unambiguous in the API and UI specification.
- The design has a strict upper bound on outbound calls and response size.

### 4.2 Build The Backend Wind Integration

- [ ] Add a dedicated provider client with validated coordinates, strict connect
  and read timeouts, response-size limits, schema validation, and sanitized
  errors that never expose provider credentials or URLs.
- [ ] Keep provider credentials server-side; never expose them through `VITE_*`
  variables, frontend bundles, logs, or API errors.
- [ ] Add a service that accepts all active focus coordinates, deduplicates
  identical or approved nearby samples, and maps results back to every focus ID.
- [ ] Use provider-supported batching where available; otherwise use bounded
  concurrency instead of launching one unrestricted request per coordinate.
- [ ] Add a versioned TTL cache keyed by the approved spatial resolution and
  provider time window so nearby focuses and concurrent clients reuse data.
- [ ] Coalesce concurrent cache misses and add provider retry backoff or a circuit
  breaker that does not block `/fires`, `/stats`, or `/incidents`.
- [ ] Return partial results when only some coordinates resolve, with per-focus
  unavailable status instead of failing the entire map.
- [ ] Add a separate authenticated and rate-limited wind route so existing public
  response contracts remain backward compatible.
- [ ] Derive or validate requested focus coordinates against the backend's cached
  fire snapshot so the route cannot become an arbitrary weather-proxy endpoint.
- [ ] Add global request-budget protection to prevent UUID rotation or Cloud Run
  scale-out from multiplying paid or quota-limited weather calls.
- [ ] Log only aggregate counts, cache outcomes, latency, and sanitized provider
  status; do not log coordinates or full payloads.

Tests:

- [ ] Test coordinate validation, provider schema errors, timeout, oversized
  response, partial success, and stale-cache fallback.
- [ ] Test coordinate deduplication, batch splitting, bounded concurrency,
  request-budget exhaustion, and concurrent miss coalescing.
- [ ] Test direction conversion at north, east, south, west, and wrap-around.
- [ ] Ensure tests use recorded synthetic fixtures or mocks and never call the
  live weather provider.

Acceptance criteria:

- Every accepted focus receives current, stale, or explicitly unavailable wind
  state without an unbounded N+1 request pattern.
- Weather-provider failure never prevents live or stale fire data from loading.
- Cache, batching, and request budgets keep usage inside the provider quota.
- No provider secret, coordinate, or payload enters logs or frontend artifacts.

### 4.3 Render Wind At Each Active Focus

- [ ] Add an explicit wind overlay toggle and load wind only when requested or
  when the approved product behavior requires it.
- [ ] Render a directional marker at each active focus using the agreed
  direction convention and scale or label speed without obscuring fire markers.
- [ ] Keep wind markers associated with stable focus IDs during refreshes and
  layer changes.
- [ ] Show speed, direction, provider timestamp, freshness, and attribution in
  the focus details and accessible data explorer.
- [ ] Add a legend explaining arrow direction, units, timestamp, and that wind
  does not predict fire spread.
- [ ] Distinguish loading, stale, partial, unavailable, and quota-limited wind
  states without clearing fire observations.
- [ ] Declutter arrows at low zoom while retaining complete non-map data access.
- [ ] Support keyboard navigation, screen readers, forced colors, reduced motion,
  desktop, and mobile layouts.

Tests:

- [ ] Test one wind result is associated with each active focus and that stale
  responses cannot attach to a newer focus collection.
- [ ] Test toggle, loading, partial, stale, unavailable, and retry states.
- [ ] Add visual and accessibility tests for arrow orientation, legend text, and
  overlap at representative focus counts.

Acceptance criteria:

- Users can inspect current wind direction, speed, and timestamp at every active
  focus with available data.
- Wind remains legible without hiding detections or cluster envelopes.
- The UI clearly states that displayed wind is context, not spread prediction.
- Disabling or failing the overlay has no effect on core map availability.

### 4.4 Validate Cost, Freshness, And Load

- [ ] Load-test typical and maximum focus counts against the mocked provider.
- [ ] Measure cache hit rate, calls per map refresh, response latency, payload
  size, and frontend render cost.
- [ ] Calculate expected daily and peak provider usage across projected traffic
  and Cloud Run instances.
- [ ] Confirm cache TTL and spatial deduplication do not present materially wrong
  wind for separated focuses or beyond the accepted freshness window.
- [ ] Add privacy-safe metrics and alerts for provider errors, quota pressure,
  stale age, and request-budget rejection.
- [ ] Document provider outage, quota exhaustion, key rotation, and provider
  replacement procedures.

Acceptance criteria:

- Measured usage remains within the documented quota and cost budget.
- Maximum supported focus counts meet the agreed API and rendering budgets.
- Operators can detect stale or unavailable wind without inspecting user data.

## Milestone 5: Production Operations

### 5.1 Add Observability

- [ ] Define service indicators for API latency, 5xx responses, stale serves,
  NASA failures, wind-provider failures, rate-limit rejections, clustering time,
  and ingestion outcomes.
- [ ] Add privacy-safe structured metrics or log-based metrics without IDs,
  coordinates, payloads, or secrets.
- [ ] Add uptime checks for the frontend and API liveness endpoint.
- [ ] Add alerts for sustained API errors, excessive data age, Scheduler
  failures, wind quota pressure, BigQuery storage guard events, and Firestore
  quota pressure.
- [ ] Add a readiness endpoint that validates configuration without consuming
  NASA quota or requiring all optional integrations.
- [ ] Document alert owners and first-response actions.

Acceptance criteria:

- Operators can detect stale data, failed ingestion, and public outages without
  manually inspecting logs.
- Alerts contain enough request-safe context to start diagnosis.

### 5.2 Capture Infrastructure And Delivery

- [ ] Select an infrastructure-as-code tool compatible with the current GCP and
  Firebase deployment.
- [ ] Define Cloud Run configuration, service accounts, IAM, Secret Manager
  bindings including any wind-provider credential, Firestore policy, BigQuery
  dataset/tables, and Scheduler job.
- [ ] Parameterize project, region, dataset, service account, and audience values.
- [x] Remove the hard-coded project ID from reusable BigQuery schema setup.
- [ ] Add preview or staging deployment support before automatic production
  deployment.
- [ ] Add explicit approval and post-deploy smoke checks for production.
- [ ] Keep schema migration order separate from application rollout when needed.

Acceptance criteria:

- A new environment can be provisioned from reviewed configuration.
- Production deployment and rollback do not depend on undocumented console work.

### 5.3 Add Runbooks And Hosting Hardening

- [ ] Document deployment, smoke testing, rollback, Scheduler recovery, schema
  migration, weather-provider recovery, secret rotation, and incident response.
- [ ] Configure Firestore TTL for expired rate-limit documents and document how
  to verify it.
- [ ] Add Firebase Hosting security headers: CSP, frame protection, referrer
  policy, permissions policy, and content-type protection.
- [ ] Add immutable caching for hashed assets and safe revalidation for HTML.
- [ ] Add deployed end-to-end smoke tests for map load, layer switch, stale-data
  behavior, and App Check.
- [ ] Add `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, and release notes or a
  changelog if the repository is intended for external contributors.
- [ ] Align package and release versioning or explicitly document why they differ.

Acceptance criteria:

- A maintainer unfamiliar with the deployment can release and roll back safely.
- Hosting headers are validated against the deployed site.
- Security reporting and support paths are explicit.

## Milestone 6: GitHub Actions Delivery Automation

This is the final roadmap step. Pull-request validation begins in Milestone 0,
but production deployment automation waits until environments, monitoring,
smoke tests, rollback procedures, and infrastructure ownership are established.
The frontend and backend remain independently deployable.

### 6.1 Establish GitHub And Runtime Prerequisites

- [ ] Confirm `main` is protected and requires the independent backend and
  frontend checks introduced in Milestone 0 before merge.
- [ ] Create a protected GitHub `production` environment that accepts deployments
  only from `main`; decide whether a required reviewer is appropriate.
- [ ] Store project IDs, region, service names, API URL, and public Firebase web
  configuration as GitHub environment variables, not source-code secrets.
- [ ] Keep `NASA_KEY`, the client-ID HMAC secret, and other server credentials in
  Google Secret Manager; do not copy them into GitHub.
- [ ] Standardize CI and deployment on the supported Python and Node versions
  selected in Milestone 0.
- [ ] Pin third-party actions to reviewed commit SHAs and pin the Firebase CLI in
  `frontend/package-lock.json`.
- [ ] Document the required checks and environment protection in the deployment
  runbook because GitHub repository settings are not represented by workflow
  files.

Acceptance criteria:

- Direct changes cannot bypass the required backend and frontend checks on
  `main`.
- Production configuration is clearly classified as public build configuration,
  GitHub metadata, or a runtime secret.
- No long-lived Google service-account key exists in GitHub.

### 6.2 Configure Keyless Google Cloud Authentication

- [ ] Enable the IAM Credentials, Security Token Service, Cloud Run, Cloud Build,
  Artifact Registry, and Firebase Hosting APIs required by delivery workflows.
- [ ] Create a Workload Identity Pool and GitHub OIDC provider restricted to
  `celcg/wildfire-tracker` and `refs/heads/main`.
- [ ] Create separate least-privilege deployment service accounts for Cloud Run
  and Firebase Hosting.
- [ ] Grant the Cloud Run principal only the source-deployment, service-usage,
  and runtime-service-account impersonation permissions it requires; grant the
  Cloud Build identity its builder role separately.
- [ ] Grant the Firebase principal only Firebase Hosting deployment and required
  service-usage permissions.
- [ ] Bind both service accounts to the repository identity with
  `roles/iam.workloadIdentityUser`.
- [ ] Record the provider resource name and service-account email addresses as
  GitHub `production` environment variables.
- [ ] Validate the trust condition and effective IAM permissions before enabling
  an automatic production trigger.

Acceptance criteria:

- GitHub exchanges its OIDC token for short-lived Google credentials.
- Pull requests, forks, other repositories, and non-`main` refs cannot obtain
  production deployment credentials.
- Neither workflow requires a downloaded service-account JSON key.

### 6.3 Add The Backend Deployment Workflow

- [ ] Add `.github/workflows/deploy-backend.yml`, triggered by a push to `main`
  affecting `backend/**`, changes to its own workflow, or a manual dispatch.
- [ ] Give the job only `contents: read` and `id-token: write` permissions and
  attach it to the protected `production` environment.
- [ ] Use a non-cancelling production concurrency group so two backend releases
  cannot race or interrupt one another.
- [ ] Install backend dependencies and rerun the complete mocked unit suite in
  the deployment job.
- [ ] Authenticate through `google-github-actions/auth` and deploy `backend/` to
  the existing `wildfire-api` service in `europe-west1` using the documented
  Cloud Run source-build strategy.
- [ ] Do not pass broad `--set-env-vars` or `--set-secrets` flags that could
  replace the service's existing Secret Manager, BigQuery, Firestore, Scheduler,
  App Check, or logging configuration.
- [ ] Read the deployed service URL from Cloud Run and run a retrying HTTP check
  against the lightweight `/` endpoint without consuming NASA quota.
- [ ] Retain enough workflow and Cloud Run revision metadata to connect a Git
  commit to the deployed revision.

Acceptance criteria:

- A backend-only merge validates and deploys only the backend application.
- Failed tests, authentication, source builds, deployments, or smoke checks make
  the workflow fail visibly.
- Deployment preserves the existing runtime identity, secrets, environment, and
  public access policy.
- The post-deploy check performs no NASA, Firestore, or BigQuery operation.

### 6.4 Add The Frontend Deployment Workflow

- [ ] Add `.github/workflows/deploy-frontend.yml`, triggered by a push to `main`
  affecting `frontend/**`, changes to its own workflow, or a manual dispatch.
- [ ] Give the job only `contents: read` and `id-token: write` permissions and
  attach it to the protected `production` environment.
- [ ] Use a non-cancelling production concurrency group so Firebase releases do
  not race.
- [ ] Run `npm ci`, `npm test`, `npm run lint`, and `npm run build` before
  authentication or deployment.
- [ ] Supply `VITE_API_URL` and the public Firebase/App Check values from the
  GitHub environment during the production build; never supply a server secret
  through a `VITE_*` variable.
- [ ] Authenticate through GitHub OIDC and deploy only Firebase Hosting with the
  lockfile-pinned Firebase CLI.
- [ ] Run a retrying HTTP check against the canonical Firebase Hosting URL after
  deployment.
- [ ] Do not add pull-request preview channels until their domains have an
  explicit CORS, App Check, privacy, expiry, and cleanup design.

Acceptance criteria:

- A frontend-only merge validates and deploys only the frontend application.
- The deployed bundle has App Check enabled with the intended production values.
- The canonical hosting URL serves the new release after the workflow succeeds.
- No workflow log or frontend artifact contains a server-side secret.

### 6.5 Exercise Deployment And Recovery

- [ ] Open a test pull request and confirm the required backend and frontend jobs
  report failures independently and block merge when either application fails.
- [ ] Merge isolated backend and frontend changes and confirm path filters launch
  only the corresponding deployment workflow.
- [ ] Confirm production environment approval, concurrency, OIDC trust, and
  least-privilege failures behave as documented.
- [ ] Verify Cloud Run revision health, Firebase release health, App Check, CORS,
  Scheduler ingestion, Firestore limiting, and BigQuery ingestion after a
  representative release without making tests call live dependencies.
- [ ] Perform a controlled Cloud Run traffic rollback to a prior healthy revision
  and a Firebase Hosting rollback using the documented runbook.
- [ ] Reapply the current release after each rollback exercise and record the
  evidence and recovery time.
- [ ] Add deployment-failure notifications only after their owner and response
  expectations are documented.

Acceptance criteria:

- A maintainer can trace, approve, deploy, verify, and roll back either
  application without undocumented credentials or console-only knowledge.
- A failed release does not overwrite the other application's deployment.
- Rollback procedures have been executed successfully, not merely documented.
- Automatic production delivery is enabled only after all Milestone 6 checks
  pass.

## Deferred Ideas

These ideas are intentionally outside the ordered milestones until usage or
research justifies them.

- Installable PWA and offline map shell, subject to tile-provider cache policy.
- Notifications or alerts, which require careful false-positive, consent,
  location-privacy, and emergency-information design.
- Vegetation, precipitation, temperature, or official incident overlays, which
  require source licensing, timestamp alignment, and clear authority boundaries.
- Predictive spread modeling. This must not be presented as a forecast without
  validated models, domain review, uncertainty communication, and operations.
- Native mobile applications while the responsive web experience remains
  sufficient.

## Decision Log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-09-22 | Stabilization precedes feature work. | The active refactor and stale tests prevent a trustworthy baseline. |
| 2026-09-22 | Accessible map-equivalent data is the first major product feature. | It improves accessibility, mobile use, exploration, and testability together. |
| 2026-09-22 | Historical features remain independent of live map reads. | BigQuery must not become an availability dependency for current detections. |
| 2026-09-22 | Performance changes require measurements first. | The smallest proven optimization is preferable to premature infrastructure. |
| 2026-09-22 | Cluster computation and historical storage require an explicit invariant and cost review before historical UI work depends on them. | Repeated rolling calculations, merges and splits, and hourly snapshots can create correctness, compute, and storage risks that are difficult to repair after exposure. |
| 2026-09-22 | Wind is a separate, failure-isolated context overlay resolved for every active focus through a bounded backend integration. | A direct unbounded browser request per coordinate would expose provider concerns and create quota, cost, privacy, and availability risks. |
| 2026-09-22 | Production delivery uses GitHub OIDC and separate deployment identities. | Short-lived credentials and independent least-privilege access avoid stored service-account keys and reduce deployment blast radius. |
| 2026-09-22 | Automatic production deployment is the final roadmap milestone. | Delivery automation should rely on established branch checks, reproducible builds, staging, observability, smoke tests, and proven rollback procedures. |
| 2026-09-22 | Cloud Run continues to use source builds with one Uvicorn worker. | This preserves the current deployment model and avoids duplicating process-local NASA cache and coordination state. |
| 2026-09-22 | The first validation workflow ships without dependency caching. | A hosted uncached run must establish the baseline before cache behavior is introduced. |
| 2026-09-22 | Ordinary changes run small smoke suites; most tests are reserved for very important changes. | Proportionate verification keeps minor work fast while retaining full validation for high-blast-radius changes and releases. |

## Plan Change Log

| Date | Change |
| --- | --- |
| 2026-09-22 | Created the milestone-based implementation plan from the project assessment. |
| 2026-09-22 | Added proportionate verification rules so minor fixes do not require full test suites. |
| 2026-09-22 | Added the final GitHub Actions delivery milestone covering protected environments, keyless Google authentication, independent deployments, verification, and rollback exercises. |
| 2026-09-22 | Added a cluster calculation and BigQuery storage review, plus a wind-at-each-active-focus milestone before production operations; renumbered later milestones. |
| 2026-09-22 | Completed Milestone 0 locally: stabilized NASA and BigQuery boundaries, added focused tests and CI, pinned runtimes and dependency locks, validated production configuration, and documented builds and deployment. |
| 2026-09-22 | Classified verification into five levels, changed default CI to smoke validation, and added label/manual full-validation workflows for very important changes. |
