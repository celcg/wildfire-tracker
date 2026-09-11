/**
 * Static hero markup is isolated from live data so API updates never re-render
 * the decorative orbital illustration.
 */
export function Hero() {
  return (
    <header className="hero">
      <div className="hero-copy">
        <p className="mission-label">
          <span className="live-signal" aria-hidden="true" />
          Earth observation · Iberian Peninsula
        </p>
        <h1>
          Wildfire <span>Tracker</span>
        </h1>
        <p className="hero-description">
          A near-real-time view of satellite thermal detections, built to make
          environmental change visible.
        </p>
      </div>

      <div className="orbital-scan" data-reveal aria-hidden="true">
        <span className="orbit orbit-one" />
        <span className="orbit orbit-two" />
        <span className="planet-core" />
        <span className="satellite-dot" />
        <span className="coordinate north">43° N</span>
        <span className="coordinate west">09° W</span>
      </div>
    </header>
  );
}
