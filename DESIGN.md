# Wildfire Atlas Design System

## Product character

Wildfire Tracker is an operational cartographic tool for exploring NASA FIRMS
VIIRS thermal observations across the Iberian Peninsula. The map and its real
data are the functional focus. Its identity comes from a warm black field, a
thermal flame, and an amber-to-ember spectrum. Decoration must never imitate
telemetry or imply scientific certainty that the data does not provide.

## Color

| Token | Value | Purpose |
| --- | --- | --- |
| Charcoal canvas | `#090605` | Warm black application background |
| Burnt surface | `#120B08` | Controls and records |
| Raised surface | `#1A0E0A` | Inputs and secondary buttons |
| Warm text | `#F8E5D6` | Primary content |
| Muted clay | `#C5A89A` | Supporting information |
| Ember | `#FF4D21` | Fire data, selection, and gradient endpoint |
| Signal amber | `#FF9418` | Thermal scale, focus, and gradient midpoint |

The flame uses the full yellow-to-ember gradient as the single brand signature.
The background uses broad, low-opacity thermal blooms rather than grids or
generic decorative gradients. Primary actions use a solid coral fill; elsewhere, fire colors communicate
heat, selection, or warning. Text must meet WCAG AA contrast.

## Typography

Barlow is bundled locally and used throughout the interface. Its compact,
wayfinding character fits maps without turning labels into technical costume.
Use sentence case. Tabular numerals are enabled only for counts and measured
values. Body copy stays below 75 characters per line where practical.

## Layout

- The compact header identifies the product with the original thermal flame and
  heat rings, states its limitation, and exposes only the useful privacy link.
- Observation controls form one toolbar.
- The map is visible in the first desktop and mobile viewport.
- The legend describes domain values directly below the map.
- Records form a continuous, paginated observation log rather than cards.
- Methodology and privacy use native disclosures near the data they explain.

## Components and states

- Controls use an 8 px radius; major containers use 12–16 px.
- Buttons have three explicit levels: solid coral primary action, warm internal
  glow for the selected layer, and raised dark surfaces for secondary actions.
- Warm translucent borders separate dark surfaces; shadows are reserved for the
  map, the primary action, and floating controls.
- Every control needs hover, focus, disabled, and loading behavior.
- Loading occupies the stable map shell; errors and stale data explain recovery.
- Selection is communicated by color, border/position, and text together.

## Motion

Motion is limited to user-triggered state changes: refresh rotation, map flight,
selection, and disclosure. Do not add global scroll reveals, decorative scans,
or continuous ambient animation. Respect `prefers-reduced-motion`.

## Content and trust

Prefer precise terms: detection, observation, possible cluster, FRP, data age,
and source. Always state that satellite observations are not confirmed fires and
that cluster envelopes are not measured burned perimeters. Avoid marketing copy
such as “environmental intelligence”.

## Accessibility

Preserve keyboard map/list synchronization, skip navigation, semantic records,
visible focus, forced-colors support, reduced motion, and equivalent popup/list
information. No state may rely on color alone.
