import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

function App() {
  const [fires, setFires] = useState([]);

  useEffect(() => {
    fetch("https://wildfire-api-440479996053.europe-west1.run.app/fires")
      .then((response) => response.json())
      .then((data) => setFires(data))
      .catch((error) => console.error("Error:", error));
  }, []);

  return (
    <main>
      <h1> Wildfire Tracker</h1>
      <p>Active wildfire detections</p>

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
              <strong>🔥 Fire detection</strong>
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