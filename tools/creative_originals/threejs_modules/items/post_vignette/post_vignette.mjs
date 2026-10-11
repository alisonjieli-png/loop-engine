// Vignette pass for three.js post-processing: darken or tint the frame toward its edges, round in pixels or shaped
// like the frame, with a smooth band between an inner and an outer radius. Original Baltor implementation; the shader
// definition is a plain object that three.js ShaderPass and ShaderMaterial both accept, and the pass math has an
// exact CPU mirror.

/** Default options of createVignetteShader and createVignetteMaterial. */
export const VIGNETTE_DEFAULTS = Object.freeze({
  color: Object.freeze([0, 0, 0]),
  strength: 0.65,
  inner: 0.45,
  outer: 1.3,
  roundness: 1,
  aspect: 1,
});

/** Vertex stage for a full-screen triangle or quad (three.js ShaderPass supplies one). */
export const VIGNETTE_VERTEX = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

/** Fragment stage: reads tDiffuse and mixes toward uColor by the vignette amount, then the output colour space. */
export const VIGNETTE_FRAGMENT = `
uniform sampler2D tDiffuse;
uniform vec3 uColor;
uniform float uStrength;
uniform float uInner;
uniform float uOuter;
uniform float uRoundness;
uniform float uAspect;
varying vec2 vUv;

float vignetteAmount(vec2 uv, float aspect, float roundness, float inner, float outer, float strength) {
  vec2 offset = (uv - 0.5) * vec2(mix(1.0, aspect, roundness), 1.0);
  float distanceFromCentre = length(offset) * 2.0;
  return smoothstep(inner, max(outer, inner + 1e-4), distanceFromCentre) * strength;
}

void main() {
  vec4 texel = texture2D(tDiffuse, vUv);
  float amount = vignetteAmount(vUv, uAspect, uRoundness, uInner, uOuter, uStrength);
  gl_FragColor = vec4(mix(texel.rgb, uColor, amount), texel.a);
  #include <colorspace_fragment>
}
`;

function smoothstep(edge0, edge1, x) {
  const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1);
  return t * t * (3 - 2 * t);
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(VIGNETTE_DEFAULTS, key)) throw new TypeError(`unknown vignette option ${key}`);
  }
  const settings = {...VIGNETTE_DEFAULTS, ...options};
  const ranges = {strength: [0, 1], inner: [0, 4], outer: [0, 4], roundness: [0, 1], aspect: [0.01, 100]};
  for (const [key, [low, high]] of Object.entries(ranges)) {
    if (!(typeof settings[key] === 'number' && settings[key] >= low && settings[key] <= high)) {
      throw new RangeError(`${key} must be a number in [${low}, ${high}], got ${settings[key]}`);
    }
  }
  if (!(settings.outer >= settings.inner)) throw new RangeError('outer must not be smaller than inner');
  const color = settings.color;
  if (!(Array.isArray(color) && color.length === 3 && color.every(Number.isFinite))) {
    throw new TypeError('color must be a linear RGB triple');
  }
  return settings;
}

/**
 * CPU mirror of the shader: the vignette amount (0 = untouched, strength = fully uColor) at uv in [0, 1]^2. The
 * distance is 0 at the centre and 1 at the middle of the top and bottom edges; roundness 1 measures it in pixels
 * (aspect = width / height), roundness 0 stretches it with the frame.
 */
export function vignetteAmount(u, v, options = {}) {
  const settings = settingsOf(options);
  const x = (u - 0.5) * (1 + (settings.aspect - 1) * settings.roundness);
  const y = v - 0.5;
  const distance = Math.hypot(x, y) * 2;
  return smoothstep(settings.inner, Math.max(settings.outer, settings.inner + 1e-4), distance) * settings.strength;
}

/**
 * A new shader definition {name, uniforms, vertexShader, fragmentShader} for three.js ShaderPass (input texture
 * uniform tDiffuse) or ShaderMaterial. Vector uniforms are plain arrays, which three.js uploads as vec3.
 */
export function createVignetteShader(options = {}) {
  const settings = settingsOf(options);
  return {
    name: 'BaltorVignetteShader',
    uniforms: {
      tDiffuse: {value: null},
      uColor: {value: [...settings.color]},
      uStrength: {value: settings.strength},
      uInner: {value: settings.inner},
      uOuter: {value: settings.outer},
      uRoundness: {value: settings.roundness},
      uAspect: {value: settings.aspect},
    },
    vertexShader: VIGNETTE_VERTEX,
    fragmentShader: VIGNETTE_FRAGMENT,
  };
}

/** A THREE.ShaderMaterial for a full-screen pass; set uniforms.tDiffuse.value to the input texture. */
export function createVignetteMaterial(THREE, options = {}) {
  const material = new THREE.ShaderMaterial(createVignetteShader(options));
  material.depthTest = false;
  material.depthWrite = false;
  return material;
}
