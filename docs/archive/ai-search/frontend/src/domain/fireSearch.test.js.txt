import assert from "node:assert/strict";
import test from "node:test";
import {
  applyFireSearchFilters,
  describeFireSearchFilters,
  isSupportedSearchPlace,
} from "./fireSearch.js";

test("filters, sorts and limits detections without mutating the source", () => {
  const fires = [
    { latitude: 42.1, longitude: -8.6, frp: 20, confidence: "n", acq_date: "2026-10-29", acq_time: 900 },
    { latitude: 42.2, longitude: -8.5, frp: 80, confidence: "h", acq_date: "2026-10-29", acq_time: 1000 },
    { latitude: 40.4, longitude: -3.7, frp: 100, confidence: "h", acq_date: "2026-10-29", acq_time: 1100 },
  ];

  const result = applyFireSearchFilters(fires, "detections", {
    place: "Galicia",
    minimum_frp_mw: 30,
    sort: "highest_frp",
    limit: 1,
  });

  assert.equal(result.length, 1);
  assert.equal(result[0].frp, 80);
  assert.equal(fires.length, 3);
});

test("filters clusters by severity and persistence", () => {
  const incidents = [
    { severity: "moderate", duration_hours: 30, maximum_frp_mw: 40, center: { latitude: 42.1, longitude: -8.6 } },
    { severity: "high", duration_hours: 8, maximum_frp_mw: 70, center: { latitude: 42.2, longitude: -8.5 } },
  ];
  const result = applyFireSearchFilters(incidents, "clusters", {
    minimum_severity: "moderate",
    minimum_persistence_hours: 24,
    sort: "persistent",
    limit: 20,
  });
  assert.equal(result.length, 1);
  assert.equal(result[0].duration_hours, 30);
});

test("supports only deterministic named-area boundaries", () => {
  assert.equal(isSupportedSearchPlace("Galicia"), true);
  assert.equal(isSupportedSearchPlace("near me"), false);
  assert.deepEqual(describeFireSearchFilters({ days: 3, layer: "clusters" }), [
    "Last 3 days",
    "Possible clusters",
  ]);
});
