function FlameMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 180 220" aria-hidden="true">
      <defs>
        <linearGradient id="brand-flame-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffd166" />
          <stop offset="0.48" stopColor="#ff9418" />
          <stop offset="1" stopColor="#ff4d21" />
        </linearGradient>
      </defs>
      <path
        className="brand-flame-outline"
        d="M98 8c9 42-21 52-8 84 9 22 29 19 34-1 20 24 34 50 30 77-5 31-31 48-64 48-38 0-67-23-64-58 3-33 28-54 48-78 13-16 22-38 24-72Z"
      />
      <path
        className="brand-flame-core"
        d="M91 112c5 22-13 30-10 50 2 13 13 19 24 13 8-4 11-13 9-24 11 12 17 25 13 38-5 17-20 25-38 23-20-2-33-16-31-34 2-20 18-32 33-66Z"
      />
    </svg>
  );
}

function openPrivacyNotice(event) {
  const notice = document.getElementById("privacy");
  if (!notice) {
    return;
  }

  event.preventDefault();
  notice.open = true;
  window.history.replaceState(null, "", "#privacy");
  notice.scrollIntoView?.({ behavior: "smooth", block: "start" });
  notice.querySelector("summary")?.focus({ preventScroll: true });
}

export function AppHeader() {
  return (
    <header className="app-header">
      <a className="brand" href="#map-title" aria-label="Wildfire Tracker map">
        <span className="brand-emblem" aria-hidden="true">
          <i className="brand-ring brand-ring-outer" />
          <i className="brand-ring brand-ring-inner" />
          <FlameMark />
        </span>
        <span>
          <strong>Wildfire Tracker</strong>
          <small>Iberian Peninsula</small>
        </span>
      </a>

      <p className="header-description">
        Near-real-time VIIRS thermal detections. Satellite observations are not
        confirmed fires.
      </p>

      <a className="privacy-link" href="#privacy" onClick={openPrivacyNotice}>
        Privacy
      </a>
    </header>
  );
}
