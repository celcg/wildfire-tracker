import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppHeader } from "./AppHeader";
import { PrivacyNotice } from "./PrivacyNotice";

test("privacy navigation opens and focuses the disclosure", async () => {
  const user = userEvent.setup();
  render(
    <>
      <AppHeader />
      <PrivacyNotice />
    </>,
  );

  expect(screen.queryByRole("link", { name: "Methodology" })).toBeNull();

  await user.click(screen.getByRole("link", { name: "Privacy" }));

  const summary = screen.getByText("Privacy notice").closest("summary");
  expect(document.getElementById("privacy")).toHaveAttribute("open");
  expect(summary).toHaveFocus();
  expect(window.location.hash).toBe("#privacy");
});
