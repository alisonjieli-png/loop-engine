# Ordered Bayer dither pass to levels or a palette

A post-processing pass for low-colour looks. Each block of output pixels reads one input pixel and one threshold from a Bayer matrix (2, 4, 8 or 16 wide, built by the recursion `M(2n) = [[4M, 4M + 2], [4M + 3, 4M + 1]]`). In `levels` mode every channel is rounded to `levels` steps with the threshold in place of 0.5, so a flat colour turns into a fine pattern whose average is the colour. In `palette` mode the threshold nudges the colour by up to `spread / 2` and the nearest of up to 16 palette colours is drawn. In the `srgb` domain the work happens on sRGB-encoded values, so steps are even to the eye; in `linear` it happens on the values received. The shader computes the matrix bit by bit; `bayerThreshold` mirrors it and `bayerMatrix` builds it recursively, and the tests hold the two against each other.

## When to use it

Use it for retro and handheld-console looks, newspaper and zine prints, limited-palette pixel art from 3D scenes, reduced-colour UI themes, or to break up banding in a smooth gradient by dithering to 64 or more levels.

## Use it

```js
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {createOrderedDitherShader} from './post_ordered_dither_palette.mjs';

const size = [innerWidth * devicePixelRatio, innerHeight * devicePixelRatio];
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const handheld = new ShaderPass(createOrderedDitherShader({
  mode: 'palette', pixelSize: 3, matrixSize: 4, spread: 0.4, resolution: size,
  palette: [[0.06, 0.15, 0.06], [0.19, 0.38, 0.19], [0.55, 0.67, 0.06], [0.61, 0.74, 0.06]],
}));
composer.addPass(handheld);
```

For banding removal: `createOrderedDitherShader({levels: 64, matrixSize: 8, resolution: size})`. Without addons, draw a render target through `createOrderedDitherMaterial(THREE, options)` on a full-screen triangle. `demo/scene.mjs` dithers a seaside still life to an 8-colour palette in 2-pixel blocks.

## Exports

- `createOrderedDitherShader(options = {})`: a new `{name, uniforms, vertexShader, fragmentShader}` object on every call, input texture uniform `tDiffuse`; `uPalette` is a flat `Float32Array` of 16 colours, unused entries zero.
- `createOrderedDitherMaterial(THREE, options = {})`: the definition as a `THREE.ShaderMaterial` with depth test and write off.
- `bayerMatrix(n)`: the `n x n` Bayer matrix (`n` = 2, 4, 8 or 16), rows counting up from the bottom of the screen.
- `bayerThreshold(x, y, n)`: the CPU mirror of the shader's threshold `(M + 0.5) / n^2`, computed bit by bit.
- `ditherSamplePixel(x, y, pixelSize = 1)`: the pixel whose input colour the block of `(x, y)` reads (the one at `floor(pixelSize / 2)` inside the block).
- `ditherPixel(rgb, x, y, options = {})`: the CPU mirror of one output pixel, with `rgb` read at `ditherSamplePixel`.
- `DITHER_MODES`: `{levels: 0, palette: 1}`; `DITHER_DOMAINS`: `{linear: 0, srgb: 1}`.
- `ORDERED_DITHER_DEFAULTS`: the frozen default options.
- `ORDERED_DITHER_VERTEX`, `ORDERED_DITHER_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| (input) | `tDiffuse` | sampler2D | null | | The frame to dither. |
| `resolution` | `uResolution` | [w, h] | (1024, 1024) | 1 to 16384 | Output size in pixels. |
| `pixelSize` | `uPixelSize` | integer | 1 | 1 to 64 | Block size in output pixels. |
| `matrixSize` | `uMatrixBits` | integer | 4 | 2, 4, 8, 16 | Bayer matrix width (the uniform holds log2 of it). |
| `mode` | `uMode` | string | `levels` | `levels`, `palette` | Levels per channel or nearest palette colour. |
| `levels` | `uLevels` | integer | 4 | 2 to 256 | Levels per channel. |
| `palette` | `uPalette`, `uPaletteSize` | colours | 4 dusk colours | 1 to 16 | Palette in the dithering domain. |
| `spread` | `uSpread` | number | 0.5 | 0 to 2 | Palette mode: threshold nudge. |
| `domain` | `uDomain` | string | `srgb` | `srgb`, `linear` | Values the dithering works on. |

## Checks

- `test_post_ordered_dither_palette.mjs`: the classic 2 x 2 and 4 x 4 matrices and the first rows of the 8 x 8; every matrix holds each value once; the bit-by-bit threshold equals the recursive matrix at every cell of 2, 4, 8 and 16; flat colours of 1/2, 5/16 and 15/16 average to themselves over one tile; levels and palette outputs at known pixels, ties and the sRGB domain; block sampling. Known-wrong controls: a threshold that reads the matrix transposed is refused, and invalid options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier runs the pass on a 32 x 32 float gradient in levels mode (linear) and in palette mode (sRGB, 2-pixel blocks, 8 x 8 matrix) and requires every pixel to equal `ditherPixel` within 0.00001, then renders the demo and compares it with a plain copy of the frame.

## Limits

Ordered dithering only: no error diffusion, blue noise or temporal dithering, so the cross-hatch of the Bayer matrix shows. The palette search is the nearest colour by Euclidean distance in the dithering domain, not a perceptual colour difference, and ties keep the earlier colour. The pattern is tied to output pixels, so it stays fixed on screen while the image moves. `uResolution` must match the output size, or blocks read the wrong input pixel. HDR inputs are clamped to [0, 1]. The output goes through three.js's output colour space conversion. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Bayer ordered dither matrix by recursion, and its bit-interleaved closed form
- Threshold-offset rounding to levels; threshold-nudged nearest-palette search
- Piecewise sRGB transfer function for perceptually even steps
