# Gerstner wave water material with CPU buoyancy

A three.js `ShaderMaterial` for a horizontal water plane. Up to four Gerstner (trochoidal) waves move each vertex in a circle: sideways along the wave direction by `a cos(phase)` and up by `a sin(phase)`, with amplitude `a = steepness / k` and `k = 2 pi / wavelength`, so crests sharpen and troughs flatten as on real swell. The fragment stage recomputes the exact surface normal from the wave sum per pixel, shades the body from a deep to a shallow colour between trough and crest, reflects a sky colour by a Schlick Fresnel term, adds a Blinn sun glint, and lays foam where the surface is compressed (the Jacobian of the horizontal displacement drops). The same wave sum runs in JavaScript, so a boat or buoy can float on exactly the surface the GPU draws.

## When to use it

Use it for seas, lakes and harbours, floating props and boats, stylized ocean games, and water around islands.

## Use it

```js
import * as THREE from 'three';
import {createGerstnerWaterMaterial, gerstnerSurfaceHeight, gerstnerNormal, GERSTNER_WATER_DEFAULTS} from './gerstner_wave_water_material.mjs';

const plane = new THREE.PlaneGeometry(200, 200, 400, 400);
plane.rotateX(-Math.PI / 2);
const water = createGerstnerWaterMaterial(THREE);
scene.add(new THREE.Mesh(plane, water));

const waves = GERSTNER_WATER_DEFAULTS.waves;
renderer.setAnimationLoop((ms) => {
  const t = ms / 1000;
  water.uniforms.uTime.value = t;
  const {height, rest} = gerstnerSurfaceHeight(waves, boat.position.x, boat.position.z, t);
  boat.position.y = height;
  const n = gerstnerNormal(waves, rest[0], rest[1], t);
  boat.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(...n));
  renderer.render(scene, camera);
});
```

To change the waves at run time, write `packGerstnerWaves(newWaves)` into `uWaves`, `uWaveSpeeds`, `uWaveCount` and `uMaxHeight`. `demo/scene.mjs` renders open water under a low sun with a buoy placed by the CPU height.

## Exports

- `createGerstnerWaterMaterial(THREE, options = {})`: the double-sided material. Options are the keys of `GERSTNER_WATER_DEFAULTS`; an unknown key throws `TypeError`, a value out of range `RangeError`.
- `packGerstnerWaves(waves)`: validates 1 to 4 waves `{direction: [x, z], wavelength, steepness, speed}` and returns `{waves: Float32Array(16), speeds, count, maxHeight}`. A steepness sum above 1 throws, because crests would loop over themselves.
- `gerstnerDisplacement(waves, x, z, time)`: CPU mirror of the wave sum, the `[dx, dy, dz]` offset of the rest point `(x, 0, z)`.
- `gerstnerNormal(waves, x, z, time)`: CPU mirror of the analytic unit normal at the displaced rest point.
- `gerstnerJacobian(waves, x, z, time)`: CPU mirror of the compression, 1 on flat water and smaller where crests bunch up.
- `gerstnerSurfaceHeight(waves, x, z, time, iterations = 8)`: the water height above a world point, found by fixed-point search for the rest point that lands there; returns `{height, rest, residual}`.
- `GERSTNER_WATER_DEFAULTS`: the frozen default options, with four waves.
- `GERSTNER_WATER_GLSL`: the GLSL `gerstnerOffset`, `gerstnerNormal` and `gerstnerJacobian`, which take the waves as array arguments.
- `GERSTNER_WATER_VERTEX`, `GERSTNER_WATER_FRAGMENT`: the two shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `waves` | `uWaves`, `uWaveSpeeds`, `uWaveCount`, `uMaxHeight` | waves | four waves | 1 to 4, steepness sum at most 1 | Direction, wavelength, steepness and phase speed of each wave. |
| | `uTime` | number | 0 | | Seconds; advance it every frame. |
| `deepColor` | `uDeepColor` | colour | (0.01, 0.07, 0.13) | | Body colour in the troughs. |
| `shallowColor` | `uShallowColor` | colour | (0.05, 0.32, 0.38) | | Body colour on the crests. |
| `skyColor` | `uSkyColor` | colour | (0.55, 0.7, 0.85) | | Reflected at grazing angles. |
| `sunDirection` | `uSunDirection` | vector | (-0.4, 0.5, -0.75) | | Direction toward the sun; normalized. |
| `sunColor` | `uSunColor` | colour | (1, 0.92, 0.75) | | Glint colour. |
| `shininess` | `uShininess` | number | 180 | 1 to 4096 | Glint exponent. |
| `foamColor` | `uFoamColor` | colour | (0.92, 0.96, 1) | | Foam colour. |
| `foamThreshold` | `uFoamThreshold` | number | 0.45 | -1 to 2 | Compression below which foam shows. |
| `foamSoftness` | `uFoamSoftness` | number | 0.15 | 0.001 to 1 | Half width of the foam fade. |

## Checks

- `test_gerstner_wave_water_material.mjs`: one wave against the closed form (crest offset, normal, compression), the four default waves against an independent transcription, the analytic normal against a finite-difference normal of the displaced surface at three places and times, the buoyancy height and its residual, and the packed uniforms (with a small stand-in for `THREE`). Known-wrong controls: a perturbed surface is refused by the normal comparison, and invalid waves (none, five, zero direction, steepness sum above 1, unknown key) and options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL offset, Jacobian and normal on the GPU at 1,024 points of a 20 by 20 unit patch and requires each to match the CPU mirror within 0.001, checks that the demo's buoy height converged, then renders the demo and compares it with the flat, unshaded plane.

## Limits

Stylized water, not a spectral or physically based ocean: four waves tile visibly at a distance, and there is no refraction, depth colour, caustics, screen-space reflection or shoreline. Displacement only looks right on a densely subdivided plane, and the plane must be horizontal in world space because the waves use world x and z. Foam is a per-pixel compression mask, not simulated foam that lingers. The height search converges slowly where crests are steep; its residual is returned. Skinned, morphed and instanced meshes are not supported. Written for three.js r155 or later; only 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Gerstner (trochoidal) waves with amplitude `steepness / k`
- Analytic surface tangents and normal of a sum of Gerstner waves
- Jacobian determinant of the horizontal displacement as a foam mask
- Schlick Fresnel blend toward a sky colour, Blinn glint
- Fixed-point inversion of the horizontal displacement for buoyancy
