import { OBSERVATION_WINDOWS } from "../config/fireConfig";
import { formatSyncTime } from "../domain/firePresentation";

export function ControlDeck({
  days,
  detectionCount,
  lastUpdated,
  loading,
  onDaysChange,
  onRefresh,
}) {
  const handleDaysChange = (event) => onDaysChange(event.target.value);

  return (
    <section className="control-deck" aria-label="Map controls">
      <div className="control-field">
        <label htmlFor="days">Observation window</label>
        <select
          id="days"
          value={days}
          onChange={handleDaysChange}
          disabled={loading}
        >
          {OBSERVATION_WINDOWS.map((window) => (
            <option value={window.days} key={window.days}>
              {window.label}
            </option>
          ))}
        </select>
      </div>

      <button
        className={"refresh-button" + (loading ? " is-loading" : "")}
        type="button"
        onClick={onRefresh}
        disabled={loading}
      >
        {/* The wrapper carries motion so the SVG remains simple and cheap. */}
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5" />
        </svg>
        {loading ? "Synchronising" : "Refresh data"}
      </button>

      <div className="data-readout" aria-live="polite">
        <span className="readout-value">{loading ? "—" : detectionCount}</span>
        <span className="readout-label">
          {loading ? "Scanning orbit" : "Active detections"}
        </span>
        <span className="readout-time">
          Last sync · {formatSyncTime(lastUpdated)}
        </span>
      </div>
    </section>
  );
}
