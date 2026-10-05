import { useRef, useState } from "react";
import "leaflet/dist/leaflet.css";
import "./App.css";
import { ControlDeck } from "./components/ControlDeck";
import { DataExplorer } from "./components/DataExplorer";
import { DataErrorNotice } from "./components/DataErrorNotice";
import { FireMap } from "./components/FireMap";
import { Hero } from "./components/Hero";
import { IncidentSummary } from "./components/IncidentSummary";
import { PrivacyNotice } from "./components/PrivacyNotice";
import { StaleDataNotice } from "./components/StaleDataNotice";
import {
  DEFAULT_OBSERVATION_DAYS,
  OBSERVATION_WINDOWS,
} from "./config/fireConfig";
import { useFireData } from "./hooks/useFireData";
import { useIncidentData } from "./hooks/useIncidentData";
import { useScrollReveal } from "./hooks/useScrollReveal";
import { refreshAllLayers } from "./services/refreshAllLayers";

const EMPTY_INCIDENTS = [];

function App() {
  useScrollReveal();
  const [days, setDays] = useState(DEFAULT_OBSERVATION_DAYS);
  const [layer, setLayer] = useState("detections");
  const [refreshingAll, setRefreshingAll] = useState(false);
  const [selectedKey, setSelectedKey] = useState(null);
  const selectedResultRef = useRef(null);

  // App composes feature sections; networking and browser APIs stay in hooks.
  const fireData = useFireData();
  const incidentData = useIncidentData();
  const showClusters = layer === "clusters";
  const activeCollection = incidentData.collection;
  const activeCount = showClusters
    ? (activeCollection?.incident_count ?? 0)
    : fireData.fires.length;
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
    setSelectedKey(null);
    setDays(nextDays);

    if (showClusters) {
      incidentData.loadIncidents(nextDays);
    } else {
      fireData.loadFires(nextDays);
    }
  };

  const handleLayerChange = (nextLayer) => {
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

  return (
    <main className="app-shell">
      <a className="skip-link" href="#data-explorer">
        Skip to data explorer
      </a>
      <Hero />

      <ControlDeck
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

      <FireMap
        fires={fireData.fires}
        incidents={activeCollection?.incidents ?? EMPTY_INCIDENTS}
        hasError={Boolean(activeError)}
        layer={layer}
        loading={activeLoading}
        onReturnToResult={() => selectedResultRef.current?.focus()}
        onSelect={setSelectedKey}
        observationWindow={observationWindow}
        selectedKey={selectedKey}
      />

      <DataExplorer
        fires={fireData.fires}
        incidents={activeCollection?.incidents ?? EMPTY_INCIDENTS}
        layer={layer}
        onSelect={setSelectedKey}
        selectedKey={selectedKey}
        selectedResultRef={selectedResultRef}
      />

      <PrivacyNotice />

      <footer className="site-footer">
        <span>Environmental intelligence through open data</span>
        <span>
          Data source · NASA FIRMS · <a href="#privacy">Privacy</a>
        </span>
      </footer>
    </main>
  );
}

export default App;
