import { useEffect } from "react";
import {
  formatConfidence,
  formatCoordinates,
  formatDetectionObservedAt,
  formatFrp,
  getFireKey,
  getIntensity,
} from "../domain/firePresentation";
import {
  formatDuration,
  formatIncidentSatellites,
  formatObservedAt,
  formatTrend,
  getIncidentSeverity,
} from "../domain/incidentPresentation";

function ResultFields({ fields }) {
  return (
    <dl className="result-fields">
      {fields.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function DetectionResult({ fire, index, isSelected, onShowOnMap, selectedRef }) {
  const resultKey = getFireKey(fire);
  const intensity = getIntensity(fire.frp);

  return (
    <li className={isSelected ? "is-selected" : ""}>
      <article>
        <div className="result-heading">
          <span className="result-sequence" aria-hidden="true">
            {String(index + 1).padStart(2, "0")}
          </span>
          <div>
            <h3>{intensity.name} thermal intensity</h3>
            <p>{formatCoordinates(fire.latitude, fire.longitude)}</p>
          </div>
          <button
            aria-pressed={isSelected}
            onClick={() => onShowOnMap(resultKey)}
            ref={isSelected ? selectedRef : null}
            type="button"
          >
            {isSelected ? "Show on map again" : "Show on map"}
          </button>
        </div>
        <ResultFields
          fields={[
            ["Observed", formatDetectionObservedAt(fire)],
            ["Confidence", formatConfidence(fire.confidence)],
            ["Satellite", fire.satellite || "Unknown"],
            ["FRP", formatFrp(fire.frp)],
            ["Location", formatCoordinates(fire.latitude, fire.longitude)],
          ]}
        />
      </article>
    </li>
  );
}

function IncidentResult({
  incident,
  index,
  isSelected,
  onShowOnMap,
  selectedRef,
}) {
  const severity = getIncidentSeverity(incident.total_frp_mw);

  return (
    <li className={isSelected ? "is-selected" : ""}>
      <article>
        <div className="result-heading">
          <span className="result-sequence" aria-hidden="true">
            {String(index + 1).padStart(2, "0")}
          </span>
          <div>
            <h3>{severity.name} aggregate intensity</h3>
            <p>
              {incident.detection_count} detections near{" "}
              {formatCoordinates(
                incident.center?.latitude,
                incident.center?.longitude,
              )}
            </p>
          </div>
          <button
            aria-pressed={isSelected}
            onClick={() => onShowOnMap(incident.id)}
            ref={isSelected ? selectedRef : null}
            type="button"
          >
            {isSelected ? "Show on map again" : "Show on map"}
          </button>
        </div>
        <ResultFields
          fields={[
            ["First observed", formatObservedAt(incident.first_detected_at)],
            ["Last observed", formatObservedAt(incident.last_detected_at)],
            ["Confidence", formatConfidence(incident.confidence)],
            ["Satellites", formatIncidentSatellites(incident)],
            ["Total FRP", formatFrp(incident.total_frp_mw)],
            ["Peak FRP", formatFrp(incident.maximum_frp_mw)],
            ["Persistence", formatDuration(incident.duration_hours)],
            ["Trend", formatTrend(incident.trend)],
            [
              "Center",
              formatCoordinates(
                incident.center?.latitude,
                incident.center?.longitude,
              ),
            ],
          ]}
        />
      </article>
    </li>
  );
}

export function DataExplorer({
  fires,
  incidents,
  layer,
  onShowOnMap,
  selectedKey,
  selectedResultRef,
}) {
  const showClusters = layer === "clusters";
  const results = showClusters ? incidents : fires;

  const handleExplorerKeyDown = (event) => {
    if (event.key === "Escape" && selectedKey) {
      event.preventDefault();
      onShowOnMap(selectedKey);
    }
  };

  useEffect(() => {
    selectedResultRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [selectedKey, selectedResultRef]);

  return (
    <section
      className="data-explorer"
      id="data-explorer"
      aria-labelledby="explorer-title"
      onKeyDown={handleExplorerKeyDown}
      tabIndex={-1}
    >
      <header className="explorer-heading">
        <div>
          <p className="section-index">ACCESSIBLE DATA EXPLORER</p>
          <h2 id="explorer-title">
            {showClusters ? "Possible cluster records" : "Detection records"}
          </h2>
        </div>
        <p aria-live="polite">
          {results.length} {results.length === 1 ? "result" : "results"}
        </p>
      </header>

      {results.length > 0 ? (
        <ol className="result-list">
          {results.map((result, index) =>
            showClusters ? (
              <IncidentResult
                incident={result}
                index={index}
                isSelected={selectedKey === result.id}
                key={result.id}
                onShowOnMap={onShowOnMap}
                selectedRef={selectedResultRef}
              />
            ) : (
              <DetectionResult
                fire={result}
                index={index}
                isSelected={selectedKey === getFireKey(result)}
                key={getFireKey(result)}
                onShowOnMap={onShowOnMap}
                selectedRef={selectedResultRef}
              />
            ),
          )}
        </ol>
      ) : (
        <p className="explorer-empty">No records are available to explore.</p>
      )}
    </section>
  );
}
