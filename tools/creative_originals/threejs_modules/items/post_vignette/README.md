# Aspect-aware vignette pass

A post-processing pass that mixes the frame toward a colour (black by default) as pixels get further from the centre. Distance is 0 at the centre and 1 at the middle of the top edge; between `inner` and `outer` the mix rises along a smoothstep curve to `strength`. With `roundness` 1 the distance is measured in pixels, so the vignette stays round on a wide frame; with 0 it stretches with the frame. The module gives the pass as a plain shader definition, the shape three.js `ShaderPass` takes, and as a ready `ShaderMaterial`, plus an exact CPU mirror of the falloff.

## When to use it

Use it to frame a shot, pull the eye toward the centre, darken busy borders behind UI, or tint the edges for a mood (a cold blue rim, a warm sepia).

## Use it

With three.js's post-processing addons:

```js
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {createVignetteShader} from './post_vignette.mjs';

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const vignette = new ShaderPass(createVignetteShader({strength: 0.7, aspect: innerWidth / innerHeight}));
composer.addPass(vignette);
addEventListener('resize', () => { vignette.uniforms.uAspect.value = innerWidth / innerHeight; });
```

Without addons, draw a render target through the material on a full-screen triangle:

```js
import {createVignetteMaterial} from './post_vignette.mjs';

const material = createVignetteMaterial(THREE, {color: [0.02, 0.04, 0.12]});
material.uniforms.tDiffuse.value = renderTarget.texture;
```

`demo/scene.mjs` renders a lit scene into a target and draws it through the pass.

## Exports

- `createVignetteShader(options = {})`: a new `{name, uniforms, vertexShader, fragmentShader}` object on every call, with the input texture uniform `tDiffuse`. Vector uniforms are plain arrays, which three.js uploads as `vec3`.
- `createVignetteMaterial(THREE, options = {})`: the definition as a `THREE.ShaderMaterial` with depth test and depth write off.
- `vignetteAmount(u, v, options = {})`: the CPU mirror; how far the pixel at `uv` is mixed toward the colour, from 0 to `strength`.
- `VIGNETTE_DEFAULTS`: the frozen default options.
- `VIGNETTE_VERTEX`, `VIGNETTE_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| (input) | `tDiffuse` | sampler2D | null | | The frame to process. |
| `color` | `uColor` | linear RGB | (0, 0, 0) | | Colour the edges are mixed toward. |
| `strength` | `uStrength` | number | 0.65 | 0 to 1 | Largest mix toward the colour. |
| `inner` | `uInner` | number | 0.45 | 0 to 4 | Distance where the falloff starts. |
| `outer` | `uOuter` | number | 1.3 | 0 to 4 | Distance where it reaches `strength`; not below `inner`. |
| `roundness` | `uRoundness` | number | 1 | 0 to 1 | 1 round in pixels, 0 shaped like the frame. |
| `aspect` | `uAspect` | number | 1 | 0.01 to 100 | Frame width over height. |

## Checks

- `test_post_vignette.mjs`: the amount at the centre, the middle of an edge, a corner and an inner point, for round and frame-shaped vignettes, against values computed independently from the closed form; fresh uniforms on every definition; the material flags. Known-wrong controls: a vignette that ignores the aspect ratio is refused, and invalid options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier runs the pass on a white input into a 32 x 32 float target and requires every pixel to equal `1 - vignetteAmount` within 0.002, then renders the demo and compares it with the same frame at strength 0.

## Limits

A colour mix, not a lens model: no optical falloff, chromatic shift or exposure change. The pass reads one texture and writes one, so it needs a render target or an `EffectComposer` before it. `uAspect` does not follow the canvas by itself; set it on resize. The output goes through three.js's output colour space conversion: as the last pass it writes sRGB to the screen, into a linear render target it writes linear values. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Smoothstep falloff between two radii
- Aspect-corrected radial distance blended with frame-shaped distance
