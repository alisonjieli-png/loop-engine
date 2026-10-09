// Cel shading for three.js: diffuse light quantized into a fixed number of bands with soft edges, a hard specular
// spot and a lit-side rim. Original Baltor implementation; three.js is passed in, nothing is imported.

/** Default options of createToonBandMaterial. Colours are linear RGB triples. */
export const TOON_BAND_DEFAULTS = Object.freeze({
  color: Object.freeze([0.85, 0.42, 0.26]),
  shadowColor: Object.freeze([0.16, 0.11, 0.2]),
  bands: 3,
  softness: 0.03,
  lightDirection: Object.freeze([0.55, 0.75, 0.35]),
  specularColor: Object.freeze([1, 0.97, 0.9]),
  specularSize: 0.06,
  rimColor: Object.freeze([1, 0.88, 0.76]),
  rimWidth: 0.22,
  rimStrength: 0.55,
});

const MAXIMUM_BANDS = 16;
const MINIMUM_SOFTNESS = 1e-4;

/** GLSL chunk: the band function shared by the fragment shader and anything that wants the same quantization. */
export const TOON_BAND_GLSL = `
float toonBandLevel(float nDotL, float bands, float softness) {
  float edgeWidth = max(softness, ${MINIMUM_SOFTNESS.toExponential()});
  float level = 0.0;
  for (int k = 0; k < ${MAXIMUM_BANDS}; k++) {
    if (float(k) >= bands) break;
    float edge = float(k) / bands;
    level += smoothstep(edge - edgeWidth, edge + edgeWidth, nDotL);
  }
  return level / bands;
}
`;

/** Vertex stage: world-space normal and position; honours InstancedMesh through USE_INSTANCING. */
export const TOON_BAND_VERTEX = `
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

/** Fragment stage: bands, specular spot and rim, then three.js tone mapping and output colour space. */
export const TOON_BAND_FRAGMENT = `
uniform vec3 uColor;
uniform vec3 uShadowColor;
uniform float uBands;
uniform float uSoftness;
uniform vec3 uLightDirection;
uniform vec3 uSpecularColor;
uniform float uSpecularSize;
uniform vec3 uRimColor;
uniform float uRimWidth;
uniform float uRimStrength;
varying vec3 vWorldNormal;
varying vec3 vWorldPosition;
${TOON_BAND_GLSL}
void main() {
  vec3 normal = normalize(vWorldNormal) * (gl_FrontFacing ? 1.0 : -1.0);
  vec3 toLight = normalize(uLightDirection);
  vec3 toEye = normalize(cameraPosition - vWorldPosition);
  float nDotL = dot(normal, toLight);
  float edgeWidth = max(uSoftness, ${MINIMUM_SOFTNESS.toExponential()});
  vec3 colour = mix(uShadowColor, uColor, toonBandLevel(nDotL, uBands, uSoftness));
  if (uSpecularSize > 0.0) {
    float facing = dot(normal, normalize(toLight + toEye));
    float spot = smoothstep(1.0 - uSpecularSize - edgeWidth, 1.0 - uSpecularSize + edgeWidth, facing);
    colour += uSpecularColor * spot * step(0.0, nDotL);
  }
  float grazing = 1.0 - max(dot(normal, toEye), 0.0);
  float rim = smoothstep(1.0 - uRimWidth - edgeWidth, 1.0 - uRimWidth + edgeWidth, grazing);
  colour += uRimColor * rim * uRimStrength * clamp(nDotL + 0.5, 0.0, 1.0);
  gl_FragColor = vec4(colour, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

function smoothstep(edge0, edge1, x) {
  const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1);
  return t * t * (3 - 2 * t);
}

function checkBands(bands) {
  if (!Number.isInteger(bands) || bands < 1 || bands > MAXIMUM_BANDS) {
    throw new RangeError(`bands must be an integer from 1 to ${MAXIMUM_BANDS}, got ${bands}`);
  }
}

/**
 * CPU mirror of the shader's band function: the lit level (0 to 1) for a Lambert term nDotL in [-1, 1]. Edges sit at
 * k / bands for k = 0 .. bands - 1, each smoothed over +-softness, so 3 bands give the levels 0, 1/3, 2/3 and 1.
 */
export function toonBandLevel(nDotL, bands, softness) {
  checkBands(bands);
  if (!(softness >= 0 && softness <= 0.5)) throw new RangeError(`softness must be in [0, 0.5], got ${softness}`);
  const edgeWidth = Math.max(softness, MINIMUM_SOFTNESS);
  let level = 0;
  for (let k = 0; k < bands; k += 1) {
    const edge = k / bands;
    level += smoothstep(edge - edgeWidth, edge + edgeWidth, nDotL);
  }
  return level / bands;
}

/** The unit vector from a target point toward a light position, as [x, y, z] (for uLightDirection). */
export function toonLightDirection(lightPosition, targetPosition = [0, 0, 0]) {
  const x = lightPosition[0] - targetPosition[0];
  const y = lightPosition[1] - targetPosition[1];
  const z = lightPosition[2] - targetPosition[2];
  const length = Math.hypot(x, y, z);
  if (!(length > 0)) throw new RangeError('the light and its target are at the same point');
  return [x / length, y / length, z / length];
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
 * A THREE.ShaderMaterial with the toon band shading. Options (all optional) are the keys of TOON_BAND_DEFAULTS; an
 * unknown key is refused so a misspelt option never passes silently. Change the look later through
 * material.uniforms (uColor, uShadowColor, uBands, uSoftness, uLightDirection, uSpecularColor, uSpecularSize,
 * uRimColor, uRimWidth, uRimStrength).
 */
export function createToonBandMaterial(THREE, options = {}) {
  for (const key of Object.keys(options)) {
    if (!(key in TOON_BAND_DEFAULTS)) throw new TypeError(`unknown toon band option ${key}`);
  }
  const settings = {...TOON_BAND_DEFAULTS, ...options};
  checkBands(settings.bands);
  const direction = toonLightDirection(settings.lightDirection);
  return new THREE.ShaderMaterial({
    name: 'BaltorToonBandMaterial',
    uniforms: {
      uColor: {value: colour(THREE, settings.color, 'color')},
      uShadowColor: {value: colour(THREE, settings.shadowColor, 'shadowColor')},
      uBands: {value: settings.bands},
      uSoftness: {value: inRange(settings.softness, 0, 0.5, 'softness')},
      uLightDirection: {value: new THREE.Vector3(direction[0], direction[1], direction[2])},
      uSpecularColor: {value: colour(THREE, settings.specularColor, 'specularColor')},
      uSpecularSize: {value: inRange(settings.specularSize, 0, 1, 'specularSize')},
      uRimColor: {value: colour(THREE, settings.rimColor, 'rimColor')},
      uRimWidth: {value: inRange(settings.rimWidth, 0, 1, 'rimWidth')},
      uRimStrength: {value: inRange(settings.rimStrength, 0, 4, 'rimStrength')},
    },
    vertexShader: TOON_BAND_VERTEX,
    fragmentShader: TOON_BAND_FRAGMENT,
  });
}
