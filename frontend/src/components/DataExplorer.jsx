import { useEffect, useMemo, useState } from "react";
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
import {
  getPageForIndex,
  paginate,
} from "../domain/explorerPagination";

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

function DetectionResult({ fire, index, isSelected, onSelect, selectedRef }) {
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
            onClick={() => onSelect(resultKey)}
            ref={isSelected ? selectedRef : null}
            type="button"
          >
            {isSelected ? "Selected on map" : "Show on map"}
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

function IncidentResult({ incident, index, isSelected, onSelect, selectedRef }) {
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
            onClick={() => onSelect(incident.id)}
            ref={isSelected ? selectedRef : null}
            type="button"
          >
            {isSelected ? "Selected on map" : "Show on map"}
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
  focusRequest = 0,
  incidents,
  layer,
  onSelect,
  selectedKey,
  selectedResultRef,
}) {
  const showClusters = layer === "clusters";
  const results = showClusters ? incidents : fires;
  const scopeKey = `${layer}:${results.length}`;
  const selectedIndex = selectedKey
    ? results.findIndex((result) =>
        showClusters
          ? result.id === selectedKey
          : getFireKey(result) === selectedKey,
      )
    : -1;
  const [pageState, setPageState] = useState({
    page: 1,
    focusRequest,
    scopeKey,
    selectedKey: null,
  });
  const requestedPage =
    pageState.scopeKey !== scopeKey
      ? 1
      : pageState.selectedKey !== selectedKey ||
          pageState.focusRequest !== focusRequest
        ? getPageForIndex(selectedIndex)
        : pageState.page;
  const pagination = useMemo(
    () => paginate(results, requestedPage),
    [requestedPage, results],
  );
  const changePage = (page) =>
    setPageState({ focusRequest, page, scopeKey, selectedKey });

  useEffect(() => {
    selectedResultRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [pagination.page, selectedKey, selectedResultRef]);

  useEffect(() => {
    if (focusRequest > 0) {
      selectedResultRef.current?.focus();
    }
  }, [focusRequest, pagination.page, selectedResultRef]);

  return (
    <section
      className="data-explorer"
      id="data-explorer"
      aria-labelledby="explorer-title"
      tabIndex={-1}
    >
      <header className="explorer-heading">
        <div>
          <h2 id="explorer-title">
            {showClusters ? "Possible cluster records" : "Detection records"}
          </h2>
          <p>
            Inspect the satellite observations behind the map without using
            map controls.
          </p>
        </div>
        <p className="result-count" aria-live="polite">
          {results.length} {results.length === 1 ? "result" : "results"}
        </p>
      </header>

      {results.length > 0 ? (
        <>
          <ol className="result-list" start={pagination.startIndex + 1}>
            {pagination.items.map((result, index) =>
              showClusters ? (
                <IncidentResult
                  incident={result}
                  index={pagination.startIndex + index}
                  isSelected={selectedKey === result.id}
                  key={result.id}
                  onSelect={onSelect}
                  selectedRef={selectedResultRef}
                />
              ) : (
                <DetectionResult
                  fire={result}
                  index={pagination.startIndex + index}
                  isSelected={selectedKey === getFireKey(result)}
                  key={getFireKey(result)}
                  onSelect={onSelect}
                  selectedRef={selectedResultRef}
                />
              ),
            )}
          </ol>

          {pagination.totalPages > 1 ? (
            <nav className="pagination" aria-label="Record pages">
              <button
                type="button"
                disabled={pagination.page === 1}
                onClick={() => changePage(pagination.page - 1)}
              >
                Previous
              </button>
              <p aria-live="polite">
                Page <strong>{pagination.page}</strong> of {pagination.totalPages}
                <small>
                  Showing {pagination.startIndex + 1}–
                  {pagination.startIndex + pagination.items.length} of{" "}
                  {pagination.totalItems}
                </small>
              </p>
              <button
                type="button"
                disabled={pagination.page === pagination.totalPages}
                onClick={() => changePage(pagination.page + 1)}
              >
                Next
              </button>
            </nav>
          ) : null}
        </>
      ) : (
        <p className="explorer-empty">No records are available to explore.</p>
      )}
    </section>
  );
}
