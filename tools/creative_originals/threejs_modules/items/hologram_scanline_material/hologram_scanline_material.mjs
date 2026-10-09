// Hologram material for three.js: a transparent, additive projection with world-space scanlines that scroll, a facing
// ratio edge, stepped flicker and horizontal glitch bands that jump in the vertex stage. Flicker and glitch come from a
// 32-bit integer hash, so the GLSL and the JavaScript mirrors agree exactly. Original Baltor implementation; three.js
// is passed in, nothing is imported.

/** Default options of createHologramMaterial. Colours are linear RGB triples. */
export const HOLOGRAM_DEFAULTS = Object.freeze({
  color: Object.freeze([0.25, 0.85, 1]),
  scanDensity: 30,
  scanSpeed: 0.5,
  scanSharpness: 6,
  baseGlow: 0.25,
  fresnelPower: 2,
  fresnelStrength: 1.2,
  flickerRate: 12,
  flickerDepth: 0.25,
  glitchBands: 6,
  glitchRate: 4,
  glitchChance: 0.12,
  glitchStrength: 0.06,
  opacity: 0.9,
  seed: 3,
});

const BAND_OFFSET = 1048576;
const MAXIMUM_SEED = 16777215;
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

/**
 * GLSL chunk shared by both stages: the integer hash, the scanline profile, the flicker factor and the glitch offset.
 * Band indices are offset by 2^20 before the integer-to-unsigned conversion, so heights stay valid for |y * bands| < 2^20.
 */
export const HOLOGRAM_GLSL = `
uint hologramHash(uint x) {
  x ^= x >> 16u;
  x *= 0x7feb352du;
  x ^= x >> 15u;
  x *= 0x846ca68bu;
  x ^= x >> 16u;
  return x;
}

float hologramUnit(uint x) {
  return float(hologramHash(x) >> 8u) * (1.0 / 16777216.0);
}

float scanlineIntensity(float height, float time, float density, float speed, float sharpness) {
  float phase = height * density - time * speed;
  return pow(max(0.5 + 0.5 * cos(6.283185307179586 * phase), 0.0), sharpness);
}

float hologramFlicker(float time, float rate, float depth, uint seed) {
  uint tick = uint(int(floor(max(time, 0.0) * rate)));
  return 1.0 - depth * hologramUnit(tick ^ seed);
}

float glitchOffset(float height, float time, float bands, float rate, float chance, float strength, uint seed) {
  uint band = uint(int(floor(height * bands)) + ${BAND_OFFSET});
  uint tick = uint(int(floor(max(time, 0.0) * rate)));
  uint key = hologramHash(band ^ hologramHash(tick ^ seed));
  float pick = float(key >> 8u) * (1.0 / 16777216.0);
  float amount = hologramUnit(key) * 2.0 - 1.0;
  return pick < chance ? amount * strength : 0.0;
}
`;

/** Vertex stage: world position shifted sideways in glitching bands; InstancedMesh aware. */
export const HOLOGRAM_VERTEX = `
uniform float uTime;
uniform float uGlitchBands;
uniform float uGlitchRate;
uniform float uGlitchChance;
uniform float uGlitchStrength;
uniform float uSeed;
varying vec3 vWorldPosition;
varying vec3 vWorldNormal;
${HOLOGRAM_GLSL}
void main() {
  mat4 placement = modelMatrix;
#ifdef USE_INSTANCING
  placement = modelMatrix * instanceMatrix;
#endif
  vec4 world = placement * vec4(position, 1.0);
  world.x += glitchOffset(world.y, uTime, uGlitchBands, uGlitchRate, uGlitchChance, uGlitchStrength, uint(uSeed));
  vWorldPosition = world.xyz;
  vWorldNormal = normalize(transpose(inverse(mat3(placement))) * normal);
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

/** Fragment stage: scanlines over a base glow plus the facing-ratio edge, times the flicker, written additively. */
export const HOLOGRAM_FRAGMENT = `
uniform vec3 uColor;
uniform float uScanDensity;
uniform float uScanSpeed;
uniform float uScanSharpness;
uniform float uBaseGlow;
uniform float uFresnelPower;
uniform float uFresnelStrength;
uniform float uFlickerRate;
uniform float uFlickerDepth;
uniform float uOpacity;
uniform float uTime;
uniform float uSeed;
varying vec3 vWorldPosition;
varying vec3 vWorldNormal;
${HOLOGRAM_GLSL}
void main() {
  vec3 normal = normalize(vWorldNormal);
  vec3 toEye = normalize(cameraPosition - vWorldPosition);
  float edge = pow(max(1.0 - abs(dot(normal, toEye)), 0.0), uFresnelPower) * uFresnelStrength;
  float scan = scanlineIntensity(vWorldPosition.y, uTime, uScanDensity, uScanSpeed, uScanSharpness);
  float flicker = hologramFlicker(uTime, uFlickerRate, uFlickerDepth, uint(uSeed));
  float brightness = (uBaseGlow + (1.0 - uBaseGlow) * scan + edge) * flicker;
  gl_FragColor = vec4(uColor * brightness, uOpacity * clamp(brightness, 0.0, 1.0));
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

function unit(value) {
  return (hash32(value) >>> 8) / 16777216;
}

function finite(value, name) {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError(`${name} must be a finite number`);
  return value;
}

function checkSeed(seed) {
  if (!Number.isInteger(seed) || seed < 0 || seed > MAXIMUM_SEED) {
    throw new RangeError(`seed must be an integer from 0 to ${MAXIMUM_SEED}, got ${seed}`);
  }
  return seed;
}

/**
 * CPU mirror of the scanline profile: (0.5 + 0.5 cos(2 pi (height * density - time * speed)))^sharpness, 1 on a line and
 * 0 half way between lines. Lines move up by speed / density world units per second.
 */
export function scanlineIntensity(height, time, density, speed, sharpness) {
  finite(height, 'height');
  finite(time, 'time');
  finite(density, 'density');
  finite(speed, 'speed');
  if (!(typeof sharpness === 'number' && sharpness > 0 && sharpness <= 64)) throw new RangeError('sharpness must be in (0, 64]');
  return Math.max(0.5 + 0.5 * Math.cos(2 * Math.PI * (height * density - time * speed)), 0) ** sharpness;
}

/** CPU mirror of the flicker: 1 - depth * a hashed value in [0, 1), held for each 1 / rate seconds. */
export function hologramFlicker(time, rate, depth, seed) {
  finite(time, 'time');
  finite(rate, 'rate');
  if (!(typeof depth === 'number' && depth >= 0 && depth <= 1)) throw new RangeError('depth must be in [0, 1]');
  const tick = Math.floor(Math.max(time, 0) * rate) >>> 0;
  return 1 - depth * unit(tick ^ checkSeed(seed));
}

/**
 * CPU mirror of the glitch: the sideways offset (world units, in [-strength, strength]) of the band that holds this
 * height at this time. About `chance` of the bands are displaced at a time; the pattern changes rate times a second.
 */
export function glitchOffset(height, time, bands, rate, chance, strength, seed) {
  finite(height, 'height');
  finite(time, 'time');
  finite(bands, 'bands');
  finite(rate, 'rate');
  finite(strength, 'strength');
  if (!(typeof chance === 'number' && chance >= 0 && chance <= 1)) throw new RangeError('chance must be in [0, 1]');
  const index = Math.floor(height * bands);
  if (Math.abs(index) >= BAND_OFFSET) throw new RangeError(`height * bands must stay below ${BAND_OFFSET} in magnitude`);
  const band = (index + BAND_OFFSET) >>> 0;
  const tick = Math.floor(Math.max(time, 0) * rate) >>> 0;
  const key = hash32(band ^ hash32(tick ^ checkSeed(seed)));
  const pick = (key >>> 8) / 16777216;
  const amount = unit(key) * 2 - 1;
  return pick < chance ? amount * strength : 0;
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
 * A transparent, additive, double-sided THREE.ShaderMaterial. Options (all optional) are the keys of HOLOGRAM_DEFAULTS;
 * an unknown key throws TypeError. Set uniforms.uTime.value to the elapsed seconds every frame.
 */
export function createHologramMaterial(THREE, options = {}) {
  for (const key of Object.keys(options)) {
    if (!own(HOLOGRAM_DEFAULTS, key)) throw new TypeError(`unknown hologram option ${key}`);
  }
  const settings = {...HOLOGRAM_DEFAULTS, ...options};
  return new THREE.ShaderMaterial({
    name: 'BaltorHologramMaterial',
    uniforms: {
      uColor: {value: colour(THREE, settings.color, 'color')},
      uScanDensity: {value: inRange(settings.scanDensity, 0, 1000, 'scanDensity')},
      uScanSpeed: {value: inRange(settings.scanSpeed, -100, 100, 'scanSpeed')},
      uScanSharpness: {value: inRange(settings.scanSharpness, 0.1, 64, 'scanSharpness')},
      uBaseGlow: {value: inRange(settings.baseGlow, 0, 1, 'baseGlow')},
      uFresnelPower: {value: inRange(settings.fresnelPower, 0.1, 16, 'fresnelPower')},
      uFresnelStrength: {value: inRange(settings.fresnelStrength, 0, 8, 'fresnelStrength')},
      uFlickerRate: {value: inRange(settings.flickerRate, 0, 120, 'flickerRate')},
      uFlickerDepth: {value: inRange(settings.flickerDepth, 0, 1, 'flickerDepth')},
      uGlitchBands: {value: inRange(settings.glitchBands, 0, 1000, 'glitchBands')},
      uGlitchRate: {value: inRange(settings.glitchRate, 0, 120, 'glitchRate')},
      uGlitchChance: {value: inRange(settings.glitchChance, 0, 1, 'glitchChance')},
      uGlitchStrength: {value: inRange(settings.glitchStrength, 0, 10, 'glitchStrength')},
      uOpacity: {value: inRange(settings.opacity, 0, 1, 'opacity')},
      uTime: {value: 0},
      uSeed: {value: checkSeed(settings.seed)},
    },
    vertexShader: HOLOGRAM_VERTEX,
    fragmentShader: HOLOGRAM_FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
  });
}
