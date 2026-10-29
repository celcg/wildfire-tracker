import { useMemo, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";
import "./App.css";
import { AppHeader } from "./components/AppHeader";
import { DataExplorer } from "./components/DataExplorer";
import { DataErrorNotice } from "./components/DataErrorNotice";
import { FireMap } from "./components/FireMap";
import { FireSearch } from "./components/FireSearch";
import { IncidentSummary } from "./components/IncidentSummary";
import { ObservationToolbar } from "./components/ObservationToolbar";
import { PrivacyNotice } from "./components/PrivacyNotice";
import { StaleDataNotice } from "./components/StaleDataNotice";
import {
  DEFAULT_OBSERVATION_DAYS,
  OBSERVATION_WINDOWS,
} from "./config/fireConfig";
import { useFireData } from "./hooks/useFireData";
import { useIncidentData } from "./hooks/useIncidentData";
import { refreshAllLayers } from "./services/refreshAllLayers";
import { applyFireSearchFilters } from "./domain/fireSearch";

const EMPTY_INCIDENTS = [];

function App() {
  const [days, setDays] = useState(DEFAULT_OBSERVATION_DAYS);
  const [layer, setLayer] = useState("detections");
  const [refreshingAll, setRefreshingAll] = useState(false);
  const [selectedKey, setSelectedKey] = useState(null);
  const [selectionFocusRequest, setSelectionFocusRequest] = useState(0);
  const [searchFilters, setSearchFilters] = useState(null);
  const selectedResultRef = useRef(null);

  // App composes feature sections; networking and browser APIs stay in hooks.
  const fireData = useFireData();
  const incidentData = useIncidentData();
  const showClusters = layer === "clusters";
  const visibleFires = useMemo(
    () => applyFireSearchFilters(fireData.fires, "detections", searchFilters),
    [fireData.fires, searchFilters],
  );
  const visibleIncidents = useMemo(
    () =>
      applyFireSearchFilters(
        incidentData.collection?.incidents ?? EMPTY_INCIDENTS,
        "clusters",
        searchFilters,
      ),
    [incidentData.collection, searchFilters],
  );
  const activeCollection = incidentData.collection
    ? {
        ...incidentData.collection,
        incident_count: visibleIncidents.length,
        incidents: visibleIncidents,
      }
    : null;
  const activeCount = showClusters
    ? (activeCollection?.incident_count ?? 0)
    : visibleFires.length;
  const activeError = showClusters ? incidentData.error : fireData.error;
  const activeLoading = showClusters
    ? incidentData.loading
    : fireData.loading;
  const activeLastUpdated = showClusters
    ? incidentData.lastUpdated
    : fireData.lastUpdated;
  const activeFreshness = showClusters
    ? incidentData.freshness
    : fireData.freshness;
  const observationWindow =
    OBSERVATION_WINDOWS.find((window) => window.days === days)?.label ??
    `${days} days`;

  const handleDaysChange = (nextDays) => {
    setSearchFilters(null);
    setSelectedKey(null);
    setDays(nextDays);

    if (showClusters) {
      incidentData.loadIncidents(nextDays);
    } else {
      fireData.loadFires(nextDays);
    }
  };

  const handleLayerChange = (nextLayer) => {
    setSearchFilters(null);
    setSelectedKey(null);
    setLayer(nextLayer);

    if (nextLayer === "clusters") {
      incidentData.loadIncidents(days);
    } else {
      fireData.loadFires(days);
    }
  };

  const handleRefresh = async () => {
    setRefreshingAll(true);
    try {
      await refreshAllLayers({ days, fireData, incidentData });
    } finally {
      setRefreshingAll(false);
    }
  };

  const handleSearchApply = (filters) => {
    const nextDays = String(filters.days);
    setSelectedKey(null);
    setSearchFilters(filters);
    setDays(nextDays);
    setLayer(filters.layer);
    if (filters.layer === "clusters") {
      incidentData.loadIncidents(nextDays);
    } else {
      fireData.loadFires(nextDays);
    }
  };

  return (
    <main className="app-shell">
      <a className="skip-link" href="#data-explorer">
        Skip to data explorer
      </a>
      <AppHeader />

      <ObservationToolbar
        days={days}
        activeCount={activeCount}
        lastUpdated={activeLastUpdated}
        layer={layer}
        loading={refreshingAll || activeLoading}
        onDaysChange={handleDaysChange}
        onLayerChange={handleLayerChange}
        onRefresh={handleRefresh}
        readoutLabel={showClusters ? "Possible clusters" : "Active detections"}
      />

      <FireSearch
        activeFilters={searchFilters}
        onApply={handleSearchApply}
        onClear={() => setSearchFilters(null)}
      />

      {activeError ? (
        <DataErrorNotice
          error={activeError}
          key={`${activeError.requestId}:${activeError.kind}`}
        />
      ) : null}

      {activeFreshness.isStale ? (
        <StaleDataNotice sourceUpdatedAt={activeFreshness.sourceUpdatedAt} />
      ) : null}

      {showClusters ? (
        <IncidentSummary collection={activeCollection} />
      ) : null}

      <div className="map-workspace">
        <FireMap
          fires={visibleFires}
          incidents={activeCollection?.incidents ?? EMPTY_INCIDENTS}
          hasError={Boolean(activeError)}
          layer={layer}
          loading={activeLoading}
          onReturnToResult={() =>
            setSelectionFocusRequest((request) => request + 1)
          }
          onSelect={setSelectedKey}
          observationWindow={observationWindow}
          selectedKey={selectedKey}
        />
      </div>

      <DataExplorer
        fires={visibleFires}
        incidents={activeCollection?.incidents ?? EMPTY_INCIDENTS}
        layer={layer}
        focusRequest={selectionFocusRequest}
        onSelect={setSelectedKey}
        selectedKey={selectedKey}
        selectedResultRef={selectedResultRef}
      />

      <PrivacyNotice />

      <footer className="site-footer">
        <span>Satellite observations, not confirmed fire reports.</span>
        <span>
          Data from NASA FIRMS / VIIRS · <a href="#privacy">Privacy</a>
        </span>
      </footer>
    </main>
  );
}

export default App;
