// glTF 2.0 document validator: checks the structure of a glTF JSON document and, when the binary data is at hand,
// the index and bound values it describes. Every problem is reported with a stable code and a JSON pointer to the
// offending value. Original Baltor implementation written from the glTF 2.0 specification; runs on plain objects and
// typed arrays in a page, a worker or Node, with no three.js.

/** Bytes per component for each accessor componentType. */
export const GLTF_COMPONENT_TYPES = Object.freeze({5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4});
/** Components per element for each accessor type. */
export const GLTF_TYPE_COMPONENTS = Object.freeze({SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT2: 4, MAT3: 9, MAT4: 16});
/** Default options of validateGltf. */
export const VALIDATOR_DEFAULTS = Object.freeze({maxIssues: 500, checkData: true});

const FLOAT = 5126;
const UNSIGNED_BYTE = 5121;
const UNSIGNED_SHORT = 5123;
const UNSIGNED_INT = 5125;
const ARRAY_BUFFER = 34962;
const ELEMENT_ARRAY_BUFFER = 34963;
const TRIANGLES = 4;
const TOP_LEVEL_ARRAYS = ['accessors', 'animations', 'buffers', 'bufferViews', 'cameras', 'images', 'materials', 'meshes',
  'nodes', 'samplers', 'scenes', 'skins', 'textures'];
const MAG_FILTERS = new Set([9728, 9729]);
const MIN_FILTERS = new Set([9728, 9729, 9984, 9985, 9986, 9987]);
const WRAPS = new Set([33071, 33648, 10497]);
const ALPHA_MODES = new Set(['OPAQUE', 'MASK', 'BLEND']);
const PATHS = new Set(['translation', 'rotation', 'scale', 'weights']);
const INTERPOLATIONS = new Set(['LINEAR', 'STEP', 'CUBICSPLINE']);
const IMAGE_TYPES = new Set(['image/png', 'image/jpeg']);
const SEMANTIC = /^(POSITION|NORMAL|TANGENT|TEXCOORD_\d+|COLOR_\d+|JOINTS_\d+|WEIGHTS_\d+|_.+)$/;
const BASE64_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const BASE64_VALUES = new Map(Array.from(BASE64_ALPHABET, (character, index) => [character, index]));
const UNIT_TOLERANCE = 1e-3;
const BOUNDS_TOLERANCE = 1e-6;

function own(table, key) {
  return Object.prototype.hasOwnProperty.call(table, key) ? table[key] : undefined;
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isIndex(value) {
  return Number.isInteger(value) && value >= 0;
}

function numbers(value, length) {
  return Array.isArray(value) && value.length === length && value.every((entry) => typeof entry === 'number'
    && Number.isFinite(entry));
}

function pointerOf(...parts) {
  return parts.map((part) => `/${String(part).replace(/~/g, '~0').replace(/\//g, '~1')}`).join('');
}

/**
 * The bytes of a base64 data URI (data:[type][;parameters];base64,...), or null when the URI is not a base64 data
 * URI. Throws TypeError on malformed base64.
 */
export function decodeDataUri(uri) {
  if (typeof uri !== 'string' || !uri.startsWith('data:')) return null;
  const comma = uri.indexOf(',');
  if (comma < 0) throw new TypeError('a data URI needs a comma before its data');
  const parameters = uri.slice(5, comma).split(';');
  if (!parameters.slice(1).includes('base64')) return null;
  const text = uri.slice(comma + 1);
  if (text.length % 4 !== 0) throw new TypeError('base64 text length is not a multiple of 4');
  const padding = text.endsWith('==') ? 2 : text.endsWith('=') ? 1 : 0;
  const bytes = new Uint8Array((text.length / 4) * 3 - padding);
  let written = 0;
  for (let index = 0; index < text.length; index += 4) {
    let group = 0;
    for (let offset = 0; offset < 4; offset += 1) {
      const character = text[index + offset];
      const isPadding = index + 4 === text.length && offset >= 4 - padding;
      const value = isPadding ? 0 : BASE64_VALUES.get(character);
      if (value === undefined || (isPadding && character !== '=')) {
        throw new TypeError(`invalid base64 character at ${index + offset}`);
      }
      group = group * 64 + value;
    }
    for (const shift of [16, 8, 0]) {
      if (written < bytes.length) bytes[written++] = (group >> shift) & 255;
    }
  }
  return bytes;
}

function asBytes(data) {
  if (data instanceof ArrayBuffer) return new Uint8Array(data);
  if (ArrayBuffer.isView(data)) return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
  return null;
}

function readComponent(view, offset, componentType) {
  switch (componentType) {
    case 5120: return view.getInt8(offset);
    case 5121: return view.getUint8(offset);
    case 5122: return view.getInt16(offset, true);
    case 5123: return view.getUint16(offset, true);
    case 5125: return view.getUint32(offset, true);
    default: return view.getFloat32(offset, true);
  }
}

class Report {
  constructor(maxIssues) {
    this.errors = [];
    this.warnings = [];
    this.maxIssues = maxIssues;
    this.truncated = false;
  }

  add(list, code, pointer, message) {
    if (this.errors.length + this.warnings.length >= this.maxIssues) {
      this.truncated = true;
      return;
    }
    list.push({code, pointer, message});
  }

  error(code, pointer, message) {
    this.add(this.errors, code, pointer, message);
  }

  warning(code, pointer, message) {
    this.add(this.warnings, code, pointer, message);
  }
}

/**
 * Validate a glTF 2.0 document. Options: buffers (an array of ArrayBuffers or typed arrays standing for buffers by
 * index, for example a GLB's BIN chunk as buffers[0]), maxIssues, checkData (read index and bound values when the data
 * is at hand; base64 data URIs are decoded). Returns {valid, errors, warnings, truncated, counts}; each issue is
 * {code, pointer, message} with a JSON pointer into the document.
 */
export function validateGltf(gltf, options = {}) {
  if (!isObject(options)) throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(VALIDATOR_DEFAULTS, key) && key !== 'buffers') throw new TypeError(`unknown validator option ${key}`);
  }
  const settings = {...VALIDATOR_DEFAULTS, ...options};
  if (!Number.isInteger(settings.maxIssues) || settings.maxIssues < 1) throw new RangeError('maxIssues must be at least 1');
  const report = new Report(settings.maxIssues);
  const counts = {};
  if (!isObject(gltf)) {
    report.error('document_not_object', '', 'the document is not a JSON object');
    return finish(report, counts);
  }
  const list = (name) => (Array.isArray(gltf[name]) ? gltf[name] : []);
  for (const name of TOP_LEVEL_ARRAYS) {
    counts[name] = list(name).length;
    if (gltf[name] === undefined) continue;
    if (!Array.isArray(gltf[name])) report.error('not_an_array', pointerOf(name), `${name} must be an array`);
    else if (gltf[name].length === 0) report.error('empty_array', pointerOf(name), `${name} must not be empty`);
  }
  const reference = (value, name, pointer) => {
    if (!isIndex(value)) {
      report.error('index_not_integer', pointer, `expected an index into ${name}`);
      return false;
    }
    if (value >= list(name).length) {
      report.error('index_out_of_range', pointer, `${name}[${value}] does not exist`);
      return false;
    }
    return true;
  };
  checkAsset(gltf, report);
  const data = bufferData(gltf, settings, report, list);
  checkBufferViews(list, reference, report);
  checkAccessors(list, reference, report, settings.checkData ? data : []);
  checkMeshes(list, reference, report, settings.checkData ? data : []);
  checkNodesAndScenes(gltf, list, reference, report);
  checkMaterialsAndTextures(list, reference, report);
  checkCamerasSkinsAnimations(list, reference, report);
  checkExtensions(gltf, report);
  return finish(report, counts);
}

function finish(report, counts) {
  return {valid: report.errors.length === 0, errors: report.errors, warnings: report.warnings,
    truncated: report.truncated, counts};
}

function checkAsset(gltf, report) {
  const asset = gltf.asset;
  if (!isObject(asset)) {
    report.error('asset_missing', '/asset', 'asset is required');
    return;
  }
  const versionPattern = /^\d+\.\d+$/;
  if (typeof asset.version !== 'string' || !versionPattern.test(asset.version)) {
    report.error('asset_version_invalid', '/asset/version', 'asset.version must look like 2.0');
  } else if (!asset.version.startsWith('2.')) {
    report.error('asset_version_unsupported', '/asset/version', `version ${asset.version} is not glTF 2`);
  }
  if (asset.minVersion !== undefined) {
    const valid = typeof asset.minVersion === 'string' && versionPattern.test(asset.minVersion)
      && asset.minVersion.startsWith('2.') && typeof asset.version === 'string'
      && Number(asset.minVersion.split('.')[1]) <= Number(asset.version.split('.')[1]);
    if (!valid) report.error('asset_min_version_invalid', '/asset/minVersion', 'minVersion must be 2.x and not above version');
  }
}

function bufferData(gltf, settings, report, list) {
  const supplied = Array.isArray(settings.buffers) ? settings.buffers : [];
  return list('buffers').map((buffer, index) => {
    const pointer = pointerOf('buffers', index);
    if (!isObject(buffer)) {
      report.error('not_an_object', pointer, 'a buffer must be an object');
      return null;
    }
    if (!isIndex(buffer.byteLength) || buffer.byteLength < 1) {
      report.error('buffer_length_invalid', `${pointer}/byteLength`, 'byteLength must be a positive integer');
    }
    let bytes = supplied[index] === undefined || supplied[index] === null ? null : asBytes(supplied[index]);
    if (supplied[index] !== undefined && supplied[index] !== null && bytes === null) {
      throw new TypeError(`options.buffers[${index}] must be an ArrayBuffer or a typed array`);
    }
    if (buffer.uri === undefined) {
      if (index !== 0) report.error('buffer_uri_missing', `${pointer}/uri`, 'only buffer 0 of a GLB may omit uri');
    } else if (typeof buffer.uri !== 'string') {
      report.error('buffer_uri_invalid', `${pointer}/uri`, 'uri must be a string');
    } else if (bytes === null && buffer.uri.startsWith('data:')) {
      try {
        bytes = decodeDataUri(buffer.uri);
        if (bytes === null) report.warning('buffer_uri_not_base64', `${pointer}/uri`, 'only base64 data URIs are read');
      } catch (error) {
        report.error('buffer_uri_invalid', `${pointer}/uri`, error.message);
      }
    }
    if (bytes === null) {
      if (settings.checkData) report.warning('buffer_data_unavailable', pointer, 'data checks skipped for this buffer');
      return null;
    }
    if (isIndex(buffer.byteLength) && bytes.byteLength < buffer.byteLength) {
      report.error('buffer_data_too_short', pointer, `${bytes.byteLength} bytes for byteLength ${buffer.byteLength}`);
      return null;
    }
    return bytes;
  });
}

function checkBufferViews(list, reference, report) {
  list('bufferViews').forEach((view, index) => {
    const pointer = pointerOf('bufferViews', index);
    if (!isObject(view)) {
      report.error('not_an_object', pointer, 'a bufferView must be an object');
      return;
    }
    const known = reference(view.buffer, 'buffers', `${pointer}/buffer`);
    const offset = view.byteOffset ?? 0;
    if (!isIndex(offset)) report.error('buffer_view_offset_invalid', `${pointer}/byteOffset`, 'byteOffset must be >= 0');
    if (!isIndex(view.byteLength) || view.byteLength < 1) {
      report.error('buffer_view_length_invalid', `${pointer}/byteLength`, 'byteLength must be a positive integer');
    } else if (known && isIndex(offset) && offset + view.byteLength > list('buffers')[view.buffer].byteLength) {
      report.error('buffer_view_out_of_bounds', pointer, 'the view runs past the end of its buffer');
    }
    if (view.byteStride !== undefined && !(Number.isInteger(view.byteStride) && view.byteStride >= 4
      && view.byteStride <= 252 && view.byteStride % 4 === 0)) {
      report.error('buffer_view_stride_invalid', `${pointer}/byteStride`, 'byteStride must be 4 to 252, a multiple of 4');
    }
    if (view.target !== undefined && view.target !== ARRAY_BUFFER && view.target !== ELEMENT_ARRAY_BUFFER) {
      report.error('buffer_view_target_invalid', `${pointer}/target`, 'target must be 34962 or 34963');
    }
  });
}

// The element values of an accessor when its data is at hand, as arrays of numbers per element; null otherwise.
function accessorValues(list, accessor, data) {
  if (!accessor || accessor.sparse !== undefined || !isIndex(accessor.bufferView)) return null;
  const view = list('bufferViews')[accessor.bufferView];
  if (!isObject(view) || !isIndex(view.buffer)) return null;
  const bytes = data[view.buffer];
  const componentBytes = own(GLTF_COMPONENT_TYPES, accessor.componentType);
  const components = own(GLTF_TYPE_COMPONENTS, accessor.type);
  if (!bytes || !componentBytes || !components || components > 4 || !isIndex(accessor.count)) return null;
  const stride = view.byteStride ?? componentBytes * components;
  const start = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
  const end = start + stride * (accessor.count - 1) + componentBytes * components;
  if (end > bytes.byteLength || end > (view.byteOffset ?? 0) + view.byteLength) return null;
  const reader = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const values = [];
  for (let element = 0; element < accessor.count; element += 1) {
    const row = [];
    for (let component = 0; component < components; component += 1) {
      row.push(readComponent(reader, start + element * stride + component * componentBytes, accessor.componentType));
    }
    values.push(row);
  }
  return values;
}

function checkAccessors(list, reference, report, data) {
  list('accessors').forEach((accessor, index) => {
    const pointer = pointerOf('accessors', index);
    if (!isObject(accessor)) {
      report.error('not_an_object', pointer, 'an accessor must be an object');
      return;
    }
    const componentBytes = own(GLTF_COMPONENT_TYPES, accessor.componentType);
    const components = own(GLTF_TYPE_COMPONENTS, accessor.type);
    if (!componentBytes) report.error('accessor_component_type_invalid', `${pointer}/componentType`, 'unknown componentType');
    if (!components) report.error('accessor_type_invalid', `${pointer}/type`, 'unknown accessor type');
    if (!Number.isInteger(accessor.count) || accessor.count < 1) {
      report.error('accessor_count_invalid', `${pointer}/count`, 'count must be at least 1');
    }
    if (accessor.normalized === true && (accessor.componentType === FLOAT || accessor.componentType === UNSIGNED_INT)) {
      report.error('accessor_normalized_invalid', `${pointer}/normalized`, 'FLOAT and UNSIGNED_INT cannot be normalized');
    }
    const offset = accessor.byteOffset ?? 0;
    if (!isIndex(offset)) report.error('accessor_offset_invalid', `${pointer}/byteOffset`, 'byteOffset must be >= 0');
    if (accessor.bufferView === undefined && accessor.byteOffset !== undefined) {
      report.error('accessor_offset_without_view', `${pointer}/byteOffset`, 'byteOffset needs a bufferView');
    }
    for (const key of ['min', 'max']) {
      if (accessor[key] !== undefined && components && !numbers(accessor[key], components)) {
        report.error('accessor_bounds_invalid', `${pointer}/${key}`, `${key} must hold ${components} numbers`);
      }
    }
    if (accessor.bufferView !== undefined && reference(accessor.bufferView, 'bufferViews', `${pointer}/bufferView`)
      && componentBytes && components && Number.isInteger(accessor.count) && accessor.count >= 1 && isIndex(offset)) {
      const view = list('bufferViews')[accessor.bufferView];
      const element = componentBytes * components;
      const stride = view.byteStride ?? element;
      if (stride < element) report.error('accessor_stride_too_small', pointer, `byteStride ${stride} < element ${element}`);
      if (((view.byteOffset ?? 0) + offset) % componentBytes !== 0) {
        report.error('accessor_offset_unaligned', `${pointer}/byteOffset`, `offset not aligned to ${componentBytes} bytes`);
      }
      if (isIndex(view.byteLength) && offset + stride * (accessor.count - 1) + element > view.byteLength) {
        report.error('accessor_out_of_bounds', pointer, 'the accessor runs past the end of its bufferView');
      }
    }
    if (accessor.sparse !== undefined) {
      const sparse = accessor.sparse;
      if (!isObject(sparse) || !Number.isInteger(sparse.count) || sparse.count < 1 || !isObject(sparse.indices)
        || !isObject(sparse.values)) {
        report.error('accessor_sparse_invalid', `${pointer}/sparse`, 'sparse needs count, indices and values');
      } else {
        reference(sparse.indices.bufferView, 'bufferViews', `${pointer}/sparse/indices/bufferView`);
        reference(sparse.values.bufferView, 'bufferViews', `${pointer}/sparse/values/bufferView`);
        report.warning('accessor_sparse_not_read', `${pointer}/sparse`, 'sparse values are not checked');
      }
    }
    const values = accessor.normalized === true ? null : accessorValues(list, accessor, data);
    if (values && numbers(accessor.min, components) && numbers(accessor.max, components)) {
      outer: for (const row of values) {
        for (let component = 0; component < components; component += 1) {
          const tolerance = BOUNDS_TOLERANCE * Math.max(1, Math.abs(row[component]));
          if (row[component] < accessor.min[component] - tolerance || row[component] > accessor.max[component] + tolerance) {
            report.error('accessor_value_outside_bounds', pointer, `a value lies outside min and max in component ${component}`);
            break outer;
          }
        }
      }
    }
  });
}

const ATTRIBUTE_FORMATS = [
  [/^POSITION$/, ['VEC3'], [FLOAT], false],
  [/^NORMAL$/, ['VEC3'], [FLOAT], false],
  [/^TANGENT$/, ['VEC4'], [FLOAT], false],
  [/^TEXCOORD_\d+$/, ['VEC2'], [FLOAT, UNSIGNED_BYTE, UNSIGNED_SHORT], true],
  [/^COLOR_\d+$/, ['VEC3', 'VEC4'], [FLOAT, UNSIGNED_BYTE, UNSIGNED_SHORT], true],
  [/^JOINTS_\d+$/, ['VEC4'], [UNSIGNED_BYTE, UNSIGNED_SHORT], false],
  [/^WEIGHTS_\d+$/, ['VEC4'], [FLOAT, UNSIGNED_BYTE, UNSIGNED_SHORT], true],
];

function attributeFormatProblem(semantic, accessor) {
  for (const [pattern, types, componentTypes, integersNormalized] of ATTRIBUTE_FORMATS) {
    if (!pattern.test(semantic)) continue;
    if (!types.includes(accessor.type) || !componentTypes.includes(accessor.componentType)) {
      return `${semantic} needs ${types.join(' or ')} of componentType ${componentTypes.join(' or ')}`;
    }
    if (integersNormalized && accessor.componentType !== FLOAT && accessor.normalized !== true) {
      return `${semantic} with integer components must be normalized`;
    }
    return null;
  }
  return null;
}

function checkMeshes(list, reference, report, data) {
  const accessors = list('accessors');
  list('meshes').forEach((mesh, meshIndex) => {
    const meshPointer = pointerOf('meshes', meshIndex);
    if (!isObject(mesh) || !Array.isArray(mesh.primitives) || mesh.primitives.length === 0) {
      report.error('mesh_primitives_missing', `${meshPointer}/primitives`, 'a mesh needs at least one primitive');
      return;
    }
    mesh.primitives.forEach((primitive, primitiveIndex) => {
      const pointer = `${meshPointer}/primitives/${primitiveIndex}`;
      if (!isObject(primitive) || !isObject(primitive.attributes) || Object.keys(primitive.attributes).length === 0) {
        report.error('primitive_attributes_missing', `${pointer}/attributes`, 'a primitive needs attributes');
        return;
      }
      const mode = primitive.mode ?? TRIANGLES;
      if (!(Number.isInteger(mode) && mode >= 0 && mode <= 6)) report.error('primitive_mode_invalid', `${pointer}/mode`, 'mode is 0 to 6');
      const countsBySemantic = new Map();
      for (const [semantic, index] of Object.entries(primitive.attributes)) {
        const attributePointer = `${pointer}/attributes/${semantic}`;
        if (!SEMANTIC.test(semantic)) report.warning('attribute_semantic_unknown', attributePointer, `${semantic} is not a known semantic`);
        if (!reference(index, 'accessors', attributePointer)) continue;
        const accessor = accessors[index];
        if (!isObject(accessor)) continue;
        const problem = attributeFormatProblem(semantic, accessor);
        if (problem) report.error('attribute_format_invalid', attributePointer, problem);
        if (semantic === 'POSITION' && !(numbers(accessor.min, 3) && numbers(accessor.max, 3))) {
          report.error('position_bounds_missing', pointerOf('accessors', index), 'POSITION accessors need min and max');
        }
        countsBySemantic.set(semantic, accessor.count);
      }
      const distinct = new Set(countsBySemantic.values());
      if (distinct.size > 1) report.error('attribute_count_mismatch', `${pointer}/attributes`, 'attribute counts differ');
      const vertexCount = countsBySemantic.get('POSITION');
      if (primitive.material !== undefined) reference(primitive.material, 'materials', `${pointer}/material`);
      let elementCount = vertexCount;
      if (primitive.indices !== undefined && reference(primitive.indices, 'accessors', `${pointer}/indices`)) {
        const accessor = accessors[primitive.indices];
        if (isObject(accessor)) {
          elementCount = accessor.count;
          if (accessor.type !== 'SCALAR' || ![UNSIGNED_BYTE, UNSIGNED_SHORT, UNSIGNED_INT].includes(accessor.componentType)
            || accessor.normalized === true) {
            report.error('indices_format_invalid', `${pointer}/indices`, 'indices are unnormalized unsigned SCALARs');
          }
          const values = accessorValues(list, accessor, data);
          if (values && Number.isInteger(vertexCount)) {
            const restart = 2 ** (8 * own(GLTF_COMPONENT_TYPES, accessor.componentType)) - 1;
            const bad = values.findIndex(([value]) => value >= vertexCount || value === restart);
            if (bad >= 0) report.error('index_value_out_of_range', `${pointer}/indices`, `index ${bad} is ${values[bad][0]}`);
          }
        }
      }
      if (Number.isInteger(elementCount)) {
        const remainder = mode === TRIANGLES ? elementCount % 3 : mode === 1 ? elementCount % 2 : 0;
        const tooFew = (mode === 5 || mode === 6) && elementCount < 3;
        if (remainder !== 0 || tooFew) report.error('primitive_count_invalid', pointer, `count ${elementCount} does not fit mode ${mode}`);
      }
      if (primitive.targets !== undefined) {
        if (!Array.isArray(primitive.targets) || primitive.targets.length === 0) {
          report.error('morph_targets_invalid', `${pointer}/targets`, 'targets must be a non-empty array');
        } else {
          primitive.targets.forEach((target, targetIndex) => {
            for (const [semantic, index] of Object.entries(isObject(target) ? target : {})) {
              const targetPointer = `${pointer}/targets/${targetIndex}/${semantic}`;
              if (reference(index, 'accessors', targetPointer) && isObject(accessors[index])
                && Number.isInteger(vertexCount) && accessors[index].count !== vertexCount) {
                report.error('morph_target_count_mismatch', targetPointer, 'a morph target needs one value per vertex');
              }
            }
          });
        }
      }
    });
  });
}

function checkNodesAndScenes(gltf, list, reference, report) {
  const nodes = list('nodes');
  const parentOf = new Array(nodes.length).fill(-1);
  nodes.forEach((node, index) => {
    const pointer = pointerOf('nodes', index);
    if (!isObject(node)) {
      report.error('not_an_object', pointer, 'a node must be an object');
      return;
    }
    for (const [key, name] of [['mesh', 'meshes'], ['camera', 'cameras'], ['skin', 'skins']]) {
      if (node[key] !== undefined) reference(node[key], name, `${pointer}/${key}`);
    }
    if (node.children !== undefined) {
      if (!Array.isArray(node.children)) {
        report.error('not_an_array', `${pointer}/children`, 'children must be an array');
      } else {
        const seen = new Set();
        node.children.forEach((child, slot) => {
          const childPointer = `${pointer}/children/${slot}`;
          if (!reference(child, 'nodes', childPointer)) return;
          if (seen.has(child)) report.error('duplicate_index', childPointer, `node ${child} is listed twice`);
          seen.add(child);
          if (child === index) report.error('node_child_self', childPointer, 'a node cannot be its own child');
          else if (parentOf[child] >= 0) report.error('node_multiple_parents', childPointer, `node ${child} already has a parent`);
          else parentOf[child] = index;
        });
      }
    }
    const hasTrs = ['translation', 'rotation', 'scale'].some((key) => node[key] !== undefined);
    if (node.matrix !== undefined) {
      if (!numbers(node.matrix, 16)) report.error('node_matrix_invalid', `${pointer}/matrix`, 'matrix must hold 16 numbers');
      if (hasTrs) report.error('node_matrix_and_trs', pointer, 'a node has either matrix or translation, rotation, scale');
    }
    if (node.translation !== undefined && !numbers(node.translation, 3)) {
      report.error('node_translation_invalid', `${pointer}/translation`, 'translation must hold 3 numbers');
    }
    if (node.scale !== undefined && !numbers(node.scale, 3)) report.error('node_scale_invalid', `${pointer}/scale`, 'scale must hold 3 numbers');
    if (node.rotation !== undefined) {
      if (!numbers(node.rotation, 4)) report.error('node_rotation_invalid', `${pointer}/rotation`, 'rotation must hold 4 numbers');
      else if (Math.abs(Math.hypot(...node.rotation) - 1) > UNIT_TOLERANCE) {
        report.error('node_rotation_not_unit', `${pointer}/rotation`, 'rotation must be a unit quaternion');
      }
    }
  });
  nodes.forEach((node, index) => {
    const visited = new Set([index]);
    for (let current = parentOf[index]; current >= 0; current = parentOf[current]) {
      if (visited.has(current)) {
        report.error('node_cycle', pointerOf('nodes', index), 'the node is part of a cycle');
        return;
      }
      visited.add(current);
    }
  });
  if (gltf.scene !== undefined) reference(gltf.scene, 'scenes', '/scene');
  list('scenes').forEach((scene, index) => {
    const pointer = pointerOf('scenes', index);
    if (!isObject(scene) || scene.nodes === undefined) return;
    if (!Array.isArray(scene.nodes)) {
      report.error('not_an_array', `${pointer}/nodes`, 'scene nodes must be an array');
      return;
    }
    if (scene.nodes.length === 0) report.error('empty_array', `${pointer}/nodes`, 'scene nodes must not be empty');
    const seen = new Set();
    scene.nodes.forEach((root, slot) => {
      const rootPointer = `${pointer}/nodes/${slot}`;
      if (!reference(root, 'nodes', rootPointer)) return;
      if (seen.has(root)) report.error('duplicate_index', rootPointer, `node ${root} is listed twice`);
      seen.add(root);
      if (parentOf[root] >= 0) report.error('scene_node_not_root', rootPointer, `node ${root} has a parent`);
    });
  });
}

function checkMaterialsAndTextures(list, reference, report) {
  list('materials').forEach((material, index) => {
    const pointer = pointerOf('materials', index);
    if (!isObject(material)) return;
    const pbr = isObject(material.pbrMetallicRoughness) ? material.pbrMetallicRoughness : {};
    const textures = [['pbrMetallicRoughness/baseColorTexture', pbr.baseColorTexture],
      ['pbrMetallicRoughness/metallicRoughnessTexture', pbr.metallicRoughnessTexture],
      ['normalTexture', material.normalTexture], ['occlusionTexture', material.occlusionTexture],
      ['emissiveTexture', material.emissiveTexture]];
    for (const [path, info] of textures) {
      if (info === undefined) continue;
      if (!isObject(info)) report.error('not_an_object', `${pointer}/${path}`, 'a texture reference must be an object');
      else reference(info.index, 'textures', `${pointer}/${path}/index`);
    }
    if (pbr.baseColorFactor !== undefined && !(numbers(pbr.baseColorFactor, 4)
      && pbr.baseColorFactor.every((value) => value >= 0 && value <= 1))) {
      report.error('material_factor_invalid', `${pointer}/pbrMetallicRoughness/baseColorFactor`, 'four numbers in [0, 1]');
    }
    for (const key of ['metallicFactor', 'roughnessFactor']) {
      if (pbr[key] !== undefined && !(typeof pbr[key] === 'number' && pbr[key] >= 0 && pbr[key] <= 1)) {
        report.error('material_factor_invalid', `${pointer}/pbrMetallicRoughness/${key}`, 'a number in [0, 1]');
      }
    }
    if (material.alphaMode !== undefined && !ALPHA_MODES.has(material.alphaMode)) {
      report.error('material_alpha_mode_invalid', `${pointer}/alphaMode`, 'OPAQUE, MASK or BLEND');
    }
  });
  list('textures').forEach((texture, index) => {
    const pointer = pointerOf('textures', index);
    if (!isObject(texture)) return;
    if (texture.sampler !== undefined) reference(texture.sampler, 'samplers', `${pointer}/sampler`);
    if (texture.source !== undefined) reference(texture.source, 'images', `${pointer}/source`);
  });
  list('samplers').forEach((sampler, index) => {
    const pointer = pointerOf('samplers', index);
    if (!isObject(sampler)) return;
    const rules = [['magFilter', MAG_FILTERS], ['minFilter', MIN_FILTERS], ['wrapS', WRAPS], ['wrapT', WRAPS]];
    for (const [key, allowed] of rules) {
      if (sampler[key] !== undefined && !allowed.has(sampler[key])) report.error('sampler_value_invalid', `${pointer}/${key}`, `invalid ${key}`);
    }
  });
  list('images').forEach((image, index) => {
    const pointer = pointerOf('images', index);
    if (!isObject(image)) return;
    if ((image.uri === undefined) === (image.bufferView === undefined)) {
      report.error('image_source_invalid', pointer, 'an image has either uri or bufferView');
    }
    if (image.bufferView !== undefined) {
      reference(image.bufferView, 'bufferViews', `${pointer}/bufferView`);
      if (!IMAGE_TYPES.has(image.mimeType)) report.warning('image_mime_type_unknown', `${pointer}/mimeType`, 'not image/png or image/jpeg');
    }
  });
}

function checkCamerasSkinsAnimations(list, reference, report) {
  const accessors = list('accessors');
  list('cameras').forEach((camera, index) => {
    const pointer = pointerOf('cameras', index);
    if (!isObject(camera)) return;
    const perspective = camera.perspective;
    const orthographic = camera.orthographic;
    let valid = false;
    if (camera.type === 'perspective' && isObject(perspective)) {
      valid = perspective.yfov > 0 && perspective.znear > 0
        && (perspective.zfar === undefined || perspective.zfar > perspective.znear)
        && (perspective.aspectRatio === undefined || perspective.aspectRatio > 0);
    } else if (camera.type === 'orthographic' && isObject(orthographic)) {
      valid = orthographic.xmag !== 0 && orthographic.ymag !== 0 && typeof orthographic.xmag === 'number'
        && typeof orthographic.ymag === 'number' && orthographic.znear >= 0 && orthographic.zfar > orthographic.znear;
    }
    if (!valid) report.error('camera_invalid', pointer, 'the camera type and its projection values do not agree');
  });
  list('skins').forEach((skin, index) => {
    const pointer = pointerOf('skins', index);
    if (!isObject(skin) || !Array.isArray(skin.joints) || skin.joints.length === 0) {
      report.error('skin_joints_invalid', `${pointer}/joints`, 'a skin needs joints');
      return;
    }
    skin.joints.forEach((joint, slot) => reference(joint, 'nodes', `${pointer}/joints/${slot}`));
    if (skin.inverseBindMatrices !== undefined
      && reference(skin.inverseBindMatrices, 'accessors', `${pointer}/inverseBindMatrices`)) {
      const accessor = accessors[skin.inverseBindMatrices];
      if (!isObject(accessor) || accessor.type !== 'MAT4' || accessor.componentType !== FLOAT || accessor.count < skin.joints.length) {
        report.error('skin_matrices_invalid', `${pointer}/inverseBindMatrices`, 'needs a FLOAT MAT4 per joint');
      }
    }
    if (skin.skeleton !== undefined) reference(skin.skeleton, 'nodes', `${pointer}/skeleton`);
  });
  list('animations').forEach((animation, index) => {
    const pointer = pointerOf('animations', index);
    if (!isObject(animation) || !Array.isArray(animation.channels) || !Array.isArray(animation.samplers)) {
      report.error('animation_invalid', pointer, 'an animation needs channels and samplers');
      return;
    }
    animation.samplers.forEach((sampler, slot) => {
      const samplerPointer = `${pointer}/samplers/${slot}`;
      const interpolation = sampler.interpolation ?? 'LINEAR';
      if (!INTERPOLATIONS.has(interpolation)) report.error('animation_interpolation_invalid', samplerPointer, 'unknown interpolation');
      if (reference(sampler.input, 'accessors', `${samplerPointer}/input`)) {
        const input = accessors[sampler.input];
        if (!isObject(input) || input.type !== 'SCALAR' || input.componentType !== FLOAT
          || !numbers(input.min, 1) || !numbers(input.max, 1)) {
          report.error('animation_input_invalid', `${samplerPointer}/input`, 'input needs FLOAT SCALAR times with min and max');
        }
      }
      reference(sampler.output, 'accessors', `${samplerPointer}/output`);
    });
    animation.channels.forEach((channel, slot) => {
      const channelPointer = `${pointer}/channels/${slot}`;
      if (!isObject(channel) || !isObject(channel.target)) {
        report.error('animation_channel_invalid', channelPointer, 'a channel needs a sampler and a target');
        return;
      }
      if (!isIndex(channel.sampler) || channel.sampler >= animation.samplers.length) {
        report.error('index_out_of_range', `${channelPointer}/sampler`, 'the channel sampler does not exist');
      }
      if (channel.target.node !== undefined) reference(channel.target.node, 'nodes', `${channelPointer}/target/node`);
      if (!PATHS.has(channel.target.path)) report.error('animation_path_invalid', `${channelPointer}/target/path`, 'unknown path');
    });
  });
}

function checkExtensions(gltf, report) {
  const used = Array.isArray(gltf.extensionsUsed) ? gltf.extensionsUsed : [];
  const required = Array.isArray(gltf.extensionsRequired) ? gltf.extensionsRequired : [];
  required.forEach((name, index) => {
    if (!used.includes(name)) report.error('extension_required_not_used', `/extensionsRequired/${index}`, `${name} is not in extensionsUsed`);
    report.warning('extension_required_not_checked', `/extensionsRequired/${index}`, `${name} is required and not validated`);
  });
}
