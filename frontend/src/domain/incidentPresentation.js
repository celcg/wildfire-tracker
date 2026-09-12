import { INCIDENT_SEVERITY_LEVELS } from "../config/fireConfig.js";

export function getIncidentSeverity(totalFrp) {
  const power = Number(totalFrp);

  if (!Number.isFinite(power)) {
    return INCIDENT_SEVERITY_LEVELS[0];
  }

  return (
    INCIDENT_SEVERITY_LEVELS.find((level) => power < level.max) ??
    INCIDENT_SEVERITY_LEVELS[0]
  );
}

export function hasClusterArea(incident) {
  return Boolean(
    Number(incident?.detection_count) > 1 &&
      Array.isArray(incident?.boundary) &&
      incident.boundary.length >= 3,
  );
}

export function getIncidentRadius(detectionCount) {
  // Square-root scaling preserves visible differences without giant outliers.
  return Math.min(25, 8 + Math.sqrt(Number(detectionCount) || 1) * 3);
}

export function formatIncidentRange(levelIndex) {
  const level = INCIDENT_SEVERITY_LEVELS[levelIndex];
  const lowerBound =
    levelIndex === 0 ? 0 : INCIDENT_SEVERITY_LEVELS[levelIndex - 1].max;

  return Number.isFinite(level.max)
    ? lowerBound + "–" + level.max + " MW"
    : lowerBound + "+ MW";
}

export function formatObservedAt(value) {
  if (!value) {
    return "Unknown";
  }

  return new Date(value).toLocaleString([], {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

export function formatDuration(hours) {
  const duration = Number(hours);
  if (!Number.isFinite(duration) || duration === 0) {
    return "Single observation";
  }
  if (duration < 1) {
    return Math.round(duration * 60) + " min";
  }
  return duration.toFixed(1) + " h";
}

export function formatTrend(trend) {
  return {
    increasing: "Increasing",
    stable: "Stable",
    decreasing: "Decreasing",
  }[trend] ?? "Unknown";
}
