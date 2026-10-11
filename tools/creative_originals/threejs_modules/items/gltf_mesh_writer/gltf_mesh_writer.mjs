// glTF 2.0 mesh writer: turn typed-array meshes and a node hierarchy into a glTF 2.0 document with one embedded
// base64 buffer, or into a GLB. Buffer views are 4-byte aligned, POSITION accessors carry min and max, every mesh
// gets a metallic-roughness material, and inputs are checked before anything is written. Original Baltor
// implementation written from the glTF 2.0 specification; no three.js needed (meshFromBufferGeometry reads a
// BufferGeometry-shaped object by its attributes).

/** Default options of writeGltf and writeGlb. */
export const GLTF_WRITER_DEFAULTS = Object.freeze({
  generator: 'Baltor gltf_mesh_writer 1.0',
  sceneName: 'Scene',
});

const BASE64_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const FLOAT = 5126;
const INDEX_TYPES = new Map([[Uint8Array, 5121], [Uint16Array, 5123], [Uint32Array, 5125]]);
const ARRAY_BUFFER = 34962;
const ELEMENT_ARRAY_BUFFER = 34963;
const UNIT_TOLERANCE = 1e-6;
const MESH_KEYS = new Set(['name', 'positions', 'normals', 'uvs', 'colors', 'indices', 'material']);
const NODE_KEYS = new Set(['name', 'mesh', 'translation', 'rotation', 'scale', 'children']);
const MATERIAL_KEYS = new Set(['name', 'color', 'metallic', 'roughness', 'emissive', 'doubleSided']);
const MATERIAL_DEFAULTS = Object.freeze({color: [0.8, 0.8, 0.8, 1], metallic: 0, roughness: 0.6, emissive: [0, 0, 0],
  doubleSided: false});

/** Base64 (RFC 4648, with padding) of a byte array, written by hand so it runs anywhere. */
export function encodeBase64(bytes) {
  if (!(bytes instanceof Uint8Array)) throw new TypeError('bytes must be a Uint8Array');
  const parts = [];
  for (let index = 0; index < bytes.length; index += 3) {
    const remaining = bytes.length - index;
    const group = (bytes[index] << 16) | ((remaining > 1 ? bytes[index + 1] : 0) << 8) | (remaining > 2 ? bytes[index + 2] : 0);
    parts.push(BASE64_ALPHABET[(group >> 18) & 63], BASE64_ALPHABET[(group >> 12) & 63],
      remaining > 1 ? BASE64_ALPHABET[(group >> 6) & 63] : '=', remaining > 2 ? BASE64_ALPHABET[group & 63] : '=');
  }
  return parts.join('');
}

function checkKeys(object, allowed, what) {
  if (!object || typeof object !== 'object' || Array.isArray(object)) throw new TypeError(`${what} must be an object`);
  for (const key of Object.keys(object)) if (!allowed.has(key)) throw new TypeError(`unknown ${what} key ${key}`);
}

function finiteVector(value, length, name) {
  if (!(Array.isArray(value) && value.length === length && value.every(Number.isFinite))) {
    throw new RangeError(`${name} must hold ${length} finite numbers`);
  }
  return value;
}

function checkFloats(array, width, count, name) {
  if (!(array instanceof Float32Array)) throw new TypeError(`${name} must be a Float32Array`);
  if (array.length !== width * count) throw new RangeError(`${name} must hold ${width} values per vertex`);
  for (const value of array) if (!Number.isFinite(value)) throw new RangeError(`${name} holds a value that is not finite`);
}

function checkMesh(mesh, index) {
  checkKeys(mesh, MESH_KEYS, `meshes[${index}]`);
  const {positions} = mesh;
  if (!(positions instanceof Float32Array) || positions.length === 0 || positions.length % 3 !== 0) {
    throw new RangeError(`meshes[${index}].positions must be a Float32Array of xyz triples`);
  }
  const count = positions.length / 3;
  checkFloats(positions, 3, count, `meshes[${index}].positions`);
  if (mesh.normals !== undefined) checkFloats(mesh.normals, 3, count, `meshes[${index}].normals`);
  if (mesh.uvs !== undefined) checkFloats(mesh.uvs, 2, count, `meshes[${index}].uvs`);
  if (mesh.colors !== undefined) {
    const width = mesh.colors.length / count;
    if (width !== 3 && width !== 4) throw new RangeError(`meshes[${index}].colors must hold 3 or 4 values per vertex`);
    checkFloats(mesh.colors, width, count, `meshes[${index}].colors`);
  }
  if (mesh.indices !== undefined) {
    if (!INDEX_TYPES.has(mesh.indices.constructor)) {
      throw new TypeError(`meshes[${index}].indices must be a Uint8Array, Uint16Array or Uint32Array`);
    }
    if (mesh.indices.length === 0 || mesh.indices.length % 3 !== 0) {
      throw new RangeError(`meshes[${index}].indices must hold whole triangles`);
    }
    for (const value of mesh.indices) {
      if (value >= count) throw new RangeError(`meshes[${index}].indices refers to vertex ${value} of ${count}`);
    }
  } else if (count % 3 !== 0) {
    throw new RangeError(`meshes[${index}] without indices must hold whole triangles`);
  }
  const material = {...MATERIAL_DEFAULTS, ...(mesh.material === undefined ? {} : (checkKeys(mesh.material, MATERIAL_KEYS,
    `meshes[${index}].material`), mesh.material))};
  finiteVector(material.color, 4, `meshes[${index}].material.color`);
  finiteVector(material.emissive, 3, `meshes[${index}].material.emissive`);
  for (const key of ['metallic', 'roughness']) {
    if (!(material[key] >= 0 && material[key] <= 1)) throw new RangeError(`meshes[${index}].material.${key} is in [0, 1]`);
  }
  if (!material.color.every((value) => value >= 0 && value <= 1)) throw new RangeError('material colour values are in [0, 1]');
  return {count, material};
}

function checkNodes(nodes, meshCount) {
  const parent = new Array(nodes.length).fill(-1);
  nodes.forEach((node, index) => {
    checkKeys(node, NODE_KEYS, `nodes[${index}]`);
    if (node.mesh !== undefined && !(Number.isInteger(node.mesh) && node.mesh >= 0 && node.mesh < meshCount)) {
      throw new RangeError(`nodes[${index}].mesh is not a mesh index`);
    }
    if (node.translation !== undefined) finiteVector(node.translation, 3, `nodes[${index}].translation`);
    if (node.scale !== undefined) finiteVector(node.scale, 3, `nodes[${index}].scale`);
    if (node.rotation !== undefined) {
      finiteVector(node.rotation, 4, `nodes[${index}].rotation`);
      if (Math.abs(Math.hypot(...node.rotation) - 1) > UNIT_TOLERANCE) throw new RangeError(`nodes[${index}].rotation is not a unit quaternion`);
    }
    for (const child of node.children ?? []) {
      if (!(Number.isInteger(child) && child >= 0 && child < nodes.length) || child === index) {
        throw new RangeError(`nodes[${index}].children holds an invalid node ${child}`);
      }
      if (parent[child] >= 0) throw new RangeError(`node ${child} has two parents`);
      parent[child] = index;
    }
  });
  nodes.forEach((node, index) => {
    const seen = new Set([index]);
    for (let current = parent[index]; current >= 0; current = parent[current]) {
      if (seen.has(current)) throw new RangeError(`node ${index} is part of a cycle`);
      seen.add(current);
    }
  });
  return parent;
}

function settingsOf(options) {
  checkKeys(options, new Set(Object.keys(GLTF_WRITER_DEFAULTS)), 'options');
  const settings = {...GLTF_WRITER_DEFAULTS, ...options};
  for (const key of Object.keys(GLTF_WRITER_DEFAULTS)) {
    if (typeof settings[key] !== 'string') throw new TypeError(`${key} must be a string`);
  }
  return settings;
}

// The document without its buffer uri, and the packed binary data its buffer views point into.
function build(input, options) {
  checkKeys(input, new Set(['meshes', 'nodes']), 'input');
  const settings = settingsOf(options);
  const meshes = input.meshes;
  if (!Array.isArray(meshes) || meshes.length === 0) throw new RangeError('input.meshes must be a non-empty array');
  const checked = meshes.map(checkMesh);
  const nodes = input.nodes ?? meshes.map((_, index) => ({mesh: index}));
  if (!Array.isArray(nodes) || nodes.length === 0) throw new RangeError('input.nodes must be a non-empty array');
  const parent = checkNodes(nodes, meshes.length);
  const chunks = [];
  let byteLength = 0;
  const gltf = {asset: {version: '2.0', generator: settings.generator}, scene: 0, scenes: [], nodes: [], meshes: [],
    materials: [], accessors: [], bufferViews: [], buffers: []};
  const view = (array, target) => {
    const bytes = new Uint8Array(array.buffer, array.byteOffset, array.byteLength);
    const padding = (4 - (byteLength % 4)) % 4;
    if (padding) chunks.push(new Uint8Array(padding));
    byteLength += padding;
    gltf.bufferViews.push({buffer: 0, byteOffset: byteLength, byteLength: bytes.byteLength, target});
    chunks.push(bytes);
    byteLength += bytes.byteLength;
    return gltf.bufferViews.length - 1;
  };
  const accessor = (array, type, width, componentType, target, bounds) => {
    const entry = {bufferView: view(array, target), componentType, count: array.length / width, type};
    if (bounds) {
      entry.min = Array.from({length: width}, (_, axis) => Infinity);
      entry.max = Array.from({length: width}, (_, axis) => -Infinity);
      for (let index = 0; index < array.length; index += 1) {
        const axis = index % width;
        entry.min[axis] = Math.min(entry.min[axis], array[index]);
        entry.max[axis] = Math.max(entry.max[axis], array[index]);
      }
    }
    gltf.accessors.push(entry);
    return gltf.accessors.length - 1;
  };
  meshes.forEach((mesh, index) => {
    const {material} = checked[index];
    const attributes = {POSITION: accessor(mesh.positions, 'VEC3', 3, FLOAT, ARRAY_BUFFER, true)};
    if (mesh.normals) attributes.NORMAL = accessor(mesh.normals, 'VEC3', 3, FLOAT, ARRAY_BUFFER, false);
    if (mesh.uvs) attributes.TEXCOORD_0 = accessor(mesh.uvs, 'VEC2', 2, FLOAT, ARRAY_BUFFER, false);
    if (mesh.colors) {
      const width = mesh.colors.length / checked[index].count;
      attributes.COLOR_0 = accessor(mesh.colors, width === 3 ? 'VEC3' : 'VEC4', width, FLOAT, ARRAY_BUFFER, false);
    }
    const primitive = {attributes, material: index};
    if (mesh.indices) {
      primitive.indices = accessor(mesh.indices, 'SCALAR', 1, INDEX_TYPES.get(mesh.indices.constructor), ELEMENT_ARRAY_BUFFER, false);
    }
    gltf.meshes.push({...(mesh.name ? {name: String(mesh.name)} : {}), primitives: [primitive]});
    const entry = {pbrMetallicRoughness: {baseColorFactor: [...material.color], metallicFactor: material.metallic,
      roughnessFactor: material.roughness}};
    if (material.name) entry.name = String(material.name);
    if (material.emissive.some((value) => value !== 0)) entry.emissiveFactor = [...material.emissive];
    if (material.doubleSided) entry.doubleSided = true;
    gltf.materials.push(entry);
  });
  nodes.forEach((node) => {
    const entry = {};
    for (const key of ['name', 'mesh', 'translation', 'rotation', 'scale']) {
      if (node[key] !== undefined) entry[key] = Array.isArray(node[key]) ? [...node[key]] : node[key];
    }
    if (node.children && node.children.length) entry.children = [...node.children];
    gltf.nodes.push(entry);
  });
  gltf.scenes.push({name: settings.sceneName, nodes: nodes.map((_, index) => index).filter((index) => parent[index] < 0)});
  const total = byteLength + ((4 - (byteLength % 4)) % 4);
  const binary = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    binary.set(chunk, offset);
    offset += chunk.byteLength;
  }
  gltf.buffers.push({byteLength: total});
  return {gltf, binary};
}

/**
 * A glTF 2.0 document (a plain object; JSON.stringify it to save a .gltf) with one buffer embedded as a base64 data
 * URI. input = {meshes: [{positions, normals?, uvs?, colors?, indices?, name?, material?}], nodes?: [{mesh?,
 * translation?, rotation?, scale?, children?, name?}]}; without nodes, each mesh gets a root node.
 */
export function writeGltf(input, options = {}) {
  const {gltf, binary} = build(input, options);
  gltf.buffers[0].uri = `data:application/octet-stream;base64,${encodeBase64(binary)}`;
  return gltf;
}

/** The same scene as a GLB container (Uint8Array): the JSON chunk padded with spaces and the BIN chunk with zeros. */
export function writeGlb(input, options = {}) {
  const {gltf, binary} = build(input, options);
  const text = new TextEncoder().encode(JSON.stringify(gltf));
  const jsonLength = Math.ceil(text.length / 4) * 4;
  const total = 12 + 8 + jsonLength + 8 + binary.byteLength;
  const out = new Uint8Array(total);
  const view = new DataView(out.buffer);
  view.setUint32(0, 0x46546c67, true);
  view.setUint32(4, 2, true);
  view.setUint32(8, total, true);
  view.setUint32(12, jsonLength, true);
  view.setUint32(16, 0x4e4f534a, true);
  out.set(text, 20);
  out.fill(0x20, 20 + text.length, 20 + jsonLength);
  view.setUint32(20 + jsonLength, binary.byteLength, true);
  view.setUint32(24 + jsonLength, 0x004e4942, true);
  out.set(binary, 28 + jsonLength);
  return out;
}

/**
 * A writer mesh from a three.js BufferGeometry (or any object with the same attribute layout): position, normal, uv
 * and color attributes and the index are copied into new typed arrays. Interleaved or normalized integer attributes
 * are refused.
 */
export function meshFromBufferGeometry(geometry, extra = {}) {
  if (!geometry || !geometry.attributes || !geometry.attributes.position) throw new TypeError('geometry needs a position attribute');
  const read = (name, width) => {
    const attribute = geometry.attributes[name];
    if (!attribute) return undefined;
    if (attribute.isInterleavedBufferAttribute || !ArrayBuffer.isView(attribute.array)) {
      throw new TypeError(`${name} is interleaved; deinterleave it first`);
    }
    if (attribute.itemSize !== width && !(name === 'color' && attribute.itemSize === 4)) {
      throw new TypeError(`${name} must have itemSize ${width}`);
    }
    if (attribute.normalized) throw new TypeError(`${name} is a normalized integer attribute`);
    return Float32Array.from(attribute.array);
  };
  const mesh = {positions: read('position', 3)};
  for (const [name, key, width] of [['normal', 'normals', 3], ['uv', 'uvs', 2], ['color', 'colors', 3]]) {
    const values = read(name, width);
    if (values) mesh[key] = values;
  }
  if (geometry.index) {
    const source = geometry.index.array;
    mesh.indices = mesh.positions.length / 3 > 65535 ? Uint32Array.from(source) : Uint16Array.from(source);
  }
  return {...mesh, ...extra};
}
