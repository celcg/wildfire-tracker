import axe from "axe-core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { DataErrorNotice } from "./DataErrorNotice";
import { DataExplorer } from "./DataExplorer";
import { MapStatus } from "./MapStatus";

const fire = {
  latitude: 42.12345,
  longitude: -8.54321,
  confidence: "h",
  acq_date: "2026-09-23",
  acq_time: "0915",
  satellite: "NOAA-20",
  frp: 18.4,
};

const incident = {
  id: "incident-example",
  center: { latitude: 42.12, longitude: -8.54 },
  detections: [fire],
  detection_count: 1,
  total_frp_mw: 18.4,
  maximum_frp_mw: 18.4,
  first_detected_at: "2026-09-23T09:15:00Z",
  last_detected_at: "2026-09-23T09:15:00Z",
  duration_hours: 0,
  confidence: "high",
  trend: "stable",
};

test("exposes every detection popup field and selects it by keyboard", async () => {
  const user = userEvent.setup();
  const onSelect = vi.fn();
  render(
    <DataExplorer
      fires={[fire]}
      incidents={[]}
      layer="detections"
      onSelect={onSelect}
      selectedKey={null}
      selectedResultRef={createRef()}
    />,
  );

  expect(screen.getByText("2026-09-23 at 09:15 UTC")).toBeVisible();
  expect(screen.getByText("High")).toBeVisible();
  expect(screen.getByText("NOAA-20")).toBeVisible();
  expect(screen.getByText("18.40 MW")).toBeVisible();
  expect(screen.getAllByText("42.1234, -8.5432")).toHaveLength(2);

  await user.tab();
  expect(screen.getByRole("button", { name: "Show on map" })).toHaveFocus();
  await user.keyboard("{Enter}");
  expect(onSelect).toHaveBeenCalledOnce();
});

test("exposes cluster persistence, trend, satellites, and location", () => {
  render(
    <DataExplorer
      fires={[]}
      incidents={[incident]}
      layer="clusters"
      onSelect={() => {}}
      selectedKey="incident-example"
      selectedResultRef={createRef()}
    />,
  );

  expect(screen.getByText("Single observation")).toBeVisible();
  expect(screen.getByText("Stable")).toBeVisible();
  expect(screen.getByText("NOAA-20")).toBeVisible();
  expect(screen.getByRole("button", { name: "Selected on map" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

test("primary loading, error, and result states have no axe violations", async () => {
  const { container } = render(
    <main>
      <h1>Wildfire tracker</h1>
      <DataErrorNotice
        error={{ kind: "offline", requestId: null, retryAfterSeconds: null }}
      />
      <MapStatus
        isEmpty={false}
        layer="detections"
        loading
        observationWindow="Last 24 hours"
      />
      <DataExplorer
        fires={[fire]}
        incidents={[]}
        layer="detections"
        onSelect={() => {}}
        selectedKey={null}
        selectedResultRef={createRef()}
      />
    </main>,
  );

  const results = await axe.run(container);
  expect(results.violations).toEqual([]);
});
