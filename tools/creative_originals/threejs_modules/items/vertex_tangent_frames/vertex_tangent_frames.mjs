// Per-vertex tangent frames for normal mapping in three.js: from positions, normals, uvs and indices, find the
// direction of increasing u on every triangle, average it around each vertex by corner angle, make it perpendicular to
// the normal (Gram-Schmidt) and store the bitangent's side as w = +1 or -1 (mirrored UVs), the vec4 tangent attribute
// three.js reads. Degenerate UVs fall back to a stable perpendicular. Original Baltor implementation on typed arrays;
// only addTangents needs three.js.

/** Default options of computeVertexTangents. */
export const TANGENT_FRAME_DEFAULTS = Object.freeze({orthogonalize: true});

const TINY = 1e-20;

function lengthOf(array, count, size, name) {
  if (!(ArrayBuffer.isView(array) || Array.isArray(array)) || array.length !== count * size) {
    throw new RangeError(`${name} must hold ${size} numbers per vertex`);
  }
}

/**
 * Tangents as a Float32Array of x, y, z, w per vertex: xyz is the unit direction of increasing u, perpendicular to the
 * normal when orthogonalize is true, and w is +1 when cross(normal, tangent) points toward increasing v, -1 when the
 * UVs are mirrored. indices null reads the vertices as a triangle soup.
 */
export function computeVertexTangents(positions, normals, uvs, indices = null, options = {}) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(TANGENT_FRAME_DEFAULTS, key)) throw new TypeError(`unknown tangent option ${key}`);
  }
  const settings = {...TANGENT_FRAME_DEFAULTS, ...options};
  if (typeof settings.orthogonalize !== 'boolean') throw new TypeError('orthogonalize must be true or false');
  if (!(ArrayBuffer.isView(positions) || Array.isArray(positions)) || positions.length % 3 !== 0) {
    throw new TypeError('positions is an array of x, y, z triples');
  }
  const count = positions.length / 3;
  lengthOf(normals, count, 3, 'normals');
  lengthOf(uvs, count, 2, 'uvs');
  const triangles = indices === null ? Uint32Array.from({length: count}, (_, k) => k) : indices;
  if (triangles.length % 3 !== 0) throw new RangeError('indices must describe whole triangles');
  for (let k = 0; k < triangles.length; k += 1) {
    if (!Number.isInteger(triangles[k]) || triangles[k] < 0 || triangles[k] >= count) throw new RangeError(`index ${k} is out of range`);
  }
  const tangentSum = new Float64Array(count * 3);
  const bitangentSum = new Float64Array(count * 3);
  const p = (v) => [positions[v * 3], positions[v * 3 + 1], positions[v * 3 + 2]];
  for (let t = 0; t < triangles.length; t += 3) {
    const corners = [triangles[t], triangles[t + 1], triangles[t + 2]];
    const [a, b, c] = corners.map(p);
    const e1 = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
    const e2 = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
    const du1 = uvs[corners[1] * 2] - uvs[corners[0] * 2];
    const dv1 = uvs[corners[1] * 2 + 1] - uvs[corners[0] * 2 + 1];
    const du2 = uvs[corners[2] * 2] - uvs[corners[0] * 2];
    const dv2 = uvs[corners[2] * 2 + 1] - uvs[corners[0] * 2 + 1];
    const determinant = du1 * dv2 - du2 * dv1;
    if (Math.abs(determinant) < TINY) continue;
    const tangent = [0, 1, 2].map((k) => (e1[k] * dv2 - e2[k] * dv1) / determinant);
    const bitangent = [0, 1, 2].map((k) => (e2[k] * du1 - e1[k] * du2) / determinant);
    const tangentLength = Math.hypot(...tangent);
    const bitangentLength = Math.hypot(...bitangent);
    if (!(tangentLength > 0 && bitangentLength > 0)) continue;
    // Each corner adds the triangle's unit directions weighted by the angle it makes at that corner.
    const points = [a, b, c];
    for (let k = 0; k < 3; k += 1) {
      const from = points[k];
      const u = points[(k + 1) % 3].map((value, i) => value - from[i]);
      const w = points[(k + 2) % 3].map((value, i) => value - from[i]);
      const cosine = (u[0] * w[0] + u[1] * w[1] + u[2] * w[2]) / (Math.hypot(...u) * Math.hypot(...w) || 1);
      const weight = Math.acos(Math.min(1, Math.max(-1, cosine)));
      for (let i = 0; i < 3; i += 1) {
        tangentSum[corners[k] * 3 + i] += (weight * tangent[i]) / tangentLength;
        bitangentSum[corners[k] * 3 + i] += (weight * bitangent[i]) / bitangentLength;
      }
    }
  }
  const result = new Float32Array(count * 4);
  for (let v = 0; v < count; v += 1) {
    const n = [normals[v * 3], normals[v * 3 + 1], normals[v * 3 + 2]];
    let t = [tangentSum[v * 3], tangentSum[v * 3 + 1], tangentSum[v * 3 + 2]];
    if (settings.orthogonalize) {
      const along = n[0] * t[0] + n[1] * t[1] + n[2] * t[2];
      t = [t[0] - n[0] * along, t[1] - n[1] * along, t[2] - n[2] * along];
    }
    let length = Math.hypot(...t);
    if (!(length > 1e-12)) {
      // No usable UV direction: any unit vector perpendicular to the normal, chosen from the least aligned axis.
      const absolute = n.map(Math.abs);
      const axis = [0, 0, 0];
      axis[absolute.indexOf(Math.min(...absolute))] = 1;
      const along = n[0] * axis[0] + n[1] * axis[1] + n[2] * axis[2];
      t = [axis[0] - n[0] * along, axis[1] - n[1] * along, axis[2] - n[2] * along];
      length = Math.hypot(...t);
    }
    t = t.map((value) => value / length);
    const side = [n[1] * t[2] - n[2] * t[1], n[2] * t[0] - n[0] * t[2], n[0] * t[1] - n[1] * t[0]];
    const handedness = side[0] * bitangentSum[v * 3] + side[1] * bitangentSum[v * 3 + 1] + side[2] * bitangentSum[v * 3 + 2];
    result.set([t[0], t[1], t[2], handedness < 0 ? -1 : 1], v * 4);
  }
  return result;
}

/**
 * Compute tangents for a THREE.BufferGeometry with position, normal and uv attributes (indexed or not) and set them as
 * its 'tangent' attribute (itemSize 4), which three.js materials use for normal maps. Returns the geometry.
 */
export function addTangents(THREE, geometry, options = {}) {
  const read = (name) => {
    const attribute = geometry.getAttribute(name);
    if (!attribute) throw new TypeError(`the geometry has no ${name} attribute`);
    return attribute.array;
  };
  const index = geometry.getIndex();
  const tangents = computeVertexTangents(read('position'), read('normal'), read('uv'), index ? index.array : null, options);
  geometry.setAttribute('tangent', new THREE.BufferAttribute(tangents, 4));
  return geometry;
}
