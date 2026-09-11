import { useCallback, useEffect, useRef, useState } from "react";
import { fetchIncidents } from "../services/fireApi";
import {
  readCachedIncidents,
  writeCachedIncidents,
} from "../services/incidentCache";

const LOAD_ERROR_MESSAGE =
  "Possible fire clusters could not be loaded. Please try again.";

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
  const activeRequest = useRef(null);

  const loadIncidents = useCallback(
    async (targetDays, forceRefresh = false) => {
      activeRequest.current?.abort();
      activeRequest.current = null;

      if (!forceRefresh) {
        const cached = readCachedIncidents(targetDays);

        if (cached) {
          setCollection(cached.data);
          loadedDays.current = targetDays;
          setLastUpdated(cached.cachedAt);
          setLoading(false);
          setError("");
          return cached.data;
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
        const data = await fetchIncidents({
          days: targetDays,
          forceRefresh,
          signal: controller.signal,
        });

        if (!controller.signal.aborted) {
          const cachedAt = writeCachedIncidents(targetDays, data);
          setCollection(data);
          loadedDays.current = targetDays;
          setLastUpdated(cachedAt);
          return data;
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
    lastUpdated,
    loadIncidents,
    loading,
  };
}
