# Noise dissolve material with a burning edge

A double-sided three.js `ShaderMaterial` that eats a mesh away. Each fragment samples fractal value noise at its object-space position; below `uThreshold` it is discarded, and in a thin band just above the threshold it glows in the edge colour, so a burning front crawls across the surface as the threshold rises from 0 (whole) to 1 (gone). The noise is built on a 32-bit integer hash of the lattice coordinates rather than a sine trick, so the GLSL and the JavaScript mirror compute the same field: tools can predict which parts survive a given threshold.

## When to use it

Use it for spawning and despawning characters and props, teleports, burning paper or cloth, disintegration, magic reveals and build-up effects.

## Use it

```js
import * as THREE from 'three';
import {createNoiseDissolveMaterial, fbm3} from './noise_dissolve_material.mjs';

const material = createNoiseDissolveMaterial(THREE, {color: 0xb0b4bc, edgeColor: [1, 0.45, 0.1], noiseScale: 2});
const statue = new THREE.Mesh(statueGeometry, material);
scene.add(statue);

renderer.setAnimationLoop((time) => {
  material.uniforms.uThreshold.value = 0.5 + 0.5 * Math.sin(time / 1500);
  renderer.render(scene, camera);
});

// On the CPU: is the vertex at (x, y, z) already gone at threshold 0.6? (object space, times noiseScale)
const gone = fbm3(2 * x, 2 * y, 2 * z, 4, 7) < 0.6;
```

`demo/scene.mjs` renders a torus knot and a sphere half dissolved with two edge colours.

## Exports

- `createNoiseDissolveMaterial(THREE, options = {})`: the material, double-sided so the inside shows through the holes. Options are the keys of `NOISE_DISSOLVE_DEFAULTS`; an unknown key throws `TypeError`, a value out of range `RangeError`.
- `valueNoise3(x, y, z, seed = 0)`: CPU mirror of the GLSL value noise, in [0, 1).
- `fbm3(x, y, z, octaves = 4, seed = 0)`: CPU mirror of the fractal sum (each octave at twice the frequency, half the amplitude and the next seed), normalized to [0, 1).
- `dissolveEdge(noise, threshold, edgeWidth)`: CPU mirror of the burn band: 1 at the front, 0 from `threshold + edgeWidth` on, and 0 while the threshold is 0.
- `isDissolved(noise, threshold)`: whether the shader discards a fragment with that noise value.
- `NOISE_DISSOLVE_DEFAULTS`: the frozen default options.
- `NOISE_DISSOLVE_GLSL`: the GLSL hash, `valueNoise3`, `fbm3` and `dissolveEdge`, to reuse in your own shaders.
- `NOISE_DISSOLVE_VERTEX`, `NOISE_DISSOLVE_FRAGMENT`: the two shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `color` | `uColor` | colour | (0.72, 0.74, 0.78) | | Lit surface colour. |
| `threshold` | `uThreshold` | number | 0.45 | 0 to 1 | Noise level below which fragments vanish. |
| `edgeWidth` | `uEdgeWidth` | number | 0.06 | 0 to 1 | Width of the glowing band, in noise units. |
| `edgeColor` | `uEdgeColor` | colour | (1, 0.42, 0.08) | | Colour of the front. |
| `edgeIntensity` | `uEdgeIntensity` | number | 3 | 0 to 32 | Brightness of the front; above 1 suits bloom. |
| `noiseScale` | `uNoiseScale` | number | 2.5 | 0.001 to 1000 | Noise frequency per object-space unit. |
| `octaves` | `uOctaves` | integer | 4 | 1 to 8 | More octaves give a more ragged front. |
| `seed` | `uSeed` | integer | 7 | 0 to 16777215 | Picks a different noise field. |
| `lightDirection` | `uLightDirection` | vector | (0.4, 0.8, 0.45) | | Direction toward the light; normalized. |
| `ambient` | `uAmbient` | number | 0.3 | 0 to 1 | Share of the colour lit without the light. |

## Checks

- `test_noise_dissolve_material.mjs`: value noise and fractal noise at seven points against values computed independently from a Python transcription of the same hash, lattice and interpolation; continuity across cell borders; the [0, 1) range; the edge at the front, inside and at threshold 0; and the uniforms and double side the builder sets (with a small stand-in for `THREE`). Known-wrong controls: linear interpolation between the same lattice values is refused, and a misspelt option, fractional octaves and seeds, and out-of-range values throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL value noise, fractal noise and edge on the GPU at 1,024 points, including negative coordinates, and requires the noise to match the CPU mirror within 0.00001 and the edge within 0.001, then renders the demo and compares it with the same scene at threshold 0.

## Limits

Value noise, not gradient noise: at low octave counts its blobs line up with the lattice axes. The noise lives in object space, so the pattern sticks to the mesh and stretches with non-uniform scale, and coordinates must stay below 2^20 in magnitude. Discarded fragments leave real holes, but three.js shadow maps and depth passes use their own materials and still see the whole mesh. The edge is plain emission, not fire or particles. Lit by one direction uniform; scene lights, shadows and fog are ignored. Requires WebGL 2 for unsigned integers in GLSL. Written for three.js r155 or later; only 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- A 32-bit integer hash (xor-shift and multiply rounds, lowbias32 style) of the lattice coordinates, offset by 2^20 to stay unsigned
- Value noise with quintic interpolation, `6t^5 - 15t^4 + 10t^3`
- Fractal Brownian motion with lacunarity 2 and gain 0.5
- Alpha-test dissolve with a smoothstep burn band
