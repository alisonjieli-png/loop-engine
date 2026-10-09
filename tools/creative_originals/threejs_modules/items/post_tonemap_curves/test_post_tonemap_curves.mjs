// Known answers for the tone mapping curves: clamp, extended Reinhard, the ACES fit and the Hable filmic curve at
// several inputs and exposures, monotonicity, the white point mapping to 1, the shader definition and the material
// (with a minimal stand-in for THREE). Plain Reinhard (no white point) is refused where extended Reinhard is expected.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TONEMAP_DEFAULTS, TONEMAP_FRAGMENT, TONEMAP_OPERATORS, TONEMAP_VERTEX, createTonemapMaterial, createTonemapShader,
  hableCurve, tonemapColor, tonemapValue,
} from './post_tonemap_curves.mjs';

// Values computed independently with python3 from the published formulas (white point 4 for Reinhard).
const KNOWN = {
  clamp: [[0.18, 0.18], [0.5, 0.5], [2, 1]],
  reinhard: [[0.18, 0.15425847457627118], [0.5, 0.34375], [1, 0.53125], [2, 0.75], [4, 1]],
  aces: [[0.18, 0.2668989203894968], [0.5, 0.6163069544364508], [1, 0.8037974683544302], [2, 0.914855072463768],
    [4, 0.9734171097148379]],
  hable: [[0.18, 0.06710982928290175], [0.5, 0.17196964226803543], [1, 0.304300561467247], [2, 0.49291854599116447],
    [4, 0.7132380109726539]],
};

function curveProblems(curve) {
  const problems = [];
  for (const [operator, points] of Object.entries(KNOWN)) {
    for (const [input, expected] of points) {
      const actual = curve(input, {operator, whitePoint: 4});
      if (Math.abs(actual - expected) > 1e-12) problems.push(`${operator}(${input}) gave ${actual}, expected ${expected}`);
    }
  }
  return problems;
}

test('tonemapValue follows the four published curves', () => {
  assert.deepEqual(curveProblems(tonemapValue), []);
  assert.ok(Math.abs(tonemapValue(1, {operator: 'hable', exposure: 4}) - 0.7132380109726539) < 1e-12, 'exposure scales');
  assert.equal(tonemapValue(-3, {operator: 'aces'}), 0);
  assert.equal(tonemapValue(1000, {operator: 'hable'}), 1);
});

test('known wrong: plain Reinhard without the white point is refused', () => {
  const plain = (value, options) => (options.operator === 'reinhard' ? value / (1 + value) : tonemapValue(value, options));
  assert.notDeepEqual(curveProblems(plain), []);
});

test('every curve rises monotonically from 0 and the white point maps to 1', () => {
  for (const operator of Object.keys(TONEMAP_OPERATORS)) {
    let previous = -1;
    for (let step = 0; step <= 400; step += 1) {
      const value = tonemapValue(step / 25, {operator});
      assert.ok(value >= previous - 1e-15, `${operator} decreases at ${step / 25}`);
      previous = value;
    }
    assert.ok(Math.abs(tonemapValue(0, {operator})) < 1e-15);
  }
  assert.ok(Math.abs(tonemapValue(11.2, {operator: 'hable'}) - 1) < 1e-12);
  assert.equal(tonemapValue(6, {operator: 'reinhard', whitePoint: 6}), 1);
  assert.ok(Math.abs(hableCurve(1) - 0.22065727699530524) < 1e-12);
  assert.ok(Math.abs(hableCurve(11.2) - 0.7251293784387428) < 1e-12);
});

test('tonemapColor maps each channel', () => {
  const mapped = tonemapColor([0.5, 1, 4], {operator: 'reinhard'});
  [0.34375, 0.53125, 1].forEach((expected, channel) => assert.ok(Math.abs(mapped[channel] - expected) < 1e-12));
  assert.throws(() => tonemapColor([1, 2]), TypeError);
});

test('createTonemapShader selects the curve by number', () => {
  const shader = createTonemapShader({operator: 'hable', exposure: 2});
  assert.deepEqual(Object.keys(shader.uniforms).sort(), ['tDiffuse', 'uExposure', 'uOperator', 'uWhitePoint']);
  assert.equal(shader.uniforms.uOperator.value, TONEMAP_OPERATORS.hable);
  assert.equal(shader.uniforms.uExposure.value, 2);
  assert.equal(createTonemapShader().uniforms.uOperator.value, TONEMAP_OPERATORS[TONEMAP_DEFAULTS.operator]);
  assert.equal(shader.vertexShader, TONEMAP_VERTEX);
  assert.equal(shader.fragmentShader, TONEMAP_FRAGMENT);
  assert.doesNotMatch(TONEMAP_FRAGMENT, /tonemapping_fragment/);
  const FakeThree = {ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } }};
  const material = createTonemapMaterial(FakeThree, {operator: 'clamp'});
  assert.equal(material.uniforms.uOperator.value, 0);
  assert.equal(material.toneMapped, false);
});

test('known wrong: invalid options are refused', () => {
  assert.throws(() => tonemapValue(1, {operator: 'filmic'}), TypeError);
  assert.throws(() => tonemapValue(1, {operator: 'toString'}), TypeError, 'an inherited name is not an operator');
  assert.throws(() => tonemapValue(1, {exposure: 0}), RangeError);
  assert.throws(() => tonemapValue(1, {whitePoint: 0.5}), RangeError);
  assert.throws(() => createTonemapShader({gamma: 2.2}), TypeError);
  assert.throws(() => createTonemapShader({toString: 1}), TypeError, 'an inherited name is not an option');
});
