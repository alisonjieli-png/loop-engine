// Known answers for the Fresnel rim material: the CPU rim and pulse, and the material the builder makes in each mode
// (with a minimal stand-in for THREE). Each guard also runs on a known-wrong input that it must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  FRESNEL_RIM_DEFAULTS, FRESNEL_RIM_FRAGMENT, FRESNEL_RIM_GLSL, FRESNEL_RIM_VERTEX,
  createFresnelRimMaterial, fresnelPulse, fresnelRim,
} from './fresnel_rim_material.mjs';

const FakeThree = {
  AdditiveBlending: 2,
  NormalBlending: 1,
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

// Values computed independently from bias + scale * (1 - clamp(c, 0, 1))^power.
const RIM_CASES = [
  [[1, 2.5, 0.02, 1.4], 0.02],
  [[0, 2.5, 0.02, 1.4], 1.42],
  [[0.5, 2, 0, 1], 0.25],
  [[-0.3, 3, 0.1, 1], 1.1],
  [[0.2, 2.5, 0.02, 1.4], 0.8214067631359246],
];

function rimProblems(rim) {
  const problems = [];
  for (const [args, expected] of RIM_CASES) {
    const actual = rim(...args);
    if (Math.abs(actual - expected) > 1e-12) problems.push(`rim(${args}) = ${actual}, expected ${expected}`);
  }
  let previous = -Infinity;
  for (let step = 100; step >= 0; step -= 1) {
    const value = rim(step / 100, 3, 0, 1);
    if (value < previous - 1e-15) problems.push(`the rim falls as the surface turns away at ${step / 100}`);
    previous = value;
  }
  return problems;
}

test('fresnelRim is bias facing the camera, bias + scale at the silhouette, and grows toward the edge', () => {
  assert.deepEqual(rimProblems(fresnelRim), []);
});

test('known wrong: a rim that uses N.V instead of 1 - N.V is refused', () => {
  const inverted = (cosTheta, power, bias, scale) => bias + scale * Math.min(Math.max(cosTheta, 0), 1) ** power;
  assert.notDeepEqual(rimProblems(inverted), []);
});

test('fresnelPulse starts at 1 and dips to 1 - depth', () => {
  assert.equal(fresnelPulse(0, 2, 0.35), 1);
  assert.ok(Math.abs(fresnelPulse(Math.PI / 2, 2, 0.4) - 0.6) < 1e-12);
  assert.ok(Math.abs(fresnelPulse(1, 3, 0.5) - 0.5025018758498887) < 1e-12);
  assert.equal(fresnelPulse(123.4, 0, 0.9), 1, 'no speed, no pulse');
});

test('invalid inputs are refused', () => {
  assert.throws(() => fresnelRim(0.5, 0, 0, 1), RangeError);
  assert.throws(() => fresnelRim(Number.NaN, 2, 0, 1), TypeError);
  assert.throws(() => fresnelPulse(0, 1, 1.5), RangeError);
  assert.throws(() => createFresnelRimMaterial(FakeThree, {rimColour: [1, 0, 0]}), TypeError);
  assert.throws(() => createFresnelRimMaterial(FakeThree, {mode: 'glow'}), RangeError);
  assert.throws(() => createFresnelRimMaterial(FakeThree, {mode: 'toString'}), RangeError);
  assert.throws(() => createFresnelRimMaterial(FakeThree, {power: 40}), RangeError);
  assert.throws(() => createFresnelRimMaterial(FakeThree, {lightDirection: [0, 0, 0]}), RangeError);
});

test('createFresnelRimMaterial wires every uniform and the blending of each mode', () => {
  const opaque = createFresnelRimMaterial(FakeThree, {power: 3, rimColor: [1, 0.5, 0], lightDirection: [0, 0, 2]});
  assert.deepEqual(Object.keys(opaque.uniforms).sort(), ['uAdditive', 'uAmbient', 'uBaseColor', 'uBias', 'uIntensity',
    'uLightDirection', 'uPower', 'uPulseDepth', 'uPulseSpeed', 'uRimColor', 'uScale', 'uTime']);
  assert.equal(opaque.uniforms.uPower.value, 3);
  assert.equal(opaque.uniforms.uAdditive.value, 0);
  assert.equal(opaque.blending, FakeThree.NormalBlending);
  assert.equal(opaque.transparent, false);
  assert.equal(opaque.depthWrite, true);
  const {x, y, z} = opaque.uniforms.uLightDirection.value;
  assert.deepEqual([x, y, z], [0, 0, 1]);
  assert.deepEqual([opaque.uniforms.uRimColor.value.r, opaque.uniforms.uRimColor.value.g], [1, 0.5]);
  const shell = createFresnelRimMaterial(FakeThree, {mode: 'additive'});
  assert.equal(shell.uniforms.uAdditive.value, 1);
  assert.equal(shell.blending, FakeThree.AdditiveBlending);
  assert.equal(shell.transparent, true);
  assert.equal(shell.depthWrite, false);
  assert.equal(shell.uniforms.uScale.value, FRESNEL_RIM_DEFAULTS.scale);
  assert.equal(opaque.vertexShader, FRESNEL_RIM_VERTEX);
  assert.equal(opaque.fragmentShader, FRESNEL_RIM_FRAGMENT);
  assert.ok(FRESNEL_RIM_FRAGMENT.includes(FRESNEL_RIM_GLSL), 'the fragment stage uses the shared rim chunk');
  for (const name of Object.keys(opaque.uniforms)) assert.match(FRESNEL_RIM_FRAGMENT, new RegExp(`uniform \\w+ ${name};`));
});
