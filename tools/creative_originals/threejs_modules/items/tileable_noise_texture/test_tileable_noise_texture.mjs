// Known answers for the tileable noise, from an independent Python port of the same lattice construction (integer
// hash, eight gradients, quintic fade): hashes, noise values, fBm values and the first byte of a 16 x 16 texture.
// Properties: zero at lattice points, exact periodicity for representable coordinates, values within [-1, 1], the
// texture's wrap neighbour equal to its last column, determinism by seed. Known-wrong control: noise whose lattice
// does not wrap fails the periodicity check.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  NOISE_DEFAULTS, createNoiseTexture, fbmNoise, latticeHash, noiseField, noiseTextureData, periodicGradientNoise,
} from './tileable_noise_texture.mjs';

// Values printed by the Python port (math.floor, % on integers, the same operation order, IEEE doubles).
const PYTHON = {
  hashes: [[0, 0, 1, 1351741842], [3, 5, 7, 3689704491], [1, 2, 3, 1162945501]],
  noise: [[0.375, 0.625, 8, 1, 0.003495636566435772], [2.25, 7.75, 8, 42, 0.22989116531442982],
    [-1.5, 3.125, 4, 3, -0.2672032254726574]],
  fbm: [[0.375, 0.625, {}, -0.01750364845125047], [5.5, 1.25, {period: 8, octaves: 3, gain: 0.6, seed: 9}, -0.36789169154432055]],
};

function periodicityProblems(noise) {
  const problems = [];
  for (const [x, y] of [[0.375, 0.625], [3.5, 6.25], [-2.125, 1.75]]) {
    for (const period of [4, 8]) {
      const here = noise(x, y, period, 5);
      if (noise(x + period, y, period, 5) !== here || noise(x, y - period, period, 5) !== here) problems.push(`${x},${y},${period}`);
    }
  }
  return problems;
}

test('the lattice hash and noise values match the Python port', () => {
  for (const [x, y, seed, expected] of PYTHON.hashes) assert.equal(latticeHash(x, y, seed), expected);
  for (const [x, y, period, seed, expected] of PYTHON.noise) {
    assert.ok(Math.abs(periodicGradientNoise(x, y, period, seed) - expected) < 1e-15, `${x}, ${y}`);
  }
  for (const [x, y, options, expected] of PYTHON.fbm) assert.ok(Math.abs(fbmNoise(x, y, options) - expected) < 1e-15);
  assert.equal(noiseTextureData(16, 16)[0], 169);
});

test('noise is zero at lattice points, periodic, bounded and seeded', () => {
  for (let x = -3; x <= 3; x += 1) assert.equal(Math.abs(periodicGradientNoise(x, 2, 8, 1)), 0);
  assert.deepEqual(periodicityProblems(periodicGradientNoise), []);
  let largest = 0;
  for (let index = 0; index < 4000; index += 1) {
    const value = fbmNoise((index * 0.618) % 8, (index * 0.382) % 8, {octaves: 5});
    assert.ok(value >= -1 && value <= 1);
    largest = Math.max(largest, Math.abs(value));
  }
  assert.ok(largest > 0.35, `the field has contrast (${largest})`);
  assert.notEqual(fbmNoise(1.3, 2.7, {seed: 1}), fbmNoise(1.3, 2.7, {seed: 2}));
  assert.equal(fbmNoise(1.3, 2.7, {seed: 2}), fbmNoise(1.3, 2.7, {seed: 2}));
});

test('known wrong: a lattice that does not wrap is not periodic', () => {
  const unwrapped = (x, y, period, seed) => periodicGradientNoise(x, y, 4096, seed);
  assert.notDeepEqual(periodicityProblems(unwrapped), []);
});

test('the texture tiles: its wrap neighbour equals its last column', () => {
  const width = 16;
  const options = {period: 4, octaves: 3};
  const field = noiseField(width, 8, options);
  for (let row = 0; row < 8; row += 1) {
    const y = ((row + 0.5) * 4) / 8;
    assert.equal(Math.fround(fbmNoise((-0.5 * 4) / width, y, options)), field[row * width + width - 1], 'left of column 0 is column 15');
    assert.equal(Math.fround(fbmNoise(((width + 0.5) * 4) / width, y, options)), field[row * width], 'right of column 15 is column 0');
  }
  const rgba = noiseTextureData(8, 8, {channels: 'rgba'});
  assert.notEqual(rgba[0], rgba[1], 'rgba channels hold different fields');
  const grey = noiseTextureData(8, 8);
  assert.deepEqual([grey[0] === grey[1], grey[1] === grey[2], grey[3]], [true, true, 255]);
});

test('textures repeat and options are strict', () => {
  const FakeThree = {
    DataTexture: class { constructor(data, width, height) { Object.assign(this, {data, width, height}); } },
    RGBAFormat: 1023, UnsignedByteType: 1009, NoColorSpace: '', RepeatWrapping: 1000, LinearFilter: 1006,
    LinearMipmapLinearFilter: 1008,
  };
  const texture = createNoiseTexture(FakeThree, 8, 8, {seed: 3});
  assert.deepEqual([texture.wrapS, texture.wrapT, texture.colorSpace, texture.generateMipmaps], [1000, 1000, '', true]);
  assert.throws(() => fbmNoise(0, 0, {octave: 2}), TypeError);
  assert.throws(() => fbmNoise(0, 0, {toString: 2}), TypeError, 'an inherited name is not an option');
  assert.throws(() => fbmNoise(0, 0, {gain: 0}), RangeError);
  assert.throws(() => periodicGradientNoise(0, 0, 0), RangeError);
  assert.throws(() => noiseField(0, 4), RangeError);
  assert.equal(NOISE_DEFAULTS.period, 8);
});
