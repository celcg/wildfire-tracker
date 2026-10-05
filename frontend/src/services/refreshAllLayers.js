export function refreshAllLayers({ days, fireData, incidentData }) {
  return Promise.allSettled([
    fireData.loadFires(days, true),
    incidentData.loadIncidents(days, true),
  ]);
}
