import assert from "node:assert/strict";
import test from "node:test";
import {
  formatIncidentSatellites,
  hasClusterArea,
} from "./incidentPresentation.js";

test("only incidents with multiple detections are rendered as cluster areas", () => {
  const boundary = [
    { latitude: 42.1, longitude: -8.6 },
    { latitude: 42.11, longitude: -8.6 },
    { latitude: 42.1, longitude: -8.59 },
  ];

  assert.equal(hasClusterArea({ boundary, detection_count: 1 }), false);
  assert.equal(hasClusterArea({ boundary, detection_count: 2 }), true);
});

test("a cluster without a valid polygon is not rendered as an area", () => {
  assert.equal(hasClusterArea({ boundary: [], detection_count: 2 }), false);
});

test("lists unique satellites represented in a cluster", () => {
  assert.equal(
    formatIncidentSatellites({
      detections: [
        { satellite: "NOAA-20" },
        { satellite: "NOAA-20" },
        { satellite: "Suomi NPP" },
      ],
    }),
    "NOAA-20, Suomi NPP",
  );
});
