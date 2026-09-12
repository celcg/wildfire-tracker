// Keep environment-specific values in one module so components remain portable.
const runtimeEnvironment = import.meta.env ?? {};
const LOCAL_API_URL = "/api";
const CLOUD_RUN_API_URL =
  "https://wildfire-api-440479996053.europe-west1.run.app";

export function resolveApiUrl(environment) {
  return (
    environment.VITE_API_URL ??
    (environment.DEV ? LOCAL_API_URL : CLOUD_RUN_API_URL)
  );
}

export const API_URL = resolveApiUrl(runtimeEnvironment);

export const DEFAULT_OBSERVATION_DAYS = "1";
export const BROWSER_CACHE_TTL_MS = 2 * 60 * 60 * 1000;

// The namespace is versioned deliberately. A future cache schema can be released
// without trying to migrate incompatible values already stored in user browsers.
export const FIRE_CACHE_NAMESPACE = "wildfire-fires-v1";
export const INCIDENT_CACHE_NAMESPACE = "wildfire-incidents-v2";

export const MAP_LAYERS = [
  { id: "detections", label: "Detections" },
  { id: "clusters", label: "Possible clusters" },
];

export const OBSERVATION_WINDOWS = [
  { days: "1", label: "Last 24 hours" },
  { days: "3", label: "Last 3 days" },
  { days: "5", label: "Last 5 days" },
];

// FRP is a visual intensity proxy, not an emergency severity rating.
// Keeping thresholds here prevents marker rendering and the legend from diverging.
export const INTENSITY_LEVELS = [
  { name: "Low", max: 5, color: "#ffd166", radius: 5 },
  { name: "Moderate", max: 15, color: "#ff9f1c", radius: 7 },
  { name: "High", max: 50, color: "#ff5a24", radius: 10 },
  { name: "Extreme", max: Infinity, color: "#ff274b", radius: 14 },
];

// Cluster colors describe aggregate FRP and deliberately use wider thresholds.
export const INCIDENT_SEVERITY_LEVELS = [
  { name: "Low", max: 10, color: "#ffd166" },
  { name: "Moderate", max: 50, color: "#ff9f1c" },
  { name: "High", max: 150, color: "#ff5a24" },
  { name: "Extreme", max: Infinity, color: "#ff274b" },
];

export const MAP_CONFIG = {
  center: [40.4, -3.7],
  zoom: 5,
  tileUrl: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  attribution: "&copy; OpenStreetMap contributors",
};
