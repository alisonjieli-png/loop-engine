// Force-field shield material for three.js: a faint transparent shell with a Fresnel edge, plus up to eight impact
// ripples, rings that spread from hit points across the surface and fade out. Hits go into a ring buffer of uniform
// arrays. Original Baltor implementation; THREE is passed in, nothing is imported.

/** Default options. Colours are linear RGB; speeds and widths are in the mesh's own units. */
export const FORCE_FIELD_DEFAULTS = Object.freeze({
  color: Object.freeze([0.25, 0.62, 1.0]),
  hitColor: Object.freeze([1.0, 0.82, 0.42]),
  baseAlpha: 0.04,
  fresnelPower: 3,
  fresnelStrength: 0.85,
  rippleSpeed: 1.6,
  rippleWidth: 0.12,
  rippleLifetime: 1.4,
  rippleStrength: 1.4,
  doubleSided: false,
});

/** How many hits the shader keeps at once; the oldest is replaced first. */
export const FORCE_FIELD_MAX_HITS = 8;
const EMPTY_TIME = -1e6;

/** GLSL chunk: the brightness one ripple adds at a distance from its hit point, `age` seconds after the hit. */
export const FORCE_FIELD_GLSL = `
float rippleIntensity(float distanceFromHit, float age, float speed, float width, float lifetime, float strength) {
  if (age < 0.0 || age > lifetime) return 0.0;
  float band = (distanceFromHit - speed * age) / max(width, 1e-4);
  float fade = 1.0 - age / lifetime;
  return exp(-band * band) * fade * fade * strength;
}
`;

/** Vertex stage: object-space position for the ripples, world position and normal for the Fresnel edge. */
export const FORCE_FIELD_VERTEX = `
varying vec3 vObjectPosition;
varying vec3 vWorldPosition;
varying vec3 vWorldNormal;

void main() {
  vObjectPosition = position;
  vec4 world = modelMatrix * vec4(position, 1.0);
  vWorldPosition = world.xyz;
  vWorldNormal = normalize(transpose(inverse(mat3(modelMatrix))) * normal);
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

/** Fragment stage: base glow, Fresnel edge and the sum of the ripples, drawn additively. */
export const FORCE_FIELD_FRAGMENT = `
uniform vec3 uColor;
uniform vec3 uHitColor;
uniform float uBaseAlpha;
uniform float uFresnelPower;
uniform float uFresnelStrength;
uniform float uRippleSpeed;
uniform float uRippleWidth;
uniform float uRippleLifetime;
uniform float uRippleStrength;
uniform float uTime;
uniform vec3 uHitPoints[${FORCE_FIELD_MAX_HITS}];
uniform float uHitTimes[${FORCE_FIELD_MAX_HITS}];
varying vec3 vObjectPosition;
varying vec3 vWorldPosition;
varying vec3 vWorldNormal;
${FORCE_FIELD_GLSL}
void main() {
  vec3 normal = normalize(vWorldNormal) * (gl_FrontFacing ? 1.0 : -1.0);
  vec3 toEye = normalize(cameraPosition - vWorldPosition);
  float rim = pow(1.0 - clamp(abs(dot(normal, toEye)), 0.0, 1.0), uFresnelPower) * uFresnelStrength;
  float ripple = 0.0;
  for (int i = 0; i < ${FORCE_FIELD_MAX_HITS}; i++) {
    ripple += rippleIntensity(distance(vObjectPosition, uHitPoints[i]), uTime - uHitTimes[i], uRippleSpeed,
      uRippleWidth, uRippleLifetime, uRippleStrength);
  }
  float glow = uBaseAlpha + rim + ripple;
  vec3 colour = mix(uColor, uHitColor, clamp(ripple, 0.0, 1.0));
  gl_FragColor = vec4(colour, clamp(glow, 0.0, 1.0));
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

function settingsOf(options) {
  if (options === null || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(FORCE_FIELD_DEFAULTS, key)) throw new TypeError(`unknown force field option ${key}`);
  }
  const settings = {...FORCE_FIELD_DEFAULTS, ...options};
  for (const key of ['color', 'hitColor']) {
    const value = settings[key];
    if (!(Array.isArray(value) && value.length === 3 && value.every(Number.isFinite))) {
      throw new TypeError(`${key} must be a linear RGB triple`);
    }
  }
  const ranges = {baseAlpha: [0, 1], fresnelPower: [0.1, 16], fresnelStrength: [0, 8], rippleSpeed: [0, 1000],
    rippleWidth: [1e-4, 1000], rippleLifetime: [1e-3, 1000], rippleStrength: [0, 16]};
  for (const [key, [low, high]] of Object.entries(ranges)) {
    if (!(typeof settings[key] === 'number' && settings[key] >= low && settings[key] <= high)) {
      throw new RangeError(`${key} must be a number in [${low}, ${high}], got ${settings[key]}`);
    }
  }
  if (typeof settings.doubleSided !== 'boolean') throw new TypeError('doubleSided must be true or false');
  return settings;
}

/**
 * CPU mirror of the GLSL chunk: exp(-((distance - speed * age) / width)^2) * (1 - age / lifetime)^2 * strength for
 * 0 <= age <= lifetime, else 0. Options use the rippleSpeed, rippleWidth, rippleLifetime and rippleStrength keys.
 */
export function rippleIntensity(distanceFromHit, age, options = {}) {
  const settings = settingsOf(options);
  if (!(Number.isFinite(distanceFromHit) && Number.isFinite(age))) throw new RangeError('distance and age must be finite');
  if (age < 0 || age > settings.rippleLifetime) return 0;
  const band = (distanceFromHit - settings.rippleSpeed * age) / Math.max(settings.rippleWidth, 1e-4);
  const fade = 1 - age / settings.rippleLifetime;
  return Math.exp(-band * band) * fade * fade * settings.rippleStrength;
}

/** The shield material: transparent, additive, no depth write; set uniforms.uTime.value every frame. */
export function createForceFieldMaterial(THREE, options = {}) {
  const settings = settingsOf(options);
  const times = new Float32Array(FORCE_FIELD_MAX_HITS).fill(EMPTY_TIME);
  const material = new THREE.ShaderMaterial({
    name: 'BaltorForceFieldMaterial',
    uniforms: {
      uColor: {value: new THREE.Color(...settings.color)},
      uHitColor: {value: new THREE.Color(...settings.hitColor)},
      uBaseAlpha: {value: settings.baseAlpha},
      uFresnelPower: {value: settings.fresnelPower},
      uFresnelStrength: {value: settings.fresnelStrength},
      uRippleSpeed: {value: settings.rippleSpeed},
      uRippleWidth: {value: settings.rippleWidth},
      uRippleLifetime: {value: settings.rippleLifetime},
      uRippleStrength: {value: settings.rippleStrength},
      uTime: {value: 0},
      uHitPoints: {value: new Float32Array(FORCE_FIELD_MAX_HITS * 3)},
      uHitTimes: {value: times},
    },
    vertexShader: FORCE_FIELD_VERTEX,
    fragmentShader: FORCE_FIELD_FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: settings.doubleSided ? THREE.DoubleSide : THREE.FrontSide,
  });
  material.userData.forceFieldCursor = 0;
  return material;
}

/**
 * Record a hit at `point` (in the mesh's own space, [x, y, z] or anything with x, y and z) at `time` seconds on the
 * same clock as uTime. The oldest of the eight slots is reused; returns the slot written.
 */
export function addHit(material, point, time) {
  if (!material || !material.uniforms || !material.uniforms.uHitPoints) throw new TypeError('material is not a force field');
  const coordinates = Array.isArray(point) ? point : [point && point.x, point && point.y, point && point.z];
  if (!(coordinates.length === 3 && coordinates.every(Number.isFinite))) throw new TypeError('point must be three finite numbers');
  if (!Number.isFinite(time)) throw new RangeError('time must be finite');
  const slot = material.userData.forceFieldCursor % FORCE_FIELD_MAX_HITS;
  material.uniforms.uHitPoints.value.set(coordinates, slot * 3);
  material.uniforms.uHitTimes.value[slot] = time;
  material.userData.forceFieldCursor = slot + 1;
  return slot;
}

/** Forget every hit. */
export function clearHits(material) {
  if (!material || !material.uniforms || !material.uniforms.uHitTimes) throw new TypeError('material is not a force field');
  material.uniforms.uHitTimes.value.fill(EMPTY_TIME);
  material.userData.forceFieldCursor = 0;
  return material;
}
