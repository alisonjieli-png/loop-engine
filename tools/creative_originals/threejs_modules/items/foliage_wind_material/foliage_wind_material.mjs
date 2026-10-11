// Wind sway for grass and foliage in the vertex stage: each blade bends along the wind direction by an amount that
// grows with height to a power (roots stay put), made of two layered sines travelling along the wind plus gusts from
// integer-hash value noise, phased by where the blade stands (its instance or object origin), with a small drop that
// keeps the blade's length roughly constant, and a root-to-tip colour ramp. Original Baltor implementation; THREE is
// passed in, nothing is imported.

/** Default options. strength is the largest sideways tip offset in world units; colours are linear RGB. */
export const FOLIAGE_WIND_DEFAULTS = Object.freeze({
  direction: Object.freeze([1, 0.35]),
  strength: 0.18,
  frequency: 1.6,
  spatialFrequency: 0.45,
  gustStrength: 0.6,
  gustScale: 0.18,
  gustSpeed: 0.9,
  height: 1,
  stiffness: 2,
  rootColor: Object.freeze([0.04, 0.16, 0.035]),
  tipColor: Object.freeze([0.42, 0.72, 0.18]),
  lightDirection: Object.freeze([0.4, 1, 0.3]),
});

/** GLSL chunk: the wind uniforms the wind function reads (shared by the vertex stage and anything else using it). */
export const FOLIAGE_WIND_UNIFORMS_GLSL = `
uniform float uTime;
uniform vec2 uWindDirection;
uniform float uWindStrength;
uniform float uWindFrequency;
uniform float uSpatialFrequency;
uniform float uGustStrength;
uniform float uGustScale;
uniform float uGustSpeed;
uniform float uBladeHeight;
uniform float uStiffness;
`;

/** GLSL chunk: the gust noise and vec3 windOffset(vec3 position, vec3 anchor, float time) on the wind uniforms. */
export const FOLIAGE_WIND_GLSL = `
float windHash(int n) {
  uint h = uint(n + 1073741824) * 747796405u + 2891336453u;
  h = ((h >> ((h >> 28u) + 4u)) ^ h) * 277803737u;
  h = (h >> 22u) ^ h;
  return float(h) / 4294967295.0;
}

float windGust(float x) {
  float cell = floor(x);
  float f = x - cell;
  int index = int(cell);
  return mix(windHash(index), windHash(index + 1), f * f * (3.0 - 2.0 * f));
}

vec3 windOffset(vec3 position, vec3 anchor, float time) {
  float h = clamp(position.y / uBladeHeight, 0.0, 1.0);
  float weight = pow(h, uStiffness);
  float along = dot(anchor.xz, uWindDirection);
  float phase = time * uWindFrequency - along * uSpatialFrequency;
  float sway = 0.65 * sin(phase) + 0.35 * sin(phase * 2.17 + 1.3);
  float gust = windGust(along * uGustScale - time * uGustSpeed);
  float amount = uWindStrength * weight * (sway + gust * uGustStrength);
  return vec3(uWindDirection.x * amount, -(amount * amount) / (2.0 * uBladeHeight), uWindDirection.y * amount);
}
`;

/** Vertex stage: place the vertex (InstancedMesh aware), add the wind in world space, pass the height for colour. */
export const FOLIAGE_WIND_VERTEX = `
${FOLIAGE_WIND_UNIFORMS_GLSL}
varying float vHeight;
varying vec3 vWorldNormal;
${FOLIAGE_WIND_GLSL}
void main() {
  mat4 placement = modelMatrix;
#ifdef USE_INSTANCING
  placement = modelMatrix * instanceMatrix;
#endif
  vec3 anchor = (placement * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
  vec4 world = placement * vec4(position, 1.0);
  world.xyz += windOffset(position, anchor, uTime);
  vHeight = clamp(position.y / uBladeHeight, 0.0, 1.0);
  vWorldNormal = normalize(mat3(placement) * normal);
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

/** Fragment stage: root-to-tip colour with simple two-sided light, tone mapping and output colour space. */
export const FOLIAGE_WIND_FRAGMENT = `
uniform vec3 uRootColor;
uniform vec3 uTipColor;
uniform vec3 uLightDirection;
varying float vHeight;
varying vec3 vWorldNormal;

void main() {
  vec3 colour = mix(uRootColor, uTipColor, vHeight);
  float light = 0.55 + 0.45 * abs(dot(normalize(vWorldNormal), normalize(uLightDirection)));
  gl_FragColor = vec4(colour * light, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

function isVector(value, size) {
  return Array.isArray(value) && value.length === size && value.every(Number.isFinite);
}

function settingsOf(options) {
  if (options === null || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(FOLIAGE_WIND_DEFAULTS, key)) throw new TypeError(`unknown foliage wind option ${key}`);
  }
  const settings = {...FOLIAGE_WIND_DEFAULTS, ...options};
  if (!isVector(settings.direction, 2) || !(Math.hypot(...settings.direction) > 0)) {
    throw new TypeError('direction must be a non-zero [x, z] pair');
  }
  for (const key of ['rootColor', 'tipColor', 'lightDirection']) {
    if (!isVector(settings[key], 3)) throw new TypeError(`${key} must be three finite numbers`);
  }
  const ranges = {strength: [0, 100], frequency: [0, 100], spatialFrequency: [0, 100], gustStrength: [0, 10],
    gustScale: [0, 100], gustSpeed: [0, 100], height: [1e-3, 1e4], stiffness: [0.5, 8]};
  for (const [key, [low, high]] of Object.entries(ranges)) {
    if (!(typeof settings[key] === 'number' && settings[key] >= low && settings[key] <= high)) {
      throw new RangeError(`${key} must be a number in [${low}, ${high}], got ${settings[key]}`);
    }
  }
  const size = Math.hypot(...settings.direction);
  return {...settings, direction: [settings.direction[0] / size, settings.direction[1] / size]};
}

function windHash(n) {
  let h = (Math.imul((n + 1073741824) >>> 0, 747796405) + 2891336453) >>> 0;
  h = Math.imul(((h >>> ((h >>> 28) + 4)) ^ h) >>> 0, 277803737) >>> 0;
  h = ((h >>> 22) ^ h) >>> 0;
  return h / 4294967295;
}

/** CPU mirror of the gust noise: value noise in [0, 1] on integer cells, smoothstep between hashed cell values. */
export function windGustNoise(x) {
  if (!Number.isFinite(x)) throw new RangeError(`x must be finite, got ${x}`);
  const cell = Math.floor(x);
  const f = x - cell;
  const a = windHash(cell);
  const b = windHash(cell + 1);
  return a + (b - a) * (f * f * (3 - 2 * f));
}

/**
 * CPU mirror of windOffset: the world-space offset [x, y, z] of a vertex at object-space `position` on a blade whose
 * origin stands at world `anchor`, at `time` seconds. Zero at the root (y = 0), largest at y = height.
 */
export function windOffset(position, anchor, time, options = {}) {
  const settings = settingsOf(options);
  if (!isVector(position, 3) || !isVector(anchor, 3)) throw new TypeError('position and anchor must be [x, y, z]');
  if (!Number.isFinite(time)) throw new RangeError(`time must be finite, got ${time}`);
  const [dx, dz] = settings.direction;
  const h = Math.min(Math.max(position[1] / settings.height, 0), 1);
  const weight = h ** settings.stiffness;
  const along = anchor[0] * dx + anchor[2] * dz;
  const phase = time * settings.frequency - along * settings.spatialFrequency;
  const sway = 0.65 * Math.sin(phase) + 0.35 * Math.sin(phase * 2.17 + 1.3);
  const gust = windGustNoise(along * settings.gustScale - time * settings.gustSpeed);
  const amount = settings.strength * weight * (sway + gust * settings.gustStrength);
  return [dx * amount, -(amount * amount) / (2 * settings.height), dz * amount];
}

/** The uniform values for a material or a probe that includes FOLIAGE_WIND_UNIFORMS_GLSL and the fragment stage. */
export function foliageWindUniforms(THREE, options = {}) {
  const settings = settingsOf(options);
  return {
    uTime: {value: 0},
    uWindDirection: {value: new THREE.Vector2(settings.direction[0], settings.direction[1])},
    uWindStrength: {value: settings.strength},
    uWindFrequency: {value: settings.frequency},
    uSpatialFrequency: {value: settings.spatialFrequency},
    uGustStrength: {value: settings.gustStrength},
    uGustScale: {value: settings.gustScale},
    uGustSpeed: {value: settings.gustSpeed},
    uBladeHeight: {value: settings.height},
    uStiffness: {value: settings.stiffness},
    uRootColor: {value: new THREE.Color(...settings.rootColor)},
    uTipColor: {value: new THREE.Color(...settings.tipColor)},
    uLightDirection: {value: new THREE.Vector3(...settings.lightDirection)},
  };
}

/** The foliage material (double-sided); set uniforms.uTime.value every frame. Works on Mesh and InstancedMesh. */
export function createFoliageWindMaterial(THREE, options = {}) {
  return new THREE.ShaderMaterial({
    name: 'BaltorFoliageWindMaterial',
    uniforms: foliageWindUniforms(THREE, options),
    vertexShader: FOLIAGE_WIND_VERTEX,
    fragmentShader: FOLIAGE_WIND_FRAGMENT,
    side: THREE.DoubleSide,
  });
}
