const runtimeEnvironment = import.meta.env ?? {};

export function resolveFirebaseAppCheckConfig(environment) {
  const firebaseConfig = {
    apiKey: environment.VITE_FIREBASE_API_KEY,
    appId: environment.VITE_FIREBASE_APP_ID,
    projectId: environment.VITE_FIREBASE_PROJECT_ID,
  };
  const siteKey = environment.VITE_RECAPTCHA_ENTERPRISE_SITE_KEY;
  const enabled = Boolean(
    firebaseConfig.apiKey && firebaseConfig.appId && firebaseConfig.projectId && siteKey,
  );

  return { enabled, firebaseConfig, siteKey };
}

export const FIREBASE_APP_CHECK_CONFIG =
  resolveFirebaseAppCheckConfig(runtimeEnvironment);
