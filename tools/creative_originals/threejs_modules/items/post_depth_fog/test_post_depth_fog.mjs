// Known answers for the depth fog pass: perspective and orthographic depth linearization and its inverse, the
// exponential squared fog with a start distance, the fogged colour of a plane at a known distance (all computed
// independently with python3), and the shader definition (with a minimal stand-in for THREE). Treating a perspective
// depth buffer as linear is refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEPTH_FOG_DEFAULTS, DEPTH_FOG_FRAGMENT, DEPTH_FOG_GLSL, DEPTH_FOG_VERTEX, applyDepthFogCpu, createDepthFogMaterial,
  createDepthFogShader, depthFromDistance, fogFactor, linearizeDepth,
} from './post_depth_fog.mjs';

function linearizeProblems(linearize) {
  const problems = [];
  const cases = [
    [[0, 0.1, 100], 0.1], [[1, 0.1, 100], 100.00000000000568], [[0.5, 0.1, 100], 0.1998001998001998],
    [[0.9853039412157649, 0.1, 50], 6.000000000000034], [[0.5, 1, 11, true], 6],
  ];
  for (const [input, expected] of cases) {
    const actual = linearize(...input);
    if (Math.abs(actual - expected) > 1e-9 * Math.max(1, expected)) problems.push(`${input} gave ${actual}`);
  }
  return problems;
}

test('linearizeDepth inverts the perspective and orthographic depth mappings', () => {
  assert.deepEqual(linearizeProblems(linearizeDepth), []);
  assert.ok(Math.abs(depthFromDistance(6, 0.1, 50) - 0.9853039412157649) < 1e-15);
  for (const distance of [0.1, 0.5, 3, 27.5, 50]) {
    assert.ok(Math.abs(linearizeDepth(depthFromDistance(distance, 0.1, 50), 0.1, 50) - distance) < 1e-9 * distance);
    assert.ok(Math.abs(linearizeDepth(depthFromDistance(distance, 0.1, 50, true), 0.1, 50, true) - distance) < 1e-12);
  }
});

test('known wrong: reading a perspective depth buffer as linear depth is refused', () => {
  const linear = (depth, near, far) => near + depth * (far - near);
  assert.notDeepEqual(linearizeProblems(linear), []);
});

test('fogFactor is exponential squared fog after the start distance', () => {
  assert.ok(Math.abs(fogFactor(10, {density: 0.12}) - 0.7630722413178782) < 1e-15);
  assert.ok(Math.abs(fogFactor(10, {density: 0.12, start: 4}) - 0.4045274577607302) < 1e-15);
  assert.equal(fogFactor(3, {density: 0.12, start: 4}), 0);
  assert.equal(fogFactor(1000, {density: 0}), 0);
  assert.ok(fogFactor(1e6) > 0.999999);
});

test('applyDepthFogCpu fogs a plane at a known distance', () => {
  const options = {density: 0.15, start: 1, near: 0.1, far: 50, color: [0.5, 0.6, 0.7]};
  const fogged = applyDepthFogCpu([0.8, 0.3, 0.2], depthFromDistance(6, 0.1, 50), options);
  [0.6709348474192769, 0.4290651525807231, 0.4151085876345385].forEach((expected, channel) => {
    assert.ok(Math.abs(fogged[channel] - expected) < 1e-9, `channel ${channel}: ${fogged[channel]}`);
  });
  assert.deepEqual(applyDepthFogCpu([0.2, 0.4, 0.6], 0.5, {density: 0}), [0.2, 0.4, 0.6]);
});

test('the shader definition carries the camera range and the chunk', () => {
  const shader = createDepthFogShader({near: 0.5, far: 300, orthographic: true, density: 0.02});
  assert.deepEqual(Object.keys(shader.uniforms).sort(), ['cameraFar', 'cameraNear', 'tDepth', 'tDiffuse',
    'uDensity', 'uFogColor', 'uOrthographic', 'uStart']);
  assert.deepEqual([shader.uniforms.cameraNear.value, shader.uniforms.cameraFar.value], [0.5, 300]);
  assert.equal(shader.uniforms.uOrthographic.value, 1);
  assert.deepEqual(createDepthFogShader().uniforms.uFogColor.value, [...DEPTH_FOG_DEFAULTS.color]);
  assert.ok(DEPTH_FOG_FRAGMENT.includes(DEPTH_FOG_GLSL));
  assert.equal(shader.vertexShader, DEPTH_FOG_VERTEX);
  const FakeThree = {ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } }};
  assert.equal(createDepthFogMaterial(FakeThree, {start: 5}).uniforms.uStart.value, 5);
});

test('known wrong: invalid cameras, depths and options are refused', () => {
  assert.throws(() => linearizeDepth(0.5, 0, 10), RangeError);
  assert.throws(() => linearizeDepth(0.5, 10, 1), RangeError);
  assert.throws(() => linearizeDepth(1.5, 0.1, 10), RangeError);
  assert.throws(() => depthFromDistance(0.01, 0.1, 10), RangeError);
  assert.throws(() => createDepthFogShader({density: -1}), RangeError);
  assert.throws(() => createDepthFogShader({colour: [1, 1, 1]}), TypeError);
  assert.throws(() => createDepthFogShader({toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => createDepthFogShader({orthographic: 'yes'}), TypeError);
});
