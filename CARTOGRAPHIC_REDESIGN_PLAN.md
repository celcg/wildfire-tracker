# Cartographic Redesign Task Plan

**Status:** Implemented and verified locally on 2026-10-28, then revised to
restore the approved black-and-orange fire identity; not deployed.

## Goal

Replace the generic cyberpunk dashboard treatment with a map-first Iberian
thermal atlas whose hierarchy, language, and visual system are specific to
satellite fire detections.

## Design direction

- Use a warm black application shell around the dark map.
- Restore the original yellow-to-ember flame and orange gradient as the brand
  signature while keeping most operational surfaces restrained.
- Replace decorative HUD/radar elements with real freshness, source, and
  methodology information.
- Use Barlow/Barlow Condensed for a cartographic and wayfinding character;
  reserve tabular numerals for measured data.
- Use sentence case instead of repeated monospace uppercase eyebrow labels.
- Keep real detection geometry as the visual signature; add no stock or
  AI-generated imagery.

Core tokens after visual review:

- charcoal canvas `#090605`;
- burnt surface `#120B08`;
- warm text `#F8E5D6`;
- muted clay `#C5A89A`;
- ember `#FF4D21`;
- signal amber `#FF9418`.

All final combinations require contrast checks against the actual map tiles.

## Information architecture

1. Compact application header with source and data age.
2. Observation toolbar for window, layer, refresh, and request state.
3. Map as the primary desktop and mobile content.
4. Context panel for the selected detection or cluster.
5. Legend, freshness, source, and limitation note.
6. Search/filters and paginated records.
7. Methodology, privacy, attribution, and architecture links.

On desktop the map uses the main column and selection uses a narrower context
column. On mobile the map occupies roughly 56–60 viewport height and selection
opens below it. The map must be visible in the first viewport.

## Component changes

- Replace `frontend/src/components/Hero.jsx` with a compact `AppHeader.jsx`.
- Reshape `ControlDeck.jsx` into `ObservationToolbar.jsx`.
- Update `FireMap.jsx` and `MapStatus.jsx` with a stable loading shell, integrated
  legend, and responsive selection context.
- Present `DataExplorer.jsx` as rows/table rather than repeated cards and leave a
  clear slot for the pagination task.
- Consolidate `DataGuide.jsx` and `PrivacyNotice.jsx` into concise methodology
  and footer disclosures without hiding required privacy information.
- Reorder `App.jsx`; replace decorative global styles in `App.css`/`index.css`.
- Remove `useScrollReveal.js` if no remaining behavior needs it.
- Add `DESIGN.md` with tokens, type, spacing, motion, content, and accessibility
  rules.

## Content changes

Prefer factual copy such as:

> Near-real-time VIIRS thermal detections across the Iberian Peninsula.
> Detections are satellite observations, not confirmed fires.

Show NASA FIRMS, satellite/dataset, last observation, data age, stale state, and
the distinction between analytical envelopes and confirmed burned perimeters.
Remove generic phrases such as “environmental intelligence”.

## Motion and accessibility

Motion responds only to selection, map movement, refresh progress, or disclosure
state. Remove global scroll reveals and continuous radar effects. Preserve
reduced-motion, forced-colors, focus visibility, skip links, keyboard map/list
synchronization, semantic records, and axe checks.

## Delivery phases

1. Capture desktop/mobile baselines for loaded, loading, empty, stale, error,
   rate-limited, detection, and cluster states.
2. Define tokens and content rules in `DESIGN.md`.
3. Implement the compact header and map-first page structure.
4. Redesign toolbar, selected context, legend, records, and footer.
5. Validate responsive behavior and every existing request state.
6. Run accessibility tests, smoke tests, lint, build, and visual comparison.
7. Publish a Firebase preview only after separate authorization; merge and
   publish production only after user approval.

## Acceptance criteria

- A first-time visitor can locate the map, period, freshness, source, and data
  limitation within five seconds.
- The map appears in the first desktop and mobile viewport.
- Fire colors communicate data rather than decorate the whole interface.
- Loading and error states do not leave unexplained empty vertical space.
- Existing selection, refresh, clusters, privacy, and accessibility behavior is
  preserved.
- The result is recognizably a wildfire satellite tool, not a reusable generic
  analytics dashboard.

## Deferred

No UI framework, stock imagery, theme switcher, animation library, or backend
contract change is required for this redesign.
