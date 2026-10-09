# Separable Gaussian blur pass with merged bilinear taps

A Gaussian blur for three.js post-processing in two directional passes: blur across into a render target, then up into the next. Each pass uses a truncated Gaussian kernel, `w_i` proportional to `exp(-i^2 / (2 sigma^2))` and normalized over both sides. Neighbouring taps are merged in pairs: fetching once between texels `i` and `i + 1`, at the offset weighted by their two weights, with linear filtering reads exactly `w_i a + w_(i+1) b`, so a radius 8 kernel needs 9 fetches instead of 17. The fragment shader is generated for one sigma and radius with the taps as constant arrays; direction and texel size are uniforms, so one shader serves both passes at any resolution.

## When to use it

Use it for glow and bloom (blur a bright-pass target and add it back), frosted glass and soft UI backdrops, depth-of-field approximations on a background layer, soft shadows of decals, or to blur a reflection or a minimap.

## Use it

Two passes with three.js's post-processing addons:

```js
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {createGaussianBlurShader} from './post_gaussian_blur_separable.mjs';

const resolution = [innerWidth * devicePixelRatio, innerHeight * devicePixelRatio];
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new ShaderPass(createGaussianBlurShader({sigma: 4, radius: 12, direction: [1, 0], resolution})));
composer.addPass(new ShaderPass(createGaussianBlurShader({sigma: 4, radius: 12, direction: [0, 1], resolution})));
```

Without addons, draw with `createGaussianBlurMaterial(THREE, options)` on a full-screen triangle from one render target into another (both with linear filtering). For a wide, cheap blur, render at half or quarter size and set `resolution` to that size. `demo/scene.mjs` blurs a scene in two passes and shows it through a frosted-glass panel.

## Exports

- `createGaussianBlurShader(options = {})`: a new `{name, uniforms, vertexShader, fragmentShader}` object for one direction, input texture uniform `tDiffuse`.
- `createGaussianBlurMaterial(THREE, options = {})`: the definition as a `THREE.ShaderMaterial` with depth test and write off.
- `gaussianWeights(sigma, radius)`: the one-sided kernel `[w0, ..., w_radius]` with `w0 + 2 (w1 + ... + w_radius) = 1`.
- `linearSampledTaps(weights)`: `{offsets, weights}` of the merged taps: the centre, each pair `(i, i + 1)` for odd `i`, and an unpaired last tap at its own offset.
- `gaussianBlurFragment(sigma, radius)`: the generated GLSL fragment stage.
- `blurLine(values, weights)`: the CPU reference, the discrete blur of one line with clamped ends.
- `GAUSSIAN_BLUR_DEFAULTS`: the frozen default options.
- `GAUSSIAN_BLUR_VERTEX`: the vertex stage.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| (input) | `tDiffuse` | sampler2D | null | | The frame to blur, read with linear filtering. |
| `sigma` | (constant) | number | 2 | over 0 to 16 texels | Standard deviation. |
| `radius` | (constant) | integer | 6 | 0 to 32 texels | Taps on each side; about 3 sigma. |
| `direction` | `uTexelStep` | [x, y] | (1, 0) | non-zero | Blur direction in texels. |
| `resolution` | `uTexelStep` | [w, h] | (1024, 1024) | 1 to 16384 | Input size; the step is direction divided by it. |

## Checks

- `test_post_gaussian_blur_separable.mjs`: kernels for sigma 1 against values computed independently, normalization for several sizes, the merged offsets and weights for sigma 1 and 2 (including the unpaired last tap), that one merged fetch reads exactly its weighted pair under linear interpolation, the line blur of an impulse in the middle and at a clamped edge, the generated GLSL and the step uniform. Known-wrong controls: a kernel normalized over one side only is refused, and invalid kernels and options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier blurs a single bright texel across a 33-texel row (in the middle and beside the edge) and requires the result to equal `blurLine` within 0.000001, then blurs an impulse across and up and requires the outer product of the kernel at every pixel; then it renders the demo and compares it with the scene without the panel.

## Limits

The kernel is fixed when the shader is made: changing `sigma` or `radius` needs a new material (direction and resolution are uniforms). The merged taps are exact only with linear filtering of the input; with nearest filtering they read the wrong texels. The kernel is truncated at the radius and renormalized, so a radius well under 3 sigma looks boxy. Pixels past the frame edge repeat the edge (clamp to edge), so bright edges bleed inward. Wide blurs cost two fetches per merged tap per pixel; downsample first. The output goes through three.js's output colour space conversion. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Separable convolution: a 2D Gaussian as two 1D passes
- Linear sampling: two taps merged into one bilinear fetch at the weighted offset
- Truncated Gaussian kernel renormalized over both sides
