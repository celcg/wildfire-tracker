import { useCallback, useEffect, useRef, useState } from "react";
import { fetchIncidents } from "../services/fireApi";
import {
  readCachedIncidents,
  writeCachedIncidents,
} from "../services/incidentCache";

const LOAD_ERROR_MESSAGE =
  "Possible fire clusters could not be loaded. Please try again.";
const FRESH_DATA = { isStale: false, sourceUpdatedAt: null };

/**
 * Loads derived clusters only when the user requests that map layer.
 *
 * Keeping this separate from useFireData prevents a layer change from creating
 * an automatic two-request waterfall against the conservative public API.
 */
export function useIncidentData() {
  const [collection, setCollection] = useState(null);
  const loadedDays = useRef(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [freshness, setFreshness] = useState(FRESH_DATA);
  const activeRequest = useRef(null);

  const loadIncidents = useCallback(
    async (targetDays, forceRefresh = false) => {
      activeRequest.current?.abort();
      activeRequest.current = null;

      if (!forceRefresh) {
        const cached = readCachedIncidents(targetDays);

        if (cached) {
          const cachedFreshness = cached.metadata?.freshness ?? FRESH_DATA;
          setCollection(cached.data);
          setFreshness(cachedFreshness);
          loadedDays.current = targetDays;
          setLastUpdated(cached.cachedAt);
          setLoading(false);
          setError("");
          return { data: cached.data, freshness: cachedFreshness };
        }
      }

      const controller = new AbortController();
      activeRequest.current = controller;

      if (loadedDays.current !== targetDays) {
        setCollection(null);
      }
      setLoading(true);
      setError("");

      try {
        const result = await fetchIncidents({
          days: targetDays,
          forceRefresh,
          signal: controller.signal,
        });

        if (!controller.signal.aborted) {
          const cachedAt = writeCachedIncidents(
            targetDays,
            result.data,
            result.freshness,
          );
          setCollection(result.data);
          setFreshness(result.freshness);
          loadedDays.current = targetDays;
          setLastUpdated(cachedAt);
          return result;
        }
      } catch (requestError) {
        if (requestError.name !== "AbortError") {
          setError(LOAD_ERROR_MESSAGE);
          console.error("Incident data request failed:", requestError);
        }
        return null;
      } finally {
        if (activeRequest.current === controller) {
          activeRequest.current = null;
          setLoading(false);
        }
      }
    },
    [],
  );

  useEffect(
    () => () => {
      activeRequest.current?.abort();
    },
    [],
  );

  return {
    collection,
    error,
    freshness,
    lastUpdated,
    loadIncidents,
    loading,
  };
}
