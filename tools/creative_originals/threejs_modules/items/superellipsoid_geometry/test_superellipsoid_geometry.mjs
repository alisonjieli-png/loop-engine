// Known answers for the superellipsoid: the closed-form volume against values computed independently (Python's
// math.lgamma), vertex and index counts, exact bounds, every vertex on Barr's surface (inside-outside value 1), a
// closed outward mesh with unit normals, the mesh volume converging from below, and the three.js geometry (with a
// minimal stand-in for THREE). Known-wrong controls: a doubled volume formula, a flipped and a missing triangle.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SUPERELLIPSOID_DEFAULTS, createSuperellipsoidGeometry, superellipsoidData, superellipsoidImplicit, superellipsoidVolume,
} from './superellipsoid_geometry.mjs';

// [radiusX, radiusY, radiusZ, exponentY, exponentXZ] -> volume from 2abc e1 e2 B(e1/2 + 1, e1) B(e2/2, e2/2) in Python.
const VOLUMES = [
  [[1, 2, 3, 1, 1], 8 * Math.PI],
  [[1, 2, 3, 2, 2], 8],
  [[1, 1, 1, 0.5, 0.5], 6.4819873517863815],
  [[1.5, 1, 0.8, 0.3, 1.5], 5.76737800399002],
  [[1, 1, 1, 1, 0.25], 5.218457717084229],
];

function volumeProblems(volume) {
  return VOLUMES.filter(([args, expected]) => Math.abs(volume(...args) - expected) > 1e-9 * expected)
    .map(([args]) => `volume(${args}) = ${volume(...args)}`);
}

function vertex(array, index) {
  return [array[index * 3], array[index * 3 + 1], array[index * 3 + 2]];
}

function signedVolume(mesh) {
  let volume = 0;
  for (let t = 0; t < mesh.indices.length; t += 3) {
    const [a, b, c] = [0, 1, 2].map((k) => vertex(mesh.positions, mesh.indices[t + k]));
    volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6;
  }
  return volume;
}

// Closed (every welded edge shared once in each direction), outward (each triangle agrees with its first vertex
// normal) and unit normals.
function solidProblems(mesh) {
  const problems = [];
  const keys = new Map();
  const weld = [];
  for (let v = 0; v < mesh.positions.length / 3; v += 1) {
    const key = vertex(mesh.positions, v).map((value) => value.toFixed(6)).join(',');
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
    const [a, b, c] = [0, 1, 2].map((k) => vertex(mesh.positions, mesh.indices[t + k]));
    const face = [
      (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]),
      (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
      (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]),
    ];
    const normal = vertex(mesh.normals, mesh.indices[t]);
    if (face[0] * normal[0] + face[1] * normal[1] + face[2] * normal[2] < 0) problems.push(`triangle ${t / 3} faces inward`);
  }
  for (const [key, count] of edges) {
    const [from, to] = key.split('>');
    if (count !== 1 || edges.get(`${to}>${from}`) !== 1) problems.push(`edge ${key} is not shared once each way`);
  }
  for (let v = 0; v < mesh.normals.length / 3; v += 1) {
    const length = Math.hypot(...vertex(mesh.normals, v));
    if (Math.abs(length - 1) > 1e-5) problems.push(`normal ${v} has length ${length}`);
  }
  return problems.slice(0, 5);
}

test('superellipsoidVolume matches independently computed values', () => {
  assert.deepEqual(volumeProblems(superellipsoidVolume), []);
  assert.ok(Math.abs(superellipsoidVolume(1, 1, 1, 0.02, 0.02) - 8) < 0.01, 'small exponents approach the cube');
});

test('known wrong: the misread formula 2abc e1 e2 B(e1/2, e1 + 1) B(e2/2, e2/2), which doubles every volume, is refused', () => {
  assert.notDeepEqual(volumeProblems((...args) => 2 * superellipsoidVolume(...args)), []);
});

test('superellipsoidData has the expected counts, bounds and surface', () => {
  const mesh = superellipsoidData();
  assert.equal(mesh.positions.length, 49 * 33 * 3);
  assert.equal(mesh.indices.length, 6 * 48 * 31);
  assert.ok(mesh.indices instanceof Uint16Array);
  const options = {radiusX: 1.5, radiusY: 0.7, radiusZ: 0.9, exponentY: 0.4, exponentXZ: 1.6};
  const shaped = superellipsoidData(options);
  const low = [Infinity, Infinity, Infinity];
  const high = [-Infinity, -Infinity, -Infinity];
  for (let v = 0; v < shaped.positions.length / 3; v += 1) {
    const [x, y, z] = vertex(shaped.positions, v);
    [x, y, z].forEach((value, axis) => {
      low[axis] = Math.min(low[axis], value);
      high[axis] = Math.max(high[axis], value);
    });
    const {exponentY, exponentXZ, radiusX, radiusY, radiusZ} = options;
    const value = superellipsoidImplicit(x, y, z, {exponentY, exponentXZ, radiusX, radiusY, radiusZ});
    if (Math.abs(x) + Math.abs(y) + Math.abs(z) > 1e-3) assert.ok(Math.abs(value - 1) < 2e-5, `vertex ${v} gives ${value}`);
  }
  [1.5, 0.7, 0.9].forEach((radius, axis) => {
    assert.ok(Math.abs(high[axis] - radius) < 1e-6 && Math.abs(low[axis] + radius) < 1e-6, `axis ${axis}`);
  });
  for (let k = 0; k < shaped.uvs.length; k += 1) assert.ok(shaped.uvs[k] >= 0 && shaped.uvs[k] <= 1);
});

test('superellipsoidImplicit separates inside from outside', () => {
  assert.equal(superellipsoidImplicit(0, 0, 0), 0);
  assert.ok(Math.abs(superellipsoidImplicit(1, 0, 0) - 1) < 1e-12);
  assert.ok(superellipsoidImplicit(0.9, 0.9, 0.9, {exponentY: 0.1, exponentXZ: 0.1}) < 1, 'a box-like shape holds its corner');
  assert.ok(superellipsoidImplicit(0.6, 0.6, 0.6, {exponentY: 1, exponentXZ: 1}) > 1, 'the sphere does not');
});

test('meshes are closed, face outward and converge to the volume from below', () => {
  for (const [exponentY, exponentXZ] of [[0.2, 0.2], [0.5, 1], [1, 1], [1.5, 0.5], [2, 2]]) {
    const mesh = superellipsoidData({exponentY, exponentXZ, widthSegments: 64, heightSegments: 40});
    assert.deepEqual(solidProblems(mesh), [], `exponents ${exponentY}, ${exponentXZ}`);
  }
  const fine = superellipsoidData({exponentY: 0.5, exponentXZ: 0.5, widthSegments: 128, heightSegments: 96});
  const exact = 6.4819873517863815;
  const volume = signedVolume(fine);
  assert.ok(volume < exact && exact - volume < 0.01 * exact, `mesh volume ${volume} is just under ${exact}`);
  const sphere = superellipsoidData({exponentY: 1, exponentXZ: 1, radiusY: 2, widthSegments: 96, heightSegments: 64});
  assert.ok(Math.abs(signedVolume(sphere) - (8 / 3) * Math.PI) < 0.005 * (8 / 3) * Math.PI);
});

test('known wrong: a flipped triangle and a missing triangle are refused', () => {
  const mesh = superellipsoidData({widthSegments: 12, heightSegments: 8});
  const flipped = {...mesh, indices: Uint16Array.from(mesh.indices)};
  [flipped.indices[40], flipped.indices[41]] = [flipped.indices[41], flipped.indices[40]];
  assert.notDeepEqual(solidProblems(flipped), []);
  assert.notDeepEqual(solidProblems({...mesh, indices: mesh.indices.slice(3)}), []);
});

test('invalid options are refused', () => {
  assert.throws(() => superellipsoidData({exponentY: 0}), RangeError);
  assert.throws(() => superellipsoidData({exponentXZ: 5}), RangeError);
  assert.throws(() => superellipsoidData({widthSegments: 2}), RangeError);
  assert.throws(() => superellipsoidData({radiusX: 0}), RangeError);
  assert.throws(() => superellipsoidData({exponent: 1}), TypeError);
  assert.throws(() => superellipsoidImplicit(0, 0, 0, {widthSegments: 4}), TypeError);
  assert.equal(SUPERELLIPSOID_DEFAULTS.exponentY, 0.5);
});

test('createSuperellipsoidGeometry fills a BufferGeometry', () => {
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
  const geometry = createSuperellipsoidGeometry(FakeThree, {widthSegments: 16, heightSegments: 8});
  assert.deepEqual(Object.keys(geometry.attributes), ['position', 'normal', 'uv']);
  assert.equal(geometry.attributes.position.array.length, 17 * 9 * 3);
  assert.equal(geometry.index.array.length, 6 * 16 * 7);
  assert.equal(geometry.bounds, 2);
});
