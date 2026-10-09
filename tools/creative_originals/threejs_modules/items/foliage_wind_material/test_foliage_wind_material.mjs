// Known answers for the foliage wind: gust noise and wind offsets from an independent Python port of the same integer
// hash and formula; roots never move, offsets run along the wind direction and drop slightly, and zero strength is
// still. Known-wrong control: a wind that bends the whole blade evenly (no height weighting) is refused by the
// root check. The material and its uniforms are built with a minimal stand-in for THREE.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  FOLIAGE_WIND_DEFAULTS, FOLIAGE_WIND_FRAGMENT, FOLIAGE_WIND_GLSL, FOLIAGE_WIND_UNIFORMS_GLSL, FOLIAGE_WIND_VERTEX,
  createFoliageWindMaterial, foliageWindUniforms, windGustNoise, windOffset,
} from './foliage_wind_material.mjs';

const FakeThree = {
  DoubleSide: 'double',
  Color: class { constructor(r, g, b) { Object.assign(this, {r, g, b}); } },
  Vector2: class { constructor(x, y) { Object.assign(this, {x, y}); } },
  Vector3: class { constructor(x, y, z) { Object.assign(this, {x, y, z}); } },
  ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } },
};

function close(actual, expected, tolerance, label) {
  actual.forEach((value, index) => assert.ok(Math.abs(value - expected[index]) <= tolerance, `${label}: [${actual}]`));
}

// Problems with a wind function: a root (y = 0) that moves, an offset off the wind direction, or a tip that rises.
function windProblems(wind) {
  const problems = [];
  for (let step = 0; step < 300; step += 1) {
    const anchor = [Math.sin(step) * 9, 0, Math.cos(step * 1.3) * 9];
    const time = step * 0.071;
    const root = wind([0.03, 0, 0.01], anchor, time);
    if (root.some((value) => value !== 0)) problems.push(`step ${step}: the root moved`);
    const tip = wind([0, 1, 0], anchor, time);
    if (Math.abs(tip[0] * 0.35 - tip[2] * 1) > 1e-12) problems.push(`step ${step}: off the wind direction`);
    if (tip[1] > 0) problems.push(`step ${step}: the tip rose`);
  }
  return problems.slice(0, 5);
}

test('windGustNoise matches an independent port and is continuous', () => {
  const known = [[0, 0.20343191926447488], [1, 0.9561599206542969], [2.5, 0.35402834784566156],
    [-3.25, 0.6176640751856413], [17.75, 0.1636804878743553]];
  for (const [x, expected] of known) assert.ok(Math.abs(windGustNoise(x) - expected) < 1e-12, `gust ${x}`);
  for (let step = 0; step < 5000; step += 1) {
    const x = step * 0.01 - 25;
    const value = windGustNoise(x);
    assert.ok(value >= 0 && value <= 1);
    assert.ok(Math.abs(windGustNoise(x + 1e-6) - value) < 1e-5, 'continuous');
  }
});

test('windOffset matches an independent port; roots stay, tips move along the wind', () => {
  close(windOffset([0, 1, 0], [2, 0, -1], 3.7), [-0.03412905249140244, -0.0006537396356980567, -0.01194516837199085], 1e-12, 'tip');
  close(windOffset([0.02, 0.5, 0], [-4, 0, 3], 1.25), [0.022463296882014063, -0.0002832065854468334, 0.00786215390870492], 1e-12, 'mid');
  assert.deepEqual(windProblems((position, anchor, time) => windOffset(position, anchor, time)), []);
  assert.deepEqual(windOffset([0, 1, 0], [2, 0, -1], 3.7, {strength: 0}).map(Math.abs), [0, 0, 0], 'no wind, no sway');
});

test('known wrong: a wind without height weighting is refused', () => {
  const rigid = (position, anchor, time) => windOffset([position[0], 1, position[2]], anchor, time);
  assert.notDeepEqual(windProblems(rigid), []);
});

test('the material: double-sided, the wind uniforms declared once in the shared chunk', () => {
  const material = createFoliageWindMaterial(FakeThree, {direction: [0, 2], strength: 0.3});
  assert.equal(material.side, 'double');
  assert.deepEqual([material.uniforms.uWindDirection.value.x, material.uniforms.uWindDirection.value.y], [0, 1]);
  assert.equal(material.uniforms.uWindStrength.value, 0.3);
  const uniforms = foliageWindUniforms(FakeThree);
  assert.equal(uniforms.uBladeHeight.value, FOLIAGE_WIND_DEFAULTS.height);
  const declared = `${FOLIAGE_WIND_UNIFORMS_GLSL}${FOLIAGE_WIND_FRAGMENT}`;
  for (const name of Object.keys(uniforms)) assert.match(declared, new RegExp(`uniform \\w+ ${name};`), name);
  assert.ok(FOLIAGE_WIND_VERTEX.includes(FOLIAGE_WIND_GLSL) && FOLIAGE_WIND_VERTEX.includes(FOLIAGE_WIND_UNIFORMS_GLSL));
  assert.equal(material.fragmentShader, FOLIAGE_WIND_FRAGMENT);
});

test('invalid options are refused', () => {
  assert.throws(() => createFoliageWindMaterial(FakeThree, {windStrength: 1}), TypeError);
  assert.throws(() => createFoliageWindMaterial(FakeThree, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => windOffset([0, 1, 0], [0, 0, 0], 0, {direction: [0, 0]}), TypeError);
  assert.throws(() => windOffset([0, 1, 0], [0, 0, 0], 0, {stiffness: 0.1}), RangeError);
  assert.throws(() => windGustNoise(Number.POSITIVE_INFINITY), RangeError);
});
