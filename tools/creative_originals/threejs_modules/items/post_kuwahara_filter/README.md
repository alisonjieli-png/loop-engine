# Kuwahara painterly filter pass

A post-processing pass that makes a frame look painted while keeping its edges. Around each pixel it looks at four overlapping squares of `(radius + 1)^2` pixels that meet at the pixel (lower left, lower right, upper left, upper right), measures each square's mean colour and the variance of its Rec. 709 luminance, and gives the pixel the mean colour of the least varied square. In flat or gently shaded areas that turns detail into soft patches; at an edge, the square that lies wholly on one side has the least variance, so the edge stays crisp instead of blurring. The quadrant measurements and the choice have an exact CPU mirror on RGBA arrays.

## When to use it

Use it for watercolour and oil-paint looks, storybook and concept-art styles, to soften a noisy render without losing silhouettes, or together with an edge pass for a cel-painted look.

## Use it

```js
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {createKuwaharaShader} from './post_kuwahara_filter.mjs';

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const paint = new ShaderPass(createKuwaharaShader({radius: 4,
  resolution: [innerWidth * devicePixelRatio, innerHeight * devicePixelRatio]}));
composer.addPass(paint);
```

Without addons, draw a render target through `createKuwaharaMaterial(THREE, options)` on a full-screen triangle. For large frames, run the pass at half resolution and upscale: the look survives and the cost drops by four. `demo/scene.mjs` paints a speckled garden of shapes with radius 5.

## Exports

- `createKuwaharaShader(options = {})`: a new `{name, uniforms, vertexShader, fragmentShader}` object on every call, input texture uniform `tDiffuse`.
- `createKuwaharaMaterial(THREE, options = {})`: the definition as a `THREE.ShaderMaterial` with depth test and write off.
- `kuwaharaQuadrants(data, width, height, x, y, radius)`: the four `{mean, variance}` measurements at one pixel of a row-major RGBA image (rows from the bottom, edges clamped).
- `kuwaharaPixel(data, width, height, x, y, radius)`: one output pixel, `[r, g, b, a]` with the centre alpha; the first quadrant wins a tie.
- `kuwaharaImage(data, width, height, radius)`: the whole pass on the CPU, a new `Float32Array`.
- `KUWAHARA_DEFAULTS`: the frozen default options.
- `KUWAHARA_VERTEX`, `KUWAHARA_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| (input) | `tDiffuse` | sampler2D | null | | The frame. |
| `radius` | `uRadius` | integer | 3 | 1 to 6 | Quadrant size; patches grow with it. |
| `resolution` | `uTexelSize` | [w, h] | (1024, 1024) | 1 to 16384 | Input size; the uniform holds its reciprocal. |

## Checks

- `test_post_kuwahara_filter.mjs`: the four quadrant means and variances of a 3 x 3 image and the chosen quadrant, against values computed independently in python3; a flat image unchanged; a step edge kept exactly at every pixel; the shader definition. Known-wrong controls: a box blur and a filter that picks the most varied quadrant both fail the same answers, and invalid radii, images and options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier runs the pass on a 24 x 24 float image (a diagonal edge, two curved gradients and three discs) with radius 3 and requires every pixel to be the mean of a least-varied quadrant (within float rounding, so near-ties may go either way) and to equal `kuwaharaPixel` within 0.00001 wherever there is no near-tie; then it compares the demo with a plain copy of the frame.

## Limits

The classic four-square Kuwahara filter, not the generalized or anisotropic variants: square quadrants give blocky patches and artefacts along diagonal edges at large radii. Variance uses luminance only, so two colours of equal luminance count as flat. When quadrants vary almost equally, the choice follows float rounding, so neighbouring pixels can pick different quadrants in flat noisy areas. Cost grows with `(radius + 1)^2` times four reads per pixel (196 at radius 6). `uTexelSize` must match the input size. The output goes through three.js's output colour space conversion. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Kuwahara filter: four overlapping quadrants, the mean of the least varied one
- Variance as `E[L^2] - E[L]^2` of Rec. 709 luminance
