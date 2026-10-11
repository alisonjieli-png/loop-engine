# Film grain pass from an integer hash with luminance response

A post-processing pass that adds film grain. Each output pixel belongs to a grain cell of `grainSize` pixels. A 32-bit integer hash of the cell, the frame number, a seed and the channel gives two uniform draws, whose sum minus one is a triangular noise value in (-1, 1). The noise is scaled by `intensity` and by a luminance response, `mix(1, 4 L (1 - L), response)`, so grain is strongest in the mid-tones and fades in deep shadows and clipped highlights, as on film. Grain is mono by default or independent per channel. The hash uses unsigned integer arithmetic in GLSL ES 3.00 and the same arithmetic in JavaScript, so `grainHash`, `grainValue` and `applyGrainCpu` reproduce the shader exactly, and the hash is a reusable GLSL chunk.

## When to use it

Use it for cinematic and documentary looks, to hide banding in dark gradients, to make clean renders feel photographed, for horror and found-footage moods, or to add texture to flat-shaded UI backdrops.

## Use it

```js
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {createFilmGrainShader} from './post_film_grain.mjs';

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const grain = new ShaderPass(createFilmGrainShader({intensity: 0.1, response: 0.7}));
composer.addPass(grain);

renderer.setAnimationLoop(() => {
  grain.uniforms.uFrame.value = (grain.uniforms.uFrame.value + 1) % 1000000;
  composer.render();
});
```

The hash alone, in your own shader: paste `FILM_GRAIN_HASH_GLSL` into the fragment stage and call `grainNoise(uvec2(gl_FragCoord.xy), frame, seed, 0u)`. Without addons, draw a render target through `createFilmGrainMaterial(THREE, options)` on a full-screen triangle. `demo/scene.mjs` shows a still life with mono grain.

## Exports

- `createFilmGrainShader(options = {})`: a new `{name, uniforms, vertexShader, fragmentShader}` object on every call, input texture uniform `tDiffuse`.
- `createFilmGrainMaterial(THREE, options = {})`: the definition as a `THREE.ShaderMaterial` with depth test and write off.
- `grainHash(x, y, frame, seed, channel)`: the CPU mirror of the shader's 32-bit cell hash, an unsigned integer.
- `grainValue(x, y, options = {})`: the grain at output pixel `(x, y)` (from the bottom-left), `[r, g, b]` in (-1, 1), equal for mono grain.
- `grainWeight(rgb, options = {})`: the grain scale for a colour.
- `applyGrainCpu(rgb, x, y, options = {})`: the CPU mirror of the whole pass for one pixel.
- `FILM_GRAIN_DEFAULTS`: the frozen default options.
- `FILM_GRAIN_HASH_GLSL`: the GLSL chunk with `grainMix`, `grainHash` and `grainNoise`.
- `FILM_GRAIN_VERTEX`, `FILM_GRAIN_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| (input) | `tDiffuse` | sampler2D | null | | The frame. |
| `intensity` | `uIntensity` | number | 0.08 | 0 to 1 | Grain amplitude at full response. |
| `response` | `uResponse` | number | 0.75 | 0 to 1 | How much the grain follows `4 L (1 - L)`. |
| `grainSize` | `uGrainSize` | integer | 1 | 1 to 16 | Cell size in output pixels. |
| `colored` | `uColored` | boolean | false | | Per-channel grain. |
| `frame` | `uFrame` | integer | 0 | 0 to 2147483647 | Frame number. |
| `seed` | `uSeed` | integer | 0 | 0 to 2147483647 | Another pattern. |

## Checks

- `test_post_film_grain.mjs`: hash values computed independently with 32-bit arithmetic in python3; grain values at known cells; mono grain equal on every channel; cells shared within a grain cell; grain changing with the frame; over 20,000 cells a mean within 0.01 of 0 and a variance within 0.01 of 1/6 (the triangular distribution); the response at mid grey, black and clamped white; the whole-pass mirror; the shader definition. Known-wrong controls: a hash with a different multiplier is refused, and invalid options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier runs the hash chunk on the GPU over 64 x 64 cells and three channels and requires the top 24 bits to equal `grainHash` exactly at every one of the 12,288 values; it runs the whole pass on a 48 x 48 coloured image (coloured grain, 2-pixel cells) and requires every pixel to equal `applyGrainCpu` within 0.00001; then it compares the demo with the same frame at intensity 0.

## Limits

Stylized grain, not a model of film emulsion: square cells, a triangular value distribution and a parabolic luminance response, with no clumping, layer structure or sharpening. Grain is added to the linear values the pass receives, so after sRGB encoding it looks stronger in the shadows than in the highlights. The pattern is tied to output pixels; the frame and seed are GLSL int uniforms, limited to 2147483647. The output goes through three.js's output colour space conversion. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- 32-bit integer hash from xor-shift and multiply rounds, chained over cell, frame, seed and channel
- Triangular distribution as the sum of two uniform draws
- Parabolic luminance response `4 L (1 - L)`
