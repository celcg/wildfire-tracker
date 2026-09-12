function formatDataAge(sourceUpdatedAt) {
  if (!Number.isFinite(sourceUpdatedAt)) {
    return "an earlier update";
  }

  const elapsedMinutes = Math.max(
    1,
    Math.round((Date.now() - sourceUpdatedAt) / 60_000),
  );

  if (elapsedMinutes < 60) {
    return `${elapsedMinutes} minute${elapsedMinutes === 1 ? "" : "s"} ago`;
  }

  const elapsedHours = Math.round(elapsedMinutes / 60);
  return `${elapsedHours} hour${elapsedHours === 1 ? "" : "s"} ago`;
}

export function StaleDataNotice({ sourceUpdatedAt }) {
  return (
    <p className="stale-data-notice" role="status">
      <span aria-hidden="true">!</span>
      <span>
        <strong>Cached satellite data</strong>
        NASA FIRMS is temporarily unavailable. Showing the last successful
        update from {formatDataAge(sourceUpdatedAt)}.
      </span>
    </p>
  );
}
