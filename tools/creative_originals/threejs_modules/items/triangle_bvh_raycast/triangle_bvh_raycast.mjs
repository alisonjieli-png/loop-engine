// A bounding volume hierarchy over a triangle mesh for fast raycasts in three.js scenes: built with binned surface
// area heuristic splits into flat typed arrays, traversed nearest child first for the closest hit, with an early-out
// any-hit query for shadow and line-of-sight rays. Triangles are tested with the Moller-Trumbore algorithm. Original
// Baltor implementation; it reads typed arrays (or a BufferGeometry's arrays) and needs no three.js.

/** Default options of buildTriangleBVH. */
export const BVH_DEFAULTS = Object.freeze({maxLeafTriangles: 4, bins: 12});

/** Default options of raycastBVH and raycastAnyBVH. side is 'double', 'front' (counter-clockwise) or 'back'. */
export const RAYCAST_DEFAULTS = Object.freeze({near: 0, far: Infinity, side: 'double'});

const SIDES = Object.freeze(['double', 'front', 'back']);
const DETERMINANT_EPSILON = 1e-12;
const TRAVERSAL_COST = 1;
const MAXIMUM_LEAF_SIZE = 64;

function strict(options, defaults, name) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(defaults, key)) throw new TypeError(`unknown ${name} option ${key}`);
  }
  return {...defaults, ...options};
}

function surface(bounds, offset) {
  const dx = bounds[offset + 3] - bounds[offset];
  const dy = bounds[offset + 4] - bounds[offset + 1];
  const dz = bounds[offset + 5] - bounds[offset + 2];
  return dx < 0 ? 0 : 2 * (dx * dy + dy * dz + dz * dx);
}

function emptyBox(box, offset) {
  box[offset] = box[offset + 1] = box[offset + 2] = Infinity;
  box[offset + 3] = box[offset + 4] = box[offset + 5] = -Infinity;
}

function growBox(box, offset, other, otherOffset) {
  for (let axis = 0; axis < 3; axis += 1) {
    box[offset + axis] = Math.min(box[offset + axis], other[otherOffset + axis]);
    box[offset + 3 + axis] = Math.max(box[offset + 3 + axis], other[otherOffset + 3 + axis]);
  }
}

/**
 * Build the hierarchy: {positions, indices, order, nodeBounds, nodeOffsets, nodeCounts, nodeCount, triangleCount}.
 * Node 0 is the root; an inner node has nodeCounts 0 and its children at nodeOffsets and nodeOffsets + 1; a leaf
 * holds nodeCounts triangles order[nodeOffsets ...]. positions holds x, y, z triples; indices may be null for a
 * non-indexed mesh. The arrays are referenced, not copied, so edit the mesh only by building again.
 */
export function buildTriangleBVH(positions, indices = null, options = {}) {
  const settings = strict(options, BVH_DEFAULTS, 'BVH');
  if (!Number.isInteger(settings.maxLeafTriangles) || settings.maxLeafTriangles < 1 || settings.maxLeafTriangles > 32) {
    throw new RangeError('maxLeafTriangles must be an integer from 1 to 32');
  }
  if (!Number.isInteger(settings.bins) || settings.bins < 2 || settings.bins > 64) {
    throw new RangeError('bins must be an integer from 2 to 64');
  }
  if (!(positions && positions.length % 3 === 0 && positions.length > 0)) {
    throw new RangeError('positions must hold x, y, z triples');
  }
  const vertexCount = positions.length / 3;
  const triangleCount = indices === null ? vertexCount / 3 : indices.length / 3;
  if (!Number.isInteger(triangleCount) || triangleCount < 1) throw new RangeError('the mesh must hold whole triangles');
  if (indices !== null) {
    for (let k = 0; k < indices.length; k += 1) {
      if (!(Number.isInteger(indices[k]) && indices[k] >= 0 && indices[k] < vertexCount)) {
        throw new RangeError(`index ${indices[k]} at ${k} is outside the ${vertexCount} vertices`);
      }
    }
  }
  const vertex = (triangle, corner) => (indices === null ? triangle * 3 + corner : indices[triangle * 3 + corner]);
  const boxes = new Float64Array(triangleCount * 6);
  const centroids = new Float64Array(triangleCount * 3);
  for (let t = 0; t < triangleCount; t += 1) {
    emptyBox(boxes, t * 6);
    for (let corner = 0; corner < 3; corner += 1) {
      const v = vertex(t, corner) * 3;
      for (let axis = 0; axis < 3; axis += 1) {
        const value = positions[v + axis];
        if (!Number.isFinite(value)) throw new RangeError(`vertex ${v / 3} is not finite`);
        boxes[t * 6 + axis] = Math.min(boxes[t * 6 + axis], value);
        boxes[t * 6 + 3 + axis] = Math.max(boxes[t * 6 + 3 + axis], value);
      }
    }
    for (let axis = 0; axis < 3; axis += 1) centroids[t * 3 + axis] = (boxes[t * 6 + axis] + boxes[t * 6 + 3 + axis]) / 2;
  }
  const order = new Uint32Array(triangleCount);
  for (let t = 0; t < triangleCount; t += 1) order[t] = t;
  const capacity = 2 * triangleCount - 1;
  const nodeBounds = new Float64Array(capacity * 6);
  const nodeOffsets = new Uint32Array(capacity);
  const nodeCounts = new Uint32Array(capacity);
  const bins = settings.bins;
  const binBounds = new Float64Array(bins * 6);
  const binCounts = new Uint32Array(bins);
  const rightAreas = new Float64Array(bins);
  const sweep = new Float64Array(6);
  let nodeCount = 1;
  const work = [[0, 0, triangleCount]];
  while (work.length > 0) {
    const [node, start, end] = work.pop();
    const count = end - start;
    emptyBox(nodeBounds, node * 6);
    const centroidBox = new Float64Array(6);
    emptyBox(centroidBox, 0);
    for (let k = start; k < end; k += 1) {
      growBox(nodeBounds, node * 6, boxes, order[k] * 6);
      for (let axis = 0; axis < 3; axis += 1) {
        const value = centroids[order[k] * 3 + axis];
        centroidBox[axis] = Math.min(centroidBox[axis], value);
        centroidBox[3 + axis] = Math.max(centroidBox[3 + axis], value);
      }
    }
    let bestAxis = -1;
    let bestBin = -1;
    let bestCost = Infinity;
    if (count > settings.maxLeafTriangles) {
      const parentArea = Math.max(surface(nodeBounds, node * 6), 1e-300);
      for (let axis = 0; axis < 3; axis += 1) {
        const low = centroidBox[axis];
        const extent = centroidBox[3 + axis] - low;
        if (!(extent > 1e-12)) continue;
        binCounts.fill(0);
        for (let b = 0; b < bins; b += 1) emptyBox(binBounds, b * 6);
        for (let k = start; k < end; k += 1) {
          const b = Math.min(bins - 1, Math.floor(((centroids[order[k] * 3 + axis] - low) / extent) * bins));
          binCounts[b] += 1;
          growBox(binBounds, b * 6, boxes, order[k] * 6);
        }
        emptyBox(sweep, 0);
        let rightCount = 0;
        for (let b = bins - 1; b > 0; b -= 1) {
          growBox(sweep, 0, binBounds, b * 6);
          rightCount += binCounts[b];
          rightAreas[b] = surface(sweep, 0) * rightCount;
        }
        emptyBox(sweep, 0);
        let leftCount = 0;
        for (let b = 0; b < bins - 1; b += 1) {
          growBox(sweep, 0, binBounds, b * 6);
          leftCount += binCounts[b];
          if (leftCount === 0 || leftCount === count) continue;
          const cost = TRAVERSAL_COST + (surface(sweep, 0) * leftCount + rightAreas[b + 1]) / parentArea;
          if (cost < bestCost) {
            bestCost = cost;
            bestAxis = axis;
            bestBin = b;
          }
        }
      }
    }
    const splitWorthIt = bestAxis >= 0 && (bestCost < count || count > MAXIMUM_LEAF_SIZE);
    if (!splitWorthIt) {
      nodeOffsets[node] = start;
      nodeCounts[node] = count;
      continue;
    }
    const low = centroidBox[bestAxis];
    const extent = centroidBox[3 + bestAxis] - low;
    let middle = start;
    for (let k = start; k < end; k += 1) {
      const b = Math.min(bins - 1, Math.floor(((centroids[order[k] * 3 + bestAxis] - low) / extent) * bins));
      if (b <= bestBin) {
        const swap = order[k];
        order[k] = order[middle];
        order[middle] = swap;
        middle += 1;
      }
    }
    const left = nodeCount;
    nodeCount += 2;
    nodeOffsets[node] = left;
    nodeCounts[node] = 0;
    work.push([left + 1, middle, end], [left, start, middle]);
  }
  return {
    positions, indices, order, triangleCount,
    nodeBounds: nodeBounds.slice(0, nodeCount * 6),
    nodeOffsets: nodeOffsets.slice(0, nodeCount),
    nodeCounts: nodeCounts.slice(0, nodeCount),
    nodeCount,
  };
}

function attributeArray(attribute) {
  if (attribute.isInterleavedBufferAttribute !== true && attribute.itemSize === 3) return attribute.array;
  const copy = new Float32Array(attribute.count * 3);
  for (let index = 0; index < attribute.count; index += 1) {
    copy[index * 3] = attribute.getX(index);
    copy[index * 3 + 1] = attribute.getY(index);
    copy[index * 3 + 2] = attribute.getZ(index);
  }
  return copy;
}

/** buildTriangleBVH on a three.js BufferGeometry's position attribute and index (in the geometry's local space). */
export function bvhFromGeometry(geometry, options = {}) {
  const position = geometry && geometry.attributes && geometry.attributes.position;
  if (!position) throw new TypeError('the geometry has no position attribute');
  return buildTriangleBVH(attributeArray(position), geometry.index ? geometry.index.array : null, options);
}

function prepareRay(origin, direction, options) {
  const settings = strict(options, RAYCAST_DEFAULTS, 'raycast');
  if (!SIDES.includes(settings.side)) throw new RangeError(`side is one of ${SIDES.join(', ')}`);
  if (!(settings.near >= 0 && settings.far >= settings.near)) throw new RangeError('need 0 <= near <= far');
  const length = Math.hypot(direction[0], direction[1], direction[2]);
  if (!(length > 0 && Number.isFinite(length))) throw new RangeError('direction must be a non-zero finite vector');
  if (!(origin.length === 3 && Array.prototype.every.call(origin, Number.isFinite))) {
    throw new RangeError('origin must be three finite numbers');
  }
  const unit = [direction[0] / length, direction[1] / length, direction[2] / length];
  // A zero component gets a huge finite inverse with its sign, which keeps the slab test free of 0 * Infinity.
  const inverse = unit.map((value) => 1 / (Math.abs(value) > 1e-300 ? value : (Object.is(value, -0) ? -1e-300 : 1e-300)));
  return {settings, unit, inverse};
}

function slab(bounds, node, origin, inverse, near, far) {
  let entry = near;
  let exit = far;
  for (let axis = 0; axis < 3; axis += 1) {
    const first = (bounds[node * 6 + axis] - origin[axis]) * inverse[axis];
    const second = (bounds[node * 6 + 3 + axis] - origin[axis]) * inverse[axis];
    entry = Math.max(entry, Math.min(first, second));
    exit = Math.min(exit, Math.max(first, second));
  }
  return entry <= exit ? entry : Infinity;
}

// Moller-Trumbore. Returns t (Infinity on a miss) and writes u, v into the hit scratch.
function intersectTriangle(bvh, triangle, origin, unit, side, near, far, scratch) {
  const {positions, indices} = bvh;
  const a = (indices === null ? triangle * 3 : indices[triangle * 3]) * 3;
  const b = (indices === null ? triangle * 3 + 1 : indices[triangle * 3 + 1]) * 3;
  const c = (indices === null ? triangle * 3 + 2 : indices[triangle * 3 + 2]) * 3;
  const e1x = positions[b] - positions[a];
  const e1y = positions[b + 1] - positions[a + 1];
  const e1z = positions[b + 2] - positions[a + 2];
  const e2x = positions[c] - positions[a];
  const e2y = positions[c + 1] - positions[a + 1];
  const e2z = positions[c + 2] - positions[a + 2];
  const px = unit[1] * e2z - unit[2] * e2y;
  const py = unit[2] * e2x - unit[0] * e2z;
  const pz = unit[0] * e2y - unit[1] * e2x;
  const determinant = e1x * px + e1y * py + e1z * pz;
  // determinant > 0 means the ray meets the counter-clockwise (front) face.
  if (side === 'front' ? determinant <= DETERMINANT_EPSILON
    : side === 'back' ? determinant >= -DETERMINANT_EPSILON : Math.abs(determinant) <= DETERMINANT_EPSILON) {
    return Infinity;
  }
  const inverse = 1 / determinant;
  const sx = origin[0] - positions[a];
  const sy = origin[1] - positions[a + 1];
  const sz = origin[2] - positions[a + 2];
  const u = (sx * px + sy * py + sz * pz) * inverse;
  if (u < 0 || u > 1) return Infinity;
  const qx = sy * e1z - sz * e1y;
  const qy = sz * e1x - sx * e1z;
  const qz = sx * e1y - sy * e1x;
  const v = (unit[0] * qx + unit[1] * qy + unit[2] * qz) * inverse;
  if (v < 0 || u + v > 1) return Infinity;
  const t = (e2x * qx + e2y * qy + e2z * qz) * inverse;
  if (t < near || t > far) return Infinity;
  scratch[0] = u;
  scratch[1] = v;
  return t;
}

function traverse(bvh, origin, direction, options, anyHit) {
  const {settings, unit, inverse} = prepareRay(origin, direction, options);
  const {nodeBounds, nodeOffsets, nodeCounts, order} = bvh;
  const scratch = [0, 0];
  let best = settings.far;
  let hit = null;
  if (slab(nodeBounds, 0, origin, inverse, settings.near, best) === Infinity) return null;
  const stack = [0];
  while (stack.length > 0) {
    const node = stack.pop();
    if (slab(nodeBounds, node, origin, inverse, settings.near, best) === Infinity) continue;
    if (nodeCounts[node] > 0) {
      const first = nodeOffsets[node];
      for (let k = first; k < first + nodeCounts[node]; k += 1) {
        const t = intersectTriangle(bvh, order[k], origin, unit, settings.side, settings.near, best, scratch);
        if (t < best || (t === best && hit === null && t !== Infinity)) {
          best = t;
          hit = {distance: t, triangle: order[k], u: scratch[0], v: scratch[1]};
          if (anyHit) return hit;
        }
      }
      continue;
    }
    const left = nodeOffsets[node];
    const nearLeft = slab(nodeBounds, left, origin, inverse, settings.near, best);
    const nearRight = slab(nodeBounds, left + 1, origin, inverse, settings.near, best);
    if (nearLeft <= nearRight) {
      if (nearRight !== Infinity) stack.push(left + 1);
      if (nearLeft !== Infinity) stack.push(left);
    } else {
      if (nearLeft !== Infinity) stack.push(left);
      stack.push(left + 1);
    }
  }
  if (hit === null) return null;
  const w = 1 - hit.u - hit.v;
  return {
    distance: hit.distance,
    triangle: hit.triangle,
    barycentric: [w, hit.u, hit.v],
    point: [0, 1, 2].map((axis) => origin[axis] + unit[axis] * hit.distance),
  };
}

/**
 * The closest hit along a ray, or null: {distance, triangle, barycentric: [w0, w1, w2], point}. The direction need
 * not be unit length; distances are in world units. options: near, far, side ('double', 'front' or 'back').
 */
export function raycastBVH(bvh, origin, direction, options = {}) {
  return traverse(bvh, origin, direction, options, false);
}

/** Whether anything is hit between near and far (stops at the first hit found, not the closest). */
export function raycastAnyBVH(bvh, origin, direction, options = {}) {
  return traverse(bvh, origin, direction, options, true) !== null;
}

/** {nodes, leaves, maximumDepth, largestLeaf, triangles} of a built hierarchy. */
export function describeBVH(bvh) {
  let leaves = 0;
  let maximumDepth = 0;
  let largestLeaf = 0;
  const stack = [[0, 0]];
  while (stack.length > 0) {
    const [node, depth] = stack.pop();
    maximumDepth = Math.max(maximumDepth, depth);
    if (bvh.nodeCounts[node] > 0) {
      leaves += 1;
      largestLeaf = Math.max(largestLeaf, bvh.nodeCounts[node]);
    } else {
      stack.push([bvh.nodeOffsets[node], depth + 1], [bvh.nodeOffsets[node] + 1, depth + 1]);
    }
  }
  return {nodes: bvh.nodeCount, leaves, maximumDepth, largestLeaf, triangles: bvh.triangleCount};
}
