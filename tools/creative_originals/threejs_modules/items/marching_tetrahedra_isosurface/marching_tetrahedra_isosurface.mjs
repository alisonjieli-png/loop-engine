// Isosurfaces for three.js by marching tetrahedra: sample a scalar field on a grid (or bring your own samples), split
// every cell into six tetrahedra around its main diagonal, and emit a welded, consistently outward-facing triangle mesh
// with normals from the field gradient. Signed distances (inside below the level) and densities such as metaballs
// (inside above it) both work. Original Baltor implementation on typed arrays; only createIsosurfaceGeometry needs
// three.js.

/** Default options of marchingTetrahedraData. */
export const MARCHING_TETRAHEDRA_DEFAULTS = Object.freeze({
  isoLevel: 0,
  insideBelow: true,
  maxVertices: 4000000,
});

const MAXIMUM_SAMPLES_PER_AXIS = 1024;
const SNAP = 1e-12;
// Cube corners as (x, y, z) offsets, and the six tetrahedra of the cube that share its diagonal 0-6. Neighbouring cubes
// split every shared face along the same diagonal, so the surface has no cracks.
const CORNERS = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]];
const TETRAHEDRA = [[0, 5, 1, 6], [0, 1, 2, 6], [0, 2, 3, 6], [0, 3, 7, 6], [0, 7, 4, 6], [0, 4, 5, 6]];

function vectorOf(value, name) {
  if (!Array.isArray(value) || value.length !== 3 || !value.every(Number.isFinite)) {
    throw new TypeError(`${name} must be [x, y, z] with finite numbers`);
  }
  return value;
}

function sizeOf(resolution) {
  const size = typeof resolution === 'number' ? [resolution, resolution, resolution] : resolution;
  if (!Array.isArray(size) || size.length !== 3 || !size.every((n) => Number.isInteger(n) && n >= 2 && n <= MAXIMUM_SAMPLES_PER_AXIS)) {
    throw new RangeError(`resolution must be an integer or [nx, ny, nz] from 2 to ${MAXIMUM_SAMPLES_PER_AXIS}`);
  }
  return size;
}

/**
 * Sample fn(x, y, z) on a box: options {min, max, resolution} with resolution a sample count per axis (or one count).
 * Returns the field {values, size, min, max} with values[x + nx * (y + ny * z)].
 */
export function sampleScalarField(fn, options = {}) {
  if (typeof fn !== 'function') throw new TypeError('fn must be a function of (x, y, z)');
  for (const key of Object.keys(options)) {
    if (!['min', 'max', 'resolution'].includes(key)) throw new TypeError(`unknown sampling option ${key}`);
  }
  const min = vectorOf(options.min ?? [-1, -1, -1], 'min');
  const max = vectorOf(options.max ?? [1, 1, 1], 'max');
  if (!min.every((value, axis) => value < max[axis])) throw new RangeError('min must be below max on every axis');
  const size = sizeOf(options.resolution ?? 32);
  const [nx, ny, nz] = size;
  const values = new Float32Array(nx * ny * nz);
  for (let k = 0; k < nz; k += 1) {
    const z = min[2] + ((max[2] - min[2]) * k) / (nz - 1);
    for (let j = 0; j < ny; j += 1) {
      const y = min[1] + ((max[1] - min[1]) * j) / (ny - 1);
      for (let i = 0; i < nx; i += 1) {
        const value = fn(min[0] + ((max[0] - min[0]) * i) / (nx - 1), y, z);
        if (!Number.isFinite(value)) throw new RangeError(`the field is not finite at sample (${i}, ${j}, ${k})`);
        values[i + nx * (j + ny * k)] = value;
      }
    }
  }
  return {values, size: [...size], min: [...min], max: [...max]};
}

function fieldOf(field) {
  if (!field || typeof field !== 'object') throw new TypeError('the field is {values, size, min, max}');
  const size = sizeOf(field.size);
  const min = vectorOf(field.min, 'min');
  const max = vectorOf(field.max, 'max');
  if (!min.every((value, axis) => value < max[axis])) throw new RangeError('min must be below max on every axis');
  if (!(ArrayBuffer.isView(field.values) || Array.isArray(field.values)) || field.values.length !== size[0] * size[1] * size[2]) {
    throw new RangeError('values must hold nx * ny * nz numbers');
  }
  return {values: field.values, size, min, max};
}

/**
 * The isosurface as typed arrays {positions, normals, indices}: welded (vertices on a grid edge are shared), triangles
 * counter-clockwise seen from outside (from the inside region toward the outside), normals from the interpolated field
 * gradient pointing outward. Where the surface leaves the sampled box it stays open: pad the field to close it.
 */
export function marchingTetrahedraData(field, options = {}) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(MARCHING_TETRAHEDRA_DEFAULTS, key)) throw new TypeError(`unknown isosurface option ${key}`);
  }
  const settings = {...MARCHING_TETRAHEDRA_DEFAULTS, ...options};
  if (!Number.isFinite(settings.isoLevel)) throw new RangeError('isoLevel must be a finite number');
  if (typeof settings.insideBelow !== 'boolean') throw new TypeError('insideBelow must be true or false');
  if (!Number.isInteger(settings.maxVertices) || settings.maxVertices < 1) throw new RangeError('maxVertices must be a positive integer');
  const {values, size, min, max} = fieldOf(field);
  const [nx, ny, nz] = size;
  const step = [0, 1, 2].map((axis) => (max[axis] - min[axis]) / (size[axis] - 1));
  const total = nx * ny * nz;
  const iso = settings.isoLevel;
  const outwardSign = settings.insideBelow ? 1 : -1;
  const at = (i, j, k) => values[i + nx * (j + ny * k)];
  const gradient = (point) => {
    const i = point % nx;
    const j = Math.floor(point / nx) % ny;
    const k = Math.floor(point / (nx * ny));
    const difference = (low, high, span) => (high - low) / span;
    return [
      difference(at(Math.max(i - 1, 0), j, k), at(Math.min(i + 1, nx - 1), j, k), (Math.min(i + 1, nx - 1) - Math.max(i - 1, 0)) * step[0]),
      difference(at(i, Math.max(j - 1, 0), k), at(i, Math.min(j + 1, ny - 1), k), (Math.min(j + 1, ny - 1) - Math.max(j - 1, 0)) * step[1]),
      difference(at(i, j, Math.max(k - 1, 0)), at(i, j, Math.min(k + 1, nz - 1)), (Math.min(k + 1, nz - 1) - Math.max(k - 1, 0)) * step[2]),
    ];
  };
  const location = (point) => [min[0] + (point % nx) * step[0], min[1] + (Math.floor(point / nx) % ny) * step[1],
    min[2] + Math.floor(point / (nx * ny)) * step[2]];
  const positions = [];
  const normals = [];
  const triangles = [];
  const cache = new Map();
  // The surface vertex on the grid edge from point p (inside) to point q (outside); one vertex per edge or grid point.
  const crossing = (p, q) => {
    const vp = values[p];
    const vq = values[q];
    let t = (iso - vp) / (vq - vp);
    let key = p < q ? p * total + q : q * total + p;
    if (t <= SNAP) {
      t = 0;
      key = -1 - p;
    } else if (t >= 1 - SNAP) {
      t = 1;
      key = -1 - q;
    }
    const known = cache.get(key);
    if (known !== undefined) return known;
    const a = location(p);
    const b = location(q);
    const ga = gradient(p);
    const gb = gradient(q);
    const g = [0, 1, 2].map((axis) => (ga[axis] + (gb[axis] - ga[axis]) * t) * outwardSign);
    const length = Math.hypot(g[0], g[1], g[2]) || 1;
    positions.push(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
    normals.push(g[0] / length, g[1] / length, g[2] / length);
    const index = positions.length / 3 - 1;
    if (index >= settings.maxVertices) throw new RangeError(`the surface needs more than ${settings.maxVertices} vertices`);
    cache.set(key, index);
    return index;
  };
  const emit = (a, b, c, from, to) => {
    if (a === b || b === c || a === c) return;
    const p = positions;
    const u = [p[b * 3] - p[a * 3], p[b * 3 + 1] - p[a * 3 + 1], p[b * 3 + 2] - p[a * 3 + 2]];
    const w = [p[c * 3] - p[a * 3], p[c * 3 + 1] - p[a * 3 + 1], p[c * 3 + 2] - p[a * 3 + 2]];
    const face = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]];
    const direction = [to[0] - from[0], to[1] - from[1], to[2] - from[2]];
    if (face[0] * direction[0] + face[1] * direction[1] + face[2] * direction[2] < 0) triangles.push(a, c, b);
    else triangles.push(a, b, c);
  };
  const corner = new Array(8);
  for (let k = 0; k < nz - 1; k += 1) {
    for (let j = 0; j < ny - 1; j += 1) {
      for (let i = 0; i < nx - 1; i += 1) {
        for (let c = 0; c < 8; c += 1) {
          const [dx, dy, dz] = CORNERS[c];
          corner[c] = (i + dx) + nx * ((j + dy) + ny * (k + dz));
        }
        for (const tetrahedron of TETRAHEDRA) {
          const points = tetrahedron.map((c) => corner[c]);
          const inside = [];
          const outside = [];
          for (const point of points) {
            const value = values[point];
            if (settings.insideBelow ? value < iso : value > iso) inside.push(point);
            else outside.push(point);
          }
          if (inside.length === 0 || outside.length === 0) continue;
          const centroid = (list) => list.map(location).reduce((sum, point) => sum.map((value, axis) => value + point[axis] / list.length), [0, 0, 0]);
          const from = centroid(inside);
          const to = centroid(outside);
          if (inside.length === 1 || outside.length === 1) {
            const [lone, others, loneInside] = inside.length === 1 ? [inside[0], outside, true] : [outside[0], inside, false];
            const vertices = others.map((other) => (loneInside ? crossing(lone, other) : crossing(other, lone)));
            emit(vertices[0], vertices[1], vertices[2], from, to);
          } else {
            const [a, b] = inside;
            const [c, d] = outside;
            const ac = crossing(a, c);
            const ad = crossing(a, d);
            const bd = crossing(b, d);
            const bc = crossing(b, c);
            emit(ac, ad, bd, from, to);
            emit(ac, bd, bc, from, to);
          }
        }
      }
    }
  }
  const vertexCount = positions.length / 3;
  return {positions: Float32Array.from(positions), normals: Float32Array.from(normals),
    indices: vertexCount > 65535 ? Uint32Array.from(triangles) : Uint16Array.from(triangles)};
}

/** A THREE.BufferGeometry of the isosurface with position and normal attributes and an index. */
export function createIsosurfaceGeometry(THREE, field, options = {}) {
  const data = marchingTetrahedraData(field, options);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(data.positions, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(data.normals, 3));
  geometry.setIndex(new THREE.BufferAttribute(data.indices, 1));
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}
