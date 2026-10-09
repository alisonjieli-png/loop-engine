// Known answers for the toon band material: the CPU band function, the light direction helper and the material the
// builder makes (with a minimal stand-in for THREE). Each guard also runs on a known-wrong input that it must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TOON_BAND_DEFAULTS, TOON_BAND_FRAGMENT, TOON_BAND_GLSL, TOON_BAND_VERTEX,
  createToonBandMaterial, toonBandLevel, toonLightDirection,
} from './toon_band_material.mjs';

// The part of THREE the builder touches: Color, Vector3 and ShaderMaterial.
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

// Problems with a candidate band function: levels at the band centres, flat shadow, full light, monotonic.
function bandProblems(level) {
  const problems = [];
  const centres = [[-0.6, 0], [0.15, 1 / 3], [0.5, 2 / 3], [0.85, 1], [1, 1]];
  for (const [nDotL, expected] of centres) {
    const actual = level(nDotL, 3, 0);
    if (Math.abs(actual - expected) > 1e-9) problems.push(`level(${nDotL}) = ${actual}, expected ${expected}`);
  }
  let previous = -Infinity;
  for (let step = 0; step <= 200; step += 1) {
    const value = level(-1 + step / 100, 4, 0.05);
    if (value < previous - 1e-12) problems.push(`decreases at ${-1 + step / 100}`);
    previous = value;
  }
  return problems;
}

test('toonBandLevel gives the band levels and never decreases', () => {
  assert.deepEqual(bandProblems(toonBandLevel), []);
  assert.equal(toonBandLevel(0, 3, 0.1), 0.5 / 3, 'a soft edge is half way at its centre');
  assert.equal(toonBandLevel(1, 1, 0), 1);
});

test('known wrong: a floor-quantized band function without the shadow edge is refused', () => {
  const wrong = (nDotL, bands) => Math.floor(Math.max(nDotL, 0) * bands) / bands;
  assert.notDeepEqual(bandProblems(wrong), []);
});

test('toonBandLevel refuses impossible band counts and softness', () => {
  for (const bands of [0, 17, 2.5, Number.NaN]) assert.throws(() => toonBandLevel(0.5, bands, 0), RangeError);
  for (const softness of [-0.1, 0.6, Number.NaN]) assert.throws(() => toonBandLevel(0.5, 3, softness), RangeError);
});

test('toonLightDirection points from the target to the light', () => {
  const direction = toonLightDirection([3, 4, 0], [0, 0, 0]);
  assert.deepEqual(direction, [0.6, 0.8, 0]);
  assert.deepEqual(toonLightDirection([1, 5, 1], [1, 1, 1]), [0, 1, 0]);
  assert.throws(() => toonLightDirection([1, 1, 1], [1, 1, 1]), RangeError);
});

test('createToonBandMaterial wires every uniform from the options', () => {
  const material = createToonBandMaterial(FakeThree, {bands: 4, color: [0.2, 0.4, 0.6], lightDirection: [0, 2, 0]});
  assert.equal(material.isShaderMaterial, true);
  assert.deepEqual(Object.keys(material.uniforms).sort(), ['uBands', 'uColor', 'uLightDirection', 'uRimColor',
    'uRimStrength', 'uRimWidth', 'uShadowColor', 'uSoftness', 'uSpecularColor', 'uSpecularSize']);
  assert.equal(material.uniforms.uBands.value, 4);
  assert.deepEqual([material.uniforms.uColor.value.r, material.uniforms.uColor.value.g], [0.2, 0.4]);
  const {x, y, z} = material.uniforms.uLightDirection.value;
  assert.deepEqual([x, y, z], [0, 1, 0]);
  assert.equal(material.uniforms.uSoftness.value, TOON_BAND_DEFAULTS.softness);
  assert.equal(material.vertexShader, TOON_BAND_VERTEX);
  assert.equal(material.fragmentShader, TOON_BAND_FRAGMENT);
  assert.ok(TOON_BAND_FRAGMENT.includes(TOON_BAND_GLSL), 'the fragment stage uses the shared band chunk');
  for (const name of Object.keys(material.uniforms)) assert.match(TOON_BAND_FRAGMENT, new RegExp(`uniform \\w+ ${name};`));
});

test('known wrong: misspelt options and out-of-range values are refused', () => {
  assert.throws(() => createToonBandMaterial(FakeThree, {band: 3}), TypeError);
  assert.throws(() => createToonBandMaterial(FakeThree, {bands: 40}), RangeError);
  assert.throws(() => createToonBandMaterial(FakeThree, {rimWidth: 2}), RangeError);
  assert.throws(() => createToonBandMaterial(FakeThree, {color: [1, 2]}), TypeError);
});
