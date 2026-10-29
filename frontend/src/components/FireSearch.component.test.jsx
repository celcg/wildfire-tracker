import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { FireSearch } from "./FireSearch";
import { interpretFireSearch } from "../services/fireApi.js";

vi.mock("../services/fireApi.js", () => ({
  interpretFireSearch: vi.fn(),
}));

test("applies schema-validated filters and exposes them as readable labels", async () => {
  const user = userEvent.setup();
  const onApply = vi.fn();
  interpretFireSearch.mockResolvedValue({
    data: {
      status: "filters",
      filters: { days: 3, layer: "clusters", place: "Galicia", sort: "persistent", limit: 20 },
    },
  });

  const { rerender } = render(
    <FireSearch activeFilters={null} onApply={onApply} onClear={vi.fn()} />,
  );
  await user.type(screen.getByLabelText("Search question"), "Clusters near Galicia");
  await user.click(screen.getByRole("button", { name: "Apply search" }));

  expect(onApply).toHaveBeenCalledWith(expect.objectContaining({ days: 3, place: "Galicia" }));
  rerender(
    <FireSearch
      activeFilters={{ days: 3, layer: "clusters", place: "Galicia", sort: "persistent", limit: 20 }}
      onApply={onApply}
      onClear={vi.fn()}
    />,
  );
  expect(screen.getByText("Last 3 days")).toBeVisible();
  expect(screen.getByText("Galicia")).toBeVisible();
});

test("never presents generated emergency advice", async () => {
  const user = userEvent.setup();
  interpretFireSearch.mockResolvedValue({ data: { status: "emergency_advice" } });
  render(<FireSearch activeFilters={null} onApply={vi.fn()} onClear={vi.fn()} />);

  await user.type(screen.getByLabelText("Search question"), "Should I evacuate?");
  await user.click(screen.getByRole("button", { name: "Apply search" }));

  expect(screen.getByText(/cannot advise on evacuation/i)).toBeVisible();
});
