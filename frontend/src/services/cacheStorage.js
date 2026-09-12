/**
 * Shared versioned storage adapter for map resources.
 *
 * A validator belongs to each caller because detections are arrays while the
 * incidents endpoint returns an envelope with metadata.
 */
export function readCachedValue(namespace, days, isValid, maxAgeMs) {
  try {
    const cached = JSON.parse(
      localStorage.getItem(namespace + ":" + days),
    );
    const cacheAge = Date.now() - cached?.cachedAt;
    const isFresh =
      Number.isFinite(cacheAge) && cacheAge >= 0 && cacheAge < maxAgeMs;

    return isValid(cached?.data) && isFresh ? cached : null;
  } catch {
    return null;
  }
}

export function writeCachedValue(namespace, days, data) {
  const cachedAt = Date.now();

  try {
    localStorage.setItem(
      namespace + ":" + days,
      JSON.stringify({ data, cachedAt }),
    );
  } catch {
    // Data remains usable when private browsing or storage quotas block writes.
  }

  return cachedAt;
}
