import { memo } from "react";
import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
} from "react-leaflet";
import { INTENSITY_LEVELS, MAP_CONFIG } from "../config/fireConfig";
import {
  formatAcquisitionTime,
  formatConfidence,
  formatFrp,
  getFireKey,
  getIntensity,
  getIntensityRange,
} from "../domain/firePresentation";
import { DataGuide } from "./DataGuide";

/**
 * Markers are the expensive part of this page. Memoization keeps them stable
 * while loading text, timestamps, or the explanatory disclosure changes.
 */
const FireMarkers = memo(function FireMarkers({ fires }) {
  return fires.map((fire) => {
    const intensity = getIntensity(fire.frp);

    return (
      <CircleMarker
        key={getFireKey(fire)}
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

function IntensityLegend() {
  return (
    <div className="intensity-key" aria-label="Thermal intensity scale">
      <span className="key-title">FRP intensity</span>
      {INTENSITY_LEVELS.map((level, index) => (
        <span className="key-level" key={level.name}>
          <i
            aria-hidden="true"
            style={{
              "--marker-color": level.color,
              "--marker-size": level.radius * 1.25 + "px",
            }}
          />
          <b>{level.name}</b>
          <small>{getIntensityRange(index)}</small>
        </span>
      ))}
    </div>
  );
}

export function FireMap({ fires }) {
  return (
    <section className="map-section" aria-labelledby="map-title" data-reveal>
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
          center={MAP_CONFIG.center}
          zoom={MAP_CONFIG.zoom}
          scrollWheelZoom
        >
          <TileLayer
            attribution={MAP_CONFIG.attribution}
            url={MAP_CONFIG.tileUrl}
          />
          <FireMarkers fires={fires} />
        </MapContainer>
        {/* Corner guides reinforce the satellite-viewfinder metaphor. */}
        <div className="map-corner map-corner-top" aria-hidden="true" />
        <div className="map-corner map-corner-bottom" aria-hidden="true" />
      </div>

      <IntensityLegend />
      <DataGuide />
    </section>
  );
}
