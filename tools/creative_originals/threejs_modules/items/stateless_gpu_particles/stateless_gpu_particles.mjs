// Stateless GPU particles for three.js: every particle's position, size and opacity are computed in the vertex stage
// from its seed and birth offset attributes and the time uniform, with no buffers updated per frame. Particles loop
// over their lifetime and draw fresh random numbers (an integer hash of seed, loop and channel) on every loop: a
// direction in a cone around +Y, a speed, a spawn point on a disc; then ballistic motion under gravity, an optional
// swirl about the Y axis, and size and opacity over life. Original Baltor implementation; THREE is passed in.

/** Default options. Lengths are in the Points object's own units, times in seconds, colours linear RGB. */
export const GPU_PARTICLES_DEFAULTS = Object.freeze({
  count: 2000,
  lifetime: 2.5,
  coneAngle: 0.35,
  speedMin: 1.8,
  speedMax: 3.2,
  gravity: Object.freeze([0, -2.4, 0]),
  swirl: 0.8,
  emitterRadius: 0.15,
  startSize: 0.18,
  endSize: 0.04,
  fadeIn: 0.08,
  fadeOut: 0.35,
  startColor: Object.freeze([1.0, 0.72, 0.3]),
  endColor: Object.freeze([0.85, 0.18, 0.28]),
  pointScale: 600,
});

const GOLDEN_FRACTION = 0.6180339887498949;
const CYCLE_OFFSET = 1073741824;
const TWO_PI = 6.283185307179586;

/** GLSL chunk: the motion and appearance uniforms the particle functions read. */
export const PARTICLE_UNIFORMS_GLSL = `
uniform float uTime;
uniform float uLifetime;
uniform float uConeAngle;
uniform float uSpeedMin;
uniform float uSpeedMax;
uniform vec3 uGravity;
uniform float uSwirl;
uniform float uEmitterRadius;
uniform float uFadeIn;
uniform float uFadeOut;
`;

/** GLSL chunk: integer-hash randoms, vec4 particleState(seed, birth, time) (position, life) and particleAlpha(life). */
export const PARTICLE_GLSL = `
uint particlePcg(uint value) {
  uint state = value * 747796405u + 2891336453u;
  uint word = ((state >> ((state >> 28u) + 4u)) ^ state) * 277803737u;
  return (word >> 22u) ^ word;
}

float particleRandom(float seed, float cycle, uint channel) {
  uint mixed = (uint(seed) * 2654435761u) ^ (uint(int(cycle) + ${CYCLE_OFFSET}) * 2246822519u) ^ (channel * 3266489917u);
  return float(particlePcg(mixed) >> 8u) / 16777216.0;
}

vec4 particleState(float seed, float birth, float time) {
  float elapsed = time - birth;
  float cycle = floor(elapsed / uLifetime);
  float age = elapsed - cycle * uLifetime;
  float cosine = mix(1.0, cos(uConeAngle), particleRandom(seed, cycle, 0u));
  float sine = sqrt(max(0.0, 1.0 - cosine * cosine));
  float around = ${TWO_PI} * particleRandom(seed, cycle, 1u);
  vec3 direction = vec3(sine * cos(around), cosine, sine * sin(around));
  float speed = mix(uSpeedMin, uSpeedMax, particleRandom(seed, cycle, 2u));
  float spawnRadius = uEmitterRadius * sqrt(particleRandom(seed, cycle, 3u));
  float spawnAngle = ${TWO_PI} * particleRandom(seed, cycle, 4u);
  vec3 start = vec3(spawnRadius * cos(spawnAngle), 0.0, spawnRadius * sin(spawnAngle));
  vec3 position = start + direction * speed * age + 0.5 * uGravity * age * age;
  float turn = uSwirl * age;
  position.xz = vec2(position.x * cos(turn) - position.z * sin(turn), position.x * sin(turn) + position.z * cos(turn));
  return vec4(position, age / uLifetime);
}

float particleAlpha(float life) {
  return smoothstep(0.0, uFadeIn, life) * (1.0 - smoothstep(1.0 - uFadeOut, 1.0, life));
}
`;

/** Vertex stage of the Points: state from the attributes, size with distance attenuation. */
export const PARTICLE_VERTEX = `
${PARTICLE_UNIFORMS_GLSL}
uniform float uStartSize;
uniform float uEndSize;
uniform float uPointScale;
attribute float aSeed;
attribute float aBirth;
varying float vAlpha;
varying float vLife;
${PARTICLE_GLSL}
void main() {
  vec4 state = particleState(aSeed, aBirth, uTime);
  vec4 view = modelViewMatrix * vec4(state.xyz, 1.0);
  gl_Position = projectionMatrix * view;
  gl_PointSize = mix(uStartSize, uEndSize, state.w) * uPointScale / max(-view.z, 1e-3);
  vAlpha = particleAlpha(state.w);
  vLife = state.w;
}
`;

/** Fragment stage: a soft round sprite whose colour moves from start to end over life. */
export const PARTICLE_FRAGMENT = `
uniform vec3 uStartColor;
uniform vec3 uEndColor;
varying float vAlpha;
varying float vLife;

void main() {
  float falloff = 1.0 - smoothstep(0.2, 0.5, length(gl_PointCoord - vec2(0.5)));
  gl_FragColor = vec4(mix(uStartColor, uEndColor, vLife), vAlpha * falloff);
  #include <colorspace_fragment>
}
`;

function triple(value, name) {
  if (!(Array.isArray(value) && value.length === 3 && value.every(Number.isFinite))) {
    throw new TypeError(`${name} must be three finite numbers`);
  }
  return value;
}

function settingsOf(options) {
  if (options === null || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(GPU_PARTICLES_DEFAULTS, key)) throw new TypeError(`unknown particle option ${key}`);
  }
  const settings = {...GPU_PARTICLES_DEFAULTS, ...options};
  if (!(Number.isInteger(settings.count) && settings.count >= 1 && settings.count <= 4194304)) {
    throw new RangeError('count must be an integer from 1 to 4194304');
  }
  const ranges = {lifetime: [0.01, 1e4], coneAngle: [0, Math.PI], speedMin: [0, 1e4], speedMax: [0, 1e4], swirl: [-100, 100],
    emitterRadius: [0, 1e4], startSize: [0, 1e4], endSize: [0, 1e4], fadeIn: [1e-3, 1], fadeOut: [1e-3, 1],
    pointScale: [1e-3, 1e6]};
  for (const [key, [low, high]] of Object.entries(ranges)) {
    if (!(typeof settings[key] === 'number' && settings[key] >= low && settings[key] <= high)) {
      throw new RangeError(`${key} must be a number in [${low}, ${high}], got ${settings[key]}`);
    }
  }
  if (settings.speedMin > settings.speedMax) throw new RangeError('speedMin must not exceed speedMax');
  triple(settings.gravity, 'gravity');
  triple(settings.startColor, 'startColor');
  triple(settings.endColor, 'endColor');
  return settings;
}

function pcg(value) {
  const state = (Math.imul(value, 747796405) + 2891336453) >>> 0;
  const word = Math.imul(((state >>> ((state >>> 28) + 4)) ^ state) >>> 0, 277803737) >>> 0;
  return ((word >>> 22) ^ word) >>> 0;
}

function random(seed, cycle, channel) {
  const mixed = (Math.imul(seed >>> 0, 2654435761) ^ Math.imul((cycle + CYCLE_OFFSET) >>> 0, 2246822519)
    ^ Math.imul(channel, 3266489917)) >>> 0;
  return (pcg(mixed) >>> 8) / 16777216;
}

function smoothstep(edge0, edge1, x) {
  const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1);
  return t * t * (3 - 2 * t);
}

/** The birth offset of particle `index`: fract(index * golden ratio) * lifetime, rounded to float32 as stored. */
export function particleBirth(index, lifetime = GPU_PARTICLES_DEFAULTS.lifetime) {
  if (!(Number.isInteger(index) && index >= 0)) throw new RangeError(`index must be a non-negative integer, got ${index}`);
  if (!(lifetime > 0)) throw new RangeError('lifetime must be positive');
  const turn = index * GOLDEN_FRACTION;
  return Math.fround((turn - Math.floor(turn)) * lifetime);
}

/**
 * CPU mirror of the vertex stage for particle `index` (seed = index, birth = particleBirth(index)) at `time`:
 * {position: [x, y, z], life, size, alpha, cycle}. life runs from 0 to 1 over each loop.
 */
export function particleState(index, time, options = {}) {
  const settings = settingsOf(options);
  if (!Number.isFinite(time)) throw new RangeError(`time must be finite, got ${time}`);
  const birth = particleBirth(index, settings.lifetime);
  const elapsed = time - birth;
  const cycle = Math.floor(elapsed / settings.lifetime);
  const age = elapsed - cycle * settings.lifetime;
  const cosine = 1 + (Math.cos(settings.coneAngle) - 1) * random(index, cycle, 0);
  const sine = Math.sqrt(Math.max(0, 1 - cosine * cosine));
  const around = TWO_PI * random(index, cycle, 1);
  const direction = [sine * Math.cos(around), cosine, sine * Math.sin(around)];
  const speed = settings.speedMin + (settings.speedMax - settings.speedMin) * random(index, cycle, 2);
  const spawnRadius = settings.emitterRadius * Math.sqrt(random(index, cycle, 3));
  const spawnAngle = TWO_PI * random(index, cycle, 4);
  const position = [0, 1, 2].map((axis) => direction[axis] * speed * age + 0.5 * settings.gravity[axis] * age * age);
  position[0] += spawnRadius * Math.cos(spawnAngle);
  position[2] += spawnRadius * Math.sin(spawnAngle);
  const turn = settings.swirl * age;
  const [x, z] = [position[0], position[2]];
  position[0] = x * Math.cos(turn) - z * Math.sin(turn);
  position[2] = x * Math.sin(turn) + z * Math.cos(turn);
  const life = age / settings.lifetime;
  const size = settings.startSize + (settings.endSize - settings.startSize) * life;
  const alpha = smoothstep(0, settings.fadeIn, life) * (1 - smoothstep(1 - settings.fadeOut, 1, life));
  return {position, life, size, alpha, cycle};
}

/** A BufferGeometry of `count` particles: a zero position attribute, aSeed = index, aBirth; bounded for culling. */
export function createParticleGeometry(THREE, options = {}) {
  const settings = settingsOf(options);
  const seeds = new Float32Array(settings.count);
  const births = new Float32Array(settings.count);
  for (let index = 0; index < settings.count; index += 1) {
    seeds[index] = index;
    births[index] = particleBirth(index, settings.lifetime);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(settings.count * 3), 3));
  geometry.setAttribute('aSeed', new THREE.BufferAttribute(seeds, 1));
  geometry.setAttribute('aBirth', new THREE.BufferAttribute(births, 1));
  const life = settings.lifetime;
  const reach = settings.emitterRadius + settings.speedMax * life + 0.5 * Math.hypot(...settings.gravity) * life * life;
  geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), reach);
  return geometry;
}

/** The additive Points material; set uniforms.uTime.value every frame and uPointScale to the viewport's scale. */
export function createParticleMaterial(THREE, options = {}) {
  const settings = settingsOf(options);
  return new THREE.ShaderMaterial({
    name: 'BaltorStatelessParticles',
    uniforms: {
      uTime: {value: 0},
      uLifetime: {value: settings.lifetime},
      uConeAngle: {value: settings.coneAngle},
      uSpeedMin: {value: settings.speedMin},
      uSpeedMax: {value: settings.speedMax},
      uGravity: {value: new THREE.Vector3(...settings.gravity)},
      uSwirl: {value: settings.swirl},
      uEmitterRadius: {value: settings.emitterRadius},
      uFadeIn: {value: settings.fadeIn},
      uFadeOut: {value: settings.fadeOut},
      uStartSize: {value: settings.startSize},
      uEndSize: {value: settings.endSize},
      uPointScale: {value: settings.pointScale},
      uStartColor: {value: new THREE.Color(...settings.startColor)},
      uEndColor: {value: new THREE.Color(...settings.endColor)},
    },
    vertexShader: PARTICLE_VERTEX,
    fragmentShader: PARTICLE_FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
}

/** THREE.Points with the geometry and the material above. */
export function createParticlePoints(THREE, options = {}) {
  const points = new THREE.Points(createParticleGeometry(THREE, options), createParticleMaterial(THREE, options));
  points.name = 'BaltorStatelessParticles';
  return points;
}
