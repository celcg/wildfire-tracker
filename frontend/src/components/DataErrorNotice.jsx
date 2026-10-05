import { useEffect, useState } from "react";
import { getErrorMessage } from "../domain/dataStatePresentation";

export function DataErrorNotice({ error }) {
  const [secondsRemaining, setSecondsRemaining] = useState(
    error.retryAfterSeconds,
  );

  useEffect(() => {
    if (!Number.isFinite(error.retryAfterSeconds)) {
      return undefined;
    }

    const retryAt = Date.now() + error.retryAfterSeconds * 1000;
    const timer = window.setInterval(() => {
      setSecondsRemaining(Math.max(0, Math.ceil((retryAt - Date.now()) / 1000)));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [error.retryAfterSeconds]);

  return (
    <div className="error" role="alert">
      <span aria-hidden="true">!</span>
      <div>
        <p>{getErrorMessage(error.kind)}</p>
        {Number.isFinite(secondsRemaining) && secondsRemaining > 0 ? (
          <p>Try again in {secondsRemaining} seconds.</p>
        ) : null}
        {error.requestId ? <small>Request ID: {error.requestId}</small> : null}
      </div>
    </div>
  );
}
