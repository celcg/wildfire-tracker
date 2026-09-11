import { formatFrp } from "../domain/firePresentation";

export function IncidentSummary({ collection }) {
  if (!collection) {
    return null;
  }

  const incidents = collection.incidents;
  const strongest = incidents[0];
  const groupedDetections = incidents.reduce(
    (total, incident) => total + incident.detection_count,
    0,
  );
  const persistentCount = incidents.filter(
    (incident) => incident.duration_hours >= 6,
  ).length;

  return (
    <section className="incident-summary" aria-label="Cluster overview">
      <p>
        Nearby observations are linked by possible affected-area envelopes;
        every source detection remains visible. These are analytical groups,
        not measured burned perimeters or confirmed incidents.
      </p>
      <dl>
        <div>
          <dt>Possible clusters</dt>
          <dd>{collection.incident_count}</dd>
        </div>
        <div>
          <dt>Grouped detections</dt>
          <dd>{groupedDetections}</dd>
        </div>
        <div>
          <dt>Highest aggregate FRP</dt>
          <dd>{strongest ? formatFrp(strongest.total_frp_mw) : "—"}</dd>
        </div>
        <div>
          <dt>Active for 6+ hours</dt>
          <dd>{persistentCount}</dd>
        </div>
      </dl>
    </section>
  );
}
