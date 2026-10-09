// Superellipsoid geometry for three.js: Barr's superquadric ellipsoid with three radii and two shape exponents, from
// boxes and cushions through ellipsoids to octahedra and stars, with analytic normals, UVs, the inside-outside function
// and the closed-form volume. Original Baltor implementation; superellipsoidData works on typed arrays alone.

/** Default options. exponentY is Barr's epsilon 1 (north-south, along Y), exponentXZ is epsilon 2 (east-west). */
export const SUPERELLIPSOID_DEFAULTS = Object.freeze({
  radiusX: 1,
  radiusY: 1,
  radiusZ: 1,
  exponentY: 0.5,
  exponentXZ: 0.5,
  widthSegments: 48,
  heightSegments: 32,
});

const MINIMUM_EXPONENT = 0.02;
const MAXIMUM_EXPONENT = 4;
const MAXIMUM_SEGMENTS = 1024;
// A cosine or sine below this is an exact zero of the angle grid (cos(pi / 2) is 6e-17 in floating point).
const ANGLE_SNAP = 1e-12;
const SHAPE_KEYS = ['radiusX', 'radiusY', 'radiusZ', 'exponentY', 'exponentXZ'];

function settingsOf(options, keys = Object.keys(SUPERELLIPSOID_DEFAULTS)) {
  for (const key of Object.keys(options)) {
    if (!keys.includes(key)) throw new TypeError(`unknown superellipsoid option ${key}`);
  }
  const settings = {...SUPERELLIPSOID_DEFAULTS, ...options};
  for (const key of ['radiusX', 'radiusY', 'radiusZ']) {
    if (!(settings[key] > 0 && Number.isFinite(settings[key]))) throw new RangeError(`${key} must be positive`);
  }
  for (const key of ['exponentY', 'exponentXZ']) {
    const value = settings[key];
    if (!(value >= MINIMUM_EXPONENT && value <= MAXIMUM_EXPONENT)) {
      throw new RangeError(`${key} must be in [${MINIMUM_EXPONENT}, ${MAXIMUM_EXPONENT}], got ${value}`);
    }
  }
  if (!Number.isInteger(settings.widthSegments) || settings.widthSegments < 3 || settings.widthSegments > MAXIMUM_SEGMENTS) {
    throw new RangeError(`widthSegments must be an integer from 3 to ${MAXIMUM_SEGMENTS}`);
  }
  if (!Number.isInteger(settings.heightSegments) || settings.heightSegments < 2 || settings.heightSegments > MAXIMUM_SEGMENTS) {
    throw new RangeError(`heightSegments must be an integer from 2 to ${MAXIMUM_SEGMENTS}`);
  }
  return settings;
}

// sign(value) * |value| ^ exponent, with an exact zero kept at zero for every exponent.
function signedPower(value, exponent) {
  if (value === 0) return 0;
  return Math.sign(value) * Math.abs(value) ** exponent;
}

function snappedCosSin(angle) {
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return [Math.abs(cosine) < ANGLE_SNAP ? 0 : cosine, Math.abs(sine) < ANGLE_SNAP ? 0 : sine];
}

// ln Gamma(x) for x > 0: shift up to 10 or more with Gamma(x + 1) = x Gamma(x), then Stirling's series to the z^-7 term.
function logGamma(x) {
  let shift = 0;
  let z = x;
  while (z < 10) {
    shift += Math.log(z);
    z += 1;
  }
  const inverse = 1 / z;
  const square = inverse * inverse;
  const series = inverse * (1 / 12 - square * (1 / 360 - square * (1 / 1260 - square / 1680)));
  return (z - 0.5) * Math.log(z) - z + 0.5 * Math.log(2 * Math.PI) + series - shift;
}

function beta(x, y) {
  return Math.exp(logGamma(x) + logGamma(y) - logGamma(x + y));
}

/**
 * Exact volume of the superellipsoid: 2 a b c e1 e2 B(e1 / 2 + 1, e1) B(e2 / 2, e2 / 2) with e1 = exponentY and
 * e2 = exponentXZ (equal to a b c e1 e2 B(e1 / 2, e1 + 1) B(e2 / 2, e2 / 2)). 4/3 pi a b c for e1 = e2 = 1.
 */
export function superellipsoidVolume(radiusX, radiusY, radiusZ, exponentY, exponentXZ) {
  const settings = settingsOf({radiusX, radiusY, radiusZ, exponentY, exponentXZ}, SHAPE_KEYS);
  const e1 = settings.exponentY;
  const e2 = settings.exponentXZ;
  return 2 * radiusX * radiusY * radiusZ * e1 * e2 * beta(e1 / 2 + 1, e1) * beta(e2 / 2, e2 / 2);
}

/**
 * Barr's inside-outside function at a point: below 1 inside, 1 on the surface, above 1 outside. Options are the shape
 * keys of SUPERELLIPSOID_DEFAULTS (radii and exponents).
 */
export function superellipsoidImplicit(x, y, z, options = {}) {
  const settings = settingsOf(options, SHAPE_KEYS);
  const e1 = settings.exponentY;
  const e2 = settings.exponentXZ;
  const across = Math.abs(x / settings.radiusX) ** (2 / e2) + Math.abs(z / settings.radiusZ) ** (2 / e2);
  return across ** (e2 / e1) + Math.abs(y / settings.radiusY) ** (2 / e1);
}

/**
 * The superellipsoid as typed arrays {positions, normals, uvs, indices}: a latitude-longitude grid of
 * (widthSegments + 1) x (heightSegments + 1) vertices (the seam and the poles repeat for UVs, as in SphereGeometry),
 * triangles counter-clockwise from outside, normals from Barr's analytic normal formula.
 */
export function superellipsoidData(options = {}) {
  const settings = settingsOf(options);
  const {radiusX, radiusY, radiusZ, widthSegments, heightSegments} = settings;
  const e1 = settings.exponentY;
  const e2 = settings.exponentXZ;
  const columns = widthSegments + 1;
  const vertexCount = columns * (heightSegments + 1);
  const positions = new Float32Array(vertexCount * 3);
  const normals = new Float32Array(vertexCount * 3);
  const uvs = new Float32Array(vertexCount * 2);
  const longitudes = Array.from({length: columns}, (_, i) => snappedCosSin(-Math.PI + (2 * Math.PI * i) / widthSegments));
  let vertex = 0;
  for (let j = 0; j <= heightSegments; j += 1) {
    const [cosLatitude, sinLatitude] = snappedCosSin(-Math.PI / 2 + (Math.PI * j) / heightSegments);
    const ring = signedPower(cosLatitude, e1);
    const height = signedPower(sinLatitude, e1);
    const normalRing = signedPower(cosLatitude, 2 - e1);
    const normalHeight = signedPower(sinLatitude, 2 - e1);
    for (let i = 0; i < columns; i += 1) {
      const [cosLongitude, sinLongitude] = longitudes[i];
      const x = radiusX * ring * signedPower(cosLongitude, e2);
      const y = radiusY * height;
      const z = radiusZ * ring * signedPower(sinLongitude, e2);
      let nx = (normalRing * signedPower(cosLongitude, 2 - e2)) / radiusX;
      let ny = normalHeight / radiusY;
      let nz = (normalRing * signedPower(sinLongitude, 2 - e2)) / radiusZ;
      let length = Math.hypot(nx, ny, nz);
      if (!(length > 0 && Number.isFinite(length))) {
        // A cusp (an exponent above 2) has no normal; use the ellipsoid normal of the point instead.
        nx = x / (radiusX * radiusX);
        ny = y / (radiusY * radiusY);
        nz = z / (radiusZ * radiusZ);
        length = Math.hypot(nx, ny, nz);
      }
      positions.set([x, y, z], vertex * 3);
      normals.set([nx / length, ny / length, nz / length], vertex * 3);
      uvs.set([i / widthSegments, j / heightSegments], vertex * 2);
      vertex += 1;
    }
  }
  const indexCount = 6 * widthSegments * (heightSegments - 1);
  const indices = vertexCount > 65535 ? new Uint32Array(indexCount) : new Uint16Array(indexCount);
  let index = 0;
  for (let j = 0; j < heightSegments; j += 1) {
    for (let i = 0; i < widthSegments; i += 1) {
      const a = j * columns + i;
      const b = a + 1;
      const d = a + columns;
      const c = d + 1;
      // a -> d climbs in latitude and d -> c turns in longitude, so (a, d, c) faces outward; the pole rows keep the
      // one triangle that is not collapsed onto the pole.
      if (j !== heightSegments - 1) {
        indices.set([a, d, c], index);
        index += 3;
      }
      if (j !== 0) {
        indices.set([a, c, b], index);
        index += 3;
      }
    }
  }
  return {positions, normals, uvs, indices};
}

/** A THREE.BufferGeometry of the superellipsoid with position, normal and uv attributes and an index. */
export function createSuperellipsoidGeometry(THREE, options = {}) {
  const data = superellipsoidData(options);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(data.positions, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(data.normals, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(data.uvs, 2));
  geometry.setIndex(new THREE.BufferAttribute(data.indices, 1));
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}
