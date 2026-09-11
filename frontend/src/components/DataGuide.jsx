/**
 * Native details/summary provides keyboard and screen-reader behavior without
 * duplicating disclosure state in React.
 */
export function DataGuide() {
  return (
    <details className="data-guide">
      <summary>
        <span>How to read the satellite data</span>
        <i aria-hidden="true" />
      </summary>
      <div className="guide-content">
        <div>
          <h3>FRP</h3>
          <p>
            Fire Radiative Power estimates the thermal energy emitted by a
            detection. It is measured in megawatts (MW). Larger, warmer points
            indicate greater detected radiative power.
          </p>
        </div>
        <div>
          <h3>Confidence</h3>
          <p>
            NASA assigns a low, nominal, or high confidence category to
            indicate how likely the satellite signal is to be a real thermal
            anomaly rather than noise.
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
          This scale describes satellite-measured thermal intensity. It is not
          an official emergency or wildfire severity classification.
        </p>
      </div>
    </details>
  );
}
