/* Pure, offline selection controls. No browser, API, model, or media generation. */
import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const source = readFileSync(new URL("../src/loop_engine/core/service_runtime/web_assets/gallery-random.js", import.meta.url));
const {choosePreview, exactPreview, requestedPreview} = await import(`data:text/javascript;base64,${source.toString("base64")}`);
const items = [{id: "first-abc123"}, {id: "second-def456"}, {id: "third-789abc"}];

test("fixed entropy gives deterministic bounded selection", () => {
  assert.equal(choosePreview(items, null, 0).id, items[0].id);
  assert.equal(choosePreview(items, null, 4).id, items[1].id);
  assert.deepEqual(choosePreview(items, null, 99), choosePreview(items, null, 99));
});
test("another does not immediately repeat when alternatives exist", () => {
  for (let n = 0; n < 100; n++) for (const current of items)
    assert.notEqual(choosePreview(items, current.id, n).id, current.id);
});
test("empty and singleton selections terminate without retries", () => {
  assert.equal(choosePreview([], null, 2), null);
  assert.equal(choosePreview([items[0]], items[0].id, 2), items[0]);
});
test("invalid entropy is refused", () => {
  for (const value of [-1, 0.5, NaN, Infinity, "2"]) assert.throws(() => choosePreview(items, null, value), TypeError);
});
test("unknown exact identity never becomes a random fallback", () => {
  assert.equal(exactPreview(items, items[1].id), items[1]);
  assert.equal(exactPreview(items, "removed-version"), null);
  assert.equal(exactPreview(items, null), null);
});
test("permalink parsing separates absent, valid, invalid and repeated values", () => {
  assert.equal(requestedPreview(""), undefined);
  assert.equal(requestedPreview("?asset=first-abc123"), "first-abc123");
  assert.equal(requestedPreview("?asset=first%2Dabc123"), "first-abc123");
  for (const text of ["?asset=", "?asset=one&asset=two", "?asset=%2Fprivate", "?asset=UPPER", "?asset=" + "a".repeat(181)])
    assert.equal(requestedPreview(text), null);
});
