# Detection Loading Performance Task Plan

## Goal

Reduce the time until useful detections are visible without weakening cache,
NASA protection, validation, stale-if-error behavior, or rate limiting.

## Investigation first

Instrument the existing request path before selecting an optimization:

1. Measure browser-cache lookup, App Check token acquisition, HTTP time to first
   byte, download, JSON parsing, React transformation, and Leaflet rendering.
2. Add aggregate backend timings for rate limiting, backend-cache lookup, NASA
   fetch, validation, clustering, and serialization. Do not log coordinates,
   identifiers, payloads, secrets, or upstream URLs.
3. Capture cold and warm results for 1, 3, 5, and 10 days, including response
   bytes and detection counts.
4. Reproduce Cloud Run cold start, browser-cache hit, backend-cache hit, fresh
   NASA fetch, stale fallback, and NASA failure separately.

## Likely fixes, applied only when supported by measurements

1. Show a valid browser-cached snapshot immediately; preserve the current
   explicit-refresh policy instead of adding background NASA traffic.
2. Prevent duplicate frontend work and requests during React development or
   rapid state changes using the existing request lifecycle boundary.
3. Cache incident derivations with the immutable backend fire snapshot so an
   unchanged `/incidents` request does not recluster the same data.
4. Use Leaflet canvas for raw detections if marker creation dominates rendering.
5. Add HTTP compression or ETag support only if transfer size is material.
6. Add server-side filters or bounding boxes only if bounded client responses
   still exceed the agreed payload and interaction budgets.

## Files likely involved

- `frontend/src/hooks/useFireData.js`
- `frontend/src/hooks/useIncidentData.js`
- `frontend/src/services/fireApi.js`
- `frontend/src/services/requestLifecycle.js`
- `frontend/src/components/FireMap.jsx`
- `backend/main.py`
- `backend/fire_data.py`
- `backend/nasa_client.py`
- `backend/incident_clustering.py`
- focused frontend and backend tests for whichever bottleneck is confirmed

## Performance budgets to establish

- Valid browser cache: useful records visible without a network dependency.
- Warm backend cache: API response target based on measured production baseline.
- Map interaction: no visible input stall on a representative mobile device.
- Payload and memory: explicit limits per supported observation window.

Numbers are deliberately not invented in advance; the baseline determines
realistic targets and prevents optimizing the wrong layer.

## Verification

- Use deterministic synthetic detections; benchmarks must not call NASA.
- Compare before/after medians and a slow-percentile sample for each state.
- Confirm data counts, cluster membership, freshness headers, and cache behavior
  are unchanged.
- Run the relevant subsystem tests, frontend lint, and build.

## Acceptance criteria

- The dominant delay is demonstrated with reproducible measurements.
- The selected change improves that stage without increasing NASA request rate.
- Loading, stale, empty, rate-limited, and error states remain explicit.
- No performance telemetry contains visitor or fire-location data.
