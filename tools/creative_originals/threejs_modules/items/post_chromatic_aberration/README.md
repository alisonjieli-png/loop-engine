# Radial chromatic aberration pass with dispersion

A post-processing pass that imitates lateral chromatic aberration: each colour channel is a copy of the frame scaled about an optical centre by a slightly different factor. Red samples toward the centre, so its image grows; blue samples away from it, so its image shrinks; green stays put. The scale difference is `strength * r^power`, where `r` is 0 at the centre and 1 at the middle of the top edge, so fringes stay thin in the middle and widen toward the corners. With `samples` above 1 the pass takes up to eight taps between the red and blue coordinates and blends them into the channels with triangular weights, which smears the fringe into a small spectrum instead of three hard copies. The tap coordinates have an exact CPU mirror.

## When to use it

Use it for lens and camera realism, found-footage and security-camera looks, impact or damage flashes, dream and glitch sequences, or to make a sharp synthetic render feel photographed. Keep `strength` small (0.005 to 0.02) for realism.

## Use it

With three.js's post-processing addons:

```js
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {createChromaticAberrationShader} from './post_chromatic_aberration.mjs';

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const fringe = new ShaderPass(createChromaticAberrationShader({strength: 0.012, power: 1.2, samples: 5,
  aspect: innerWidth / innerHeight}));
composer.addPass(fringe);

// A hit flash: raise the strength for a few frames.
fringe.uniforms.uStrength.value = 0.06;
```

Without addons, draw a render target through `createChromaticAberrationMaterial(THREE, options)` on a full-screen triangle and set `material.uniforms.tDiffuse.value = target.texture`. `demo/scene.mjs` renders bright bars and spheres through the pass.

## Exports

- `createChromaticAberrationShader(options = {})`: a new `{name, uniforms, vertexShader, fragmentShader}` object on every call, input texture uniform `tDiffuse`; the centre is a plain `[u, v]` array.
- `createChromaticAberrationMaterial(THREE, options = {})`: the definition as a `THREE.ShaderMaterial` with depth test and write off.
- `aberrationOffset(u, v, options = {})`: the CPU mirror of the three-tap path, `{red, green, blue}` texture coordinates for the output pixel at `(u, v)`.
- `dispersionWeights(samples)`: for 2 to 8 taps, one `[red, green, blue]` weight row per tap from the red end to the blue end, each channel summing to 1.
- `dispersionTaps(u, v, options = {})`: the CPU mirror of either path, every tap's `uv` and `weights`.
- `CHROMATIC_ABERRATION_DEFAULTS`: the frozen default options.
- `CHROMATIC_ABERRATION_VERTEX`, `CHROMATIC_ABERRATION_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| (input) | `tDiffuse` | sampler2D | null | | The frame to process. |
| `strength` | `uStrength` | number | 0.012 | -0.5 to 0.5 | Scale difference at distance 1; negative swaps the fringe colours. |
| `power` | `uPower` | number | 1 | 0 to 8 | Growth with distance; 0 is a uniform magnification difference. |
| `center` | `uCenter` | [u, v] | (0.5, 0.5) | 0 to 1 | Optical centre. |
| `aspect` | `uAspect` | number | 1 | 0.01 to 100 | Frame width over height. |
| `samples` | `uSamples` | integer | 1 | 1 to 8 | 1: one tap per channel; more: dispersion taps. |

## Checks

- `test_post_chromatic_aberration.mjs`: channel coordinates for a centred pass, a high power, a wide frame and an off-centre optical centre against values computed independently; the dispersion weights for 2, 3, 5 and 8 taps; the taps of both paths; fresh uniforms on every definition and the material flags. Known-wrong controls: a pass that moves every channel the same way is refused, and invalid options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier feeds the pass textures that store their own coordinates (with linear filtering), so the output reveals where every channel sampled; all 1,024 pixels must match the CPU mirror within 0.00001 for the three-tap path and for five dispersion taps. Then it renders the demo and compares it with the same frame at strength 0.

## Limits

A stylized model of lateral chromatic aberration: each channel is a scaled copy of the frame, not a traced lens, and there is no longitudinal (focus) aberration, distortion or vignetting. Dispersion blurs along the radial line with fixed triangular channel weights, not a measured spectrum. Taps that land outside the frame repeat the edge pixels (clamp to edge), so strong settings smear the border. `uAspect` does not follow the canvas by itself. The output goes through three.js's output colour space conversion. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Wavelength-dependent radial magnification about an optical centre
- Triangular spectral weights over taps between the red and blue scales
