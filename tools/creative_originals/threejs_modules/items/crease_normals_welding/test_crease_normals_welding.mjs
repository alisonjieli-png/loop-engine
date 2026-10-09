// Known answers for welding and crease normals: a cube triangle soup welds to 8 vertices and creases into 24 with
// axis normals, a subdivided octahedron sphere welds to 4 * 4^n + 2 vertices and stays smooth at 60 degrees, a capped
// cylinder splits only its rims (4N + 2 vertices), the tolerance decides what merges, UV seams stay split, and the
// three.js geometry is rebuilt. Known-wrong control: smoothing across every edge gives a cube diagonal normals.
import test from 'node:test';
import assert from 'node:assert/strict';
import {CREASE_NORMALS_DEFAULTS, createCreasedGeometry, creaseNormals, weldVertices} from './crease_normals_welding.mjs';

function cubeSoup() {
  const faces = [
    [[1, -1, -1], [1, 1, -1], [1, 1, 1], [1, -1, 1]], [[-1, -1, 1], [-1, 1, 1], [-1, 1, -1], [-1, -1, -1]],
    [[-1, 1, -1], [-1, 1, 1], [1, 1, 1], [1, 1, -1]], [[-1, -1, 1], [-1, -1, -1], [1, -1, -1], [1, -1, 1]],
    [[-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], [[1, -1, -1], [-1, -1, -1], [-1, 1, -1], [1, 1, -1]],
  ];
  const values = [];
  for (const [a, b, c, d] of faces) values.push(...a, ...b, ...c, ...a, ...c, ...d);
  return Float32Array.from(values.map((value) => value / 2));
}

function octasphere(levels) {
  let triangles = [];
  const axes = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
  for (const x of [0, 1]) for (const y of [2, 3]) for (const z of [4, 5]) {
    const corner = [axes[x], axes[y], axes[z]];
    const outward = (x === 0) === (y === 2) === (z === 4);
    triangles.push(outward ? corner : [corner[0], corner[2], corner[1]]);
  }
  const unit = (p) => p.map((value) => value / Math.hypot(...p));
  const middle = (p, q) => unit(p.map((value, i) => (value + q[i]) / 2));
  for (let level = 0; level < levels; level += 1) {
    triangles = triangles.flatMap(([a, b, c]) => {
      const ab = middle(a, b);
      const bc = middle(b, c);
      const ca = middle(c, a);
      return [[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]];
    });
  }
  return Float32Array.from(triangles.flat(2));
}

function cylinderSoup(segments) {
  const values = [];
  const rim = (k, y) => [Math.cos((2 * Math.PI * k) / segments), y, -Math.sin((2 * Math.PI * k) / segments)];
  for (let k = 0; k < segments; k += 1) {
    const [a, b, c, d] = [rim(k, -1), rim(k + 1, -1), rim(k + 1, 1), rim(k, 1)];
    values.push(...a, ...b, ...c, ...a, ...c, ...d);
    values.push(0, 1, 0, ...rim(k, 1), ...rim(k + 1, 1));
    values.push(0, -1, 0, ...rim(k + 1, -1), ...rim(k, -1));
  }
  return Float32Array.from(values);
}

// Each cube vertex normal is one axis direction and agrees with its triangle.
function cubeProblems(result) {
  const problems = [];
  for (let v = 0; v < result.normals.length / 3; v += 1) {
    const normal = Array.from(result.normals.subarray(v * 3, v * 3 + 3));
    if (normal.filter((value) => Math.abs(Math.abs(value) - 1) < 1e-9).length !== 1) problems.push(`normal ${v}: ${normal}`);
  }
  if (result.positions.length / 3 !== 24) problems.push(`${result.positions.length / 3} vertices`);
  return problems.slice(0, 3);
}

test('a cube soup welds to 8 vertices and creases into 24 with axis normals', () => {
  const soup = cubeSoup();
  const welded = weldVertices(soup);
  assert.equal(welded.positions.length / 3, 8);
  assert.equal(welded.indices.length, 36);
  assert.equal(Math.max(...welded.remap) + 1, 8);
  const creased = creaseNormals(soup, null, 30);
  assert.deepEqual(cubeProblems(creased), []);
  assert.equal(creased.indices.length, 36);
  assert.equal(creased.uvs, null);
});

test('known wrong: smoothing across every edge gives the cube diagonal normals and is refused', () => {
  assert.notDeepEqual(cubeProblems(creaseNormals(cubeSoup(), null, 180)), []);
});

test('a subdivided sphere welds to 4 * 4^n + 2 vertices and stays smooth at 60 degrees', () => {
  const soup = octasphere(2);
  assert.equal(soup.length / 3, 384);
  assert.equal(weldVertices(soup).positions.length / 3, 66);
  const smooth = creaseNormals(soup, null, 60);
  assert.equal(smooth.positions.length / 3, 66);
  for (let v = 0; v < 66; v += 1) {
    const p = Array.from(smooth.positions.subarray(v * 3, v * 3 + 3));
    const n = Array.from(smooth.normals.subarray(v * 3, v * 3 + 3));
    assert.ok(p[0] * n[0] + p[1] * n[1] + p[2] * n[2] > 0.97, `normal ${v} is near radial`);
  }
  assert.equal(creaseNormals(soup, null, 0).positions.length / 3, 384, 'every face apart at 0 degrees');
});

test('a capped cylinder splits only its rims', () => {
  const soup = cylinderSoup(16);
  assert.equal(weldVertices(soup).positions.length / 3, 2 * 16 + 2);
  const creased = creaseNormals(soup, null, 60);
  assert.equal(creased.positions.length / 3, 4 * 16 + 2);
  for (let v = 0; v < creased.positions.length / 3; v += 1) {
    const ny = creased.normals[v * 3 + 1];
    assert.ok(Math.abs(ny) < 1e-9 || Math.abs(Math.abs(ny) - 1) < 1e-9, `normal ${v} is a side or a cap normal`);
  }
});

test('the tolerance decides which nearby vertices merge, and UV seams stay split', () => {
  const e = 5e-7;
  const pair = Float32Array.from([0, 0, 0, 1, 0, 0, 0, 1, 0, 1 + e, 0, 0, 1, 1, 0, 0, 1 + e, 0]);
  assert.equal(weldVertices(pair, 1e-6).positions.length / 3, 4);
  assert.equal(weldVertices(pair, 1e-9).positions.length / 3, 6);
  assert.equal(weldVertices(pair, 0).positions.length / 3, 6);
  const square = Float32Array.from([0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0]);
  const together = [0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1];
  const apart = [0, 0, 1, 0, 0, 1, 0.5, 0, 1, 1, 0.5, 1];
  assert.equal(creaseNormals(square, null, 30, {uvs: together}).positions.length / 3, 4);
  assert.equal(creaseNormals(square, null, 30, {uvs: apart}).positions.length / 3, 6);
  assert.equal(creaseNormals(square, null, 30, {uvs: apart}).uvs.length, 12);
});

test('indexed input and invalid input', () => {
  const welded = weldVertices(cubeSoup());
  const again = creaseNormals(welded.positions, welded.indices, 30);
  assert.deepEqual(cubeProblems(again), []);
  assert.throws(() => weldVertices(new Float32Array([0, 0])), TypeError);
  assert.throws(() => weldVertices(new Float32Array([0, 0, 0, 1, 1, 1])), RangeError);
  assert.throws(() => weldVertices(cubeSoup(), -1), RangeError);
  assert.throws(() => creaseNormals(welded.positions, [0, 1, 99], 30), RangeError);
  assert.throws(() => creaseNormals(cubeSoup(), null, 200), RangeError);
  assert.throws(() => creaseNormals(cubeSoup(), null, 30, {smooth: true}), TypeError);
  assert.throws(() => creaseNormals(cubeSoup(), null, 30, {uvs: [0, 0]}), RangeError);
  assert.equal(CREASE_NORMALS_DEFAULTS.creaseAngle, 30);
});

test('createCreasedGeometry rebuilds a BufferGeometry', () => {
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
  const source = {
    getAttribute: (name) => (name === 'position' ? {array: cubeSoup(), itemSize: 3, count: 36} : undefined),
    getIndex: () => null,
  };
  const geometry = createCreasedGeometry(FakeThree, source, 30);
  assert.deepEqual(Object.keys(geometry.attributes), ['position', 'normal']);
  assert.equal(geometry.attributes.position.array.length, 24 * 3);
  assert.equal(geometry.index.array.length, 36);
  assert.equal(geometry.bounds, 2);
});
