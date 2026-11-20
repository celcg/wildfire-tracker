import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState } from "react";
import { DataExplorer } from "./DataExplorer";
import { FireMap } from "./FireMap";

const mapMocks = vi.hoisted(() => ({
  flyTo: vi.fn(),
  getZoom: vi.fn(() => 5),
  openPopup: vi.fn(),
}));

vi.mock("react-leaflet", async () => {
  const React = await import("react");
  const Layer = React.forwardRef(function Layer(
    { children, eventHandlers, pathOptions },
    ref,
  ) {
    React.useImperativeHandle(ref, () => ({ openPopup: mapMocks.openPopup }));
    return (
      <button
        aria-label="map result"
        data-weight={pathOptions?.weight}
        onClick={eventHandlers?.click}
        type="button"
      >
        {children}
      </button>
    );
  });
  const map = { flyTo: mapMocks.flyTo, getZoom: mapMocks.getZoom };
  return {
    CircleMarker: Layer,
    MapContainer: ({
      bounds,
      children,
      className,
      minZoom,
      tabIndex,
    }) => (
      <div
        className={className}
        data-bounds={JSON.stringify(bounds)}
        data-min-zoom={minZoom}
        data-testid="fire-map"
        tabIndex={tabIndex}
      >
        {children}
      </div>
    ),
    Polygon: Layer,
    Popup: ({ children }) => <div>{children}</div>,
    TileLayer: () => null,
    Tooltip: ({ children }) => <span>{children}</span>,
    useMap: () => map,
  };
});

const fire = {
  latitude: 42.1,
  longitude: -8.6,
  confidence: "n",
  acq_date: "2026-09-23",
  acq_time: "1015",
  satellite: "Suomi NPP",
  frp: 8,
};

const fires = [fire];
const incidents = [];

function Harness() {
  const [selectedKey, setSelectedKey] = useState(null);
  const [focusRequest, setFocusRequest] = useState(0);
  const [mapNavigationRequest, setMapNavigationRequest] = useState(0);
  const mapFocusRef = useRef(null);
  const selectedResultRef = useRef(null);
  const showOnMap = (key) => {
    setSelectedKey(key);
    setMapNavigationRequest((request) => request + 1);
    mapFocusRef.current?.focus();
  };
  return (
    <>
      <FireMap
        fires={fires}
        hasError={false}
        incidents={incidents}
        layer="detections"
        loading={false}
        mapFocusRef={mapFocusRef}
        mapNavigationRequest={mapNavigationRequest}
        onReturnToResult={() => setFocusRequest((request) => request + 1)}
        onSelect={setSelectedKey}
        observationWindow="Last 24 hours"
        selectedKey={selectedKey}
      />
      <DataExplorer
        fires={fires}
        focusRequest={focusRequest}
        incidents={incidents}
        layer="detections"
        onShowOnMap={showOnMap}
        selectedKey={selectedKey}
        selectedResultRef={selectedResultRef}
      />
    </>
  );
}

test("show on map can navigate repeatedly without clearing the selection", async () => {
  const user = userEvent.setup();
  render(<Harness />);

  await user.click(screen.getByRole("button", { name: "Show on map" }));
  await waitFor(() =>
    expect(mapMocks.flyTo).toHaveBeenCalledWith([42.1, -8.6], 9, {
      duration: 0.55,
    }),
  );
  const mapRegion = screen.getByLabelText(
    "Map of satellite thermal detections",
  );
  expect(mapRegion).toHaveFocus();

  fireEvent.keyDown(mapRegion, { key: "Escape" });
  const selectedButton = screen.getByRole("button", {
    name: "Show on map again",
  });
  expect(selectedButton).toHaveFocus();

  await user.click(selectedButton);
  expect(mapRegion).toHaveFocus();
  expect(mapMocks.flyTo).toHaveBeenCalledTimes(2);
});

test("map selection updates the list and Escape restores row focus", async () => {
  const user = userEvent.setup();
  render(<Harness />);

  await user.click(screen.getByRole("button", { name: "map result" }));
  const selectedButton = screen.getByRole("button", {
    name: "Show on map again",
  });
  expect(selectedButton).toHaveAttribute("aria-pressed", "true");

  fireEvent.keyDown(
    screen.getByLabelText("Map of satellite thermal detections"),
    { key: "Escape" },
  );
  expect(selectedButton).toHaveFocus();

  fireEvent.keyDown(selectedButton, { key: "Escape" });
  expect(
    screen.getByLabelText("Map of satellite thermal detections"),
  ).toHaveFocus();
});

test("map opens on the whole peninsula and allows a wider zoom", () => {
  render(<Harness />);

  const map = screen.getByTestId("fire-map");
  expect(map).toHaveAttribute("data-bounds", "[[36,-10],[44,4.5]]");
  expect(map).toHaveAttribute("data-min-zoom", "4");
});
