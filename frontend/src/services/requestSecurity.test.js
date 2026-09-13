import assert from "node:assert/strict";
import test from "node:test";
import {
  APP_CHECK_HEADER,
  buildRequestSecurityHeaders,
  CLIENT_ID_HEADER,
} from "./requestSecurity.js";

test("builds anonymous identity and App Check headers", async () => {
  const headers = await buildRequestSecurityHeaders({
    clientId: "019b4dc8-e75a-4d97-b0c2-98780b891f28",
    tokenProvider: async () => "attested-token",
  });

  assert.equal(
    headers[CLIENT_ID_HEADER],
    "019b4dc8-e75a-4d97-b0c2-98780b891f28",
  );
  assert.equal(headers[APP_CHECK_HEADER], "attested-token");
});

test("omits App Check only when the integration is disabled", async () => {
  const headers = await buildRequestSecurityHeaders({
    clientId: "019b4dc8-e75a-4d97-b0c2-98780b891f28",
    tokenProvider: async () => null,
  });

  assert.equal(APP_CHECK_HEADER in headers, false);
});
