# Normal map from a height field

Turns a height field (a `Float32Array`, row 0 at v = 0 as in a `DataTexture`) into tangent-space normals and an RGBA8 normal map. Each texel's slopes along u and v come from central differences in height units per texel; the normal is `normalize(-strength * dh/du, -strength * dh/dv, 1)`, and each component is stored as `round((c / 2 + 0.5) * 255)`. Edges either wrap, for tiling textures, or clamp, for a single decal, and the green channel follows the OpenGL convention (green up, what three.js and glTF use) or the DirectX one (green down).

## When to use it

Use it to give procedural surfaces relief (studs, ripples, scratches, terrain detail, tiles), to turn a heightmap from a tool into a normal map at load time, and to convert between the OpenGL and DirectX conventions by regenerating from height.

## Use it

```js
import * as THREE from 'three';
import {createNormalMapTexture, normalMapFromHeight} from './normal_map_from_height.mjs';

const size = 256;
const heights = new Float32Array(size * size);  // fill with your height field, in texel units
const rgba = normalMapFromHeight(heights, size, size, {strength: 1.5, edges: 'wrap'});
const normalMap = createNormalMapTexture(THREE, rgba, size, size);
const material = new THREE.MeshStandardMaterial({color: 0xb9c3d1, metalness: 0.5, roughness: 0.4, normalMap});
```

`demo/scene.mjs` lights a studded plate at a grazing angle with and without the map.

## Exports

- `normalsFromHeight(heights, width, height, options = {})`: unit normals as a `Float32Array` (xyz per texel; x along u, y along v, z out of the surface).
- `normalMapFromHeight(heights, width, height, options = {})`: the RGBA8 normal map as a `Uint8Array`, alpha 255.
- `encodeNormal(x, y, z, convention = 'opengl')`: the four bytes of one unit normal.
- `createNormalMapTexture(THREE, rgba, width, height, options = {})`: a `THREE.DataTexture` holding linear data (`NoColorSpace`), repeat wrapping (or clamp with `{edges: 'clamp'}`), linear filtering and mipmaps.
- `NORMAL_MAP_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Values | Meaning |
|---|---|---|---|---|
| `strength` | number | 1 | 0 to 1000 | Multiplies the slopes before normalizing; 0 gives a flat map. |
| `edges` | string | `wrap` | `wrap`, `clamp` | How differences read past the border. |
| `convention` | string | `opengl` | `opengl`, `directx` | Green up or green down. |

Unknown options throw `TypeError`; values out of range throw `RangeError`.

## Checks

- `test_normal_map_from_height.mjs`, against bytes computed independently with Python from the same formula: a flat field is (128, 128, 255) everywhere; a ramp along the columns gives (37, 128, 218), along the rows (128, 37, 218) or green 218 in the DirectX convention; strength 2 gives (13, 128, 185); the first column of a ramp gives (70, 128, 242) when clamped and (248, 128, 168) when wrapped; normals are unit length and face out. Known-wrong controls: a generator with rows and columns swapped, and one with the wrong green sign, are refused.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier samples a 16 x 16 map at texel centres on the GPU: every decoded component must equal the CPU bytes within 1e-5 and the unquantized normals within 0.01. Then it renders the studded plate and compares it with the plate without the map.

## Limits

Central differences over one texel: detail smaller than two texels is lost and steep steps alias; there is no Sobel or multi-scale filter, and no height-to-world scale other than `strength`. Normals are stored in 8 bits, so each component is within about 0.004 of the exact value. The tangent frame is the texture's own (u right, v up); a mesh with mirrored or rotated UVs needs matching tangents. `createNormalMapTexture` builds an RGBA texture, not a two-channel or compressed one. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Central-difference height gradient
- Tangent-space normal `normalize(-s dh/du, -s dh/dv, 1)`
- OpenGL and DirectX green-channel conventions
