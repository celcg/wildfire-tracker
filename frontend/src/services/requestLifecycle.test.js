import assert from "node:assert/strict";
import test from "node:test";
import {
  isCurrentRequest,
  shouldClearVisibleData,
  supersedeRequest,
} from "./requestLifecycle.js";

test("superseding a request cancels it and rejects its later response", () => {
  const first = new AbortController();
  const second = new AbortController();
  const activeRequest = { current: first };

  supersedeRequest(activeRequest, second);

  assert.equal(first.signal.aborted, true);
  assert.equal(isCurrentRequest(activeRequest, first), false);
  assert.equal(isCurrentRequest(activeRequest, second), true);
});

test("an aborted current request cannot update state", () => {
  const request = new AbortController();
  const activeRequest = { current: request };
  request.abort();

  assert.equal(isCurrentRequest(activeRequest, request), false);
});

test("refreshing the same window retains visible successful data", () => {
  assert.equal(shouldClearVisibleData("3", "3"), false);
  assert.equal(shouldClearVisibleData("3", "5"), true);
});
