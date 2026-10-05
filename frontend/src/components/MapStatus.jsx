import { getMapStatusText } from "../domain/dataStatePresentation";

export function MapStatus({ isEmpty, layer, loading, observationWindow }) {
  if (loading) {
    return (
      <p className="map-loading" role="status">
        {getMapStatusText({ layer, loading, observationWindow })}
      </p>
    );
  }

  if (!isEmpty) {
    return null;
  }

  return (
    <p className="empty-state" role="status">
      {getMapStatusText({ layer, loading, observationWindow })}
    </p>
  );
}
