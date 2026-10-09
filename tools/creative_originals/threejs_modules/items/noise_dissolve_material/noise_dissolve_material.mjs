// Noise dissolve for three.js: fractal value noise in object space decides which fragments survive a threshold, and a
// glowing burn edge follows the dissolve front. The noise is built on a 32-bit integer hash, so the GLSL and the
// JavaScript mirror give the same field, bit for bit at the lattice points. Original Baltor implementation; three.js
// is passed in, nothing is imported.

/** Default options of createNoiseDissolveMaterial. Colours are linear RGB triples. */
export const NOISE_DISSOLVE_DEFAULTS = Object.freeze({
  color: Object.freeze([0.72, 0.74, 0.78]),
  threshold: 0.45,
  edgeWidth: 0.06,
  edgeColor: Object.freeze([1, 0.42, 0.08]),
  edgeIntensity: 3,
  noiseScale: 2.5,
  octaves: 4,
  seed: 7,
  lightDirection: Object.freeze([0.4, 0.8, 0.45]),
  ambient: 0.3,
});

const LATTICE_OFFSET = 1048576;
const MAXIMUM_OCTAVES = 8;
const MAXIMUM_SEED = 16777215;
const MINIMUM_EDGE = 1e-4;
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

/**
 * GLSL chunk: the integer hash, lattice values, quintic-interpolated value noise, fractal sum and burn edge. Lattice
 * coordinates are offset by 2^20 before the integer-to-unsigned conversion, so they stay positive for |p| < 2^20.
 */
export const NOISE_DISSOLVE_GLSL = `
uint dissolveHash(uint x) {
  x ^= x >> 16u;
  x *= 0x7feb352du;
  x ^= x >> 15u;
  x *= 0x846ca68bu;
  x ^= x >> 16u;
  return x;
}

float dissolveLattice(ivec3 cell, uint seed) {
  uvec3 u = uvec3(cell + ivec3(${LATTICE_OFFSET}));
  uint h = dissolveHash(u.x ^ dissolveHash(u.y ^ dissolveHash(u.z ^ seed)));
  return float(h >> 8u) * (1.0 / 16777216.0);
}

float valueNoise3(vec3 p, uint seed) {
  vec3 base = floor(p);
  ivec3 cell = ivec3(base);
  vec3 f = p - base;
  vec3 w = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  float x00 = mix(dissolveLattice(cell, seed), dissolveLattice(cell + ivec3(1, 0, 0), seed), w.x);
  float x10 = mix(dissolveLattice(cell + ivec3(0, 1, 0), seed), dissolveLattice(cell + ivec3(1, 1, 0), seed), w.x);
  float x01 = mix(dissolveLattice(cell + ivec3(0, 0, 1), seed), dissolveLattice(cell + ivec3(1, 0, 1), seed), w.x);
  float x11 = mix(dissolveLattice(cell + ivec3(0, 1, 1), seed), dissolveLattice(cell + ivec3(1, 1, 1), seed), w.x);
  return mix(mix(x00, x10, w.y), mix(x01, x11, w.y), w.z);
}

float fbm3(vec3 p, float octaves, uint seed) {
  float sum = 0.0;
  float total = 0.0;
  float amplitude = 1.0;
  vec3 q = p;
  for (int i = 0; i < ${MAXIMUM_OCTAVES}; i++) {
    if (float(i) >= octaves) break;
    sum += amplitude * valueNoise3(q, seed + uint(i));
    total += amplitude;
    q *= 2.0;
    amplitude *= 0.5;
  }
  return sum / max(total, 1e-6);
}

float dissolveEdge(float noise, float threshold, float edgeWidth) {
  float width = max(edgeWidth, ${MINIMUM_EDGE.toExponential()});
  return (1.0 - smoothstep(threshold, threshold + width, noise)) * min(threshold / width, 1.0);
}
`;

/** Vertex stage: object position for the noise, world normal for the light; InstancedMesh aware. */
export const NOISE_DISSOLVE_VERTEX = `
varying vec3 vObjectPosition;
varying vec3 vWorldNormal;

void main() {
  mat4 placement = modelMatrix;
#ifdef USE_INSTANCING
  placement = modelMatrix * instanceMatrix;
#endif
  vObjectPosition = position;
  vWorldNormal = normalize(transpose(inverse(mat3(placement))) * normal);
  gl_Position = projectionMatrix * viewMatrix * placement * vec4(position, 1.0);
}
`;

/** Fragment stage: discard below the threshold, Lambert light, mix toward the glowing edge colour near the front. */
export const NOISE_DISSOLVE_FRAGMENT = `
uniform vec3 uColor;
uniform float uThreshold;
uniform float uEdgeWidth;
uniform vec3 uEdgeColor;
uniform float uEdgeIntensity;
uniform float uNoiseScale;
uniform float uOctaves;
uniform float uSeed;
uniform vec3 uLightDirection;
uniform float uAmbient;
varying vec3 vObjectPosition;
varying vec3 vWorldNormal;
${NOISE_DISSOLVE_GLSL}
void main() {
  float noise = fbm3(vObjectPosition * uNoiseScale, uOctaves, uint(uSeed));
  if (noise < uThreshold) discard;
  vec3 normal = normalize(vWorldNormal) * (gl_FrontFacing ? 1.0 : -1.0);
  float diffuse = max(dot(normal, normalize(uLightDirection)), 0.0);
  vec3 lit = uColor * (uAmbient + (1.0 - uAmbient) * diffuse);
  float edge = dissolveEdge(noise, uThreshold, uEdgeWidth);
  gl_FragColor = vec4(mix(lit, uEdgeColor * uEdgeIntensity, edge), 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

function hash32(value) {
  let x = value >>> 0;
  x = (x ^ (x >>> 16)) >>> 0;
  x = Math.imul(x, 0x7feb352d) >>> 0;
  x = (x ^ (x >>> 15)) >>> 0;
  x = Math.imul(x, 0x846ca68b) >>> 0;
  return (x ^ (x >>> 16)) >>> 0;
}

function lattice(ix, iy, iz, seed) {
  const h = hash32(((ix + LATTICE_OFFSET) >>> 0) ^ hash32(((iy + LATTICE_OFFSET) >>> 0)
    ^ hash32(((iz + LATTICE_OFFSET) >>> 0) ^ seed)));
  return (h >>> 8) / 16777216;
}

function mix(a, b, t) {
  return a * (1 - t) + b * t;
}

function fade(t) {
  return t * t * t * (t * (t * 6 - 15) + 10);
}

function checkSeed(seed) {
  if (!Number.isInteger(seed) || seed < 0 || seed > MAXIMUM_SEED) {
    throw new RangeError(`seed must be an integer from 0 to ${MAXIMUM_SEED}, got ${seed}`);
  }
  return seed;
}

function checkPoint(x, y, z) {
  for (const value of [x, y, z]) {
    if (!(typeof value === 'number' && Math.abs(value) < LATTICE_OFFSET)) {
      throw new RangeError(`noise coordinates must be finite numbers with magnitude below ${LATTICE_OFFSET}`);
    }
  }
}

/** CPU mirror of the GLSL value noise: a smooth field in [0, 1) with quintic interpolation between hashed lattice values. */
export function valueNoise3(x, y, z, seed = 0) {
  checkPoint(x, y, z);
  checkSeed(seed);
  const bx = Math.floor(x);
  const by = Math.floor(y);
  const bz = Math.floor(z);
  const wx = fade(x - bx);
  const wy = fade(y - by);
  const wz = fade(z - bz);
  const x00 = mix(lattice(bx, by, bz, seed), lattice(bx + 1, by, bz, seed), wx);
  const x10 = mix(lattice(bx, by + 1, bz, seed), lattice(bx + 1, by + 1, bz, seed), wx);
  const x01 = mix(lattice(bx, by, bz + 1, seed), lattice(bx + 1, by, bz + 1, seed), wx);
  const x11 = mix(lattice(bx, by + 1, bz + 1, seed), lattice(bx + 1, by + 1, bz + 1, seed), wx);
  return mix(mix(x00, x10, wy), mix(x01, x11, wy), wz);
}

/**
 * CPU mirror of the GLSL fractal sum: octaves of valueNoise3, each at twice the frequency, half the amplitude and the
 * next seed, normalized by the total amplitude so the result stays in [0, 1).
 */
export function fbm3(x, y, z, octaves = 4, seed = 0) {
  if (!Number.isInteger(octaves) || octaves < 1 || octaves > MAXIMUM_OCTAVES) {
    throw new RangeError(`octaves must be an integer from 1 to ${MAXIMUM_OCTAVES}, got ${octaves}`);
  }
  checkSeed(seed);
  let sum = 0;
  let total = 0;
  let amplitude = 1;
  let scale = 1;
  for (let octave = 0; octave < octaves; octave += 1) {
    sum += amplitude * valueNoise3(x * scale, y * scale, z * scale, (seed + octave) >>> 0);
    total += amplitude;
    scale *= 2;
    amplitude *= 0.5;
  }
  return sum / total;
}

/**
 * CPU mirror of the burn edge: 1 at the dissolve front (noise = threshold), falling to 0 at threshold + edgeWidth, and 0
 * everywhere while the threshold is 0. A fragment with noise below the threshold is discarded (see isDissolved).
 */
export function dissolveEdge(noise, threshold, edgeWidth) {
  for (const [value, name] of [[noise, 'noise'], [threshold, 'threshold']]) {
    if (!(typeof value === 'number' && value >= 0 && value <= 1)) throw new RangeError(`${name} must be in [0, 1]`);
  }
  if (!(typeof edgeWidth === 'number' && edgeWidth >= 0 && edgeWidth <= 1)) throw new RangeError('edgeWidth must be in [0, 1]');
  const width = Math.max(edgeWidth, MINIMUM_EDGE);
  const t = Math.min(Math.max((noise - threshold) / width, 0), 1);
  return (1 - t * t * (3 - 2 * t)) * Math.min(threshold / width, 1);
}

/** Whether the shader discards a fragment with this noise value at this threshold. */
export function isDissolved(noise, threshold) {
  if (!(Number.isFinite(noise) && Number.isFinite(threshold))) throw new TypeError('noise and threshold must be numbers');
  return noise < threshold;
}

function colour(THREE, value, name) {
  if (Array.isArray(value) && value.length === 3 && value.every(Number.isFinite)) {
    return new THREE.Color(value[0], value[1], value[2]);
  }
  if (typeof value === 'number' || typeof value === 'string' || (value && value.isColor)) return new THREE.Color(value);
  throw new TypeError(`${name} must be a linear RGB triple, a hex number, a CSS colour string or a THREE.Color`);
}

function inRange(value, low, high, name) {
  if (!(typeof value === 'number' && value >= low && value <= high)) {
    throw new RangeError(`${name} must be a number in [${low}, ${high}], got ${value}`);
  }
  return value;
}

/**
 * A double-sided THREE.ShaderMaterial that dissolves the mesh. Options (all optional) are the keys of
 * NOISE_DISSOLVE_DEFAULTS; an unknown key throws TypeError. Animate uniforms.uThreshold from 0 (whole) to 1 (gone).
 */
export function createNoiseDissolveMaterial(THREE, options = {}) {
  for (const key of Object.keys(options)) {
    if (!own(NOISE_DISSOLVE_DEFAULTS, key)) throw new TypeError(`unknown noise dissolve option ${key}`);
  }
  const settings = {...NOISE_DISSOLVE_DEFAULTS, ...options};
  if (!Number.isInteger(settings.octaves) || settings.octaves < 1 || settings.octaves > MAXIMUM_OCTAVES) {
    throw new RangeError(`octaves must be an integer from 1 to ${MAXIMUM_OCTAVES}`);
  }
  const light = settings.lightDirection;
  if (!(Array.isArray(light) && light.length === 3 && light.every(Number.isFinite))) {
    throw new TypeError('lightDirection must be an [x, y, z] array');
  }
  const length = Math.hypot(light[0], light[1], light[2]);
  if (!(length > 0)) throw new RangeError('lightDirection must not be the zero vector');
  return new THREE.ShaderMaterial({
    name: 'BaltorNoiseDissolveMaterial',
    uniforms: {
      uColor: {value: colour(THREE, settings.color, 'color')},
      uThreshold: {value: inRange(settings.threshold, 0, 1, 'threshold')},
      uEdgeWidth: {value: inRange(settings.edgeWidth, 0, 1, 'edgeWidth')},
      uEdgeColor: {value: colour(THREE, settings.edgeColor, 'edgeColor')},
      uEdgeIntensity: {value: inRange(settings.edgeIntensity, 0, 32, 'edgeIntensity')},
      uNoiseScale: {value: inRange(settings.noiseScale, 1e-3, 1000, 'noiseScale')},
      uOctaves: {value: settings.octaves},
      uSeed: {value: checkSeed(settings.seed)},
      uLightDirection: {value: new THREE.Vector3(light[0] / length, light[1] / length, light[2] / length)},
      uAmbient: {value: inRange(settings.ambient, 0, 1, 'ambient')},
    },
    vertexShader: NOISE_DISSOLVE_VERTEX,
    fragmentShader: NOISE_DISSOLVE_FRAGMENT,
    side: THREE.DoubleSide,
  });
}
