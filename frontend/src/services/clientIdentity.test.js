import assert from "node:assert/strict";
import test from "node:test";
import { loadOrCreateClientId } from "./clientIdentity.js";

const ID = "019b4dc8-e75a-4d97-b0c2-98780b891f28";

test("reuses one canonical UUID from versioned local storage", () => {
  const storage = { getItem: () => ID, setItem: () => assert.fail() };

  assert.equal(
    loadOrCreateClientId({ storage, randomUUID: () => assert.fail() }),
    ID,
  );
});

test("creates and stores a UUID when no valid identifier exists", () => {
  let stored;
  const storage = {
    getItem: () => "invalid",
    setItem: (_key, value) => {
      stored = value;
    },
  };

  assert.equal(loadOrCreateClientId({ storage, randomUUID: () => ID }), ID);
  assert.equal(stored, ID);
});

test("continues with an in-memory UUID when storage is unavailable", () => {
  const storage = {
    getItem: () => {
      throw new Error("disabled");
    },
    setItem: () => {
      throw new Error("disabled");
    },
  };

  assert.equal(loadOrCreateClientId({ storage, randomUUID: () => ID }), ID);
});
