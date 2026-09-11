import { INTENSITY_LEVELS } from "../config/fireConfig";

const CONFIDENCE_LABELS = {
  l: "Low",
  low: "Low",
  n: "Nominal",
  nominal: "Nominal",
  h: "High",
  high: "High",
};

/**
 * Maps satellite radiative power to the shared visual scale.
 *
 * Invalid FRP values intentionally fall back to the lowest level. This keeps a
 * usable detection visible while avoiding an unsupported high-severity claim.
 */
export function getIntensity(frp) {
  const power = Number(frp);

  if (!Number.isFinite(power)) {
    return INTENSITY_LEVELS[0];
  }

  return (
    INTENSITY_LEVELS.find((level) => power < level.max) ??
    INTENSITY_LEVELS[INTENSITY_LEVELS.length - 1]
  );
}

/**
 * NASA encodes acquisition time as HHMM and may omit leading zeroes in JSON.
 * UTC is explicit because showing a local-looking time would be ambiguous.
 */
export function formatAcquisitionTime(value) {
  const digits = String(value ?? "").padStart(4, "0");
  return digits.slice(0, 2) + ":" + digits.slice(2, 4) + " UTC";
}

export function formatConfidence(value) {
  const normalized = String(value ?? "Unknown").toLowerCase();
  return CONFIDENCE_LABELS[normalized] ?? String(value ?? "Unknown");
}

export function formatFrp(value) {
  const power = Number(value);
  return Number.isFinite(power) ? power.toFixed(2) + " MW" : "Not available";
}

export function formatSyncTime(timestamp) {
  if (!timestamp) {
    return "Awaiting sync";
  }

  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function getIntensityRange(levelIndex) {
  const level = INTENSITY_LEVELS[levelIndex];
  const lowerBound = levelIndex === 0 ? 0 : INTENSITY_LEVELS[levelIndex - 1].max;

  return Number.isFinite(level.max)
    ? lowerBound + "–" + level.max + " MW"
    : lowerBound + "+ MW";
}

/**
 * A composite key is preferable to the array index alone because the same
 * detection keeps its Leaflet layer when API results arrive in a new order.
 */
export function getFireKey(fire) {
  return [
    fire.latitude,
    fire.longitude,
    fire.acq_date,
    fire.acq_time,
    fire.satellite,
  ].join("-");
}
