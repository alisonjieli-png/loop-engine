// Sobel edge pass for three.js post-processing: the luminance gradient of each pixel's 3 x 3 neighbourhood becomes a
// soft edge mask, drawn as an outline over the image or alone over a background colour. Original Baltor
// implementation; the shader definition is a plain object three.js ShaderPass and ShaderMaterial both accept, and the
// gradient and mask have an exact CPU mirror on luminance arrays.

/** Output modes: the outline drawn over the image, or the edges alone over the background colour. */
export const SOBEL_EDGE_MODES = Object.freeze({overlay: 0, edges: 1});

/** Default options of createSobelEdgesShader, createSobelEdgesMaterial and sobelEdgeMask. */
export const SOBEL_EDGES_DEFAULTS = Object.freeze({
  threshold: 0.2,
  softness: 0.1,
  outlineColor: Object.freeze([0.03, 0.025, 0.05]),
  backgroundColor: Object.freeze([1, 1, 1]),
  mode: 'overlay',
  opacity: 1,
  resolution: Object.freeze([1024, 1024]),
});

const MINIMUM_SOFTNESS = 1e-4;
/** Rec. 709 luminance weights, applied to the values the pass receives. */
const LUMA = Object.freeze([0.2126, 0.7152, 0.0722]);

/** Vertex stage for a full-screen triangle or quad (three.js ShaderPass supplies one). */
export const SOBEL_EDGES_VERTEX = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

/** Fragment stage: 3 x 3 Sobel on luminance, a smoothstep mask, then overlay or edges-only output. */
export const SOBEL_EDGES_FRAGMENT = `
uniform sampler2D tDiffuse;
uniform vec2 uTexelSize;
uniform float uThreshold;
uniform float uSoftness;
uniform vec3 uOutlineColor;
uniform vec3 uBackgroundColor;
uniform int uMode;
uniform float uOpacity;
varying vec2 vUv;

float lumaAt(float dx, float dy) {
  vec3 rgb = texture2D(tDiffuse, vUv + vec2(dx, dy) * uTexelSize).rgb;
  return dot(rgb, vec3(${LUMA.join(', ')}));
}

float sobelMagnitude() {
  float a = lumaAt(-1.0, -1.0);
  float b = lumaAt(0.0, -1.0);
  float c = lumaAt(1.0, -1.0);
  float d = lumaAt(-1.0, 0.0);
  float f = lumaAt(1.0, 0.0);
  float g = lumaAt(-1.0, 1.0);
  float h = lumaAt(0.0, 1.0);
  float i = lumaAt(1.0, 1.0);
  float gx = (c + 2.0 * f + i) - (a + 2.0 * d + g);
  float gy = (g + 2.0 * h + i) - (a + 2.0 * b + c);
  return sqrt(gx * gx + gy * gy);
}

void main() {
  vec4 texel = texture2D(tDiffuse, vUv);
  float width = max(uSoftness, ${MINIMUM_SOFTNESS.toExponential()});
  float mask = smoothstep(uThreshold - width, uThreshold + width, sobelMagnitude()) * uOpacity;
  vec3 base = uMode == 1 ? uBackgroundColor : texel.rgb;
  gl_FragColor = vec4(mix(base, uOutlineColor, mask), texel.a);
  #include <colorspace_fragment>
}
`;

function smoothstep(edge0, edge1, x) {
  const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1);
  return t * t * (3 - 2 * t);
}

function triple(value, name) {
  if (!(Array.isArray(value) && value.length === 3 && value.every(Number.isFinite))) {
    throw new TypeError(`${name} must be a linear RGB triple`);
  }
  return [...value];
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(SOBEL_EDGES_DEFAULTS, key)) throw new TypeError(`unknown Sobel edges option ${key}`);
  }
  const settings = {...SOBEL_EDGES_DEFAULTS, ...options};
  const ranges = {threshold: [0, 8], softness: [0, 4], opacity: [0, 1]};
  for (const [key, [low, high]] of Object.entries(ranges)) {
    if (!(typeof settings[key] === 'number' && settings[key] >= low && settings[key] <= high)) {
      throw new RangeError(`${key} must be a number in [${low}, ${high}], got ${settings[key]}`);
    }
  }
  if (!Object.prototype.hasOwnProperty.call(SOBEL_EDGE_MODES, settings.mode)) throw new TypeError(`mode must be one of ${Object.keys(SOBEL_EDGE_MODES)}`);
  const resolution = settings.resolution;
  if (!(Array.isArray(resolution) && resolution.length === 2 && resolution.every((value) => Number.isInteger(value)
      && value >= 1 && value <= 16384))) {
    throw new RangeError('resolution must be [width, height] in pixels');
  }
  triple(settings.outlineColor, 'outlineColor');
  triple(settings.backgroundColor, 'backgroundColor');
  return settings;
}

/** Rec. 709 luminance of a linear RGB value. */
export function luminance(r, g, b) {
  return LUMA[0] * r + LUMA[1] * g + LUMA[2] * b;
}

/**
 * CPU mirror of the shader's gradient: the Sobel magnitude at pixel (x, y) of a row-major luminance array, rows from
 * the bottom (texture order), reading outside the image as the nearest edge pixel (clamp to edge).
 */
export function sobelMagnitude(luma, width, height, x, y) {
  if (luma.length !== width * height) throw new RangeError(`expected ${width * height} values, got ${luma.length}`);
  const at = (dx, dy) => {
    const column = Math.min(Math.max(x + dx, 0), width - 1);
    const row = Math.min(Math.max(y + dy, 0), height - 1);
    return luma[row * width + column];
  };
  const gx = (at(1, -1) + 2 * at(1, 0) + at(1, 1)) - (at(-1, -1) + 2 * at(-1, 0) + at(-1, 1));
  const gy = (at(-1, 1) + 2 * at(0, 1) + at(1, 1)) - (at(-1, -1) + 2 * at(0, -1) + at(1, -1));
  return Math.sqrt(gx * gx + gy * gy);
}

/** CPU mirror of the mask: smoothstep(threshold - softness, threshold + softness, magnitude) * opacity per pixel. */
export function sobelEdgeMask(luma, width, height, options = {}) {
  const settings = settingsOf(options);
  const widthOfEdge = Math.max(settings.softness, MINIMUM_SOFTNESS);
  const mask = new Float32Array(width * height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const magnitude = sobelMagnitude(luma, width, height, x, y);
      mask[y * width + x] = smoothstep(settings.threshold - widthOfEdge, settings.threshold + widthOfEdge, magnitude)
        * settings.opacity;
    }
  }
  return mask;
}

/**
 * A new shader definition {name, uniforms, vertexShader, fragmentShader} for three.js ShaderPass (input texture
 * uniform tDiffuse) or ShaderMaterial. Set uTexelSize to [1 / width, 1 / height] of the input when it is resized.
 */
export function createSobelEdgesShader(options = {}) {
  const settings = settingsOf(options);
  return {
    name: 'BaltorSobelEdgesShader',
    uniforms: {
      tDiffuse: {value: null},
      uTexelSize: {value: [1 / settings.resolution[0], 1 / settings.resolution[1]]},
      uThreshold: {value: settings.threshold},
      uSoftness: {value: settings.softness},
      uOutlineColor: {value: triple(settings.outlineColor, 'outlineColor')},
      uBackgroundColor: {value: triple(settings.backgroundColor, 'backgroundColor')},
      uMode: {value: SOBEL_EDGE_MODES[settings.mode]},
      uOpacity: {value: settings.opacity},
    },
    vertexShader: SOBEL_EDGES_VERTEX,
    fragmentShader: SOBEL_EDGES_FRAGMENT,
  };
}

/** A THREE.ShaderMaterial for a full-screen pass; set uniforms.tDiffuse.value to the input texture. */
export function createSobelEdgesMaterial(THREE, options = {}) {
  const material = new THREE.ShaderMaterial(createSobelEdgesShader(options));
  material.depthTest = false;
  material.depthWrite = false;
  return material;
}
