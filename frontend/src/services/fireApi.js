import { API_URL } from "../config/fireConfig";

/**
 * Owns the HTTP contract so UI code does not know URL construction or response
 * validation details.
 */
export async function fetchFires({ days, forceRefresh, signal }) {
  const searchParams = new URLSearchParams({ days });

  if (forceRefresh) {
    searchParams.set("refresh", "true");
  }

  const response = await fetch(
    API_URL + "/fires?" + searchParams.toString(),
    { signal },
  );

  if (!response.ok) {
    throw new Error("API request failed (" + response.status + ")");
  }

  const data = await response.json();

  // Fail at the service boundary rather than letting invalid data break Leaflet.
  if (!Array.isArray(data)) {
    throw new TypeError("The fire API returned an invalid response");
  }

  return data;
}

export async function fetchIncidents({ days, forceRefresh, signal }) {
  const searchParams = new URLSearchParams({ days });

  if (forceRefresh) {
    searchParams.set("refresh", "true");
  }

  const response = await fetch(
    API_URL + "/incidents?" + searchParams.toString(),
    { signal },
  );

  if (!response.ok) {
    throw new Error("Incident API request failed (" + response.status + ")");
  }

  const data = await response.json();
  const hasValidAreas = data?.incidents?.every(
    (incident) =>
      Array.isArray(incident.boundary) &&
      incident.boundary.length >= 3 &&
      Array.isArray(incident.detections) &&
      incident.detections.length >= 1,
  );

  if (!Array.isArray(data?.incidents) || !hasValidAreas) {
    throw new TypeError("The incident API returned an invalid response");
  }

  return data;
}
