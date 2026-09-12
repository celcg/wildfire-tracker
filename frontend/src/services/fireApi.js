import { API_URL } from "../config/fireConfig.js";

const REQUEST_ID_HEADER = "X-Request-ID";

function readFreshness(response) {
  const isStale = response.headers.get("X-Data-Stale") === "true";
  const parsedAge = Number(response.headers.get("X-Data-Age-Seconds"));
  const ageSeconds = Number.isFinite(parsedAge) ? Math.max(0, parsedAge) : 0;

  return {
    isStale,
    sourceUpdatedAt: isStale ? Date.now() - ageSeconds * 1000 : null,
  };
}

function attachRequestId(error, requestId) {
  if (error && typeof error === "object") {
    try {
      error.requestId = requestId;
    } catch {
      // Preserve immutable browser errors instead of masking the root failure.
    }
  }
  return error;
}

async function requestJson({ path, errorLabel, signal }) {
  // A per-request identifier lets Cloud Logging connect a UI failure with the
  // exact API and NASA/cache events that produced it.
  const clientRequestId = globalThis.crypto.randomUUID();
  let response;

  try {
    response = await fetch(API_URL + path, {
      headers: {
        Accept: "application/json",
        [REQUEST_ID_HEADER]: clientRequestId,
      },
      signal,
    });
  } catch (error) {
    throw attachRequestId(error, clientRequestId);
  }

  const requestId = response.headers.get(REQUEST_ID_HEADER) ?? clientRequestId;
  if (!response.ok) {
    throw attachRequestId(
      new Error(errorLabel + " (" + response.status + ")"),
      requestId,
    );
  }

  try {
    return {
      data: await response.json(),
      freshness: readFreshness(response),
      requestId,
    };
  } catch (error) {
    throw attachRequestId(error, requestId);
  }
}

/**
 * Owns the HTTP contract so UI code does not know URL construction or response
 * validation details.
 */
export async function fetchFires({ days, forceRefresh, signal }) {
  const searchParams = new URLSearchParams({ days });

  if (forceRefresh) {
    searchParams.set("refresh", "true");
  }

  const result = await requestJson({
    path: "/fires?" + searchParams.toString(),
    errorLabel: "API request failed",
    signal,
  });

  // Fail at the service boundary rather than letting invalid data break Leaflet.
  if (!Array.isArray(result.data)) {
    throw attachRequestId(
      new TypeError("The fire API returned an invalid response"),
      result.requestId,
    );
  }

  return result;
}

export async function fetchIncidents({ days, forceRefresh, signal }) {
  const searchParams = new URLSearchParams({ days });

  if (forceRefresh) {
    searchParams.set("refresh", "true");
  }

  const result = await requestJson({
    path: "/incidents?" + searchParams.toString(),
    errorLabel: "Incident API request failed",
    signal,
  });
  const hasValidAreas = result.data?.incidents?.every(
    (incident) =>
      Array.isArray(incident.boundary) &&
      incident.boundary.length >= 3 &&
      Array.isArray(incident.detections) &&
      incident.detections.length >= 1,
  );

  if (!Array.isArray(result.data?.incidents) || !hasValidAreas) {
    throw attachRequestId(
      new TypeError("The incident API returned an invalid response"),
      result.requestId,
    );
  }

  return result;
}
