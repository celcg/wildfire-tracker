const PROVIDERS = [
  ["Firebase Hosting", "Delivers the web application."],
  ["Google Cloud Run", "Processes API requests."],
  ["Cloud Logging", "Keeps operational and security records."],
  ["OpenStreetMap", "Provides the map tiles requested by your browser."],
];

export function PrivacyNotice() {
  return (
    <details className="privacy-notice" id="privacy">
      <summary>
        <span>Privacy notice</span>
        <small>No advertising cookies or analytics</small>
      </summary>
      <div className="privacy-content">
        <p className="privacy-intro">
          Wildfire Tracker is a portfolio project with no accounts, forms,
          advertising cookies, or behavioural profiling.
        </p>

        <section>
          <h3>On this device</h3>
          <p>
            Recent fire data and synchronization times are cached in browser
            local storage for up to two hours. A random installation identifier
            is also stored there to apply fair request limits without logging
            your IP address. It is not an account and you can remove it by
            clearing this site&apos;s data in your browser.
          </p>
        </section>

        <section>
          <h3>External services</h3>
          <ul>
            {PROVIDERS.map(([name, purpose]) => (
              <li key={name}>
                <strong>{name}</strong> — {purpose}
              </li>
            ))}
          </ul>
          <p>
            These providers may receive technical metadata such as an IP
            address, browser information, request time, and requested resource.
            Firebase App Check also verifies that API requests originate from
            the published application.
          </p>
        </section>

        <section>
          <h3>Purpose and retention</h3>
          <p>
            Technical data is used only to deliver, protect, and diagnose the
            service. Application logs avoid request bodies, coordinates,
            credentials, and complete upstream URLs. Cloud records follow the
            retention configured for the Google Cloud project.
          </p>
        </section>

        <p className="privacy-contact">
          Privacy questions can be sent through the contact method on the{" "}
          <a
            href="https://github.com/celcg"
            target="_blank"
            rel="noreferrer"
          >
            project maintainer&apos;s GitHub profile
          </a>
          . Do not post sensitive information in a public issue.
        </p>
      </div>
    </details>
  );
}
