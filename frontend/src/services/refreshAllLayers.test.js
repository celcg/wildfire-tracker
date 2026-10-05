import assert from "node:assert/strict";
import test from "node:test";
import { refreshAllLayers } from "./refreshAllLayers.js";

function resources({ fireResult = [], incidentResult = {} } = {}) {
  const calls = [];
  return {
    calls,
    fireData: {
      loadFires: async (...args) => {
        calls.push(["fires", ...args]);
        return fireResult;
      },
    },
    incidentData: {
      loadIncidents: async (...args) => {
        calls.push(["incidents", ...args]);
        return incidentResult;
      },
    },
  };
}

test("refresh updates both layers for the selected window", async () => {
  const context = resources();
  const results = await refreshAllLayers({ days: "3", ...context });

  assert.deepEqual(context.calls, [
    ["fires", "3", true],
    ["incidents", "3", true],
  ]);
  assert.equal(results.every((result) => result.status === "fulfilled"), true);
});

test("one layer failure does not prevent the other refresh", async () => {
  const context = resources();
  context.fireData.loadFires = async (...args) => {
    context.calls.push(["fires", ...args]);
    throw new Error("fire request failed");
  };

  const results = await refreshAllLayers({ days: "5", ...context });

  assert.deepEqual(context.calls, [
    ["fires", "5", true],
    ["incidents", "5", true],
  ]);
  assert.equal(results[0].status, "rejected");
  assert.equal(results[1].status, "fulfilled");
});
