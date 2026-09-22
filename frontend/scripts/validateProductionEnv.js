import { loadEnv } from "vite";

const requiredVariables = [
  "VITE_API_URL",
  "VITE_FIREBASE_API_KEY",
  "VITE_FIREBASE_APP_ID",
  "VITE_FIREBASE_PROJECT_ID",
  "VITE_RECAPTCHA_ENTERPRISE_SITE_KEY",
];

const environment = {
  ...loadEnv("production", process.cwd(), ""),
  ...process.env,
};
const missingVariables = requiredVariables.filter(
  (name) => !environment[name]?.trim(),
);

if (missingVariables.length > 0) {
  console.error(
    "Production build is missing required public configuration: " +
      missingVariables.join(", "),
  );
  process.exitCode = 1;
} else {
  const approvedApiOrigin =
    "https://wildfire-api-440479996053.europe-west1.run.app";
  let apiUrl;

  try {
    apiUrl = new URL(environment.VITE_API_URL);
  } catch {
    console.error("VITE_API_URL must be a valid absolute URL.");
    process.exitCode = 1;
  }

  if (
    apiUrl &&
    (apiUrl.origin !== approvedApiOrigin ||
      apiUrl.username ||
      apiUrl.password ||
      (apiUrl.pathname !== "/" && apiUrl.pathname !== "") ||
      apiUrl.search ||
      apiUrl.hash)
  ) {
    console.error(
      "VITE_API_URL must use the approved production API origin: " +
        approvedApiOrigin,
    );
    process.exitCode = 1;
  }
}
