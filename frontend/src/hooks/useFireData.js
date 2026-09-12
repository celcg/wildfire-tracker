import { useCallback, useEffect, useRef, useState } from "react";
import { DEFAULT_OBSERVATION_DAYS } from "../config/fireConfig";
import { fetchFires } from "../services/fireApi";
import { readCachedFires, writeCachedFires } from "../services/fireCache";

const LOAD_ERROR_MESSAGE =
  "Fire detections could not be loaded. Please try again.";
const FRESH_DATA = { isStale: false, sourceUpdatedAt: null };

/**
 * Coordinates cached and remote fire data behind a small UI-facing interface.
 *
 * The hook owns cancellation because only the latest observation window should
 * update the map. Otherwise, a slow old request could overwrite a newer choice.
 */
export function useFireData() {
  const [initialCache] = useState(() =>
    readCachedFires(DEFAULT_OBSERVATION_DAYS),
  );
  const [fires, setFires] = useState(initialCache?.data ?? []);
  const [loading, setLoading] = useState(!initialCache);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(
    initialCache?.cachedAt ?? null,
  );
  const [freshness, setFreshness] = useState(
    initialCache?.metadata?.freshness ?? FRESH_DATA,
  );
  const activeRequest = useRef(null);

  const loadFires = useCallback(async (targetDays, forceRefresh = false) => {
    // Cancel first so a pending response cannot replace cached data selected now.
    activeRequest.current?.abort();
    activeRequest.current = null;

    if (!forceRefresh) {
      const cached = readCachedFires(targetDays);

      if (cached) {
        const cachedFreshness = cached.metadata?.freshness ?? FRESH_DATA;
        setFires(cached.data);
        setFreshness(cachedFreshness);
        setLastUpdated(cached.cachedAt);
        setLoading(false);
        setError("");
        return { data: cached.data, freshness: cachedFreshness };
      }
    }

    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true);
    setError("");

    try {
      const result = await fetchFires({
        days: targetDays,
        forceRefresh,
        signal: controller.signal,
      });

      if (!controller.signal.aborted) {
        const cachedAt = writeCachedFires(
          targetDays,
          result.data,
          result.freshness,
        );
        setFires(result.data);
        setFreshness(result.freshness);
        setLastUpdated(cachedAt);
        return result;
      }
    } catch (requestError) {
      if (requestError.name !== "AbortError") {
        setError(LOAD_ERROR_MESSAGE);
        console.error("Fire data request failed:", requestError);
      }
      return null;
    } finally {
      // A superseded request must not clear its successor's loading indicator.
      if (activeRequest.current === controller) {
        activeRequest.current = null;
        setLoading(false);
      }
    }
  }, []);

  const replaceFires = useCallback((targetDays, data, nextFreshness) => {
    // A cluster refresh carries the same source detections, so reuse that
    // response instead of spending a second API and NASA request.
    activeRequest.current?.abort();
    activeRequest.current = null;

    const cachedAt = writeCachedFires(targetDays, data, nextFreshness);
    setFires(data);
    setFreshness(nextFreshness);
    setLastUpdated(cachedAt);
    setLoading(false);
    setError("");
  }, []);

  useEffect(() => {
    let initialRequestTimer;

    if (!initialCache) {
      // Defer state changes until after the mount effect has synchronized.
      // The initial state already renders the correct loading indicator.
      initialRequestTimer = window.setTimeout(() => {
        loadFires(DEFAULT_OBSERVATION_DAYS);
      }, 0);
    }

    return () => {
      window.clearTimeout(initialRequestTimer);
      activeRequest.current?.abort();
    };
  }, [initialCache, loadFires]);

  return {
    error,
    fires,
    freshness,
    lastUpdated,
    loadFires,
    loading,
    replaceFires,
  };
}
