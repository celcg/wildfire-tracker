import { INCIDENT_CACHE_NAMESPACE } from "../config/fireConfig";
import { readCachedValue, writeCachedValue } from "./cacheStorage";

function isIncidentCollection(data) {
  return Boolean(data && Array.isArray(data.incidents));
}

export function readCachedIncidents(days) {
  return readCachedValue(
    INCIDENT_CACHE_NAMESPACE,
    days,
    isIncidentCollection,
  );
}

export function writeCachedIncidents(days, data) {
  return writeCachedValue(INCIDENT_CACHE_NAMESPACE, days, data);
}
