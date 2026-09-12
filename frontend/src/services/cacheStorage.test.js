import assert from "node:assert/strict";
import test from "node:test";
import { BROWSER_CACHE_TTL_MS } from "../config/fireConfig.js";
import { readCachedFires } from "./fireCache.js";
import { readCachedValue } from "./cacheStorage.js";

const originalDateNow = Date.now;

function installStorage(value) {
  globalThis.localStorage = {
    getItem: () => JSON.stringify(value),
  };
}

test.afterEach(() => {
  Date.now = originalDateNow;
  delete globalThis.localStorage;
});

test("returns a cache entry while it is inside its maximum age", () => {
  Date.now = () => 10_000;
  installStorage({ data: ["fire"], cachedAt: 9_000 });

  const cached = readCachedValue("fires", "1", Array.isArray, 2_000);

  assert.deepEqual(cached?.data, ["fire"]);
});

test("rejects a cache entry after its maximum age", () => {
  Date.now = () => 12_001;
  installStorage({ data: ["fire"], cachedAt: 10_000 });

  const cached = readCachedValue("fires", "1", Array.isArray, 2_000);

  assert.equal(cached, null);
});

test("fire data uses the configured two-hour browser lifetime", () => {
  Date.now = () => BROWSER_CACHE_TTL_MS + 1;
  installStorage({ data: ["fire"], cachedAt: 0 });

  assert.equal(BROWSER_CACHE_TTL_MS, 2 * 60 * 60 * 1000);
  assert.equal(readCachedFires("1"), null);
});
