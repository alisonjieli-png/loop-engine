import test from 'node:test';
import assert from 'node:assert/strict';
import { clamp } from './clamp.mjs';

test('clamp preserves values inside the interval', () => {
  for (const [value, lower, upper] of [[5, 0, 10], [-2, -5, 3], [0.5, 0, 1]]) {
    assert.equal(clamp(value, lower, upper), value);
  }
});
test('clamp handles both outer regions and boundary values', () => {
  assert.equal(clamp(-7, -5, 3), -5);
  assert.equal(clamp(12, 0, 10), 10);
  assert.equal(clamp(-5, -5, 3), -5);
  assert.equal(clamp(3, -5, 3), 3);
  assert.equal(clamp(12, 4, 4), 4);
});
test('clamp rejects reversed bounds and nonfinite values', () => {
  assert.throws(() => clamp(2, 3, 1), RangeError);
  assert.throws(() => clamp(NaN, 0, 1), TypeError);
  assert.throws(() => clamp(0, -Infinity, 1), TypeError);
  assert.throws(() => clamp(0, 0, Infinity), TypeError);
});
