# GPU id picking with a one-pixel render

Picking by colour: every pickable mesh (or every instance of an `InstancedMesh`) is drawn with a material that writes its 24-bit id as red, green and blue bytes, and the id under the pointer is read back from the frame. Rendering the whole frame for one pixel is wasteful, so the picker narrows the camera to that pixel with `camera.setViewOffset` and renders into a 1 x 1 render target: the same scene and depth test, one pixel of shading. The answer respects occlusion exactly as the screen does, costs the same whether the scene has ten triangles or ten million, and handles instances that a CPU raycast would test one by one. Afterwards every material, the background, the override material, the camera view and the renderer state are put back.

## When to use it

Use it for clicking and hovering in scenes with many objects or instances, selection in editors and configurators, and anywhere a CPU raycast is too slow or does not match what is drawn (displaced or GPU-instanced geometry with the same vertex transform).

## Use it

```js
import * as THREE from 'three';
import {createPicker, setInstancePickIds} from './gpu_id_picking.mjs';

chair.userData.pickId = 1;                                  // any integer from 1 to 16,777,215
table.userData.pickId = 2;
setInstancePickIds(THREE, crowd, Array.from({length: crowd.count}, (_, i) => 1000 + i));   // one id per instance

const picker = createPicker(THREE, renderer);
renderer.domElement.addEventListener('pointerdown', (event) => {
  const rect = renderer.domElement.getBoundingClientRect();
  const id = picker.pick(scene, camera, event.clientX - rect.left, event.clientY - rect.top);
  if (id !== 0) select(id);
});
```

`demo/scene.mjs` picks six meshes, a ring of twelve instances, an unnamed panel and the background.

## Exports

- `createPicker(THREE, renderer)`: `{pick(scene, camera, x, y), dispose()}`. `x` and `y` are pixels from the top left in `renderer.getSize()` units. A mesh reports `userData.pickId`, an instanced mesh with a `pickId` attribute reports each instance's id, background and meshes without an id report 0 (they still hide what is behind them). Points, lines and sprites are hidden while picking.
- `createPickingMaterial(THREE, options = {})`: the picking `ShaderMaterial`; `uniforms.uPickId.value` holds the id, or with `instanced: true` each instance's id comes from the `pickId` attribute.
- `setInstancePickIds(THREE, instancedMesh, ids)`: adds the `pickId` `InstancedBufferAttribute` to the mesh's (shared) geometry.
- `encodeId(id)`: `[red, green, blue]`, red the lowest byte.
- `decodeId(red, green, blue)`: the id.
- `PICK_ID_LIMIT`: 16,777,215.
- `PICKING_DEFAULTS`: the frozen material options.
- `PICKING_VERTEX`, `PICKING_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Meaning |
|---|---|---|---|---|
| `id` | `uPickId` | integer | 0 | Id written by a non-instanced picking material (0 to 16,777,215). |
| `instanced` | define `BALTOR_PICK_INSTANCED` | boolean | false | Read each instance's id from the `pickId` attribute. |

An unknown option throws `TypeError`; an id outside 0 to 16,777,215, a byte outside 0 to 255 or a wrong number of instance ids throws `RangeError`.

## Checks

- `test_gpu_id_picking.mjs`: ids round-trip through three bytes at every byte boundary up to 16,777,215; the fragment shader's float32 arithmetic (floor, mod, divide by 255, store as 8 bits) gives the same bytes; the material's uniform, define and blending; instance ids; and the picker on a stand-in renderer that draws the frontmost mesh with the material it is given: the right ids, 0 for an occluder without an id and for background, the instance attribute, points hidden during the pick, and every material, the background, the camera view and the clear colour restored. Known-wrong controls: a decoder with the bytes in the wrong order fails the round trip, and out-of-range ids and options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declaration.
- The verifier renders the demo and, in the browser, picks 20 pixels with the real renderer, requires the expected ids, compares each with the first mesh three.js `Raycaster` finds through the same pixel centre, and checks that the state is restored.

## Limits

Picking materials draw rest-pose geometry, so skinned and morphed meshes are picked where their undeformed shape is. Transparent objects are picked as if opaque, alpha-tested cut-outs as full quads, and points, lines and sprites are not pickable (they are hidden while picking). Each pick renders the scene once for one pixel: cheap in fill rate but a full pass of draw calls, so pick on pointer events rather than for many points every frame. Ids above 16,777,215 do not fit. A multi-material mesh is picked with its first material's side. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Colour-coded id buffer picking
- Projection window offset (`camera.setViewOffset`) to render a single pixel
- Flat varyings for exact integer ids
- Integer to bytes with floor and mod in float32
