# Explorer Pagination Task Plan

**Status:** Implemented and verified locally on 2026-10-28; not deployed.

## Goal

Keep the detection and cluster explorer usable when an API response contains
hundreds or thousands of records, without changing the map dataset or issuing
additional NASA requests.

## Scope

The first version uses client-side pagination because the frontend already has
the complete, bounded API response. Pagination changes only the records rendered
in the explorer; map points, aggregate counts, selection, filters, and cached
responses continue to use the full collection.

## Implementation

1. Add a pure pagination helper in `frontend/src/domain/` that clamps invalid
   page numbers and returns the current slice and page metadata.
2. Update `frontend/src/components/DataExplorer.jsx` to render 25 rows per page
   with Previous/Next controls and a compact `Page X of Y` status.
3. Reset to page 1 when the observation window, layer, or active filters change.
4. If a selected item is outside the current page, move to its page before
   returning keyboard focus from the map.
5. Keep total results and visible results distinct. An empty filtered result has
   no pagination controls.
6. On mobile, use Previous/Next rather than a long list of numbered buttons.

## Files

- `frontend/src/components/DataExplorer.jsx`
- `frontend/src/components/DataExplorer.component.test.jsx`
- `frontend/src/domain/explorerPagination.js` (new)
- `frontend/src/domain/explorerPagination.test.js` (new)
- `frontend/src/App.css`

## Verification

- Test zero, one, exactly 25, and more than 25 records.
- Test the last partial page and page clamping after data changes.
- Test map-to-list focus when the selected record is on another page.
- Test keyboard labels, disabled controls, narrow layout, and forced colors.
- Run the frontend smoke tests, lint, and production build.

## Acceptance criteria

- No explorer page renders more than 25 data rows.
- Pagination does not trigger an API or NASA request.
- Map counts and results totals still describe the full filtered collection.
- Selection and keyboard focus remain synchronized across page changes.

## Deferred

Server-side pagination remains deferred until measurements show that API payload
size, rather than DOM rendering, is the actual bottleneck.
