// Triplanar texture mapping for three.js: project one texture (or a built-in checker) along the three axes in world or
// object space and blend the three projections by the surface normal raised to a sharpness power, so meshes without
// good UVs (terrain, rocks, scaled boxes, generated shapes) get an even texel density. Original Baltor implementation;
// three.js is passed in, nothing is imported.

/** Default options of createTriplanarMaterial. Colours are linear RGB triples. */
export const TRIPLANAR_DEFAULTS = Object.freeze({
  map: null,
  scale: 1,
  sharpness: 4,
  space: 'world',
  checkerColors: Object.freeze([Object.freeze([0.85, 0.82, 0.75]), Object.freeze([0.16, 0.2, 0.28])]),
  tint: Object.freeze([1, 1, 1]),
  lightDirection: Object.freeze([0.45, 0.8, 0.4]),
  ambient: 0.35,
});

const SPACES = Object.freeze({world: 0, object: 1});
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

/**
 * GLSL chunk: the blend weights, the three planar coordinates (oriented so no projection is mirrored) and the checker.
 */
export const TRIPLANAR_GLSL = `
vec3 triplanarWeights(vec3 normal, float sharpness) {
  vec3 weights = pow(abs(normal), vec3(sharpness));
  return weights / max(weights.x + weights.y + weights.z, 1e-6);
}

void triplanarCoordinates(vec3 position, vec3 normal, float scale, out vec2 onX, out vec2 onY, out vec2 onZ) {
  vec3 p = position * scale;
  vec3 side = vec3(normal.x < 0.0 ? -1.0 : 1.0, normal.y < 0.0 ? -1.0 : 1.0, normal.z < 0.0 ? -1.0 : 1.0);
  onX = vec2(-p.z * side.x, p.y);
  onY = vec2(p.x, -p.z * side.y);
  onZ = vec2(p.x * side.z, p.y);
}

float triplanarChecker(vec2 coordinate) {
  return mod(floor(coordinate.x) + floor(coordinate.y), 2.0);
}
`;

/** Vertex stage: world and object position and normal; honours InstancedMesh through USE_INSTANCING. */
export const TRIPLANAR_VERTEX = `
varying vec3 vWorldPosition;
varying vec3 vWorldNormal;
varying vec3 vObjectPosition;
varying vec3 vObjectNormal;

void main() {
  mat4 placement = modelMatrix;
#ifdef USE_INSTANCING
  placement = modelMatrix * instanceMatrix;
#endif
  vec4 world = placement * vec4(position, 1.0);
  vWorldPosition = world.xyz;
  vWorldNormal = normalize(transpose(inverse(mat3(placement))) * normal);
  vObjectPosition = position;
  vObjectNormal = normal;
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

/** Fragment stage: three projections of uMap (or the checker) blended by the normal, then Lambert light. */
export const TRIPLANAR_FRAGMENT = `
uniform sampler2D uMap;
uniform float uHasMap;
uniform float uScale;
uniform float uSharpness;
uniform float uObjectSpace;
uniform vec3 uCheckerA;
uniform vec3 uCheckerB;
uniform vec3 uTint;
uniform vec3 uLightDirection;
uniform float uAmbient;
varying vec3 vWorldPosition;
varying vec3 vWorldNormal;
varying vec3 vObjectPosition;
varying vec3 vObjectNormal;
${TRIPLANAR_GLSL}
vec3 planarColour(vec2 coordinate) {
  if (uHasMap > 0.5) return texture2D(uMap, coordinate).rgb;
  return mix(uCheckerA, uCheckerB, triplanarChecker(coordinate));
}

void main() {
  vec3 position = mix(vWorldPosition, vObjectPosition, uObjectSpace);
  vec3 normal = normalize(mix(vWorldNormal, vObjectNormal, uObjectSpace));
  vec3 weights = triplanarWeights(normal, uSharpness);
  vec2 onX;
  vec2 onY;
  vec2 onZ;
  triplanarCoordinates(position, normal, uScale, onX, onY, onZ);
  vec3 colour = weights.x * planarColour(onX) + weights.y * planarColour(onY) + weights.z * planarColour(onZ);
  vec3 lit = normalize(vWorldNormal) * (gl_FrontFacing ? 1.0 : -1.0);
  float diffuse = max(dot(lit, normalize(uLightDirection)), 0.0);
  gl_FragColor = vec4(colour * uTint * (uAmbient + (1.0 - uAmbient) * diffuse), 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

function vector3(value, name) {
  if (!(Array.isArray(value) && value.length === 3 && value.every(Number.isFinite))) {
    throw new TypeError(`${name} must be an [x, y, z] array of finite numbers`);
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
 * CPU mirror of the blend weights: |n|^sharpness per axis, divided by their sum, as [x, y, z]. Pass a unit normal.
 */
export function triplanarWeights(normal, sharpness) {
  vector3(normal, 'normal');
  inRange(sharpness, 1, 32, 'sharpness');
  const weights = normal.map((component) => Math.abs(component) ** sharpness);
  const sum = Math.max(weights[0] + weights[1] + weights[2], 1e-6);
  return weights.map((weight) => weight / sum);
}

/**
 * CPU mirror of the planar coordinates: [[u, v] seen along X, [u, v] along Y, [u, v] along Z] for a point and its
 * normal at a given texture scale. Each projection is flipped on the negative side so no face shows a mirror image.
 */
export function triplanarCoordinates(position, normal, scale) {
  vector3(position, 'position');
  vector3(normal, 'normal');
  if (!(typeof scale === 'number' && scale > 0 && Number.isFinite(scale))) throw new RangeError('scale must be positive');
  const [x, y, z] = position.map((component) => component * scale);
  const side = normal.map((component) => (component < 0 ? -1 : 1));
  return [[-z * side[0], y], [x, -z * side[1]], [x * side[2], y]];
}

/** CPU mirror of the built-in checker: 0 or 1 by the parity of floor(u) + floor(v). */
export function triplanarChecker(u, v) {
  if (!(Number.isFinite(u) && Number.isFinite(v))) throw new TypeError('u and v must be finite numbers');
  const sum = Math.floor(u) + Math.floor(v);
  return sum - 2 * Math.floor(sum / 2);
}

function colour(THREE, value, name) {
  if (Array.isArray(value) && value.length === 3 && value.every(Number.isFinite)) {
    return new THREE.Color(value[0], value[1], value[2]);
  }
  if (typeof value === 'number' || typeof value === 'string' || (value && value.isColor)) return new THREE.Color(value);
  throw new TypeError(`${name} must be a linear RGB triple, a hex number, a CSS colour string or a THREE.Color`);
}

/**
 * A THREE.ShaderMaterial with triplanar mapping. Options (all optional) are the keys of TRIPLANAR_DEFAULTS; an unknown
 * key throws TypeError. map is a THREE.Texture (give it RepeatWrapping) or null for the built-in checker; space
 * 'world' keeps the texture fixed in the world, 'object' makes it move and scale with the mesh.
 */
export function createTriplanarMaterial(THREE, options = {}) {
  for (const key of Object.keys(options)) {
    if (!own(TRIPLANAR_DEFAULTS, key)) throw new TypeError(`unknown triplanar option ${key}`);
  }
  const settings = {...TRIPLANAR_DEFAULTS, ...options};
  if (settings.map !== null && !(settings.map && settings.map.isTexture)) {
    throw new TypeError('map must be a THREE.Texture or null');
  }
  if (!own(SPACES, settings.space)) throw new RangeError(`space must be one of ${Object.keys(SPACES).join(', ')}`);
  if (!(Array.isArray(settings.checkerColors) && settings.checkerColors.length === 2)) {
    throw new TypeError('checkerColors must be two colours');
  }
  const light = vector3(settings.lightDirection, 'lightDirection');
  const length = Math.hypot(light[0], light[1], light[2]);
  if (!(length > 0)) throw new RangeError('lightDirection must not be the zero vector');
  if (!(typeof settings.scale === 'number' && settings.scale > 0 && settings.scale <= 1000)) {
    throw new RangeError(`scale must be in (0, 1000], got ${settings.scale}`);
  }
  return new THREE.ShaderMaterial({
    name: 'BaltorTriplanarMaterial',
    uniforms: {
      uMap: {value: settings.map},
      uHasMap: {value: settings.map ? 1 : 0},
      uScale: {value: settings.scale},
      uSharpness: {value: inRange(settings.sharpness, 1, 32, 'sharpness')},
      uObjectSpace: {value: SPACES[settings.space]},
      uCheckerA: {value: colour(THREE, settings.checkerColors[0], 'checkerColors[0]')},
      uCheckerB: {value: colour(THREE, settings.checkerColors[1], 'checkerColors[1]')},
      uTint: {value: colour(THREE, settings.tint, 'tint')},
      uLightDirection: {value: new THREE.Vector3(light[0] / length, light[1] / length, light[2] / length)},
      uAmbient: {value: inRange(settings.ambient, 0, 1, 'ambient')},
    },
    vertexShader: TRIPLANAR_VERTEX,
    fragmentShader: TRIPLANAR_FRAGMENT,
  });
}
