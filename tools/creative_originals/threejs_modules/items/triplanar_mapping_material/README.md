# Triplanar texture mapping material

A three.js `ShaderMaterial` that textures a mesh without using its UVs. The texture is projected three times, along the X, Y and Z axes, in world or object space, and the three samples are blended by weights `|n|^k / sum`, where `n` is the surface normal and `k` the sharpness. A surface facing up shows the top projection, a wall facing sideways the side projection, and slopes a smooth mix. Each projection is flipped on the negative side so no face shows a mirror image. Without a texture it uses a built-in two-colour checker, handy for blocking out levels.

## When to use it

Use it for terrain, rocks, cliffs and caves, scaled boxes in level blockouts, marching-cubes and other generated meshes, and any mesh whose UVs stretch or are missing.

## Use it

```js
import * as THREE from 'three';
import {createTriplanarMaterial} from './triplanar_mapping_material.mjs';

const rockTexture = new THREE.TextureLoader().load('rock.jpg');
rockTexture.wrapS = rockTexture.wrapT = THREE.RepeatWrapping;
rockTexture.colorSpace = THREE.SRGBColorSpace;

const cliff = new THREE.Mesh(cliffGeometry, createTriplanarMaterial(THREE, {map: rockTexture, scale: 0.5, sharpness: 6}));

// Level blockout: the checker stays one unit per cell however the boxes are scaled.
const block = new THREE.Mesh(new THREE.BoxGeometry(), createTriplanarMaterial(THREE, {scale: 1}));
block.scale.set(8, 2, 3);
```

`demo/scene.mjs` renders a stretched box and a tall cylinder with a brick texture and a lumpy rock with the checker; the verifier compares it with the same textures through the meshes' own UVs.

## Exports

- `createTriplanarMaterial(THREE, options = {})`: the material. Options are the keys of `TRIPLANAR_DEFAULTS`; an unknown key throws `TypeError`, a value out of range `RangeError`.
- `triplanarWeights(normal, sharpness)`: CPU mirror of the blend weights, `[x, y, z]` summing to 1. Pass a unit normal.
- `triplanarCoordinates(position, normal, scale)`: CPU mirror of the three planar coordinates seen along X, Y and Z.
- `triplanarChecker(u, v)`: CPU mirror of the checker, 0 or 1 by the parity of `floor(u) + floor(v)`.
- `TRIPLANAR_DEFAULTS`: the frozen default options.
- `TRIPLANAR_GLSL`: the GLSL `triplanarWeights`, `triplanarCoordinates` and `triplanarChecker`, to reuse in your own shaders.
- `TRIPLANAR_VERTEX`, `TRIPLANAR_FRAGMENT`: the two shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `map` | `uMap`, `uHasMap` | texture or null | null | | Texture to project (use `RepeatWrapping`); null uses the checker. |
| `scale` | `uScale` | number | 1 | above 0 to 1000 | Texture repeats per scene unit. |
| `sharpness` | `uSharpness` | number | 4 | 1 to 32 | Higher narrows the blend between projections. |
| `space` | `uObjectSpace` | string | `world` | `world`, `object` | Fixed in the scene, or moving and scaling with the mesh. |
| `checkerColors` | `uCheckerA`, `uCheckerB` | two colours | light, dark | | Checker colours when there is no map. |
| `tint` | `uTint` | colour | (1, 1, 1) | | Multiplies the projected colour. |
| `lightDirection` | `uLightDirection` | vector | (0.45, 0.8, 0.4) | | Direction toward the light; normalized. |
| `ambient` | `uAmbient` | number | 0.35 | 0 to 1 | Share of the colour lit without the light. |

## Checks

- `test_triplanar_mapping_material.mjs`: the weights for axis, diagonal and tilted normals against values computed independently, the planar coordinates on positive and negative faces, the checker across zero, and the uniforms the builder sets for a texture and for the checker (with a small stand-in for `THREE`). Known-wrong controls: weights that are not normalized are refused, and a misspelt option, a non-texture map, an unknown space, a low sharpness and a one-colour checker throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL weights and checker on the GPU for 256 normals and requires the weights to match the CPU mirror within 0.0001 and the checker exactly, then renders the demo and compares it with the UV-mapped baseline.

## Limits

Three texture reads per pixel instead of one. Blend zones mix two or three projections, which smears textures with strong directional features such as planks or lettering. Projections are axis aligned: a face at 45 degrees gets an even mix, not a texture aligned to the face. There is no normal or tangent mapping. The checker is not filtered, so it shimmers in the distance. In object space the texture follows each instance's local coordinates. Lit by one direction uniform; three.js scene lights, shadows and fog are ignored. Written for three.js r155 or later; only 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Triplanar projection blended by `|n|^k` weights
- A sign flip per projection so no face is mirrored
- Parity checker, `floor(u) + floor(v)` modulo 2
