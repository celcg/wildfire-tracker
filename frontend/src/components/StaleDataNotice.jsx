import { formatDataAge } from "../domain/dataStatePresentation";

export function StaleDataNotice({ sourceUpdatedAt }) {
  return (
    <p className="stale-data-notice" role="status">
      <span aria-hidden="true">!</span>
      <span>
        <strong>Source data age · {formatDataAge(sourceUpdatedAt)}</strong>
        NASA FIRMS is temporarily unavailable. Showing the last successful
        source update.
      </span>
    </p>
  );
}
