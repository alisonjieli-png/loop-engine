// Ordered dithering pass for three.js post-processing: a Bayer threshold matrix (2, 4, 8 or 16 wide) dithers each
// pixel block either to a fixed number of levels per channel or to the nearest colour of a palette of up to 16
// colours, in sRGB-encoded or linear values, for retro, print and low-colour looks. Original Baltor implementation;
// the matrix is built recursively here and computed bit by bit in the shader, and every output pixel has an exact
// CPU mirror.

/** Quantization modes for uMode. */
export const DITHER_MODES = Object.freeze({levels: 0, palette: 1});

/** Value domains for uDomain: dither sRGB-encoded values (perceptually even steps) or the linear values received. */
export const DITHER_DOMAINS = Object.freeze({linear: 0, srgb: 1});

/** Default options of createOrderedDitherShader, createOrderedDitherMaterial and ditherPixel. */
export const ORDERED_DITHER_DEFAULTS = Object.freeze({
  matrixSize: 4,
  mode: 'levels',
  levels: 4,
  palette: Object.freeze([
    Object.freeze([0.07, 0.06, 0.11]), Object.freeze([0.33, 0.23, 0.33]),
    Object.freeze([0.76, 0.45, 0.35]), Object.freeze([0.98, 0.89, 0.71]),
  ]),
  spread: 0.5,
  pixelSize: 1,
  domain: 'srgb',
  resolution: Object.freeze([1024, 1024]),
});

const MATRIX_BITS = Object.freeze({2: 1, 4: 2, 8: 3, 16: 4});
const MAXIMUM_PALETTE = 16;

/** Vertex stage for a full-screen triangle or quad (three.js ShaderPass supplies one). */
export const ORDERED_DITHER_VERTEX = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

/** Fragment stage: block sample, Bayer threshold, levels or nearest palette colour, back to linear. */
export const ORDERED_DITHER_FRAGMENT = `
uniform sampler2D tDiffuse;
uniform vec2 uResolution;
uniform float uPixelSize;
uniform int uMatrixBits;
uniform int uMode;
uniform float uLevels;
uniform vec3 uPalette[${MAXIMUM_PALETTE}];
uniform int uPaletteSize;
uniform float uSpread;
uniform int uDomain;
varying vec2 vUv;

float bayerThreshold(ivec2 cell) {
  int value = 0;
  int weight = 1;
  for (int level = 0; level < 4; level++) {
    if (level >= uMatrixBits) break;
    int bit = uMatrixBits - 1 - level;
    int xBit = (cell.x >> bit) & 1;
    int yBit = (cell.y >> bit) & 1;
    int corner = yBit == 0 ? (xBit == 0 ? 0 : 2) : (xBit == 0 ? 3 : 1);
    value += corner * weight;
    weight *= 4;
  }
  int side = 1 << uMatrixBits;
  return (float(value) + 0.5) / float(side * side);
}

vec3 ditherEncodeSrgb(vec3 value) {
  return mix(value * 12.92, 1.055 * pow(value, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), value));
}

vec3 ditherDecodeSrgb(vec3 value) {
  return mix(value / 12.92, pow((value + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), value));
}

void main() {
  ivec2 cell = ivec2(floor(gl_FragCoord.xy / uPixelSize));
  vec2 samplePixel = vec2(cell) * uPixelSize + floor(uPixelSize * 0.5) + 0.5;
  vec4 texel = texture2D(tDiffuse, samplePixel / uResolution);
  vec3 colour = clamp(texel.rgb, 0.0, 1.0);
  if (uDomain == 1) colour = ditherEncodeSrgb(colour);
  float threshold = bayerThreshold(cell);
  vec3 result;
  if (uMode == 1) {
    vec3 shifted = colour + uSpread * (threshold - 0.5);
    result = uPalette[0];
    vec3 delta = shifted - uPalette[0];
    float best = dot(delta, delta);
    for (int index = 1; index < ${MAXIMUM_PALETTE}; index++) {
      if (index >= uPaletteSize) break;
      delta = shifted - uPalette[index];
      float distanceSquared = dot(delta, delta);
      if (distanceSquared < best) {
        best = distanceSquared;
        result = uPalette[index];
      }
    }
  } else {
    result = floor(colour * (uLevels - 1.0) + threshold) / (uLevels - 1.0);
  }
  if (uDomain == 1) result = ditherDecodeSrgb(result);
  gl_FragColor = vec4(result, texel.a);
  #include <colorspace_fragment>
}
`;

/** The n x n Bayer matrix (n = 2, 4, 8 or 16) built by the recursion M(2n) = [[4M, 4M + 2], [4M + 3, 4M + 1]]. */
export function bayerMatrix(n) {
  if (!Object.prototype.hasOwnProperty.call(MATRIX_BITS, n) && n !== 1) throw new RangeError(`matrix size must be 2, 4, 8 or 16, got ${n}`);
  if (n === 1) return [[0]];
  const half = n / 2;
  const inner = bayerMatrix(half);
  const corners = [[0, 2], [3, 1]];
  return Array.from({length: n}, (_, y) => Array.from({length: n},
    (__, x) => 4 * inner[y % half][x % half] + corners[Math.floor(y / half)][Math.floor(x / half)]));
}

/**
 * CPU mirror of the shader's threshold for cell (x, y): (M + 0.5) / n^2 with M the Bayer value at (x mod n, y mod n),
 * computed bit by bit from the most significant bit down, as the shader does. Rows count up from the bottom.
 */
export function bayerThreshold(x, y, n) {
  const bits = MATRIX_BITS[n];
  if (bits === undefined) throw new RangeError(`matrix size must be 2, 4, 8 or 16, got ${n}`);
  let value = 0;
  let weight = 1;
  for (let level = 0; level < bits; level += 1) {
    const bit = bits - 1 - level;
    const xBit = (x >> bit) & 1;
    const yBit = (y >> bit) & 1;
    const corner = yBit === 0 ? (xBit === 0 ? 0 : 2) : (xBit === 0 ? 3 : 1);
    value += corner * weight;
    weight *= 4;
  }
  return (value + 0.5) / (n * n);
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(ORDERED_DITHER_DEFAULTS, key)) throw new TypeError(`unknown ordered dither option ${key}`);
  }
  const settings = {...ORDERED_DITHER_DEFAULTS, ...options};
  if (MATRIX_BITS[settings.matrixSize] === undefined) throw new RangeError('matrixSize must be 2, 4, 8 or 16');
  if (!Object.prototype.hasOwnProperty.call(DITHER_MODES, settings.mode)) throw new TypeError(`mode must be one of ${Object.keys(DITHER_MODES)}`);
  if (!Object.prototype.hasOwnProperty.call(DITHER_DOMAINS, settings.domain)) throw new TypeError(`domain must be one of ${Object.keys(DITHER_DOMAINS)}`);
  if (!Number.isInteger(settings.levels) || settings.levels < 2 || settings.levels > 256) {
    throw new RangeError(`levels must be an integer from 2 to 256, got ${settings.levels}`);
  }
  if (!Number.isInteger(settings.pixelSize) || settings.pixelSize < 1 || settings.pixelSize > 64) {
    throw new RangeError(`pixelSize must be an integer from 1 to 64, got ${settings.pixelSize}`);
  }
  if (!(typeof settings.spread === 'number' && settings.spread >= 0 && settings.spread <= 2)) {
    throw new RangeError(`spread must be in [0, 2], got ${settings.spread}`);
  }
  const palette = settings.palette;
  if (!(Array.isArray(palette) && palette.length >= 1 && palette.length <= MAXIMUM_PALETTE && palette.every(
    (colour) => Array.isArray(colour) && colour.length === 3 && colour.every((value) => value >= 0 && value <= 1)))) {
    throw new TypeError(`palette must hold 1 to ${MAXIMUM_PALETTE} [r, g, b] colours with values in [0, 1]`);
  }
  const resolution = settings.resolution;
  if (!(Array.isArray(resolution) && resolution.length === 2 && resolution.every((value) => Number.isInteger(value)
      && value >= 1 && value <= 16384))) {
    throw new RangeError('resolution must be [width, height] in pixels');
  }
  return settings;
}

function encodeSrgb(value) {
  return value < 0.0031308 ? value * 12.92 : 1.055 * value ** (1 / 2.4) - 0.055;
}

function decodeSrgb(value) {
  return value < 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

/**
 * The output pixel whose input colour the block of output pixel (x, y) uses: the pixel at floor(pixelSize / 2)
 * inside the block, so every block reads one exact texel. Pixel coordinates count from the bottom-left.
 */
export function ditherSamplePixel(x, y, pixelSize = 1) {
  if (!Number.isInteger(pixelSize) || pixelSize < 1) throw new RangeError('pixelSize must be a positive integer');
  const offset = Math.floor(pixelSize / 2);
  return [Math.floor(x / pixelSize) * pixelSize + offset, Math.floor(y / pixelSize) * pixelSize + offset];
}

/**
 * CPU mirror of one output pixel: the colour rgb (read at ditherSamplePixel) clamped, sRGB-encoded in the srgb
 * domain, dithered with the threshold of the pixel's block to levels or to the nearest palette colour (ties go to
 * the earlier colour), and decoded back. Palette colours are given in the dithering domain.
 */
export function ditherPixel(rgb, x, y, options = {}) {
  const settings = settingsOf(options);
  const threshold = bayerThreshold(Math.floor(x / settings.pixelSize), Math.floor(y / settings.pixelSize),
    settings.matrixSize);
  const srgb = DITHER_DOMAINS[settings.domain] === DITHER_DOMAINS.srgb;
  let colour = rgb.map((value) => Math.min(Math.max(value, 0), 1));
  if (srgb) colour = colour.map(encodeSrgb);
  let result;
  if (DITHER_MODES[settings.mode] === DITHER_MODES.palette) {
    const shifted = colour.map((value) => value + settings.spread * (threshold - 0.5));
    let best = Infinity;
    for (const entry of settings.palette) {
      const distance = entry.reduce((sum, value, channel) => sum + (shifted[channel] - value) ** 2, 0);
      if (distance < best) {
        best = distance;
        result = [...entry];
      }
    }
  } else {
    const steps = settings.levels - 1;
    result = colour.map((value) => Math.floor(value * steps + threshold) / steps);
  }
  return srgb ? result.map(decodeSrgb) : result;
}

/**
 * A new shader definition {name, uniforms, vertexShader, fragmentShader} for three.js ShaderPass (input texture
 * uniform tDiffuse) or ShaderMaterial. uResolution is the output size in pixels; uPalette is a flat array of 16
 * colours (unused entries zero), the layout three.js uploads for a vec3 array uniform.
 */
export function createOrderedDitherShader(options = {}) {
  const settings = settingsOf(options);
  const palette = new Float32Array(MAXIMUM_PALETTE * 3);
  settings.palette.forEach((colour, index) => palette.set(colour, index * 3));
  return {
    name: 'BaltorOrderedDitherShader',
    uniforms: {
      tDiffuse: {value: null},
      uResolution: {value: [...settings.resolution]},
      uPixelSize: {value: settings.pixelSize},
      uMatrixBits: {value: MATRIX_BITS[settings.matrixSize]},
      uMode: {value: DITHER_MODES[settings.mode]},
      uLevels: {value: settings.levels},
      uPalette: {value: palette},
      uPaletteSize: {value: settings.palette.length},
      uSpread: {value: settings.spread},
      uDomain: {value: DITHER_DOMAINS[settings.domain]},
    },
    vertexShader: ORDERED_DITHER_VERTEX,
    fragmentShader: ORDERED_DITHER_FRAGMENT,
  };
}

/** A THREE.ShaderMaterial for a full-screen pass; set uniforms.tDiffuse.value to the input texture. */
export function createOrderedDitherMaterial(THREE, options = {}) {
  const material = new THREE.ShaderMaterial(createOrderedDitherShader(options));
  material.depthTest = false;
  material.depthWrite = false;
  return material;
}
