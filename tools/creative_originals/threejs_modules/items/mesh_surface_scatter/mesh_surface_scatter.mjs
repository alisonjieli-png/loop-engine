// Mesh surface scattering for three.js: uniformly distributed points on any triangle mesh, picked by area with a Vose
// alias table and placed with uniform barycentric coordinates, an optional per-vertex density by rejection, and
// matrices that stand a model on each point along its normal. Original Baltor implementation; it reads typed arrays
// (or a BufferGeometry's arrays) and needs no three.js.

/** Default options of scatterOnSurface and scatterOnGeometry. weights and normals are per-vertex arrays or null. */
export const SURFACE_SCATTER_DEFAULTS = Object.freeze({count: 1000, seed: 1, weights: null, normals: null});

/** Default options of surfaceMatrices. */
export const SURFACE_MATRIX_DEFAULTS = Object.freeze({scale: 1, scaleJitter: 0, spin: true, offset: 0, seed: 5});

const MAXIMUM_SAMPLES = 10000000;
const MAXIMUM_REJECTIONS = 1000;

// A small seeded generator: a Weyl sequence through the 32-bit finalizer of a hash mixer. Uniform in [0, 1).
function createRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x9e3779b9) >>> 0;
    let mixed = state;
    mixed = Math.imul(mixed ^ (mixed >>> 16), 0x85ebca6b);
    mixed = Math.imul(mixed ^ (mixed >>> 13), 0xc2b2ae35);
    mixed ^= mixed >>> 16;
    return (mixed >>> 0) / 4294967296;
  };
}

function strict(options, defaults, name) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(defaults, key)) throw new TypeError(`unknown ${name} option ${key}`);
  }
  return {...defaults, ...options};
}

function triangleCount(positions, indices) {
  if (!positions || positions.length % 3 !== 0) throw new RangeError('positions must hold x, y, z triples');
  const vertices = positions.length / 3;
  if (indices === null) {
    if (vertices % 3 !== 0) throw new RangeError('non-indexed positions must hold whole triangles');
    return vertices / 3;
  }
  if (indices.length % 3 !== 0) throw new RangeError('indices must hold whole triangles');
  for (let k = 0; k < indices.length; k += 1) {
    if (!(indices[k] >= 0 && indices[k] < vertices && Number.isInteger(indices[k]))) {
      throw new RangeError(`index ${indices[k]} at ${k} is outside the ${vertices} vertices`);
    }
  }
  return indices.length / 3;
}

function corner(indices, triangle, k) {
  return indices === null ? triangle * 3 + k : indices[triangle * 3 + k];
}

/** The area of every triangle (Float64Array), from positions and optional indices (null for non-indexed). */
export function triangleAreas(positions, indices = null) {
  const count = triangleCount(positions, indices);
  const areas = new Float64Array(count);
  for (let t = 0; t < count; t += 1) {
    const a = corner(indices, t, 0) * 3;
    const b = corner(indices, t, 1) * 3;
    const c = corner(indices, t, 2) * 3;
    const ux = positions[b] - positions[a];
    const uy = positions[b + 1] - positions[a + 1];
    const uz = positions[b + 2] - positions[a + 2];
    const vx = positions[c] - positions[a];
    const vy = positions[c + 1] - positions[a + 1];
    const vz = positions[c + 2] - positions[a + 2];
    areas[t] = 0.5 * Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx);
  }
  return areas;
}

/**
 * Vose's alias table for sampling index i with probability weights[i] / sum(weights) in constant time:
 * {probability: Float64Array, alias: Uint32Array}. Weights must be finite, non-negative and not all zero.
 */
export function buildAliasTable(weights) {
  const size = weights.length;
  let total = 0;
  for (let i = 0; i < size; i += 1) {
    if (!(weights[i] >= 0 && Number.isFinite(weights[i]))) throw new RangeError(`weight ${i} is ${weights[i]}`);
    total += weights[i];
  }
  if (!(size > 0 && total > 0)) throw new RangeError('the weights must not all be zero');
  const scaled = new Float64Array(size);
  const probability = new Float64Array(size);
  const alias = new Uint32Array(size);
  const small = [];
  const large = [];
  for (let i = 0; i < size; i += 1) {
    scaled[i] = (weights[i] * size) / total;
    alias[i] = i;
    (scaled[i] < 1 ? small : large).push(i);
  }
  while (small.length > 0 && large.length > 0) {
    const low = small.pop();
    const high = large.pop();
    probability[low] = scaled[low];
    alias[low] = high;
    scaled[high] -= 1 - scaled[low];
    (scaled[high] < 1 ? small : large).push(high);
  }
  for (const index of large) probability[index] = 1;
  for (const index of small) probability[index] = 1;
  return {probability, alias};
}

/** One draw from an alias table with two uniform numbers in [0, 1). */
export function sampleAlias(table, first, second) {
  const size = table.probability.length;
  const index = Math.min(Math.floor(first * size), size - 1);
  return second < table.probability[index] ? index : table.alias[index];
}

/**
 * count points on the surface, uniform by area (or by the per-vertex weights, interpolated across each triangle):
 * {positions, normals, triangles, barycentrics}. Normals are interpolated from options.normals when given, else the
 * face normal (counter-clockwise winding). Deterministic for a seed.
 */
export function scatterOnSurface(positions, indices = null, options = {}) {
  const settings = strict(options, SURFACE_SCATTER_DEFAULTS, 'surface scatter');
  if (!Number.isInteger(settings.count) || settings.count < 0 || settings.count > MAXIMUM_SAMPLES) {
    throw new RangeError(`count must be an integer from 0 to ${MAXIMUM_SAMPLES}`);
  }
  if (!Number.isInteger(settings.seed)) throw new RangeError('seed must be an integer');
  const triangles = triangleCount(positions, indices);
  const vertices = positions.length / 3;
  const {weights, normals} = settings;
  if (weights !== null && weights.length !== vertices) throw new RangeError('weights need one value per vertex');
  if (normals !== null && normals.length !== positions.length) throw new RangeError('normals need one triple per vertex');
  const areas = triangleAreas(positions, indices);
  const envelope = new Float64Array(triangles);
  for (let t = 0; t < triangles; t += 1) {
    let top = 1;
    if (weights !== null) {
      top = Math.max(weights[corner(indices, t, 0)], weights[corner(indices, t, 1)], weights[corner(indices, t, 2)]);
    }
    envelope[t] = areas[t] * top;
  }
  const table = buildAliasTable(envelope);
  const random = createRandom(settings.seed);
  const out = {
    positions: new Float32Array(settings.count * 3),
    normals: new Float32Array(settings.count * 3),
    triangles: new Uint32Array(settings.count),
    barycentrics: new Float32Array(settings.count * 3),
  };
  for (let sample = 0; sample < settings.count; sample += 1) {
    let triangle = 0;
    let weightA = 1;
    let weightB = 0;
    let weightC = 0;
    for (let attempt = 0; attempt <= MAXIMUM_REJECTIONS; attempt += 1) {
      triangle = sampleAlias(table, random(), random());
      const root = Math.sqrt(random());
      const second = random();
      weightA = 1 - root;
      weightB = root * (1 - second);
      weightC = root * second;
      if (weights === null) break;
      const wa = weights[corner(indices, triangle, 0)];
      const wb = weights[corner(indices, triangle, 1)];
      const wc = weights[corner(indices, triangle, 2)];
      if (random() * Math.max(wa, wb, wc) < weightA * wa + weightB * wb + weightC * wc) break;
    }
    const a = corner(indices, triangle, 0);
    const b = corner(indices, triangle, 1);
    const c = corner(indices, triangle, 2);
    let nx = 0;
    let ny = 0;
    let nz = 0;
    if (normals !== null) {
      nx = weightA * normals[a * 3] + weightB * normals[b * 3] + weightC * normals[c * 3];
      ny = weightA * normals[a * 3 + 1] + weightB * normals[b * 3 + 1] + weightC * normals[c * 3 + 1];
      nz = weightA * normals[a * 3 + 2] + weightB * normals[b * 3 + 2] + weightC * normals[c * 3 + 2];
    } else {
      const ux = positions[b * 3] - positions[a * 3];
      const uy = positions[b * 3 + 1] - positions[a * 3 + 1];
      const uz = positions[b * 3 + 2] - positions[a * 3 + 2];
      const vx = positions[c * 3] - positions[a * 3];
      const vy = positions[c * 3 + 1] - positions[a * 3 + 1];
      const vz = positions[c * 3 + 2] - positions[a * 3 + 2];
      nx = uy * vz - uz * vy;
      ny = uz * vx - ux * vz;
      nz = ux * vy - uy * vx;
    }
    const length = Math.hypot(nx, ny, nz) || 1;
    for (let axis = 0; axis < 3; axis += 1) {
      out.positions[sample * 3 + axis] = weightA * positions[a * 3 + axis] + weightB * positions[b * 3 + axis]
        + weightC * positions[c * 3 + axis];
    }
    out.normals.set([nx / length, ny / length, nz / length], sample * 3);
    out.triangles[sample] = triangle;
    out.barycentrics.set([weightA, weightB, weightC], sample * 3);
  }
  return out;
}

function attributeArray(attribute, size) {
  if (!attribute) return null;
  if (attribute.isInterleavedBufferAttribute !== true && attribute.array && attribute.itemSize === size) {
    return attribute.array;
  }
  const copy = new Float32Array(attribute.count * size);
  const read = [attribute.getX, attribute.getY, attribute.getZ];
  for (let index = 0; index < attribute.count; index += 1) {
    for (let axis = 0; axis < size; axis += 1) copy[index * size + axis] = read[axis].call(attribute, index);
  }
  return copy;
}

/**
 * scatterOnSurface on a three.js BufferGeometry: reads its position attribute, its index and, unless
 * options.normals is given, its normal attribute. Interleaved attributes are copied out first.
 */
export function scatterOnGeometry(geometry, options = {}) {
  const positions = attributeArray(geometry.attributes.position, 3);
  if (positions === null) throw new TypeError('the geometry has no position attribute');
  const indices = geometry.index ? geometry.index.array : null;
  const normals = Object.prototype.hasOwnProperty.call(options, 'normals') ? options.normals
    : attributeArray(geometry.attributes.normal, 3);
  return scatterOnSurface(positions, indices, {...options, normals});
}

/**
 * Column-major matrices (16 per sample) that stand a model on each sample: its +Y axis along the sample normal, a
 * seeded spin about that axis, uniform scale * (1 +- scaleJitter), lifted by offset along the normal.
 */
export function surfaceMatrices(samples, options = {}) {
  const settings = strict(options, SURFACE_MATRIX_DEFAULTS, 'surface matrix');
  if (!(settings.scale > 0 && Number.isFinite(settings.scale))) throw new RangeError('scale must be positive');
  if (!(settings.scaleJitter >= 0 && settings.scaleJitter < 1)) throw new RangeError('scaleJitter must be in [0, 1)');
  if (!Number.isFinite(settings.offset)) throw new RangeError('offset must be finite');
  const count = samples.positions.length / 3;
  if (samples.normals.length !== samples.positions.length) throw new RangeError('one normal per position is needed');
  const random = createRandom(settings.seed);
  const matrices = new Float32Array(count * 16);
  for (let index = 0; index < count; index += 1) {
    const nx = samples.normals[index * 3];
    const ny = samples.normals[index * 3 + 1];
    const nz = samples.normals[index * 3 + 2];
    // The shortest rotation from +Y to n: axis (n.z, 0, -n.x), quaternion (axis, 1 + n.y), normalized; straight
    // down is a half turn about +X.
    let qx = nz;
    let qy = 0;
    let qz = -nx;
    let qw = 1 + ny;
    const norm = Math.hypot(qx, qy, qz, qw);
    if (norm < 1e-9) [qx, qy, qz, qw] = [1, 0, 0, 0];
    else [qx, qy, qz, qw] = [qx / norm, qy / norm, qz / norm, qw / norm];
    const angle = settings.spin ? random() * Math.PI * 2 : 0;
    const sy = Math.sin(angle / 2);
    const cw = Math.cos(angle / 2);
    // Spin about +Y first, then align: q = align * spin with spin = (0, sy, 0, cw).
    const x = qx * cw - qz * sy;
    const y = qw * sy + qy * cw;
    const z = qz * cw + qx * sy;
    const w = qw * cw - qy * sy;
    const size = settings.scale * (1 + settings.scaleJitter * (2 * random() - 1));
    const xx = x * x * 2;
    const yy = y * y * 2;
    const zz = z * z * 2;
    const xy = x * y * 2;
    const xz = x * z * 2;
    const yz = y * z * 2;
    const wx = w * x * 2;
    const wy = w * y * 2;
    const wz = w * z * 2;
    matrices.set([
      (1 - yy - zz) * size, (xy + wz) * size, (xz - wy) * size, 0,
      (xy - wz) * size, (1 - xx - zz) * size, (yz + wx) * size, 0,
      (xz + wy) * size, (yz - wx) * size, (1 - xx - yy) * size, 0,
      samples.positions[index * 3] + nx * settings.offset, samples.positions[index * 3 + 1] + ny * settings.offset,
      samples.positions[index * 3 + 2] + nz * settings.offset, 1,
    ], index * 16);
  }
  return matrices;
}
