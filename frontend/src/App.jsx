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

function App() {
  const [fires, setFires] = useState([]);
  const [days, setDays] = useState("1");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/fires?days=${days}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`API request failed (${response.status})`);
        }
        return response.json();
      })
      .then((data) => {
        if (!controller.signal.aborted) {
          setFires(data);
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
  }, [days]);

  return (
    <main>
      <h1>Wildfire Tracker</h1>
      <p>Active wildfire detections</p>

      <div className="controls">
        <label htmlFor="days">Observation window</label>
        <select
          id="days"
          value={days}
          onChange={(event) => {
            setLoading(true);
            setError("");
            setDays(event.target.value);
          }}
        >
          <option value="1">24 hours</option>
          <option value="3">3 days</option>
          <option value="5">5 days</option>
        </select>
        <span aria-live="polite">
          {loading ? "Loading detections…" : `${fires.length} detections`}
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
