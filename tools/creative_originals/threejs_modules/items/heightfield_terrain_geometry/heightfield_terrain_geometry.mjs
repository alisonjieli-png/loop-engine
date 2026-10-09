// Heightfield terrain geometry for three.js: a grid mesh from a row-major array of heights with central-difference
// normals (one-sided at the borders, so a plane stays exact), UVs, an LOD stride, optional skirts down to a base height
// and an optional bottom that makes the terrain a closed block, plus height queries that match the mesh. Original
// Baltor implementation; heightfieldTerrainData and the samplers work on typed arrays alone.

/** Default options. skirtBase null puts the base one cell size below the lowest scaled height. */
export const HEIGHTFIELD_DEFAULTS = Object.freeze({
  cellSize: 1,
  heightScale: 1,
  stride: 1,
  skirt: false,
  skirtBase: null,
  closeBottom: false,
  center: true,
});

const MAXIMUM_SAMPLES = 8193;

function fieldOf(heights, width, depth) {
  if (!Number.isInteger(width) || !Number.isInteger(depth) || width < 2 || depth < 2 || width > MAXIMUM_SAMPLES
    || depth > MAXIMUM_SAMPLES) {
    throw new RangeError(`width and depth must be integers from 2 to ${MAXIMUM_SAMPLES}`);
  }
  if (!(Array.isArray(heights) || ArrayBuffer.isView(heights))) throw new TypeError('heights must be an array or typed array');
  if (heights.length !== width * depth) throw new RangeError(`heights needs width * depth = ${width * depth} values`);
  for (let k = 0; k < heights.length; k += 1) {
    if (!Number.isFinite(heights[k])) throw new RangeError(`height ${k} is not a finite number`);
  }
}

function settingsOf(options, width, depth) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(HEIGHTFIELD_DEFAULTS, key)) throw new TypeError(`unknown heightfield option ${key}`);
  }
  const settings = {...HEIGHTFIELD_DEFAULTS, ...options};
  if (!(settings.cellSize > 0 && Number.isFinite(settings.cellSize))) throw new RangeError('cellSize must be positive');
  if (!Number.isFinite(settings.heightScale)) throw new RangeError('heightScale must be a finite number');
  if (!Number.isInteger(settings.stride) || settings.stride < 1 || (width - 1) % settings.stride !== 0
    || (depth - 1) % settings.stride !== 0) {
    throw new RangeError('stride must be a positive integer that divides width - 1 and depth - 1');
  }
  for (const key of ['skirt', 'closeBottom', 'center']) {
    if (typeof settings[key] !== 'boolean') throw new TypeError(`${key} must be true or false`);
  }
  if (settings.skirtBase !== null && !Number.isFinite(settings.skirtBase)) throw new RangeError('skirtBase must be null or finite');
  if (settings.closeBottom && !settings.skirt) throw new RangeError('closeBottom needs skirt');
  return settings;
}

/**
 * Bilinear height at sample coordinates x in [0, width - 1] and z in [0, depth - 1] (clamped), in the units of the
 * heights array (multiply by heightScale for world units).
 */
export function sampleHeight(heights, width, depth, x, z) {
  fieldOf(heights, width, depth);
  const cx = Math.min(Math.max(x, 0), width - 1);
  const cz = Math.min(Math.max(z, 0), depth - 1);
  const i = Math.min(Math.floor(cx), width - 2);
  const j = Math.min(Math.floor(cz), depth - 2);
  const fx = cx - i;
  const fz = cz - j;
  const at = (a, b) => heights[b * width + a];
  return (1 - fz) * ((1 - fx) * at(i, j) + fx * at(i + 1, j)) + fz * ((1 - fx) * at(i, j + 1) + fx * at(i + 1, j + 1));
}

/**
 * Height on the mesh surface itself (stride 1): each cell is split along the diagonal from (i + 1, j) to (i, j + 1),
 * so this differs from sampleHeight inside a cell that is not planar. Use it to set objects exactly on the terrain.
 */
export function sampleSurfaceHeight(heights, width, depth, x, z) {
  fieldOf(heights, width, depth);
  const cx = Math.min(Math.max(x, 0), width - 1);
  const cz = Math.min(Math.max(z, 0), depth - 1);
  const i = Math.min(Math.floor(cx), width - 2);
  const j = Math.min(Math.floor(cz), depth - 2);
  const fx = cx - i;
  const fz = cz - j;
  const a = heights[j * width + i];
  const b = heights[j * width + i + 1];
  const d = heights[(j + 1) * width + i];
  const c = heights[(j + 1) * width + i + 1];
  if (fx + fz <= 1) return a + fx * (b - a) + fz * (d - a);
  return c + (1 - fx) * (d - c) + (1 - fz) * (b - c);
}

/**
 * The terrain as typed arrays {positions, normals, uvs, indices, columns, rows}: a grid of columns x rows vertices
 * (every stride-th sample) with y = height * heightScale, x and z in steps of cellSize (centred on the origin when
 * center is true), normals from central differences of the full-resolution field, u along +x and v toward -z,
 * triangles counter-clockwise from above. Skirts add four outward walls down to the base; closeBottom adds a bottom
 * grid facing down, so the block is closed.
 */
export function heightfieldTerrainData(heights, width, depth, options = {}) {
  fieldOf(heights, width, depth);
  const settings = settingsOf(options, width, depth);
  const {cellSize, heightScale, stride} = settings;
  const columns = (width - 1) / stride + 1;
  const rows = (depth - 1) / stride + 1;
  const offsetX = settings.center ? ((width - 1) * cellSize) / 2 : 0;
  const offsetZ = settings.center ? ((depth - 1) * cellSize) / 2 : 0;
  const at = (i, j) => heights[j * width + i];
  let lowest = Infinity;
  for (let k = 0; k < heights.length; k += 1) lowest = Math.min(lowest, heights[k] * heightScale);
  const base = settings.skirtBase === null ? lowest - cellSize : settings.skirtBase;
  if (base > lowest) throw new RangeError(`skirtBase ${base} is above the lowest scaled height ${lowest}`);
  const perimeter = 2 * columns + 2 * rows;
  const vertexCount = columns * rows + (settings.skirt ? 2 * perimeter : 0) + (settings.closeBottom ? columns * rows : 0);
  const quadCount = (columns - 1) * (rows - 1);
  const wallCount = settings.skirt ? 2 * (columns - 1) + 2 * (rows - 1) : 0;
  const indexCount = 6 * quadCount * (settings.closeBottom ? 2 : 1) + 6 * wallCount;
  const positions = new Float32Array(vertexCount * 3);
  const normals = new Float32Array(vertexCount * 3);
  const uvs = new Float32Array(vertexCount * 2);
  const indices = vertexCount > 65535 ? new Uint32Array(indexCount) : new Uint16Array(indexCount);
  let vertex = 0;
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < columns; c += 1) {
      const i = c * stride;
      const j = r * stride;
      const left = at(Math.max(i - 1, 0), j);
      const right = at(Math.min(i + 1, width - 1), j);
      const near = at(i, Math.max(j - 1, 0));
      const far = at(i, Math.min(j + 1, depth - 1));
      const slopeX = ((right - left) * heightScale) / ((Math.min(i + 1, width - 1) - Math.max(i - 1, 0)) * cellSize);
      const slopeZ = ((far - near) * heightScale) / ((Math.min(j + 1, depth - 1) - Math.max(j - 1, 0)) * cellSize);
      const length = Math.hypot(slopeX, 1, slopeZ);
      positions.set([i * cellSize - offsetX, at(i, j) * heightScale, j * cellSize - offsetZ], vertex * 3);
      normals.set([(0 - slopeX) / length, 1 / length, (0 - slopeZ) / length], vertex * 3);
      uvs.set([c / (columns - 1), 1 - r / (rows - 1)], vertex * 2);
      vertex += 1;
    }
  }
  let index = 0;
  for (let r = 0; r < rows - 1; r += 1) {
    for (let c = 0; c < columns - 1; c += 1) {
      const a = r * columns + c;
      const b = a + 1;
      const d = a + columns;
      indices.set([a, d, b, b, d, d + 1], index);
      index += 6;
    }
  }
  if (settings.skirt) {
    // Each side: the border vertices in order, the outward direction.
    const sides = [
      {cells: Array.from({length: columns}, (_, c) => c), outward: [0, 0, -1]},
      {cells: Array.from({length: columns}, (_, c) => (rows - 1) * columns + c), outward: [0, 0, 1]},
      {cells: Array.from({length: rows}, (_, r) => r * columns), outward: [-1, 0, 0]},
      {cells: Array.from({length: rows}, (_, r) => r * columns + columns - 1), outward: [1, 0, 0]},
    ];
    for (const side of sides) {
      const first = vertex;
      side.cells.forEach((cell, k) => {
        const top = positions.subarray(cell * 3, cell * 3 + 3);
        positions.set(top, vertex * 3);
        positions.set([top[0], base, top[2]], (vertex + 1) * 3);
        normals.set(side.outward, vertex * 3);
        normals.set(side.outward, (vertex + 1) * 3);
        const u = k / (side.cells.length - 1);
        uvs.set([u, 1], vertex * 2);
        uvs.set([u, 0], (vertex + 1) * 2);
        vertex += 2;
      });
      for (let k = 0; k < side.cells.length - 1; k += 1) {
        const top0 = first + 2 * k;
        const bottom0 = top0 + 1;
        const top1 = top0 + 2;
        const bottom1 = top0 + 3;
        // Order the two triangles so their normal agrees with the side's outward direction.
        const edge = [positions[top1 * 3] - positions[top0 * 3], 0, positions[top1 * 3 + 2] - positions[top0 * 3 + 2]];
        const facing = edge[2] * side.outward[0] - edge[0] * side.outward[2];
        if (facing > 0) indices.set([top0, top1, bottom0, top1, bottom1, bottom0], index);
        else indices.set([top0, bottom0, top1, top1, bottom0, bottom1], index);
        index += 6;
      }
    }
    if (settings.closeBottom) {
      const first = vertex;
      for (let r = 0; r < rows; r += 1) {
        for (let c = 0; c < columns; c += 1) {
          const cell = r * columns + c;
          positions.set([positions[cell * 3], base, positions[cell * 3 + 2]], vertex * 3);
          normals.set([0, -1, 0], vertex * 3);
          uvs.set([c / (columns - 1), r / (rows - 1)], vertex * 2);
          vertex += 1;
        }
      }
      for (let r = 0; r < rows - 1; r += 1) {
        for (let c = 0; c < columns - 1; c += 1) {
          const a = first + r * columns + c;
          const b = a + 1;
          const d = a + columns;
          indices.set([a, b, d, b, d + 1, d], index);
          index += 6;
        }
      }
    }
  }
  return {positions, normals, uvs, indices, columns, rows};
}

/** A THREE.BufferGeometry of the terrain with position, normal and uv attributes and an index. */
export function createHeightfieldTerrainGeometry(THREE, heights, width, depth, options = {}) {
  const data = heightfieldTerrainData(heights, width, depth, options);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(data.positions, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(data.normals, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(data.uvs, 2));
  geometry.setIndex(new THREE.BufferAttribute(data.indices, 1));
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}
