// Known answers for the vignette pass: the CPU amount at the centre, edges and corners for round and frame-shaped
// vignettes, the shader definition (fresh uniforms per call, the names three.js ShaderPass expects) and the material
// builder (with a minimal stand-in for THREE). A vignette that ignores the aspect ratio is refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  VIGNETTE_DEFAULTS, VIGNETTE_FRAGMENT, VIGNETTE_VERTEX, createVignetteMaterial, createVignetteShader, vignetteAmount,
} from './post_vignette.mjs';

// Values computed independently from the closed form smoothstep(inner, outer, 2 |(u - 0.5) k, v - 0.5|) * strength.
const KNOWN = [
  [[0.5, 0.5, {}], 0],
  [[0, 0.5, {}], 0.46424791369835133],
  [[0, 0, {}], 0.65],
  [[0.25, 0.75, {}], 0.14243471760901436],
  [[0, 0.5, {aspect: 2}], 0.65],
  [[0, 0.5, {aspect: 2, roundness: 0}], 0.46424791369835133],
];

function amountProblems(amount) {
  const problems = [];
  for (const [[u, v, options], expected] of KNOWN) {
    const actual = amount(u, v, options);
    if (Math.abs(actual - expected) > 1e-12) problems.push(`(${u}, ${v}, ${JSON.stringify(options)}) gave ${actual}`);
  }
  return problems;
}

test('vignetteAmount matches the closed form at known points', () => {
  assert.deepEqual(amountProblems(vignetteAmount), []);
  assert.equal(vignetteAmount(0, 0, {strength: 0}), 0);
  assert.equal(vignetteAmount(0.5, 0.5, {inner: 0, outer: 0}), 0, 'equal radii still give a defined step');
});

test('known wrong: a vignette that ignores the aspect ratio is refused', () => {
  const ignoresAspect = (u, v, options) => vignetteAmount(u, v, {...options, aspect: 1});
  assert.notDeepEqual(amountProblems(ignoresAspect), []);
});

test('createVignetteShader returns a fresh ShaderPass-style definition', () => {
  const first = createVignetteShader({strength: 0.3, color: [0.1, 0, 0.2]});
  const second = createVignetteShader();
  assert.deepEqual(Object.keys(first).sort(), ['fragmentShader', 'name', 'uniforms', 'vertexShader']);
  assert.deepEqual(Object.keys(first.uniforms).sort(),
    ['tDiffuse', 'uAspect', 'uColor', 'uInner', 'uOuter', 'uRoundness', 'uStrength']);
  assert.equal(first.uniforms.tDiffuse.value, null);
  assert.deepEqual(first.uniforms.uColor.value, [0.1, 0, 0.2]);
  first.uniforms.uColor.value[0] = 9;
  assert.deepEqual(second.uniforms.uColor.value, [...VIGNETTE_DEFAULTS.color], 'uniform values are not shared');
  assert.equal(second.uniforms.uStrength.value, VIGNETTE_DEFAULTS.strength);
  assert.equal(first.vertexShader, VIGNETTE_VERTEX);
  assert.equal(first.fragmentShader, VIGNETTE_FRAGMENT);
});

test('createVignetteMaterial makes a ShaderMaterial without depth', () => {
  const FakeThree = {ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } }};
  const material = createVignetteMaterial(FakeThree, {roundness: 0});
  assert.equal(material.uniforms.uRoundness.value, 0);
  assert.equal(material.depthTest, false);
  assert.equal(material.depthWrite, false);
});

test('known wrong: invalid options are refused', () => {
  assert.throws(() => vignetteAmount(0, 0, {strength: 2}), RangeError);
  assert.throws(() => createVignetteShader({inner: 1, outer: 0.5}), RangeError);
  assert.throws(() => createVignetteShader({colour: [0, 0, 0]}), TypeError);
  assert.throws(() => createVignetteShader({color: [0, 0]}), TypeError);
});
