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

test("sends a unique request ID and keeps the ID returned by the API", async () => {
  const receivedIds = [];
  globalThis.fetch = async (_url, options) => {
    receivedIds.push(options.headers["X-Request-ID"]);
    return new Response(JSON.stringify([]), {
      headers: { "X-Request-ID": "419a80bf-3498-4e90-8b47-cf929c637caa" },
    });
  };

  const first = await fetchFires({ days: "1", forceRefresh: false });
  await fetchFires({ days: "3", forceRefresh: false });

  assert.match(receivedIds[0], /^[0-9a-f-]{36}$/);
  assert.notEqual(receivedIds[0], receivedIds[1]);
  assert.equal(first.requestId, "419a80bf-3498-4e90-8b47-cf929c637caa");
});

test("attaches the correlated request ID to HTTP errors", async () => {
  globalThis.fetch = async () =>
    new Response(null, {
      status: 503,
      headers: { "X-Request-ID": "b856861c-c01c-40e7-8aca-3c4a6fe87e3f" },
    });

  await assert.rejects(
    fetchFires({ days: "1", forceRefresh: true }),
    (error) => {
      assert.equal(error.requestId, "b856861c-c01c-40e7-8aca-3c4a6fe87e3f");
      assert.match(error.message, /503/);
      return true;
    },
  );
});
