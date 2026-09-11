import { memo, useMemo } from "react";
import {
  CircleMarker,
  MapContainer,
  Polygon,
  Popup,
  TileLayer,
  Tooltip,
} from "react-leaflet";
import {
  INCIDENT_SEVERITY_LEVELS,
  INTENSITY_LEVELS,
  MAP_CONFIG,
} from "../config/fireConfig";
import {
  formatAcquisitionTime,
  formatConfidence,
  formatFrp,
  getFireKey,
  getIntensity,
  getIntensityRange,
} from "../domain/firePresentation";
import {
  formatDuration,
  formatIncidentRange,
  formatObservedAt,
  formatTrend,
  getIncidentSeverity,
} from "../domain/incidentPresentation";
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

const IncidentAreas = memo(function IncidentAreas({ incidents }) {
  return incidents
    .filter(
      (incident) =>
        Array.isArray(incident.boundary) && incident.boundary.length >= 3,
    )
    .map((incident) => {
      const severity = getIncidentSeverity(incident.total_frp_mw);
      const boundary = incident.boundary.map((point) => [
        point.latitude,
        point.longitude,
      ]);

      return (
        <Polygon
          key={incident.id}
          positions={boundary}
          pathOptions={{
            className: "possible-area",
            color: severity.color,
            dashArray: "7 6",
            fillColor: severity.color,
            fillOpacity: 0.12,
            opacity: 0.78,
            weight: 1.5,
          }}
        >
          {incident.detection_count > 1 ? (
            <Tooltip permanent direction="center" className="cluster-count">
              {incident.detection_count}
            </Tooltip>
          ) : null}
          <Popup>
            <strong>{severity.name} aggregate intensity</strong>
            <p className="incident-id">{incident.id}</p>
            <dl className="detection-data">
              <div>
                <dt>Detections</dt>
                <dd>{incident.detection_count}</dd>
              </div>
              <div>
                <dt>Total FRP</dt>
                <dd>{formatFrp(incident.total_frp_mw)}</dd>
              </div>
              <div>
                <dt>Peak FRP</dt>
                <dd>{formatFrp(incident.maximum_frp_mw)}</dd>
              </div>
              <div>
                <dt>First observed</dt>
                <dd>{formatObservedAt(incident.first_detected_at)}</dd>
              </div>
              <div>
                <dt>Last observed</dt>
                <dd>{formatObservedAt(incident.last_detected_at)}</dd>
              </div>
              <div>
                <dt>Observed span</dt>
                <dd>{formatDuration(incident.duration_hours)}</dd>
              </div>
              <div>
                <dt>Trend</dt>
                <dd>{formatTrend(incident.trend)}</dd>
              </div>
              <div>
                <dt>Confidence</dt>
                <dd>{formatConfidence(incident.confidence)}</dd>
              </div>
            </dl>
            <p className="incident-note">
              The shaded envelope is analytical context, not a measured burned
              perimeter.
            </p>
          </Popup>
        </Polygon>
      );
    });
});

function DetectionLegend() {
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

function IncidentLegend() {
  return (
    <div className="intensity-key" aria-label="Cluster intensity scale">
      <span className="key-title">Aggregate FRP</span>
      {INCIDENT_SEVERITY_LEVELS.map((level, index) => (
        <span className="key-level" key={level.name}>
          <i
            aria-hidden="true"
            style={{
              "--marker-color": level.color,
              "--marker-size": 13 + index * 2 + "px",
            }}
          />
          <b>{level.name}</b>
          <small>{formatIncidentRange(index)}</small>
        </span>
      ))}
    </div>
  );
}

export function FireMap({ fires, incidents, layer }) {
  const showClusters = layer === "clusters";
  const clusteredDetections = useMemo(
    () =>
      incidents.flatMap((incident) =>
        Array.isArray(incident.detections) ? incident.detections : [],
      ),
    [incidents],
  );

  return (
    <section className="map-section" aria-labelledby="map-title" data-reveal>
      <div className="map-heading">
        <div>
          <p className="section-index">
            {showClusters ? "DERIVED CLUSTER LAYER" : "LIVE DETECTION LAYER"}
          </p>
          <h2 id="map-title">
            {showClusters ? "Possible fire areas" : "Thermal activity map"}
          </h2>
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
          {showClusters ? (
            <>
              <IncidentAreas incidents={incidents} />
              <FireMarkers fires={clusteredDetections} />
            </>
          ) : (
            <FireMarkers fires={fires} />
          )}
        </MapContainer>
        {/* Corner guides reinforce the satellite-viewfinder metaphor. */}
        <div className="map-corner map-corner-top" aria-hidden="true" />
        <div className="map-corner map-corner-bottom" aria-hidden="true" />
      </div>

      {showClusters ? <IncidentLegend /> : <DetectionLegend />}
      <DataGuide showClusters={showClusters} />
    </section>
  );
}
