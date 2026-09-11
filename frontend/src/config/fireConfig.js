// Keep environment-specific values in one module so components remain portable.
export const API_URL =
  import.meta.env.VITE_API_URL ??
  "https://wildfire-api-440479996053.europe-west1.run.app";

export const DEFAULT_OBSERVATION_DAYS = "1";

// The namespace is versioned deliberately. A future cache schema can be released
// without trying to migrate incompatible values already stored in user browsers.
export const FIRE_CACHE_NAMESPACE = "wildfire-fires-v1";

export const OBSERVATION_WINDOWS = [
  { days: "1", label: "Last 24 hours" },
  { days: "3", label: "Last 3 days" },
  { days: "5", label: "Last 5 days" },
];

// FRP is a visual intensity proxy, not an emergency severity rating.
// Keeping thresholds here prevents marker rendering and the legend from diverging.
export const INTENSITY_LEVELS = [
  { name: "Low", max: 5, color: "#71f6b5", radius: 5 },
  { name: "Moderate", max: 15, color: "#f2c94c", radius: 7 },
  { name: "High", max: 50, color: "#ff8a4c", radius: 10 },
  { name: "Extreme", max: Infinity, color: "#ff3d5a", radius: 14 },
];

export const MAP_CONFIG = {
  center: [40.4, -3.7],
  zoom: 5,
  tileUrl: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  attribution: "&copy; OpenStreetMap contributors",
};
