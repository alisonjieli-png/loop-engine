// Chromatic aberration pass for three.js post-processing: each colour channel is scaled about a centre by a slightly
// different factor, red magnified and blue shrunk, by an amount that grows with distance from the centre. Optional
// dispersion spreads the samples along the red-to-blue line and weights them into the three channels. Original Baltor
// implementation; the shader definition is a plain object three.js ShaderPass and ShaderMaterial both accept, and
// the sample coordinates have an exact CPU mirror.

/** Default options of createChromaticAberrationShader and createChromaticAberrationMaterial. */
export const CHROMATIC_ABERRATION_DEFAULTS = Object.freeze({
  strength: 0.012,
  power: 1,
  center: Object.freeze([0.5, 0.5]),
  aspect: 1,
  samples: 1,
});

const MAXIMUM_SAMPLES = 8;
const RADIUS_FLOOR = 1e-8;
// Dispersion: a sample at position t on the red (0) to blue (1) line feeds each channel with a triangular weight of
// half width SPREAD around the channel's own position.
const CHANNEL_POSITIONS = Object.freeze([0, 0.5, 1]);
const SPREAD = 0.75;

/** Vertex stage for a full-screen triangle or quad (three.js ShaderPass supplies one). */
export const CHROMATIC_ABERRATION_VERTEX = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

/** Fragment stage: three taps (one per channel) or up to eight dispersion taps along the red-to-blue line. */
export const CHROMATIC_ABERRATION_FRAGMENT = `
uniform sampler2D tDiffuse;
uniform float uStrength;
uniform float uPower;
uniform vec2 uCenter;
uniform float uAspect;
uniform int uSamples;
varying vec2 vUv;

float aberrationScale(vec2 offset) {
  float radius = 2.0 * length(offset * vec2(uAspect, 1.0));
  return uStrength * pow(max(radius, ${RADIUS_FLOOR.toExponential()}), uPower);
}

vec3 dispersionWeight(float t) {
  return max(vec3(0.0), 1.0 - abs(t - vec3(0.0, 0.5, 1.0)) / ${SPREAD.toFixed(2)});
}

void main() {
  vec2 offset = vUv - uCenter;
  float scale = aberrationScale(offset);
  vec4 centre = texture2D(tDiffuse, vUv);
  vec3 colour;
  if (uSamples <= 1) {
    float red = texture2D(tDiffuse, uCenter + offset * (1.0 - scale)).r;
    float blue = texture2D(tDiffuse, uCenter + offset * (1.0 + scale)).b;
    colour = vec3(red, centre.g, blue);
  } else {
    vec3 sum = vec3(0.0);
    vec3 total = vec3(0.0);
    for (int i = 0; i < ${MAXIMUM_SAMPLES}; i++) {
      if (i >= uSamples) break;
      float t = float(i) / float(uSamples - 1);
      vec3 weight = dispersionWeight(t);
      sum += weight * texture2D(tDiffuse, uCenter + offset * (1.0 - scale + 2.0 * scale * t)).rgb;
      total += weight;
    }
    colour = sum / total;
  }
  gl_FragColor = vec4(colour, centre.a);
  #include <colorspace_fragment>
}
`;

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(CHROMATIC_ABERRATION_DEFAULTS, key)) throw new TypeError(`unknown chromatic aberration option ${key}`);
  }
  const settings = {...CHROMATIC_ABERRATION_DEFAULTS, ...options};
  const ranges = {strength: [-0.5, 0.5], power: [0, 8], aspect: [0.01, 100]};
  for (const [key, [low, high]] of Object.entries(ranges)) {
    if (!(typeof settings[key] === 'number' && settings[key] >= low && settings[key] <= high)) {
      throw new RangeError(`${key} must be a number in [${low}, ${high}], got ${settings[key]}`);
    }
  }
  const center = settings.center;
  if (!(Array.isArray(center) && center.length === 2 && center.every((value) => value >= 0 && value <= 1))) {
    throw new TypeError('center must be [u, v] with both in [0, 1]');
  }
  if (!Number.isInteger(settings.samples) || settings.samples < 1 || settings.samples > MAXIMUM_SAMPLES) {
    throw new RangeError(`samples must be an integer from 1 to ${MAXIMUM_SAMPLES}, got ${settings.samples}`);
  }
  return settings;
}

function scaleAt(du, dv, settings) {
  const radius = 2 * Math.hypot(du * settings.aspect, dv);
  return settings.strength * Math.max(radius, RADIUS_FLOOR) ** settings.power;
}

/**
 * CPU mirror of the three-tap path: the texture coordinate each channel samples for the output pixel at (u, v).
 * Red samples toward the centre (its image is magnified), blue away from it, green at (u, v). The scale is
 * strength * r^power, where r is 0 at the centre and 1 at the middle of the top edge (aspect = width / height).
 */
export function aberrationOffset(u, v, options = {}) {
  const settings = settingsOf(options);
  const [cu, cv] = settings.center;
  const du = u - cu;
  const dv = v - cv;
  const scale = scaleAt(du, dv, settings);
  return {
    red: [cu + du * (1 - scale), cv + dv * (1 - scale)],
    green: [u, v],
    blue: [cu + du * (1 + scale), cv + dv * (1 + scale)],
  };
}

/**
 * Per-sample channel weights of the dispersion path for a sample count of 2 to 8: one [red, green, blue] row per
 * sample from the red end to the blue end, each channel normalized to sum to 1.
 */
export function dispersionWeights(samples) {
  if (!Number.isInteger(samples) || samples < 2 || samples > MAXIMUM_SAMPLES) {
    throw new RangeError(`dispersion needs 2 to ${MAXIMUM_SAMPLES} samples, got ${samples}`);
  }
  const rows = [];
  const totals = [0, 0, 0];
  for (let index = 0; index < samples; index += 1) {
    const t = index / (samples - 1);
    const row = CHANNEL_POSITIONS.map((position) => Math.max(0, 1 - Math.abs(t - position) / SPREAD));
    row.forEach((weight, channel) => { totals[channel] += weight; });
    rows.push(row);
  }
  return rows.map((row) => row.map((weight, channel) => weight / totals[channel]));
}

/**
 * CPU mirror of the dispersion path: for the output pixel at (u, v), every tap's texture coordinate and its
 * normalized [red, green, blue] weights. With samples = 1 it gives the three taps of aberrationOffset.
 */
export function dispersionTaps(u, v, options = {}) {
  const settings = settingsOf(options);
  if (settings.samples === 1) {
    const offsets = aberrationOffset(u, v, options);
    return [
      {uv: offsets.red, weights: [1, 0, 0]},
      {uv: offsets.green, weights: [0, 1, 0]},
      {uv: offsets.blue, weights: [0, 0, 1]},
    ];
  }
  const [cu, cv] = settings.center;
  const du = u - cu;
  const dv = v - cv;
  const scale = scaleAt(du, dv, settings);
  return dispersionWeights(settings.samples).map((weights, index) => {
    const t = index / (settings.samples - 1);
    const factor = 1 - scale + 2 * scale * t;
    return {uv: [cu + du * factor, cv + dv * factor], weights};
  });
}

/**
 * A new shader definition {name, uniforms, vertexShader, fragmentShader} for three.js ShaderPass (input texture
 * uniform tDiffuse) or ShaderMaterial. The centre is a plain [u, v] array, which three.js uploads as vec2.
 */
export function createChromaticAberrationShader(options = {}) {
  const settings = settingsOf(options);
  return {
    name: 'BaltorChromaticAberrationShader',
    uniforms: {
      tDiffuse: {value: null},
      uStrength: {value: settings.strength},
      uPower: {value: settings.power},
      uCenter: {value: [...settings.center]},
      uAspect: {value: settings.aspect},
      uSamples: {value: settings.samples},
    },
    vertexShader: CHROMATIC_ABERRATION_VERTEX,
    fragmentShader: CHROMATIC_ABERRATION_FRAGMENT,
  };
}

/** A THREE.ShaderMaterial for a full-screen pass; set uniforms.tDiffuse.value to the input texture. */
export function createChromaticAberrationMaterial(THREE, options = {}) {
  const material = new THREE.ShaderMaterial(createChromaticAberrationShader(options));
  material.depthTest = false;
  material.depthWrite = false;
  return material;
}
