// Known answers for the BVH raycaster: closest hits equal a brute-force reference (a plane hit plus a signed-area
// inside test, a different method from the module's) on hundreds of random rays over a triangle soup and a sphere
// mesh, the hierarchy covers every triangle once with bounds that contain their contents, any-hit agrees with
// closest-hit, faces are culled by side, and hits on a unit sphere sit at the analytic distance. A hierarchy with
// one corrupted node box is the known-wrong control the brute-force comparison must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  BVH_DEFAULTS, RAYCAST_DEFAULTS, buildTriangleBVH, bvhFromGeometry, describeBVH, raycastAnyBVH, raycastBVH,
} from './triangle_bvh_raycast.mjs';

function random(seed) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function soup(count, seed) {
  const next = random(seed);
  const positions = new Float32Array(count * 9);
  for (let t = 0; t < count; t += 1) {
    const centre = [next() * 10 - 5, next() * 10 - 5, next() * 10 - 5];
    for (let k = 0; k < 9; k += 1) positions[t * 9 + k] = centre[k % 3] + (next() - 0.5) * 1.6;
  }
  return positions;
}

function sphereMesh(rows, columns) {
  const positions = [];
  const indices = [];
  for (let r = 0; r <= rows; r += 1) {
    const polar = (Math.PI * r) / rows;
    for (let c = 0; c <= columns; c += 1) {
      const azimuth = (2 * Math.PI * c) / columns;
      positions.push(Math.sin(polar) * Math.sin(azimuth), Math.cos(polar), Math.sin(polar) * Math.cos(azimuth));
    }
  }
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < columns; c += 1) {
      const a = r * (columns + 1) + c;
      const b = a + columns + 1;
      indices.push(a, b, a + 1, a + 1, b, b + 1);
    }
  }
  return {positions: Float32Array.from(positions), indices: Uint32Array.from(indices)};
}

const sub = (p, q) => [p[0] - q[0], p[1] - q[1], p[2] - q[2]];
const cross = (p, q) => [p[1] * q[2] - p[2] * q[1], p[2] * q[0] - p[0] * q[2], p[0] * q[1] - p[1] * q[0]];
const dot = (p, q) => p[0] * q[0] + p[1] * q[1] + p[2] * q[2];

// Brute force by a different method: the plane hit, then the signs of the three sub-triangle areas.
function bruteForce(positions, indices, origin, direction) {
  const length = Math.hypot(...direction);
  const unit = direction.map((value) => value / length);
  const count = indices === null ? positions.length / 9 : indices.length / 3;
  const corner = (t, k) => {
    const v = indices === null ? t * 3 + k : indices[t * 3 + k];
    return [positions[v * 3], positions[v * 3 + 1], positions[v * 3 + 2]];
  };
  let best = null;
  for (let t = 0; t < count; t += 1) {
    const [a, b, c] = [corner(t, 0), corner(t, 1), corner(t, 2)];
    const normal = cross(sub(b, a), sub(c, a));
    const facing = dot(normal, unit);
    if (Math.abs(facing) < 1e-12) continue;
    const distance = dot(normal, sub(a, origin)) / facing;
    if (distance < 0) continue;
    const point = origin.map((value, axis) => value + unit[axis] * distance);
    const inside = [[b, c], [c, a], [a, b]].every(([p, q]) => dot(normal, cross(sub(q, p), sub(point, p))) >= 0);
    if (inside && (best === null || distance < best.distance)) best = {distance, triangle: t};
  }
  return best;
}

// Rays where the hierarchy and the brute force disagree (a different triangle at the same distance is allowed).
function mismatches(bvh, positions, indices, rays) {
  const wrong = [];
  for (const [origin, direction] of rays) {
    const ours = raycastBVH(bvh, origin, direction);
    const reference = bruteForce(positions, indices, origin, direction);
    if ((ours === null) !== (reference === null)) wrong.push({origin, ours, reference});
    else if (ours !== null && Math.abs(ours.distance - reference.distance) > 1e-6 * Math.max(1, reference.distance)) {
      wrong.push({origin, ours, reference});
    }
  }
  return wrong;
}

function rays(count, seed, spread) {
  const next = random(seed);
  return Array.from({length: count}, () => [
    [next() * spread * 2 - spread, next() * spread * 2 - spread, next() * spread * 2 - spread],
    [next() * 2 - 1, next() * 2 - 1, next() * 2 - 1],
  ]);
}

test('closest hits equal brute force on a triangle soup and on a sphere mesh', () => {
  const positions = soup(600, 7);
  const bvh = buildTriangleBVH(positions);
  const cast = rays(500, 3, 8);
  assert.deepEqual(mismatches(bvh, positions, null, cast).slice(0, 3), []);
  const hits = cast.filter(([origin, direction]) => raycastBVH(bvh, origin, direction) !== null).length;
  assert.ok(hits > 60, `${hits} of 500 rays hit something, so the comparison is not empty`);
  const sphere = sphereMesh(24, 48);
  const sphereBVH = buildTriangleBVH(sphere.positions, sphere.indices, {maxLeafTriangles: 2});
  assert.deepEqual(mismatches(sphereBVH, sphere.positions, sphere.indices, rays(300, 9, 3)).slice(0, 3), []);
});

test('the hierarchy covers every triangle once and every box holds its contents', () => {
  const positions = soup(400, 11);
  const bvh = buildTriangleBVH(positions, null, {maxLeafTriangles: 3});
  const seen = new Uint8Array(400);
  const stack = [0];
  while (stack.length > 0) {
    const node = stack.pop();
    const box = bvh.nodeBounds.subarray(node * 6, node * 6 + 6);
    const contains = (other) => [0, 1, 2].every((axis) => box[axis] <= other[axis] + 1e-12 && box[3 + axis] >= other[3 + axis] - 1e-12);
    if (bvh.nodeCounts[node] > 0) {
      for (let k = bvh.nodeOffsets[node]; k < bvh.nodeOffsets[node] + bvh.nodeCounts[node]; k += 1) {
        const t = bvh.order[k];
        seen[t] += 1;
        const xs = [0, 3, 6].map((o) => positions[t * 9 + o]);
        const ys = [1, 4, 7].map((o) => positions[t * 9 + o]);
        const zs = [2, 5, 8].map((o) => positions[t * 9 + o]);
        assert.ok(contains([Math.min(...xs), Math.min(...ys), Math.min(...zs), Math.max(...xs), Math.max(...ys), Math.max(...zs)]));
      }
    } else {
      const left = bvh.nodeOffsets[node];
      assert.ok(contains(bvh.nodeBounds.subarray(left * 6, left * 6 + 6)));
      assert.ok(contains(bvh.nodeBounds.subarray((left + 1) * 6, (left + 1) * 6 + 6)));
      stack.push(left, left + 1);
    }
  }
  assert.ok(seen.every((value) => value === 1), 'each triangle in exactly one leaf');
  const summary = describeBVH(bvh);
  assert.equal(summary.triangles, 400);
  assert.ok(summary.largestLeaf <= 3 && summary.nodes === 2 * summary.leaves - 1 && summary.maximumDepth < 40);
});

test('any-hit agrees with closest-hit, and far limits are honoured', () => {
  const positions = soup(300, 21);
  const bvh = buildTriangleBVH(positions);
  for (const [origin, direction] of rays(300, 5, 8)) {
    const closest = raycastBVH(bvh, origin, direction, {far: 4});
    assert.equal(raycastAnyBVH(bvh, origin, direction, {far: 4}), closest !== null);
    if (closest !== null) assert.ok(closest.distance <= 4);
  }
});

test('a unit sphere is hit at the analytic distance, with consistent points and barycentrics', () => {
  const sphere = sphereMesh(64, 128);
  const bvh = buildTriangleBVH(sphere.positions, sphere.indices);
  const hit = raycastBVH(bvh, [0, 0, 5], [0, 0, -2]);
  // The tessellated sphere is inscribed, so the hit lies at most 1 - cos(pi / 64) inside the true sphere.
  assert.ok(hit.distance >= 4 && hit.distance <= 4 + (1 - Math.cos(Math.PI / 64)) + 1e-9, `${hit.distance}`);
  const [w0, w1, w2] = hit.barycentric;
  assert.ok(Math.abs(w0 + w1 + w2 - 1) < 1e-12 && Math.min(w0, w1, w2) >= 0);
  assert.ok(Math.abs(hit.point[2] - (5 - hit.distance)) < 1e-12);
  const tri = sphere.indices.subarray(hit.triangle * 3, hit.triangle * 3 + 3);
  for (let axis = 0; axis < 3; axis += 1) {
    const blended = w0 * sphere.positions[tri[0] * 3 + axis] + w1 * sphere.positions[tri[1] * 3 + axis]
      + w2 * sphere.positions[tri[2] * 3 + axis];
    assert.ok(Math.abs(blended - hit.point[axis]) < 1e-6);
  }
  assert.equal(raycastBVH(bvh, [0, 0, 5], [0, 0, 1]), null, 'a ray pointing away misses');
});

test('side culling: front faces are counter-clockwise', () => {
  const one = buildTriangleBVH(Float32Array.from([0, 0, 0, 1, 0, 0, 0, 1, 0]));
  assert.notEqual(raycastBVH(one, [0.2, 0.2, 1], [0, 0, -1], {side: 'front'}), null);
  assert.equal(raycastBVH(one, [0.2, 0.2, -1], [0, 0, 1], {side: 'front'}), null);
  assert.notEqual(raycastBVH(one, [0.2, 0.2, -1], [0, 0, 1], {side: 'back'}), null);
  assert.notEqual(raycastBVH(one, [0.2, 0.2, -1], [0, 0, 1]), null, 'double-sided by default');
  assert.equal(RAYCAST_DEFAULTS.side, 'double');
  assert.equal(BVH_DEFAULTS.bins, 12);
});

test('bvhFromGeometry reads a BufferGeometry-shaped object', () => {
  const sphere = sphereMesh(8, 16);
  const geometry = {attributes: {position: {array: sphere.positions, itemSize: 3, count: sphere.positions.length / 3}},
    index: {array: sphere.indices}};
  const bvh = bvhFromGeometry(geometry);
  assert.equal(bvh.triangleCount, sphere.indices.length / 3);
  assert.notEqual(raycastBVH(bvh, [0, 3, 0], [0, -1, 0]), null);
});

test('known wrong: a hierarchy with a corrupted node box is refused by the brute-force comparison', () => {
  const positions = soup(500, 31);
  const bvh = buildTriangleBVH(positions);
  const broken = {...bvh, nodeBounds: Float64Array.from(bvh.nodeBounds)};
  const leaf = Array.from(bvh.nodeCounts).findIndex((count, node) => count > 0 && node > 0);
  broken.nodeBounds.set([1e9, 1e9, 1e9, 1e9 + 1, 1e9 + 1, 1e9 + 1], leaf * 6);
  const cast = [];
  for (let k = bvh.nodeOffsets[leaf]; k < bvh.nodeOffsets[leaf] + bvh.nodeCounts[leaf]; k += 1) {
    const t = bvh.order[k];
    const centre = [0, 1, 2].map((axis) => (positions[t * 9 + axis] + positions[t * 9 + 3 + axis] + positions[t * 9 + 6 + axis]) / 3);
    cast.push([[centre[0], centre[1], 50], [0, 0, -1]], [[centre[0], 50, centre[2]], [0, -1, 0]]);
  }
  assert.deepEqual(mismatches(bvh, positions, null, cast), []);
  assert.notDeepEqual(mismatches(broken, positions, null, cast), []);
});

test('known wrong: malformed meshes, rays and options are refused', () => {
  assert.throws(() => buildTriangleBVH(Float32Array.from([0, 0, 0, 1])), RangeError);
  assert.throws(() => buildTriangleBVH(Float32Array.from([0, 0, 0, 1, 0, 0, 0, 1, 0]), Uint16Array.from([0, 1, 5])), RangeError);
  assert.throws(() => buildTriangleBVH(Float32Array.from([0, 0, 0, 1, 0, 0, 0, 1, 0]), null, {leafSize: 2}), TypeError);
  assert.throws(() => buildTriangleBVH(Float32Array.from([0, 0, 0, 1, 0, 0, 0, 1, 0]), null, {toString: 1}), TypeError);
  const one = buildTriangleBVH(Float32Array.from([0, 0, 0, 1, 0, 0, 0, 1, 0]));
  assert.throws(() => raycastBVH(one, [0, 0, 1], [0, 0, 0]), RangeError);
  assert.throws(() => raycastBVH(one, [0, 0, 1], [0, 0, -1], {side: 'both'}), RangeError);
  assert.throws(() => raycastBVH(one, [0, 0, 1], [0, 0, -1], {near: 2, far: 1}), RangeError);
});
