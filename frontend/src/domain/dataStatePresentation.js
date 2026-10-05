const ERROR_MESSAGES = {
  offline: "You appear to be offline. Check your connection and try again.",
  "rate-limit": "The request limit has been reached.",
  service: "The satellite data service is temporarily unavailable.",
  malformed: "The service returned data that could not be safely displayed.",
};

export function getErrorMessage(kind) {
  return ERROR_MESSAGES[kind] ?? ERROR_MESSAGES.service;
}

export function getMapStatusText({ layer, loading, observationWindow }) {
  const showClusters = layer === "clusters";
  if (loading) {
    return `Updating ${showClusters ? "possible clusters" : "detections"}…`;
  }
  return showClusters
    ? `No possible fire clusters were derived for ${observationWindow.toLowerCase()}.`
    : `No satellite detections were returned for ${observationWindow.toLowerCase()}.`;
}

export function formatDataAge(sourceUpdatedAt) {
  if (!Number.isFinite(sourceUpdatedAt)) {
    return "an earlier update";
  }

  const elapsedMinutes = Math.max(
    1,
    Math.round((Date.now() - sourceUpdatedAt) / 60_000),
  );
  if (elapsedMinutes < 60) {
    return `${elapsedMinutes} minute${elapsedMinutes === 1 ? "" : "s"} ago`;
  }

  const elapsedHours = Math.round(elapsedMinutes / 60);
  return `${elapsedHours} hour${elapsedHours === 1 ? "" : "s"} ago`;
}
