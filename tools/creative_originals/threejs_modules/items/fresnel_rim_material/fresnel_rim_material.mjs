// Fresnel rim glow for three.js: a view-dependent rim, bias + scale * (1 - max(N.V, 0))^power, added as emission over
// a lit base colour (opaque mode) or drawn alone with additive blending on a slightly larger glow shell (additive
// mode), with an optional slow pulse. Original Baltor implementation; three.js is passed in, nothing is imported.

/** Default options of createFresnelRimMaterial. Colours are linear RGB triples. */
export const FRESNEL_RIM_DEFAULTS = Object.freeze({
  mode: 'opaque',
  baseColor: Object.freeze([0.05, 0.07, 0.12]),
  rimColor: Object.freeze([0.25, 0.85, 1]),
  power: 2.5,
  bias: 0.02,
  scale: 1.4,
  intensity: 1,
  pulseSpeed: 0,
  pulseDepth: 0.35,
  lightDirection: Object.freeze([0.4, 0.8, 0.45]),
  ambient: 0.25,
});

const MODES = Object.freeze({opaque: 0, additive: 1});
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

/** GLSL chunk: the rim term and the pulse factor, shared by the fragment stage and anything that wants the same rim. */
export const FRESNEL_RIM_GLSL = `
float fresnelRim(float cosTheta, float power, float bias, float scale) {
  return bias + scale * pow(1.0 - clamp(cosTheta, 0.0, 1.0), power);
}

float fresnelPulse(float time, float speed, float depth) {
  return 1.0 - depth * 0.5 * (1.0 - cos(time * speed));
}
`;

/** Vertex stage: world-space normal and position; honours InstancedMesh through USE_INSTANCING. */
export const FRESNEL_RIM_VERTEX = `
varying vec3 vWorldNormal;
varying vec3 vWorldPosition;

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

/** Fragment stage: the rim over a Lambert-lit base (uAdditive 0) or the rim alone as additive glow (uAdditive 1). */
export const FRESNEL_RIM_FRAGMENT = `
uniform vec3 uBaseColor;
uniform vec3 uRimColor;
uniform float uPower;
uniform float uBias;
uniform float uScale;
uniform float uIntensity;
uniform float uTime;
uniform float uPulseSpeed;
uniform float uPulseDepth;
uniform vec3 uLightDirection;
uniform float uAmbient;
uniform float uAdditive;
varying vec3 vWorldNormal;
varying vec3 vWorldPosition;
${FRESNEL_RIM_GLSL}
void main() {
  vec3 normal = normalize(vWorldNormal) * (gl_FrontFacing ? 1.0 : -1.0);
  vec3 toEye = normalize(cameraPosition - vWorldPosition);
  float rim = fresnelRim(dot(normal, toEye), uPower, uBias, uScale) * fresnelPulse(uTime, uPulseSpeed, uPulseDepth);
  if (uAdditive > 0.5) {
    gl_FragColor = vec4(uRimColor * uIntensity, clamp(rim, 0.0, 1.0));
  } else {
    float diffuse = max(dot(normal, normalize(uLightDirection)), 0.0);
    vec3 lit = uBaseColor * (uAmbient + (1.0 - uAmbient) * diffuse);
    gl_FragColor = vec4(lit + uRimColor * rim * uIntensity, 1.0);
  }
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

function finite(value, name) {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError(`${name} must be a finite number`);
  return value;
}

/**
 * CPU mirror of the shader rim: bias + scale * (1 - clamp(cosTheta, 0, 1))^power, where cosTheta is N.V. It is bias
 * where the surface faces the camera and bias + scale at the silhouette; it can pass 1 when bias + scale does.
 */
export function fresnelRim(cosTheta, power, bias, scale) {
  finite(cosTheta, 'cosTheta');
  if (!(typeof power === 'number' && power > 0 && power <= 64)) throw new RangeError(`power must be in (0, 64], got ${power}`);
  finite(bias, 'bias');
  finite(scale, 'scale');
  return bias + scale * (1 - Math.min(Math.max(cosTheta, 0), 1)) ** power;
}

/** CPU mirror of the pulse: 1 at time 0, dipping to 1 - depth and back once every 2 pi / speed seconds. */
export function fresnelPulse(time, speed, depth) {
  finite(time, 'time');
  finite(speed, 'speed');
  if (!(typeof depth === 'number' && depth >= 0 && depth <= 1)) throw new RangeError(`depth must be in [0, 1], got ${depth}`);
  return 1 - depth * 0.5 * (1 - Math.cos(time * speed));
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

function unitVector(value, name) {
  if (!(Array.isArray(value) && value.length === 3 && value.every(Number.isFinite))) {
    throw new TypeError(`${name} must be an [x, y, z] array`);
  }
  const length = Math.hypot(value[0], value[1], value[2]);
  if (!(length > 0)) throw new RangeError(`${name} must not be the zero vector`);
  return value.map((component) => component / length);
}

/**
 * A THREE.ShaderMaterial with the Fresnel rim. Options (all optional) are the keys of FRESNEL_RIM_DEFAULTS; an unknown
 * key throws TypeError. mode 'opaque' adds the rim to a Lambert-lit base colour; mode 'additive' draws only the rim with
 * additive blending, no depth write and transparency, for a glow shell. Animate the pulse through uniforms.uTime.
 */
export function createFresnelRimMaterial(THREE, options = {}) {
  for (const key of Object.keys(options)) {
    if (!own(FRESNEL_RIM_DEFAULTS, key)) throw new TypeError(`unknown fresnel rim option ${key}`);
  }
  const settings = {...FRESNEL_RIM_DEFAULTS, ...options};
  if (!own(MODES, settings.mode)) throw new RangeError(`mode must be one of ${Object.keys(MODES).join(', ')}`);
  const additive = MODES[settings.mode] === MODES.additive;
  const light = unitVector(settings.lightDirection, 'lightDirection');
  return new THREE.ShaderMaterial({
    name: 'BaltorFresnelRimMaterial',
    uniforms: {
      uBaseColor: {value: colour(THREE, settings.baseColor, 'baseColor')},
      uRimColor: {value: colour(THREE, settings.rimColor, 'rimColor')},
      uPower: {value: inRange(settings.power, 0.1, 16, 'power')},
      uBias: {value: inRange(settings.bias, 0, 1, 'bias')},
      uScale: {value: inRange(settings.scale, 0, 8, 'scale')},
      uIntensity: {value: inRange(settings.intensity, 0, 16, 'intensity')},
      uTime: {value: 0},
      uPulseSpeed: {value: inRange(settings.pulseSpeed, 0, 50, 'pulseSpeed')},
      uPulseDepth: {value: inRange(settings.pulseDepth, 0, 1, 'pulseDepth')},
      uLightDirection: {value: new THREE.Vector3(light[0], light[1], light[2])},
      uAmbient: {value: inRange(settings.ambient, 0, 1, 'ambient')},
      uAdditive: {value: additive ? 1 : 0},
    },
    vertexShader: FRESNEL_RIM_VERTEX,
    fragmentShader: FRESNEL_RIM_FRAGMENT,
    transparent: additive,
    depthWrite: !additive,
    blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
  });
}
