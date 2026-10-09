// Normal map from a height field: central differences of a Float32Array of heights give tangent-space normals,
// encoded as an RGBA8 normal map in the OpenGL (green up) or DirectX (green down) convention, with wrapped or
// clamped edges. Original Baltor implementation; works on typed arrays alone, and createNormalMapTexture wraps the
// result in a three.js DataTexture when three.js is passed in.

/** Default options of normalsFromHeight and normalMapFromHeight. */
export const NORMAL_MAP_DEFAULTS = Object.freeze({strength: 1, edges: 'wrap', convention: 'opengl'});

const EDGE_MODES = new Set(['wrap', 'clamp']);
const CONVENTIONS = new Set(['opengl', 'directx']);
const MAXIMUM_STRENGTH = 1000;

function settingsOf(options) {
  if (!options || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(NORMAL_MAP_DEFAULTS, key)) throw new TypeError(`unknown normal map option ${key}`);
  }
  const settings = {...NORMAL_MAP_DEFAULTS, ...options};
  if (!(typeof settings.strength === 'number' && settings.strength >= 0 && settings.strength <= MAXIMUM_STRENGTH)) {
    throw new RangeError(`strength must be in [0, ${MAXIMUM_STRENGTH}]`);
  }
  if (!EDGE_MODES.has(settings.edges)) throw new RangeError('edges must be wrap or clamp');
  if (!CONVENTIONS.has(settings.convention)) throw new RangeError('convention must be opengl or directx');
  return settings;
}

function checkField(heights, width, height) {
  if (!(heights instanceof Float32Array || heights instanceof Float64Array)) {
    throw new TypeError('heights must be a Float32Array or Float64Array');
  }
  if (!(Number.isInteger(width) && width >= 1 && Number.isInteger(height) && height >= 1)) {
    throw new RangeError('width and height must be positive integers');
  }
  if (heights.length !== width * height) throw new RangeError(`heights must hold width * height = ${width * height} values`);
}

/**
 * Unit tangent-space normals (x along +u, the columns; y along +v, the rows, row 0 being v = 0 as in a DataTexture;
 * z out of the surface) as a Float32Array of xyz per texel: normalize(-strength * dh/du, -strength * dh/dv, 1), the
 * slopes taken by central differences in height units per texel.
 */
export function normalsFromHeight(heights, width, height, options = {}) {
  checkField(heights, width, height);
  const settings = settingsOf(options);
  const wrap = settings.edges === 'wrap';
  const sample = (x, y) => {
    const column = wrap ? ((x % width) + width) % width : Math.min(Math.max(x, 0), width - 1);
    const row = wrap ? ((y % height) + height) % height : Math.min(Math.max(y, 0), height - 1);
    return heights[row * width + column];
  };
  const normals = new Float32Array(width * height * 3);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const slopeU = (sample(x + 1, y) - sample(x - 1, y)) / 2;
      const slopeV = (sample(x, y + 1) - sample(x, y - 1)) / 2;
      const nx = -settings.strength * slopeU;
      const ny = -settings.strength * slopeV;
      const length = Math.sqrt(nx * nx + ny * ny + 1);
      const at = (y * width + x) * 3;
      normals[at] = nx / length;
      normals[at + 1] = ny / length;
      normals[at + 2] = 1 / length;
    }
  }
  return normals;
}

/** The RGBA8 bytes of one unit normal: each component c becomes round((c * 0.5 + 0.5) * 255); alpha 255. */
export function encodeNormal(x, y, z, convention = 'opengl') {
  if (!CONVENTIONS.has(convention)) throw new RangeError('convention must be opengl or directx');
  const byte = (value) => Math.round((Math.min(Math.max(value, -1), 1) * 0.5 + 0.5) * 255);
  return [byte(x), byte(convention === 'opengl' ? y : -y), byte(z), 255];
}

/** The normal map as RGBA8 bytes, row 0 at v = 0 (the DataTexture layout); see normalsFromHeight for the options. */
export function normalMapFromHeight(heights, width, height, options = {}) {
  const settings = settingsOf(options);
  const normals = normalsFromHeight(heights, width, height, settings);
  const bytes = new Uint8Array(width * height * 4);
  for (let texel = 0; texel < width * height; texel += 1) {
    bytes.set(encodeNormal(normals[texel * 3], normals[texel * 3 + 1], normals[texel * 3 + 2], settings.convention), texel * 4);
  }
  return bytes;
}

/**
 * A three.js DataTexture for MeshStandardMaterial.normalMap: linear data (NoColorSpace), repeat or clamp wrapping,
 * linear filtering with mipmaps. Use the OpenGL convention with three.js.
 */
export function createNormalMapTexture(THREE, rgba, width, height, options = {}) {
  if (!(rgba instanceof Uint8Array) || rgba.length !== width * height * 4) {
    throw new RangeError('rgba must be a Uint8Array of width * height * 4 bytes');
  }
  for (const key of Object.keys(options)) if (key !== 'edges') throw new TypeError(`unknown texture option ${key}`);
  const edges = options.edges ?? NORMAL_MAP_DEFAULTS.edges;
  if (!EDGE_MODES.has(edges)) throw new RangeError('edges must be wrap or clamp');
  const texture = new THREE.DataTexture(rgba, width, height, THREE.RGBAFormat, THREE.UnsignedByteType);
  texture.colorSpace = THREE.NoColorSpace;
  texture.wrapS = edges === 'wrap' ? THREE.RepeatWrapping : THREE.ClampToEdgeWrapping;
  texture.wrapT = texture.wrapS;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.needsUpdate = true;
  return texture;
}
