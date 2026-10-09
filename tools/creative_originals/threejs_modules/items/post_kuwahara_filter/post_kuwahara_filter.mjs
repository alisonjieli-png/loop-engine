// Kuwahara filter pass for three.js post-processing: for each pixel the four overlapping square quadrants that meet
// at it (radius 1 to 6) are measured, and the pixel takes the mean colour of the quadrant whose luminance varies
// least. Flat areas become painterly patches while edges stay sharp, because the quadrant that lies on one side of
// an edge always wins. Original Baltor implementation with an exact CPU mirror on RGBA float arrays.

/** Default options of createKuwaharaShader and createKuwaharaMaterial. */
export const KUWAHARA_DEFAULTS = Object.freeze({
  radius: 3,
  resolution: Object.freeze([1024, 1024]),
});

const MAXIMUM_RADIUS = 6;
const LUMA = Object.freeze([0.2126, 0.7152, 0.0722]);
/** Quadrant directions in output order: lower left, lower right, upper left, upper right (rows from the bottom). */
const QUADRANTS = Object.freeze([[-1, -1], [1, -1], [-1, 1], [1, 1]]);

/** Vertex stage for a full-screen triangle or quad (three.js ShaderPass supplies one). */
export const KUWAHARA_VERTEX = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

/** Fragment stage: mean and luminance variance of four quadrants, the least varied wins (the first on a tie). */
export const KUWAHARA_FRAGMENT = `
uniform sampler2D tDiffuse;
uniform vec2 uTexelSize;
uniform int uRadius;
varying vec2 vUv;

void kuwaharaQuadrant(vec2 direction, out vec3 mean, out float variance) {
  vec3 sum = vec3(0.0);
  float lumaSum = 0.0;
  float lumaSquares = 0.0;
  float count = 0.0;
  for (int j = 0; j <= ${MAXIMUM_RADIUS}; j++) {
    if (j > uRadius) break;
    for (int i = 0; i <= ${MAXIMUM_RADIUS}; i++) {
      if (i > uRadius) break;
      vec3 colour = texture2D(tDiffuse, vUv + vec2(float(i) * direction.x, float(j) * direction.y) * uTexelSize).rgb;
      float luma = dot(colour, vec3(${LUMA.join(', ')}));
      sum += colour;
      lumaSum += luma;
      lumaSquares += luma * luma;
      count += 1.0;
    }
  }
  mean = sum / count;
  float lumaMean = lumaSum / count;
  variance = lumaSquares / count - lumaMean * lumaMean;
}

void main() {
  vec3 bestMean;
  float bestVariance;
  kuwaharaQuadrant(vec2(-1.0, -1.0), bestMean, bestVariance);
  vec3 mean;
  float variance;
  kuwaharaQuadrant(vec2(1.0, -1.0), mean, variance);
  if (variance < bestVariance) { bestMean = mean; bestVariance = variance; }
  kuwaharaQuadrant(vec2(-1.0, 1.0), mean, variance);
  if (variance < bestVariance) { bestMean = mean; bestVariance = variance; }
  kuwaharaQuadrant(vec2(1.0, 1.0), mean, variance);
  if (variance < bestVariance) { bestMean = mean; bestVariance = variance; }
  gl_FragColor = vec4(bestMean, texture2D(tDiffuse, vUv).a);
  #include <colorspace_fragment>
}
`;

function checkRadius(radius) {
  if (!Number.isInteger(radius) || radius < 1 || radius > MAXIMUM_RADIUS) {
    throw new RangeError(`radius must be an integer from 1 to ${MAXIMUM_RADIUS}, got ${radius}`);
  }
}

function checkImage(data, width, height) {
  if (!(Number.isInteger(width) && Number.isInteger(height) && width >= 1 && height >= 1)) {
    throw new RangeError('width and height must be positive integers');
  }
  if (!(ArrayBuffer.isView(data) || Array.isArray(data)) || data.length !== width * height * 4) {
    throw new TypeError(`expected ${width * height * 4} RGBA values`);
  }
}

/**
 * CPU mirror of the four quadrant measurements at pixel (x, y) of a row-major RGBA image (rows from the bottom,
 * outside reads clamped to the edge): [{mean: [r, g, b], variance}] for lower left, lower right, upper left, upper
 * right. Variance is that of Rec. 709 luminance, E[L^2] - E[L]^2.
 */
export function kuwaharaQuadrants(data, width, height, x, y, radius) {
  checkImage(data, width, height);
  checkRadius(radius);
  return QUADRANTS.map(([dx, dy]) => {
    const sum = [0, 0, 0];
    let lumaSum = 0;
    let lumaSquares = 0;
    let count = 0;
    for (let j = 0; j <= radius; j += 1) {
      for (let i = 0; i <= radius; i += 1) {
        const column = Math.min(Math.max(x + i * dx, 0), width - 1);
        const row = Math.min(Math.max(y + j * dy, 0), height - 1);
        const base = (row * width + column) * 4;
        const luma = LUMA[0] * data[base] + LUMA[1] * data[base + 1] + LUMA[2] * data[base + 2];
        for (let channel = 0; channel < 3; channel += 1) sum[channel] += data[base + channel];
        lumaSum += luma;
        lumaSquares += luma * luma;
        count += 1;
      }
    }
    const lumaMean = lumaSum / count;
    return {mean: sum.map((value) => value / count), variance: lumaSquares / count - lumaMean * lumaMean};
  });
}

/** CPU mirror of one output pixel: the mean of the least varied quadrant (the first on a tie) and the centre alpha. */
export function kuwaharaPixel(data, width, height, x, y, radius) {
  const quadrants = kuwaharaQuadrants(data, width, height, x, y, radius);
  let best = quadrants[0];
  for (const quadrant of quadrants.slice(1)) {
    if (quadrant.variance < best.variance) best = quadrant;
  }
  return [...best.mean, data[(y * width + x) * 4 + 3]];
}

/** CPU mirror of the whole pass: a new Float32Array RGBA image. */
export function kuwaharaImage(data, width, height, radius) {
  checkImage(data, width, height);
  const out = new Float32Array(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) out.set(kuwaharaPixel(data, width, height, x, y, radius), (y * width + x) * 4);
  }
  return out;
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(KUWAHARA_DEFAULTS, key)) throw new TypeError(`unknown Kuwahara option ${key}`);
  }
  const settings = {...KUWAHARA_DEFAULTS, ...options};
  checkRadius(settings.radius);
  const resolution = settings.resolution;
  if (!(Array.isArray(resolution) && resolution.length === 2 && resolution.every((value) => Number.isInteger(value)
      && value >= 1 && value <= 16384))) {
    throw new RangeError('resolution must be [width, height] in pixels');
  }
  return settings;
}

/**
 * A new shader definition {name, uniforms, vertexShader, fragmentShader} for three.js ShaderPass (input texture
 * uniform tDiffuse) or ShaderMaterial. Set uTexelSize to [1 / width, 1 / height] of the input when it is resized.
 */
export function createKuwaharaShader(options = {}) {
  const settings = settingsOf(options);
  return {
    name: 'BaltorKuwaharaShader',
    uniforms: {
      tDiffuse: {value: null},
      uTexelSize: {value: [1 / settings.resolution[0], 1 / settings.resolution[1]]},
      uRadius: {value: settings.radius},
    },
    vertexShader: KUWAHARA_VERTEX,
    fragmentShader: KUWAHARA_FRAGMENT,
  };
}

/** A THREE.ShaderMaterial for a full-screen pass; set uniforms.tDiffuse.value to the input texture. */
export function createKuwaharaMaterial(THREE, options = {}) {
  const material = new THREE.ShaderMaterial(createKuwaharaShader(options));
  material.depthTest = false;
  material.depthWrite = false;
  return material;
}
