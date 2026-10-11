# Tone mapping curves pass: clamp, Reinhard, ACES fit and Hable

A post-processing pass that maps high-dynamic-range values into [0, 1] for display. It multiplies by `exposure`, then applies one of four curves chosen by an integer uniform, so a game or viewer can switch curves at run time: a plain clamp; extended Reinhard, `x (1 + x / W^2) / (1 + x)`, which maps the white point `W` to 1; Narkowicz's 2015 rational fit of the ACES filmic curve, `x (2.51 x + 0.03) / (x (2.43 x + 0.59) + 0.14)`; and Hable's filmic curve with its published parameters, normalized by its white point 11.2. Every curve has an exact CPU mirror, so tools can predict the displayed value of any HDR input.

## When to use it

Use it at the end of an HDR pipeline (bloom, bright emissives, physically based lights) when you want the curve inside your own pass chain instead of the renderer, when you want to compare curves side by side, or when a tool needs to know exactly how a value will display.

## Use it

```js
import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {TONEMAP_OPERATORS, createTonemapShader} from './post_tonemap_curves.mjs';

renderer.toneMapping = THREE.NoToneMapping;               // the pass applies the curve once
const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(innerWidth, innerHeight,
  {type: THREE.HalfFloatType}));                          // keep values above 1
composer.addPass(new RenderPass(scene, camera));
const tonemap = new ShaderPass(createTonemapShader({operator: 'aces', exposure: 1.1}));
composer.addPass(tonemap);

tonemap.uniforms.uOperator.value = TONEMAP_OPERATORS.hable;  // switch at run time
```

Without addons, render the scene into a `HalfFloatType` render target and draw it through `createTonemapMaterial(THREE, options)` on a full-screen triangle. `demo/scene.mjs` shows an HDR scene through the ACES curve.

## Exports

- `createTonemapShader(options = {})`: a new `{name, uniforms, vertexShader, fragmentShader}` object on every call, input texture uniform `tDiffuse`.
- `createTonemapMaterial(THREE, options = {})`: the definition as a `THREE.ShaderMaterial` with depth test, depth write and three.js tone mapping off.
- `tonemapValue(value, options = {})`: the CPU mirror for one channel: `max(value * exposure, 0)` through the curve, clamped to [0, 1].
- `tonemapColor(rgb, options = {})`: the CPU mirror for an `[r, g, b]` colour.
- `hableCurve(x)`: Hable's curve `((x (Ax + CB) + DE) / (x (Ax + B) + DF)) - E / F` with A 0.15, B 0.5, C 0.1, D 0.2, E 0.02, F 0.3.
- `TONEMAP_OPERATORS`: `{clamp: 0, reinhard: 1, aces: 2, hable: 3}`, the values of `uOperator`.
- `TONEMAP_DEFAULTS`: the frozen default options.
- `TONEMAP_VERTEX`, `TONEMAP_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| (input) | `tDiffuse` | sampler2D | null | | The HDR frame. |
| `operator` | `uOperator` | string | `aces` | `clamp`, `reinhard`, `aces`, `hable` | The curve. |
| `exposure` | `uExposure` | number | 1 | over 0 to 64 | Multiplier before the curve. |
| `whitePoint` | `uWhitePoint` | number | 4 | 1 to 64 | Reinhard: the exposed value that maps to 1. |

## Checks

- `test_post_tonemap_curves.mjs`: every curve at several inputs against values computed independently from the published formulas, exposure scaling, negative and very large inputs, that each curve rises monotonically from 0, that Reinhard maps its white point and Hable maps 11.2 to 1, the colour mirror and the shader definition (which must not include three.js's tone mapping chunk). Known-wrong controls: plain Reinhard without the white point is refused, and invalid options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier runs an HDR ramp (0 to 16 across the channels) through all four curves and requires every texel to equal `tonemapValue` within 0.00001, then renders an HDR scene into a HalfFloat target and compares the ACES frame with the clamped one.

## Limits

Each curve acts on every channel separately, so saturated highlights shift hue toward the primaries; there is no luminance-only mode, gamut mapping or AgX. The ACES curve is Narkowicz's single rational fit, not the full ACES reference rendering transform, and no 0.6 input scale is applied (use `exposure`). The Hable parameters are fixed at the published values. The input must keep values above 1 (a HalfFloat or Float target) and three.js's own tone mapping must be off, or the curve applies twice. The output goes through three.js's output colour space conversion. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Extended Reinhard operator with a white point
- Narkowicz 2015 rational fit of the ACES filmic curve
- Hable filmic curve (toe, linear section and shoulder) normalized by its white point
