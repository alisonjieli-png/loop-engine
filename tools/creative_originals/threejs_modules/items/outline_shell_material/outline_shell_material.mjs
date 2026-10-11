// Inverted-hull outline for three.js with a constant width in pixels: a second mesh that shares the geometry draws
// only back faces, with every vertex pushed along its projected normal in clip space by a fixed number of pixels, so
// a band of outline colour shows around the silhouette at any distance. Original Baltor implementation; THREE is
// passed in, nothing is imported.

/** Default options. color is linear RGB; width is in pixels of the drawing buffer given by resolution. */
export const OUTLINE_SHELL_DEFAULTS = Object.freeze({
  color: Object.freeze([0.02, 0.02, 0.03]),
  width: 3,
  opacity: 1,
  resolution: Object.freeze([1024, 1024]),
});

/** GLSL chunk: the clip-space position pushed widthPixels along the screen direction of the clip-space normal. */
export const OUTLINE_GLSL = `
vec4 outlineClipOffset(vec4 clipPosition, vec4 clipNormal, float widthPixels, vec2 resolution) {
  vec2 screenNormal = clipNormal.xy * resolution;
  float size = length(screenNormal);
  vec2 direction = size > 1e-6 ? screenNormal / size : vec2(0.0);
  vec2 offset = direction * widthPixels * 2.0 / resolution;
  return vec4(clipPosition.xy + offset * clipPosition.w, clipPosition.zw);
}
`;

/** Vertex stage of the hull: world normal through the inverse-transpose, then the pixel offset; InstancedMesh aware. */
export const OUTLINE_VERTEX = `
uniform float uWidth;
uniform vec2 uResolution;
${OUTLINE_GLSL}
void main() {
  mat4 placement = modelMatrix;
#ifdef USE_INSTANCING
  placement = modelMatrix * instanceMatrix;
#endif
  vec4 world = placement * vec4(position, 1.0);
  vec3 worldNormal = normalize(transpose(inverse(mat3(placement))) * normal);
  vec4 clipPosition = projectionMatrix * viewMatrix * world;
  vec4 clipNormal = projectionMatrix * viewMatrix * vec4(worldNormal, 0.0);
  gl_Position = outlineClipOffset(clipPosition, clipNormal, uWidth, uResolution);
}
`;

/** Fragment stage: flat outline colour in the output colour space. */
export const OUTLINE_FRAGMENT = `
uniform vec3 uColor;
uniform float uOpacity;

void main() {
  gl_FragColor = vec4(uColor, uOpacity);
  #include <colorspace_fragment>
}
`;

function settingsOf(options) {
  if (options === null || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(OUTLINE_SHELL_DEFAULTS, key)) throw new TypeError(`unknown outline option ${key}`);
  }
  const settings = {...OUTLINE_SHELL_DEFAULTS, ...options};
  const {color, resolution} = settings;
  if (!(Array.isArray(color) && color.length === 3 && color.every(Number.isFinite))) {
    throw new TypeError('color must be a linear RGB triple');
  }
  if (!(Array.isArray(resolution) && resolution.length === 2 && resolution.every((value) => value >= 1))) {
    throw new TypeError('resolution must be [width, height] in pixels');
  }
  if (!(settings.width >= 0 && settings.width <= 256)) throw new RangeError('width must be in [0, 256] pixels');
  if (!(settings.opacity >= 0 && settings.opacity <= 1)) throw new RangeError('opacity must be in [0, 1]');
  return settings;
}

/**
 * CPU mirror of the GLSL chunk: clipPosition [x, y, z, w] pushed widthPixels along the screen-space direction of
 * clipNormal [x, y, z, w] for a drawing buffer of resolution [width, height] pixels.
 */
export function outlineClipOffset(clipPosition, clipNormal, widthPixels, resolution) {
  for (const [value, name, size] of [[clipPosition, 'clipPosition', 4], [clipNormal, 'clipNormal', 4], [resolution, 'resolution', 2]]) {
    if (!(Array.isArray(value) && value.length === size && value.every(Number.isFinite))) {
      throw new TypeError(`${name} must be ${size} finite numbers`);
    }
  }
  if (!(widthPixels >= 0)) throw new RangeError('widthPixels must be non-negative');
  const sx = clipNormal[0] * resolution[0];
  const sy = clipNormal[1] * resolution[1];
  const size = Math.hypot(sx, sy);
  const dx = size > 1e-6 ? sx / size : 0;
  const dy = size > 1e-6 ? sy / size : 0;
  return [
    clipPosition[0] + ((dx * widthPixels * 2) / resolution[0]) * clipPosition[3],
    clipPosition[1] + ((dy * widthPixels * 2) / resolution[1]) * clipPosition[3],
    clipPosition[2],
    clipPosition[3],
  ];
}

/** The hull material: back faces only, uniforms uColor, uWidth, uOpacity and uResolution. */
export function createOutlineMaterial(THREE, options = {}) {
  const settings = settingsOf(options);
  const [r, g, b] = settings.color;
  return new THREE.ShaderMaterial({
    name: 'BaltorOutlineShellMaterial',
    uniforms: {
      uColor: {value: new THREE.Color(r, g, b)},
      uWidth: {value: settings.width},
      uOpacity: {value: settings.opacity},
      uResolution: {value: new THREE.Vector2(settings.resolution[0], settings.resolution[1])},
    },
    vertexShader: OUTLINE_VERTEX,
    fragmentShader: OUTLINE_FRAGMENT,
    side: THREE.BackSide,
    transparent: settings.opacity < 1,
  });
}

/**
 * An outline for `mesh`: a Mesh (or an InstancedMesh sharing the instance matrices) with the same geometry and the
 * hull material, added as a child of `mesh` so it follows it, and ignored by raycasting. Remove it with
 * mesh.remove(shell). Skinned and morphed meshes are not followed.
 */
export function createOutlineShell(THREE, mesh, options = {}) {
  if (!mesh || !mesh.isMesh || !mesh.geometry) throw new TypeError('mesh must be a three.js Mesh with a geometry');
  const material = createOutlineMaterial(THREE, options);
  let shell;
  if (mesh.isInstancedMesh) {
    shell = new THREE.InstancedMesh(mesh.geometry, material, mesh.count);
    shell.instanceMatrix = mesh.instanceMatrix;
  } else {
    shell = new THREE.Mesh(mesh.geometry, material);
  }
  shell.name = `${mesh.name || 'mesh'}Outline`;
  shell.raycast = () => {};
  mesh.add(shell);
  return shell;
}

/** Update the hull's resolution uniform, for example from renderer.getDrawingBufferSize on resize. */
export function setOutlineResolution(material, width, height) {
  if (!(width >= 1 && height >= 1)) throw new RangeError('width and height must be at least 1 pixel');
  if (!material || !material.uniforms || !material.uniforms.uResolution) throw new TypeError('material is not an outline');
  material.uniforms.uResolution.value.set(width, height);
  return material;
}
