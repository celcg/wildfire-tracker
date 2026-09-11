import { FIRE_CACHE_NAMESPACE } from "../config/fireConfig";
import { readCachedValue, writeCachedValue } from "./cacheStorage";

export function readCachedFires(days) {
  return readCachedValue(FIRE_CACHE_NAMESPACE, days, Array.isArray);
}

export function writeCachedFires(days, data) {
  return writeCachedValue(FIRE_CACHE_NAMESPACE, days, data);
}
