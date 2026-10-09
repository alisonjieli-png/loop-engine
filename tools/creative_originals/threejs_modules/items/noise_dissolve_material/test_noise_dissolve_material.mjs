// Known answers for the noise dissolve material: lattice values, value noise, fractal noise and the burn edge against
// values computed independently from the same integer hash, plus the material the builder makes (with a minimal
// stand-in for THREE). Each guard also runs on a known-wrong input that it must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  NOISE_DISSOLVE_DEFAULTS, NOISE_DISSOLVE_FRAGMENT, NOISE_DISSOLVE_GLSL, NOISE_DISSOLVE_VERTEX,
  createNoiseDissolveMaterial, dissolveEdge, fbm3, isDissolved, valueNoise3,
} from './noise_dissolve_material.mjs';

const FakeThree = {
  DoubleSide: 2,
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

// Computed independently (a Python transcription of the hash, lattice, quintic interpolation and fractal sum).
const NOISE_CASES = [
  [[0, 0, 0, 0], 0.3226417303085327],
  [[-3, 5, 2, 7], 0.5661833882331848],
  [[0.5, 0.25, -1.75, 7], 0.24617859718591717],
  [[10.3, -4.6, 0.01, 123], 0.8199033265488532],
];
const FBM_CASES = [
  [[0.3, -1.2, 2.5, 4, 7], 0.5903951430473363],
  [[0, 0, 0, 1, 0], 0.3226417303085327],
  [[1.5, 2.5, -0.5, 3, 2], 0.4553614301340921],
];

function noiseProblems(noise, fractal) {
  const problems = [];
  for (const [args, expected] of NOISE_CASES) {
    const actual = noise(...args);
    if (Math.abs(actual - expected) > 1e-12) problems.push(`valueNoise3(${args}) = ${actual}, expected ${expected}`);
  }
  for (const [args, expected] of FBM_CASES) {
    const actual = fractal(...args);
    if (Math.abs(actual - expected) > 1e-12) problems.push(`fbm3(${args}) = ${actual}, expected ${expected}`);
  }
  return problems;
}

test('value noise and fractal noise match the independent transcription', () => {
  assert.deepEqual(noiseProblems(valueNoise3, fbm3), []);
});

test('known wrong: linear instead of quintic interpolation between the same lattice values is refused', () => {
  const linear = (x, y, z, seed) => {
    const [bx, by, bz] = [Math.floor(x), Math.floor(y), Math.floor(z)];
    const corner = (i, j, k) => valueNoise3(bx + i, by + j, bz + k, seed);
    const lerp = (a, b, t) => a + (b - a) * t;
    const [fx, fy, fz] = [x - bx, y - by, z - bz];
    return lerp(lerp(lerp(corner(0, 0, 0), corner(1, 0, 0), fx), lerp(corner(0, 1, 0), corner(1, 1, 0), fx), fy),
      lerp(lerp(corner(0, 0, 1), corner(1, 0, 1), fx), lerp(corner(0, 1, 1), corner(1, 1, 1), fx), fy), fz);
  };
  assert.notDeepEqual(noiseProblems(linear, fbm3), []);
});

test('the noise is continuous across lattice cells and stays in [0, 1)', () => {
  for (const offset of [-2, 0, 3]) {
    const left = valueNoise3(offset - 1e-9, 0.3, 0.7, 5);
    const right = valueNoise3(offset + 1e-9, 0.3, 0.7, 5);
    assert.ok(Math.abs(left - right) < 1e-7, `continuous at x = ${offset}`);
  }
  for (let step = 0; step < 200; step += 1) {
    const value = fbm3(step * 0.173 - 17, step * 0.071, -step * 0.113, 5, 3);
    assert.ok(value >= 0 && value < 1);
  }
});

test('dissolveEdge glows at the front and nowhere while the threshold is 0', () => {
  assert.ok(Math.abs(dissolveEdge(0.48, 0.45, 0.06) - 0.5000000000000007) < 1e-12);
  assert.equal(dissolveEdge(0.45, 0.45, 0.06), 1);
  assert.equal(dissolveEdge(0.6, 0.45, 0.06), 0);
  assert.equal(dissolveEdge(0.02, 0, 0.06), 0);
  assert.equal(dissolveEdge(0.03, 0.03, 0.06), 0.5);
  assert.equal(isDissolved(0.3, 0.45), true);
  assert.equal(isDissolved(0.45, 0.45), false);
});

test('invalid inputs are refused', () => {
  assert.throws(() => valueNoise3(0, 0, 0, -1), RangeError);
  assert.throws(() => valueNoise3(2e6, 0, 0, 0), RangeError);
  assert.throws(() => fbm3(0, 0, 0, 9, 0), RangeError);
  assert.throws(() => dissolveEdge(1.5, 0.4, 0.1), RangeError);
  assert.throws(() => isDissolved(Number.NaN, 0.4), TypeError);
  assert.throws(() => createNoiseDissolveMaterial(FakeThree, {treshold: 0.4}), TypeError);
  assert.throws(() => createNoiseDissolveMaterial(FakeThree, {octaves: 2.5}), RangeError);
  assert.throws(() => createNoiseDissolveMaterial(FakeThree, {seed: 3.5}), RangeError);
});

test('createNoiseDissolveMaterial wires every uniform and draws both sides', () => {
  const material = createNoiseDissolveMaterial(FakeThree, {threshold: 0.6, octaves: 3, seed: 42});
  assert.deepEqual(Object.keys(material.uniforms).sort(), ['uAmbient', 'uColor', 'uEdgeColor', 'uEdgeIntensity',
    'uEdgeWidth', 'uLightDirection', 'uNoiseScale', 'uOctaves', 'uSeed', 'uThreshold']);
  assert.equal(material.uniforms.uThreshold.value, 0.6);
  assert.equal(material.uniforms.uOctaves.value, 3);
  assert.equal(material.uniforms.uSeed.value, 42);
  assert.equal(material.uniforms.uEdgeWidth.value, NOISE_DISSOLVE_DEFAULTS.edgeWidth);
  assert.equal(material.side, FakeThree.DoubleSide);
  assert.equal(material.vertexShader, NOISE_DISSOLVE_VERTEX);
  assert.equal(material.fragmentShader, NOISE_DISSOLVE_FRAGMENT);
  assert.ok(NOISE_DISSOLVE_FRAGMENT.includes(NOISE_DISSOLVE_GLSL));
  assert.match(NOISE_DISSOLVE_GLSL, /0x7feb352du/, 'the GLSL uses the same hash constants as the mirror');
  for (const name of Object.keys(material.uniforms)) {
    assert.match(NOISE_DISSOLVE_FRAGMENT, new RegExp(`uniform \\w+ ${name};`));
  }
});
