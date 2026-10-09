# Strict GLB container reader and writer

Reads and writes the binary glTF 2.0 container: a 12-byte header (`glTF`, version 2, total length), a JSON chunk and an optional BIN chunk, every chunk a multiple of 4 bytes. Reading checks every rule of the layout and refuses a bad file with a `GlbError` whose `code` names the rule, so a pipeline can report "BIN chunk shorter than buffers[0]" instead of a loader failing somewhere later. Writing pads the JSON with spaces and the binary with zeros, as the specification requires. It works on `ArrayBuffer`s and typed arrays in a page, a worker or Node, without three.js.

## When to use it

Use it to inspect or repack `.glb` files in an asset pipeline, to split a GLB into its JSON and binary for editing and join them again, to sniff whether downloaded bytes are a GLB before choosing a loader, and to give clear errors for truncated or hand-edited files.

## Use it

```js
import {encodeGlb, isGlb, parseGlb, GlbError} from './glb_container_codec.mjs';

const bytes = new Uint8Array(arrayBufferFromSomewhere);
if (isGlb(bytes)) {
  try {
    const {json, binary, chunks} = parseGlb(bytes);
    json.asset.generator = 'my pipeline';
    const repacked = encodeGlb(json, binary.subarray(0, json.buffers[0].byteLength));
    // repacked.buffer is a complete .glb, ready for GLTFLoader.parse or a download
  } catch (error) {
    if (error instanceof GlbError) console.log(error.code, error.message);
  }
}
```

`demo/scene.mjs` exports a scene with three.js's `GLTFExporter`, reads the GLB with `parseGlb`, repacks it with `encodeGlb` and loads the result with `GLTFLoader`.

## Exports

- `parseGlb(data)`: reads a GLB from an `ArrayBuffer` or typed array and returns `{json, binary, version, byteLength, chunks}`. `binary` is a `Uint8Array` view of the BIN chunk (it may hold up to 3 padding bytes beyond `buffers[0].byteLength`) or `null`; `chunks` lists every chunk's `{type, name, byteOffset, byteLength}`.
- `encodeGlb(json, binary = null)`: writes a GLB as a `Uint8Array` that owns its `ArrayBuffer`. With `binary`, `buffers[0]` must have no `uri` and a `byteLength` equal to its length.
- `isGlb(data)`: true when the bytes start with a glTF 2.0 binary header; never throws.
- `GlbError`: the refusal error, with `code` and a message.
- `GLB_FORMAT`: the frozen container constants (magic, version, chunk types, header sizes, alignment).

## Refusal codes

| Code | Rule |
|---|---|
| `too_short` | Fewer than 20 bytes. |
| `magic` | The first four bytes are not `glTF`. |
| `version` | The container version is not 2. |
| `length_mismatch` | The header's total length differs from the data length. |
| `length_unaligned` | The total length is not a multiple of 4. |
| `chunk_truncated` | A chunk header or chunk runs past the end. |
| `chunk_unaligned` | A chunk length is not a multiple of 4. |
| `first_chunk_not_json` | The first chunk is not JSON. |
| `json_not_utf8`, `json_bom`, `json_invalid`, `json_not_object` | The JSON chunk is not UTF-8, starts with a byte order mark, does not parse, or is not an object. |
| `second_json_chunk` | A second JSON chunk. |
| `bin_chunk_not_second` | A BIN chunk that is not chunk 1. |
| `bin_without_buffer` | A BIN chunk but no `buffers[0]` without a `uri`. |
| `bin_length_mismatch` | The BIN chunk is shorter than `buffers[0].byteLength` or more than 3 bytes longer. |
| `buffer_without_bin` | `buffers[0]` has no `uri` but there is no BIN chunk (reading and writing). |
| `buffer_binding` | `encodeGlb` got binary data that does not match `buffers[0]`. |

## Checks

- `test_glb_container_codec.mjs`: the exact bytes of two containers (48 and 92 bytes), computed independently with Python's `struct` module from the binary layout; reading them back, including from a view with a byte offset and with an unknown extra chunk. Known-wrong controls: one hand-built bad container for each of 17 refusal codes, each refused with its own code while the unchanged container is accepted, and `encodeGlb` refusing a mismatched binding.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier exports a scene with three.js's `GLTFExporter` as GLB, requires `parseGlb` to read it, repacks it with `encodeGlb`, requires `GLTFLoader` to load the same number of meshes and vertices, requires a damaged magic and a shortened copy to be refused, and renders the loaded model against the empty stage.

## Limits

A container codec only: it checks the header, the chunk layout and the binding of `buffers[0]` to the BIN chunk, not the glTF document inside (accessors, meshes and references are a document validator's job). The returned `binary` is a view into the input, so changing the input changes it. Chunks of unknown types after the first two are listed and skipped, as the specification asks; their contents are not read. Writing keeps the JSON as `JSON.stringify` gives it. Only the Node 22 tests and three.js 0.186.1 `GLTFExporter` and `GLTFLoader` in headless Chrome on SwiftShader WebGL 2 were run.

## Technique

- glTF 2.0 binary container: 12-byte header, 8-byte chunk headers, 4-byte alignment
- UTF-8 JSON chunk padded with spaces, BIN chunk padded with zeros
