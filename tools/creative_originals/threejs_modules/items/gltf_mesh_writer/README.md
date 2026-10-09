# glTF 2.0 writer for typed-array meshes

Turns meshes held as typed arrays, plus an optional node hierarchy, into a glTF 2.0 document: one buffer embedded as a base64 data URI (or a GLB with a BIN chunk), one 4-byte aligned buffer view per array, accessors with `min` and `max` on POSITION, a metallic-roughness material per mesh, nodes with translation, rotation and scale, and a scene listing the root nodes. Inputs are checked before anything is written: an index past the vertices, a node with two parents, a cycle or a rotation that is not a unit quaternion throws instead of producing a file a loader rejects.

## When to use it

Use it to export procedural geometry (generators, scatter results, CAD-like tools, simulations) from a worker, a build step or Node, where three.js's `GLTFExporter` is not loaded or a scene graph would be overhead; to save user creations from an editor; and to produce test models.

## Use it

```js
import {meshFromBufferGeometry, writeGlb, writeGltf} from './gltf_mesh_writer.mjs';

const gltf = writeGltf({
  meshes: [{positions, normals, uvs, indices, name: 'rock', material: {color: [0.5, 0.45, 0.4, 1], roughness: 0.9}}],
  nodes: [{name: 'rock', mesh: 0, translation: [0, 0, -2], rotation: [0, 0.3826834, 0, 0.9238795]}],
});
const text = JSON.stringify(gltf);                // a .gltf file

const glbBytes = writeGlb({meshes: [meshFromBufferGeometry(new THREE.TorusKnotGeometry())]});
```

`demo/scene.mjs` writes three meshes in a small hierarchy and loads the result back with three.js's `GLTFLoader`.

## Exports

- `writeGltf({meshes, nodes}, options = {})`: a glTF 2.0 document as a plain object, its buffer embedded as `data:application/octet-stream;base64,...`. Without `nodes`, each mesh gets a root node.
- `writeGlb({meshes, nodes}, options = {})`: the same scene as a GLB `Uint8Array` (JSON chunk padded with spaces, BIN chunk with zeros).
- `meshFromBufferGeometry(geometry, extra = {})`: a writer mesh copied from a three.js `BufferGeometry` (or any object with `attributes.position.array` and the same layout); `extra` adds `name` and `material`. Interleaved and normalized integer attributes are refused.
- `encodeBase64(bytes)`: RFC 4648 base64 of a `Uint8Array`, written by hand.
- `GLTF_WRITER_DEFAULTS`: the frozen default options.

## Inputs and options

| Field | Type | Meaning |
|---|---|---|
| mesh `positions` | `Float32Array` | xyz per vertex; required. |
| mesh `normals`, `uvs`, `colors` | `Float32Array` | 3, 2 and 3 or 4 values per vertex. |
| mesh `indices` | `Uint8Array`, `Uint16Array`, `Uint32Array` | Whole triangles, each index below the vertex count; without them the vertex count must be a multiple of 3. |
| mesh `material` | object | `color` [r, g, b, a] linear in [0, 1], `metallic`, `roughness`, `emissive` [r, g, b], `doubleSided`, `name`. |
| node | object | `mesh`, `translation`, `rotation` (unit quaternion x, y, z, w), `scale`, `children`, `name`. |
| option `generator` | string | `asset.generator`; default `Baltor gltf_mesh_writer 1.0`. |
| option `sceneName` | string | Name of the scene; default `Scene`. |

Unknown keys throw `TypeError`; inconsistent values throw `RangeError`.

## Checks

- `test_gltf_mesh_writer.mjs`: `encodeBase64` against Python's `base64`; a one-triangle mesh written with buffer views at 0, 36 and 72, a buffer of 80 bytes whose base64 equals the bytes packed independently with Python's `struct`, POSITION bounds [0, 0, 0] to [1, 1, 0] and UNSIGNED_SHORT indices; the GLB header, chunk lengths and BIN bytes; scene roots and transforms of a hierarchy; the `BufferGeometry` reader. Known-wrong controls: an index past the vertices, a node cycle, a second parent, a non-unit rotation, half a vertex, a misspelt key and a colour above 1 are refused.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier writes a torus knot, a vertex-coloured icosahedron and a box in a hierarchy, loads the `.gltf` and the GLB with three.js's `GLTFLoader`, requires every node's world matrix to match the written transforms within 1e-5, the vertex counts to match, the vertex colours to survive, and renders the loaded model.

## Limits

Writes triangle lists only (mode 4), one primitive per mesh, one buffer, FLOAT attributes and unsigned indices: no textures, images, samplers, skins, morph targets, animations, cameras, lights, extensions, or sparse or quantized accessors. Materials are plain metallic-roughness factors, and each mesh gets its own material even when two are equal. The data URI form is a third larger than the binary; use `writeGlb` for large meshes. Only the Node 22 tests and three.js 0.186.1 `GLTFLoader` in headless Chrome on SwiftShader WebGL 2 were run.

## Technique

- glTF 2.0 accessors, buffer views and buffers with 4-byte alignment
- RFC 4648 base64 data URIs
- GLB container with a JSON and a BIN chunk
