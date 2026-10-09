// Known answers for the LUT strip grading pass: the strip layout of a 2-point identity, trilinear samples of
// identity, inverted, squared and warm strips, the sRGB-domain round trip, the texture wrapper and the shader
// definition (with a minimal stand-in for THREE). A sampler that picks the nearest blue slice is refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  COLOR_LUT_DEFAULTS, COLOR_LUT_DOMAINS, COLOR_LUT_FRAGMENT, COLOR_LUT_VERTEX, createColorLutMaterial,
  createColorLutShader, createLutStripTexture, gradeColorCpu, identityLutStrip, lutStripFromFunction,
  sampleLutStripCpu,
} from './post_color_lut_strip.mjs';

const WARM = (r, g, b) => [Math.min(1, r * 1.1 + 0.03), g, b * 0.85];

// Expected values computed independently (python3, the same grid and trilinear weights).
function samplerProblems(sample) {
  const problems = [];
  const cases = [
    [identityLutStrip(16), 16, [0.3, 0.6, 0.9], [0.3, 0.6, 0.9]],
    [lutStripFromFunction(2, (r, g, b) => [1 - r, g, b]), 2, [0.25, 0.5, 0.5], [0.75, 0.5, 0.5]],
    [lutStripFromFunction(3, (r, g, b) => [r * r, g, b]), 3, [0.25, 0, 0], [0.12549019607843137, 0, 0]],
    [lutStripFromFunction(4, WARM), 4, [0.4, 0.7, 0.2], [0.4698039215686275, 0.7, 0.16941176470588237]],
  ];
  for (const [data, size, input, expected] of cases) {
    const actual = sample(data, size, ...input);
    if (actual.some((value, channel) => Math.abs(value - expected[channel]) > 1e-12)) {
      problems.push(`size ${size} at ${input} gave ${actual}, expected ${expected}`);
    }
  }
  return problems;
}

test('the strip layout puts blue slices side by side, red along x and green along y', () => {
  assert.deepEqual(Array.from(identityLutStrip(2)), [
    0, 0, 0, 255, 255, 0, 0, 255, 0, 0, 255, 255, 255, 0, 255, 255,
    0, 255, 0, 255, 255, 255, 0, 255, 0, 255, 255, 255, 255, 255, 255, 255,
  ]);
  assert.equal(identityLutStrip(16).length, 16 * 16 * 16 * 4);
});

test('sampleLutStripCpu is trilinear over the 8-bit strip', () => {
  assert.deepEqual(samplerProblems(sampleLutStripCpu), []);
  assert.deepEqual(sampleLutStripCpu(identityLutStrip(8), 8, -1, 2, 0.5).map((value) => Math.round(value * 1e9) / 1e9),
    [0, 1, 0.5], 'inputs outside [0, 1] are clamped');
});

test('known wrong: a sampler that takes the nearest blue slice is refused', () => {
  const nearestSlice = (data, size, r, g, b) => {
    const slice = Math.round(b * (size - 1)) / (size - 1);
    return sampleLutStripCpu(data, size, r, g, slice);
  };
  assert.notDeepEqual(samplerProblems(nearestSlice), []);
});

test('gradeColorCpu round-trips the sRGB domain and mixes by intensity', () => {
  const identity = identityLutStrip(16);
  const graded = gradeColorCpu(identity, 16, [0.2, 0.5, 0.8], {domain: 'srgb'});
  graded.forEach((value, channel) => assert.ok(Math.abs(value - [0.2, 0.5, 0.8][channel]) < 1e-9));
  const inverted = lutStripFromFunction(2, (r, g, b) => [1 - r, 1 - g, 1 - b]);
  const half = gradeColorCpu(inverted, 2, [0.25, 0.5, 1], {domain: 'linear', intensity: 0.5});
  assert.deepEqual(half.map((value) => Math.round(value * 1e9) / 1e9), [0.5, 0.5, 0.5]);
  assert.throws(() => gradeColorCpu(identity, 16, [0, 0, 0], {domain: 'log'}), TypeError);
});

test('createLutStripTexture and the shader definition', () => {
  const FakeThree = {
    RGBAFormat: 1023, UnsignedByteType: 1009, LinearFilter: 1006, ClampToEdgeWrapping: 1001,
    DataTexture: class { constructor(data, width, height, format, type) { Object.assign(this, {data, width, height, format, type}); } },
    ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } },
  };
  const texture = createLutStripTexture(FakeThree, identityLutStrip(4), 4);
  assert.deepEqual([texture.width, texture.height, texture.minFilter, texture.generateMipmaps, texture.needsUpdate],
    [16, 4, 1006, false, true]);
  assert.throws(() => createLutStripTexture(FakeThree, identityLutStrip(4), 8), TypeError);
  const shader = createColorLutShader({size: 32, domain: 'linear'});
  assert.deepEqual(Object.keys(shader.uniforms).sort(), ['tDiffuse', 'tLut', 'uDomain', 'uIntensity', 'uLutSize']);
  assert.equal(shader.uniforms.uDomain.value, COLOR_LUT_DOMAINS.linear);
  assert.equal(shader.uniforms.uLutSize.value, 32);
  assert.equal(createColorLutShader().uniforms.uLutSize.value, COLOR_LUT_DEFAULTS.size);
  assert.equal(shader.vertexShader, COLOR_LUT_VERTEX);
  assert.equal(shader.fragmentShader, COLOR_LUT_FRAGMENT);
  const material = createColorLutMaterial(FakeThree, {intensity: 0.3});
  assert.equal(material.uniforms.uIntensity.value, 0.3);
  assert.equal(material.depthWrite, false);
});

test('known wrong: invalid sizes, strips and options are refused', () => {
  assert.throws(() => identityLutStrip(1), RangeError);
  assert.throws(() => identityLutStrip(65), RangeError);
  assert.throws(() => lutStripFromFunction(4, () => [0, 0]), TypeError);
  assert.throws(() => sampleLutStripCpu(new Uint8Array(10), 4, 0, 0, 0), TypeError);
  assert.throws(() => createColorLutShader({intensity: 2}), RangeError);
  assert.throws(() => createColorLutShader({lut: null}), TypeError);
  assert.throws(() => createColorLutShader({toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => createColorLutShader({domain: 'toString'}), TypeError, 'an inherited name is not a domain');
});
