// Known answers for the ordered dither pass: the classic 2 x 2 and 4 x 4 Bayer matrices, agreement of the bit-by-bit
// threshold with the recursive matrix, that a dithered flat colour averages to itself over one tile, level and
// palette outputs at known pixels, block sampling, and the shader definition (with a minimal stand-in for THREE).
// A threshold that reads the matrix transposed is refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DITHER_DOMAINS, DITHER_MODES, ORDERED_DITHER_DEFAULTS, ORDERED_DITHER_FRAGMENT, ORDERED_DITHER_VERTEX, bayerMatrix,
  bayerThreshold, createOrderedDitherMaterial, createOrderedDitherShader, ditherPixel, ditherSamplePixel,
} from './post_ordered_dither_palette.mjs';

const PRIMARIES = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 1]];

test('bayerMatrix builds the classic matrices recursively', () => {
  assert.deepEqual(bayerMatrix(2), [[0, 2], [3, 1]]);
  assert.deepEqual(bayerMatrix(4), [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]);
  assert.deepEqual(bayerMatrix(8).slice(0, 2), [[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26]]);
  for (const n of [2, 4, 8, 16]) {
    assert.deepEqual(bayerMatrix(n).flat().sort((a, b) => a - b), Array.from({length: n * n}, (_, index) => index));
  }
  assert.throws(() => bayerMatrix(3), RangeError);
});

function thresholdProblems(threshold) {
  const problems = [];
  for (const n of [2, 4, 8, 16]) {
    const matrix = bayerMatrix(n);
    for (let y = 0; y < n; y += 1) {
      for (let x = 0; x < n; x += 1) {
        if (threshold(x, y, n) !== (matrix[y][x] + 0.5) / (n * n)) problems.push(`n ${n} (${x}, ${y})`);
      }
    }
  }
  return problems;
}

test('bayerThreshold (bit by bit, as the shader computes it) agrees with the recursive matrix', () => {
  assert.deepEqual(thresholdProblems(bayerThreshold), []);
  assert.equal(bayerThreshold(5, 6, 4), bayerThreshold(1, 2, 4), 'the matrix tiles');
});

test('known wrong: a threshold that reads the matrix transposed is refused', () => {
  assert.notDeepEqual(thresholdProblems((x, y, n) => bayerThreshold(y, x, n)), []);
});

test('a dithered flat colour averages to itself over one tile', () => {
  for (const value of [0.5, 5 / 16, 0.9375]) {
    let sum = 0;
    for (let y = 0; y < 4; y += 1) {
      for (let x = 0; x < 4; x += 1) sum += ditherPixel([value, value, value], x, y, {levels: 2, domain: 'linear'})[0];
    }
    assert.equal(sum / 16, value);
  }
});

test('levels and palette outputs at known pixels', () => {
  const linear = {domain: 'linear'};
  assert.deepEqual(ditherPixel([0.4, 0.4, 0.4], 0, 0, {...linear, levels: 4}), [1 / 3, 1 / 3, 1 / 3]);
  assert.deepEqual(ditherPixel([0.4, 0.4, 0.4], 2, 3, {...linear, levels: 4}), [2 / 3, 2 / 3, 2 / 3]);
  const palette = {...linear, mode: 'palette', palette: PRIMARIES, spread: 0.5};
  assert.deepEqual(ditherPixel([0.6, 0.3, 0.2], 0, 0, palette), [0, 0, 0]);
  assert.deepEqual(ditherPixel([0.6, 0.3, 0.2], 3, 0, palette), [1, 0, 0]);
  assert.deepEqual(ditherPixel([0.5, 0.5, 0.5], 1, 1, {...palette, palette: [[0.2, 0.2, 0.2], [0.2, 0.2, 0.2]]}),
    [0.2, 0.2, 0.2], 'ties keep the earlier colour');
  // sRGB domain: linear 0.2 encodes to 0.4845; with 2 levels the (0, 0) threshold 1/32 rounds it down to 0, the (3, 0)
  // threshold 21/32 rounds it up to 1, which decodes to 1.
  assert.deepEqual(ditherPixel([0.2, 0.2, 0.2], 0, 0, {levels: 2}), [0, 0, 0]);
  assert.deepEqual(ditherPixel([0.2, 0.2, 0.2], 3, 0, {levels: 2}), [1, 1, 1]);
});

test('blocks share one sample pixel and one threshold', () => {
  assert.deepEqual(ditherSamplePixel(5, 2, 4), [6, 2]);
  assert.deepEqual(ditherSamplePixel(5, 2, 1), [5, 2]);
  assert.deepEqual(ditherSamplePixel(0, 7, 3), [1, 7]);
  const options = {levels: 4, pixelSize: 3, domain: 'linear'};
  assert.deepEqual(ditherPixel([0.4, 0.4, 0.4], 3, 3, options), ditherPixel([0.4, 0.4, 0.4], 5, 4, options));
});

test('createOrderedDitherShader flattens the palette and maps the modes', () => {
  const shader = createOrderedDitherShader({mode: 'palette', palette: PRIMARIES, matrixSize: 8, resolution: [320, 200]});
  assert.equal(shader.uniforms.uPalette.value.length, 48);
  assert.deepEqual(Array.from(shader.uniforms.uPalette.value.slice(0, 7)), [0, 0, 0, 1, 0, 0, 0]);
  assert.equal(shader.uniforms.uPaletteSize.value, 4);
  assert.equal(shader.uniforms.uMatrixBits.value, 3);
  assert.equal(shader.uniforms.uMode.value, DITHER_MODES.palette);
  assert.equal(shader.uniforms.uDomain.value, DITHER_DOMAINS.srgb);
  assert.deepEqual(shader.uniforms.uResolution.value, [320, 200]);
  assert.equal(createOrderedDitherShader().uniforms.uLevels.value, ORDERED_DITHER_DEFAULTS.levels);
  assert.equal(shader.vertexShader, ORDERED_DITHER_VERTEX);
  assert.equal(shader.fragmentShader, ORDERED_DITHER_FRAGMENT);
  const FakeThree = {ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } }};
  assert.equal(createOrderedDitherMaterial(FakeThree, {pixelSize: 2}).uniforms.uPixelSize.value, 2);
});

test('known wrong: invalid options are refused', () => {
  assert.throws(() => createOrderedDitherShader({matrixSize: 6}), RangeError);
  assert.throws(() => createOrderedDitherShader({levels: 1}), RangeError);
  assert.throws(() => createOrderedDitherShader({palette: []}), TypeError);
  assert.throws(() => createOrderedDitherShader({palette: [[2, 0, 0]]}), TypeError);
  assert.throws(() => createOrderedDitherShader({mode: 'error-diffusion'}), TypeError);
  assert.throws(() => createOrderedDitherShader({mode: 'toString'}), TypeError, 'an inherited name is not a mode');
  assert.throws(() => bayerMatrix('toString'), RangeError, 'an inherited name is not a matrix size');
  assert.throws(() => createOrderedDitherShader({toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => ditherSamplePixel(0, 0, 0), RangeError);
});
