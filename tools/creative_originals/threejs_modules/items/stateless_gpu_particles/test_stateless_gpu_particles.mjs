// Known answers for the stateless particles: birth offsets, and states from an independent Python port of the same
// integer hash and motion; then properties: every launch direction lies in the cone and every speed in its range,
// opacity fades in and out, a particle draws fresh randoms on each loop, and births spread over the lifetime.
// Known-wrong control: launches spread over the whole sphere are refused by the cone check.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  GPU_PARTICLES_DEFAULTS, PARTICLE_FRAGMENT, PARTICLE_GLSL, PARTICLE_UNIFORMS_GLSL, PARTICLE_VERTEX, createParticleGeometry,
  createParticleMaterial, createParticlePoints, particleBirth, particleState,
} from './stateless_gpu_particles.mjs';

const FakeThree = {
  AdditiveBlending: 'additive',
  BufferAttribute: class { constructor(array, itemSize) { Object.assign(this, {array, itemSize}); } },
  BufferGeometry: class {
    constructor() { this.attributes = {}; }
    setAttribute(name, attribute) { this.attributes[name] = attribute; }
  },
  Color: class { constructor(r, g, b) { Object.assign(this, {r, g, b}); } },
  Points: class { constructor(geometry, material) { Object.assign(this, {geometry, material}); } },
  ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } },
  Sphere: class { constructor(center, radius) { Object.assign(this, {center, radius}); } },
  Vector3: class { constructor(x, y, z) { Object.assign(this, {x, y, z}); } },
};

function close(actual, expected, tolerance, label) {
  actual.forEach((value, index) => assert.ok(Math.abs(value - expected[index]) <= tolerance, `${label}: [${actual}]`));
}

// Problems with a state function launched without gravity, swirl or spawn disc: the displacement over the age must
// point within the cone around +Y and have a speed within [speedMin, speedMax].
function coneProblems(state) {
  const options = {gravity: [0, 0, 0], swirl: 0, emitterRadius: 0, coneAngle: 0.35, speedMin: 1.8, speedMax: 3.2};
  const problems = [];
  for (let index = 0; index < 3000; index += 1) {
    const {position, life} = state(index, 7.3, options);
    const age = life * GPU_PARTICLES_DEFAULTS.lifetime;
    if (age < 1e-3) continue;
    const length = Math.hypot(...position);
    if (Math.acos(Math.min(1, position[1] / length)) > 0.35 + 1e-9) problems.push(`particle ${index} leaves the cone`);
    const speed = length / age;
    if (speed < 1.8 - 1e-9 || speed > 3.2 + 1e-9) problems.push(`particle ${index} speed ${speed}`);
  }
  return problems.slice(0, 5);
}

test('births and states match an independent Python port', () => {
  assert.deepEqual([0, 1, 2, 5].map((index) => particleBirth(index)), [0, 1.5450849533081055, 0.5901699662208557, 0.2254248559474945]);
  const known = [
    [0, 1.0, [-0.8669949992680486, 1.2927800923030561, 0.24379187461596064], 0.4, 0],
    [5, 3.25, [0.33590461024667034, 1.1110868003386942, -0.18414613223375204], 0.2098300576210022, 1],
    [17, 0.4, [1.2702977580481434, 1.8202808268641788, -0.2761001300923318], 0.6534221744537353, -1],
    [1000, 12.0, [-1.0822097276877458, -0.15502722561446092, -0.4182369211767549], 0.7660112500190734, 4],
  ];
  for (const [index, time, position, life, cycle] of known) {
    const state = particleState(index, time);
    close(state.position, position, 1e-12, `particle ${index}`);
    assert.ok(Math.abs(state.life - life) < 1e-12);
    assert.equal(state.cycle, cycle);
  }
  const late = particleState(1000, 12.0);
  assert.ok(Math.abs(late.alpha - 0.7432340462295789) < 1e-12 && Math.abs(late.size - 0.07275842499732972) < 1e-12);
});

test('launch directions stay in the cone and speeds in range', () => {
  assert.deepEqual(coneProblems(particleState), []);
});

test('known wrong: launches over the whole sphere are refused', () => {
  const everywhere = (index, time, options) => {
    const state = particleState(index, time, {...options, coneAngle: Math.PI});
    return state;
  };
  assert.notDeepEqual(coneProblems(everywhere), []);
});

test('loops draw fresh randoms; opacity fades in and out; births spread evenly', () => {
  const first = particleState(3, 2.0);
  const next = particleState(3, 2.0 + GPU_PARTICLES_DEFAULTS.lifetime);
  assert.ok(Math.abs(first.life - next.life) < 1e-12 && next.cycle === first.cycle + 1);
  assert.ok(Math.hypot(first.position[0] - next.position[0], first.position[2] - next.position[2]) > 1e-6, 'a new path');
  const birth = particleBirth(9);
  assert.equal(particleState(9, birth).alpha, 0, 'invisible at birth');
  assert.equal(particleState(9, birth + 1.25).alpha, 1, 'fully visible mid-life');
  assert.ok(particleState(9, birth + 2.5 - 1e-9).alpha < 1e-6, 'gone at the end of its life');
  const counts = new Array(10).fill(0);
  for (let index = 0; index < 1000; index += 1) counts[Math.floor(particleBirth(index, 1) * 10)] += 1;
  assert.ok(counts.every((count) => count >= 90 && count <= 110), `births spread: ${counts}`);
});

test('geometry, material and points', () => {
  const geometry = createParticleGeometry(FakeThree, {count: 64});
  assert.equal(geometry.attributes.position.array.length, 192);
  assert.deepEqual([...geometry.attributes.aSeed.array.slice(0, 3)], [0, 1, 2]);
  assert.equal(geometry.attributes.aBirth.array[5], particleBirth(5));
  assert.ok(Math.abs(geometry.boundingSphere.radius - (0.15 + 3.2 * 2.5 + 0.5 * 2.4 * 6.25)) < 1e-12);
  const material = createParticleMaterial(FakeThree, {swirl: 0});
  assert.equal(material.blending, 'additive');
  assert.equal(material.depthWrite, false);
  assert.equal(material.uniforms.uSwirl.value, 0);
  const declared = `${PARTICLE_UNIFORMS_GLSL}${PARTICLE_VERTEX}${PARTICLE_FRAGMENT}`;
  for (const name of Object.keys(material.uniforms)) assert.match(declared, new RegExp(`uniform \\w+ ${name};`), name);
  assert.ok(PARTICLE_VERTEX.includes(PARTICLE_GLSL));
  const points = createParticlePoints(FakeThree, {count: 10});
  assert.equal(points.geometry.attributes.aSeed.array.length, 10);
  assert.equal(points.name, 'BaltorStatelessParticles');
});

test('invalid options are refused', () => {
  assert.throws(() => particleState(0, 0, {speed: 1}), TypeError);
  assert.throws(() => particleState(0, 0, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => particleState(0, 0, {speedMin: 5, speedMax: 1}), RangeError);
  assert.throws(() => particleState(0, 0, {fadeIn: 0}), RangeError);
  assert.throws(() => particleBirth(-1), RangeError);
  assert.throws(() => createParticleGeometry(FakeThree, {count: 0}), RangeError);
});
