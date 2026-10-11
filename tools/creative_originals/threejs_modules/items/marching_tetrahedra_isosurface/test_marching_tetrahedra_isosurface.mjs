// Known answers for marching tetrahedra: a sampled sphere distance field gives a welded closed manifold with Euler
// characteristic 2, vertices on the sphere, radial normals and the ball's volume within 2 percent; a torus gives 0 and
// two separate balls give 4; a metaball density (inside above the level) gives an outward sphere of radius
// sqrt(strength); empty and full fields give nothing; the sampler stores values x-fastest. Known-wrong controls: an
// unwelded copy of the surface and a flipped triangle are refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MARCHING_TETRAHEDRA_DEFAULTS, createIsosurfaceGeometry, marchingTetrahedraData, sampleScalarField,
} from './marching_tetrahedra_isosurface.mjs';

const sphere = (radius) => (x, y, z) => Math.hypot(x, y, z) - radius;

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

// Closed by index (each directed edge once, its reverse once), faces agreeing with vertex normals; Euler V - E + F.
function surface(mesh) {
  const problems = [];
  const edges = new Map();
  const used = new Set();
  for (let t = 0; t < mesh.indices.length; t += 3) {
    const corner = [0, 1, 2].map((k) => mesh.indices[t + k]);
    corner.forEach((index) => used.add(index));
    for (let k = 0; k < 3; k += 1) {
      const key = `${corner[k]}>${corner[(k + 1) % 3]}`;
      edges.set(key, (edges.get(key) || 0) + 1);
    }
    const [a, b, c] = corner.map((index) => vertex(mesh.positions, index));
    const u = b.map((value, i) => value - a[i]);
    const w = c.map((value, i) => value - a[i]);
    const face = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]];
    const normal = corner.map((index) => vertex(mesh.normals, index)).reduce((sum, n) => sum.map((value, i) => value + n[i]));
    if (face[0] * normal[0] + face[1] * normal[1] + face[2] * normal[2] < 0) problems.push(`triangle ${t / 3} faces inward`);
  }
  for (const [key, count] of edges) {
    const [from, to] = key.split('>');
    if (count !== 1 || edges.get(`${to}>${from}`) !== 1) problems.push(`edge ${key} is not shared once each way`);
  }
  return {problems: problems.slice(0, 5), euler: used.size - edges.size / 2 + mesh.indices.length / 3};
}

test('a sphere distance field gives a closed sphere with the ball volume', () => {
  const field = sampleScalarField(sphere(0.8), {resolution: 33});
  const mesh = marchingTetrahedraData(field);
  const {problems, euler} = surface(mesh);
  assert.deepEqual(problems, []);
  assert.equal(euler, 2);
  const ball = (4 / 3) * Math.PI * 0.8 ** 3;
  assert.ok(Math.abs(ball - 2.1446605848506324) < 1e-12);
  assert.ok(Math.abs(signedVolume(mesh) - ball) < 0.02 * ball, `volume ${signedVolume(mesh)}`);
  for (let v = 0; v < mesh.positions.length / 3; v += 1) {
    const point = vertex(mesh.positions, v);
    const radius = Math.hypot(...point);
    assert.ok(Math.abs(radius - 0.8) < 0.01, `vertex ${v} at radius ${radius}`);
    const normal = vertex(mesh.normals, v);
    assert.ok((normal[0] * point[0] + normal[1] * point[1] + normal[2] * point[2]) / radius > 0.99, `normal ${v} is radial`);
  }
});

test('a torus has Euler characteristic 0, two balls 4, empty and full fields nothing', () => {
  const torus = (x, y, z) => Math.hypot(Math.hypot(x, z) - 0.55, y) - 0.2;
  assert.equal(surface(marchingTetrahedraData(sampleScalarField(torus, {resolution: 41}))).euler, 0);
  const pair = (x, y, z) => Math.min(Math.hypot(x - 0.5, y, z) - 0.3, Math.hypot(x + 0.5, y, z) - 0.3);
  const two = marchingTetrahedraData(sampleScalarField(pair, {resolution: [41, 21, 21], min: [-1, -0.5, -0.5], max: [1, 0.5, 0.5]}));
  assert.deepEqual(surface(two).problems, []);
  assert.equal(surface(two).euler, 4);
  assert.equal(marchingTetrahedraData(sampleScalarField(() => 1, {resolution: 6})).indices.length, 0);
  assert.equal(marchingTetrahedraData(sampleScalarField(() => -1, {resolution: 6})).indices.length, 0);
});

test('a metaball density with insideBelow false gives an outward sphere of radius sqrt(strength)', () => {
  const density = (x, y, z) => 0.1 / (x * x + y * y + z * z + 1e-9);
  const mesh = marchingTetrahedraData(sampleScalarField(density, {resolution: 33, min: [-0.6, -0.6, -0.6], max: [0.6, 0.6, 0.6]}),
    {isoLevel: 1, insideBelow: false});
  const {problems, euler} = surface(mesh);
  assert.deepEqual(problems, []);
  assert.equal(euler, 2);
  const radius = Math.sqrt(0.1);
  assert.ok(Math.abs(signedVolume(mesh) - (4 / 3) * Math.PI * radius ** 3) < 0.03 * (4 / 3) * Math.PI * radius ** 3);
  for (let v = 0; v < mesh.positions.length / 3; v += 1) {
    const point = vertex(mesh.positions, v);
    const normal = vertex(mesh.normals, v);
    assert.ok(normal[0] * point[0] + normal[1] * point[1] + normal[2] * point[2] > 0, `normal ${v} points out`);
  }
});

test('sampleScalarField stores values x-fastest on the box grid', () => {
  const field = sampleScalarField((x, y, z) => x + 2 * y + 3 * z, {min: [0, 0, 0], max: [1, 1, 1], resolution: 3});
  assert.deepEqual(field.size, [3, 3, 3]);
  assert.equal(field.values[2 + 3 * (1 + 3 * 0)], 2);
  assert.equal(field.values[0 + 3 * (0 + 3 * 2)], 3);
  assert.equal(field.values.length, 27);
});

test('known wrong: an unwelded copy and a flipped triangle are refused', () => {
  const mesh = marchingTetrahedraData(sampleScalarField(sphere(0.6), {resolution: 9}));
  const corners = Array.from(mesh.indices);
  const unwelded = {
    positions: Float32Array.from(corners.flatMap((index) => vertex(mesh.positions, index))),
    normals: Float32Array.from(corners.flatMap((index) => vertex(mesh.normals, index))),
    indices: Uint32Array.from(corners.map((_, k) => k)),
  };
  assert.notDeepEqual(surface(unwelded).problems, []);
  const flipped = {...mesh, indices: Uint16Array.from(mesh.indices)};
  [flipped.indices[1], flipped.indices[2]] = [flipped.indices[2], flipped.indices[1]];
  assert.notDeepEqual(surface(flipped).problems, []);
});

test('invalid fields and options are refused', () => {
  const field = sampleScalarField(sphere(0.5), {resolution: 5});
  assert.throws(() => marchingTetrahedraData({...field, values: field.values.slice(1)}), RangeError);
  assert.throws(() => marchingTetrahedraData(field, {iso: 0}), TypeError);
  assert.throws(() => marchingTetrahedraData(field, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => marchingTetrahedraData(field, {maxVertices: 3}), RangeError);
  assert.throws(() => sampleScalarField(sphere(0.5), {resolution: 1}), RangeError);
  assert.throws(() => sampleScalarField(sphere(0.5), {min: [1, 0, 0], max: [0, 1, 1]}), RangeError);
  assert.throws(() => sampleScalarField(() => Number.NaN, {resolution: 3}), RangeError);
  assert.throws(() => sampleScalarField('sphere'), TypeError);
  assert.equal(MARCHING_TETRAHEDRA_DEFAULTS.isoLevel, 0);
});

test('createIsosurfaceGeometry fills a BufferGeometry', () => {
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
  const geometry = createIsosurfaceGeometry(FakeThree, sampleScalarField(sphere(0.5), {resolution: 9}));
  assert.deepEqual(Object.keys(geometry.attributes), ['position', 'normal']);
  assert.ok(geometry.index.array.length > 0 && geometry.index.array.length % 3 === 0);
  assert.equal(geometry.bounds, 2);
});
