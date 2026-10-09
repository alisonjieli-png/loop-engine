// Depth fog pass for three.js post-processing: the depth buffer of the rendered frame (a DepthTexture) is turned back
// into view distance for a perspective or orthographic camera, and the frame is mixed toward a fog colour by
// exponential squared fog that begins at a start distance. Works after any scene render, with materials that ignore
// scene fog, and lets fog change without recompiling materials. Original Baltor implementation, with CPU mirrors of
// depth linearization, its inverse and the fog factor.

/** Default options of createDepthFogShader, createDepthFogMaterial and the CPU mirror. */
export const DEPTH_FOG_DEFAULTS = Object.freeze({
  color: Object.freeze([0.62, 0.7, 0.8]),
  density: 0.12,
  start: 0,
  near: 0.1,
  far: 100,
  orthographic: false,
});

/**
 * GLSL chunk: fogViewDistance turns a [0, 1] depth-buffer value into the distance along the view axis, fogAmount is
 * 1 - exp(-(density * max(distance - start, 0))^2).
 */
export const DEPTH_FOG_GLSL = `
float fogViewDistance(float depth, float near, float far, int orthographic) {
  if (orthographic == 1) return near + depth * (far - near);
  return near * far / (far - depth * (far - near));
}

float fogAmount(float viewDistance, float density, float start) {
  float optical = density * max(viewDistance - start, 0.0);
  return 1.0 - exp(-optical * optical);
}
`;

/** Vertex stage for a full-screen triangle or quad (three.js ShaderPass supplies one). */
export const DEPTH_FOG_VERTEX = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

/** Fragment stage: depth to distance, fog amount, mix toward the fog colour, then the output colour space. */
export const DEPTH_FOG_FRAGMENT = `
uniform sampler2D tDiffuse;
uniform sampler2D tDepth;
uniform float cameraNear;
uniform float cameraFar;
uniform int uOrthographic;
uniform vec3 uFogColor;
uniform float uDensity;
uniform float uStart;
varying vec2 vUv;
${DEPTH_FOG_GLSL}
void main() {
  vec4 texel = texture2D(tDiffuse, vUv);
  float depth = texture2D(tDepth, vUv).x;
  float amount = fogAmount(fogViewDistance(depth, cameraNear, cameraFar, uOrthographic), uDensity, uStart);
  gl_FragColor = vec4(mix(texel.rgb, uFogColor, amount), texel.a);
  #include <colorspace_fragment>
}
`;

function checkCamera(near, far) {
  if (!(typeof near === 'number' && typeof far === 'number' && near > 0 && far > near && Number.isFinite(far))) {
    throw new RangeError(`need 0 < near < far, got near ${near} and far ${far}`);
  }
}

/**
 * CPU mirror of fogViewDistance: the distance along the view axis for a depth-buffer value in [0, 1] (the WebGL
 * default depth range, no logarithmic or reversed depth). Perspective: near * far / (far - depth (far - near));
 * orthographic: near + depth (far - near).
 */
export function linearizeDepth(depth, near, far, orthographic = false) {
  checkCamera(near, far);
  if (!(depth >= 0 && depth <= 1)) throw new RangeError(`depth must be in [0, 1], got ${depth}`);
  return orthographic ? near + depth * (far - near) : (near * far) / (far - depth * (far - near));
}

/** The inverse of linearizeDepth: the depth-buffer value of a point at a view distance in [near, far]. */
export function depthFromDistance(distance, near, far, orthographic = false) {
  checkCamera(near, far);
  if (!(distance >= near && distance <= far)) throw new RangeError(`distance must be in [${near}, ${far}]`);
  return orthographic ? (distance - near) / (far - near) : (far * (distance - near)) / (distance * (far - near));
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(DEPTH_FOG_DEFAULTS, key)) throw new TypeError(`unknown depth fog option ${key}`);
  }
  const settings = {...DEPTH_FOG_DEFAULTS, ...options};
  if (!(typeof settings.density === 'number' && settings.density >= 0 && settings.density <= 10)) {
    throw new RangeError(`density must be in [0, 10], got ${settings.density}`);
  }
  if (!(typeof settings.start === 'number' && settings.start >= 0 && Number.isFinite(settings.start))) {
    throw new RangeError(`start must be a non-negative distance, got ${settings.start}`);
  }
  checkCamera(settings.near, settings.far);
  if (typeof settings.orthographic !== 'boolean') throw new TypeError('orthographic must be true or false');
  const color = settings.color;
  if (!(Array.isArray(color) && color.length === 3 && color.every(Number.isFinite))) {
    throw new TypeError('color must be a linear RGB triple');
  }
  return settings;
}

/** CPU mirror of fogAmount: 1 - exp(-(density * max(distance - start, 0))^2). */
export function fogFactor(distance, options = {}) {
  const settings = settingsOf(options);
  const optical = settings.density * Math.max(distance - settings.start, 0);
  return 1 - Math.exp(-optical * optical);
}

/** CPU mirror of the whole pass for one pixel: rgb mixed toward the fog colour by the fog at its depth value. */
export function applyDepthFogCpu(rgb, depth, options = {}) {
  const settings = settingsOf(options);
  const amount = fogFactor(linearizeDepth(depth, settings.near, settings.far, settings.orthographic), options);
  return rgb.map((value, channel) => value + (settings.color[channel] - value) * amount);
}

/**
 * A new shader definition {name, uniforms, vertexShader, fragmentShader} for three.js ShaderPass (input texture
 * uniform tDiffuse) or ShaderMaterial. Set uniforms.tDepth.value to the frame's DepthTexture and keep cameraNear and
 * cameraFar equal to the camera's.
 */
export function createDepthFogShader(options = {}) {
  const settings = settingsOf(options);
  return {
    name: 'BaltorDepthFogShader',
    uniforms: {
      tDiffuse: {value: null},
      tDepth: {value: null},
      cameraNear: {value: settings.near},
      cameraFar: {value: settings.far},
      uOrthographic: {value: settings.orthographic ? 1 : 0},
      uFogColor: {value: [...settings.color]},
      uDensity: {value: settings.density},
      uStart: {value: settings.start},
    },
    vertexShader: DEPTH_FOG_VERTEX,
    fragmentShader: DEPTH_FOG_FRAGMENT,
  };
}

/** A THREE.ShaderMaterial for a full-screen pass; set uniforms.tDiffuse and uniforms.tDepth. */
export function createDepthFogMaterial(THREE, options = {}) {
  const material = new THREE.ShaderMaterial(createDepthFogShader(options));
  material.depthTest = false;
  material.depthWrite = false;
  return material;
}
