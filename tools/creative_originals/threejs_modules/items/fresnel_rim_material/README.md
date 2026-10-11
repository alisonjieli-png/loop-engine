# Fresnel rim glow material with additive shell mode

A three.js `ShaderMaterial` that lights the silhouette of a mesh. The facing ratio `N.V` is 1 where the surface faces the camera and 0 at the edge; the rim is `bias + scale * (1 - N.V)^power`, so the power sets how tightly the glow hugs the silhouette. In `opaque` mode the rim is added as emission over a Lambert-lit base colour. In `additive` mode the material draws only the rim, with additive blending and no depth write, so a slightly larger copy of the mesh becomes a soft glow shell around it. A cosine pulse driven by `uTime` can breathe the glow. The rim and pulse exist twice, as GLSL and as exact JavaScript mirrors.

## When to use it

Use it for energy cores, crystals, collectables, spirits, force fields seen edge-on, selection and hover highlights that work under any lighting, and sci-fi props.

## Use it

```js
import * as THREE from 'three';
import {createFresnelRimMaterial} from './fresnel_rim_material.mjs';

const core = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 32),
  createFresnelRimMaterial(THREE, {baseColor: [0.06, 0.02, 0.1], rimColor: 0xff40e0, power: 3}));

// A glow shell: the same geometry, 10 percent larger, additive.
const shell = new THREE.Mesh(core.geometry, createFresnelRimMaterial(THREE, {mode: 'additive', rimColor: 0xff40e0, pulseSpeed: 2}));
shell.scale.setScalar(1.1);
scene.add(core, shell);

renderer.setAnimationLoop((time) => {
  shell.material.uniforms.uTime.value = time / 1000;
  renderer.render(scene, camera);
});
```

`demo/scene.mjs` is the scene the verifier renders: a torus knot with an opaque rim, and a sphere with a rim inside an additive shell.

## Exports

- `createFresnelRimMaterial(THREE, options = {})`: the material. Options are the keys of `FRESNEL_RIM_DEFAULTS`; an unknown key throws `TypeError`, a value out of range `RangeError`.
- `fresnelRim(cosTheta, power, bias, scale)`: CPU mirror of the rim, `bias + scale * (1 - clamp(cosTheta, 0, 1))^power`.
- `fresnelPulse(time, speed, depth)`: CPU mirror of the pulse, `1 - depth * (1 - cos(time * speed)) / 2`.
- `FRESNEL_RIM_DEFAULTS`: the frozen default options.
- `FRESNEL_RIM_GLSL`: the GLSL `fresnelRim` and `fresnelPulse` functions, to reuse in your own shaders.
- `FRESNEL_RIM_VERTEX`, `FRESNEL_RIM_FRAGMENT`: the two shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `mode` | `uAdditive` | string | `opaque` | `opaque`, `additive` | Rim over a lit base, or rim alone with additive blending. |
| `baseColor` | `uBaseColor` | colour | (0.05, 0.07, 0.12) | | Lit base colour in opaque mode. |
| `rimColor` | `uRimColor` | colour | (0.25, 0.85, 1) | | Colour of the rim. |
| `power` | `uPower` | number | 2.5 | 0.1 to 16 | Higher keeps the rim closer to the silhouette. |
| `bias` | `uBias` | number | 0.02 | 0 to 1 | Rim everywhere, even facing the camera. |
| `scale` | `uScale` | number | 1.4 | 0 to 8 | Rim at the silhouette on top of the bias. |
| `intensity` | `uIntensity` | number | 1 | 0 to 16 | Rim emission multiplier. |
| | `uTime` | number | 0 | | Seconds; set it every frame to animate the pulse. |
| `pulseSpeed` | `uPulseSpeed` | number | 0 | 0 to 50 | Pulse speed in radians per second; 0 turns it off. |
| `pulseDepth` | `uPulseDepth` | number | 0.35 | 0 to 1 | How far the pulse dims the rim. |
| `lightDirection` | `uLightDirection` | vector | (0.4, 0.8, 0.45) | | Direction toward the light for the base; normalized. |
| `ambient` | `uAmbient` | number | 0.25 | 0 to 1 | Share of the base lit without the light. |

Colours are linear RGB triples, hex numbers, CSS strings or `THREE.Color`.

## Checks

- `test_fresnel_rim_material.mjs`: the rim at five points against values computed independently from the formula, the rim never falling as the surface turns away, the pulse at known times, and the uniforms, blending, transparency and depth write the builder sets in each mode (with a small stand-in for `THREE`). Known-wrong controls: a rim that uses `N.V` instead of `1 - N.V` is refused, and a misspelt option, an unknown mode, an out-of-range power and a zero light direction throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL rim times the pulse on the GPU across a 128 x 1 float target and requires it to match the CPU mirror within 0.0001, then renders the demo and compares it with the same scene at rim intensity 0.

## Limits

An empirical Schlick-style curve for looks, not a physical Fresnel term: there is no index of refraction, reflection or energy conservation. Flat faces seen head-on get only the bias, so boxes glow at grazing angles alone. The base is lit by one direction uniform; three.js scene lights, shadows and fog are ignored, and skinned or morphed meshes are not deformed. The additive shell needs its own slightly larger mesh, and additive blending brightens whatever is behind it. Without a bloom pass the glow does not spread past the silhouette. Written for three.js r155 or later; only 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Schlick-style facing-ratio rim, `bias + scale * (1 - N.V)^power`
- Additive glow shell (source alpha, one) without depth write
- Cosine pulse modulation
