// Gooch shading for three.js: the cool-to-warm technical illustration model. Light does not darken toward black;
// it shifts hue from a warm tone (facing the light) to a cool tone (facing away), so shape stays readable in the
// shadowed half. A white highlight and a dark silhouette band finish the look. Original Baltor implementation;
// three.js is passed in, nothing is imported.

/** Default options of createGoochMaterial. Colours are linear RGB triples. */
export const GOOCH_DEFAULTS = Object.freeze({
  baseColor: Object.freeze([0.75, 0.3, 0.2]),
  coolColor: Object.freeze([0, 0, 0.55]),
  warmColor: Object.freeze([0.3, 0.3, 0]),
  alpha: 0.25,
  beta: 0.5,
  highlightColor: Object.freeze([1, 1, 1]),
  shininess: 32,
  highlightStrength: 0.6,
  silhouetteWidth: 0.18,
  silhouetteSoftness: 0.06,
  silhouetteColor: Object.freeze([0.03, 0.03, 0.05]),
  lightDirection: Object.freeze([0.5, 0.8, 0.4]),
});

const MINIMUM_WIDTH = 1e-4;
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

/** GLSL chunk: the cool-to-warm tone and the silhouette band. */
export const GOOCH_GLSL = `
vec3 goochColor(float nDotL, vec3 base, vec3 cool, vec3 warm, float alpha, float beta) {
  float t = (1.0 + nDotL) * 0.5;
  return t * (warm + beta * base) + (1.0 - t) * (cool + alpha * base);
}

float goochSilhouette(float nDotV, float width, float softness) {
  float fade = max(softness, ${MINIMUM_WIDTH.toExponential()});
  return (1.0 - smoothstep(width, width + fade, abs(nDotV))) * step(${MINIMUM_WIDTH.toExponential()}, width);
}
`;

/** Vertex stage: world-space normal and position; honours InstancedMesh through USE_INSTANCING. */
export const GOOCH_VERTEX = `
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

/** Fragment stage: Gooch tone, Phong highlight toward white, silhouette band toward a dark colour. */
export const GOOCH_FRAGMENT = `
uniform vec3 uBaseColor;
uniform vec3 uCoolColor;
uniform vec3 uWarmColor;
uniform float uAlpha;
uniform float uBeta;
uniform vec3 uHighlightColor;
uniform float uShininess;
uniform float uHighlightStrength;
uniform float uSilhouetteWidth;
uniform float uSilhouetteSoftness;
uniform vec3 uSilhouetteColor;
uniform vec3 uLightDirection;
varying vec3 vWorldNormal;
varying vec3 vWorldPosition;
${GOOCH_GLSL}
void main() {
  vec3 normal = normalize(vWorldNormal) * (gl_FrontFacing ? 1.0 : -1.0);
  vec3 toLight = normalize(uLightDirection);
  vec3 toEye = normalize(cameraPosition - vWorldPosition);
  vec3 colour = goochColor(dot(normal, toLight), uBaseColor, uCoolColor, uWarmColor, uAlpha, uBeta);
  float highlight = pow(max(dot(reflect(-toLight, normal), toEye), 0.0), uShininess) * uHighlightStrength;
  colour = mix(colour, uHighlightColor, clamp(highlight, 0.0, 1.0));
  colour = mix(colour, uSilhouetteColor, goochSilhouette(dot(normal, toEye), uSilhouetteWidth, uSilhouetteSoftness));
  gl_FragColor = vec4(colour, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

function triple(value, name) {
  if (!(Array.isArray(value) && value.length === 3 && value.every(Number.isFinite))) {
    throw new TypeError(`${name} must be a linear RGB triple`);
  }
  return value;
}

function inRange(value, low, high, name) {
  if (!(typeof value === 'number' && value >= low && value <= high)) {
    throw new RangeError(`${name} must be a number in [${low}, ${high}], got ${value}`);
  }
  return value;
}

/**
 * CPU mirror of the Gooch tone: with t = (1 + nDotL) / 2, t * (warm + beta * base) + (1 - t) * (cool + alpha * base), as
 * a linear RGB triple. nDotL = 1 faces the light, -1 faces away.
 */
export function goochColor(nDotL, base, cool, warm, alpha, beta) {
  inRange(nDotL, -1, 1, 'nDotL');
  triple(base, 'base');
  triple(cool, 'cool');
  triple(warm, 'warm');
  inRange(alpha, 0, 1, 'alpha');
  inRange(beta, 0, 1, 'beta');
  const t = (1 + nDotL) * 0.5;
  return [0, 1, 2].map((k) => t * (warm[k] + beta * base[k]) + (1 - t) * (cool[k] + alpha * base[k]));
}

/**
 * CPU mirror of the silhouette band: 1 where |N.V| is below width (the outline), fading to 0 at width + softness, and
 * 0 everywhere when width is 0.
 */
export function goochSilhouette(nDotV, width, softness) {
  inRange(nDotV, -1, 1, 'nDotV');
  inRange(width, 0, 1, 'width');
  inRange(softness, 0, 1, 'softness');
  if (width < MINIMUM_WIDTH) return 0;
  const fade = Math.max(softness, MINIMUM_WIDTH);
  const t = Math.min(Math.max((Math.abs(nDotV) - width) / fade, 0), 1);
  return 1 - t * t * (3 - 2 * t);
}

function colour(THREE, value, name) {
  if (Array.isArray(value) && value.length === 3 && value.every(Number.isFinite)) {
    return new THREE.Color(value[0], value[1], value[2]);
  }
  if (typeof value === 'number' || typeof value === 'string' || (value && value.isColor)) return new THREE.Color(value);
  throw new TypeError(`${name} must be a linear RGB triple, a hex number, a CSS colour string or a THREE.Color`);
}

/**
 * A THREE.ShaderMaterial with Gooch shading. Options (all optional) are the keys of GOOCH_DEFAULTS; an unknown key
 * throws TypeError. Set silhouetteWidth to 0 to drop the outline band.
 */
export function createGoochMaterial(THREE, options = {}) {
  for (const key of Object.keys(options)) {
    if (!own(GOOCH_DEFAULTS, key)) throw new TypeError(`unknown gooch option ${key}`);
  }
  const s = {...GOOCH_DEFAULTS, ...options};
  const light = s.lightDirection;
  if (!(Array.isArray(light) && light.length === 3 && light.every(Number.isFinite) && Math.hypot(...light) > 0)) {
    throw new TypeError('lightDirection must be a non-zero [x, y, z] array');
  }
  const length = Math.hypot(light[0], light[1], light[2]);
  return new THREE.ShaderMaterial({
    name: 'BaltorGoochMaterial',
    uniforms: {
      uBaseColor: {value: colour(THREE, s.baseColor, 'baseColor')},
      uCoolColor: {value: colour(THREE, s.coolColor, 'coolColor')},
      uWarmColor: {value: colour(THREE, s.warmColor, 'warmColor')},
      uAlpha: {value: inRange(s.alpha, 0, 1, 'alpha')},
      uBeta: {value: inRange(s.beta, 0, 1, 'beta')},
      uHighlightColor: {value: colour(THREE, s.highlightColor, 'highlightColor')},
      uShininess: {value: inRange(s.shininess, 1, 1024, 'shininess')},
      uHighlightStrength: {value: inRange(s.highlightStrength, 0, 4, 'highlightStrength')},
      uSilhouetteWidth: {value: inRange(s.silhouetteWidth, 0, 1, 'silhouetteWidth')},
      uSilhouetteSoftness: {value: inRange(s.silhouetteSoftness, 0, 1, 'silhouetteSoftness')},
      uSilhouetteColor: {value: colour(THREE, s.silhouetteColor, 'silhouetteColor')},
      uLightDirection: {value: new THREE.Vector3(light[0] / length, light[1] / length, light[2] / length)},
    },
    vertexShader: GOOCH_VERTEX,
    fragmentShader: GOOCH_FRAGMENT,
  });
}
