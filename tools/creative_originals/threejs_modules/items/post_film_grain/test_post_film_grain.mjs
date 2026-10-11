// Known answers for the film grain pass: integer hash values computed independently with 32-bit arithmetic in
// python3, triangular noise values, the noise statistics (mean 0, variance 1/6), cells and channels, the luminance
// response, the whole-pass mirror and the shader definition (with a minimal stand-in for THREE). A hash with a wrong
// multiplier is refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  FILM_GRAIN_DEFAULTS, FILM_GRAIN_FRAGMENT, FILM_GRAIN_HASH_GLSL, FILM_GRAIN_VERTEX, applyGrainCpu,
  createFilmGrainMaterial, createFilmGrainShader, grainHash, grainValue, grainWeight,
} from './post_film_grain.mjs';

const KNOWN_HASHES = [
  [[0, 0, 0, 0, 0], 0],
  [[1, 2, 3, 4, 0], 1204710985],
  [[1, 2, 3, 4, 1], 841825412],
  [[100, 200, 7, 3, 2], 3906534070],
];

function hashProblems(hash) {
  return KNOWN_HASHES.filter(([input, expected]) => hash(...input) !== expected)
    .map(([input, expected]) => `${input} gave ${hash(...input)}, expected ${expected}`);
}

test('grainHash reproduces the 32-bit integer hash', () => {
  assert.deepEqual(hashProblems(grainHash), []);
  assert.throws(() => grainHash(-1, 0, 0, 0, 0), RangeError);
  assert.throws(() => grainHash(0.5, 0, 0, 0, 0), RangeError);
});

test('known wrong: a hash with a different multiplier is refused', () => {
  const wrong = (x, y, frame, seed, channel) => (grainHash(x, y, frame, seed, channel) * 3) >>> 0;
  assert.notDeepEqual(hashProblems(wrong), []);
});

test('grainValue gives triangular noise per cell and channel', () => {
  const at = (x, y, options) => grainValue(x, y, options);
  assert.ok(Math.abs(at(0, 0)[0] - -0.16457349061965942) < 1e-15);
  assert.ok(Math.abs(at(1, 2, {frame: 3, seed: 4})[0] - 0.2070329189300537) < 1e-15);
  assert.ok(Math.abs(at(17, 5, {frame: 9, seed: 1, colored: true})[1] - -0.3373050093650818) < 1e-15);
  const mono = at(10, 20, {frame: 2});
  assert.ok(mono[0] === mono[1] && mono[1] === mono[2], 'mono grain is the same on every channel');
  const colour = at(10, 20, {frame: 2, colored: true});
  assert.ok(colour[0] === mono[0] && colour[1] !== colour[0] && colour[2] !== colour[1]);
  assert.deepEqual(at(5, 6, {grainSize: 4}), at(7, 7, {grainSize: 4}), 'pixels of one cell share the grain');
  assert.notDeepEqual(at(5, 6, {frame: 1}), at(5, 6, {frame: 2}), 'the grain changes with the frame');
  let sum = 0;
  let squares = 0;
  const count = 200 * 100;
  for (let y = 0; y < 100; y += 1) {
    for (let x = 0; x < 200; x += 1) {
      const value = at(x, y, {seed: 11})[0];
      assert.ok(value > -1 && value < 1);
      sum += value;
      squares += value * value;
    }
  }
  assert.ok(Math.abs(sum / count) < 0.01, `mean ${sum / count}`);
  assert.ok(Math.abs(squares / count - 1 / 6) < 0.01, `variance ${squares / count}`);
});

test('grainWeight peaks in the mid-tones and applyGrainCpu adds weighted grain', () => {
  assert.ok(Math.abs(grainWeight([0.5, 0.5, 0.5]) - 0.08) < 1e-15);
  assert.ok(Math.abs(grainWeight([0, 0, 0]) - 0.02) < 1e-15);
  assert.ok(Math.abs(grainWeight([3, 3, 3], {response: 1})) < 1e-15, 'clamped white gets no grain at full response');
  assert.equal(grainWeight([0, 0, 0], {response: 0, intensity: 0.2}), 0.2);
  const rgb = [0.5, 0.5, 0.5];
  const out = applyGrainCpu(rgb, 3, 4, {frame: 5});
  const grain = grainValue(3, 4, {frame: 5});
  out.forEach((value, channel) => assert.ok(Math.abs(value - (0.5 + grain[channel] * 0.08)) < 1e-15));
});

test('the shader definition carries the hash chunk and the frame', () => {
  const shader = createFilmGrainShader({colored: true, frame: 12, grainSize: 2});
  assert.deepEqual(Object.keys(shader.uniforms).sort(),
    ['tDiffuse', 'uColored', 'uFrame', 'uGrainSize', 'uIntensity', 'uResponse', 'uSeed']);
  assert.equal(shader.uniforms.uColored.value, 1);
  assert.equal(shader.uniforms.uFrame.value, 12);
  assert.equal(createFilmGrainShader().uniforms.uIntensity.value, FILM_GRAIN_DEFAULTS.intensity);
  assert.ok(FILM_GRAIN_FRAGMENT.includes(FILM_GRAIN_HASH_GLSL));
  assert.match(FILM_GRAIN_HASH_GLSL, /0x68e31da4u/);
  assert.equal(shader.vertexShader, FILM_GRAIN_VERTEX);
  const FakeThree = {ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } }};
  assert.equal(createFilmGrainMaterial(FakeThree, {seed: 9}).uniforms.uSeed.value, 9);
});

test('known wrong: invalid options are refused', () => {
  assert.throws(() => createFilmGrainShader({intensity: 2}), RangeError);
  assert.throws(() => createFilmGrainShader({grainSize: 0}), RangeError);
  assert.throws(() => createFilmGrainShader({colored: 1}), TypeError);
  assert.throws(() => createFilmGrainShader({frame: -1}), RangeError);
  assert.throws(() => createFilmGrainShader({amount: 0.1}), TypeError);
  assert.throws(() => createFilmGrainShader({toString: 1}), TypeError, 'an inherited name is not an option');
});
