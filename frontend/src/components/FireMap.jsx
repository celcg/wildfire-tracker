import { memo, useCallback, useEffect, useMemo, useRef } from "react";
import {
  CircleMarker,
  MapContainer,
  Polygon,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
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
  hasClusterArea,
} from "../domain/incidentPresentation";
import { DataGuide } from "./DataGuide";
import { MapStatus } from "./MapStatus";

/**
 * Markers are the expensive part of this page. Memoization keeps them stable
 * while loading text, timestamps, or the explanatory disclosure changes.
 */
const FireMarkers = memo(function FireMarkers({
  fires,
  layerKeys,
  onSelect,
  registerLayer,
  selectionKeys,
  selectedKey,
}) {
  return fires.map((fire) => {
    const fireKey = getFireKey(fire);
    const selectionKey = selectionKeys?.get(fireKey) ?? fireKey;
    const layerKey = layerKeys?.get(fireKey) ?? fireKey;
    const intensity = getIntensity(fire.frp);
    const isSelected = selectedKey === selectionKey;
    const shouldRegister =
      registerLayer && (!selectionKeys || layerKeys?.has(fireKey));

    return (
      <CircleMarker
        key={fireKey}
        ref={
          shouldRegister
            ? (layerInstance) => registerLayer(layerKey, layerInstance)
            : null
        }
        center={[fire.latitude, fire.longitude]}
        eventHandlers={{ click: () => onSelect(selectionKey) }}
        radius={intensity.radius + (isSelected ? 3 : 0)}
        pathOptions={{
          color: intensity.color,
          fillColor: intensity.color,
          fillOpacity: 0.7,
          opacity: 0.92,
          weight: isSelected ? 4 : 1.5,
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

const IncidentAreas = memo(function IncidentAreas({
  incidents,
  onSelect,
  registerLayer,
  selectedKey,
}) {
  return incidents
    .filter(hasClusterArea)
    .map((incident) => {
      const severity = getIncidentSeverity(incident.total_frp_mw);
      const boundary = incident.boundary.map((point) => [
        point.latitude,
        point.longitude,
      ]);
      const isSelected = selectedKey === incident.id;

      return (
        <Polygon
          key={incident.id}
          ref={(layerInstance) => registerLayer(incident.id, layerInstance)}
          positions={boundary}
          eventHandlers={{ click: () => onSelect(incident.id) }}
          pathOptions={{
            className: "possible-area",
            color: severity.color,
            dashArray: "7 6",
            fillColor: severity.color,
            fillOpacity: 0.12,
            opacity: 0.78,
            weight: isSelected ? 4 : 1.5,
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

function MapSelectionController({ selectedResult, layerInstances }) {
  const map = useMap();

  useEffect(() => {
    if (!selectedResult) {
      return;
    }

    map.flyTo(
      [selectedResult.latitude, selectedResult.longitude],
      Math.max(map.getZoom(), 9),
      { duration: 0.55 },
    );
    layerInstances.current.get(selectedResult.key)?.openPopup();
  }, [layerInstances, map, selectedResult]);

  return null;
}

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

export function FireMap({
  fires,
  hasError,
  incidents,
  layer,
  loading,
  onReturnToResult,
  onSelect,
  observationWindow,
  selectedKey,
}) {
  const showClusters = layer === "clusters";
  const layerInstances = useRef(new Map());
  const isEmpty =
    !hasError && (showClusters ? incidents.length === 0 : fires.length === 0);
  const clusteredDetections = useMemo(
    () =>
      incidents.flatMap((incident) =>
        Array.isArray(incident.detections) ? incident.detections : [],
      ),
    [incidents],
  );
  const clusterKeysByDetection = useMemo(
    () =>
      new Map(
        incidents.flatMap((incident) =>
          incident.detections.map((fire) => [getFireKey(fire), incident.id]),
        ),
      ),
    [incidents],
  );
  const singletonLayerKeys = useMemo(
    () =>
      new Map(
        incidents
          .filter((incident) => !hasClusterArea(incident))
          .flatMap((incident) => {
            const firstDetection = incident.detections[0];
            return firstDetection
              ? [[getFireKey(firstDetection), incident.id]]
              : [];
          }),
      ),
    [incidents],
  );
  const selectedResult = useMemo(() => {
    if (!selectedKey) {
      return null;
    }
    if (showClusters) {
      const incident = incidents.find((item) => item.id === selectedKey);
      return incident?.center
        ? {
            key: incident.id,
            latitude: incident.center.latitude,
            longitude: incident.center.longitude,
          }
        : null;
    }
    const fire = fires.find((item) => getFireKey(item) === selectedKey);
    return fire
      ? {
          key: selectedKey,
          latitude: fire.latitude,
          longitude: fire.longitude,
        }
      : null;
  }, [fires, incidents, selectedKey, showClusters]);
  const registerLayer = useCallback((key, layerInstance) => {
    if (layerInstance) {
      layerInstances.current.set(key, layerInstance);
    } else {
      layerInstances.current.delete(key);
    }
  }, []);
  const handleMapKeyDown = (event) => {
    if (event.key === "Escape" && selectedResult) {
      event.preventDefault();
      onReturnToResult();
    }
  };

  return (
    <section
      className="map-section"
      aria-busy={loading}
      aria-labelledby="map-title"
      data-reveal
    >
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

      <p className="map-instructions" id="map-instructions">
        Use the zoom controls or arrow keys to explore. Select a record below to
        locate it here. Press Escape to return to the selected record.
      </p>

      <div
        className="map-frame"
        aria-describedby="map-instructions"
        aria-label={
          showClusters
            ? "Map of possible fire cluster observation envelopes"
            : "Map of satellite thermal detections"
        }
        onKeyDown={handleMapKeyDown}
        role="region"
      >
        {loading ? (
          <MapStatus
            isEmpty={isEmpty}
            layer={layer}
            loading
            observationWindow={observationWindow}
          />
        ) : null}
        {selectedResult ? (
          <button
            className="return-to-result"
            onClick={onReturnToResult}
            type="button"
          >
            Return to selected record
          </button>
        ) : null}
        <MapContainer
          className="fire-map"
          center={MAP_CONFIG.center}
          zoom={MAP_CONFIG.zoom}
          scrollWheelZoom
          tabIndex={0}
        >
          <MapSelectionController
            layerInstances={layerInstances}
            selectedResult={selectedResult}
          />
          <TileLayer
            attribution={MAP_CONFIG.attribution}
            url={MAP_CONFIG.tileUrl}
          />
          {showClusters ? (
            <>
              <IncidentAreas
                incidents={incidents}
                onSelect={onSelect}
                registerLayer={registerLayer}
                selectedKey={selectedKey}
              />
              <FireMarkers
                fires={clusteredDetections}
                layerKeys={singletonLayerKeys}
                onSelect={onSelect}
                registerLayer={registerLayer}
                selectionKeys={clusterKeysByDetection}
                selectedKey={selectedKey}
              />
            </>
          ) : (
            <FireMarkers
              fires={fires}
              onSelect={onSelect}
              registerLayer={registerLayer}
              selectedKey={selectedKey}
            />
          )}
        </MapContainer>
        {/* Corner guides reinforce the satellite-viewfinder metaphor. */}
        <div className="map-corner map-corner-top" aria-hidden="true" />
        <div className="map-corner map-corner-bottom" aria-hidden="true" />
      </div>

      {!loading ? (
        <MapStatus
          isEmpty={isEmpty}
          layer={layer}
          loading={false}
          observationWindow={observationWindow}
        />
      ) : null}

      {showClusters ? <IncidentLegend /> : <DetectionLegend />}
      <DataGuide showClusters={showClusters} />
    </section>
  );
}
