import { API_URL } from "../config/fireConfig.js";
import { buildRequestSecurityHeaders } from "./requestSecurity.js";

const REQUEST_ID_HEADER = "X-Request-ID";
const REQUEST_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export class FireApiError extends Error {
  constructor(kind, options = {}) {
    super(kind);
    this.name = "FireApiError";
    this.kind = kind;
    this.requestId = sanitizeRequestId(options.requestId);
    this.retryAfterSeconds = options.retryAfterSeconds ?? null;
    this.status = options.status ?? null;
  }
}

export function sanitizeRequestId(requestId) {
  return typeof requestId === "string" && REQUEST_ID_PATTERN.test(requestId)
    ? requestId
    : null;
}

export function parseRetryAfter(value, now = Date.now()) {
  if (typeof value !== "string" || value.trim() === "") {
    return null;
  }

  const seconds = Number(value);
  if (Number.isFinite(seconds) && seconds >= 0) {
    return Math.ceil(seconds);
  }

  const retryAt = Date.parse(value);
  return Number.isFinite(retryAt)
    ? Math.max(0, Math.ceil((retryAt - now) / 1000))
    : null;
}

export function classifyNetworkError(online = globalThis.navigator?.onLine) {
  return online === false ? "offline" : "service";
}

function readFreshness(response) {
  const isStale = response.headers.get("X-Data-Stale") === "true";
  const parsedAge = Number(response.headers.get("X-Data-Age-Seconds"));
  const ageSeconds = Number.isFinite(parsedAge) ? Math.max(0, parsedAge) : 0;

  return {
    isStale,
    sourceUpdatedAt: isStale ? Date.now() - ageSeconds * 1000 : null,
  };
}

async function requestJson({ path, signal }) {
  // A per-request identifier lets Cloud Logging connect a UI failure with the
  // exact API and NASA/cache events that produced it.
  const clientRequestId = globalThis.crypto.randomUUID();
  let response;

  try {
    const securityHeaders = await buildRequestSecurityHeaders();
    response = await fetch(API_URL + path, {
      headers: {
        Accept: "application/json",
        [REQUEST_ID_HEADER]: clientRequestId,
        ...securityHeaders,
      },
      signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }
    throw new FireApiError(classifyNetworkError(), {
      requestId: clientRequestId,
    });
  }

  const requestId = response.headers.get(REQUEST_ID_HEADER) ?? clientRequestId;
  if (!response.ok) {
    throw new FireApiError(response.status === 429 ? "rate-limit" : "service", {
      requestId,
      retryAfterSeconds: parseRetryAfter(response.headers.get("Retry-After")),
      status: response.status,
    });
  }

  try {
    return {
      data: await response.json(),
      freshness: readFreshness(response),
      requestId,
    };
  } catch {
    throw new FireApiError("malformed", { requestId });
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
    signal,
  });

  // Fail at the service boundary rather than letting invalid data break Leaflet.
  if (!Array.isArray(result.data)) {
    throw new FireApiError("malformed", { requestId: result.requestId });
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
    throw new FireApiError("malformed", { requestId: result.requestId });
  }

  return result;
}
