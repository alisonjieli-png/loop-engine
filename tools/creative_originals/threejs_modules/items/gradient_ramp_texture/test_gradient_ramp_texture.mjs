// Known answers for the gradient ramp, computed independently with Python from the sRGB transfer functions: sRGB 0.5
// is 0.21404114048223255 in linear light; linear 0.5 encodes as sRGB 0.7353569830524495 (byte 188); a black-to-white
// ramp of 3 texels is (113, 188, 235) because it is interpolated in linear light; red to blue meets at (188, 0, 188).
// Known-wrong control: a ramp interpolated on the sRGB bytes (128 in the middle) is refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  GRADIENT_DEFAULTS, createGradientTexture, createToonGradientMap, gradientRamp, linearToSrgb, sampleGradient, srgbToLinear,
} from './gradient_ramp_texture.mjs';

const BLACK_TO_WHITE = [{position: 0, color: 0x000000}, {position: 1, color: [1, 1, 1]}];

function channel(bytes, texel, index = 0) {
  return bytes[texel * 4 + index];
}

// Problems with a ramp builder: the 3-texel black-to-white ramp and the red-to-blue middle.
function rampProblems(build) {
  const problems = [];
  const grey = build(BLACK_TO_WHITE, {width: 3});
  if ([0, 1, 2].map((texel) => channel(grey, texel)).join() !== '113,188,235') problems.push('black to white');
  const middle = build([{position: 0, color: 0xff0000}, {position: 1, color: 0x0000ff}], {width: 1});
  if (Array.from(middle.subarray(0, 3)).join() !== '188,0,188') problems.push('red to blue');
  return problems;
}

test('transfer functions match the sRGB definition', () => {
  assert.ok(Math.abs(srgbToLinear(0.5) - 0.21404114048223255) < 1e-15);
  assert.ok(Math.abs(linearToSrgb(0.5) - 0.7353569830524495) < 1e-15);
  assert.equal(srgbToLinear(0), 0);
  assert.ok(Math.abs(srgbToLinear(1) - 1) < 1e-15);
  for (const value of [0.001, 0.02, 0.3, 0.77, 0.999]) assert.ok(Math.abs(linearToSrgb(srgbToLinear(value)) - value) < 1e-12);
});

test('gradientRamp interpolates in linear light and stores sRGB bytes', () => {
  assert.deepEqual(rampProblems(gradientRamp), []);
  const linearBytes = gradientRamp(BLACK_TO_WHITE, {width: 2, encoding: 'linear'});
  assert.deepEqual([channel(linearBytes, 0), channel(linearBytes, 1)], [64, 191], 'linear encoding stores 0.25 and 0.75');
  const alpha = gradientRamp([{position: 0, color: [1, 1, 1, 0]}, {position: 1, color: [1, 1, 1, 1]}], {width: 2});
  assert.deepEqual([channel(alpha, 0, 3), channel(alpha, 1, 3)], [64, 191], 'alpha is interpolated linearly');
});

test('known wrong: a ramp interpolated on sRGB values is refused', () => {
  const naive = (stops, options) => gradientRamp(stops, {...options, input: 'linear', encoding: 'linear'});
  assert.deepEqual(rampProblems(naive), ['black to white', 'red to blue']);
});

test('stepped mode holds each stop until the next', () => {
  const stops = [{position: 0, color: 0x202020}, {position: 0.5, color: 0xffffff}];
  const bytes = gradientRamp(stops, {width: 4, mode: 'stepped'});
  assert.deepEqual([0, 1, 2, 3].map((texel) => channel(bytes, texel)), [32, 32, 255, 255]);
  assert.deepEqual(sampleGradient(stops, 0.49, {mode: 'stepped'}).slice(0, 3).map((value) => Math.round(linearToSrgb(value) * 255)),
    [32, 32, 32]);
  const smooth = sampleGradient(BLACK_TO_WHITE, 0.25);
  assert.deepEqual(smooth, [0.25, 0.25, 0.25, 1]);
});

test('textures carry the colour space and filtering of their use', () => {
  const FakeThree = {
    DataTexture: class { constructor(data, width, height) { Object.assign(this, {data, width, height}); } },
    RGBAFormat: 1023, UnsignedByteType: 1009, SRGBColorSpace: 'srgb', NoColorSpace: '', NearestFilter: 1003,
    LinearFilter: 1006, ClampToEdgeWrapping: 1001,
  };
  const colour = createGradientTexture(FakeThree, BLACK_TO_WHITE, {width: 8});
  assert.deepEqual([colour.colorSpace, colour.magFilter, colour.width, colour.height, colour.generateMipmaps],
    ['srgb', 1006, 8, 1, false]);
  const toon = createToonGradientMap(FakeThree, [0.2, 0.55, 1]);
  assert.deepEqual([toon.colorSpace, toon.magFilter, toon.minFilter, toon.width], ['', 1003, 1003, 3]);
  assert.deepEqual([0, 1, 2].map((texel) => channel(toon.data, texel)), [51, 140, 255]);
});

test('invalid stops and options are refused', () => {
  assert.throws(() => gradientRamp([]), RangeError);
  assert.throws(() => gradientRamp([{position: 0.5, color: 0}, {position: 0.2, color: 0}]), RangeError);
  assert.throws(() => gradientRamp([{position: 0, color: [2, 0, 0]}]), TypeError);
  assert.throws(() => gradientRamp(BLACK_TO_WHITE, {widht: 4}), TypeError);
  assert.throws(() => gradientRamp(BLACK_TO_WHITE, {toString: 4}), TypeError, 'an inherited name is not an option');
  assert.throws(() => gradientRamp(BLACK_TO_WHITE, {mode: 'cubic'}), RangeError);
  assert.throws(() => createToonGradientMap({}, [0.5]), RangeError);
  assert.equal(GRADIENT_DEFAULTS.width, 256);
});
