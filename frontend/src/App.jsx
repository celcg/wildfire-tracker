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
  const [refreshingAll, setRefreshingAll] = useState(false);
  const [refreshError, setRefreshError] = useState("");

  // App composes feature sections; networking and browser APIs stay in hooks.
  const fireData = useFireData();
  const incidentData = useIncidentData();
  const showClusters = layer === "clusters";
  const activeCollection = incidentData.collection;
  const activeCount = showClusters
    ? (activeCollection?.incident_count ?? 0)
    : fireData.fires.length;
  const activeError =
    refreshError || (showClusters ? incidentData.error : fireData.error);
  const activeLoading =
    refreshingAll ||
    (showClusters ? incidentData.loading : fireData.loading);
  const activeLastUpdated = showClusters
    ? incidentData.lastUpdated
    : fireData.lastUpdated;

  const handleDaysChange = (nextDays) => {
    setRefreshError("");
    setDays(nextDays);

    if (showClusters) {
      incidentData.loadIncidents(nextDays);
    } else {
      fireData.loadFires(nextDays);
    }
  };

  const handleLayerChange = (nextLayer) => {
    setRefreshError("");
    setLayer(nextLayer);

    if (nextLayer === "clusters") {
      incidentData.loadIncidents(days);
    } else {
      fireData.loadFires(days);
    }
  };

  const handleRefresh = async () => {
    setRefreshingAll(true);
    setRefreshError("");

    const refreshedCollection = await incidentData.loadIncidents(days, true);

    if (refreshedCollection) {
      const refreshedDetections = refreshedCollection.incidents.flatMap(
        (incident) => incident.detections,
      );
      fireData.replaceFires(days, refreshedDetections);
    } else {
      setRefreshError(
        "Points and clusters could not be refreshed. Please try again.",
      );
    }

    setRefreshingAll(false);
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
