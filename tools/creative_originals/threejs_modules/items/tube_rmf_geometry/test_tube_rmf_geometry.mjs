// Known answers for the tube: centripetal Catmull-Rom samples against values computed independently in Python, frames
// that stay constant on a straight path and close exactly on a planar circle, the twist of a trefoil loop spread
// evenly so an independent transport (the minimal rotation between tangents) closes on the first frame, closed and
// outward meshes, prism, mitred and frustum volumes, the normal tilt of a widening tube, and the three.js geometry.
// Known-wrong controls: the uncorrected trefoil frames, a flipped triangle and a missing triangle are refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TUBE_RMF_DEFAULTS, createTubeRmfGeometry, rotationMinimizingFrames, sampleCentripetalCatmullRom, tubeRmfData,
} from './tube_rmf_geometry.mjs';

const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const angleAbout = (from, to, axis) => Math.atan2(dot(cross(from, to), axis), dot(from, to));
const TREFOIL = Array.from({length: 36}, (_, k) => {
  const t = (2 * Math.PI * k) / 36;
  return [0.3 * (Math.sin(t) + 2 * Math.sin(2 * t)), 0.3 * (Math.cos(t) - 2 * Math.cos(2 * t)), -0.3 * Math.sin(3 * t)];
});

function close(actual, expected, tolerance) {
  return actual.every((value, axis) => Math.abs(value - expected[axis]) <= tolerance);
}

// Rotate r by the smallest rotation that takes tangent a to tangent b: an independent way to carry a frame.
function minimalRotation(r, a, b) {
  const axis = cross(a, b);
  const sine = Math.hypot(...axis);
  if (sine < 1e-12) return r;
  const k = axis.map((value) => value / sine);
  const angle = Math.atan2(sine, dot(a, b));
  const kxr = cross(k, r);
  return r.map((value, i) => value * Math.cos(angle) + kxr[i] * Math.sin(angle) + k[i] * dot(k, r) * (1 - Math.cos(angle)));
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
    const [a, b, c] = [0, 1, 2].map((k) => vertex(mesh.positions, mesh.indices[t + k]));
    const face = cross(a.map((value, i) => b[i] - value), a.map((value, i) => c[i] - value));
    if (dot(face, vertex(mesh.normals, mesh.indices[t])) < 0) problems.push(`triangle ${t / 3} faces inward`);
  }
  for (const [key, count] of edges) {
    const [from, to] = key.split('>');
    if (count !== 1 || edges.get(`${to}>${from}`) !== 1) problems.push(`edge ${key} is not shared once each way`);
  }
  for (let v = 0; v < mesh.normals.length / 3; v += 1) {
    if (Math.abs(Math.hypot(...vertex(mesh.normals, v)) - 1) > 1e-5) problems.push(`normal ${v} is not unit`);
  }
  return problems.slice(0, 5);
}

test('sampleCentripetalCatmullRom passes through the points and matches the reference values', () => {
  const square = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]];
  const samples = sampleCentripetalCatmullRom(square, 4);
  assert.equal(samples.points.length, 13);
  assert.deepEqual(samples.points[4], [1, 0, 0]);
  assert.deepEqual(samples.points[12], [0, 1, 0]);
  assert.ok(close(samples.points[5], [1.09375, 0.203125, 0], 1e-12));
  assert.ok(close(samples.points[6], [1.125, 0.5, 0], 1e-12));
  const uneven = sampleCentripetalCatmullRom([[0, 0, 0], [4, 0, 0], [4, 1, 0], [3, 1, 2]], 2);
  assert.ok(close(uneven.points[3], [4.116832673686526, 0.508426531102194, -0.06699868070638418], 1e-12));
  for (let i = 0; i + 1 < samples.points.length; i += 1) {
    const chord = samples.points[i + 1].map((value, k) => value - samples.points[i][k]);
    assert.ok(Math.abs(Math.hypot(...samples.tangents[i]) - 1) < 1e-12);
    assert.ok(dot(chord, samples.tangents[i]) > 0, `tangent ${i} points along the curve`);
  }
  assert.equal(sampleCentripetalCatmullRom(square, 4, true).points.length, 16);
});

test('frames stay constant on a straight path and close exactly on a planar circle', () => {
  const line = [[0, 0, 0], [0, 0, 1], [0, 0, 2], [0, 0, 3]];
  const tangents = line.map(() => [0, 0, 1]);
  const straight = rotationMinimizingFrames(line, tangents, {initialNormal: [1, 0, 0]});
  for (const normal of straight.normals) assert.deepEqual(normal, [1, 0, 0]);
  for (const binormal of straight.binormals) assert.deepEqual(binormal, [0, 1, 0]);
  const circle = Array.from({length: 24}, (_, k) => [Math.cos((2 * Math.PI * k) / 24), 0, Math.sin((2 * Math.PI * k) / 24)]);
  const samples = sampleCentripetalCatmullRom(circle, 8, true);
  const frames = rotationMinimizingFrames(samples.points, samples.tangents, {closed: true});
  assert.ok(Math.abs(frames.closingAngle) < 1e-9, `a planar loop has no twist (${frames.closingAngle})`);
});

test('a trefoil loop spreads its twist evenly and closes on its first frame', () => {
  const samples = sampleCentripetalCatmullRom(TREFOIL, 6, true);
  const raw = rotationMinimizingFrames(samples.points, samples.tangents, {closed: true, correctTwist: false});
  const fixed = rotationMinimizingFrames(samples.points, samples.tangents, {closed: true});
  const count = samples.points.length;
  assert.ok(Math.abs(raw.closingAngle) > 1, `the trefoil twists (${raw.closingAngle})`);
  assert.equal(fixed.closingAngle, raw.closingAngle);
  for (let i = 0; i < count; i += 1) {
    const turned = angleAbout(raw.normals[i], fixed.normals[i], samples.tangents[i]);
    assert.ok(Math.abs(turned - (raw.closingAngle * i) / count) < 1e-9, `frame ${i} turned by ${turned}`);
  }
  const closingStep = (frames) => {
    const carried = minimalRotation(frames.normals[count - 1], samples.tangents[count - 1], samples.tangents[0]);
    return Math.abs(angleAbout(carried, frames.normals[0], samples.tangents[0]));
  };
  assert.ok(closingStep(fixed) < 0.03, `the corrected loop closes (${closingStep(fixed)})`);
  assert.ok(closingStep(raw) > 1, 'known wrong: without the correction the loop misses its first frame');
});

test('straight, mitred and widening tubes are closed solids with the polygon volumes', () => {
  const straight = tubeRmfData([[0, 0, 0], [0, 0, 2]], {curve: 'polyline', radius: 0.5, radialSegments: 32});
  assert.deepEqual(solidProblems(straight), []);
  assert.ok(Math.abs(signedVolume(straight) - 1.560722576129026) < 1e-5);
  assert.equal(straight.positions.length / 3, 2 * 33 + 2 * 34);
  assert.equal(straight.pathLength, 2);
  const elbow = tubeRmfData([[0, 0, 0], [1, 0, 0], [1, 1, 0]], {curve: 'polyline', radius: 0.1, radialSegments: 16});
  assert.deepEqual(solidProblems(elbow), []);
  assert.ok(Math.abs(signedVolume(elbow) - 0.061229349178414376) < 1e-6);
  let reach = 0;
  for (let j = 0; j < 17; j += 1) reach = Math.max(reach, Math.hypot(...vertex(elbow.positions, 17 + j).map((v, i) => v - [1, 0, 0][i])));
  assert.ok(Math.abs(reach - 0.1 * Math.SQRT2) < 1e-6, `the corner ring reaches ${reach}`);
  const cone = tubeRmfData([[0, 0, 0], [0, 0, 1]], {curve: 'polyline', radii: [0.2, 0.4], radialSegments: 24});
  assert.deepEqual(solidProblems(cone), []);
  assert.ok(Math.abs(signedVolume(cone) - 0.2898773305148233) < 1e-5);
  assert.ok(Math.abs(cone.normals[2] - -0.19611613513818402) < 1e-6, 'the side normal tilts back by the radius slope');
});

test('closed spline tubes are watertight and their UVs wrap', () => {
  const knot = tubeRmfData(TREFOIL, {closed: true, radius: 0.08, samplesPerSegment: 4, radialSegments: 10});
  assert.deepEqual(solidProblems(knot), []);
  assert.ok(signedVolume(knot) > 0);
  assert.equal(knot.uvs[knot.uvs.length - 2], 1, 'the last ring has u = 1');
  const open = tubeRmfData([[0, 0, 0], [1, 0.5, 0], [2, 0, 0.5], [3, 1, 0]], {radius: 0.1});
  assert.deepEqual(solidProblems(open), []);
});

test('known wrong: a flipped triangle and a missing triangle are refused', () => {
  const mesh = tubeRmfData([[0, 0, 0], [0, 0, 1]], {curve: 'polyline', radialSegments: 6});
  const flipped = {...mesh, indices: Uint16Array.from(mesh.indices)};
  [flipped.indices[1], flipped.indices[2]] = [flipped.indices[2], flipped.indices[1]];
  assert.notDeepEqual(solidProblems(flipped), []);
  assert.notDeepEqual(solidProblems({...mesh, indices: mesh.indices.slice(3)}), []);
});

test('invalid paths and options are refused', () => {
  assert.throws(() => tubeRmfData([[0, 0, 0]]), RangeError);
  assert.throws(() => tubeRmfData([[0, 0, 0], [0, 0, 0]]), RangeError);
  assert.throws(() => tubeRmfData([[0, 0, 0], [1, 0, 0]], {curve: 'bezier'}), RangeError);
  assert.throws(() => tubeRmfData([[0, 0, 0], [1, 0, 0]], {curve: 'toString'}), RangeError, 'an inherited name is not a curve');
  assert.throws(() => tubeRmfData([[0, 0, 0], [1, 0, 0]], {radii: [1]}), RangeError);
  assert.throws(() => tubeRmfData([[0, 0, 0], [1, 0, 0]], {thickness: 1}), TypeError);
  assert.throws(() => tubeRmfData([[0, 0, 0], [1, 0, 0]], {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => tubeRmfData([[0, 0], [1, 0, 0]]), TypeError);
  assert.throws(() => rotationMinimizingFrames([[0, 0, 0], [1, 0, 0]], [[1, 0, 0], [1, 0, 0]], {initialNormal: [2, 0, 0]}), RangeError);
  assert.throws(() => sampleCentripetalCatmullRom([[0, 0, 0], [1, 0, 0]], 0), RangeError);
  assert.equal(TUBE_RMF_DEFAULTS.radialSegments, 12);
});

test('createTubeRmfGeometry fills a BufferGeometry', () => {
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
  const geometry = createTubeRmfGeometry(FakeThree, [[0, 0, 0], [0, 1, 0], [1, 2, 0]], {samplesPerSegment: 4, caps: false});
  assert.deepEqual(Object.keys(geometry.attributes), ['position', 'normal', 'uv']);
  assert.equal(geometry.attributes.position.array.length, 9 * 13 * 3);
  assert.equal(geometry.index.array.length, 8 * 12 * 6);
  assert.equal(geometry.bounds, 2);
});
