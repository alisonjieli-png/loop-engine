// Vertex welding and crease-angle normals for three.js geometry: merge vertices closer than a tolerance through a
// spatial hash, then give every triangle corner the angle-weighted normal of the faces around its vertex that bend by
// no more than the crease angle, splitting vertices only where a crease (or a UV seam) needs it. Original Baltor
// implementation; weldVertices and creaseNormals work on typed arrays alone.

/** Default tolerance (distance in scene units) and crease angle (degrees). */
export const CREASE_NORMALS_DEFAULTS = Object.freeze({tolerance: 1e-6, creaseAngle: 30});

const NEIGHBOURS = [-1, 0, 1];

function positionsOf(positions) {
  if (!(ArrayBuffer.isView(positions) || Array.isArray(positions)) || positions.length % 3 !== 0 || positions.length === 0) {
    throw new TypeError('positions is a non-empty array of x, y, z triples');
  }
  for (let k = 0; k < positions.length; k += 1) {
    if (!Number.isFinite(positions[k])) throw new RangeError(`position component ${k} is not finite`);
  }
  return positions.length / 3;
}

function trianglesOf(indices, vertexCount) {
  if (indices === null || indices === undefined) {
    if (vertexCount % 3 !== 0) throw new RangeError('a triangle soup needs a multiple of three vertices');
    return Uint32Array.from({length: vertexCount}, (_, k) => k);
  }
  if (!(ArrayBuffer.isView(indices) || Array.isArray(indices)) || indices.length % 3 !== 0) {
    throw new TypeError('indices is an array whose length is a multiple of three');
  }
  for (let k = 0; k < indices.length; k += 1) {
    if (!Number.isInteger(indices[k]) || indices[k] < 0 || indices[k] >= vertexCount) throw new RangeError(`index ${k} is out of range`);
  }
  return indices;
}

/**
 * Merge vertices within `tolerance` of each other (Euclidean distance, through a hash of cells of that size; 0 merges
 * exact copies only). indices null treats positions as a triangle soup. Returns {positions, indices, remap}: the
 * unique positions in first-seen order, the triangles over them and, for every input vertex, its unique vertex.
 */
export function weldVertices(positions, tolerance = CREASE_NORMALS_DEFAULTS.tolerance, indices = null) {
  const count = positionsOf(positions);
  if (!(tolerance >= 0 && Number.isFinite(tolerance))) throw new RangeError('tolerance must be a finite number >= 0');
  const triangles = trianglesOf(indices, count);
  const remap = new Uint32Array(count);
  const unique = [];
  const cells = new Map();
  const cellOf = (value) => (tolerance > 0 ? Math.floor(value / tolerance) : value);
  for (let v = 0; v < count; v += 1) {
    const x = positions[v * 3];
    const y = positions[v * 3 + 1];
    const z = positions[v * 3 + 2];
    const cx = cellOf(x);
    const cy = cellOf(y);
    const cz = cellOf(z);
    let found = -1;
    const offsets = tolerance > 0 ? NEIGHBOURS : [0];
    search: for (const dx of offsets) {
      for (const dy of offsets) {
        for (const dz of offsets) {
          const bucket = cells.get(`${cx + dx},${cy + dy},${cz + dz}`);
          if (!bucket) continue;
          for (const candidate of bucket) {
            const ux = unique[candidate * 3] - x;
            const uy = unique[candidate * 3 + 1] - y;
            const uz = unique[candidate * 3 + 2] - z;
            if (ux * ux + uy * uy + uz * uz <= tolerance * tolerance) {
              found = candidate;
              break search;
            }
          }
        }
      }
    }
    if (found < 0) {
      found = unique.length / 3;
      unique.push(x, y, z);
      const key = `${cx},${cy},${cz}`;
      if (!cells.has(key)) cells.set(key, []);
      cells.get(key).push(found);
    }
    remap[v] = found;
  }
  const welded = unique.length / 3;
  const out = welded > 65535 ? new Uint32Array(triangles.length) : new Uint16Array(triangles.length);
  for (let k = 0; k < triangles.length; k += 1) out[k] = remap[triangles[k]];
  return {positions: Float32Array.from(unique), indices: out, remap};
}

/**
 * Crease-angle normals: every triangle corner gets the angle-weighted average of the unit normals of the triangles
 * around its welded vertex whose normal is within creaseAngleDegrees of its own triangle's normal. Corners with the
 * same vertex, normal (and uv, when options.uvs is given) share one output vertex. indices null treats positions as a
 * triangle soup. options: {tolerance, uvs}. Returns {positions, normals, uvs, indices} (uvs null without input uvs).
 */
export function creaseNormals(positions, indices, creaseAngleDegrees = CREASE_NORMALS_DEFAULTS.creaseAngle, options = {}) {
  for (const key of Object.keys(options)) {
    if (!['tolerance', 'uvs'].includes(key)) throw new TypeError(`unknown crease option ${key}`);
  }
  const count = positionsOf(positions);
  if (!(creaseAngleDegrees >= 0 && creaseAngleDegrees <= 180)) throw new RangeError('creaseAngleDegrees must be in [0, 180]');
  const uvs = options.uvs ?? null;
  if (uvs !== null && (!(ArrayBuffer.isView(uvs) || Array.isArray(uvs)) || uvs.length !== count * 2)) {
    throw new RangeError('uvs must hold two numbers per vertex');
  }
  const triangles = trianglesOf(indices, count);
  const {remap} = weldVertices(positions, options.tolerance ?? CREASE_NORMALS_DEFAULTS.tolerance, triangles);
  const triangleCount = triangles.length / 3;
  const faces = new Float64Array(triangleCount * 3);
  const angles = new Float64Array(triangleCount * 3);
  const flat = new Uint8Array(triangleCount);
  const point = (v) => [positions[v * 3], positions[v * 3 + 1], positions[v * 3 + 2]];
  for (let t = 0; t < triangleCount; t += 1) {
    const corners = [point(triangles[t * 3]), point(triangles[t * 3 + 1]), point(triangles[t * 3 + 2])];
    const u = corners[1].map((value, i) => value - corners[0][i]);
    const w = corners[2].map((value, i) => value - corners[0][i]);
    const normal = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]];
    const length = Math.hypot(...normal);
    if (!(length > 0)) {
      flat[t] = 1;
      continue;
    }
    faces.set(normal.map((value) => value / length), t * 3);
    for (let k = 0; k < 3; k += 1) {
      const a = corners[(k + 1) % 3].map((value, i) => value - corners[k][i]);
      const b = corners[(k + 2) % 3].map((value, i) => value - corners[k][i]);
      const cosine = (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (Math.hypot(...a) * Math.hypot(...b));
      angles[t * 3 + k] = Math.acos(Math.min(1, Math.max(-1, cosine)));
    }
  }
  // Corners grouped by welded vertex (compressed rows).
  let weldedCount = 0;
  for (let v = 0; v < remap.length; v += 1) weldedCount = Math.max(weldedCount, remap[v] + 1);
  const start = new Uint32Array(weldedCount + 1);
  for (let c = 0; c < triangles.length; c += 1) start[remap[triangles[c]] + 1] += 1;
  for (let v = 0; v < weldedCount; v += 1) start[v + 1] += start[v];
  const fill = start.slice(0, weldedCount);
  const around = new Uint32Array(triangles.length);
  for (let c = 0; c < triangles.length; c += 1) around[fill[remap[triangles[c]]]++] = c;
  const limit = Math.cos((creaseAngleDegrees * Math.PI) / 180) - 1e-12;
  const outPositions = [];
  const outNormals = [];
  const outUvs = [];
  const outIndices = new Uint32Array(triangles.length);
  const seen = new Map();
  for (let c = 0; c < triangles.length; c += 1) {
    const t = Math.floor(c / 3);
    const welded = remap[triangles[c]];
    const sum = [0, 0, 0];
    for (let k = start[welded]; k < start[welded + 1]; k += 1) {
      const other = Math.floor(around[k] / 3);
      if (flat[other]) continue;
      const cosine = flat[t] ? 1 : faces[t * 3] * faces[other * 3] + faces[t * 3 + 1] * faces[other * 3 + 1]
        + faces[t * 3 + 2] * faces[other * 3 + 2];
      if (cosine < limit) continue;
      const weight = angles[around[k]];
      sum[0] += weight * faces[other * 3];
      sum[1] += weight * faces[other * 3 + 1];
      sum[2] += weight * faces[other * 3 + 2];
    }
    const length = Math.hypot(...sum);
    const normal = length > 0 ? sum.map((value) => value / length) : [0, 1, 0];
    const source = triangles[c];
    const uv = uvs === null ? null : [uvs[source * 2], uvs[source * 2 + 1]];
    const key = `${welded}|${normal.map((value) => value.toFixed(6)).join(',')}|${uv === null ? '' : uv.join(',')}`;
    let index = seen.get(key);
    if (index === undefined) {
      index = outPositions.length / 3;
      seen.set(key, index);
      outPositions.push(...point(source));
      outNormals.push(...normal);
      if (uv !== null) outUvs.push(...uv);
    }
    outIndices[c] = index;
  }
  const vertexCount = outPositions.length / 3;
  return {positions: Float32Array.from(outPositions), normals: Float32Array.from(outNormals),
    uvs: uvs === null ? null : Float32Array.from(outUvs),
    indices: vertexCount > 65535 ? outIndices : Uint16Array.from(outIndices)};
}

function attributeArray(attribute) {
  if (typeof attribute.getX === 'function' && attribute.isInterleavedBufferAttribute) {
    const values = new Float32Array(attribute.count * attribute.itemSize);
    const getters = ['getX', 'getY', 'getZ', 'getW'].slice(0, attribute.itemSize);
    for (let v = 0; v < attribute.count; v += 1) getters.forEach((name, k) => { values[v * attribute.itemSize + k] = attribute[name](v); });
    return values;
  }
  return attribute.array;
}

/**
 * A new indexed THREE.BufferGeometry with crease-angle normals from any triangle geometry (indexed or not); its uv
 * attribute, when present, is kept and its seams stay split.
 */
export function createCreasedGeometry(THREE, geometry, creaseAngleDegrees = CREASE_NORMALS_DEFAULTS.creaseAngle) {
  const position = geometry.getAttribute('position');
  if (!position) throw new TypeError('the geometry has no position attribute');
  const uv = geometry.getAttribute('uv');
  const index = geometry.getIndex();
  const data = creaseNormals(attributeArray(position), index ? attributeArray(index) : null, creaseAngleDegrees,
    uv ? {uvs: attributeArray(uv)} : {});
  const result = new THREE.BufferGeometry();
  result.setAttribute('position', new THREE.BufferAttribute(data.positions, 3));
  result.setAttribute('normal', new THREE.BufferAttribute(data.normals, 3));
  if (data.uvs) result.setAttribute('uv', new THREE.BufferAttribute(data.uvs, 2));
  result.setIndex(new THREE.BufferAttribute(data.indices, 1));
  result.computeBoundingBox();
  result.computeBoundingSphere();
  return result;
}
