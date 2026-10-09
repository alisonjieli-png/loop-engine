// Known answers for the force-field ripples: intensities from an independent Python port of the ring formula, the
// ring's peak travelling at the ripple speed and fading to nothing at the end of its life, the material's uniforms
// and the eight-slot ring buffer of hits (with a minimal stand-in for THREE). Known-wrong control: a ripple that
// does not fade is refused by the lifetime check.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  FORCE_FIELD_DEFAULTS, FORCE_FIELD_FRAGMENT, FORCE_FIELD_GLSL, FORCE_FIELD_MAX_HITS, FORCE_FIELD_VERTEX, addHit,
  clearHits, createForceFieldMaterial, rippleIntensity,
} from './force_field_ripple_material.mjs';

const FakeThree = {
  AdditiveBlending: 'additive', DoubleSide: 'double', FrontSide: 'front',
  Color: class { constructor(r, g, b) { Object.assign(this, {r, g, b}); } },
  ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters, {userData: {}}); } },
};

// Problems with a ripple function: the peak must sit at speed * age, values must fall to zero at the lifetime, stay
// zero before the hit and after the lifetime, and never exceed the strength.
function rippleProblems(ripple) {
  const problems = [];
  for (const age of [0.1, 0.4, 0.9]) {
    let best = -1;
    let at = 0;
    for (let step = 0; step <= 4000; step += 1) {
      const value = ripple(step / 1000, age);
      if (value > best) { best = value; at = step / 1000; }
    }
    if (Math.abs(at - 1.6 * age) > 1e-3) problems.push(`peak at ${at} for age ${age}`);
  }
  if (ripple(1.6 * 1.39, 1.39) > 1e-3) problems.push('still bright just before the end of its life');
  if (ripple(0.5, 1.41) !== 0 || ripple(0, -0.01) !== 0) problems.push('visible outside its life');
  for (let step = 0; step <= 200; step += 1) {
    if (ripple(step / 50, step / 150) > 1.4 + 1e-12) problems.push('brighter than the strength');
  }
  return problems.slice(0, 5);
}

test('rippleIntensity matches an independent port of the ring formula', () => {
  const known = [[0.4, 0.25, 0.9446428571428569], [0.52, 0.25, 0.3475146863923089], [0, 0, 1.4],
    [1, 0.5, 0.03597356032708163], [0.3, 1.5, 0], [0.3, -0.1, 0]];
  for (const [distance, age, expected] of known) {
    assert.ok(Math.abs(rippleIntensity(distance, age) - expected) < 1e-12, `${distance}, ${age}`);
  }
  assert.deepEqual(rippleProblems((distance, age) => rippleIntensity(distance, age)), []);
});

test('known wrong: a ripple that never fades is refused', () => {
  const everlasting = (distance, age) => (age < 0 ? 0 : Math.exp(-(((distance - 1.6 * age) / 0.12) ** 2)) * 1.4);
  assert.notDeepEqual(rippleProblems(everlasting), []);
});

test('createForceFieldMaterial: additive, transparent, every uniform declared', () => {
  const material = createForceFieldMaterial(FakeThree, {doubleSided: true, rippleSpeed: 2});
  assert.equal(material.blending, 'additive');
  assert.equal(material.side, 'double');
  assert.equal(material.transparent, true);
  assert.equal(material.depthWrite, false);
  assert.equal(material.uniforms.uRippleSpeed.value, 2);
  assert.equal(material.uniforms.uHitPoints.value.length, 3 * FORCE_FIELD_MAX_HITS);
  assert.ok([...material.uniforms.uHitTimes.value].every((time) => time < -1e5), 'empty slots are far in the past');
  for (const name of Object.keys(material.uniforms)) {
    assert.match(FORCE_FIELD_FRAGMENT, new RegExp(`uniform \\w+ ${name}(\\[\\d+\\])?;`), name);
  }
  assert.equal(material.vertexShader, FORCE_FIELD_VERTEX);
  assert.ok(FORCE_FIELD_FRAGMENT.includes(FORCE_FIELD_GLSL));
  assert.equal(createForceFieldMaterial(FakeThree).side, 'front');
  assert.equal(FORCE_FIELD_DEFAULTS.rippleLifetime, 1.4);
});

test('addHit fills an eight-slot ring buffer, oldest first, and clearHits empties it', () => {
  const material = createForceFieldMaterial(FakeThree);
  for (let hit = 0; hit < 9; hit += 1) assert.equal(addHit(material, [hit, hit + 0.5, -hit], 10 + hit), hit % 8);
  assert.deepEqual([...material.uniforms.uHitPoints.value.slice(0, 3)], [8, 8.5, -8], 'the ninth hit replaced the first');
  assert.equal(material.uniforms.uHitTimes.value[0], 18);
  assert.equal(material.uniforms.uHitTimes.value[1], 11);
  assert.equal(addHit(material, {x: 1, y: 2, z: 3}, 30), 1, 'a Vector3-like point works too');
  clearHits(material);
  assert.ok([...material.uniforms.uHitTimes.value].every((time) => time < -1e5));
  assert.equal(addHit(material, [0, 0, 0], 1), 0);
});

test('invalid options and inputs are refused', () => {
  assert.throws(() => createForceFieldMaterial(FakeThree, {rippleSpeeds: 2}), TypeError);
  assert.throws(() => createForceFieldMaterial(FakeThree, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => createForceFieldMaterial(FakeThree, {rippleWidth: 0}), RangeError);
  assert.throws(() => rippleIntensity(Number.NaN, 0), RangeError);
  assert.throws(() => addHit({}, [0, 0, 0], 0), TypeError);
  assert.throws(() => addHit(createForceFieldMaterial(FakeThree), [0, 0], 0), TypeError);
  assert.throws(() => clearHits(null), TypeError);
});
