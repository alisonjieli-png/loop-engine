// Known answers for tangent frames: a plane with u along x gives (1, 0, 0, 1), mirrored u gives (-1, 0, 0, -1),
// u along y gives (0, 1, 0, 1); a cylinder gets its exact circumferential tangent with w = -1 at every vertex, seam
// included; degenerate UVs fall back to a unit perpendicular; soups and indexed meshes agree; addTangents sets the
// vec4 attribute. Known-wrong controls: tangents without Gram-Schmidt, and a handedness fixed at +1, are refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {TANGENT_FRAME_DEFAULTS, addTangents, computeVertexTangents} from './vertex_tangent_frames.mjs';

const PLANE = {
  positions: [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0],
  normals: [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1],
  indices: [0, 1, 2, 0, 2, 3],
};

function cylinder(segments) {
  const positions = [];
  const normals = [];
  const uvs = [];
  for (let row = 0; row < 2; row += 1) {
    for (let k = 0; k <= segments; k += 1) {
      const angle = (2 * Math.PI * k) / segments;
      positions.push(Math.cos(angle), row, Math.sin(angle));
      normals.push(Math.cos(angle), 0, Math.sin(angle));
      uvs.push(k / segments, row);
    }
  }
  const indices = [];
  for (let k = 0; k < segments; k += 1) {
    const a = k;
    const d = k + segments + 1;
    indices.push(a, a + 1, d + 1, a, d + 1, d);
  }
  return {positions, normals, uvs, indices, segments};
}

function allEqual(tangents, expected) {
  for (let v = 0; v < tangents.length / 4; v += 1) {
    const actual = Array.from(tangents.subarray(v * 4, v * 4 + 4));
    if (actual.some((value, k) => Math.abs(value - expected[k]) > 1e-6)) return false;
  }
  return true;
}

// The cylinder's tangent at angle phi is (-sin phi, 0, cos phi) and its handedness -1, at every vertex.
function cylinderProblems(compute) {
  const shape = cylinder(12);
  const tangents = compute(shape.positions, shape.normals, shape.uvs, shape.indices);
  const problems = [];
  for (let v = 0; v < tangents.length / 4; v += 1) {
    const angle = (2 * Math.PI * (v % (shape.segments + 1))) / shape.segments;
    const expected = [-Math.sin(angle), 0, Math.cos(angle), -1];
    if (expected.some((value, k) => Math.abs(tangents[v * 4 + k] - value) > 1e-6)) problems.push(`vertex ${v}`);
  }
  return problems.slice(0, 3);
}

test('plane tangents follow u and its mirror', () => {
  const forward = computeVertexTangents(PLANE.positions, PLANE.normals, [0, 0, 1, 0, 1, 1, 0, 1], PLANE.indices);
  assert.ok(allEqual(forward, [1, 0, 0, 1]));
  const mirrored = computeVertexTangents(PLANE.positions, PLANE.normals, [1, 0, 0, 0, 0, 1, 1, 1], PLANE.indices);
  assert.ok(allEqual(mirrored, [-1, 0, 0, -1]));
  const turned = computeVertexTangents(PLANE.positions, PLANE.normals, [0, 1, 0, 0, 1, 0, 1, 1], PLANE.indices);
  assert.ok(allEqual(turned, [0, 1, 0, 1]));
});

test('a cylinder gets its exact circumferential tangent everywhere, seam included', () => {
  assert.deepEqual(cylinderProblems(computeVertexTangents), []);
});

test('known wrong: tangents without Gram-Schmidt and a fixed handedness are refused', () => {
  const raw = (...args) => computeVertexTangents(...args, {orthogonalize: false});
  assert.notDeepEqual(cylinderProblems(raw), []);
  const rightHanded = (...args) => {
    const tangents = computeVertexTangents(...args);
    for (let v = 3; v < tangents.length; v += 4) tangents[v] = 1;
    return tangents;
  };
  assert.notDeepEqual(cylinderProblems(rightHanded), []);
});

test('degenerate UVs fall back to a unit vector perpendicular to the normal', () => {
  const normal = [0.6, 0.8, 0];
  const tangents = computeVertexTangents([0, 0, 0, 1, 0, 0, 0, 1, 0], [...normal, ...normal, ...normal], [0, 0, 0, 0, 0, 0]);
  for (let v = 0; v < 3; v += 1) {
    const t = Array.from(tangents.subarray(v * 4, v * 4 + 3));
    assert.ok(Math.abs(Math.hypot(...t) - 1) < 1e-6);
    assert.ok(Math.abs(t[0] * normal[0] + t[1] * normal[1] + t[2] * normal[2]) < 1e-6);
    assert.equal(tangents[v * 4 + 3], 1);
  }
});

test('a triangle soup and the indexed mesh agree', () => {
  const uvs = [0, 0, 1, 0, 1, 1, 0, 1];
  const soupPositions = [];
  const soupNormals = [];
  const soupUvs = [];
  for (const index of PLANE.indices) {
    soupPositions.push(...PLANE.positions.slice(index * 3, index * 3 + 3));
    soupNormals.push(...PLANE.normals.slice(index * 3, index * 3 + 3));
    soupUvs.push(...uvs.slice(index * 2, index * 2 + 2));
  }
  assert.ok(allEqual(computeVertexTangents(soupPositions, soupNormals, soupUvs), [1, 0, 0, 1]));
});

test('invalid input is refused', () => {
  assert.throws(() => computeVertexTangents([0, 0], [0, 0, 1], [0, 0]), TypeError);
  assert.throws(() => computeVertexTangents(PLANE.positions, PLANE.normals, [0, 0]), RangeError);
  assert.throws(() => computeVertexTangents(PLANE.positions, PLANE.normals, [0, 0, 1, 0, 1, 1, 0, 1], [0, 1, 7]), RangeError);
  assert.throws(() => computeVertexTangents(PLANE.positions, PLANE.normals, [0, 0, 1, 0, 1, 1, 0, 1], null, {weight: 1}), TypeError);
  assert.throws(() => computeVertexTangents(PLANE.positions, PLANE.normals, [0, 0, 1, 0, 1, 1, 0, 1], null, {toString: 1}),
    TypeError, 'an inherited name is not an option');
  assert.equal(TANGENT_FRAME_DEFAULTS.orthogonalize, true);
});

test('addTangents sets a vec4 tangent attribute on a BufferGeometry', () => {
  const uvs = [0, 0, 1, 0, 1, 1, 0, 1];
  const attributes = {position: {array: Float32Array.from(PLANE.positions)}, normal: {array: Float32Array.from(PLANE.normals)},
    uv: {array: Float32Array.from(uvs)}};
  const geometry = {
    set: {},
    getAttribute(name) { return attributes[name]; },
    getIndex() { return {array: Uint16Array.from(PLANE.indices)}; },
    setAttribute(name, attribute) { this.set[name] = attribute; },
  };
  const FakeThree = {BufferAttribute: class { constructor(array, itemSize) { Object.assign(this, {array, itemSize}); } }};
  assert.equal(addTangents(FakeThree, geometry), geometry);
  assert.equal(geometry.set.tangent.itemSize, 4);
  assert.ok(allEqual(geometry.set.tangent.array, [1, 0, 0, 1]));
  delete attributes.uv;
  assert.throws(() => addTangents(FakeThree, geometry), TypeError);
});
