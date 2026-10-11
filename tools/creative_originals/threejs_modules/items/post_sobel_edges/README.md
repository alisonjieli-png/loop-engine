# Sobel edge outline pass

A post-processing pass that finds edges from the luminance gradient and draws them as lines. For each pixel it reads the 3 x 3 neighbourhood, takes Rec. 709 luminance, applies the two Sobel kernels (derivative across, smoothing along, centre weight 2) and turns the gradient magnitude into a mask with a smoothstep around `threshold`. In `overlay` mode the outline colour is drawn over the image, for an ink or comic look; in `edges` mode the edges are drawn alone over a background colour, for blueprint, sketch and line-art frames. The gradient and the mask have an exact CPU mirror on luminance arrays.

## When to use it

Use it for comic and cel styles over a lit scene, technical line-art views, sketch and blueprint modes, edge highlights in a scanner or detective vision, or as a cheap outline when a model has no outline mesh. For outlines that follow geometry exactly, use depth and normal edges instead.

## Use it

With three.js's post-processing addons:

```js
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {createSobelEdgesShader} from './post_sobel_edges.mjs';

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const ink = new ShaderPass(createSobelEdgesShader({threshold: 0.12, softness: 0.06,
  resolution: [innerWidth * devicePixelRatio, innerHeight * devicePixelRatio]}));
composer.addPass(ink);
addEventListener('resize', () => {
  ink.uniforms.uTexelSize.value = [1 / (innerWidth * devicePixelRatio), 1 / (innerHeight * devicePixelRatio)];
});
```

For line art alone: `createSobelEdgesShader({mode: 'edges', outlineColor: [0.1, 0.2, 0.6], backgroundColor: [0.95, 0.95, 1]})`. Without addons, draw a render target through `createSobelEdgesMaterial(THREE, options)` on a full-screen triangle. `demo/scene.mjs` draws lit shapes with ink outlines.

## Exports

- `createSobelEdgesShader(options = {})`: a new `{name, uniforms, vertexShader, fragmentShader}` object on every call, input texture uniform `tDiffuse`.
- `createSobelEdgesMaterial(THREE, options = {})`: the definition as a `THREE.ShaderMaterial` with depth test and write off.
- `sobelMagnitude(luma, width, height, x, y)`: the CPU gradient magnitude at one pixel of a row-major luminance array (rows from the bottom, as in a texture), with clamped borders.
- `sobelEdgeMask(luma, width, height, options = {})`: the CPU mask for every pixel as a `Float32Array`.
- `luminance(r, g, b)`: Rec. 709 luminance (0.2126, 0.7152, 0.0722).
- `SOBEL_EDGE_MODES`: `{overlay: 0, edges: 1}`, the values of `uMode`.
- `SOBEL_EDGES_DEFAULTS`: the frozen default options.
- `SOBEL_EDGES_VERTEX`, `SOBEL_EDGES_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| (input) | `tDiffuse` | sampler2D | null | | The frame to process. |
| `resolution` | `uTexelSize` | [w, h] | (1024, 1024) | 1 to 16384 | Input size; the uniform holds its reciprocal. |
| `threshold` | `uThreshold` | number | 0.2 | 0 to 8 | Gradient magnitude where the mask is half on. |
| `softness` | `uSoftness` | number | 0.1 | 0 to 4 | Half width of the transition. |
| `outlineColor` | `uOutlineColor` | linear RGB | (0.03, 0.025, 0.05) | | Edge colour. |
| `backgroundColor` | `uBackgroundColor` | linear RGB | (1, 1, 1) | | Background in `edges` mode. |
| `mode` | `uMode` | string | `overlay` | `overlay`, `edges` | Outline over the image, or edges alone. |
| `opacity` | `uOpacity` | number | 1 | 0 to 1 | Strength of the drawn edges. |

## Checks

- `test_post_sobel_edges.mjs`: magnitudes on a step edge (0, 4, 4, 0), a single bright pixel (square root of 2 at the corner, 2 beside it, 0 on it) and a diagonal ramp, computed independently; the soft mask and its opacity; Rec. 709 luminance; fresh uniforms. Known-wrong controls: a Prewitt gradient (no centre weight) is refused by the step-edge answer, and invalid options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier runs the pass in edges mode on a 24 x 24 coloured test image (disc, step and ramp) and requires the mask at every pixel to equal `sobelEdgeMask` within 0.0001, then renders the demo and compares it with the same frame at opacity 0.

## Limits

Edges come from luminance alone: two colours of equal luminance give no edge, while texture detail and noise give edges too; depth and normal discontinuities are not used. Lines are one to two pixels wide at any distance and are not antialiased beyond the soft threshold. `uTexelSize` must match the input size, or lines thicken or break. Thresholds act on the values the pass receives (linear in three.js's pipeline). The output goes through three.js's output colour space conversion. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Sobel operator: 3 x 3 derivative kernels with centre weight 2
- Rec. 709 luminance
- Smoothstep threshold of the gradient magnitude
