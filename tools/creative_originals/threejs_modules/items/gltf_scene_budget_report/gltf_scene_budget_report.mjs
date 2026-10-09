// glTF scene budget report: walk the scene graph of a glTF 2.0 document and count what a renderer will draw
// (triangles, lines and points by primitive mode, vertices, draw calls as primitives times node instances), the
// materials, textures and images in use with an estimate of texture memory, the node count and depth, and the world
// bounds from accessor min and max through the node transforms; then check the counts against a budget. Original
// Baltor implementation from the glTF 2.0 specification; plain objects only, no three.js needed.

/** The metrics checkBudget accepts as budget keys. */
export const BUDGET_METRICS = Object.freeze(['triangles', 'lines', 'points', 'vertices', 'drawCalls', 'materials',
  'textures', 'textureBytes', 'nodes', 'maxDepth', 'extent']);
/** Default options of sceneBudgetReport. */
export const REPORT_DEFAULTS = Object.freeze({scene: null, imageSizes: null, mipmaps: true});

const TEXTURE_SLOTS = [['pbrMetallicRoughness', 'baseColorTexture'], ['pbrMetallicRoughness', 'metallicRoughnessTexture'],
  [null, 'normalTexture'], [null, 'occlusionTexture'], [null, 'emissiveTexture']];
const BYTES_PER_TEXEL = 4;
const MIPMAP_FACTOR = 4 / 3;

/** What one primitive draws for a mode (0 to 6) and an element count: {triangles, lines, points}. */
export function primitiveCounts(mode, count) {
  if (!(Number.isInteger(mode) && mode >= 0 && mode <= 6)) throw new RangeError(`mode must be 0 to 6, got ${mode}`);
  if (!(Number.isInteger(count) && count >= 0)) throw new RangeError(`count must be a non-negative integer, got ${count}`);
  const result = {triangles: 0, lines: 0, points: 0};
  if (mode === 0) result.points = count;
  else if (mode === 1) result.lines = Math.floor(count / 2);
  else if (mode === 2) result.lines = count >= 2 ? count : 0;
  else if (mode === 3) result.lines = Math.max(count - 1, 0);
  else if (mode === 4) result.triangles = Math.floor(count / 3);
  else result.triangles = Math.max(count - 2, 0);
  return result;
}

// list[index] when index is a whole number inside the list, otherwise undefined (never an inherited property).
function entry(list, index) {
  return Array.isArray(list) && Number.isInteger(index) && index >= 0 && index < list.length ? list[index] : undefined;
}

function multiply(a, b) {
  const out = new Array(16).fill(0);
  for (let column = 0; column < 4; column += 1) {
    for (let row = 0; row < 4; row += 1) {
      let sum = 0;
      for (let k = 0; k < 4; k += 1) sum += a[k * 4 + row] * b[column * 4 + k];
      out[column * 4 + row] = sum;
    }
  }
  return out;
}

// The local matrix of a node (column-major): its matrix, or translation * rotation * scale.
function localMatrix(node) {
  if (Array.isArray(node.matrix)) return node.matrix.slice();
  const [tx, ty, tz] = node.translation ?? [0, 0, 0];
  const [x, y, z, w] = node.rotation ?? [0, 0, 0, 1];
  const [sx, sy, sz] = node.scale ?? [1, 1, 1];
  return [
    (1 - 2 * (y * y + z * z)) * sx, (2 * (x * y + z * w)) * sx, (2 * (x * z - y * w)) * sx, 0,
    (2 * (x * y - z * w)) * sy, (1 - 2 * (x * x + z * z)) * sy, (2 * (y * z + x * w)) * sy, 0,
    (2 * (x * z + y * w)) * sz, (2 * (y * z - x * w)) * sz, (1 - 2 * (x * x + y * y)) * sz, 0,
    tx, ty, tz, 1,
  ];
}

function settingsOf(options) {
  if (!options || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(REPORT_DEFAULTS, key)) throw new TypeError(`unknown report option ${key}`);
  }
  return {...REPORT_DEFAULTS, ...options};
}

/**
 * Count what the document's scene draws. Options: scene (an index; default the document's scene or 0), imageSizes
 * (an array of {width, height} by image index, for the texture memory estimate) and mipmaps (add a third for mip
 * chains). Returns {scene, nodes, maxDepth, meshInstances, drawCalls, triangles, lines, points, vertices, materials,
 * defaultMaterial, textures, images, textureBytes, unknownImageSizes, bounds, extent, modes}.
 */
export function sceneBudgetReport(gltf, options = {}) {
  if (!gltf || typeof gltf !== 'object' || Array.isArray(gltf)) throw new TypeError('gltf must be a glTF object');
  const settings = settingsOf(options);
  const scenes = gltf.scenes ?? [];
  const sceneIndex = settings.scene ?? gltf.scene ?? 0;
  const nodes = gltf.nodes ?? [];
  const meshes = gltf.meshes ?? [];
  const accessors = gltf.accessors ?? [];
  const report = {scene: sceneIndex, nodes: 0, maxDepth: 0, meshInstances: 0, drawCalls: 0, triangles: 0, lines: 0,
    points: 0, vertices: 0, materials: 0, defaultMaterial: false, textures: 0, images: 0, textureBytes: 0,
    unknownImageSizes: [], bounds: null, extent: 0, modes: [0, 0, 0, 0, 0, 0, 0]};
  if (scenes.length === 0) return report;
  if (!(Number.isInteger(sceneIndex) && sceneIndex >= 0 && sceneIndex < scenes.length)) {
    throw new RangeError(`scene ${sceneIndex} does not exist`);
  }
  const usedMaterials = new Set();
  const low = [Infinity, Infinity, Infinity];
  const high = [-Infinity, -Infinity, -Infinity];
  const visited = new Set();
  const stack = (scenes[sceneIndex].nodes ?? []).map((index) => [index, 1, null]);
  const identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  while (stack.length) {
    const [index, depth, parentMatrix] = stack.pop();
    const node = entry(nodes, index);
    if (!node) throw new RangeError(`node ${index} does not exist`);
    if (visited.has(index)) throw new RangeError(`node ${index} is reached twice; the node graph is not a forest`);
    visited.add(index);
    report.maxDepth = Math.max(report.maxDepth, depth);
    const world = multiply(parentMatrix ?? identity, localMatrix(node));
    if (node.mesh !== undefined) {
      const mesh = entry(meshes, node.mesh);
      if (!mesh) throw new RangeError(`mesh ${node.mesh} does not exist`);
      report.meshInstances += 1;
      for (const primitive of mesh.primitives ?? []) {
        const mode = primitive.mode ?? 4;
        const position = entry(accessors, primitive.attributes?.POSITION);
        const vertexCount = position && Number.isInteger(position.count) ? position.count : 0;
        const elements = primitive.indices !== undefined ? entry(accessors, primitive.indices)?.count ?? 0 : vertexCount;
        const counted = primitiveCounts(mode, elements);
        report.triangles += counted.triangles;
        report.lines += counted.lines;
        report.points += counted.points;
        report.vertices += vertexCount;
        report.drawCalls += 1;
        report.modes[mode] += 1;
        if (primitive.material === undefined) report.defaultMaterial = true;
        else usedMaterials.add(primitive.material);
        if (position && Array.isArray(position.min) && Array.isArray(position.max)) {
          for (let corner = 0; corner < 8; corner += 1) {
            const point = [0, 1, 2].map((axis) => ((corner >> axis) & 1 ? position.max[axis] : position.min[axis]));
            for (let axis = 0; axis < 3; axis += 1) {
              const value = world[axis] * point[0] + world[4 + axis] * point[1] + world[8 + axis] * point[2] + world[12 + axis];
              low[axis] = Math.min(low[axis], value);
              high[axis] = Math.max(high[axis], value);
            }
          }
        }
      }
    }
    for (const child of node.children ?? []) stack.push([child, depth + 1, world]);
  }
  report.nodes = visited.size;
  report.materials = usedMaterials.size;
  const usedTextures = new Set();
  for (const index of usedMaterials) {
    const material = entry(gltf.materials, index) ?? {};
    for (const [group, slot] of TEXTURE_SLOTS) {
      const info = group ? material[group]?.[slot] : material[slot];
      if (info && Number.isInteger(info.index)) usedTextures.add(info.index);
    }
  }
  report.textures = usedTextures.size;
  const usedImages = new Set();
  for (const index of usedTextures) {
    const texture = entry(gltf.textures, index);
    if (texture && Number.isInteger(texture.source)) usedImages.add(texture.source);
  }
  report.images = usedImages.size;
  for (const image of [...usedImages].sort((a, b) => a - b)) {
    const size = settings.imageSizes ? settings.imageSizes[image] : null;
    if (size && Number.isInteger(size.width) && Number.isInteger(size.height) && size.width > 0 && size.height > 0) {
      report.textureBytes += size.width * size.height * BYTES_PER_TEXEL * (settings.mipmaps ? MIPMAP_FACTOR : 1);
    } else {
      report.unknownImageSizes.push(image);
    }
  }
  report.textureBytes = report.unknownImageSizes.length ? null : Math.round(report.textureBytes);
  if (Number.isFinite(low[0])) {
    report.bounds = {min: low, max: high};
    report.extent = Math.max(high[0] - low[0], high[1] - low[1], high[2] - low[2]);
  }
  return report;
}

/**
 * Compare a report with a budget {metric: limit} over BUDGET_METRICS. Returns the violations as
 * {metric, value, limit, reason}, reason 'over' or 'unknown' (a value the report could not count, such as texture
 * memory without image sizes). An empty list means the scene fits.
 */
export function checkBudget(report, budget) {
  if (!report || typeof report !== 'object') throw new TypeError('report must be a sceneBudgetReport result');
  if (!budget || typeof budget !== 'object') throw new TypeError('budget must be an object');
  const violations = [];
  for (const [metric, limit] of Object.entries(budget)) {
    if (!BUDGET_METRICS.includes(metric)) throw new TypeError(`unknown budget metric ${metric}`);
    if (!(typeof limit === 'number' && limit >= 0)) throw new RangeError(`the ${metric} limit must be a number >= 0`);
    const value = report[metric];
    if (value === null || value === undefined) violations.push({metric, value: null, limit, reason: 'unknown'});
    else if (value > limit) violations.push({metric, value, limit, reason: 'over'});
  }
  return violations;
}
