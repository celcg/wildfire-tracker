import { FIREBASE_APP_CHECK_CONFIG } from "../config/firebaseConfig.js";

let appCheckPromise;

async function initializeAppCheckOnce() {
  const [{ initializeApp }, appCheckSdk] = await Promise.all([
    import("firebase/app"),
    import("firebase/app-check"),
  ]);
  const app = initializeApp(FIREBASE_APP_CHECK_CONFIG.firebaseConfig);
  return appCheckSdk.initializeAppCheck(app, {
    provider: new appCheckSdk.ReCaptchaEnterpriseProvider(
      FIREBASE_APP_CHECK_CONFIG.siteKey,
    ),
    isTokenAutoRefreshEnabled: true,
  });
}

export async function getAppCheckToken() {
  if (!FIREBASE_APP_CHECK_CONFIG.enabled) {
    return null;
  }

  appCheckPromise ??= initializeAppCheckOnce();
  const [{ getToken }, appCheck] = await Promise.all([
    import("firebase/app-check"),
    appCheckPromise,
  ]);
  return (await getToken(appCheck, false)).token;
}
