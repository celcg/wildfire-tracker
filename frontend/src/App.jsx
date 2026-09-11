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

const INTENSITY_LEVELS = [
  { name: "Low", max: 5, color: "#71f6b5", radius: 5 },
  { name: "Moderate", max: 15, color: "#f2c94c", radius: 7 },
  { name: "High", max: 50, color: "#ff8a4c", radius: 10 },
  { name: "Extreme", max: Infinity, color: "#ff3d5a", radius: 14 },
];

function getIntensity(frp) {
  const power = Number(frp);
  return (
    INTENSITY_LEVELS.find((level) => power < level.max) ??
    INTENSITY_LEVELS[0]
  );
}

function formatAcquisitionTime(value) {
  const time = String(value ?? "").padStart(4, "0");
  return `${time.slice(0, 2)}:${time.slice(2, 4)} UTC`;
}

function formatConfidence(value) {
  const confidenceLabels = {
    l: "Low",
    low: "Low",
    n: "Nominal",
    nominal: "Nominal",
    h: "High",
    high: "High",
  };
  const normalized = String(value ?? "Unknown").toLowerCase();
  return confidenceLabels[normalized] ?? String(value ?? "Unknown");
}

function formatFrp(value) {
  const power = Number(value);
  return Number.isFinite(power) ? `${power.toFixed(2)} MW` : "Not available";
}

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
  return fires.map((fire, index) => {
    const intensity = getIntensity(fire.frp);

    return (
      <CircleMarker
        key={`${fire.latitude}-${fire.longitude}-${fire.acq_date}-${fire.acq_time}-${index}`}
        center={[fire.latitude, fire.longitude]}
        radius={intensity.radius}
        pathOptions={{
          color: intensity.color,
          fillColor: intensity.color,
          fillOpacity: 0.7,
          opacity: 0.92,
          weight: 1.5,
        }}
      >
        <Popup>
          <strong>{intensity.name} thermal intensity</strong>
          <dl className="detection-data">
            <div>
              <dt>Date</dt>
              <dd>{fire.acq_date}</dd>
            </div>
            <div>
              <dt>Time (UTC)</dt>
              <dd>{formatAcquisitionTime(fire.acq_time)}</dd>
            </div>
            <div>
              <dt>Satellite</dt>
              <dd>{fire.satellite}</dd>
            </div>
            <div>
              <dt>Confidence (category)</dt>
              <dd>{formatConfidence(fire.confidence)}</dd>
            </div>
            <div>
              <dt>FRP (MW)</dt>
              <dd>{formatFrp(fire.frp)}</dd>
            </div>
          </dl>
        </Popup>
      </CircleMarker>
    );
  });
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
    const revealElements = document.querySelectorAll("[data-reveal]");

    if (!("IntersectionObserver" in window)) {
      revealElements.forEach((element) => element.classList.add("is-visible"));
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.18 },
    );

    revealElements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

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

        <div
          className="orbital-scan"
          data-reveal
          aria-hidden="true"
        >
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

      <section
        className="map-section"
        aria-labelledby="map-title"
        data-reveal
      >
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
        </div>

        <div className="intensity-key" aria-label="Thermal intensity scale">
          <span className="key-title">FRP intensity</span>
          {INTENSITY_LEVELS.map((level, index) => {
            const previousMax = index === 0 ? 0 : INTENSITY_LEVELS[index - 1].max;
            const range = Number.isFinite(level.max)
              ? `${previousMax}–${level.max} MW`
              : `50+ MW`;

            return (
              <span className="key-level" key={level.name}>
                <i
                  aria-hidden="true"
                  style={{
                    "--marker-color": level.color,
                    "--marker-size": `${level.radius * 1.25}px`,
                  }}
                />
                <b>{level.name}</b>
                <small>{range}</small>
              </span>
            );
          })}
        </div>

        <details className="data-guide">
          <summary>
            <span>How to read the satellite data</span>
            <i aria-hidden="true" />
          </summary>
          <div className="guide-content">
            <div>
              <h3>FRP</h3>
              <p>
                Fire Radiative Power estimates the thermal energy emitted by
                a detection. It is measured in megawatts (MW). Larger, warmer
                points indicate greater detected radiative power.
              </p>
            </div>
            <div>
              <h3>Confidence</h3>
              <p>
                NASA assigns a low, nominal, or high confidence category to
                indicate how likely the satellite signal is to be a real
                thermal anomaly rather than noise.
              </p>
            </div>
            <div>
              <h3>Time</h3>
              <p>
                Acquisition time is the moment the satellite observed the
                location, displayed in Coordinated Universal Time (UTC).
              </p>
            </div>
            <p className="guide-note">
              This scale describes satellite-measured thermal intensity. It is
              not an official emergency or wildfire severity classification.
            </p>
          </div>
        </details>
      </section>

      <footer className="site-footer">
        <span>Environmental intelligence through open data</span>
        <span>Data source · NASA FIRMS</span>
      </footer>
    </main>
  );
}

export default App;
