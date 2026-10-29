import { MAP_LAYERS, OBSERVATION_WINDOWS } from "../config/fireConfig";
import { formatSyncTime } from "../domain/firePresentation";

export function ObservationToolbar({
  days,
  activeCount,
  lastUpdated,
  layer,
  loading,
  onDaysChange,
  onLayerChange,
  onRefresh,
  readoutLabel,
}) {
  return (
    <section className="observation-toolbar" aria-label="Observation controls">
      <div className="control-field">
        <label htmlFor="days">Time window</label>
        <select
          id="days"
          value={days}
          onChange={(event) => onDaysChange(event.target.value)}
          disabled={loading}
        >
          {OBSERVATION_WINDOWS.map((window) => (
            <option value={window.days} key={window.days}>
              {window.label}
            </option>
          ))}
        </select>
      </div>

      <div className="layer-switch" aria-label="Map layer">
        {MAP_LAYERS.map((option) => (
          <button
            type="button"
            className={layer === option.id ? "is-active" : ""}
            aria-pressed={layer === option.id}
            disabled={loading}
            onClick={() => onLayerChange(option.id)}
            key={option.id}
          >
            {option.label}
          </button>
        ))}
      </div>

      <div className="data-readout" aria-live="polite">
        <strong>{activeCount}</strong>
        <span>{loading ? `Updating ${readoutLabel}` : readoutLabel}</span>
        <small>Retrieved {formatSyncTime(lastUpdated)}</small>
      </div>

      <button
        className={"refresh-button" + (loading ? " is-loading" : "")}
        type="button"
        onClick={onRefresh}
        disabled={loading}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5" />
        </svg>
        {loading ? "Refreshing" : "Refresh data"}
      </button>
    </section>
  );
}
