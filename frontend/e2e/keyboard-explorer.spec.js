import { expect, test } from "@playwright/test";

test("a keyboard user can skip to and select a detection", async ({ page }) => {
  await page.route("**/api/fires?**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      headers: { "X-Data-Stale": "false" },
      json: [
        {
          latitude: 42.1,
          longitude: -8.6,
          confidence: "h",
          acq_date: "2026-09-23",
          acq_time: "1015",
          satellite: "NOAA-20",
          frp: 18.4,
        },
      ],
    });
  });
  await page.route("https://*.tile.openstreetmap.org/**", (route) => route.abort());
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Show on map" })).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Map of satellite thermal detections" }),
  ).toHaveAttribute("aria-describedby", "map-instructions");

  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to data explorer" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#data-explorer")).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Show on map" })).toBeFocused();
  await page.keyboard.press("Enter");

  await expect(page.getByRole("button", { name: "Selected on map" })).toBeFocused();
  await expect(
    page.getByRole("button", { name: "Return to selected record" }),
  ).toBeVisible();
});
