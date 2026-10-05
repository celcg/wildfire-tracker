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
  return {
    CircleMarker: Layer,
    MapContainer: ({ children, className, tabIndex }) => (
      <div className={className} tabIndex={tabIndex}>
        {children}
      </div>
    ),
    Polygon: Layer,
    Popup: ({ children }) => <div>{children}</div>,
    TileLayer: () => null,
    Tooltip: ({ children }) => <span>{children}</span>,
    useMap: () => ({ flyTo: mapMocks.flyTo, getZoom: mapMocks.getZoom }),
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

function Harness() {
  const [selectedKey, setSelectedKey] = useState(null);
  const selectedResultRef = useRef(null);
  return (
    <>
      <FireMap
        fires={[fire]}
        hasError={false}
        incidents={[]}
        layer="detections"
        loading={false}
        onReturnToResult={() => selectedResultRef.current?.focus()}
        onSelect={setSelectedKey}
        observationWindow="Last 24 hours"
        selectedKey={selectedKey}
      />
      <DataExplorer
        fires={[fire]}
        incidents={[]}
        layer="detections"
        onSelect={setSelectedKey}
        selectedKey={selectedKey}
        selectedResultRef={selectedResultRef}
      />
    </>
  );
}

test("list selection moves the map and the return action restores row focus", async () => {
  const user = userEvent.setup();
  render(<Harness />);

  await user.click(screen.getByRole("button", { name: "Show on map" }));
  await waitFor(() =>
    expect(mapMocks.flyTo).toHaveBeenCalledWith([42.1, -8.6], 9, {
      duration: 0.55,
    }),
  );

  await user.click(
    screen.getByRole("button", { name: "Return to selected record" }),
  );
  expect(screen.getByRole("button", { name: "Selected on map" })).toHaveFocus();
});

test("map selection updates the list and Escape restores row focus", async () => {
  const user = userEvent.setup();
  render(<Harness />);

  await user.click(screen.getByRole("button", { name: "map result" }));
  const selectedButton = screen.getByRole("button", {
    name: "Selected on map",
  });
  expect(selectedButton).toHaveAttribute("aria-pressed", "true");

  fireEvent.keyDown(
    screen.getByLabelText("Map of satellite thermal detections"),
    { key: "Escape" },
  );
  expect(selectedButton).toHaveFocus();
});
