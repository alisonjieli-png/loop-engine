// Terrain splat material for three.js: four layers (sand, grass, rock, snow) blended per pixel from world height and
// slope, with smooth bands and height boundaries jittered by an integer-hash value noise so they do not run in straight
// contour lines. Layer colours are procedural with a fine noise variation. The weights have an exact CPU mirror that sums
// to 1. Original Baltor implementation; three.js is passed in, nothing is imported.

/** Default options of createTerrainSplatMaterial. Heights and jitter are in world units; colours are linear RGB. */
export const TERRAIN_SPLAT_DEFAULTS = Object.freeze({
  sandLevel: 0.15,
  snowLevel: 1.6,
  band: 0.12,
  rockSlope: 0.45,
  slopeBand: 0.08,
  jitter: 0.25,
  noiseScale: 1.5,
  seed: 11,
  sandColor: Object.freeze([0.76, 0.66, 0.46]),
  grassColor: Object.freeze([0.22, 0.42, 0.15]),
  rockColor: Object.freeze([0.38, 0.35, 0.33]),
  snowColor: Object.freeze([0.93, 0.95, 0.98]),
  detail: 0.18,
  lightDirection: Object.freeze([0.5, 0.8, 0.3]),
  ambient: 0.35,
});

const WEIGHT_KEYS = Object.freeze(['sandLevel', 'snowLevel', 'band', 'rockSlope', 'slopeBand', 'jitter']);
const LATTICE_OFFSET = 1048576;
const MAXIMUM_SEED = 16777215;
const MINIMUM_BAND = 1e-4;
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

/**
 * GLSL chunk: the integer hash, 2D value noise and the four layer weights (sand, grass, rock, snow), which sum to 1.
 */
export const TERRAIN_SPLAT_GLSL = `
uint splatHash(uint x) {
  x ^= x >> 16u;
  x *= 0x7feb352du;
  x ^= x >> 15u;
  x *= 0x846ca68bu;
  x ^= x >> 16u;
  return x;
}

float splatLattice(ivec2 cell, uint seed) {
  uvec2 u = uvec2(cell + ivec2(${LATTICE_OFFSET}));
  return float(splatHash(u.x ^ splatHash(u.y ^ seed)) >> 8u) * (1.0 / 16777216.0);
}

float valueNoise2(vec2 p, uint seed) {
  vec2 base = floor(p);
  ivec2 cell = ivec2(base);
  vec2 f = p - base;
  vec2 w = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  float bottom = mix(splatLattice(cell, seed), splatLattice(cell + ivec2(1, 0), seed), w.x);
  float top = mix(splatLattice(cell + ivec2(0, 1), seed), splatLattice(cell + ivec2(1, 1), seed), w.x);
  return mix(bottom, top, w.y);
}

vec4 splatWeights(float height, float slope, float noiseValue, float sandLevel, float snowLevel, float band,
                  float rockSlope, float slopeBand, float jitter) {
  float bandWidth = max(band, ${MINIMUM_BAND.toExponential()});
  float slopeWidth = max(slopeBand, ${MINIMUM_BAND.toExponential()});
  float h = height + (noiseValue - 0.5) * jitter;
  float sand = 1.0 - smoothstep(sandLevel - bandWidth, sandLevel + bandWidth, h);
  float snow = smoothstep(snowLevel - bandWidth, snowLevel + bandWidth, h);
  float grass = max(1.0 - sand - snow, 0.0);
  float rock = smoothstep(rockSlope - slopeWidth, rockSlope + slopeWidth, slope);
  float rest = (1.0 - rock) / (sand + grass + snow);
  return vec4(sand * rest, grass * rest, rock, snow * rest);
}
`;

/** Vertex stage: world position and normal; honours InstancedMesh through USE_INSTANCING. */
export const TERRAIN_SPLAT_VERTEX = `
varying vec3 vWorldPosition;
varying vec3 vWorldNormal;

void main() {
  mat4 placement = modelMatrix;
#ifdef USE_INSTANCING
  placement = modelMatrix * instanceMatrix;
#endif
  vec4 world = placement * vec4(position, 1.0);
  vWorldPosition = world.xyz;
  vWorldNormal = normalize(transpose(inverse(mat3(placement))) * normal);
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

/** Fragment stage: layer weights from height, slope and noise; procedural layer colours; Lambert light. */
export const TERRAIN_SPLAT_FRAGMENT = `
uniform float uSandLevel;
uniform float uSnowLevel;
uniform float uBand;
uniform float uRockSlope;
uniform float uSlopeBand;
uniform float uJitter;
uniform float uNoiseScale;
uniform float uSeed;
uniform vec3 uSandColor;
uniform vec3 uGrassColor;
uniform vec3 uRockColor;
uniform vec3 uSnowColor;
uniform float uDetail;
uniform vec3 uLightDirection;
uniform float uAmbient;
varying vec3 vWorldPosition;
varying vec3 vWorldNormal;
${TERRAIN_SPLAT_GLSL}
void main() {
  vec3 normal = normalize(vWorldNormal) * (gl_FrontFacing ? 1.0 : -1.0);
  float slope = clamp(1.0 - normal.y, 0.0, 1.0);
  uint seed = uint(uSeed);
  float jitterNoise = valueNoise2(vWorldPosition.xz * uNoiseScale, seed);
  vec4 weights = splatWeights(vWorldPosition.y, slope, jitterNoise, uSandLevel, uSnowLevel, uBand, uRockSlope,
                              uSlopeBand, uJitter);
  float fine = valueNoise2(vWorldPosition.xz * uNoiseScale * 7.0, seed + 1u) - 0.5;
  float strata = valueNoise2(vec2(vWorldPosition.x + vWorldPosition.z, vWorldPosition.y * 6.0) * uNoiseScale, seed + 2u) - 0.5;
  vec3 albedo = weights.x * uSandColor * (1.0 + uDetail * fine)
              + weights.y * uGrassColor * (1.0 + 1.4 * uDetail * fine)
              + weights.z * uRockColor * (1.0 + 2.0 * uDetail * strata)
              + weights.w * uSnowColor * (1.0 + 0.3 * uDetail * fine);
  float diffuse = max(dot(normal, normalize(uLightDirection)), 0.0);
  gl_FragColor = vec4(albedo * (uAmbient + (1.0 - uAmbient) * diffuse), 1.0);
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

function lattice(ix, iz, seed) {
  return (hash32(((ix + LATTICE_OFFSET) >>> 0) ^ hash32(((iz + LATTICE_OFFSET) >>> 0) ^ seed)) >>> 8) / 16777216;
}

function mix(a, b, t) {
  return a * (1 - t) + b * t;
}

function fade(t) {
  return t * t * t * (t * (t * 6 - 15) + 10);
}

function smoothstep(edge0, edge1, x) {
  const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1);
  return t * t * (3 - 2 * t);
}

function checkSeed(seed) {
  if (!Number.isInteger(seed) || seed < 0 || seed > MAXIMUM_SEED) {
    throw new RangeError(`seed must be an integer from 0 to ${MAXIMUM_SEED}, got ${seed}`);
  }
  return seed;
}

/** CPU mirror of the GLSL 2D value noise in [0, 1): quintic interpolation of hashed lattice values. */
export function valueNoise2(x, z, seed = 0) {
  if (!(Number.isFinite(x) && Number.isFinite(z) && Math.abs(x) < LATTICE_OFFSET && Math.abs(z) < LATTICE_OFFSET)) {
    throw new RangeError(`noise coordinates must be finite with magnitude below ${LATTICE_OFFSET}`);
  }
  checkSeed(seed);
  const bx = Math.floor(x);
  const bz = Math.floor(z);
  const wx = fade(x - bx);
  const wz = fade(z - bz);
  const bottom = mix(lattice(bx, bz, seed), lattice(bx + 1, bz, seed), wx);
  const top = mix(lattice(bx, bz + 1, seed), lattice(bx + 1, bz + 1, seed), wx);
  return mix(bottom, top, wz);
}

/**
 * CPU mirror of the layer weights [sand, grass, rock, snow] (they sum to 1) for a world height, a slope (1 - normal.y:
 * 0 flat, 1 vertical) and a jitter noise sample in [0, 1] (0.5 shifts nothing). settings may hold any of sandLevel,
 * snowLevel, band, rockSlope, slopeBand and jitter; the rest come from TERRAIN_SPLAT_DEFAULTS.
 */
export function splatWeights(height, slope, settings = {}, noiseValue = 0.5) {
  for (const key of Object.keys(settings)) {
    if (!WEIGHT_KEYS.includes(key)) throw new TypeError(`unknown splat weight setting ${key}`);
  }
  if (![height, slope, noiseValue].every(Number.isFinite)) throw new TypeError('height, slope and noiseValue must be numbers');
  const s = {...TERRAIN_SPLAT_DEFAULTS, ...settings};
  const band = Math.max(s.band, MINIMUM_BAND);
  const slopeBand = Math.max(s.slopeBand, MINIMUM_BAND);
  const h = height + (noiseValue - 0.5) * s.jitter;
  const sand = 1 - smoothstep(s.sandLevel - band, s.sandLevel + band, h);
  const snow = smoothstep(s.snowLevel - band, s.snowLevel + band, h);
  const grass = Math.max(1 - sand - snow, 0);
  const rock = smoothstep(s.rockSlope - slopeBand, s.rockSlope + slopeBand, slope);
  const rest = (1 - rock) / (sand + grass + snow);
  return [sand * rest, grass * rest, rock, snow * rest];
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
 * A THREE.ShaderMaterial that paints a terrain mesh by height and slope. Options (all optional) are the keys of
 * TERRAIN_SPLAT_DEFAULTS; an unknown key throws TypeError. The mesh needs smooth vertex normals.
 */
export function createTerrainSplatMaterial(THREE, options = {}) {
  for (const key of Object.keys(options)) {
    if (!own(TERRAIN_SPLAT_DEFAULTS, key)) throw new TypeError(`unknown terrain splat option ${key}`);
  }
  const s = {...TERRAIN_SPLAT_DEFAULTS, ...options};
  if (!(typeof s.sandLevel === 'number' && typeof s.snowLevel === 'number' && s.sandLevel < s.snowLevel)) {
    throw new RangeError('sandLevel must be below snowLevel');
  }
  const light = s.lightDirection;
  if (!(Array.isArray(light) && light.length === 3 && light.every(Number.isFinite) && Math.hypot(...light) > 0)) {
    throw new TypeError('lightDirection must be a non-zero [x, y, z] array');
  }
  const length = Math.hypot(light[0], light[1], light[2]);
  return new THREE.ShaderMaterial({
    name: 'BaltorTerrainSplatMaterial',
    uniforms: {
      uSandLevel: {value: inRange(s.sandLevel, -1e6, 1e6, 'sandLevel')},
      uSnowLevel: {value: inRange(s.snowLevel, -1e6, 1e6, 'snowLevel')},
      uBand: {value: inRange(s.band, 0, 1e6, 'band')},
      uRockSlope: {value: inRange(s.rockSlope, 0, 1, 'rockSlope')},
      uSlopeBand: {value: inRange(s.slopeBand, 0, 1, 'slopeBand')},
      uJitter: {value: inRange(s.jitter, 0, 1e6, 'jitter')},
      uNoiseScale: {value: inRange(s.noiseScale, 1e-4, 1e4, 'noiseScale')},
      uSeed: {value: checkSeed(s.seed)},
      uSandColor: {value: colour(THREE, s.sandColor, 'sandColor')},
      uGrassColor: {value: colour(THREE, s.grassColor, 'grassColor')},
      uRockColor: {value: colour(THREE, s.rockColor, 'rockColor')},
      uSnowColor: {value: colour(THREE, s.snowColor, 'snowColor')},
      uDetail: {value: inRange(s.detail, 0, 1, 'detail')},
      uLightDirection: {value: new THREE.Vector3(light[0] / length, light[1] / length, light[2] / length)},
      uAmbient: {value: inRange(s.ambient, 0, 1, 'ambient')},
    },
    vertexShader: TERRAIN_SPLAT_VERTEX,
    fragmentShader: TERRAIN_SPLAT_FRAGMENT,
  });
}
