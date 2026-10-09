// Spherical harmonics light probes: project a radiance function or an equirectangular image onto the nine real
// spherical harmonics of bands 0 to 2 (three coefficients each, red, green and blue), evaluate the diffuse irradiance
// they give with the cosine-lobe convolution, and hand them to three.js as a LightProbe. Original Baltor
// implementation written from the mathematics of spherical harmonic irradiance environment maps; coefficients use
// the order of three.js SphericalHarmonics3: 1, y, z, x, xy, yz, 3z^2 - 1, xz, x^2 - y^2.

/** Normalization constants of the nine real basis functions, in three.js order. */
export const SH_BASIS = Object.freeze([
  1 / (2 * Math.sqrt(Math.PI)),
  Math.sqrt(3 / (4 * Math.PI)), Math.sqrt(3 / (4 * Math.PI)), Math.sqrt(3 / (4 * Math.PI)),
  Math.sqrt(15 / (4 * Math.PI)), Math.sqrt(15 / (4 * Math.PI)), Math.sqrt(5 / (16 * Math.PI)),
  Math.sqrt(15 / (4 * Math.PI)), Math.sqrt(15 / (16 * Math.PI)),
]);
/** Cosine-lobe convolution factors per band: pi, 2 pi / 3, pi / 4. */
export const SH_COSINE_LOBE = Object.freeze([Math.PI, (2 * Math.PI) / 3, Math.PI / 4]);
/** Default options of projectRadiance. */
export const SH_DEFAULTS = Object.freeze({latitudeSamples: 64, longitudeSamples: 128});

const BAND_OF = [0, 1, 1, 1, 2, 2, 2, 2, 2];
const MAXIMUM_SAMPLES = 4096;

/** The nine basis values for a unit direction [x, y, z], in three.js order. */
export function shBasis(direction) {
  const [x, y, z] = direction;
  const b = SH_BASIS;
  return [b[0], b[1] * y, b[2] * z, b[3] * x, b[4] * x * y, b[5] * y * z, b[6] * (3 * z * z - 1), b[7] * x * z,
    b[8] * (x * x - y * y)];
}

function unit(direction, name) {
  if (!(Array.isArray(direction) && direction.length === 3 && direction.every(Number.isFinite))) {
    throw new TypeError(`${name} must be [x, y, z]`);
  }
  const length = Math.hypot(...direction);
  if (!(length > 0)) throw new RangeError(`${name} must not be zero`);
  return direction.map((value) => value / length);
}

function checkCoefficients(coefficients) {
  if (!((Array.isArray(coefficients) || ArrayBuffer.isView(coefficients)) && coefficients.length === 27)) {
    throw new TypeError('coefficients must hold 27 numbers (nine RGB triples)');
  }
}

// Integrate radiance(direction) * basis over the sphere on a latitude-longitude grid: each cell's solid angle is
// exact (cos theta0 - cos theta1) * delta phi, sampled at its centre; theta is measured from +Y.
function integrate(rows, columns, radianceAt) {
  const coefficients = new Float64Array(27);
  for (let row = 0; row < rows; row += 1) {
    const top = (Math.PI * row) / rows;
    const bottom = (Math.PI * (row + 1)) / rows;
    const theta = (top + bottom) / 2;
    const weight = (Math.cos(top) - Math.cos(bottom)) * ((2 * Math.PI) / columns);
    const sinTheta = Math.sin(theta);
    for (let column = 0; column < columns; column += 1) {
      const phi = ((column + 0.5) / columns - 0.5) * 2 * Math.PI;
      const direction = [sinTheta * Math.cos(phi), Math.cos(theta), sinTheta * Math.sin(phi)];
      const radiance = radianceAt(direction, row, column);
      const basis = shBasis(direction);
      for (let index = 0; index < 9; index += 1) {
        for (let channel = 0; channel < 3; channel += 1) coefficients[index * 3 + channel] += radiance[channel] * basis[index] * weight;
      }
    }
  }
  return coefficients;
}

/**
 * Project radiance(direction) -> [r, g, b] (direction a unit [x, y, z], +Y up) onto the nine coefficients per channel.
 * Returns a Float64Array of 27 values, coefficient by coefficient (c0 r, c0 g, c0 b, c1 r, ...), the layout of
 * three.js SphericalHarmonics3.fromArray.
 */
export function projectRadiance(radiance, options = {}) {
  if (typeof radiance !== 'function') throw new TypeError('radiance must be a function of a direction');
  for (const key of Object.keys(options)) if (!Object.prototype.hasOwnProperty.call(SH_DEFAULTS, key)) throw new TypeError(`unknown option ${key}`);
  const settings = {...SH_DEFAULTS, ...options};
  for (const key of Object.keys(SH_DEFAULTS)) {
    if (!(Number.isInteger(settings[key]) && settings[key] >= 4 && settings[key] <= MAXIMUM_SAMPLES)) {
      throw new RangeError(`${key} must be an integer from 4 to ${MAXIMUM_SAMPLES}`);
    }
  }
  return integrate(settings.latitudeSamples, settings.longitudeSamples, (direction) => {
    const value = radiance(direction);
    if (!(Array.isArray(value) && value.length >= 3)) throw new TypeError('radiance must return [r, g, b]');
    return value;
  });
}

/**
 * Project an equirectangular radiance image (rows top to bottom from +Y to -Y; columns following three.js's
 * equirectangular mapping, u = atan2(z, x) / 2 pi + 0.5) given as a Float32Array of RGB or RGBA texels.
 */
export function projectEquirect(pixels, width, height, channels = 4) {
  if (!(pixels instanceof Float32Array || pixels instanceof Float64Array)) throw new TypeError('pixels must be a float array');
  if (!(Number.isInteger(width) && width >= 4 && Number.isInteger(height) && height >= 2)) throw new RangeError('image too small');
  if (channels !== 3 && channels !== 4) throw new RangeError('channels must be 3 or 4');
  if (pixels.length !== width * height * channels) throw new RangeError('pixels must hold width * height * channels values');
  return integrate(height, width, (direction, row, column) => {
    const at = (row * width + column) * channels;
    return [pixels[at], pixels[at + 1], pixels[at + 2]];
  });
}

function evaluate(coefficients, direction, convolve) {
  checkCoefficients(coefficients);
  const basis = shBasis(unit(direction, 'direction'));
  const result = [0, 0, 0];
  for (let index = 0; index < 9; index += 1) {
    const factor = basis[index] * (convolve ? SH_COSINE_LOBE[BAND_OF[index]] : 1);
    for (let channel = 0; channel < 3; channel += 1) result[channel] += coefficients[index * 3 + channel] * factor;
  }
  return result;
}

/** Irradiance [r, g, b] arriving at a surface with this normal: sum of A_l c_lm Y_lm(n). */
export function evaluateIrradiance(coefficients, normal) {
  return evaluate(coefficients, normal, true);
}

/** The band-limited radiance [r, g, b] the coefficients reconstruct in a direction. */
export function evaluateRadiance(coefficients, direction) {
  return evaluate(coefficients, direction, false);
}

/** A THREE.LightProbe holding the coefficients (SphericalHarmonics3.fromArray layout). */
export function toLightProbe(THREE, coefficients, intensity = 1) {
  checkCoefficients(coefficients);
  if (!(typeof intensity === 'number' && intensity >= 0)) throw new RangeError('intensity must be a number >= 0');
  const harmonics = new THREE.SphericalHarmonics3();
  harmonics.fromArray(Array.from(coefficients));
  return new THREE.LightProbe(harmonics, intensity);
}
