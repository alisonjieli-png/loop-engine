// Colour grading pass for three.js post-processing with a 3D lookup table stored as a horizontal strip: N tiles of
// N x N texels side by side, tile b holding the blue slice b, red along x and green along y. The pass blends the two
// nearest blue slices, each read with bilinear filtering at half-texel insets, so the lookup is trilinear. Helpers
// build identity and function-baked strips, sample a strip on the CPU exactly as the shader does and wrap a strip in
// a three.js DataTexture. Original Baltor implementation.

/** Lookup domains: grade the values as received (linear), or sRGB-encode them first as grading tools expect. */
export const COLOR_LUT_DOMAINS = Object.freeze({linear: 0, srgb: 1});

/** Default options of createColorLutShader, createColorLutMaterial and gradeColorCpu. */
export const COLOR_LUT_DEFAULTS = Object.freeze({
  size: 16,
  intensity: 1,
  domain: 'srgb',
});

const MINIMUM_SIZE = 2;
const MAXIMUM_SIZE = 64;

/** Vertex stage for a full-screen triangle or quad (three.js ShaderPass supplies one). */
export const COLOR_LUT_VERTEX = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

/** Fragment stage: optional sRGB encode, trilinear strip lookup, decode, mix by intensity. */
export const COLOR_LUT_FRAGMENT = `
uniform sampler2D tDiffuse;
uniform sampler2D tLut;
uniform float uLutSize;
uniform float uIntensity;
uniform int uDomain;
varying vec2 vUv;

vec3 lutEncodeSrgb(vec3 value) {
  return mix(value * 12.92, 1.055 * pow(value, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), value));
}

vec3 lutDecodeSrgb(vec3 value) {
  return mix(value / 12.92, pow((value + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), value));
}

vec3 sampleLutStrip(vec3 colour) {
  float n = uLutSize;
  vec3 scaled = clamp(colour, 0.0, 1.0) * (n - 1.0);
  float slice0 = floor(scaled.b);
  float slice1 = min(slice0 + 1.0, n - 1.0);
  float blend = scaled.b - slice0;
  float v = (scaled.g + 0.5) / n;
  vec3 low = texture2D(tLut, vec2((slice0 * n + scaled.r + 0.5) / (n * n), v)).rgb;
  vec3 high = texture2D(tLut, vec2((slice1 * n + scaled.r + 0.5) / (n * n), v)).rgb;
  return mix(low, high, blend);
}

void main() {
  vec4 texel = texture2D(tDiffuse, vUv);
  vec3 colour = clamp(texel.rgb, 0.0, 1.0);
  vec3 graded;
  if (uDomain == 1) {
    graded = lutDecodeSrgb(sampleLutStrip(lutEncodeSrgb(colour)));
  } else {
    graded = sampleLutStrip(colour);
  }
  gl_FragColor = vec4(mix(texel.rgb, graded, uIntensity), texel.a);
  #include <colorspace_fragment>
}
`;

function checkSize(size) {
  if (!Number.isInteger(size) || size < MINIMUM_SIZE || size > MAXIMUM_SIZE) {
    throw new RangeError(`size must be an integer from ${MINIMUM_SIZE} to ${MAXIMUM_SIZE}, got ${size}`);
  }
}

function checkStrip(data, size) {
  checkSize(size);
  if (!(data instanceof Uint8Array) || data.length !== size * size * size * 4) {
    throw new TypeError(`a size ${size} strip is a Uint8Array of ${size * size * size * 4} RGBA bytes`);
  }
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(COLOR_LUT_DEFAULTS, key)) throw new TypeError(`unknown colour LUT option ${key}`);
  }
  const settings = {...COLOR_LUT_DEFAULTS, ...options};
  checkSize(settings.size);
  if (!(typeof settings.intensity === 'number' && settings.intensity >= 0 && settings.intensity <= 1)) {
    throw new RangeError(`intensity must be in [0, 1], got ${settings.intensity}`);
  }
  if (!Object.prototype.hasOwnProperty.call(COLOR_LUT_DOMAINS, settings.domain)) throw new TypeError(`domain must be one of ${Object.keys(COLOR_LUT_DOMAINS)}`);
  return settings;
}

function toByte(value) {
  return Math.round(Math.min(Math.max(value, 0), 1) * 255);
}

/**
 * A strip baked from fn(r, g, b) -> [r, g, b] (inputs and outputs in [0, 1]) at every grid point k / (size - 1):
 * a Uint8Array of size * size * size RGBA texels, width size * size and height size, rows from the bottom.
 */
export function lutStripFromFunction(size, fn) {
  checkSize(size);
  if (typeof fn !== 'function') throw new TypeError('fn must be a function (r, g, b) -> [r, g, b]');
  const width = size * size;
  const data = new Uint8Array(width * size * 4);
  for (let blue = 0; blue < size; blue += 1) {
    for (let green = 0; green < size; green += 1) {
      for (let red = 0; red < size; red += 1) {
        const out = fn(red / (size - 1), green / (size - 1), blue / (size - 1));
        if (!(Array.isArray(out) && out.length === 3 && out.every(Number.isFinite))) {
          throw new TypeError('fn must return three finite numbers');
        }
        data.set([toByte(out[0]), toByte(out[1]), toByte(out[2]), 255], (green * width + blue * size + red) * 4);
      }
    }
  }
  return data;
}

/** The identity strip: grading with it returns the input. */
export function identityLutStrip(size) {
  return lutStripFromFunction(size, (r, g, b) => [r, g, b]);
}

/**
 * CPU mirror of the shader lookup: the trilinear value of a strip at (r, g, b) in [0, 1] (clamped), bilinear inside
 * the two nearest blue slices and linear between them, as [r, g, b] in [0, 1].
 */
export function sampleLutStripCpu(data, size, r, g, b) {
  checkStrip(data, size);
  const width = size * size;
  const scaled = [r, g, b].map((value) => Math.min(Math.max(value, 0), 1) * (size - 1));
  const slice0 = Math.floor(scaled[2]);
  const slice1 = Math.min(slice0 + 1, size - 1);
  const blend = scaled[2] - slice0;
  const x0 = Math.floor(scaled[0]);
  const x1 = Math.min(x0 + 1, size - 1);
  const y0 = Math.floor(scaled[1]);
  const y1 = Math.min(y0 + 1, size - 1);
  const fx = scaled[0] - x0;
  const fy = scaled[1] - y0;
  const texel = (slice, x, y, channel) => data[(y * width + slice * size + x) * 4 + channel] / 255;
  const bilinear = (slice, channel) => {
    const bottom = texel(slice, x0, y0, channel) * (1 - fx) + texel(slice, x1, y0, channel) * fx;
    const top = texel(slice, x0, y1, channel) * (1 - fx) + texel(slice, x1, y1, channel) * fx;
    return bottom * (1 - fy) + top * fy;
  };
  return [0, 1, 2].map((channel) => bilinear(slice0, channel) * (1 - blend) + bilinear(slice1, channel) * blend);
}

function encodeSrgb(value) {
  return value < 0.0031308 ? value * 12.92 : 1.055 * value ** (1 / 2.4) - 0.055;
}

function decodeSrgb(value) {
  return value < 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

/**
 * CPU mirror of the whole pass for one colour: clamp, sRGB-encode in the srgb domain, look up, decode, then mix with
 * the original colour by intensity. Returns [r, g, b].
 */
export function gradeColorCpu(data, size, rgb, options = {}) {
  const settings = settingsOf({...options, size});
  const clamped = rgb.map((value) => Math.min(Math.max(value, 0), 1));
  const srgb = COLOR_LUT_DOMAINS[settings.domain] === COLOR_LUT_DOMAINS.srgb;
  const lookup = srgb ? clamped.map(encodeSrgb) : clamped;
  let graded = sampleLutStripCpu(data, size, lookup[0], lookup[1], lookup[2]);
  if (srgb) graded = graded.map(decodeSrgb);
  return graded.map((value, channel) => rgb[channel] + (value - rgb[channel]) * settings.intensity);
}

/** A THREE.DataTexture holding the strip, with linear filtering, clamped edges and no mipmaps. */
export function createLutStripTexture(THREE, data, size) {
  checkStrip(data, size);
  const texture = new THREE.DataTexture(data, size * size, size, THREE.RGBAFormat, THREE.UnsignedByteType);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}

/**
 * A new shader definition {name, uniforms, vertexShader, fragmentShader} for three.js ShaderPass (input texture
 * uniform tDiffuse) or ShaderMaterial. Set uniforms.tLut.value to a strip texture of the declared size.
 */
export function createColorLutShader(options = {}) {
  const settings = settingsOf(options);
  return {
    name: 'BaltorColorLutStripShader',
    uniforms: {
      tDiffuse: {value: null},
      tLut: {value: null},
      uLutSize: {value: settings.size},
      uIntensity: {value: settings.intensity},
      uDomain: {value: COLOR_LUT_DOMAINS[settings.domain]},
    },
    vertexShader: COLOR_LUT_VERTEX,
    fragmentShader: COLOR_LUT_FRAGMENT,
  };
}

/** A THREE.ShaderMaterial for a full-screen pass; set uniforms.tDiffuse and uniforms.tLut. */
export function createColorLutMaterial(THREE, options = {}) {
  const material = new THREE.ShaderMaterial(createColorLutShader(options));
  material.depthTest = false;
  material.depthWrite = false;
  return material;
}
