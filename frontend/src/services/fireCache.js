import {
  BROWSER_CACHE_TTL_MS,
  FIRE_CACHE_NAMESPACE,
} from "../config/fireConfig.js";
import { readCachedValue, writeCachedValue } from "./cacheStorage.js";

export function readCachedFires(days) {
  return readCachedValue(
    FIRE_CACHE_NAMESPACE,
    days,
    Array.isArray,
    BROWSER_CACHE_TTL_MS,
  );
}

export function writeCachedFires(days, data, freshness) {
  return writeCachedValue(FIRE_CACHE_NAMESPACE, days, data, { freshness });
}
