import { useState } from "react";
import "leaflet/dist/leaflet.css";
import "./App.css";
import { ControlDeck } from "./components/ControlDeck";
import { FireMap } from "./components/FireMap";
import { Hero } from "./components/Hero";
import { IncidentSummary } from "./components/IncidentSummary";
import { DEFAULT_OBSERVATION_DAYS } from "./config/fireConfig";
import { useFireData } from "./hooks/useFireData";
import { useIncidentData } from "./hooks/useIncidentData";
import { useScrollReveal } from "./hooks/useScrollReveal";

const EMPTY_INCIDENTS = [];

function App() {
  useScrollReveal();
  const [days, setDays] = useState(DEFAULT_OBSERVATION_DAYS);
  const [layer, setLayer] = useState("detections");

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

  const handleDaysChange = (nextDays) => {
    setDays(nextDays);

    if (showClusters) {
      incidentData.loadIncidents(nextDays);
    } else {
      fireData.loadFires(nextDays);
    }
  };

  const handleLayerChange = (nextLayer) => {
    setLayer(nextLayer);

    if (nextLayer === "clusters") {
      incidentData.loadIncidents(days);
    } else {
      fireData.loadFires(days);
    }
  };

  const handleRefresh = () => {
    if (showClusters) {
      incidentData.loadIncidents(days, true);
    } else {
      fireData.loadFires(days, true);
    }
  };

  return (
    <main className="app-shell">
      <Hero />

      <ControlDeck
        days={days}
        activeCount={activeCount}
        lastUpdated={activeLastUpdated}
        layer={layer}
        loading={activeLoading}
        onDaysChange={handleDaysChange}
        onLayerChange={handleLayerChange}
        onRefresh={handleRefresh}
        readoutLabel={showClusters ? "Possible clusters" : "Active detections"}
      />

      {activeError ? (
        <p className="error" role="alert">
          <span aria-hidden="true">!</span>
          {activeError}
        </p>
      ) : null}

      {showClusters ? (
        <IncidentSummary collection={activeCollection} />
      ) : null}

      <FireMap
        fires={fireData.fires}
        incidents={activeCollection?.incidents ?? EMPTY_INCIDENTS}
        layer={layer}
      />

      <footer className="site-footer">
        <span>Environmental intelligence through open data</span>
        <span>Data source · NASA FIRMS</span>
      </footer>
    </main>
  );
}

export default App;
