import assert from "node:assert/strict";
import test from "node:test";
import { resolveApiUrl } from "./fireConfig.js";

test("development uses the local FastAPI server by default", () => {
  assert.equal(resolveApiUrl({ DEV: true }), "/api");
});

test("production uses Cloud Run and an explicit URL always wins", () => {
  assert.match(resolveApiUrl({ PROD: true }), /run\.app$/);
  assert.equal(
    resolveApiUrl({ DEV: true, VITE_API_URL: "https://api.example.com" }),
    "https://api.example.com",
  );
});
