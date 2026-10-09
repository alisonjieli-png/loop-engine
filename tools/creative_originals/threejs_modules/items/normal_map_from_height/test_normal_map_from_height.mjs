// Known answers for the normal map generator, computed independently with Python from n = normalize(-s dh/du,
// -s dh/dv, 1) and byte = round((c / 2 + 0.5) * 255): a flat field is (128, 128, 255); a ramp along the columns gives
// (37, 128, 218); along the rows (128, 37, 218), or green 218 in the DirectX convention; strength 2 gives (13, 128, 185);
// the first column of a ramp gives (70, 128, 242) with clamped edges and (248, 128, 168) with wrapped ones. Known-wrong
// controls: a generator with rows and columns swapped, and one with the wrong green sign, are refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  NORMAL_MAP_DEFAULTS, createNormalMapTexture, encodeNormal, normalMapFromHeight, normalsFromHeight,
} from './normal_map_from_height.mjs';

function ramp(width, height, alongRows = false) {
  const heights = new Float32Array(width * height);
  for (let y = 0; y < height; y += 1) for (let x = 0; x < width; x += 1) heights[y * width + x] = alongRows ? y : x;
  return heights;
}

function texel(bytes, width, x, y) {
  return Array.from(bytes.subarray((y * width + x) * 4, (y * width + x) * 4 + 4));
}

// Problems with a generator: the ramps must tilt toward -u and -v in the OpenGL convention.
function generatorProblems(generate) {
  const problems = [];
  if (texel(generate(ramp(8, 4), 8, 4, {edges: 'clamp'}), 8, 3, 2).join() !== '37,128,218,255') problems.push('column ramp');
  if (texel(generate(ramp(8, 4, true), 8, 4, {edges: 'clamp'}), 8, 3, 2).join() !== '128,37,218,255') problems.push('row ramp');
  return problems;
}

test('a flat field encodes as (128, 128, 255) everywhere', () => {
  const bytes = normalMapFromHeight(new Float32Array(16).fill(3.5), 4, 4);
  for (let index = 0; index < 16; index += 1) assert.deepEqual(texel(bytes, 4, index % 4, Math.floor(index / 4)), [128, 128, 255, 255]);
});

test('ramps tilt the expected way in both conventions', () => {
  assert.deepEqual(generatorProblems(normalMapFromHeight), []);
  const directx = normalMapFromHeight(ramp(8, 4, true), 8, 4, {edges: 'clamp', convention: 'directx'});
  assert.deepEqual(texel(directx, 8, 3, 2), [128, 218, 218, 255]);
  const steep = normalMapFromHeight(ramp(8, 4), 8, 4, {strength: 2, edges: 'clamp'});
  assert.deepEqual(texel(steep, 8, 3, 1), [13, 128, 185, 255]);
});

test('edges: clamped and wrapped first columns', () => {
  assert.deepEqual(texel(normalMapFromHeight(ramp(8, 4), 8, 4, {edges: 'clamp'}), 8, 0, 1), [70, 128, 242, 255]);
  assert.deepEqual(texel(normalMapFromHeight(ramp(8, 4), 8, 4, {edges: 'wrap'}), 8, 0, 1), [248, 128, 168, 255]);
});

test('normalsFromHeight returns unit normals', () => {
  const heights = new Float32Array(64).map((_, index) => Math.sin(index * 0.7) * 2);
  const normals = normalsFromHeight(heights, 8, 8, {strength: 1.5});
  for (let texelIndex = 0; texelIndex < 64; texelIndex += 1) {
    const length = Math.hypot(normals[texelIndex * 3], normals[texelIndex * 3 + 1], normals[texelIndex * 3 + 2]);
    assert.ok(Math.abs(length - 1) < 1e-6);
    assert.ok(normals[texelIndex * 3 + 2] > 0, 'normals face out of the surface');
  }
  assert.deepEqual(encodeNormal(0, 0, 1), [128, 128, 255, 255]);
  assert.deepEqual(encodeNormal(0, 1, 0, 'directx'), [128, 0, 128, 255]);
});

test('known wrong: swapped axes and a flipped green sign are refused', () => {
  const transposed = (heights, width, height, options) => {
    const swapped = new Float32Array(width * height);
    for (let y = 0; y < height; y += 1) for (let x = 0; x < width; x += 1) swapped[y * width + x] = heights[x * height + y] ?? 0;
    return normalMapFromHeight(swapped, width, height, options);
  };
  assert.notDeepEqual(generatorProblems(transposed), []);
  const flipped = (heights, width, height, options) => normalMapFromHeight(heights, width, height, {...options, convention: 'directx'});
  assert.deepEqual(generatorProblems(flipped), ['row ramp']);
});

test('invalid input is refused and the texture is linear data', () => {
  assert.throws(() => normalMapFromHeight(new Float32Array(5), 2, 2), RangeError);
  assert.throws(() => normalMapFromHeight([0, 0, 0, 0], 2, 2), TypeError);
  assert.throws(() => normalMapFromHeight(new Float32Array(4), 2, 2, {edge: 'wrap'}), TypeError);
  assert.throws(() => normalMapFromHeight(new Float32Array(4), 2, 2, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => normalMapFromHeight(new Float32Array(4), 2, 2, {convention: 'vulkan'}), RangeError);
  const FakeThree = {
    DataTexture: class { constructor(data, width, height, format, type) { Object.assign(this, {data, width, height, format, type}); } },
    RGBAFormat: 1023, UnsignedByteType: 1009, NoColorSpace: '', RepeatWrapping: 1000, ClampToEdgeWrapping: 1001,
    LinearFilter: 1006, LinearMipmapLinearFilter: 1008,
  };
  const texture = createNormalMapTexture(FakeThree, new Uint8Array(16), 2, 2, {edges: 'clamp'});
  assert.deepEqual([texture.colorSpace, texture.wrapS, texture.wrapT, texture.needsUpdate], ['', 1001, 1001, true]);
  assert.throws(() => createNormalMapTexture(FakeThree, new Uint8Array(15), 2, 2), RangeError);
  assert.equal(NORMAL_MAP_DEFAULTS.convention, 'opengl');
});
