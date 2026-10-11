# glTF scene budget report and checker

Walks one scene of a glTF 2.0 document and counts what a renderer will be asked to draw: triangles, lines and points from each primitive's mode and element count, vertices, and draw calls as primitives times the nodes that instance their mesh. It also lists the materials, textures and images in use with an estimate of texture memory, the number of nodes and the deepest level, and the world bounds of the scene from each POSITION accessor's `min` and `max` carried through the node transforms. `checkBudget` then compares the report with your limits.

## When to use it

Use it as a gate in an asset pipeline ("no more than 50,000 triangles and 30 draw calls for a mobile prop"), in a model viewer's statistics panel, to compare exports of the same model, and to catch a model exported at the wrong scale from its extent.

## Use it

```js
import {checkBudget, sceneBudgetReport} from './gltf_scene_budget_report.mjs';

const report = sceneBudgetReport(gltfJson, {imageSizes: [{width: 1024, height: 1024}]});
console.log(report.triangles, report.drawCalls, report.textureBytes, report.extent);

const problems = checkBudget(report, {triangles: 50000, drawCalls: 30, textureBytes: 16 * 1024 * 1024});
for (const {metric, value, limit, reason} of problems) console.log(`${metric}: ${value} (${reason}, limit ${limit})`);
```

`demo/scene.mjs` exports a scene with three.js's `GLTFExporter`, reports it, loads it with `GLTFLoader` and compares the report with `renderer.info`.

## Exports

- `sceneBudgetReport(gltf, options = {})`: returns `{scene, nodes, maxDepth, meshInstances, drawCalls, triangles, lines, points, vertices, materials, defaultMaterial, textures, images, textureBytes, unknownImageSizes, bounds, extent, modes}`. `textureBytes` is `null` when an image in use has no size; `unknownImageSizes` lists those images; `bounds` is `{min, max}` or `null`; `modes` counts primitives per mode 0 to 6. Throws `RangeError` when the scene, a node or a mesh does not exist or a node is reached twice.
- `checkBudget(report, budget)`: the violations of `budget` (`{metric: limit}` over `BUDGET_METRICS`) as `{metric, value, limit, reason}`, `reason` being `over` or `unknown`.
- `primitiveCounts(mode, count)`: what one primitive draws: POINTS `count` points, LINES `count / 2`, LINE_LOOP `count`, LINE_STRIP `count - 1` lines, TRIANGLES `count / 3`, strips and fans `count - 2` triangles.
- `BUDGET_METRICS`: `triangles`, `lines`, `points`, `vertices`, `drawCalls`, `materials`, `textures`, `textureBytes`, `nodes`, `maxDepth`, `extent`.
- `REPORT_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Meaning |
|---|---|---|---|
| `scene` | integer or null | null | Scene to walk; null uses `gltf.scene` or 0. |
| `imageSizes` | array or null | null | `{width, height}` by image index for the texture memory estimate. |
| `mipmaps` | boolean | true | Add a third to each image for its mip chain. |

## Checks

- `test_gltf_scene_budget_report.mjs`: the counts of all seven primitive modes; a triangle translated by (0, 1, 0) with bounds (0, 1, 0) to (1, 2, 0); two instances of one mesh under a quarter turn about +Y with bounds (0, 0, -3) to (0, 1, 0), worked out by hand; a matrix node four levels deep; texture memory 349,525 bytes with mip chains and 262,144 without for one 256 x 256 image; budget violations. Known-wrong controls: a mode table that counts strips and fans as lists is refused, a node cycle and bad options throw, and a budget below the count is reported.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier exports a torus knot, four instances of one sphere, line segments and points with three.js's `GLTFExporter`, requires the report to agree with three.js's `renderer.info` (triangles, lines, points, draw calls) after `GLTFLoader` loads and draws the scene, checks that the four spheres share one mesh, and renders budget bars beside the model.

## Limits

Counts follow the glTF primitive modes, not a renderer: a renderer that splits, merges, instances or culls objects draws something else. Texture memory is an estimate (4 bytes a texel, plus a third for mip chains), not GPU memory: compression, formats and padding are ignored, and it is unknown without image sizes. Bounds come from POSITION `min` and `max`, so morph targets, skins and animations are not included. Only one scene is walked, and extensions such as `EXT_mesh_gpu_instancing` are not counted. Only the Node 22 tests and three.js 0.186.1 in headless Chrome on SwiftShader WebGL 2 were run.

## Technique

- glTF 2.0 primitive modes and element counts
- Node world matrices from translation, rotation and scale or a matrix, column-major
- Axis-aligned bounds of transformed accessor boxes
