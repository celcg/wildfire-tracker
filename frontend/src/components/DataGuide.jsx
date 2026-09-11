/**
 * Native details/summary provides keyboard and screen-reader behavior without
 * duplicating disclosure state in React.
 */
export function DataGuide({ showClusters }) {
  return (
    <details className="data-guide">
      <summary>
        <span>How to read the satellite data</span>
        <i aria-hidden="true" />
      </summary>
      <div className="guide-content">
        {showClusters ? (
          <div>
            <h3>Possible clusters</h3>
            <p>
              Detections within 2 km and 12 hours are connected into one
              possible fire area. Every original point remains visible. The
              shaded envelope joins related observations and adds a 1 km
              context margin so isolated observations also remain legible.
            </p>
          </div>
        ) : null}
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
          {showClusters
            ? "Shaded envelopes, clusters, and trends are analytical indicators—not measured burned perimeters, confirmed incidents, or forecasts."
            : "This scale describes satellite-measured thermal intensity. It is not an official emergency or wildfire severity classification."}
        </p>
      </div>
    </details>
  );
}
