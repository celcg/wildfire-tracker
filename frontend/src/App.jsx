import { useEffect, useState } from "react";
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

  return (
    <main>
      <h1>Wildfire Tracker</h1>
      <p>Active wildfire detections</p>

      <div className="controls">
        <label htmlFor="days">Observation window</label>
        <select
          id="days"
          value={days}
          onChange={handleDaysChange}
          disabled={loading}
        >
          <option value="1">24 hours</option>
          <option value="3">3 days</option>
          <option value="5">5 days</option>
        </select>
        <button type="button" onClick={handleRefresh} disabled={loading}>
          Refresh data
        </button>
        <span aria-live="polite">
          {loading
            ? "Loading detections…"
            : `${fires.length} detections${
                lastUpdated
                  ? ` · Updated ${new Date(lastUpdated).toLocaleTimeString()}`
                  : ""
              }`}
        </span>
      </div>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <MapContainer
        center={[40.4, -3.7]}
        zoom={5}
        style={{ height: "600px", width: "100%" }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {fires.map((fire, index) => (
          <CircleMarker
            key={index}
            center={[fire.latitude, fire.longitude]}
            radius={8}
          >
            <Popup>
              <strong>Fire detection</strong>
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
        ))}
      </MapContainer>
    </main>
  );
}

export default App;
