# Height and slope terrain splat material

A three.js `ShaderMaterial` that paints a terrain mesh without a splat map. Every pixel gets four layer weights from its world height and slope (`1 - normal.y`, 0 on flat ground and 1 on a vertical face): sand below `sandLevel`, snow above `snowLevel`, grass between, and rock wherever the slope passes `rockSlope`, each change spread over a smooth band. The height boundaries are jittered by an integer-hash value noise, so beaches and snow lines wander instead of following contour lines. Each layer has a procedural colour with a fine noise variation, and rock gets horizontal strata. The weights always sum to 1 and have an exact CPU mirror, so gameplay code can ask what ground a point is on.

## When to use it

Use it for islands, mountains and valleys, procedurally generated worlds, heightfield terrain in prototypes, and strategy-game maps where the ground type should follow the shape.

## Use it

```js
import * as THREE from 'three';
import {createTerrainSplatMaterial, splatWeights, valueNoise2} from './terrain_splat_material.mjs';

const terrain = new THREE.Mesh(heightfieldGeometry, createTerrainSplatMaterial(THREE, {sandLevel: 0.2, snowLevel: 2.4}));
scene.add(terrain);

// What is under the player? Same weights as the shader (slope = 1 - normal.y, noise at x, z times noiseScale).
const [sand, grass, rock, snow] = splatWeights(player.y, 1 - groundNormal.y, {sandLevel: 0.2, snowLevel: 2.4},
  valueNoise2(player.x * 1.5, player.z * 1.5, 11));
const footstep = snow > 0.5 ? 'crunch' : sand > 0.5 ? 'sand' : 'step';
```

`demo/scene.mjs` renders an island with beaches, grass, rock faces and a snowy peak above a sea plane.

## Exports

- `createTerrainSplatMaterial(THREE, options = {})`: the material. Options are the keys of `TERRAIN_SPLAT_DEFAULTS`; an unknown key throws `TypeError`, a value out of range `RangeError`.
- `splatWeights(height, slope, settings = {}, noiseValue = 0.5)`: CPU mirror of the weights `[sand, grass, rock, snow]`. `settings` may hold `sandLevel`, `snowLevel`, `band`, `rockSlope`, `slopeBand` and `jitter`; `noiseValue` is the jitter sample in [0, 1], where 0.5 shifts nothing.
- `valueNoise2(x, z, seed = 0)`: CPU mirror of the 2D value noise in [0, 1) that the shader samples at `xz * noiseScale`.
- `TERRAIN_SPLAT_DEFAULTS`: the frozen default options.
- `TERRAIN_SPLAT_GLSL`: the GLSL hash, `valueNoise2` and `splatWeights`, to reuse in your own shaders.
- `TERRAIN_SPLAT_VERTEX`, `TERRAIN_SPLAT_FRAGMENT`: the two shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `sandLevel` | `uSandLevel` | number | 0.15 | below `snowLevel` | Height where sand gives way to grass. |
| `snowLevel` | `uSnowLevel` | number | 1.6 | | Height where snow takes over. |
| `band` | `uBand` | number | 0.12 | 0 and up | Half width of each height transition. |
| `rockSlope` | `uRockSlope` | number | 0.45 | 0 to 1 | Slope where rock takes over. |
| `slopeBand` | `uSlopeBand` | number | 0.08 | 0 to 1 | Half width of the rock transition. |
| `jitter` | `uJitter` | number | 0.25 | 0 and up | How far noise moves the height boundaries. |
| `noiseScale` | `uNoiseScale` | number | 1.5 | 0.0001 to 10000 | Noise frequency per world unit. |
| `seed` | `uSeed` | integer | 11 | 0 to 16777215 | Picks another noise field. |
| `sandColor` | `uSandColor` | colour | (0.76, 0.66, 0.46) | | Sand. |
| `grassColor` | `uGrassColor` | colour | (0.22, 0.42, 0.15) | | Grass. |
| `rockColor` | `uRockColor` | colour | (0.38, 0.35, 0.33) | | Rock. |
| `snowColor` | `uSnowColor` | colour | (0.93, 0.95, 0.98) | | Snow. |
| `detail` | `uDetail` | number | 0.18 | 0 to 1 | Brightness variation inside each layer. |
| `lightDirection` | `uLightDirection` | vector | (0.5, 0.8, 0.3) | | Direction toward the light; normalized. |
| `ambient` | `uAmbient` | number | 0.35 | 0 to 1 | Share of the colour lit without the light. |

## Checks

- `test_terrain_splat_material.mjs`: the weights at eight heights and slopes (pure layers, band centres, the rock band, a jittered snow line and overlapping bands) against values computed independently; the weights summing to 1 and staying non-negative over a sweep; the 2D value noise at three points; and the uniforms the builder sets (with a small stand-in for `THREE`). Known-wrong controls: weights not renormalized after the rock share are refused, and unknown settings, fractional seeds, crossed levels and out-of-range slopes throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL weights on the GPU for 1,024 heights, slopes and noise samples and requires them to match the CPU mirror within 0.0001 and to sum to 1 within 0.00001, then renders the island and compares it with the same terrain in one flat colour.

## Limits

Procedural colours, not textured layers: there are no albedo, normal or roughness maps per layer, so close-ups look flat. Weights depend only on height, slope and noise, not on curvature, moisture, water flow or painted masks. Heights are world y, so moving the mesh up or down moves the bands. The slope comes from vertex normals, so faceted or unsmoothed meshes paint in facets. Lit by one direction uniform; scene lights, shadows and fog are ignored. Requires WebGL 2 for unsigned integers in GLSL. Written for three.js r155 or later; only 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Height and slope layer weights with smoothstep bands
- Value-noise boundary jitter on a 32-bit integer hash
- Renormalized four-layer splat (sand, grass, rock, snow) with procedural colour variation
