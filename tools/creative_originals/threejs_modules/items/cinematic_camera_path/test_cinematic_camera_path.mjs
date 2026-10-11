// Known answers for the cinematic camera path: Catmull-Rom points (values from an independent Python port), the look
// rotation of a -Z camera, slerp and the easings; then the path passes through every keyframe, moves at near-constant
// speed, keeps unit quaternions and looks at its targets. Known-wrong control: a sampler that steps the spline
// parameter instead of the arc length is refused by the constant-speed check.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CINEMATIC_PATH_DEFAULTS, CameraPath, catmullRomPoint, easeTime, lookRotation, slerpQuaternion,
} from './cinematic_camera_path.mjs';

function close(actual, expected, tolerance, label) {
  assert.equal(actual.length, expected.length, label);
  actual.forEach((value, index) => assert.ok(Math.abs(value - expected[index]) <= tolerance,
    `${label}: [${actual}] against [${expected}]`));
}

function rotate(q, v) {
  const [x, y, z, w] = q;
  const t = [2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])];
  return [v[0] + w * t[0] + y * t[2] - z * t[1], v[1] + w * t[1] + z * t[0] - x * t[2], v[2] + w * t[2] + x * t[1] - y * t[0]];
}

// Problems with a sampler (t -> position): the ratio of the largest to the smallest step between 400 equal time steps.
function speedProblems(sample) {
  const steps = [];
  let previous = sample(0);
  for (let index = 1; index <= 400; index += 1) {
    const point = sample(index / 400);
    steps.push(Math.hypot(point[0] - previous[0], point[1] - previous[1], point[2] - previous[2]));
    previous = point;
  }
  const ratio = Math.max(...steps) / Math.min(...steps);
  return ratio < 1.02 ? [] : [`step ratio ${ratio}`];
}

const UNEVEN = [
  {position: [0, 1, 6], target: [0, 1, 0]},
  {position: [4, 1.5, 4], target: [0, 1.2, 0]},
  {position: [4.4, 2, -0.5], target: [0, 1, 0]},
  {position: [0.5, 3, -5], target: [0, 0.8, 0]},
  {position: [-5, 2, -2], target: [0, 1, 0]},
];

test('catmullRomPoint: endpoints, collinear points and an uneven segment', () => {
  close(catmullRomPoint([0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0], 0.25), [1.25, 0, 0], 1e-12, 'collinear');
  close(catmullRomPoint([0, 0, 0], [1, 0, 0], [1, 3, 0], [1, 3.1, 0], 0.3),
    [1.1614172030689374, 0.7510588835044707, 0], 1e-12, 'uneven, from the Python port');
  close(catmullRomPoint([0, 0, 0], [1, 0, 0], [1, 3, 0], [1, 3.1, 0], 0), [1, 0, 0], 1e-12, 'starts at p1');
  close(catmullRomPoint([0, 0, 0], [1, 0, 0], [1, 3, 0], [1, 3.1, 0], 1), [1, 3, 0], 1e-12, 'ends at p2');
  assert.throws(() => catmullRomPoint([0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0], 1.5), RangeError);
});

test('lookRotation, slerpQuaternion and easeTime known answers', () => {
  close(lookRotation([0, 0, 5], [0, 0, 0]), [0, 0, 0, 1], 1e-12, 'looking down -Z is the identity');
  close(lookRotation([5, 0, 0], [0, 0, 0]), [0, Math.SQRT1_2, 0, Math.SQRT1_2], 1e-12, 'a quarter turn about Y');
  const straightDown = lookRotation([0, 5, 0], [0, 0, 0]);
  close(rotate(straightDown, [0, 0, -1]), [0, -1, 0], 1e-12, 'a view parallel to up still points at the target');
  close(slerpQuaternion([0, 0, 0, 1], [0, Math.SQRT1_2, 0, Math.SQRT1_2], 0.5), [0, 0.3826834323650898, 0, 0.9238795325112867],
    1e-12, 'half of a quarter turn');
  close(slerpQuaternion([0, 0, 0, 1], [0, 0, 0, -1], 0.5), [0, 0, 0, 1], 1e-12, 'the shorter arc');
  assert.equal(easeTime(0.25, 'smoothstep'), 0.15625);
  assert.equal(easeTime(0.5, 'smootherstep'), 0.5);
  assert.equal(easeTime(2, 'linear'), 1);
  assert.throws(() => easeTime(0.5, 'bounce'), TypeError);
  assert.throws(() => easeTime(0.5, 'toString'), TypeError, 'an inherited name is not an easing');
});

test('the path passes through every keyframe and moves at near-constant speed', () => {
  const path = new CameraPath(UNEVEN, {easing: 'linear'});
  const fractions = path.keyframeFractions();
  assert.equal(fractions.length, UNEVEN.length);
  fractions.forEach((fraction, index) => close(path.sampleAt(fraction).position, UNEVEN[index].position, 1e-9, `keyframe ${index}`));
  assert.deepEqual(speedProblems((t) => path.sampleAt(t).position), []);
  for (let index = 0; index <= 100; index += 1) {
    const {position, quaternion} = path.sampleAt(index / 100);
    assert.ok(Math.abs(Math.hypot(...quaternion) - 1) < 1e-12, 'unit quaternion');
    if (index === 0 || index === 100) {
      const forward = rotate(quaternion, [0, 0, -1]);
      const target = UNEVEN[index === 0 ? 0 : UNEVEN.length - 1].target;
      const toward = [target[0] - position[0], target[1] - position[1], target[2] - position[2]];
      const cosine = (forward[0] * toward[0] + forward[1] * toward[1] + forward[2] * toward[2]) / Math.hypot(...toward);
      assert.ok(cosine > 1 - 1e-9, 'the camera looks at the keyframe target');
    }
  }
});

test('known wrong: stepping the spline parameter instead of the arc length is refused', () => {
  const path = new CameraPath(UNEVEN, {easing: 'linear'});
  const byParameter = (t) => {
    const position = Math.min(t * path.segments, path.segments - 1e-9);
    const segment = Math.floor(position);
    return path.pointOnSegment(segment, position - segment);
  };
  assert.notDeepEqual(speedProblems(byParameter), []);
});

test('closed loops, quaternion keyframes and tangent orientation', () => {
  const ring = [[3, 1, 0], [0, 1, 3], [-3, 1, 0], [0, 1, -3]].map((position) => ({position}));
  const loop = new CameraPath(ring, {closed: true, easing: 'linear'});
  assert.equal(loop.segments, 4);
  close(loop.sampleAt(1).position, ring[0].position, 1e-9, 'a closed path ends where it starts');
  // 64 chords a segment, summed by an independent Python port: 17.8347140853541, more than the square through the
  // keyframes (any curve through them in order is at least that long) and less than the circle they lie on.
  assert.ok(Math.abs(loop.length - 17.8347140853541) < 1e-9, `arc-length table total ${loop.length}`);
  assert.ok(loop.length > 4 * 3 * Math.SQRT2 && loop.length < 2 * Math.PI * 3);
  const turning = new CameraPath([{position: [0, 0, 0], quaternion: [0, 0, 0, 1]},
    {position: [1, 0, 0], quaternion: [0, 1, 0, 0]}], {easing: 'linear'});
  close(turning.sampleAt(0.5).quaternion, [0, Math.SQRT1_2, 0, Math.SQRT1_2], 1e-9, 'half way through a half turn');
  const pose = {position: {set(...value) { this.value = value; }}, quaternion: {set(...value) { this.value = value; }}};
  loop.applyTo(pose, 0.25);
  close(pose.position.value, loop.sampleAt(0.25).position, 0, 'applyTo uses sampleAt');
  const ahead = rotate(pose.quaternion.value, [0, 0, -1]);
  const next = loop.sampleAt(0.26).position;
  const step = [next[0] - pose.position.value[0], next[1] - pose.position.value[1], next[2] - pose.position.value[2]];
  assert.ok((ahead[0] * step[0] + ahead[1] * step[1] + ahead[2] * step[2]) / Math.hypot(...step) > 0.99, 'looks along travel');
  assert.equal(CINEMATIC_PATH_DEFAULTS.alpha, 0.5);
});

test('invalid keyframes and options are refused', () => {
  assert.throws(() => new CameraPath([{position: [0, 0, 0]}]), TypeError);
  assert.throws(() => new CameraPath([{position: [0, 0, 0], target: [1, 0, 0]}, {position: [1, 1, 1]}]), TypeError);
  assert.throws(() => new CameraPath([{position: [0, 0, 0]}, {position: [0, 0, 0]}]), RangeError);
  assert.throws(() => new CameraPath(UNEVEN, {easing: 'elastic'}), TypeError);
  assert.throws(() => new CameraPath(UNEVEN, {sample: 3}), TypeError);
  assert.throws(() => new CameraPath(UNEVEN, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => lookRotation([1, 1, 1], [1, 1, 1]), RangeError);
});
