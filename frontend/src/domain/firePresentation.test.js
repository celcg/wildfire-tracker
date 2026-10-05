import assert from "node:assert/strict";
import test from "node:test";
import {
  formatCoordinates,
  formatDetectionObservedAt,
} from "./firePresentation.js";

test("formats detection time and location for the explorer", () => {
  assert.equal(
    formatDetectionObservedAt({ acq_date: "2026-09-23", acq_time: "915" }),
    "2026-09-23 at 09:15 UTC",
  );
  assert.equal(formatCoordinates(42.12345, -8.54321), "42.1234, -8.5432");
});

test("does not expose invalid coordinates as a real location", () => {
  assert.equal(formatCoordinates("invalid", null), "Location unavailable");
});
