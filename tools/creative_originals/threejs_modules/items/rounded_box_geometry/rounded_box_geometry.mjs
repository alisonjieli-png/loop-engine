// Rounded box geometry for three.js: a box whose edges and corners are rounded to one radius, built as six face
// grids with per-face UVs and material groups, like BoxGeometry, and smooth normals across the bevels. Original Baltor
// implementation; roundedBoxData works on typed arrays alone, createRoundedBoxGeometry takes three.js as an argument.

/** Default options of roundedBoxData and createRoundedBoxGeometry. */
export const ROUNDED_BOX_DEFAULTS = Object.freeze({
  width: 1,
  height: 1,
  depth: 1,
  radius: 0.1,
  bevelSegments: 4,
  flatSegments: 1,
});

const MAXIMUM_SEGMENTS = 256;
const FLAT_EPSILON = 1e-12;
// Faces in BoxGeometry's material order (+x, -x, +y, -y, +z, -z). For each face, u x v points outward, so a
// counter-clockwise quad in (u, v) is front-facing from outside; uSign and vSign orient the u and v axes.
const FACES = [
  {axis: 0, sign: 1, u: 2, uSign: -1, v: 1, vSign: 1},
  {axis: 0, sign: -1, u: 2, uSign: 1, v: 1, vSign: 1},
  {axis: 1, sign: 1, u: 0, uSign: 1, v: 2, vSign: -1},
  {axis: 1, sign: -1, u: 0, uSign: 1, v: 2, vSign: 1},
  {axis: 2, sign: 1, u: 0, uSign: 1, v: 1, vSign: 1},
  {axis: 2, sign: -1, u: 0, uSign: -1, v: 1, vSign: 1},
];

/**
 * Exact volume of the smooth rounded box (a box shrunk by the radius, grown by a ball of that radius): the inner box,
 * six slabs, twelve quarter cylinders and one ball.
 */
export function roundedBoxVolume(width, height, depth, radius) {
  const a = width / 2 - radius;
  const b = height / 2 - radius;
  const c = depth / 2 - radius;
  if (!(a >= 0 && b >= 0 && c >= 0 && radius >= 0)) throw new RangeError('radius must be in [0, half the smallest size]');
  return 8 * a * b * c + 8 * radius * (a * b + b * c + c * a) + 2 * Math.PI * radius * radius * (a + b + c)
    + (4 / 3) * Math.PI * radius ** 3;
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!(key in ROUNDED_BOX_DEFAULTS)) throw new TypeError(`unknown rounded box option ${key}`);
  }
  const settings = {...ROUNDED_BOX_DEFAULTS, ...options};
  for (const key of ['width', 'height', 'depth']) {
    if (!(settings[key] > 0 && Number.isFinite(settings[key]))) throw new RangeError(`${key} must be positive`);
  }
  const limit = Math.min(settings.width, settings.height, settings.depth) / 2;
  if (!(settings.radius >= 0 && settings.radius <= limit)) {
    throw new RangeError(`radius must be in [0, ${limit}], got ${settings.radius}`);
  }
  for (const key of ['bevelSegments', 'flatSegments']) {
    const value = settings[key];
    if (!Number.isInteger(value) || value < 1 || value > MAXIMUM_SEGMENTS) {
      throw new RangeError(`${key} must be an integer from 1 to ${MAXIMUM_SEGMENTS}`);
    }
  }
  return settings;
}

// Coordinates along one axis of half extent h: the bevel bands are spaced by equal angles (t = -(h - r) - r tan phi),
// the flat middle evenly; a zero-length flat middle collapses to one sample.
function axisSamples(half, radius, bevelSegments, flatSegments) {
  if (radius === 0) {
    return Array.from({length: flatSegments + 1}, (_, index) => -half + (2 * half * index) / flatSegments);
  }
  const inner = half - radius;
  const left = [];
  for (let k = bevelSegments; k >= 1; k -= 1) left.push(-inner - radius * Math.tan((Math.PI / 4) * (k / bevelSegments)));
  const middle = inner > FLAT_EPSILON
    ? Array.from({length: flatSegments + 1}, (_, index) => -inner + (2 * inner * index) / flatSegments)
    : [0];
  const right = left.map((value) => -value).reverse();
  left[0] = -half;
  right[right.length - 1] = half;
  return [...left, ...middle, ...right];
}

/**
 * The rounded box as typed arrays: positions, normals and uvs per vertex, triangle indices (counter-clockwise from
 * outside) and six groups {start, count, materialIndex} in BoxGeometry's face order. Centred at the origin.
 */
export function roundedBoxData(options = {}) {
  const settings = settingsOf(options);
  const half = [settings.width / 2, settings.height / 2, settings.depth / 2];
  const radius = settings.radius;
  const inner = half.map((value) => value - radius);
  const samples = half.map((value) => axisSamples(value, radius, settings.bevelSegments, settings.flatSegments));
  let vertexCount = 0;
  let indexCount = 0;
  for (const face of FACES) {
    const columns = samples[face.u].length;
    const rows = samples[face.v].length;
    vertexCount += columns * rows;
    indexCount += (columns - 1) * (rows - 1) * 6;
  }
  const positions = new Float32Array(vertexCount * 3);
  const normals = new Float32Array(vertexCount * 3);
  const uvs = new Float32Array(vertexCount * 2);
  const indices = vertexCount > 65535 ? new Uint32Array(indexCount) : new Uint16Array(indexCount);
  const groups = [];
  let vertex = 0;
  let index = 0;
  const point = [0, 0, 0];
  FACES.forEach((face, materialIndex) => {
    const alongU = samples[face.u];
    const alongV = samples[face.v];
    const first = vertex;
    for (let row = 0; row < alongV.length; row += 1) {
      for (let column = 0; column < alongU.length; column += 1) {
        point[face.axis] = face.sign * half[face.axis];
        point[face.u] = face.uSign * alongU[column];
        point[face.v] = face.vSign * alongV[row];
        let length = 0;
        const direction = [0, 0, 0];
        for (let axis = 0; axis < 3; axis += 1) {
          const nearest = Math.min(Math.max(point[axis], -inner[axis]), inner[axis]);
          direction[axis] = point[axis] - nearest;
          length += direction[axis] * direction[axis];
        }
        length = Math.sqrt(length);
        for (let axis = 0; axis < 3; axis += 1) {
          const unit = length > 0 ? direction[axis] / length : (axis === face.axis ? face.sign : 0);
          normals[vertex * 3 + axis] = unit;
          const nearest = Math.min(Math.max(point[axis], -inner[axis]), inner[axis]);
          positions[vertex * 3 + axis] = length > 0 ? nearest + radius * unit : point[axis];
        }
        uvs[vertex * 2] = (alongU[column] + half[face.u]) / (2 * half[face.u]);
        uvs[vertex * 2 + 1] = (alongV[row] + half[face.v]) / (2 * half[face.v]);
        vertex += 1;
      }
    }
    const start = index;
    const columns = alongU.length;
    for (let row = 0; row < alongV.length - 1; row += 1) {
      for (let column = 0; column < columns - 1; column += 1) {
        const a = first + row * columns + column;
        const b = a + 1;
        const c = a + columns + 1;
        const d = a + columns;
        indices.set([a, b, c, a, c, d], index);
        index += 6;
      }
    }
    groups.push({start, count: index - start, materialIndex});
  });
  return {positions, normals, uvs, indices, groups};
}

/** A THREE.BufferGeometry of the rounded box with position, normal and uv attributes, an index and six groups. */
export function createRoundedBoxGeometry(THREE, options = {}) {
  const data = roundedBoxData(options);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(data.positions, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(data.normals, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(data.uvs, 2));
  geometry.setIndex(new THREE.BufferAttribute(data.indices, 1));
  for (const group of data.groups) geometry.addGroup(group.start, group.count, group.materialIndex);
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}
