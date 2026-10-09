// Known answers for the rounded box: vertex and index counts, bounds, closed surface, outward winding, unit normals,
// the exact volume of the smooth shape, the sharp-box and sphere limits, and the three.js geometry it builds (with a
// minimal stand-in for THREE). Each mesh check also runs on a known-wrong mesh that it must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {ROUNDED_BOX_DEFAULTS, createRoundedBoxGeometry, roundedBoxData, roundedBoxVolume} from './rounded_box_geometry.mjs';

function vertex(positions, index) {
  return [positions[index * 3], positions[index * 3 + 1], positions[index * 3 + 2]];
}

function signedVolume(mesh) {
  let volume = 0;
  for (let t = 0; t < mesh.indices.length; t += 3) {
    const [a, b, c] = [0, 1, 2].map((k) => vertex(mesh.positions, mesh.indices[t + k]));
    volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6;
  }
  return volume;
}

// Problems that make a mesh unusable as a closed solid: an edge not shared by exactly two triangles with opposite
// directions (after welding equal positions), a normal that is not unit length or points against its triangle.
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
    if (corner[0] === corner[1] || corner[1] === corner[2] || corner[0] === corner[2]) continue;
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

function bounds(mesh) {
  const low = [Infinity, Infinity, Infinity];
  const high = [-Infinity, -Infinity, -Infinity];
  for (let v = 0; v < mesh.positions.length / 3; v += 1) {
    vertex(mesh.positions, v).forEach((value, axis) => {
      low[axis] = Math.min(low[axis], value);
      high[axis] = Math.max(high[axis], value);
    });
  }
  return [low, high];
}

test('roundedBoxData has the expected counts, bounds and groups', () => {
  const mesh = roundedBoxData();
  assert.equal(mesh.positions.length / 3, 600);
  assert.equal(mesh.indices.length, 2916);
  assert.ok(mesh.indices instanceof Uint16Array);
  assert.deepEqual(mesh.groups.map((group) => group.materialIndex), [0, 1, 2, 3, 4, 5]);
  assert.equal(mesh.groups.reduce((sum, group) => sum + group.count, 0), mesh.indices.length);
  const [low, high] = bounds(roundedBoxData({width: 2, height: 1, depth: 1.4, radius: 0.25}));
  low.forEach((value, axis) => assert.ok(Math.abs(value + [1, 0.5, 0.7][axis]) < 1e-6));
  high.forEach((value, axis) => assert.ok(Math.abs(value - [1, 0.5, 0.7][axis]) < 1e-6));
  for (let k = 0; k < mesh.uvs.length; k += 1) assert.ok(mesh.uvs[k] >= 0 && mesh.uvs[k] <= 1);
});

test('the rounded box is a closed, outward-facing solid with the smooth volume', () => {
  const options = {width: 2, height: 1, depth: 1.4, radius: 0.25, bevelSegments: 8, flatSegments: 2};
  const mesh = roundedBoxData(options);
  assert.deepEqual(solidProblems(mesh), []);
  const exact = roundedBoxVolume(2, 1, 1.4, 0.25);
  assert.ok(Math.abs(exact - 2.5848635154129373) < 1e-12, 'the closed-form volume');
  const volume = signedVolume(mesh);
  assert.ok(volume < exact && exact - volume < 0.004 * exact, `mesh volume ${volume} is just under ${exact}`);
});

test('limits: a zero radius is the sharp box, a radius of half the size is a sphere', () => {
  const sharp = roundedBoxData({width: 2, height: 1, depth: 1.4, radius: 0});
  assert.deepEqual(solidProblems(sharp), []);
  assert.ok(Math.abs(signedVolume(sharp) - 2.8) < 1e-6);
  assert.ok(Math.abs(roundedBoxVolume(2, 1, 1.4, 0) - 2.8) < 1e-12);
  const sphere = roundedBoxData({radius: 0.5, bevelSegments: 6});
  assert.deepEqual(solidProblems(sphere), []);
  for (let v = 0; v < sphere.positions.length / 3; v += 1) {
    assert.ok(Math.abs(Math.hypot(...vertex(sphere.positions, v)) - 0.5) < 1e-6);
  }
  assert.ok(Math.abs(roundedBoxVolume(1, 1, 1, 0.5) - Math.PI / 6) < 1e-12);
});

test('known wrong: a flipped triangle and a missing triangle are refused', () => {
  const mesh = roundedBoxData({bevelSegments: 2});
  const flipped = {...mesh, indices: Uint16Array.from(mesh.indices)};
  [flipped.indices[1], flipped.indices[2]] = [flipped.indices[2], flipped.indices[1]];
  assert.notDeepEqual(solidProblems(flipped), []);
  const holed = {...mesh, indices: mesh.indices.slice(3)};
  assert.notDeepEqual(solidProblems(holed), []);
});

test('invalid options are refused', () => {
  assert.throws(() => roundedBoxData({radius: 0.6}), RangeError);
  assert.throws(() => roundedBoxData({bevelSegments: 0}), RangeError);
  assert.throws(() => roundedBoxData({width: -1}), RangeError);
  assert.throws(() => roundedBoxData({radious: 0.1}), TypeError);
  assert.throws(() => roundedBoxVolume(1, 1, 1, 0.7), RangeError);
  assert.equal(ROUNDED_BOX_DEFAULTS.radius, 0.1);
});

test('createRoundedBoxGeometry fills a BufferGeometry', () => {
  const calls = [];
  const FakeThree = {
    BufferAttribute: class { constructor(array, itemSize) { Object.assign(this, {array, itemSize}); } },
    BufferGeometry: class {
      constructor() { this.attributes = {}; this.groups = []; }
      setAttribute(name, attribute) { this.attributes[name] = attribute; }
      setIndex(index) { this.index = index; }
      addGroup(start, count, materialIndex) { this.groups.push({start, count, materialIndex}); }
      computeBoundingBox() { calls.push('box'); }
      computeBoundingSphere() { calls.push('sphere'); }
    },
  };
  const geometry = createRoundedBoxGeometry(FakeThree, {radius: 0.2});
  assert.deepEqual(Object.keys(geometry.attributes), ['position', 'normal', 'uv']);
  assert.equal(geometry.attributes.uv.itemSize, 2);
  assert.equal(geometry.index.array.length, 2916);
  assert.equal(geometry.groups.length, 6);
  assert.deepEqual(calls, ['box', 'sphere']);
});
