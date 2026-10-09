# glTF 2.0 document validator with JSON pointers

Checks a glTF 2.0 document the way an importer depends on it: the asset version, every index reference, accessor component types and layouts against their buffer views and buffers, mesh attributes and their formats, the node graph as a forest, materials, samplers, images, cameras, skins and animations. When the binary data is at hand (a base64 data URI in the document, or bytes you pass, such as a GLB's BIN chunk) it also reads index values and accessor values against their declared bounds. Every problem comes back as `{code, pointer, message}`, where `pointer` is a JSON pointer (RFC 6901) to the offending value, so a tool can show exactly what to fix.

## When to use it

Use it as a gate in an asset pipeline before a model is published, in an importer that wants a clear error instead of a crash, in an editor's "check file" command, and in tests of glTF writers.

## Use it

```js
import {validateGltf} from './gltf_document_validator.mjs';

const report = validateGltf(gltfJson);                       // .gltf with embedded data URIs
const fromGlb = validateGltf(json, {buffers: [binChunk]});   // a GLB's JSON and BIN chunk
if (!report.valid) {
  for (const issue of report.errors) console.log(issue.code, issue.pointer, issue.message);
}
```

`demo/scene.mjs` validates three.js `GLTFExporter` output as JSON and as GLB, then damages copies of it.

## Exports

- `validateGltf(document, options = {})`: returns `{valid, errors, warnings, truncated, counts}`. `valid` is true when there is no error; warnings never make a document invalid; `counts` gives the length of each top-level array.
- `decodeDataUri(uri)`: the bytes of a base64 data URI as a `Uint8Array`, `null` for any other URI (an external file, a data URI that is not base64); throws `TypeError` on malformed base64.
- `GLTF_COMPONENT_TYPES`: bytes per component for 5120, 5121, 5122, 5123, 5125 and 5126.
- `GLTF_TYPE_COMPONENTS`: components per element for SCALAR to MAT4.
- `VALIDATOR_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Meaning |
|---|---|---|---|
| `buffers` | array | none | Bytes for buffers by index (`ArrayBuffer` or typed array); base64 data URIs are decoded when a slot is empty. |
| `maxIssues` | integer | 500 | Stop collecting after this many issues; `truncated` is then true. |
| `checkData` | boolean | true | Read index values and accessor bounds when the data is at hand. |

An unknown option throws `TypeError`; `maxIssues` below 1 throws `RangeError`.

## What it checks

- Asset: `asset.version` is `2.x`; `minVersion`, when present, is not above it.
- Top-level arrays are arrays and not empty; every index reference is an integer inside its array; no index is listed twice in `children` or `scene.nodes`, and scene nodes are not empty.
- Buffers have a positive `byteLength`, only buffer 0 may omit `uri`, and the data at hand is long enough.
- Buffer views fit their buffer; `byteStride` is 4 to 252 and a multiple of 4; `target` is 34962 or 34963.
- Accessors have a known component type and type, a count of at least 1, legal normalization, aligned offsets, a stride no smaller than an element, and fit their view; `min` and `max` have one number per component and, with data, hold every value (not for normalized accessors).
- Primitives have attributes of the right type and component type (POSITION, NORMAL, TANGENT, TEXCOORD, COLOR, JOINTS, WEIGHTS), POSITION has `min` and `max`, all attributes have one count, indices are unnormalized unsigned scalars below the vertex count and not the restart value, the count fits the mode, and morph targets have one value per vertex.
- Nodes: each has at most one parent, no cycle, `matrix` or translation, rotation and scale but not both, a unit rotation quaternion, and scene roots have no parent.
- Materials, textures, samplers, images, cameras, skins and animation channels and samplers reference what exists and use legal values.

## Checks

- `test_gltf_document_validator.mjs`: base64 data URIs decode to the bytes Python's `base64` module gives; a hand-built one-triangle document (its buffer packed independently with Python's `struct` and `base64`) validates with no error and no warning, as JSON with a data URI and as a GLB-style document with its bytes passed in. Known-wrong controls: twelve damaged copies (a dangling bufferView, a node cycle, matrix with TRS, POSITION without bounds, mismatched attribute counts, an index past the vertices, an accessor past its view, version 1.0, bounds that do not hold the values, a non-unit rotation, a scene root with a parent, an empty array) are each refused with their own code at the right pointer.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier validates three.js 0.186.1 `GLTFExporter` output as JSON and as GLB with its BIN chunk (no error allowed), requires three damaged copies to be refused with the expected codes, and renders tiles that show the verdicts.

## Limits

Covers the core glTF 2.0 schema rules listed above, not the whole specification: extension contents, sparse accessor values, matrix column padding for byte and short MAT2 and MAT3 accessors, animation output counts, morph target weights, skin joint hierarchies, image bytes and texture coordinate ranges are not checked, and only base64 data URIs are decoded (pass external files as `options.buffers`). Bounds are compared with a small relative tolerance, and not for normalized accessors. It is not the Khronos reference validator and does not claim its results. Only the Node 22 tests and three.js 0.186.1 `GLTFExporter` output in headless Chrome on SwiftShader WebGL 2 were run.

## Technique

- glTF 2.0 schema rules for accessors, buffer views, meshes, nodes, materials and animations
- JSON pointer (RFC 6901) issue locations
- Base64 decoding by hand (RFC 4648)
