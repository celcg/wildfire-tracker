import assert from "node:assert/strict";
import test from "node:test";
import { resolveFirebaseAppCheckConfig } from "./firebaseConfig.js";

test("enables App Check only when every public setting is present", () => {
  const complete = resolveFirebaseAppCheckConfig({
    VITE_FIREBASE_API_KEY: "public-api-key",
    VITE_FIREBASE_APP_ID: "web-app-id",
    VITE_FIREBASE_PROJECT_ID: "project-id",
    VITE_RECAPTCHA_ENTERPRISE_SITE_KEY: "site-key",
  });

  assert.equal(complete.enabled, true);
  assert.equal(resolveFirebaseAppCheckConfig({}).enabled, false);
});
