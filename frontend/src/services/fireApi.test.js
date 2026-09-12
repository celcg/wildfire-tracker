import assert from "node:assert/strict";
import test from "node:test";
import { fetchFires } from "./fireApi.js";

const originalDateNow = Date.now;
const originalFetch = globalThis.fetch;

test.afterEach(() => {
  Date.now = originalDateNow;
  globalThis.fetch = originalFetch;
});

test("returns stale-data metadata exposed by the API", async () => {
  Date.now = () => 20_000;
  globalThis.fetch = async () =>
    new Response(JSON.stringify([{ latitude: 42, longitude: -8 }]), {
      headers: {
        "Content-Type": "application/json",
        "X-Data-Stale": "true",
        "X-Data-Age-Seconds": "7200",
      },
    });

  const result = await fetchFires({ days: "1", forceRefresh: true });

  assert.equal(result.freshness.isStale, true);
  assert.equal(result.freshness.sourceUpdatedAt, 20_000 - 7_200_000);
  assert.equal(result.data.length, 1);
});
