// Known answers for the heightfield: flat normals, the exact normal of a sloped plane at every vertex (borders
// included), cell size and height scale, skirt and LOD counts, a closed block whose volume is the prism volume under
// the plane, bilinear and surface height queries on small fields, and the three.js geometry. Known-wrong controls: a
// normal that ignores the cell size, a flipped triangle and a missing triangle are refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  HEIGHTFIELD_DEFAULTS, createHeightfieldTerrainGeometry, heightfieldTerrainData, sampleHeight, sampleSurfaceHeight,
} from './heightfield_terrain_geometry.mjs';

function plane(width, depth, a, b, cellSize = 1) {
  const heights = new Float32Array(width * depth);
  for (let j = 0; j < depth; j += 1) for (let i = 0; i < width; i += 1) heights[j * width + i] = a * i * cellSize + b * j * cellSize;
  return heights;
}

function vertex(array, index) {
  return [array[index * 3], array[index * 3 + 1], array[index * 3 + 2]];
}

// Every top vertex normal equals the plane normal normalize(-a, 1, -b).
function planeNormalProblems(mesh, a, b) {
  const length = Math.hypot(a, 1, b);
  const expected = [-a / length, 1 / length, -b / length];
  const problems = [];
  for (let v = 0; v < mesh.columns * mesh.rows; v += 1) {
    const normal = vertex(mesh.normals, v);
    if (normal.some((value, axis) => Math.abs(value - expected[axis]) > 1e-6)) problems.push(`normal ${v}: ${normal}`);
  }
  return problems.slice(0, 3);
}

function solidProblems(mesh) {
  const problems = [];
  const keys = new Map();
  const weld = [];
  for (let v = 0; v < mesh.positions.length / 3; v += 1) {
    const key = vertex(mesh.positions, v).map((value) => `${Math.round(value * 1e5)}`).join(',');
    if (!keys.has(key)) keys.set(key, keys.size);
    weld.push(keys.get(key));
  }
  const edges = new Map();
  for (let t = 0; t < mesh.indices.length; t += 3) {
    const corner = [0, 1, 2].map((k) => weld[mesh.indices[t + k]]);
    if (new Set(corner).size < 3) continue;
    for (let k = 0; k < 3; k += 1) {
      const key = `${corner[k]}>${corner[(k + 1) % 3]}`;
      edges.set(key, (edges.get(key) || 0) + 1);
    }
    const [p, q, r] = [0, 1, 2].map((k) => vertex(mesh.positions, mesh.indices[t + k]));
    const u = q.map((value, i) => value - p[i]);
    const w = r.map((value, i) => value - p[i]);
    const face = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]];
    const normal = vertex(mesh.normals, mesh.indices[t]);
    if (face[0] * normal[0] + face[1] * normal[1] + face[2] * normal[2] <= 0) problems.push(`triangle ${t / 3} faces inward`);
  }
  for (const [key, count] of edges) {
    const [from, to] = key.split('>');
    if (count !== 1 || edges.get(`${to}>${from}`) !== 1) problems.push(`edge ${key} is not shared once each way`);
  }
  return problems.slice(0, 5);
}

function signedVolume(mesh) {
  let volume = 0;
  for (let t = 0; t < mesh.indices.length; t += 3) {
    const [a, b, c] = [0, 1, 2].map((k) => vertex(mesh.positions, mesh.indices[t + k]));
    volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6;
  }
  return volume;
}

test('a flat field has upward normals and the grid layout', () => {
  const mesh = heightfieldTerrainData(new Float32Array(12), 4, 3, {cellSize: 2});
  assert.equal(mesh.positions.length / 3, 12);
  assert.equal(mesh.indices.length, 6 * 3 * 2);
  for (let v = 0; v < 12; v += 1) assert.deepEqual(vertex(mesh.normals, v), [0, 1, 0]);
  assert.deepEqual(vertex(mesh.positions, 0), [-3, 0, -2]);
  assert.deepEqual(vertex(mesh.positions, 11), [3, 0, 2]);
  assert.deepEqual([mesh.uvs[0], mesh.uvs[1], mesh.uvs[22], mesh.uvs[23]], [0, 1, 1, 0]);
});

test('a sloped plane gets its exact normal at every vertex, borders included', () => {
  assert.deepEqual(planeNormalProblems(heightfieldTerrainData(plane(6, 5, 0.5, 0.25), 6, 5), 0.5, 0.25), []);
  const scaled = heightfieldTerrainData(plane(6, 5, 0.5, 0.25), 6, 5, {cellSize: 2, heightScale: 3});
  assert.deepEqual(planeNormalProblems(scaled, 0.75, 0.375), [], 'slope = a * heightScale / cellSize');
  const length = Math.hypot(0.5, 1, 0.25);
  assert.ok(Math.abs(scaled.normals[1] - 1 / Math.hypot(0.75, 1, 0.375)) < 1e-6);
  assert.ok(Math.abs(1 / length - 0.8728715609439696) < 1e-12);
});

test('known wrong: a normal that ignores the cell size is refused', () => {
  const mesh = heightfieldTerrainData(plane(6, 5, 0.5, 0.25), 6, 5, {cellSize: 2, heightScale: 3});
  assert.notDeepEqual(planeNormalProblems(mesh, 1.5, 0.75), [], 'the slope without dividing by the cell size');
});

test('skirts, a bottom and an LOD stride have the expected counts and make a closed block', () => {
  const heights = plane(5, 4, 0.5, 0.25);
  const skirted = heightfieldTerrainData(heights, 5, 4, {skirt: true});
  assert.equal(skirted.positions.length / 3, 20 + 2 * (2 * 5 + 2 * 4));
  assert.equal(skirted.indices.length, 6 * 12 + 6 * (2 * 4 + 2 * 3));
  const block = heightfieldTerrainData(heights, 5, 4, {skirt: true, closeBottom: true, skirtBase: -1, center: false});
  assert.deepEqual(solidProblems(block), []);
  assert.ok(Math.abs(signedVolume(block) - 28.5) < 1e-5, `volume ${signedVolume(block)}`);
  const lod = heightfieldTerrainData(plane(9, 5, 0.1, 0.2), 9, 5, {stride: 2});
  assert.deepEqual([lod.columns, lod.rows], [5, 3]);
  assert.deepEqual(planeNormalProblems(lod, 0.1, 0.2), []);
});

test('sampleHeight is bilinear and sampleSurfaceHeight follows the mesh triangles', () => {
  const ramp = [0, 1, 2, 3];
  assert.equal(sampleHeight(ramp, 2, 2, 0.5, 0.5), 1.5);
  assert.equal(sampleHeight(ramp, 2, 2, 0.25, 0.75), 1.75);
  assert.equal(sampleHeight(ramp, 2, 2, -4, 9), 2, 'clamped to the border');
  const saddle = [0, 0, 0, 1];
  assert.equal(sampleSurfaceHeight(saddle, 2, 2, 0.25, 0.25), 0);
  assert.equal(sampleSurfaceHeight(saddle, 2, 2, 0.75, 0.75), 0.5);
  assert.equal(sampleHeight(saddle, 2, 2, 0.75, 0.75), 0.5625, 'bilinear differs inside a non-planar cell');
  const field = plane(7, 6, 0.3, -0.2);
  for (const [x, z] of [[1.3, 2.7], [5.9, 0.2], [0, 4.5]]) {
    assert.ok(Math.abs(sampleSurfaceHeight(field, 7, 6, x, z) - (0.3 * x - 0.2 * z)) < 1e-6);
    assert.ok(Math.abs(sampleHeight(field, 7, 6, x, z) - (0.3 * x - 0.2 * z)) < 1e-6);
  }
});

test('known wrong: a flipped triangle and a missing triangle are refused', () => {
  const block = heightfieldTerrainData(plane(4, 4, 0.2, 0.1), 4, 4, {skirt: true, closeBottom: true});
  const flipped = {...block, indices: Uint16Array.from(block.indices)};
  [flipped.indices[1], flipped.indices[2]] = [flipped.indices[2], flipped.indices[1]];
  assert.notDeepEqual(solidProblems(flipped), []);
  assert.notDeepEqual(solidProblems({...block, indices: block.indices.slice(3)}), []);
});

test('invalid fields and options are refused', () => {
  assert.throws(() => heightfieldTerrainData(new Float32Array(5), 2, 3), RangeError);
  assert.throws(() => heightfieldTerrainData([0, 1, Number.NaN, 2], 2, 2), RangeError);
  assert.throws(() => heightfieldTerrainData(new Float32Array(25), 5, 5, {stride: 3}), RangeError);
  assert.throws(() => heightfieldTerrainData(new Float32Array(4), 2, 2, {closeBottom: true}), RangeError);
  assert.throws(() => heightfieldTerrainData(new Float32Array(4), 2, 2, {skirt: true, skirtBase: 1}), RangeError);
  assert.throws(() => heightfieldTerrainData(new Float32Array(4), 2, 2, {scale: 2}), TypeError);
  assert.throws(() => heightfieldTerrainData(new Float32Array(4), 2, 2, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => sampleHeight('heights', 2, 2, 0, 0), TypeError);
  assert.equal(HEIGHTFIELD_DEFAULTS.stride, 1);
});

test('createHeightfieldTerrainGeometry fills a BufferGeometry', () => {
  const FakeThree = {
    BufferAttribute: class { constructor(array, itemSize) { Object.assign(this, {array, itemSize}); } },
    BufferGeometry: class {
      constructor() { this.attributes = {}; this.bounds = 0; }
      setAttribute(name, attribute) { this.attributes[name] = attribute; }
      setIndex(index) { this.index = index; }
      computeBoundingBox() { this.bounds += 1; }
      computeBoundingSphere() { this.bounds += 1; }
    },
  };
  const geometry = createHeightfieldTerrainGeometry(FakeThree, plane(3, 3, 0, 0), 3, 3, {skirt: true});
  assert.deepEqual(Object.keys(geometry.attributes), ['position', 'normal', 'uv']);
  assert.equal(geometry.attributes.position.array.length, (9 + 24) * 3);
  assert.equal(geometry.index.array.length, 24 + 48);
  assert.equal(geometry.bounds, 2);
});
