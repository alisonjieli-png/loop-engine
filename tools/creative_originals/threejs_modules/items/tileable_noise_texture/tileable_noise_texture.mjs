// Tileable noise textures: gradient noise on an integer lattice that repeats every `period` cells, summed over
// octaves (fBm) whose lattice periods double with their frequency, so the whole field repeats exactly and a texture
// of one period tiles without a seam. Gradients come from an integer hash of the wrapped lattice point and the seed
// (Math.imul arithmetic, the same in every JavaScript engine). Original Baltor implementation; typed arrays only, and
// createNoiseTexture wraps the result in a three.js DataTexture with repeat wrapping.

/** Default options of fbmNoise, noiseField, noiseTextureData and createNoiseTexture. */
export const NOISE_DEFAULTS = Object.freeze({period: 8, octaves: 4, gain: 0.5, seed: 1, channels: 'grey'});

const DIAGONAL = Math.SQRT1_2;
const GRADIENTS = [[1, 0], [-1, 0], [0, 1], [0, -1], [DIAGONAL, DIAGONAL], [-DIAGONAL, DIAGONAL], [DIAGONAL, -DIAGONAL],
  [-DIAGONAL, -DIAGONAL]];
const RANGE_SCALE = Math.SQRT2;
const MAXIMUM_PERIOD = 4096;
const MAXIMUM_OCTAVES = 12;
const CHANNEL_SEED_STEP = 101;
const CHANNEL_MODES = new Set(['grey', 'rgba']);

/** A 32-bit integer hash of a lattice point and a seed, as an unsigned integer. */
export function latticeHash(x, y, seed) {
  let h = Math.imul(x | 0, 0x27d4eb2d) ^ Math.imul(y | 0, 0x165667b1) ^ Math.imul(seed | 0, 0x2c1b3c6d);
  h = Math.imul(h ^ (h >>> 15), 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
  return (h ^ (h >>> 16)) >>> 0;
}

function fade(t) {
  return t * t * t * (t * (t * 6 - 15) + 10);
}

function checkPeriod(period) {
  if (!(Number.isInteger(period) && period >= 1 && period <= MAXIMUM_PERIOD)) {
    throw new RangeError(`period must be an integer from 1 to ${MAXIMUM_PERIOD}`);
  }
}

/**
 * Gradient noise at (x, y) whose lattice repeats every `period` cells along both axes: periodicGradientNoise(x +
 * period, y) equals periodicGradientNoise(x, y), exactly when both coordinates are representable (for example texel
 * centres of power-of-two textures). Zero at lattice points; values lie in [-1, 1].
 */
export function periodicGradientNoise(x, y, period, seed = 1) {
  checkPeriod(period);
  if (!Number.isInteger(seed)) throw new RangeError('seed must be an integer');
  return latticeNoise(x, y, period, seed);
}

function latticeNoise(x, y, period, seed) {
  const column = Math.floor(x);
  const row = Math.floor(y);
  const fx = x - column;
  const fy = y - row;
  const wrap = (value) => ((value % period) + period) % period;
  const x0 = wrap(column);
  const x1 = wrap(column + 1);
  const y0 = wrap(row);
  const y1 = wrap(row + 1);
  const corner = (cornerX, cornerY, dx, dy) => {
    const [gx, gy] = GRADIENTS[latticeHash(cornerX, cornerY, seed) & 7];
    return gx * dx + gy * dy;
  };
  const u = fade(fx);
  const v = fade(fy);
  const bottom = corner(x0, y0, fx, fy) + (corner(x1, y0, fx - 1, fy) - corner(x0, y0, fx, fy)) * u;
  const top = corner(x0, y1, fx, fy - 1) + (corner(x1, y1, fx - 1, fy - 1) - corner(x0, y1, fx, fy - 1)) * u;
  return RANGE_SCALE * (bottom + (top - bottom) * v);
}

function settingsOf(options) {
  if (!options || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(NOISE_DEFAULTS, key)) throw new TypeError(`unknown noise option ${key}`);
  }
  const settings = {...NOISE_DEFAULTS, ...options};
  checkPeriod(settings.period);
  if (!(Number.isInteger(settings.octaves) && settings.octaves >= 1 && settings.octaves <= MAXIMUM_OCTAVES)) {
    throw new RangeError(`octaves must be an integer from 1 to ${MAXIMUM_OCTAVES}`);
  }
  if (!(typeof settings.gain === 'number' && settings.gain > 0 && settings.gain <= 1)) throw new RangeError('gain must be in (0, 1]');
  if (!Number.isInteger(settings.seed)) throw new RangeError('seed must be an integer');
  if (!CHANNEL_MODES.has(settings.channels)) throw new RangeError('channels must be grey or rgba');
  return settings;
}

/**
 * Fractal sum of periodic gradient noise at (x, y) in units of base lattice cells: octave k has frequency 2^k, lattice
 * period period * 2^k, amplitude gain^k and seed seed + k; the sum is divided by the total amplitude, so it stays in
 * [-1, 1] and repeats every `period` along x and y.
 */
export function fbmNoise(x, y, options = {}) {
  const settings = settingsOf(options);
  let sum = 0;
  let amplitude = 1;
  let total = 0;
  for (let octave = 0; octave < settings.octaves; octave += 1) {
    const frequency = 2 ** octave;
    sum += amplitude * latticeNoise(x * frequency, y * frequency, settings.period * frequency, settings.seed + octave);
    total += amplitude;
    amplitude *= settings.gain;
  }
  return sum / total;
}

/**
 * One period of fBm noise sampled on a width x height grid: texel (i, j) reads x = (i + 0.5) * period / width and
 * y = (j + 0.5) * period / height, so the grid tiles in both directions. Float32Array, row 0 at v = 0.
 */
export function noiseField(width, height, options = {}) {
  const settings = settingsOf(options);
  if (!(Number.isInteger(width) && width >= 1 && width <= MAXIMUM_PERIOD * 4 && Number.isInteger(height) && height >= 1
    && height <= MAXIMUM_PERIOD * 4)) {
    throw new RangeError('width and height must be integers from 1 to 16384');
  }
  const field = new Float32Array(width * height);
  for (let row = 0; row < height; row += 1) {
    for (let column = 0; column < width; column += 1) {
      field[row * width + column] = fbmNoise(((column + 0.5) * settings.period) / width,
        ((row + 0.5) * settings.period) / height, settings);
    }
  }
  return field;
}

/**
 * RGBA8 bytes of the noise, mapped from [-1, 1] to [0, 255]: channels 'grey' writes one field into red, green and
 * blue with alpha 255; 'rgba' writes four independent fields (seeds seed, seed + 101, seed + 202, seed + 303).
 */
export function noiseTextureData(width, height, options = {}) {
  const settings = settingsOf(options);
  const count = settings.channels === 'rgba' ? 4 : 1;
  const fields = Array.from({length: count}, (_, channel) => noiseField(width, height,
    {...settings, seed: settings.seed + channel * CHANNEL_SEED_STEP}));
  const bytes = new Uint8Array(width * height * 4);
  for (let texel = 0; texel < width * height; texel += 1) {
    for (let channel = 0; channel < 4; channel += 1) {
      const field = count === 4 ? fields[channel] : channel < 3 ? fields[0] : null;
      bytes[texel * 4 + channel] = field ? Math.round((Math.min(Math.max(field[texel], -1), 1) * 0.5 + 0.5) * 255) : 255;
    }
  }
  return bytes;
}

/** A repeat-wrapped, mipmapped THREE.DataTexture of noiseTextureData, holding linear data (NoColorSpace). */
export function createNoiseTexture(THREE, width, height, options = {}) {
  const texture = new THREE.DataTexture(noiseTextureData(width, height, options), width, height, THREE.RGBAFormat,
    THREE.UnsignedByteType);
  texture.colorSpace = THREE.NoColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.needsUpdate = true;
  return texture;
}
