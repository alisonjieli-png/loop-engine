// Known answers for the chromatic aberration pass: each channel's sample coordinate for centred, offset-centre,
// high-power and wide-frame settings, the dispersion weights and taps, the shader definition and the material (with
// a minimal stand-in for THREE). An aberration that moves every channel the same way is refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CHROMATIC_ABERRATION_DEFAULTS, CHROMATIC_ABERRATION_FRAGMENT, CHROMATIC_ABERRATION_VERTEX, aberrationOffset,
  createChromaticAberrationMaterial, createChromaticAberrationShader, dispersionTaps, dispersionWeights,
} from './post_chromatic_aberration.mjs';

// Coordinates computed independently: red = c + d (1 - s), blue = c + d (1 + s), s = strength (2 |d k|)^power.
const KNOWN = [
  [[1, 0.5, {strength: 0.1}], {red: [0.95, 0.5], green: [1, 0.5], blue: [1.05, 0.5]}],
  [[0.75, 0.5, {strength: 0.1, power: 2}], {red: [0.74375, 0.5], green: [0.75, 0.5], blue: [0.75625, 0.5]}],
  [[0.75, 0.5, {strength: 0.1, aspect: 2}], {red: [0.725, 0.5], green: [0.75, 0.5], blue: [0.775, 0.5]}],
  [[0.2, 0.9, {strength: 0.05, power: 1.5, center: [0.4, 0.6]}],
    {red: [0.20612353927600907, 0.8908146910859864], green: [0.2, 0.9], blue: [0.19387646072399095, 0.9091853089140136]}],
  [[0.5, 0.5, {strength: 0.3}], {red: [0.5, 0.5], green: [0.5, 0.5], blue: [0.5, 0.5]}],
];

function offsetProblems(offset) {
  const problems = [];
  for (const [[u, v, options], expected] of KNOWN) {
    const actual = offset(u, v, options);
    for (const channel of ['red', 'green', 'blue']) {
      for (let axis = 0; axis < 2; axis += 1) {
        if (Math.abs(actual[channel][axis] - expected[channel][axis]) > 1e-12) {
          problems.push(`${channel}[${axis}] at (${u}, ${v}) is ${actual[channel][axis]}`);
        }
      }
    }
  }
  return problems;
}

test('aberrationOffset gives each channel its sample coordinate', () => {
  assert.deepEqual(offsetProblems(aberrationOffset), []);
});

test('known wrong: an aberration that moves every channel the same way is refused', () => {
  const sameForAll = (u, v, options) => {
    const offsets = aberrationOffset(u, v, options);
    return {red: offsets.blue, green: offsets.blue, blue: offsets.blue};
  };
  assert.notDeepEqual(offsetProblems(sameForAll), []);
});

test('dispersionWeights normalizes triangular channel weights', () => {
  const close = (actual, expected) => actual.forEach((row, index) => row.forEach((value, channel) => {
    assert.ok(Math.abs(value - expected[index][channel]) < 1e-12, `row ${index} channel ${channel}`);
  }));
  close(dispersionWeights(3), [[0.75, 0.2, 0], [0.25, 0.6, 0.25], [0, 0.2, 0.75]]);
  close(dispersionWeights(2), [[1, 0.5, 0], [0, 0.5, 1]]);
  for (const samples of [2, 5, 8]) {
    const weights = dispersionWeights(samples);
    for (let channel = 0; channel < 3; channel += 1) {
      assert.ok(Math.abs(weights.reduce((sum, row) => sum + row[channel], 0) - 1) < 1e-12);
    }
  }
  assert.throws(() => dispersionWeights(1), RangeError);
  assert.throws(() => dispersionWeights(9), RangeError);
});

test('dispersionTaps spread from the red sample to the blue sample', () => {
  const taps = dispersionTaps(1, 0.5, {strength: 0.1, samples: 3});
  assert.equal(taps.length, 3);
  assert.ok(Math.abs(taps[0].uv[0] - 0.95) < 1e-12 && Math.abs(taps[1].uv[0] - 1) < 1e-12);
  assert.ok(Math.abs(taps[2].uv[0] - 1.05) < 1e-12);
  const three = dispersionTaps(1, 0.5, {strength: 0.1});
  assert.deepEqual(three.map((tap) => tap.weights), [[1, 0, 0], [0, 1, 0], [0, 0, 1]]);
  assert.ok(Math.abs(three[2].uv[0] - 1.05) < 1e-12);
});

test('createChromaticAberrationShader returns fresh ShaderPass-style definitions', () => {
  const first = createChromaticAberrationShader({samples: 4, center: [0.3, 0.6]});
  const second = createChromaticAberrationShader();
  assert.deepEqual(Object.keys(first.uniforms).sort(),
    ['tDiffuse', 'uAspect', 'uCenter', 'uPower', 'uSamples', 'uStrength']);
  assert.equal(first.uniforms.uSamples.value, 4);
  first.uniforms.uCenter.value[0] = 9;
  assert.deepEqual(second.uniforms.uCenter.value, [...CHROMATIC_ABERRATION_DEFAULTS.center]);
  assert.equal(first.vertexShader, CHROMATIC_ABERRATION_VERTEX);
  assert.equal(first.fragmentShader, CHROMATIC_ABERRATION_FRAGMENT);
  const FakeThree = {ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } }};
  const material = createChromaticAberrationMaterial(FakeThree, {strength: 0.02});
  assert.equal(material.uniforms.uStrength.value, 0.02);
  assert.equal(material.depthTest, false);
  assert.equal(material.depthWrite, false);
});

test('known wrong: invalid options are refused', () => {
  assert.throws(() => aberrationOffset(0, 0, {strength: 2}), RangeError);
  assert.throws(() => aberrationOffset(0, 0, {samples: 0}), RangeError);
  assert.throws(() => createChromaticAberrationShader({centre: [0.5, 0.5]}), TypeError);
  assert.throws(() => createChromaticAberrationShader({toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => createChromaticAberrationShader({center: [0.5, 2]}), TypeError);
});
