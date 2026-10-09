// Separable Gaussian blur for three.js post-processing: one pass blurs along a direction with a normalized Gaussian
// kernel, and two passes (across, then up) give the full 2D blur. Neighbouring kernel taps are merged in pairs into
// single bilinear fetches placed between the two texels, which halves the texture reads without changing the result.
// The fragment shader is generated for one sigma and radius, with the taps as constant arrays; the direction and the
// texel size are uniforms. Original Baltor implementation, with a CPU reference of the discrete blur.

/** Default options of createGaussianBlurShader and createGaussianBlurMaterial. */
export const GAUSSIAN_BLUR_DEFAULTS = Object.freeze({
  sigma: 2,
  radius: 6,
  direction: Object.freeze([1, 0]),
  resolution: Object.freeze([1024, 1024]),
});

const MAXIMUM_RADIUS = 32;
const MAXIMUM_SIGMA = 16;

/** Vertex stage for a full-screen triangle or quad (three.js ShaderPass supplies one). */
export const GAUSSIAN_BLUR_VERTEX = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

function checkKernel(sigma, radius) {
  if (!(typeof sigma === 'number' && sigma > 0 && sigma <= MAXIMUM_SIGMA)) {
    throw new RangeError(`sigma must be in (0, ${MAXIMUM_SIGMA}] texels, got ${sigma}`);
  }
  if (!Number.isInteger(radius) || radius < 0 || radius > MAXIMUM_RADIUS) {
    throw new RangeError(`radius must be an integer from 0 to ${MAXIMUM_RADIUS}, got ${radius}`);
  }
}

/**
 * The one-sided discrete Gaussian kernel [w0, w1, ..., w_radius], w_i proportional to exp(-i^2 / (2 sigma^2)),
 * normalized so w0 + 2 (w1 + ... + w_radius) = 1.
 */
export function gaussianWeights(sigma, radius) {
  checkKernel(sigma, radius);
  const raw = Array.from({length: radius + 1}, (_, index) => Math.exp(-(index * index) / (2 * sigma * sigma)));
  const total = raw[0] + 2 * raw.slice(1).reduce((sum, value) => sum + value, 0);
  return raw.map((value) => value / total);
}

/**
 * Merge a one-sided kernel into bilinear taps: the centre tap, then each pair (i, i + 1) for i = 1, 3, 5 ... as one
 * fetch at offset (i w_i + (i + 1) w_(i+1)) / (w_i + w_(i+1)) with weight w_i + w_(i+1); an unpaired last tap keeps
 * its own offset. Fetching at the merged offset with linear filtering reads exactly the weighted pair.
 */
export function linearSampledTaps(weights) {
  if (!(Array.isArray(weights) && weights.length >= 1 && weights.every((value) => Number.isFinite(value) && value >= 0))) {
    throw new TypeError('weights must be a non-empty array of non-negative numbers');
  }
  const offsets = [0];
  const merged = [weights[0]];
  for (let index = 1; index < weights.length; index += 2) {
    if (index + 1 < weights.length) {
      const total = weights[index] + weights[index + 1];
      offsets.push(total > 0 ? (index * weights[index] + (index + 1) * weights[index + 1]) / total : index);
      merged.push(total);
    } else {
      offsets.push(index);
      merged.push(weights[index]);
    }
  }
  return {offsets, weights: merged};
}

function literal(value) {
  const text = value.toPrecision(10);
  return text.includes('.') || text.includes('e') ? text : `${text}.0`;
}

/**
 * The fragment stage for one sigma and radius: the merged taps as constant arrays, a symmetric pair of fetches per
 * tap along uTexelStep (the direction divided by the input size), then three.js's output colour space conversion.
 */
export function gaussianBlurFragment(sigma, radius) {
  const taps = linearSampledTaps(gaussianWeights(sigma, radius));
  const count = taps.offsets.length;
  return `
uniform sampler2D tDiffuse;
uniform vec2 uTexelStep;
varying vec2 vUv;

const int TAP_COUNT = ${count};
const float TAP_OFFSETS[${count}] = float[${count}](${taps.offsets.map(literal).join(', ')});
const float TAP_WEIGHTS[${count}] = float[${count}](${taps.weights.map(literal).join(', ')});

void main() {
  vec4 sum = texture2D(tDiffuse, vUv) * TAP_WEIGHTS[0];
  for (int i = 1; i < TAP_COUNT; i++) {
    vec2 offset = uTexelStep * TAP_OFFSETS[i];
    sum += (texture2D(tDiffuse, vUv + offset) + texture2D(tDiffuse, vUv - offset)) * TAP_WEIGHTS[i];
  }
  gl_FragColor = sum;
  #include <colorspace_fragment>
}
`;
}

/**
 * CPU reference: the discrete blur of one line of values with a one-sided kernel, reading past either end as the
 * end value (clamp to edge, as the pass samples its input).
 */
export function blurLine(values, weights) {
  const radius = weights.length - 1;
  const last = values.length - 1;
  const out = new Float64Array(values.length);
  for (let x = 0; x < values.length; x += 1) {
    let sum = 0;
    for (let offset = -radius; offset <= radius; offset += 1) {
      sum += weights[Math.abs(offset)] * values[Math.min(Math.max(x + offset, 0), last)];
    }
    out[x] = sum;
  }
  return out;
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(GAUSSIAN_BLUR_DEFAULTS, key)) throw new TypeError(`unknown Gaussian blur option ${key}`);
  }
  const settings = {...GAUSSIAN_BLUR_DEFAULTS, ...options};
  checkKernel(settings.sigma, settings.radius);
  const direction = settings.direction;
  if (!(Array.isArray(direction) && direction.length === 2 && direction.every(Number.isFinite)
      && Math.hypot(direction[0], direction[1]) > 0)) {
    throw new TypeError('direction must be a non-zero [x, y] array, such as [1, 0] or [0, 1]');
  }
  const resolution = settings.resolution;
  if (!(Array.isArray(resolution) && resolution.length === 2 && resolution.every((value) => Number.isInteger(value)
      && value >= 1 && value <= 16384))) {
    throw new RangeError('resolution must be [width, height] in pixels');
  }
  return settings;
}

/**
 * A new shader definition {name, uniforms, vertexShader, fragmentShader} for one blur direction, for three.js
 * ShaderPass (input texture uniform tDiffuse) or ShaderMaterial. Use one with direction [1, 0] and one with [0, 1].
 * The input must be read with linear filtering (render targets are by default).
 */
export function createGaussianBlurShader(options = {}) {
  const settings = settingsOf(options);
  return {
    name: 'BaltorGaussianBlurShader',
    uniforms: {
      tDiffuse: {value: null},
      uTexelStep: {value: [settings.direction[0] / settings.resolution[0], settings.direction[1] / settings.resolution[1]]},
    },
    vertexShader: GAUSSIAN_BLUR_VERTEX,
    fragmentShader: gaussianBlurFragment(settings.sigma, settings.radius),
  };
}

/** A THREE.ShaderMaterial for one blur direction; set uniforms.tDiffuse.value to the input texture. */
export function createGaussianBlurMaterial(THREE, options = {}) {
  const material = new THREE.ShaderMaterial(createGaussianBlurShader(options));
  material.depthTest = false;
  material.depthWrite = false;
  return material;
}
