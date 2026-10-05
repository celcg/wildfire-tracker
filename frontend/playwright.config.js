import { defineConfig } from "@playwright/test";
import os from "node:os";
import path from "node:path";

export default defineConfig({
  testDir: "./e2e",
  // Keep disposable traces outside OneDrive, which can lock generated files.
  outputDir:
    process.env.PLAYWRIGHT_OUTPUT_DIR ??
    path.join(os.tmpdir(), "wildfire-playwright-results"),
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: true,
  },
});
