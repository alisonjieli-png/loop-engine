// Known answers for the glTF mesh writer: base64 strings and the 80-byte buffer of a one-triangle mesh computed
// independently with Python's base64 and struct modules, the buffer view layout, accessor bounds, the GLB container
// fields, the scene roots of a node hierarchy and the BufferGeometry reader. Known-wrong inputs (an index past the
// vertices, a node cycle, a second parent, a non-unit rotation, half a vertex, a misspelt key) must be refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {GLTF_WRITER_DEFAULTS, encodeBase64, meshFromBufferGeometry, writeGlb, writeGltf} from './gltf_mesh_writer.mjs';

// base64.b64encode(struct.pack('<9f', 0,0,0, 1,0,0, 0,1,0) + struct.pack('<9f', 0,0,1, 0,0,1, 0,0,1)
//                  + struct.pack('<3H', 0,1,2) + b'\0\0')
const TRIANGLE_BASE64 = 'AAAAAAAAAAAAAAAAAACAPwAAAAAAAAAAAAAAAAAAgD8AAAAAAAAAAAAAAAAAAIA/AAAAAAAAAAAAAIA/AAAAAAAAAAAAAIA/AAABAAIAAAA=';

function triangle(extra = {}) {
  return {
    positions: new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]),
    normals: new Float32Array([0, 0, 1, 0, 0, 1, 0, 0, 1]),
    indices: new Uint16Array([0, 1, 2]),
    ...extra,
  };
}

test('encodeBase64 matches Python base64', () => {
  assert.equal(encodeBase64(new Uint8Array([0, 1, 2, 253, 254, 255])), 'AAEC/f7/');
  assert.equal(encodeBase64(new Uint8Array([1, 2])), 'AQI=');
  assert.equal(encodeBase64(new Uint8Array([65])), 'QQ==');
  assert.equal(encodeBase64(new Uint8Array([])), '');
  assert.throws(() => encodeBase64([1, 2, 3]), TypeError);
});

test('writeGltf lays out the triangle exactly', () => {
  const gltf = writeGltf({meshes: [triangle()]});
  assert.equal(gltf.asset.version, '2.0');
  assert.equal(gltf.asset.generator, GLTF_WRITER_DEFAULTS.generator);
  assert.deepEqual(gltf.bufferViews.map((view) => [view.byteOffset, view.byteLength, view.target]),
    [[0, 36, 34962], [36, 36, 34962], [72, 6, 34963]]);
  assert.equal(gltf.buffers[0].byteLength, 80);
  assert.equal(gltf.buffers[0].uri, `data:application/octet-stream;base64,${TRIANGLE_BASE64}`);
  const position = gltf.accessors[gltf.meshes[0].primitives[0].attributes.POSITION];
  assert.deepEqual([position.min, position.max, position.count, position.type], [[0, 0, 0], [1, 1, 0], 3, 'VEC3']);
  const indices = gltf.accessors[gltf.meshes[0].primitives[0].indices];
  assert.deepEqual([indices.componentType, indices.count, indices.type], [5123, 3, 'SCALAR']);
  assert.deepEqual(gltf.scenes, [{name: 'Scene', nodes: [0]}]);
  assert.deepEqual(gltf.materials[0].pbrMetallicRoughness, {baseColorFactor: [0.8, 0.8, 0.8, 1], metallicFactor: 0,
    roughnessFactor: 0.6});
});

test('writeGlb packs the same scene into a container', () => {
  const glb = writeGlb({meshes: [triangle()]}, {generator: 'test'});
  const view = new DataView(glb.buffer);
  assert.deepEqual([view.getUint32(0, true), view.getUint32(4, true), view.getUint32(8, true)], [0x46546c67, 2, glb.length]);
  const jsonLength = view.getUint32(12, true);
  assert.equal(jsonLength % 4, 0);
  const json = JSON.parse(new TextDecoder().decode(glb.subarray(20, 20 + jsonLength)));
  assert.equal(json.buffers[0].uri, undefined);
  assert.equal(json.asset.generator, 'test');
  assert.deepEqual([view.getUint32(20 + jsonLength, true), view.getUint32(24 + jsonLength, true)], [80, 0x004e4942]);
  const binary = glb.subarray(28 + jsonLength);
  assert.equal(encodeBase64(Uint8Array.from(binary)), TRIANGLE_BASE64);
});

test('a node hierarchy keeps its transforms and only roots go in the scene', () => {
  const gltf = writeGltf({
    meshes: [triangle(), triangle({indices: new Uint32Array([2, 1, 0]), uvs: new Float32Array(6)})],
    nodes: [{name: 'base', translation: [0, 1, 0], children: [1, 2]}, {mesh: 0, rotation: [0, 0.7071067811865476, 0, 0.7071067811865476]},
      {mesh: 1, scale: [2, 2, 2]}, {mesh: 1, translation: [3, 0, 0]}],
  });
  assert.deepEqual(gltf.scenes[0].nodes, [0, 3]);
  assert.deepEqual(gltf.nodes[0], {name: 'base', translation: [0, 1, 0], children: [1, 2]});
  assert.deepEqual(gltf.nodes[2], {mesh: 1, scale: [2, 2, 2]});
  assert.equal(gltf.accessors[gltf.meshes[1].primitives[0].indices].componentType, 5125);
  assert.ok('TEXCOORD_0' in gltf.meshes[1].primitives[0].attributes);
  gltf.bufferViews.forEach((view) => assert.equal(view.byteOffset % 4, 0, 'every view is 4-byte aligned'));
});

test('known wrong: inconsistent inputs are refused', () => {
  assert.throws(() => writeGltf({meshes: [triangle({indices: new Uint16Array([0, 1, 3])})]}), RangeError);
  assert.throws(() => writeGltf({meshes: [triangle()], nodes: [{mesh: 0, children: [1]}, {children: [0]}]}), RangeError);
  assert.throws(() => writeGltf({meshes: [triangle()], nodes: [{children: [2]}, {children: [2]}, {mesh: 0}]}), RangeError);
  assert.throws(() => writeGltf({meshes: [triangle()], nodes: [{mesh: 0, rotation: [0, 0, 0, 2]}]}), RangeError);
  assert.throws(() => writeGltf({meshes: [{positions: new Float32Array([0, 0])}]}), RangeError);
  assert.throws(() => writeGltf({meshes: [triangle({normal: new Float32Array(9)})]}), TypeError);
  assert.throws(() => writeGltf({meshes: [triangle()]}, {generatr: 'x'}), TypeError);
  assert.throws(() => writeGltf({meshes: [triangle()]}, {toString: 'x'}), TypeError, 'an inherited name is not an option');
  assert.throws(() => writeGltf({meshes: [triangle({constructor: 1})]}), TypeError);
  assert.throws(() => writeGltf({meshes: [triangle({material: {color: [2, 0, 0, 1]}})]}), RangeError);
});

test('meshFromBufferGeometry copies attributes and refuses interleaved data', () => {
  const geometry = {
    attributes: {
      position: {array: new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]), itemSize: 3},
      uv: {array: new Float32Array([0, 0, 1, 0, 0, 1]), itemSize: 2},
    },
    index: {array: new Uint16Array([0, 1, 2])},
  };
  const mesh = meshFromBufferGeometry(geometry, {name: 'tri'});
  assert.deepEqual(Array.from(mesh.uvs), [0, 0, 1, 0, 0, 1]);
  assert.ok(mesh.indices instanceof Uint16Array);
  assert.equal(mesh.name, 'tri');
  assert.notEqual(mesh.positions, geometry.attributes.position.array, 'arrays are copied');
  const interleaved = {attributes: {position: {isInterleavedBufferAttribute: true, itemSize: 3}}};
  assert.throws(() => meshFromBufferGeometry(interleaved), TypeError);
  assert.throws(() => meshFromBufferGeometry({attributes: {}}), TypeError);
});
