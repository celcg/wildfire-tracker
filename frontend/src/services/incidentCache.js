import {
  BROWSER_CACHE_TTL_MS,
  INCIDENT_CACHE_NAMESPACE,
} from "../config/fireConfig.js";
import { readCachedValue, writeCachedValue } from "./cacheStorage.js";

function isIncidentCollection(data) {
  return Boolean(
    data &&
      Array.isArray(data.incidents) &&
      data.incidents.every(
        (incident) =>
          Array.isArray(incident.boundary) &&
          incident.boundary.length >= 3 &&
          Array.isArray(incident.detections) &&
          incident.detections.length >= 1,
      ),
  );
}

export function readCachedIncidents(days) {
  return readCachedValue(
    INCIDENT_CACHE_NAMESPACE,
    days,
    isIncidentCollection,
    BROWSER_CACHE_TTL_MS,
  );
}

export function writeCachedIncidents(days, data, freshness) {
  return writeCachedValue(INCIDENT_CACHE_NAMESPACE, days, data, { freshness });
}
