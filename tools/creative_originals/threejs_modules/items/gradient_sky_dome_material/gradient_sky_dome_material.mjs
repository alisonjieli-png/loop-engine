// Gradient sky dome for three.js: a back-faced sphere whose colour runs from a ground colour below the horizon through a
// horizon colour to a zenith colour, with a soft blend across the horizon, a sun disc of a given angular radius with a
// soft edge, and a halo around it. The sky colour of any direction has an exact CPU mirror, handy for matching fog,
// lights and UI to the sky. Original Baltor implementation; three.js is passed in, nothing is imported.

/** Default options of createSkyDomeMaterial and skyColor. Colours are linear RGB; angles in degrees. */
export const SKY_DOME_DEFAULTS = Object.freeze({
  zenithColor: Object.freeze([0.12, 0.3, 0.68]),
  horizonColor: Object.freeze([0.62, 0.74, 0.86]),
  groundColor: Object.freeze([0.16, 0.15, 0.14]),
  skyExponent: 0.8,
  groundExponent: 0.6,
  horizonSoftness: 0.04,
  sunDirection: Object.freeze([0.35, 0.18, -0.92]),
  sunColor: Object.freeze([1, 0.86, 0.62]),
  sunAngularRadius: 1.2,
  sunEdgeSoftness: 0.4,
  sunIntensity: 12,
  haloSharpness: 64,
  haloStrength: 0.35,
});

const DEGREE = Math.PI / 180;
const MINIMUM_SOFTNESS = 1e-4;
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

/**
 * GLSL chunk: skyGradient (shape = sky exponent, ground exponent, horizon softness) and skySun (disc = cos of the inner
 * radius, cos of the outer radius, intensity, halo sharpness).
 */
export const SKY_DOME_GLSL = `
vec3 skyGradient(vec3 direction, vec3 zenith, vec3 horizon, vec3 ground, vec3 shape) {
  float y = normalize(direction).y;
  vec3 above = mix(horizon, zenith, pow(clamp(y, 0.0, 1.0), shape.x));
  vec3 below = mix(horizon, ground, pow(clamp(-y, 0.0, 1.0), shape.y));
  float softness = max(shape.z, ${MINIMUM_SOFTNESS.toExponential()});
  return mix(below, above, smoothstep(-softness, softness, y));
}

vec3 skySun(vec3 direction, vec3 sunDirection, vec3 sunColor, vec4 disc, float haloStrength) {
  float cosAngle = dot(normalize(direction), normalize(sunDirection));
  float inside = smoothstep(disc.y, disc.x, cosAngle);
  float halo = haloStrength * pow(max(cosAngle, 0.0), disc.w);
  return sunColor * (inside * disc.z + halo);
}
`;

/** Vertex stage: the direction from the dome's centre, in world orientation. */
export const SKY_DOME_VERTEX = `
varying vec3 vDirection;

void main() {
  vDirection = mat3(modelMatrix) * position;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

/** Fragment stage: gradient plus sun, then tone mapping and output colour space. */
export const SKY_DOME_FRAGMENT = `
uniform vec3 uZenithColor;
uniform vec3 uHorizonColor;
uniform vec3 uGroundColor;
uniform vec3 uShape;
uniform vec3 uSunDirection;
uniform vec3 uSunColor;
uniform vec4 uSunDisc;
uniform float uHaloStrength;
varying vec3 vDirection;
${SKY_DOME_GLSL}
void main() {
  vec3 colour = skyGradient(vDirection, uZenithColor, uHorizonColor, uGroundColor, uShape)
              + skySun(vDirection, uSunDirection, uSunColor, uSunDisc, uHaloStrength);
  gl_FragColor = vec4(colour, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

function triple(value, name) {
  if (!(Array.isArray(value) && value.length === 3 && value.every(Number.isFinite))) {
    throw new TypeError(`${name} must be an array of three finite numbers`);
  }
  return value;
}

function unit(value, name) {
  triple(value, name);
  const length = Math.hypot(value[0], value[1], value[2]);
  if (!(length > 0)) throw new RangeError(`${name} must not be the zero vector`);
  return value.map((component) => component / length);
}

function inRange(value, low, high, name) {
  if (!(typeof value === 'number' && value >= low && value <= high)) {
    throw new RangeError(`${name} must be a number in [${low}, ${high}], got ${value}`);
  }
  return value;
}

function smoothstep(edge0, edge1, x) {
  const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1);
  return t * t * (3 - 2 * t);
}

// Every option checked once, with the derived uniform values both the shader and the CPU mirror use.
function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!own(SKY_DOME_DEFAULTS, key)) throw new TypeError(`unknown sky dome option ${key}`);
  }
  const s = {...SKY_DOME_DEFAULTS, ...options};
  for (const name of ['zenithColor', 'horizonColor', 'groundColor', 'sunColor']) triple(s[name], name);
  const radius = inRange(s.sunAngularRadius, 0, 45, 'sunAngularRadius');
  const edge = inRange(s.sunEdgeSoftness, 0.01, 45, 'sunEdgeSoftness');
  return {
    ...s,
    shape: [inRange(s.skyExponent, 0.05, 16, 'skyExponent'), inRange(s.groundExponent, 0.05, 16, 'groundExponent'),
      inRange(s.horizonSoftness, 0, 1, 'horizonSoftness')],
    sun: unit(s.sunDirection, 'sunDirection'),
    disc: [Math.cos(radius * DEGREE), Math.cos((radius + edge) * DEGREE), inRange(s.sunIntensity, 0, 1000, 'sunIntensity'),
      inRange(s.haloSharpness, 1, 4096, 'haloSharpness')],
    halo: inRange(s.haloStrength, 0, 100, 'haloStrength'),
  };
}

/**
 * The unit direction toward a point of the sky at an elevation above the horizon and an azimuth, both in degrees.
 * Azimuth 0 looks along -Z (three.js's default forward) and 90 along +X.
 */
export function sunDirectionFromAngles(elevationDegrees, azimuthDegrees) {
  inRange(elevationDegrees, -90, 90, 'elevationDegrees');
  if (!Number.isFinite(azimuthDegrees)) throw new TypeError('azimuthDegrees must be a finite number');
  const elevation = elevationDegrees * DEGREE;
  const azimuth = azimuthDegrees * DEGREE;
  return [Math.cos(elevation) * Math.sin(azimuth), Math.sin(elevation), -Math.cos(elevation) * Math.cos(azimuth)];
}

/** CPU mirror of the dome: the linear RGB sky colour seen in a direction (any length) for the given options. */
export function skyColor(direction, options = {}) {
  const d = unit(direction, 'direction');
  const s = settingsOf(options);
  const y = d[1];
  const above = Math.min(Math.max(y, 0), 1) ** s.shape[0];
  const below = Math.min(Math.max(-y, 0), 1) ** s.shape[1];
  const softness = Math.max(s.shape[2], MINIMUM_SOFTNESS);
  const blend = smoothstep(-softness, softness, y);
  const cosAngle = d[0] * s.sun[0] + d[1] * s.sun[1] + d[2] * s.sun[2];
  const sun = smoothstep(s.disc[1], s.disc[0], cosAngle) * s.disc[2] + s.halo * Math.max(cosAngle, 0) ** s.disc[3];
  return [0, 1, 2].map((k) => {
    const sky = s.horizonColor[k] * (1 - above) + s.zenithColor[k] * above;
    const ground = s.horizonColor[k] * (1 - below) + s.groundColor[k] * below;
    return ground * (1 - blend) + sky * blend + s.sunColor[k] * sun;
  });
}

/**
 * A THREE.ShaderMaterial for a sky dome: draw it on a large sphere centred on the camera (or the scene); it renders the
 * back faces, writes no depth and ignores fog. Options (all optional) are the keys of SKY_DOME_DEFAULTS; an unknown key
 * throws TypeError.
 */
export function createSkyDomeMaterial(THREE, options = {}) {
  const s = settingsOf(options);
  const color = (value) => new THREE.Color(value[0], value[1], value[2]);
  return new THREE.ShaderMaterial({
    name: 'BaltorSkyDomeMaterial',
    uniforms: {
      uZenithColor: {value: color(s.zenithColor)},
      uHorizonColor: {value: color(s.horizonColor)},
      uGroundColor: {value: color(s.groundColor)},
      uShape: {value: new THREE.Vector3(s.shape[0], s.shape[1], s.shape[2])},
      uSunDirection: {value: new THREE.Vector3(s.sun[0], s.sun[1], s.sun[2])},
      uSunColor: {value: color(s.sunColor)},
      uSunDisc: {value: new THREE.Vector4(s.disc[0], s.disc[1], s.disc[2], s.disc[3])},
      uHaloStrength: {value: s.halo},
    },
    vertexShader: SKY_DOME_VERTEX,
    fragmentShader: SKY_DOME_FRAGMENT,
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
  });
}
