// Known answers for the triplanar material: blend weights, planar coordinates and the checker on the CPU, and the
// material the builder makes (with a minimal stand-in for THREE). Each guard also runs on a known-wrong input.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TRIPLANAR_DEFAULTS, TRIPLANAR_FRAGMENT, TRIPLANAR_GLSL, TRIPLANAR_VERTEX,
  createTriplanarMaterial, triplanarChecker, triplanarCoordinates, triplanarWeights,
} from './triplanar_mapping_material.mjs';

const FakeThree = {
  Color: class {
    constructor(r, g, b) {
      this.isColor = true;
      if (g === undefined) Object.assign(this, {source: r});
      else Object.assign(this, {r, g, b});
    }
  },
  Vector3: class { constructor(x, y, z) { Object.assign(this, {x, y, z}); } },
  ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters, {isShaderMaterial: true}); } },
};

// Values computed independently: |n|^k normalized by the sum.
const WEIGHT_CASES = [
  [[[1, 0, 0], 4], [1, 0, 0]],
  [[[0, -1, 0], 4], [0, 1, 0]],
  [[[1 / Math.sqrt(3), 1 / Math.sqrt(3), 1 / Math.sqrt(3)], 4], [1 / 3, 1 / 3, 1 / 3]],
  [[[0.6, 0.8, 0], 1], [0.4285714285714286, 0.5714285714285715, 0]],
  [[[0.6, 0.8, 0], 2], [0.36, 0.6400000000000001, 0]],
  [[[-0.48, 0.6, 0.64], 3], [0.18784650505489722, 0.36688770518534614, 0.44526578975975656]],
];

function weightProblems(weights) {
  const problems = [];
  for (const [args, expected] of WEIGHT_CASES) {
    const actual = weights(...args);
    const sum = actual[0] + actual[1] + actual[2];
    if (Math.abs(sum - 1) > 1e-12) problems.push(`weights of ${args[0]} sum to ${sum}`);
    actual.forEach((value, axis) => {
      if (Math.abs(value - expected[axis]) > 1e-12) problems.push(`weight ${axis} of ${args[0]} is ${value}`);
    });
  }
  return problems;
}

test('triplanarWeights normalize |n|^sharpness', () => {
  assert.deepEqual(weightProblems(triplanarWeights), []);
});

test('known wrong: weights that are not normalized are refused', () => {
  const raw = (normal, sharpness) => normal.map((component) => Math.abs(component) ** sharpness);
  assert.notDeepEqual(weightProblems(raw), []);
});

test('triplanarCoordinates orient every projection and follow the scale', () => {
  assert.deepEqual(triplanarCoordinates([1, 2, 3], [1, 0, 0], 2), [[-6, 4], [2, -6], [2, 4]]);
  assert.deepEqual(triplanarCoordinates([1, 2, 3], [-0.2, -0.9, -0.3], 0.5), [[1.5, 1], [0.5, 1.5], [-0.5, 1]]);
  assert.throws(() => triplanarCoordinates([1, 2, 3], [0, 1, 0], 0), RangeError);
});

test('triplanarChecker alternates across cells, also below zero', () => {
  assert.deepEqual([[0.5, 0.5], [1.5, 0.5], [-0.5, 0.5], [-0.5, -0.5], [2.2, -3.7]].map(([u, v]) => triplanarChecker(u, v)),
    [0, 1, 1, 0, 0]);
  assert.throws(() => triplanarChecker(Number.NaN, 0), TypeError);
});

test('createTriplanarMaterial wires the uniforms, the map and the space', () => {
  const texture = {isTexture: true};
  const material = createTriplanarMaterial(FakeThree, {map: texture, space: 'object', scale: 0.5, lightDirection: [0, 3, 0]});
  assert.deepEqual(Object.keys(material.uniforms).sort(), ['uAmbient', 'uCheckerA', 'uCheckerB', 'uHasMap',
    'uLightDirection', 'uMap', 'uObjectSpace', 'uScale', 'uSharpness', 'uTint']);
  assert.equal(material.uniforms.uMap.value, texture);
  assert.equal(material.uniforms.uHasMap.value, 1);
  assert.equal(material.uniforms.uObjectSpace.value, 1);
  assert.equal(material.uniforms.uScale.value, 0.5);
  const {x, y, z} = material.uniforms.uLightDirection.value;
  assert.deepEqual([x, y, z], [0, 1, 0]);
  const checker = createTriplanarMaterial(FakeThree);
  assert.equal(checker.uniforms.uMap.value, null);
  assert.equal(checker.uniforms.uHasMap.value, 0);
  assert.equal(checker.uniforms.uSharpness.value, TRIPLANAR_DEFAULTS.sharpness);
  assert.equal(material.vertexShader, TRIPLANAR_VERTEX);
  assert.equal(material.fragmentShader, TRIPLANAR_FRAGMENT);
  assert.ok(TRIPLANAR_FRAGMENT.includes(TRIPLANAR_GLSL));
  for (const name of Object.keys(material.uniforms)) assert.match(TRIPLANAR_FRAGMENT, new RegExp(`uniform \\w+ ${name};`));
});

test('known wrong: invalid options are refused', () => {
  assert.throws(() => createTriplanarMaterial(FakeThree, {texture: null}), TypeError);
  assert.throws(() => createTriplanarMaterial(FakeThree, {map: {}}), TypeError);
  assert.throws(() => createTriplanarMaterial(FakeThree, {space: 'view'}), RangeError);
  assert.throws(() => createTriplanarMaterial(FakeThree, {sharpness: 0.5}), RangeError);
  assert.throws(() => createTriplanarMaterial(FakeThree, {checkerColors: [[1, 1, 1]]}), TypeError);
  assert.throws(() => triplanarWeights([1, 0], 4), TypeError);
});
