// Film grain pass for three.js post-processing: per-cell noise from an integer hash of the cell, the frame number and
// a seed, shaped into a triangular distribution and weighted by a luminance response that is strongest in the
// mid-tones. Mono or per-channel grain, any grain cell size. The hash uses 32-bit unsigned integer arithmetic in GLSL
// ES 3.00 and the same arithmetic in JavaScript (Math.imul), so the CPU mirror reproduces every grain value. Original
// Baltor implementation.

/** Default options of createFilmGrainShader, createFilmGrainMaterial and the CPU mirror. */
export const FILM_GRAIN_DEFAULTS = Object.freeze({
  intensity: 0.08,
  response: 0.75,
  grainSize: 1,
  colored: false,
  frame: 0,
  seed: 0,
});

const SECOND_DRAW = 0x68e31da4;
const LUMA = Object.freeze([0.2126, 0.7152, 0.0722]);

/**
 * GLSL chunk: the 32-bit integer mix (xor-shift and multiply rounds), the cell hash and the triangular noise in
 * (-1, 1). Reusable in other shaders; grainHash and grainNoise take the frame, seed and channel explicitly.
 */
export const FILM_GRAIN_HASH_GLSL = `
uint grainMix(uint value) {
  value ^= value >> 16u;
  value *= 0x7feb352du;
  value ^= value >> 15u;
  value *= 0x846ca68bu;
  value ^= value >> 16u;
  return value;
}

uint grainHash(uvec2 cell, uint frame, uint seed, uint channel) {
  return grainMix(cell.x + grainMix(cell.y + grainMix(frame + grainMix(seed * 3u + channel))));
}

float grainNoise(uvec2 cell, uint frame, uint seed, uint channel) {
  uint first = grainHash(cell, frame, seed, channel);
  uint second = grainMix(first ^ 0x${SECOND_DRAW.toString(16)}u);
  return float(first >> 8u) / 16777216.0 + float(second >> 8u) / 16777216.0 - 1.0;
}
`;

/** Vertex stage for a full-screen triangle or quad (three.js ShaderPass supplies one). */
export const FILM_GRAIN_VERTEX = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

/** Fragment stage: grain cell from gl_FragCoord, luminance response, mono or per-channel grain added to the input. */
export const FILM_GRAIN_FRAGMENT = `
uniform sampler2D tDiffuse;
uniform float uIntensity;
uniform float uResponse;
uniform float uGrainSize;
uniform int uColored;
uniform int uFrame;
uniform int uSeed;
varying vec2 vUv;
${FILM_GRAIN_HASH_GLSL}
void main() {
  vec4 texel = texture2D(tDiffuse, vUv);
  uvec2 cell = uvec2(floor(gl_FragCoord.xy / uGrainSize));
  uint frame = uint(uFrame);
  uint seed = uint(uSeed);
  float luma = clamp(dot(texel.rgb, vec3(${LUMA.join(', ')})), 0.0, 1.0);
  float weight = uIntensity * mix(1.0, 4.0 * luma * (1.0 - luma), uResponse);
  vec3 grain = vec3(grainNoise(cell, frame, seed, 0u));
  if (uColored == 1) {
    grain.g = grainNoise(cell, frame, seed, 1u);
    grain.b = grainNoise(cell, frame, seed, 2u);
  }
  gl_FragColor = vec4(texel.rgb + grain * weight, texel.a);
  #include <colorspace_fragment>
}
`;

function mix32(value) {
  let x = value >>> 0;
  x = (x ^ (x >>> 16)) >>> 0;
  x = Math.imul(x, 0x7feb352d) >>> 0;
  x = (x ^ (x >>> 15)) >>> 0;
  x = Math.imul(x, 0x846ca68b) >>> 0;
  x = (x ^ (x >>> 16)) >>> 0;
  return x;
}

function unsigned(value, name) {
  if (!Number.isInteger(value) || value < 0 || value > 0xffffffff) {
    throw new RangeError(`${name} must be an integer from 0 to 4294967295, got ${value}`);
  }
  return value;
}

/**
 * CPU mirror of the shader's grainHash: the 32-bit hash of grain cell (x, y) for a frame, a seed and a channel (0, 1
 * or 2), as an unsigned integer.
 */
export function grainHash(x, y, frame, seed, channel) {
  unsigned(x, 'x');
  unsigned(y, 'y');
  unsigned(frame, 'frame');
  unsigned(seed, 'seed');
  const inner = mix32((Math.imul(seed, 3) + channel) >>> 0);
  return mix32((x + mix32((y + mix32((frame + inner) >>> 0)) >>> 0)) >>> 0);
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(FILM_GRAIN_DEFAULTS, key)) throw new TypeError(`unknown film grain option ${key}`);
  }
  const settings = {...FILM_GRAIN_DEFAULTS, ...options};
  for (const [key, low, high] of [['intensity', 0, 1], ['response', 0, 1]]) {
    if (!(typeof settings[key] === 'number' && settings[key] >= low && settings[key] <= high)) {
      throw new RangeError(`${key} must be a number in [${low}, ${high}], got ${settings[key]}`);
    }
  }
  if (!Number.isInteger(settings.grainSize) || settings.grainSize < 1 || settings.grainSize > 16) {
    throw new RangeError(`grainSize must be an integer from 1 to 16, got ${settings.grainSize}`);
  }
  if (typeof settings.colored !== 'boolean') throw new TypeError('colored must be true or false');
  for (const key of ['frame', 'seed']) {
    if (!Number.isInteger(settings[key]) || settings[key] < 0 || settings[key] > 0x7fffffff) {
      throw new RangeError(`${key} must be an integer from 0 to 2147483647 (a GLSL int uniform)`);
    }
  }
  return settings;
}

/**
 * CPU mirror of the grain at output pixel (x, y) (from the bottom-left): one triangular noise value in (-1, 1) per
 * channel, all three equal for mono grain.
 */
export function grainValue(x, y, options = {}) {
  const settings = settingsOf(options);
  const cellX = Math.floor(x / settings.grainSize);
  const cellY = Math.floor(y / settings.grainSize);
  const noise = (channel) => {
    const first = grainHash(cellX, cellY, settings.frame, settings.seed, channel);
    const second = mix32((first ^ SECOND_DRAW) >>> 0);
    return (first >>> 8) / 16777216 + (second >>> 8) / 16777216 - 1;
  };
  const mono = noise(0);
  return settings.colored ? [mono, noise(1), noise(2)] : [mono, mono, mono];
}

/** The grain weight for a colour: intensity * mix(1, 4 L (1 - L), response), L its clamped Rec. 709 luminance. */
export function grainWeight(rgb, options = {}) {
  const settings = settingsOf(options);
  const luma = Math.min(Math.max(LUMA[0] * rgb[0] + LUMA[1] * rgb[1] + LUMA[2] * rgb[2], 0), 1);
  return settings.intensity * (1 + (4 * luma * (1 - luma) - 1) * settings.response);
}

/** CPU mirror of the whole pass for the colour rgb at output pixel (x, y): rgb + grain * weight. */
export function applyGrainCpu(rgb, x, y, options = {}) {
  const weight = grainWeight(rgb, options);
  const grain = grainValue(x, y, options);
  return rgb.map((value, channel) => value + grain[channel] * weight);
}

/**
 * A new shader definition {name, uniforms, vertexShader, fragmentShader} for three.js ShaderPass (input texture
 * uniform tDiffuse) or ShaderMaterial. Increase uniforms.uFrame.value every frame for moving grain.
 */
export function createFilmGrainShader(options = {}) {
  const settings = settingsOf(options);
  return {
    name: 'BaltorFilmGrainShader',
    uniforms: {
      tDiffuse: {value: null},
      uIntensity: {value: settings.intensity},
      uResponse: {value: settings.response},
      uGrainSize: {value: settings.grainSize},
      uColored: {value: settings.colored ? 1 : 0},
      uFrame: {value: settings.frame},
      uSeed: {value: settings.seed},
    },
    vertexShader: FILM_GRAIN_VERTEX,
    fragmentShader: FILM_GRAIN_FRAGMENT,
  };
}

/** A THREE.ShaderMaterial for a full-screen pass; set uniforms.tDiffuse.value to the input texture. */
export function createFilmGrainMaterial(THREE, options = {}) {
  const material = new THREE.ShaderMaterial(createFilmGrainShader(options));
  material.depthTest = false;
  material.depthWrite = false;
  return material;
}
