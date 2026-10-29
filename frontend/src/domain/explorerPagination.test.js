import assert from "node:assert/strict";
import test from "node:test";
import {
  EXPLORER_PAGE_SIZE,
  getPageForIndex,
  paginate,
} from "./explorerPagination.js";

test("paginates records with a partial final page", () => {
  const records = Array.from({ length: 58 }, (_, index) => index);
  const result = paginate(records, 3);

  assert.equal(EXPLORER_PAGE_SIZE, 25);
  assert.equal(result.page, 3);
  assert.equal(result.totalPages, 3);
  assert.equal(result.startIndex, 50);
  assert.deepEqual(result.items, records.slice(50));
});

test("clamps invalid pages and locates a selected record", () => {
  assert.equal(paginate([], 8).page, 1);
  assert.equal(paginate([1, 2, 3], 99).page, 1);
  assert.equal(getPageForIndex(0), 1);
  assert.equal(getPageForIndex(24), 1);
  assert.equal(getPageForIndex(25), 2);
  assert.equal(getPageForIndex(-1), 1);
});
