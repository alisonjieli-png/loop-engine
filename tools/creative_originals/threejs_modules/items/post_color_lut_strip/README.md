# 3D LUT colour grading pass from a texture strip

A post-processing pass that grades colour through a 3D lookup table. The table is stored as a strip: N tiles of N x N texels side by side, tile `b` holding blue slice `b`, red along x and green along y, so a 16-point table is a 256 x 16 RGBA image. For each pixel the pass finds the two nearest blue slices, reads each with hardware bilinear filtering at half-texel insets (so a lookup never bleeds into the next tile) and blends them, which makes the lookup trilinear. In the `srgb` domain the colour is sRGB-encoded before the lookup and decoded after, which is what tables from grading tools expect; in `linear` the values are looked up as received. Helpers bake strips from any function, sample a strip on the CPU exactly as the shader does and wrap a strip in a `DataTexture`.

## When to use it

Use it to give a scene a look (teal and orange, bleach bypass, film emulation, day-for-night, sepia), to match colour between shots, to drive mood changes by swapping or blending strips, or to apply a grade designed in another tool once it is baked into this layout.

## Use it

```js
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {createColorLutShader, createLutStripTexture, lutStripFromFunction} from './post_color_lut_strip.mjs';

// Bake a look from a function of sRGB-encoded colour (any 16 to 64 point grid).
const sepia = lutStripFromFunction(32, (r, g, b) => {
  const y = 0.299 * r + 0.587 * g + 0.114 * b;
  return [y * 1.07, y * 0.92, y * 0.72];
});
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const grade = new ShaderPass(createColorLutShader({size: 32, intensity: 0.85}));
grade.uniforms.tLut.value = createLutStripTexture(THREE, sepia, 32);
composer.addPass(grade);
```

Without addons, use `createColorLutMaterial(THREE, options)` on a full-screen triangle and set `tDiffuse` and `tLut`. A strip image made in an image editor in this layout can be loaded with `TextureLoader` instead of baked; give it linear filtering, no mipmaps and no colour space conversion. `demo/scene.mjs` grades a lit scene teal and orange.

## Exports

- `createColorLutShader(options = {})`: a new `{name, uniforms, vertexShader, fragmentShader}` object with the input texture `tDiffuse` and the strip `tLut`.
- `createColorLutMaterial(THREE, options = {})`: the definition as a `THREE.ShaderMaterial` with depth test and write off.
- `createLutStripTexture(THREE, data, size)`: the strip as a `THREE.DataTexture` (width `size * size`, height `size`, linear filtering, clamped edges, no mipmaps).
- `identityLutStrip(size)`: the strip that returns its input.
- `lutStripFromFunction(size, fn)`: a strip baked from `fn(r, g, b) -> [r, g, b]` at every grid point `k / (size - 1)`, rounded to 8 bits.
- `sampleLutStripCpu(data, size, r, g, b)`: the CPU mirror of the trilinear lookup.
- `gradeColorCpu(data, size, rgb, options = {})`: the CPU mirror of the whole pass for one colour.
- `COLOR_LUT_DOMAINS`: `{linear: 0, srgb: 1}`, the values of `uDomain`.
- `COLOR_LUT_DEFAULTS`: the frozen default options.
- `COLOR_LUT_VERTEX`, `COLOR_LUT_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| (input) | `tDiffuse` | sampler2D | null | | The frame to grade. |
| (strip) | `tLut` | sampler2D | null | | The strip texture. |
| `size` | `uLutSize` | integer | 16 | 2 to 64 | Grid points per axis of the strip. |
| `intensity` | `uIntensity` | number | 1 | 0 to 1 | Mix between the input and the graded colour. |
| `domain` | `uDomain` | string | `srgb` | `srgb`, `linear` | Look up sRGB-encoded or received values. |

## Checks

- `test_post_color_lut_strip.mjs`: the byte layout of a 2-point identity strip; trilinear samples of identity, red-inverted, red-squared and warm strips against values computed independently; clamping of out-of-range inputs; the sRGB round trip with the identity strip and the intensity mix; the texture wrapper and the shader definition. Known-wrong controls: a sampler that takes the nearest blue slice is refused, and invalid sizes, strips and options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier runs the pass on a 32 x 32 float test image: the identity strip must return the input within 0.0001 and a baked warm grade in the sRGB domain must equal `gradeColorCpu` within 0.0001 at every pixel. Then it renders the demo and compares it with the same frame at intensity 0.

## Limits

Inputs are clamped to [0, 1] before the lookup, so HDR values above 1 grade as 1: tone map before this pass. Strips are 8 bits per channel, so smooth grades step by 1/255 and very small sizes band. The pass reads strips in this module's layout only (blue slices left to right, green upward); other layouts and `.cube` files must be converted or baked with `lutStripFromFunction` first. The sRGB domain uses the exact piecewise sRGB curve, not three.js's colour space chunks. The output goes through three.js's output colour space conversion. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- 3D lookup table unfolded into a 2D strip of blue slices
- Trilinear interpolation: hardware bilinear inside a slice, a manual blend between slices
- Half-texel insets so a lookup never bleeds into the neighbouring slice
- Piecewise sRGB transfer function
