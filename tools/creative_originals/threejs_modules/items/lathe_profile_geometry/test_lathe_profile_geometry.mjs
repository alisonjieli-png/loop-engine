// Known answers for the lathe: profile volume and area against cylinder, cone and Pappus torus formulas; vertex and
// index counts with and without crease splitting; closed, outward meshes whose volume is the profile volume times the
// polygon factor (N / 2 pi) sin(2 pi / N); UVs by arc length; the three.js geometry with a minimal stand-in for THREE.
// Known-wrong controls: a cylinder-slice volume formula, a flipped and a missing triangle are refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LATHE_PROFILE_DEFAULTS, createLatheProfileGeometry, latheProfileArea, latheProfileData, latheProfileVolume,
} from './lathe_profile_geometry.mjs';

const CYLINDER = [[1, 0], [1, 2]];
const CONE = [[1, 0], [0, 2]];
const TORUS = Array.from({length: 24}, (_, k) => [1 + 0.3 * Math.cos((2 * Math.PI * k) / 24), 0.3 * Math.sin((2 * Math.PI * k) / 24)]);
const SPHERE = Array.from({length: 17}, (_, k) => {
  const angle = -Math.PI / 2 + (Math.PI * k) / 16;
  return [k === 0 || k === 16 ? 0 : Math.cos(angle), Math.sin(angle)];
});

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

// Closed, outward (each triangle agrees with its first vertex normal), unit normals; returns problems and the Euler
// characteristic of the welded mesh.
function solid(mesh) {
  const problems = [];
  const keys = new Map();
  const weld = [];
  for (let v = 0; v < mesh.positions.length / 3; v += 1) {
    const key = vertex(mesh.positions, v).map((value) => `${Math.round(value * 1e6)}`).join(',');
    if (!keys.has(key)) keys.set(key, keys.size);
    weld.push(keys.get(key));
  }
  const edges = new Map();
  let faces = 0;
  for (let t = 0; t < mesh.indices.length; t += 3) {
    const corner = [0, 1, 2].map((k) => weld[mesh.indices[t + k]]);
    if (new Set(corner).size < 3) continue;
    faces += 1;
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
  return {problems: problems.slice(0, 5), euler: keys.size - edges.size / 2 + faces};
}

function volumeProblems(volume) {
  const problems = [];
  const known = [[CYLINDER, false, 2 * Math.PI], [CONE, false, 2.0943951023931953], [TORUS, true, 1.7563046631189216]];
  for (const [profile, closed, expected] of known) {
    const actual = volume(profile, closed);
    if (Math.abs(actual - expected) > 1e-9) problems.push(`${JSON.stringify(profile.slice(0, 2))}: ${actual}`);
  }
  return problems;
}

test('latheProfileVolume and latheProfileArea match the cylinder, cone and Pappus torus', () => {
  assert.deepEqual(volumeProblems(latheProfileVolume), []);
  assert.ok(Math.abs(latheProfileArea(CYLINDER) - 4 * Math.PI) < 1e-12);
  assert.ok(Math.abs(latheProfileArea(CONE) - 7.024814731040727) < 1e-12, 'pi r l for the cone');
  assert.ok(latheProfileVolume([[1, 2], [1, 0]]) < 0, 'a profile drawn downward is inside out');
});

test('known wrong: a volume that treats each segment as a cylinder slice is refused', () => {
  const slices = (profile, closed) => {
    const points = closed ? [...profile, profile[0]] : profile;
    let volume = 0;
    for (let s = 0; s + 1 < points.length; s += 1) volume += Math.PI * points[s][0] ** 2 * (points[s + 1][1] - points[s][1]);
    return volume;
  };
  assert.notDeepEqual(volumeProblems(slices), []);
});

test('the capped cylinder has the expected counts, polygon volume and band area', () => {
  const mesh = latheProfileData(CYLINDER);
  assert.equal(mesh.positions.length / 3, 2 * 49 + 2 * 50);
  assert.equal(mesh.indices.length, 48 * 6 + 2 * 48 * 3);
  const {problems, euler} = solid(mesh);
  assert.deepEqual(problems, []);
  assert.equal(euler, 2);
  assert.ok(Math.abs(signedVolume(mesh) - 6.2652572265624755) < 1e-5, `volume ${signedVolume(mesh)}`);
  let band = 0;
  for (let t = 0; t < 48 * 6; t += 3) {
    const [a, b, c] = [0, 1, 2].map((k) => vertex(mesh.positions, mesh.indices[t + k]));
    const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
    const w = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
    band += Math.hypot(u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]) / 2;
  }
  assert.ok(Math.abs(band - 12.557400812187467) < 1e-5, `band area ${band}`);
});

test('crease splitting adds rings only where the profile turns past the angle', () => {
  const box = [[0, 0], [1, 0], [1, 1], [0, 1]];
  assert.equal(latheProfileData(box, {creaseAngle: 30}).positions.length / 3, 6 * 49);
  assert.equal(latheProfileData(box, {creaseAngle: 100}).positions.length / 3, 4 * 49);
  const sharp = latheProfileData(box, {creaseAngle: 30});
  assert.deepEqual(solid(sharp).problems, []);
  assert.ok(Math.abs(signedVolume(sharp) - Math.PI * (49 - 1) / (2 * Math.PI) * Math.sin((2 * Math.PI) / 48)) < 1e-5);
  const top = sharp.normals.slice(5 * 49 * 3, 5 * 49 * 3 + 3);
  assert.deepEqual(Array.from(top), [0, 1, 0], 'the ring on the top face points straight up');
});

test('closed and axis-to-axis profiles make watertight solids with the polygon volume', () => {
  const torus = latheProfileData(TORUS, {closed: true});
  const ring = solid(torus);
  assert.deepEqual(ring.problems, []);
  assert.equal(ring.euler, 0, 'a torus');
  assert.ok(Math.abs(signedVolume(torus) - 1.7512933241166126) < 1e-5);
  const ball = latheProfileData(SPHERE, {segments: 32});
  const sphere = solid(ball);
  assert.deepEqual(sphere.problems, []);
  assert.equal(sphere.euler, 2);
  const factor = (32 / (2 * Math.PI)) * Math.sin((2 * Math.PI) / 32);
  assert.ok(Math.abs(signedVolume(ball) - latheProfileVolume(SPHERE) * factor) < 1e-5);
  for (let k = 1; k < ball.uvs.length; k += 2) assert.ok(ball.uvs[k] >= 0 && ball.uvs[k] <= 1);
});

test('known wrong: a flipped triangle and a missing triangle are refused', () => {
  const mesh = latheProfileData(CYLINDER, {segments: 8});
  const flipped = {...mesh, indices: Uint16Array.from(mesh.indices)};
  [flipped.indices[1], flipped.indices[2]] = [flipped.indices[2], flipped.indices[1]];
  assert.notDeepEqual(solid(flipped).problems, []);
  assert.notDeepEqual(solid({...mesh, indices: mesh.indices.slice(3)}).problems, []);
});

test('invalid profiles and options are refused', () => {
  assert.throws(() => latheProfileData([[1, 0]]), RangeError);
  assert.throws(() => latheProfileData([[-1, 0], [1, 1]]), RangeError);
  assert.throws(() => latheProfileData([[1, 0], [1, 0], [1, 1]]), RangeError);
  assert.throws(() => latheProfileData([[1, 0], [1]]), TypeError);
  assert.throws(() => latheProfileData(CYLINDER, {segments: 2}), RangeError);
  assert.throws(() => latheProfileData(CYLINDER, {phiLength: 7}), RangeError);
  assert.throws(() => latheProfileData(CYLINDER, {smooth: true}), TypeError);
  assert.throws(() => latheProfileData(CYLINDER, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => latheProfileData(CYLINDER, {caps: 1}), TypeError);
  assert.equal(LATHE_PROFILE_DEFAULTS.segments, 48);
});

test('createLatheProfileGeometry fills a BufferGeometry', () => {
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
  const geometry = createLatheProfileGeometry(FakeThree, CONE, {segments: 12, caps: false});
  assert.deepEqual(Object.keys(geometry.attributes), ['position', 'normal', 'uv']);
  assert.equal(geometry.attributes.position.array.length, 2 * 13 * 3);
  assert.equal(geometry.index.array.length, 12 * 3);
  assert.equal(geometry.bounds, 2);
});
