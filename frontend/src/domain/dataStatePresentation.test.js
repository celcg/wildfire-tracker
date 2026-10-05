import assert from "node:assert/strict";
import test from "node:test";
import {
  formatDataAge,
  getErrorMessage,
  getMapStatusText,
} from "./dataStatePresentation.js";

test("describes loading and detection empty states", () => {
  assert.equal(
    getMapStatusText({ layer: "detections", loading: true }),
    "Updating detections…",
  );
  assert.equal(
    getMapStatusText({
      layer: "detections",
      loading: false,
      observationWindow: "Last 3 days",
    }),
    "No satellite detections were returned for last 3 days.",
  );
});

test("distinguishes the four supported request failures", () => {
  assert.match(getErrorMessage("offline"), /offline/);
  assert.match(getErrorMessage("rate-limit"), /request limit/);
  assert.match(getErrorMessage("service"), /temporarily unavailable/);
  assert.match(getErrorMessage("malformed"), /safely displayed/);
});

test("formats source age independently from retrieval time", () => {
  const originalNow = Date.now;
  Date.now = () => 3_600_000;
  try {
    assert.equal(formatDataAge(0), "1 hour ago");
    assert.equal(formatDataAge(null), "an earlier update");
  } finally {
    Date.now = originalNow;
  }
});
