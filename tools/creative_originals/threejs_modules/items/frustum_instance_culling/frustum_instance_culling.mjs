// Frustum culling for three.js instancing: the six planes of a view frustum read straight from a column-major
// view-projection matrix (Gribb and Hartmann), sphere and box classification, and a pass that copies only the visible
// instance matrices to the front of an InstancedMesh's matrix array and returns the count to draw. Original Baltor
// implementation; it needs no three.js and works on plain arrays.

/** Classification results of classifySphere and classifyBox. */
export const FRUSTUM_RESULT = Object.freeze({OUTSIDE: 0, INTERSECTS: 1, INSIDE: 2});

/** Default options: frustumPlanes takes depthZeroToOne, cullInstances takes center and indices. */
export const FRUSTUM_CULL_DEFAULTS = Object.freeze({
  depthZeroToOne: false,
  center: Object.freeze([0, 0, 0]),
  indices: null,
});

const PLANE_NAMES = Object.freeze(['left', 'right', 'bottom', 'top', 'near', 'far']);

function strict(options, allowed) {
  for (const key of Object.keys(options)) {
    if (!allowed.includes(key)) throw new TypeError(`unknown frustum option ${key}`);
  }
  return {...FRUSTUM_CULL_DEFAULTS, ...options};
}

function checkMatrix(matrix, name) {
  if (!(matrix && matrix.length === 16)) throw new RangeError(`${name} must hold 16 numbers`);
  for (let k = 0; k < 16; k += 1) {
    if (!Number.isFinite(matrix[k])) throw new RangeError(`${name}[${k}] is not finite`);
  }
}

/** The product a * b of two column-major 4 x 4 matrices (for example projection * view), as a Float64Array. */
export function multiplyMatrices(a, b) {
  checkMatrix(a, 'a');
  checkMatrix(b, 'b');
  const out = new Float64Array(16);
  for (let column = 0; column < 4; column += 1) {
    for (let row = 0; row < 4; row += 1) {
      out[column * 4 + row] = a[row] * b[column * 4] + a[4 + row] * b[column * 4 + 1] + a[8 + row] * b[column * 4 + 2]
        + a[12 + row] * b[column * 4 + 3];
    }
  }
  return out;
}

/**
 * The six frustum planes of a column-major view-projection matrix, normalized, as a Float64Array of 24 numbers
 * [a, b, c, d] in the order left, right, bottom, top, near, far; a point is inside a plane where
 * a x + b y + c z + d >= 0. depthZeroToOne selects WebGPU-style depth (clip z in [0, w]) instead of WebGL's [-w, w].
 * Pass projection * view * model to test in a mesh's local space.
 */
export function frustumPlanes(matrix, options = {}) {
  const settings = strict(options, ['depthZeroToOne']);
  checkMatrix(matrix, 'matrix');
  const row = (index) => [matrix[index], matrix[4 + index], matrix[8 + index], matrix[12 + index]];
  const [x, y, z, w] = [row(0), row(1), row(2), row(3)];
  const add = (p, q, sign) => p.map((value, k) => value + sign * q[k]);
  const raw = [add(w, x, 1), add(w, x, -1), add(w, y, 1), add(w, y, -1),
    settings.depthZeroToOne ? z : add(w, z, 1), add(w, z, -1)];
  const planes = new Float64Array(24);
  raw.forEach((plane, index) => {
    const length = Math.hypot(plane[0], plane[1], plane[2]);
    if (!(length > 0)) throw new RangeError(`the ${PLANE_NAMES[index]} plane is degenerate`);
    for (let k = 0; k < 4; k += 1) planes[index * 4 + k] = plane[k] / length;
  });
  return planes;
}

/** OUTSIDE, INTERSECTS or INSIDE for a sphere at (x, y, z) with the given radius against normalized planes. */
export function classifySphere(planes, x, y, z, radius) {
  let result = FRUSTUM_RESULT.INSIDE;
  for (let plane = 0; plane < 24; plane += 4) {
    const distance = planes[plane] * x + planes[plane + 1] * y + planes[plane + 2] * z + planes[plane + 3];
    if (distance < -radius) return FRUSTUM_RESULT.OUTSIDE;
    if (distance < radius) result = FRUSTUM_RESULT.INTERSECTS;
  }
  return result;
}

/**
 * OUTSIDE, INTERSECTS or INSIDE for an axis-aligned box [min, max] against normalized planes. Like every plane test
 * it may call a box near a frustum corner INTERSECTS when it is just outside; it never calls a visible box OUTSIDE.
 */
export function classifyBox(planes, min, max) {
  let result = FRUSTUM_RESULT.INSIDE;
  for (let plane = 0; plane < 24; plane += 4) {
    const a = planes[plane];
    const b = planes[plane + 1];
    const c = planes[plane + 2];
    const d = planes[plane + 3];
    const far = a * (a >= 0 ? max[0] : min[0]) + b * (b >= 0 ? max[1] : min[1]) + c * (c >= 0 ? max[2] : min[2]) + d;
    if (far < 0) return FRUSTUM_RESULT.OUTSIDE;
    const near = a * (a >= 0 ? min[0] : max[0]) + b * (b >= 0 ? min[1] : max[1]) + c * (c >= 0 ? min[2] : max[2]) + d;
    if (near < 0) result = FRUSTUM_RESULT.INTERSECTS;
  }
  return result;
}

/**
 * Copy every instance whose bounding sphere (radius around options.center, both in the model's space, scaled by the
 * instance's largest axis scale) is not outside the planes to the front of target, in order, and return how many
 * were kept: set InstancedMesh.count to it. target may be source itself (compaction in place). options.indices, a
 * Uint32Array, receives the kept instance numbers.
 */
export function cullInstances(source, radius, planes, target, options = {}) {
  const settings = strict(options, ['center', 'indices']);
  if (!(source && source.length % 16 === 0)) throw new RangeError('source must hold whole 4 x 4 matrices');
  if (!(target && target.length >= source.length)) throw new RangeError('target must be at least as long as source');
  if (!(radius >= 0 && Number.isFinite(radius))) throw new RangeError('radius must be a non-negative number');
  if (!(planes && planes.length === 24)) throw new RangeError('planes must come from frustumPlanes');
  const [cx, cy, cz] = settings.center;
  const indices = settings.indices;
  const total = source.length / 16;
  if (indices !== null && !(indices.length >= total)) throw new RangeError('indices must have room for every instance');
  let kept = 0;
  for (let instance = 0; instance < total; instance += 1) {
    const m = instance * 16;
    const x = source[m] * cx + source[m + 4] * cy + source[m + 8] * cz + source[m + 12];
    const y = source[m + 1] * cx + source[m + 5] * cy + source[m + 9] * cz + source[m + 13];
    const z = source[m + 2] * cx + source[m + 6] * cy + source[m + 10] * cz + source[m + 14];
    const scale = Math.sqrt(Math.max(
      source[m] ** 2 + source[m + 1] ** 2 + source[m + 2] ** 2,
      source[m + 4] ** 2 + source[m + 5] ** 2 + source[m + 6] ** 2,
      source[m + 8] ** 2 + source[m + 9] ** 2 + source[m + 10] ** 2));
    if (classifySphere(planes, x, y, z, radius * scale) === FRUSTUM_RESULT.OUTSIDE) continue;
    if (kept !== instance || target !== source) {
      if (target === source) target.copyWithin(kept * 16, m, m + 16);
      else for (let k = 0; k < 16; k += 1) target[kept * 16 + k] = source[m + k];
    }
    if (indices !== null) indices[kept] = instance;
    kept += 1;
  }
  return kept;
}
