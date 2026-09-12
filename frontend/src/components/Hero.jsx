/**
 * Static hero markup is isolated from live data so API updates never re-render
 * the decorative thermal signature.
 */
export function Hero() {
  return (
    <header className="hero">
      <div className="hero-copy">
        <p className="mission-label">
          <span className="live-signal" aria-hidden="true" />
          Thermal watch · Iberian Peninsula
        </p>
        <h1>
          Wildfire <span>Tracker</span>
        </h1>
        <p className="hero-description">
          A near-real-time view of satellite thermal detections, built to make
          environmental change visible.
        </p>
      </div>

      <div className="thermal-emblem" data-reveal aria-hidden="true">
        <span className="heat-ring heat-ring-outer" />
        <span className="heat-ring heat-ring-inner" />
        <div className="flame-carrier">
          <svg className="flame-mark" viewBox="0 0 180 220">
            <defs>
              <linearGradient id="flame-thermal-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#ffd166" />
                <stop offset="0.48" stopColor="#ff9418" />
                <stop offset="1" stopColor="#ff4d21" />
              </linearGradient>
            </defs>
            <path
              className="flame-outline"
              d="M98 8c9 42-21 52-8 84 9 22 29 19 34-1 20 24 34 50 30 77-5 31-31 48-64 48-38 0-67-23-64-58 3-33 28-54 48-78 13-16 22-38 24-72Z"
            />
            <path
              className="flame-core"
              d="M91 112c5 22-13 30-10 50 2 13 13 19 24 13 8-4 11-13 9-24 11 12 17 25 13 38-5 17-20 25-38 23-20-2-33-16-31-34 2-20 18-32 33-66Z"
            />
          </svg>
        </div>
        <span className="thermal-reading reading-top">FRP SIGNAL</span>
        <span className="thermal-reading reading-bottom">VIIRS / LIVE</span>
      </div>
    </header>
  );
}
