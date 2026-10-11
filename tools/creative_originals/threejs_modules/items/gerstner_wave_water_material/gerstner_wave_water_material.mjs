// Gerstner wave water for three.js: up to four trochoidal waves displace a horizontal plane in the vertex stage, the
// fragment stage computes the analytic normal and the compression of the surface (the Jacobian of the horizontal
// displacement) per pixel, and shades by facing (deep and shallow colours, sky reflection), sun glint and crest foam.
// The same wave sum runs on the CPU for buoyancy. Original Baltor implementation; three.js is passed in.

const TAU = 2 * Math.PI;
const MAXIMUM_WAVES = 4;

/** Default options of createGerstnerWaterMaterial. Colours are linear RGB triples; directions are [x, z]. */
export const GERSTNER_WATER_DEFAULTS = Object.freeze({
  waves: Object.freeze([
    Object.freeze({direction: Object.freeze([1, 0.2]), wavelength: 6, steepness: 0.22, speed: 1.6}),
    Object.freeze({direction: Object.freeze([-0.4, 1]), wavelength: 3.5, steepness: 0.18, speed: 1.2}),
    Object.freeze({direction: Object.freeze([0.7, -0.6]), wavelength: 2.1, steepness: 0.14, speed: 0.9}),
    Object.freeze({direction: Object.freeze([-0.9, -0.3]), wavelength: 1.3, steepness: 0.1, speed: 0.7}),
  ]),
  deepColor: Object.freeze([0.01, 0.07, 0.13]),
  shallowColor: Object.freeze([0.05, 0.32, 0.38]),
  skyColor: Object.freeze([0.55, 0.7, 0.85]),
  sunDirection: Object.freeze([-0.4, 0.5, -0.75]),
  sunColor: Object.freeze([1, 0.92, 0.75]),
  shininess: 180,
  foamColor: Object.freeze([0.92, 0.96, 1]),
  foamThreshold: 0.45,
  foamSoftness: 0.15,
});

const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

/**
 * GLSL chunk: the wave sum, its analytic normal and the Jacobian of the horizontal displacement. Each wave is a vec4
 * (direction x, direction z, wavelength, steepness) with its phase speed in the matching component of `speeds`.
 */
export const GERSTNER_WATER_GLSL = `
vec3 gerstnerOffset(vec2 xz, float time, vec4 waves[4], vec4 speeds, float count) {
  vec3 offset = vec3(0.0);
  for (int i = 0; i < 4; i++) {
    if (float(i) >= count) break;
    float k = 6.283185307179586 / waves[i].z;
    float amplitude = waves[i].w / k;
    float phase = k * (dot(waves[i].xy, xz) - speeds[i] * time);
    float c = cos(phase);
    offset.x += waves[i].x * amplitude * c;
    offset.y += amplitude * sin(phase);
    offset.z += waves[i].y * amplitude * c;
  }
  return offset;
}

vec3 gerstnerNormal(vec2 xz, float time, vec4 waves[4], vec4 speeds, float count) {
  vec3 alongX = vec3(1.0, 0.0, 0.0);
  vec3 alongZ = vec3(0.0, 0.0, 1.0);
  for (int i = 0; i < 4; i++) {
    if (float(i) >= count) break;
    float k = 6.283185307179586 / waves[i].z;
    float phase = k * (dot(waves[i].xy, xz) - speeds[i] * time);
    float q = waves[i].w;
    float s = sin(phase);
    float c = cos(phase);
    vec2 d = waves[i].xy;
    alongX += vec3(-q * d.x * d.x * s, q * d.x * c, -q * d.x * d.y * s);
    alongZ += vec3(-q * d.x * d.y * s, q * d.y * c, -q * d.y * d.y * s);
  }
  return normalize(cross(alongZ, alongX));
}

float gerstnerJacobian(vec2 xz, float time, vec4 waves[4], vec4 speeds, float count) {
  float xx = 1.0;
  float zz = 1.0;
  float xz2 = 0.0;
  for (int i = 0; i < 4; i++) {
    if (float(i) >= count) break;
    float k = 6.283185307179586 / waves[i].z;
    float s = sin(k * (dot(waves[i].xy, xz) - speeds[i] * time));
    float q = waves[i].w;
    vec2 d = waves[i].xy;
    xx -= q * d.x * d.x * s;
    zz -= q * d.y * d.y * s;
    xz2 -= q * d.x * d.y * s;
  }
  return xx * zz - xz2 * xz2;
}
`;

/** Vertex stage: the world position of the flat plane, displaced by the waves; the rest position goes to the pixel. */
export const GERSTNER_WATER_VERTEX = `
uniform vec4 uWaves[4];
uniform vec4 uWaveSpeeds;
uniform float uWaveCount;
uniform float uTime;
varying vec2 vRest;
varying float vHeight;
varying vec3 vWorldPosition;
${GERSTNER_WATER_GLSL}
void main() {
  vec4 world = modelMatrix * vec4(position, 1.0);
  vRest = world.xz;
  vec3 offset = gerstnerOffset(world.xz, uTime, uWaves, uWaveSpeeds, uWaveCount);
  world.xyz += offset;
  vHeight = offset.y;
  vWorldPosition = world.xyz;
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

/** Fragment stage: analytic normal, deep and shallow body colour, sky reflection, sun glint and crest foam. */
export const GERSTNER_WATER_FRAGMENT = `
uniform vec4 uWaves[4];
uniform vec4 uWaveSpeeds;
uniform float uWaveCount;
uniform float uTime;
uniform vec3 uDeepColor;
uniform vec3 uShallowColor;
uniform vec3 uSkyColor;
uniform vec3 uSunDirection;
uniform vec3 uSunColor;
uniform float uShininess;
uniform vec3 uFoamColor;
uniform float uFoamThreshold;
uniform float uFoamSoftness;
uniform float uMaxHeight;
varying vec2 vRest;
varying float vHeight;
varying vec3 vWorldPosition;
${GERSTNER_WATER_GLSL}
void main() {
  vec3 normal = gerstnerNormal(vRest, uTime, uWaves, uWaveSpeeds, uWaveCount) * (gl_FrontFacing ? 1.0 : -1.0);
  vec3 toEye = normalize(cameraPosition - vWorldPosition);
  float facing = max(dot(normal, toEye), 0.0);
  float crest = clamp(vHeight / max(uMaxHeight, 1e-4) * 0.5 + 0.5, 0.0, 1.0);
  vec3 colour = mix(uDeepColor, uShallowColor, crest);
  colour = mix(colour, uSkyColor, 0.02 + 0.98 * pow(1.0 - facing, 5.0));
  vec3 halfway = normalize(normalize(uSunDirection) + toEye);
  colour += uSunColor * pow(max(dot(normal, halfway), 0.0), uShininess);
  float jacobian = gerstnerJacobian(vRest, uTime, uWaves, uWaveSpeeds, uWaveCount);
  float foam = 1.0 - smoothstep(uFoamThreshold - uFoamSoftness, uFoamThreshold + uFoamSoftness, jacobian);
  gl_FragColor = vec4(mix(colour, uFoamColor, foam), 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

/**
 * The waves as the shader takes them: {waves: Float32Array(16) of (dx, dz, wavelength, steepness) with unit
 * directions, speeds: [4 phase speeds], count, maxHeight: the sum of amplitudes}. Refuses more than four waves, a
 * zero direction, a non-positive wavelength, steepness outside [0, 1] and a steepness sum above 1 (crests would loop).
 */
export function packGerstnerWaves(waves) {
  if (!Array.isArray(waves) || waves.length < 1 || waves.length > MAXIMUM_WAVES) {
    throw new RangeError(`waves must be an array of 1 to ${MAXIMUM_WAVES} waves`);
  }
  const packed = new Float32Array(16);
  const speeds = [0, 0, 0, 0];
  let steepnessSum = 0;
  let maxHeight = 0;
  waves.forEach((wave, index) => {
    if (!wave || typeof wave !== 'object') throw new TypeError(`wave ${index} must be an object`);
    for (const key of Object.keys(wave)) {
      if (!['direction', 'wavelength', 'steepness', 'speed'].includes(key)) throw new TypeError(`unknown wave key ${key}`);
    }
    const {direction, wavelength, steepness, speed} = wave;
    if (!(Array.isArray(direction) && direction.length === 2 && direction.every(Number.isFinite))) {
      throw new TypeError(`wave ${index} direction must be an [x, z] array`);
    }
    const length = Math.hypot(direction[0], direction[1]);
    if (!(length > 0)) throw new RangeError(`wave ${index} direction must not be zero`);
    if (!(typeof wavelength === 'number' && wavelength >= 0.01 && wavelength <= 10000)) {
      throw new RangeError(`wave ${index} wavelength must be in [0.01, 10000]`);
    }
    if (!(typeof steepness === 'number' && steepness >= 0 && steepness <= 1)) {
      throw new RangeError(`wave ${index} steepness must be in [0, 1]`);
    }
    if (!(typeof speed === 'number' && Number.isFinite(speed))) throw new TypeError(`wave ${index} speed must be a number`);
    packed.set([direction[0] / length, direction[1] / length, wavelength, steepness], index * 4);
    speeds[index] = speed;
    steepnessSum += steepness;
    maxHeight += (steepness * wavelength) / TAU;
  });
  if (steepnessSum > 1 + 1e-9) throw new RangeError(`the steepness sum ${steepnessSum} is above 1, so crests would loop`);
  return {waves: packed, speeds, count: waves.length, maxHeight};
}

function terms(waves, x, z, time) {
  if (![x, z, time].every(Number.isFinite)) throw new TypeError('x, z and time must be finite numbers');
  const packed = packGerstnerWaves(waves);
  const rows = [];
  for (let index = 0; index < packed.count; index += 1) {
    const length = Math.hypot(waves[index].direction[0], waves[index].direction[1]);
    const dx = waves[index].direction[0] / length;
    const dz = waves[index].direction[1] / length;
    const k = TAU / waves[index].wavelength;
    const phase = k * (dx * x + dz * z - waves[index].speed * time);
    rows.push({dx, dz, q: waves[index].steepness, amplitude: waves[index].steepness / k, s: Math.sin(phase), c: Math.cos(phase)});
  }
  return rows;
}

/** CPU mirror of gerstnerOffset: the [dx, dy, dz] that moves the rest point (x, 0, z) onto the surface at time t. */
export function gerstnerDisplacement(waves, x, z, time) {
  const offset = [0, 0, 0];
  for (const row of terms(waves, x, z, time)) {
    offset[0] += row.dx * row.amplitude * row.c;
    offset[1] += row.amplitude * row.s;
    offset[2] += row.dz * row.amplitude * row.c;
  }
  return offset;
}

/** CPU mirror of gerstnerNormal: the unit surface normal [nx, ny, nz] at the point displaced from rest (x, z). */
export function gerstnerNormal(waves, x, z, time) {
  const alongX = [1, 0, 0];
  const alongZ = [0, 0, 1];
  for (const {dx, dz, q, s, c} of terms(waves, x, z, time)) {
    alongX[0] -= q * dx * dx * s;
    alongX[1] += q * dx * c;
    alongX[2] -= q * dx * dz * s;
    alongZ[0] -= q * dx * dz * s;
    alongZ[1] += q * dz * c;
    alongZ[2] -= q * dz * dz * s;
  }
  const normal = [alongZ[1] * alongX[2] - alongZ[2] * alongX[1], alongZ[2] * alongX[0] - alongZ[0] * alongX[2],
    alongZ[0] * alongX[1] - alongZ[1] * alongX[0]];
  const length = Math.hypot(normal[0], normal[1], normal[2]);
  return normal.map((component) => component / length);
}

/** CPU mirror of gerstnerJacobian: 1 on flat water, smaller where crests bunch up (foam), 0 or below where they fold. */
export function gerstnerJacobian(waves, x, z, time) {
  let xx = 1;
  let zz = 1;
  let cross = 0;
  for (const {dx, dz, q, s} of terms(waves, x, z, time)) {
    xx -= q * dx * dx * s;
    zz -= q * dz * dz * s;
    cross -= q * dx * dz * s;
  }
  return xx * zz - cross * cross;
}

/**
 * Height of the surface above the world point (x, z) at time t, for buoyancy: the rest point whose displaced
 * position lands on (x, z) is found by fixed-point iteration, then its vertical offset is returned. Returns
 * {height, rest: [x0, z0], residual} where residual is the horizontal miss distance after the last iteration.
 */
export function gerstnerSurfaceHeight(waves, x, z, time, iterations = 8) {
  if (!Number.isInteger(iterations) || iterations < 1 || iterations > 64) throw new RangeError('iterations must be 1 to 64');
  let restX = x;
  let restZ = z;
  for (let step = 0; step < iterations; step += 1) {
    const [dx, , dz] = gerstnerDisplacement(waves, restX, restZ, time);
    restX = x - dx;
    restZ = z - dz;
  }
  const [dx, dy, dz] = gerstnerDisplacement(waves, restX, restZ, time);
  return {height: dy, rest: [restX, restZ], residual: Math.hypot(restX + dx - x, restZ + dz - z)};
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
 * A THREE.ShaderMaterial of Gerstner water for a horizontal plane mesh (for example PlaneGeometry rotated by -pi/2 about
 * X). Options (all optional) are the keys of GERSTNER_WATER_DEFAULTS; an unknown key throws TypeError. Advance
 * uniforms.uTime every frame; to change the waves, write packGerstnerWaves(waves) into uWaves, uWaveSpeeds, uWaveCount
 * and uMaxHeight.
 */
export function createGerstnerWaterMaterial(THREE, options = {}) {
  for (const key of Object.keys(options)) {
    if (!own(GERSTNER_WATER_DEFAULTS, key)) throw new TypeError(`unknown gerstner water option ${key}`);
  }
  const settings = {...GERSTNER_WATER_DEFAULTS, ...options};
  const packed = packGerstnerWaves(settings.waves);
  const sun = settings.sunDirection;
  if (!(Array.isArray(sun) && sun.length === 3 && sun.every(Number.isFinite) && Math.hypot(...sun) > 0)) {
    throw new TypeError('sunDirection must be a non-zero [x, y, z] array');
  }
  const sunLength = Math.hypot(sun[0], sun[1], sun[2]);
  return new THREE.ShaderMaterial({
    name: 'BaltorGerstnerWaterMaterial',
    uniforms: {
      uWaves: {value: packed.waves},
      uWaveSpeeds: {value: packed.speeds},
      uWaveCount: {value: packed.count},
      uTime: {value: 0},
      uDeepColor: {value: colour(THREE, settings.deepColor, 'deepColor')},
      uShallowColor: {value: colour(THREE, settings.shallowColor, 'shallowColor')},
      uSkyColor: {value: colour(THREE, settings.skyColor, 'skyColor')},
      uSunDirection: {value: new THREE.Vector3(sun[0] / sunLength, sun[1] / sunLength, sun[2] / sunLength)},
      uSunColor: {value: colour(THREE, settings.sunColor, 'sunColor')},
      uShininess: {value: inRange(settings.shininess, 1, 4096, 'shininess')},
      uFoamColor: {value: colour(THREE, settings.foamColor, 'foamColor')},
      uFoamThreshold: {value: inRange(settings.foamThreshold, -1, 2, 'foamThreshold')},
      uFoamSoftness: {value: inRange(settings.foamSoftness, 0.001, 1, 'foamSoftness')},
      uMaxHeight: {value: packed.maxHeight},
    },
    vertexShader: GERSTNER_WATER_VERTEX,
    fragmentShader: GERSTNER_WATER_FRAGMENT,
    side: THREE.DoubleSide,
  });
}
