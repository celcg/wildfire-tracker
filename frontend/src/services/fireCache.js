import { FIRE_CACHE_NAMESPACE } from "../config/fireConfig";

function getCacheKey(days) {
  return FIRE_CACHE_NAMESPACE + ":" + days;
}

/**
 * Browser storage is an optional performance layer, never a requirement.
 * Malformed or unavailable storage therefore behaves exactly like a cache miss.
 */
export function readCachedFires(days) {
  try {
    const cached = JSON.parse(localStorage.getItem(getCacheKey(days)));
    return Array.isArray(cached?.data) ? cached : null;
  } catch {
    return null;
  }
}

/**
 * Returns the timestamp even if persistence fails so fresh API data can still
 * update the UI accurately in private browsing or when storage is full.
 */
export function writeCachedFires(days, data) {
  const cachedAt = Date.now();

  try {
    localStorage.setItem(
      getCacheKey(days),
      JSON.stringify({ data, cachedAt }),
    );
  } catch {
    // Cache failures must not turn a successful network request into an error.
  }

  return cachedAt;
}
