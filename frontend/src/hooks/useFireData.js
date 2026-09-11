import { useCallback, useEffect, useRef, useState } from "react";
import { DEFAULT_OBSERVATION_DAYS } from "../config/fireConfig";
import { fetchFires } from "../services/fireApi";
import { readCachedFires, writeCachedFires } from "../services/fireCache";

const LOAD_ERROR_MESSAGE =
  "Fire detections could not be loaded. Please try again.";

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
  const activeRequest = useRef(null);

  const loadFires = useCallback(async (targetDays, forceRefresh = false) => {
    // Cancel first so a pending response cannot replace cached data selected now.
    activeRequest.current?.abort();
    activeRequest.current = null;

    if (!forceRefresh) {
      const cached = readCachedFires(targetDays);

      if (cached) {
        setFires(cached.data);
        setLastUpdated(cached.cachedAt);
        setLoading(false);
        setError("");
        return;
      }
    }

    const controller = new AbortController();
    activeRequest.current = controller;
    setLoading(true);
    setError("");

    try {
      const data = await fetchFires({
        days: targetDays,
        forceRefresh,
        signal: controller.signal,
      });

      if (!controller.signal.aborted) {
        const cachedAt = writeCachedFires(targetDays, data);
        setFires(data);
        setLastUpdated(cachedAt);
      }
    } catch (requestError) {
      if (requestError.name !== "AbortError") {
        setError(LOAD_ERROR_MESSAGE);
        console.error("Fire data request failed:", requestError);
      }
    } finally {
      // A superseded request must not clear its successor's loading indicator.
      if (activeRequest.current === controller) {
        activeRequest.current = null;
        setLoading(false);
      }
    }
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
    lastUpdated,
    loadFires,
    loading,
  };
}
