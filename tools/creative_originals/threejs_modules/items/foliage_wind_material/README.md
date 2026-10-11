# Foliage wind sway material with gusts

Wind for grass, crops, reeds and foliage, computed in the vertex stage. Every vertex moves along the wind direction by an amount weighted by its height on the blade raised to a stiffness exponent, so roots stay planted and tips swing most. The sway is two layered sines whose phase shifts with the blade's position along the wind, so waves travel across a field, plus gusts: smooth value noise on integer-hashed cells that drifts downwind over time. Each blade takes its phase from where it stands (its instance origin), and the tip drops slightly as it bends so the blade keeps roughly its length. A root-to-tip colour ramp and a simple two-sided light finish the look. The wind function has an exact CPU mirror.

## When to use it

Use it for meadows and lawns, wheat and reed beds, bushes and leaves on `InstancedMesh`, and anywhere a field of thin geometry should feel alive without a physics simulation. Use `windOffset` on the CPU to make particles, leaves or audio follow the same gusts.

## Use it

```js
import * as THREE from 'three';
import {createFoliageWindMaterial} from './foliage_wind_material.mjs';

const blade = new THREE.PlaneGeometry(0.07, 1, 1, 6).translate(0, 0.5, 0);   // root at y = 0, tip at y = 1
const material = createFoliageWindMaterial(THREE, {direction: [1, 0.3], strength: 0.25, height: 1});
const grass = new THREE.InstancedMesh(blade, material, 5000);
// ... setMatrixAt for each blade: position on the ground, a random turn about Y, a height scale
scene.add(grass);

function frame(elapsed) {
  material.uniforms.uTime.value = elapsed;
  renderer.render(scene, camera);
}
```

`demo/scene.mjs` renders a meadow of 2,200 tapered blades in a gust.

## Exports

- `createFoliageWindMaterial(THREE, options = {})`: the double-sided `ShaderMaterial`; works on `Mesh` and `InstancedMesh`.
- `foliageWindUniforms(THREE, options = {})`: the uniform values, to share the wind with another material or a probe.
- `windOffset(position, anchor, time, options = {})`: the CPU mirror; the world offset of an object-space vertex on a blade standing at a world anchor.
- `windGustNoise(x)`: the CPU mirror of the gust noise, in [0, 1].
- `FOLIAGE_WIND_DEFAULTS`: the frozen default options.
- `FOLIAGE_WIND_UNIFORMS_GLSL`, `FOLIAGE_WIND_GLSL`: the wind uniforms and functions, to put the same wind in your own shader; `FOLIAGE_WIND_VERTEX`, `FOLIAGE_WIND_FRAGMENT`: the stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| (clock) | `uTime` | float | 0 | | Seconds; set every frame. |
| `direction` | `uWindDirection` | [x, z] | (1, 0.35) | non-zero | Wind direction; normalized. |
| `strength` | `uWindStrength` | number | 0.18 | 0 to 100 | Largest sideways tip offset of the sway, world units. |
| `frequency` | `uWindFrequency` | number | 1.6 | 0 to 100 | Sway speed, radians per second. |
| `spatialFrequency` | `uSpatialFrequency` | number | 0.45 | 0 to 100 | Phase change per world unit along the wind. |
| `gustStrength` | `uGustStrength` | number | 0.6 | 0 to 10 | Gust push as a fraction of strength. |
| `gustScale` | `uGustScale` | number | 0.18 | 0 to 100 | Gust cells per world unit. |
| `gustSpeed` | `uGustSpeed` | number | 0.9 | 0 to 100 | Gust cells per second. |
| `height` | `uBladeHeight` | number | 1 | 0.001 to 10,000 | Tip height in object units. |
| `stiffness` | `uStiffness` | number | 2 | 0.5 to 8 | Height weighting exponent. |
| `rootColor` | `uRootColor` | linear RGB | (0.04, 0.16, 0.035) | | Colour at the root. |
| `tipColor` | `uTipColor` | linear RGB | (0.42, 0.72, 0.18) | | Colour at the tip. |
| `lightDirection` | `uLightDirection` | vector | (0.4, 1, 0.3) | | Direction toward the light. |

## Checks

- `test_foliage_wind_material.mjs`: gust noise and wind offsets equal an independent Python port of the same integer hash and formula (a tip offset of (-0.03413, -0.00065, -0.01195) at time 3.7); over 300 positions and times roots never move, tips move exactly along the wind direction and never rise; the gust noise stays in [0, 1] and is continuous; zero strength is still; the material declares every uniform it sets. Known-wrong control: a wind that bends the whole blade evenly is refused by the root check.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL wind on the GPU for 512 blade positions and heights against `windOffset` (within 1e-4), then renders the meadow and compares it with the same meadow without wind.

## Limits

Stylized, not a simulation: no blade collision, no recovery dynamics, and the bend shears each vertex rather than rotating it, so strong wind stretches blades slightly. Normals are not bent with the blade. Shading is one simple two-sided term; three.js lights, shadows and fog are ignored. Geometry must stand on y = 0 with its tip at y = `height` in object space. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Height-weighted vertex displacement for vegetation
- Travelling layered sine waves along the wind direction
- 1D value noise on PCG-style integer hashes for gusts
- Second-order drop of a sheared tip to keep its length
