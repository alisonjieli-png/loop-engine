// Tone mapping pass for three.js post-processing: exposure, then one of four curves that bring high-dynamic-range
// values into [0, 1]: a plain clamp, extended Reinhard with a white point, the Narkowicz 2015 fit of the ACES curve
// and the Hable filmic curve. The curve is chosen by an integer uniform, so it can change at run time. Original
// Baltor implementation from the published formulas, with an exact CPU mirror.

/** Curve numbers for uOperator. */
export const TONEMAP_OPERATORS = Object.freeze({clamp: 0, reinhard: 1, aces: 2, hable: 3});

/** Default options of createTonemapShader, createTonemapMaterial and the CPU mirror. */
export const TONEMAP_DEFAULTS = Object.freeze({
  operator: 'aces',
  exposure: 1,
  whitePoint: 4,
});

// The Narkowicz 2015 rational fit of the ACES curve, and Hable's filmic curve parameters with its white point.
const ACES = Object.freeze({a: 2.51, b: 0.03, c: 2.43, d: 0.59, e: 0.14});
const HABLE = Object.freeze({A: 0.15, B: 0.5, C: 0.1, D: 0.2, E: 0.02, F: 0.3, W: 11.2});

const number = (value) => (Number.isInteger(value) ? `${value}.0` : `${value}`);

/** Vertex stage for a full-screen triangle or quad (three.js ShaderPass supplies one). */
export const TONEMAP_VERTEX = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

/** Fragment stage: exposure, the chosen curve, clamp, then three.js's output colour space (no tonemapping chunk). */
export const TONEMAP_FRAGMENT = `
uniform sampler2D tDiffuse;
uniform float uExposure;
uniform int uOperator;
uniform float uWhitePoint;
varying vec2 vUv;

vec3 hableCurve(vec3 x) {
  return (x * (${number(HABLE.A)} * x + ${number(HABLE.C * HABLE.B)}) + ${number(HABLE.D * HABLE.E)})
    / (x * (${number(HABLE.A)} * x + ${number(HABLE.B)}) + ${number(HABLE.D * HABLE.F)}) - ${number(HABLE.E / HABLE.F)};
}

vec3 tonemapCurve(vec3 colour) {
  vec3 x = max(colour * uExposure, 0.0);
  if (uOperator == 1) {
    return x * (1.0 + x / (uWhitePoint * uWhitePoint)) / (1.0 + x);
  }
  if (uOperator == 2) {
    return (x * (${number(ACES.a)} * x + ${number(ACES.b)})) / (x * (${number(ACES.c)} * x + ${number(ACES.d)}) + ${number(ACES.e)});
  }
  if (uOperator == 3) {
    return hableCurve(x) / hableCurve(vec3(${number(HABLE.W)}));
  }
  return x;
}

void main() {
  vec4 texel = texture2D(tDiffuse, vUv);
  gl_FragColor = vec4(clamp(tonemapCurve(texel.rgb), 0.0, 1.0), texel.a);
  #include <colorspace_fragment>
}
`;

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(TONEMAP_DEFAULTS, key)) throw new TypeError(`unknown tone mapping option ${key}`);
  }
  const settings = {...TONEMAP_DEFAULTS, ...options};
  if (!Object.prototype.hasOwnProperty.call(TONEMAP_OPERATORS, settings.operator)) {
    throw new TypeError(`operator must be one of ${Object.keys(TONEMAP_OPERATORS)}`);
  }
  if (!(typeof settings.exposure === 'number' && settings.exposure > 0 && settings.exposure <= 64)) {
    throw new RangeError(`exposure must be in (0, 64], got ${settings.exposure}`);
  }
  if (!(typeof settings.whitePoint === 'number' && settings.whitePoint >= 1 && settings.whitePoint <= 64)) {
    throw new RangeError(`whitePoint must be in [1, 64], got ${settings.whitePoint}`);
  }
  return settings;
}

/** Hable's filmic curve before white normalization: ((x (Ax + CB) + DE) / (x (Ax + B) + DF)) - E / F. */
export function hableCurve(x) {
  const {A, B, C, D, E, F} = HABLE;
  return (x * (A * x + C * B) + D * E) / (x * (A * x + B) + D * F) - E / F;
}

/** CPU mirror for one channel: max(value * exposure, 0) through the chosen curve, clamped to [0, 1]. */
export function tonemapValue(value, options = {}) {
  const settings = settingsOf(options);
  const x = Math.max(value * settings.exposure, 0);
  let mapped = x;
  const operator = TONEMAP_OPERATORS[settings.operator];
  if (operator === TONEMAP_OPERATORS.reinhard) {
    mapped = (x * (1 + x / (settings.whitePoint * settings.whitePoint))) / (1 + x);
  } else if (operator === TONEMAP_OPERATORS.aces) {
    mapped = (x * (ACES.a * x + ACES.b)) / (x * (ACES.c * x + ACES.d) + ACES.e);
  } else if (operator === TONEMAP_OPERATORS.hable) {
    mapped = hableCurve(x) / hableCurve(HABLE.W);
  }
  return Math.min(Math.max(mapped, 0), 1);
}

/** CPU mirror for a colour: tonemapValue on each channel, [r, g, b]. */
export function tonemapColor(rgb, options = {}) {
  if (!(Array.isArray(rgb) && rgb.length === 3 && rgb.every(Number.isFinite))) {
    throw new TypeError('rgb must be three finite numbers');
  }
  return rgb.map((value) => tonemapValue(value, options));
}

/**
 * A new shader definition {name, uniforms, vertexShader, fragmentShader} for three.js ShaderPass (input texture
 * uniform tDiffuse) or ShaderMaterial. Use it with renderer.toneMapping = THREE.NoToneMapping so the curve is applied
 * once, and feed it a HalfFloat or Float render target so values above 1 survive.
 */
export function createTonemapShader(options = {}) {
  const settings = settingsOf(options);
  return {
    name: 'BaltorTonemapCurvesShader',
    uniforms: {
      tDiffuse: {value: null},
      uExposure: {value: settings.exposure},
      uOperator: {value: TONEMAP_OPERATORS[settings.operator]},
      uWhitePoint: {value: settings.whitePoint},
    },
    vertexShader: TONEMAP_VERTEX,
    fragmentShader: TONEMAP_FRAGMENT,
  };
}

/** A THREE.ShaderMaterial for a full-screen pass; set uniforms.tDiffuse.value to the HDR input texture. */
export function createTonemapMaterial(THREE, options = {}) {
  const material = new THREE.ShaderMaterial(createTonemapShader(options));
  material.depthTest = false;
  material.depthWrite = false;
  material.toneMapped = false;
  return material;
}
