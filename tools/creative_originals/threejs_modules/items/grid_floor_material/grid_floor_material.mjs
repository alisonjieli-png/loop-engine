// Editor ground grid for three.js: minor and major lines of a fixed width in pixels, anti-aliased from screen-space
// derivatives (fwidth), coloured X and Z axis lines through the origin, and a fade with distance from the camera.
// Lines whose cells shrink below a few pixels fade out instead of shimmering. Original Baltor implementation; three.js
// is passed in, nothing is imported.

/** Default options of createGridFloorMaterial. Spacings are world units; widths are pixels; colours linear RGB. */
export const GRID_FLOOR_DEFAULTS = Object.freeze({
  minorSpacing: 1,
  majorSpacing: 10,
  minorLineWidth: 1,
  majorLineWidth: 1.6,
  axisLineWidth: 2.2,
  minorColor: Object.freeze([0.33, 0.35, 0.4]),
  majorColor: Object.freeze([0.55, 0.58, 0.64]),
  xAxisColor: Object.freeze([0.85, 0.2, 0.2]),
  zAxisColor: Object.freeze([0.2, 0.4, 0.95]),
  fadeStart: 15,
  fadeEnd: 45,
  opacity: 1,
});

const MINIMUM_FOOTPRINT = 1e-6;
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

/**
 * GLSL chunk: coverage (0 to 1) of the nearest grid line and of an axis line at a coordinate, given the world size of
 * one pixel there (the material passes fwidth of the coordinate).
 */
export const GRID_FLOOR_GLSL = `
float gridLineCoverage(float coordinate, float spacing, float lineWidthPixels, float pixelFootprint) {
  float footprint = max(pixelFootprint, ${MINIMUM_FOOTPRINT.toExponential()});
  float distancePixels = abs(fract(coordinate / spacing - 0.5) - 0.5) * spacing / footprint;
  float halfWidth = lineWidthPixels * 0.5;
  float coverage = (1.0 - smoothstep(halfWidth - 0.5, halfWidth + 0.5, distancePixels)) * min(lineWidthPixels, 1.0);
  return coverage * smoothstep(1.5, 4.0, spacing / footprint);
}

float gridAxisCoverage(float coordinate, float lineWidthPixels, float pixelFootprint) {
  float distancePixels = abs(coordinate) / max(pixelFootprint, ${MINIMUM_FOOTPRINT.toExponential()});
  float halfWidth = lineWidthPixels * 0.5;
  return (1.0 - smoothstep(halfWidth - 0.5, halfWidth + 0.5, distancePixels)) * min(lineWidthPixels, 1.0);
}

float gridFade(float distanceToCamera, float fadeStart, float fadeEnd) {
  return 1.0 - smoothstep(fadeStart, max(fadeEnd, fadeStart + 1e-3), distanceToCamera);
}
`;

/** Vertex stage: world position for the grid coordinates. */
export const GRID_FLOOR_VERTEX = `
varying vec3 vWorldPosition;

void main() {
  vec4 world = modelMatrix * vec4(position, 1.0);
  vWorldPosition = world.xyz;
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

/** Fragment stage: minor, major and axis lines on world x and z, faded with distance, written with alpha. */
export const GRID_FLOOR_FRAGMENT = `
uniform float uMinorSpacing;
uniform float uMajorSpacing;
uniform float uMinorLineWidth;
uniform float uMajorLineWidth;
uniform float uAxisLineWidth;
uniform vec3 uMinorColor;
uniform vec3 uMajorColor;
uniform vec3 uXAxisColor;
uniform vec3 uZAxisColor;
uniform float uFadeStart;
uniform float uFadeEnd;
uniform float uOpacity;
varying vec3 vWorldPosition;
${GRID_FLOOR_GLSL}
void main() {
  vec2 coordinate = vWorldPosition.xz;
  vec2 footprint = fwidth(coordinate);
  float minor = max(gridLineCoverage(coordinate.x, uMinorSpacing, uMinorLineWidth, footprint.x),
                    gridLineCoverage(coordinate.y, uMinorSpacing, uMinorLineWidth, footprint.y));
  float major = max(gridLineCoverage(coordinate.x, uMajorSpacing, uMajorLineWidth, footprint.x),
                    gridLineCoverage(coordinate.y, uMajorSpacing, uMajorLineWidth, footprint.y));
  float alongX = gridAxisCoverage(coordinate.y, uAxisLineWidth, footprint.y);
  float alongZ = gridAxisCoverage(coordinate.x, uAxisLineWidth, footprint.x);
  vec3 colour = mix(uMinorColor, uMajorColor, major);
  colour = mix(colour, uZAxisColor, alongZ);
  colour = mix(colour, uXAxisColor, alongX);
  float alpha = max(max(minor, major), max(alongX, alongZ));
  float fade = gridFade(distance(cameraPosition.xz, vWorldPosition.xz), uFadeStart, uFadeEnd);
  gl_FragColor = vec4(colour, alpha * fade * uOpacity);
  #include <colorspace_fragment>
}
`;

function smoothstep(edge0, edge1, x) {
  const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1);
  return t * t * (3 - 2 * t);
}

function positive(value, name) {
  if (!(typeof value === 'number' && value > 0 && Number.isFinite(value))) throw new RangeError(`${name} must be positive`);
  return value;
}

function finite(value, name) {
  if (!(typeof value === 'number' && Number.isFinite(value))) throw new TypeError(`${name} must be a finite number`);
  return value;
}

/**
 * CPU mirror of the grid line coverage: how much of the pixel at `coordinate` (world units along x or z) the nearest
 * line of a grid with `spacing` covers, for lines `lineWidthPixels` wide and pixels `pixelFootprint` world units wide.
 * Grids whose cells are under about 4 pixels fade toward 0 to avoid moire.
 */
export function gridLineCoverage(coordinate, spacing, lineWidthPixels, pixelFootprint) {
  finite(coordinate, 'coordinate');
  positive(spacing, 'spacing');
  positive(lineWidthPixels, 'lineWidthPixels');
  finite(pixelFootprint, 'pixelFootprint');
  const footprint = Math.max(pixelFootprint, MINIMUM_FOOTPRINT);
  const cell = coordinate / spacing - 0.5;
  const distancePixels = Math.abs(cell - Math.floor(cell) - 0.5) * spacing / footprint;
  const half = lineWidthPixels * 0.5;
  const coverage = (1 - smoothstep(half - 0.5, half + 0.5, distancePixels)) * Math.min(lineWidthPixels, 1);
  return coverage * smoothstep(1.5, 4, spacing / footprint);
}

/** CPU mirror of the axis line coverage: the line through coordinate 0, `lineWidthPixels` wide. */
export function gridAxisCoverage(coordinate, lineWidthPixels, pixelFootprint) {
  finite(coordinate, 'coordinate');
  positive(lineWidthPixels, 'lineWidthPixels');
  finite(pixelFootprint, 'pixelFootprint');
  const distancePixels = Math.abs(coordinate) / Math.max(pixelFootprint, MINIMUM_FOOTPRINT);
  const half = lineWidthPixels * 0.5;
  return (1 - smoothstep(half - 0.5, half + 0.5, distancePixels)) * Math.min(lineWidthPixels, 1);
}

/** CPU mirror of the distance fade: 1 up to fadeStart, 0 from fadeEnd, smooth between. */
export function gridFade(distanceToCamera, fadeStart, fadeEnd) {
  finite(distanceToCamera, 'distanceToCamera');
  finite(fadeStart, 'fadeStart');
  finite(fadeEnd, 'fadeEnd');
  return 1 - smoothstep(fadeStart, Math.max(fadeEnd, fadeStart + 1e-3), distanceToCamera);
}

function colour(THREE, value, name) {
  if (Array.isArray(value) && value.length === 3 && value.every(Number.isFinite)) {
    return new THREE.Color(value[0], value[1], value[2]);
  }
  if (typeof value === 'number' || typeof value === 'string' || (value && value.isColor)) return new THREE.Color(value);
  throw new TypeError(`${name} must be a linear RGB triple, a hex number, a CSS colour string or a THREE.Color`);
}

function inRange(value, low, high, name) {
  if (!(typeof value === 'number' && value >= low && value <= high)) {
    throw new RangeError(`${name} must be a number in [${low}, ${high}], got ${value}`);
  }
  return value;
}

/**
 * A transparent, double-sided THREE.ShaderMaterial for a large horizontal plane (for example a 1000 x 1000
 * PlaneGeometry rotated by -pi/2 about X). Options (all optional) are the keys of GRID_FLOOR_DEFAULTS; an unknown key
 * throws TypeError. It writes no depth, so objects below the plane still show through the gaps.
 */
export function createGridFloorMaterial(THREE, options = {}) {
  for (const key of Object.keys(options)) {
    if (!own(GRID_FLOOR_DEFAULTS, key)) throw new TypeError(`unknown grid floor option ${key}`);
  }
  const s = {...GRID_FLOOR_DEFAULTS, ...options};
  if (!(s.fadeEnd >= s.fadeStart)) throw new RangeError('fadeEnd must not be smaller than fadeStart');
  return new THREE.ShaderMaterial({
    name: 'BaltorGridFloorMaterial',
    uniforms: {
      uMinorSpacing: {value: inRange(s.minorSpacing, 1e-6, 1e6, 'minorSpacing')},
      uMajorSpacing: {value: inRange(s.majorSpacing, 1e-6, 1e6, 'majorSpacing')},
      uMinorLineWidth: {value: inRange(s.minorLineWidth, 0.01, 64, 'minorLineWidth')},
      uMajorLineWidth: {value: inRange(s.majorLineWidth, 0.01, 64, 'majorLineWidth')},
      uAxisLineWidth: {value: inRange(s.axisLineWidth, 0.01, 64, 'axisLineWidth')},
      uMinorColor: {value: colour(THREE, s.minorColor, 'minorColor')},
      uMajorColor: {value: colour(THREE, s.majorColor, 'majorColor')},
      uXAxisColor: {value: colour(THREE, s.xAxisColor, 'xAxisColor')},
      uZAxisColor: {value: colour(THREE, s.zAxisColor, 'zAxisColor')},
      uFadeStart: {value: inRange(s.fadeStart, 0, 1e7, 'fadeStart')},
      uFadeEnd: {value: inRange(s.fadeEnd, 0, 1e7, 'fadeEnd')},
      uOpacity: {value: inRange(s.opacity, 0, 1, 'opacity')},
    },
    vertexShader: GRID_FLOOR_VERTEX,
    fragmentShader: GRID_FLOOR_FRAGMENT,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}
