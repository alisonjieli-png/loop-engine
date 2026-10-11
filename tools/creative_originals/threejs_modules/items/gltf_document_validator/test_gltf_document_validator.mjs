// Known answers for the glTF validator: a hand-built one-triangle document (its 80-byte buffer encoded independently
// with Python's base64 and struct modules) validates with no error; base64 data URIs decode to the bytes Python
// gives; and each known-wrong copy of the document (a dangling index, a node cycle, matrix with TRS, missing POSITION
// bounds, mismatched counts, an index past the vertices, an accessor past its view, a wrong version, bounds that do
// not hold the values) is refused with its own code at the right JSON pointer.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  GLTF_COMPONENT_TYPES, GLTF_TYPE_COMPONENTS, VALIDATOR_DEFAULTS, decodeDataUri, validateGltf,
} from './gltf_document_validator.mjs';

// struct.pack('<9f', 0,0,0, 1,0,0, 0,1,0) + struct.pack('<9f', 0,0,1, 0,0,1, 0,0,1) + struct.pack('<3H', 0,1,2) + 2 zeros
const TRIANGLE_BASE64 = 'AAAAAAAAAAAAAAAAAACAPwAAAAAAAAAAAAAAAAAAgD8AAAAAAAAAAAAAAAAAAIA/AAAAAAAAAAAAAIA/AAAAAAAAAAAAAIA/AAABAAIAAAA=';

function triangle() {
  return {
    asset: {version: '2.0', generator: 'hand written'},
    scene: 0,
    scenes: [{nodes: [0]}],
    nodes: [{mesh: 0, translation: [0, 1, 0], children: [1]}, {rotation: [0, 0, 0, 1]}],
    meshes: [{primitives: [{attributes: {POSITION: 0, NORMAL: 1}, indices: 2, material: 0}]}],
    materials: [{pbrMetallicRoughness: {baseColorFactor: [1, 0.5, 0.2, 1], metallicFactor: 0, roughnessFactor: 0.6}}],
    accessors: [
      {bufferView: 0, componentType: 5126, count: 3, type: 'VEC3', min: [0, 0, 0], max: [1, 1, 0]},
      {bufferView: 1, componentType: 5126, count: 3, type: 'VEC3'},
      {bufferView: 2, componentType: 5123, count: 3, type: 'SCALAR'},
    ],
    bufferViews: [
      {buffer: 0, byteOffset: 0, byteLength: 36, target: 34962},
      {buffer: 0, byteOffset: 36, byteLength: 36, target: 34962},
      {buffer: 0, byteOffset: 72, byteLength: 6, target: 34963},
    ],
    buffers: [{byteLength: 80, uri: `data:application/octet-stream;base64,${TRIANGLE_BASE64}`}],
  };
}

function codes(result) {
  return result.errors.map((issue) => `${issue.code} ${issue.pointer}`);
}

test('decodeDataUri decodes base64 data URIs as Python does', () => {
  assert.deepEqual(Array.from(decodeDataUri('data:application/octet-stream;base64,AAEC/f7/')), [0, 1, 2, 253, 254, 255]);
  assert.deepEqual(Array.from(decodeDataUri('data:;base64,QQ==')), [65]);
  assert.equal(decodeDataUri(`data:application/octet-stream;base64,${TRIANGLE_BASE64}`).length, 80);
  assert.equal(decodeDataUri('data:text/plain,hello'), null, 'a data URI that is not base64 is not read');
  assert.equal(decodeDataUri('model.bin'), null);
  assert.throws(() => decodeDataUri('data:;base64,QQ=A'), TypeError);
  assert.throws(() => decodeDataUri('data:;base64,QQ'), TypeError);
});

test('the hand-built triangle validates with no error', () => {
  const result = validateGltf(triangle());
  assert.deepEqual(codes(result), []);
  assert.equal(result.valid, true);
  assert.deepEqual(result.warnings, []);
  assert.equal(result.counts.accessors, 3);
  assert.equal(GLTF_COMPONENT_TYPES[5123], 2);
  assert.equal(GLTF_TYPE_COMPONENTS.MAT4, 16);
});

test('a GLB-style document reads its binary from options.buffers', () => {
  const document = triangle();
  delete document.buffers[0].uri;
  const bytes = decodeDataUri(triangle().buffers[0].uri);
  assert.deepEqual(codes(validateGltf(document, {buffers: [bytes]})), []);
  const withoutData = validateGltf(document);
  assert.equal(withoutData.valid, true);
  assert.deepEqual(withoutData.warnings.map((issue) => issue.code), ['buffer_data_unavailable']);
  assert.deepEqual(codes(validateGltf(document, {buffers: [bytes.subarray(0, 40)]})), ['buffer_data_too_short /buffers/0']);
});

test('known wrong: each damaged copy is refused with its code and pointer', () => {
  const cases = [
    ['index_out_of_range /accessors/0/bufferView', (doc) => { doc.accessors[0].bufferView = 7; }],
    ['node_cycle /nodes/0', (doc) => { doc.nodes[1].children = [0]; }],
    ['node_matrix_and_trs /nodes/0', (doc) => { doc.nodes[0].matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]; }],
    ['position_bounds_missing /accessors/0', (doc) => { delete doc.accessors[0].min; }],
    ['attribute_count_mismatch /meshes/0/primitives/0/attributes', (doc) => { doc.accessors[1].count = 2; }],
    ['index_value_out_of_range /meshes/0/primitives/0/indices', (doc) => {
      // Python: the same buffer with indices (0, 3, 2); only the last 16 base64 characters change.
      doc.buffers[0].uri = `data:application/octet-stream;base64,${TRIANGLE_BASE64.slice(0, -16)}AIA/AAADAAIAAAA=`;
    }],
    ['accessor_out_of_bounds /accessors/2', (doc) => { doc.accessors[2].count = 6; }],
    ['asset_version_unsupported /asset/version', (doc) => { doc.asset.version = '1.0'; }],
    ['accessor_value_outside_bounds /accessors/0', (doc) => { doc.accessors[0].max = [1, 0.5, 0]; }],
    ['node_rotation_not_unit /nodes/1/rotation', (doc) => { doc.nodes[1].rotation = [0, 0, 0, 2]; }],
    ['scene_node_not_root /scenes/0/nodes/0', (doc) => { doc.scenes[0].nodes = [1]; doc.nodes.push({children: [1]}); }],
    ['empty_array /materials', (doc) => { doc.materials = []; delete doc.meshes[0].primitives[0].material; }],
    ['accessor_component_type_invalid /accessors/1/componentType', (doc) => { doc.accessors[1].componentType = 'toString'; }],
    ['accessor_type_invalid /accessors/1/type', (doc) => { doc.accessors[1].type = 'constructor'; }],
  ];
  for (const [expected, damage] of cases) {
    const document = triangle();
    damage(document);
    const result = validateGltf(document);
    assert.equal(result.valid, false, expected);
    assert.ok(codes(result).includes(expected), `${expected} in ${JSON.stringify(codes(result))}`);
  }
  assert.equal(validateGltf(null).errors[0].code, 'document_not_object');
});

test('options are strict and the issue list is bounded', () => {
  assert.throws(() => validateGltf(triangle(), {maxIssue: 3}), TypeError);
  assert.throws(() => validateGltf(triangle(), {maxIssues: 0}), RangeError);
  assert.throws(() => validateGltf(triangle(), {toString: 1}), TypeError, 'an inherited name is not an option');
  const many = triangle();
  many.accessors.forEach((accessor) => { accessor.bufferView = 99; });
  const result = validateGltf(many, {maxIssues: 2});
  assert.equal(result.errors.length, 2);
  assert.equal(result.truncated, true);
  assert.equal(VALIDATOR_DEFAULTS.maxIssues, 500);
});
