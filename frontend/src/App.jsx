import { memo, useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL ??
  "https://wildfire-api-440479996053.europe-west1.run.app";
const CACHE_PREFIX = "wildfire-fires-v1";

function readCachedFires(days) {
  try {
    const cached = JSON.parse(localStorage.getItem(`${CACHE_PREFIX}:${days}`));
    return Array.isArray(cached?.data) ? cached : null;
  } catch {
    return null;
  }
}

function cacheFires(days, data) {
  const cachedAt = Date.now();
  try {
    localStorage.setItem(
      `${CACHE_PREFIX}:${days}`,
      JSON.stringify({ data, cachedAt }),
    );
  } catch {
    // Fresh data remains usable when browser storage is unavailable or full.
  }
  return cachedAt;
}

const FireMarkers = memo(function FireMarkers({ fires }) {
  return fires.map((fire, index) => (
    <CircleMarker
      key={`${fire.latitude}-${fire.longitude}-${fire.acq_date}-${fire.acq_time}-${index}`}
      center={[fire.latitude, fire.longitude]}
      radius={8}
      pathOptions={{
        color: "#ffb197",
        fillColor: "#ff6248",
        fillOpacity: 0.78,
        opacity: 0.9,
        weight: 1.5,
      }}
    >
      <Popup>
        <strong>Thermal detection</strong>
        <br />
        Date: {fire.acq_date}
        <br />
        Time: {fire.acq_time}
        <br />
        Satellite: {fire.satellite}
        <br />
        Confidence: {fire.confidence}
        <br />
        FRP: {fire.frp} MW
      </Popup>
    </CircleMarker>
  ));
});

function App() {
  const [initialCache] = useState(() => readCachedFires("1"));
  const [fires, setFires] = useState(initialCache?.data ?? []);
  const [days, setDays] = useState("1");
  const [loading, setLoading] = useState(!initialCache);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(
    initialCache?.cachedAt ?? null,
  );
  const [request, setRequest] = useState(() =>
    initialCache ? null : { days: "1", refresh: false, id: 0 },
  );

  useEffect(() => {
    if (!request) {
      return undefined;
    }

    const controller = new AbortController();
    const refreshParam = request.refresh ? "&refresh=true" : "";

    fetch(`${API_URL}/fires?days=${request.days}${refreshParam}`, {
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`API request failed (${response.status})`);
        }
        return response.json();
      })
      .then((data) => {
        if (!controller.signal.aborted) {
          const cachedAt = cacheFires(request.days, data);
          setFires(data);
          setLastUpdated(cachedAt);
          setLoading(false);
        }
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          setError("Fire detections could not be loaded. Please try again.");
          setLoading(false);
          console.error("Error:", requestError);
        }
      });

    return () => controller.abort();
  }, [request]);

  const handleDaysChange = (event) => {
    const nextDays = event.target.value;
    const cached = readCachedFires(nextDays);

    setDays(nextDays);
    setError("");

    if (cached) {
      setRequest(null);
      setFires(cached.data);
      setLastUpdated(cached.cachedAt);
      setLoading(false);
      return;
    }

    setLoading(true);
    setRequest({ days: nextDays, refresh: false, id: Date.now() });
  };

  const handleRefresh = () => {
    setError("");
    setLoading(true);
    setRequest({ days, refresh: true, id: Date.now() });
  };

  const updatedTime = lastUpdated
    ? new Date(lastUpdated).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Awaiting sync";

  return (
    <main className="app-shell">
      <header className="hero">
        <div className="hero-copy">
          <p className="mission-label">
            <span className="live-signal" aria-hidden="true" />
            Earth observation · Iberian Peninsula
          </p>
          <h1>
            Wildfire <span>Tracker</span>
          </h1>
          <p className="hero-description">
            A near-real-time view of satellite thermal detections, built to
            make environmental change visible.
          </p>
        </div>

        <div className="orbital-scan" aria-hidden="true">
          <span className="orbit orbit-one" />
          <span className="orbit orbit-two" />
          <span className="planet-core" />
          <span className="satellite-dot" />
          <span className="coordinate north">43° N</span>
          <span className="coordinate west">09° W</span>
        </div>
      </header>

      <section className="control-deck" aria-label="Map controls">
        <div className="control-field">
          <label htmlFor="days">Observation window</label>
          <select
            id="days"
            value={days}
            onChange={handleDaysChange}
            disabled={loading}
          >
            <option value="1">Last 24 hours</option>
            <option value="3">Last 3 days</option>
            <option value="5">Last 5 days</option>
          </select>
        </div>

        <button
          className={`refresh-button${loading ? " is-loading" : ""}`}
          type="button"
          onClick={handleRefresh}
          disabled={loading}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5" />
          </svg>
          {loading ? "Synchronising" : "Refresh data"}
        </button>

        <div className="data-readout" aria-live="polite">
          <span className="readout-value">{loading ? "—" : fires.length}</span>
          <span className="readout-label">
            {loading ? "Scanning orbit" : "Active detections"}
          </span>
          <span className="readout-time">Last sync · {updatedTime}</span>
        </div>
      </section>

      {error && (
        <p className="error" role="alert">
          <span aria-hidden="true">!</span>
          {error}
        </p>
      )}

      <section className="map-section" aria-labelledby="map-title">
        <div className="map-heading">
          <div>
            <p className="section-index">01 / LIVE LAYER</p>
            <h2 id="map-title">Thermal activity map</h2>
          </div>
          <div className="source-badge">
            <span aria-hidden="true" />
            NASA FIRMS · VIIRS
          </div>
        </div>

        <div className="map-frame">
          <MapContainer
            className="fire-map"
            center={[40.4, -3.7]}
            zoom={5}
            scrollWheelZoom
          >
            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FireMarkers fires={fires} />
          </MapContainer>
          <div className="map-corner map-corner-top" aria-hidden="true" />
          <div className="map-corner map-corner-bottom" aria-hidden="true" />
          <p className="map-legend">
            <span aria-hidden="true" /> Satellite thermal anomaly
          </p>
        </div>
      </section>

      <footer className="site-footer">
        <span>Environmental intelligence through open data</span>
        <span>Data source · NASA FIRMS</span>
      </footer>
    </main>
  );
}

export default App;
