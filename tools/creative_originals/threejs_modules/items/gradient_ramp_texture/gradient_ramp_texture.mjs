// Gradient ramp textures: colour stops sampled into an RGBA8 ramp, interpolated in linear light (so the middle of
// black and white is a perceptually even grey, not a dark one), or held as steps for MeshToonMaterial.gradientMap.
// Original Baltor implementation; works on numbers and typed arrays alone, and createGradientTexture and
// createToonGradientMap wrap the result in a three.js DataTexture with the matching colour space and filtering.

/** Default options of gradientRamp, sampleGradient and createGradientTexture. */
export const GRADIENT_DEFAULTS = Object.freeze({width: 256, mode: 'smooth', input: 'srgb', encoding: 'srgb'});

const MODES = new Set(['smooth', 'stepped']);
const SPACES = new Set(['srgb', 'linear']);
const MAXIMUM_WIDTH = 4096;

/** The sRGB transfer function's inverse: an sRGB-encoded component in [0, 1] to linear light. */
export function srgbToLinear(value) {
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

/** Linear light in [0, 1] to an sRGB-encoded component. */
export function linearToSrgb(value) {
  return value <= 0.0031308 ? value * 12.92 : 1.055 * value ** (1 / 2.4) - 0.055;
}

function settingsOf(options) {
  if (!options || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(GRADIENT_DEFAULTS, key)) throw new TypeError(`unknown gradient option ${key}`);
  }
  const settings = {...GRADIENT_DEFAULTS, ...options};
  if (!(Number.isInteger(settings.width) && settings.width >= 1 && settings.width <= MAXIMUM_WIDTH)) {
    throw new RangeError(`width must be an integer from 1 to ${MAXIMUM_WIDTH}`);
  }
  if (!MODES.has(settings.mode)) throw new RangeError('mode must be smooth or stepped');
  if (!SPACES.has(settings.input) || !SPACES.has(settings.encoding)) throw new RangeError('input and encoding are srgb or linear');
  return settings;
}

function colourOf(value) {
  if (typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 0xffffff) {
    return [((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255, 1];
  }
  if (Array.isArray(value) && (value.length === 3 || value.length === 4)
    && value.every((component) => typeof component === 'number' && component >= 0 && component <= 1)) {
    return value.length === 3 ? [...value, 1] : [...value];
  }
  throw new TypeError('a stop colour is a 0xRRGGBB number or [r, g, b] or [r, g, b, a] in [0, 1]');
}

// Stops as {position, linear: [r, g, b, a]} in increasing position.
function stopsOf(stops, input) {
  if (!Array.isArray(stops) || stops.length === 0) throw new RangeError('stops must be a non-empty array');
  let previous = -Infinity;
  return stops.map((stop, index) => {
    if (!stop || typeof stop !== 'object') throw new TypeError(`stop ${index} must be {position, color}`);
    const {position} = stop;
    if (!(typeof position === 'number' && position >= 0 && position <= 1)) throw new RangeError(`stop ${index} position is in [0, 1]`);
    if (position < previous) throw new RangeError('stop positions must not decrease');
    previous = position;
    const colour = colourOf(stop.color);
    const linear = colour.map((component, channel) => (channel < 3 && input === 'srgb' ? srgbToLinear(component) : component));
    return {position, linear};
  });
}

function sample(stops, t, mode) {
  if (mode === 'stepped') {
    let chosen = stops[0];
    for (const stop of stops) if (stop.position <= t) chosen = stop;
    return [...chosen.linear];
  }
  if (t <= stops[0].position) return [...stops[0].linear];
  const last = stops[stops.length - 1];
  if (t >= last.position) return [...last.linear];
  for (let index = 1; index < stops.length; index += 1) {
    const right = stops[index];
    if (t <= right.position) {
      const left = stops[index - 1];
      const span = right.position - left.position;
      const mix = span > 0 ? (t - left.position) / span : 1;
      return left.linear.map((value, channel) => value + (right.linear[channel] - value) * mix);
    }
  }
  return [...last.linear];
}

/** The gradient at t in [0, 1] as linear-light [r, g, b, a]; stepped mode holds the last stop at or before t. */
export function sampleGradient(stops, t, options = {}) {
  const settings = settingsOf(options);
  if (!(typeof t === 'number' && t >= 0 && t <= 1)) throw new RangeError('t must be in [0, 1]');
  return sample(stopsOf(stops, settings.input), t, settings.mode);
}

/**
 * The ramp as RGBA8 bytes, width texels long; texel i samples t = (i + 0.5) / width. Colour channels are stored
 * sRGB-encoded (encoding 'srgb', the default, for colour textures) or as linear values (encoding 'linear', for
 * MeshToonMaterial gradient maps and data lookups); alpha is always linear.
 */
export function gradientRamp(stops, options = {}) {
  const settings = settingsOf(options);
  const parsed = stopsOf(stops, settings.input);
  const bytes = new Uint8Array(settings.width * 4);
  for (let texel = 0; texel < settings.width; texel += 1) {
    const colour = sample(parsed, (texel + 0.5) / settings.width, settings.mode);
    colour.forEach((value, channel) => {
      const stored = channel < 3 && settings.encoding === 'srgb' ? linearToSrgb(value) : value;
      bytes[texel * 4 + channel] = Math.round(Math.min(Math.max(stored, 0), 1) * 255);
    });
  }
  return bytes;
}

/**
 * A width x 1 THREE.DataTexture of the ramp: SRGBColorSpace for encoding 'srgb', NoColorSpace for 'linear';
 * NearestFilter in stepped mode, LinearFilter otherwise; clamped at both ends; no mipmaps.
 */
export function createGradientTexture(THREE, stops, options = {}) {
  const settings = settingsOf(options);
  const texture = new THREE.DataTexture(gradientRamp(stops, settings), settings.width, 1, THREE.RGBAFormat, THREE.UnsignedByteType);
  texture.colorSpace = settings.encoding === 'srgb' ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  const filter = settings.mode === 'stepped' ? THREE.NearestFilter : THREE.LinearFilter;
  texture.magFilter = filter;
  texture.minFilter = filter;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}

/**
 * A MeshToonMaterial.gradientMap with one texel per level: levels are linear light multipliers in [0, 1] from the
 * darkest band to the brightest, held as steps with NearestFilter.
 */
export function createToonGradientMap(THREE, levels) {
  if (!Array.isArray(levels) || levels.length < 2 || levels.length > 64) throw new RangeError('levels must hold 2 to 64 values');
  const stops = levels.map((level, index) => {
    if (!(typeof level === 'number' && level >= 0 && level <= 1)) throw new RangeError('each level is in [0, 1]');
    return {position: index / levels.length, color: [level, level, level]};
  });
  return createGradientTexture(THREE, stops, {width: levels.length, mode: 'stepped', input: 'linear', encoding: 'linear'});
}
