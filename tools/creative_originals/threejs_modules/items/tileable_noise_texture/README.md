# Seamless tileable fBm noise textures

Gradient noise on an integer lattice that wraps every `period` cells: the gradient at each lattice point comes from an integer hash of the wrapped point and the seed, blended with a quintic fade, so the field repeats exactly. Octaves double the frequency and the lattice period together and are summed with a gain (fractal Brownian motion), which keeps the sum periodic over the base period. Sampling one period on a grid therefore gives a texture that tiles without a seam, as a `Float32Array`, as RGBA8 bytes (grey, or four independent fields) or as a repeat-wrapped three.js `DataTexture`. The hash uses `Math.imul`, so every JavaScript engine gives the same bytes.

## When to use it

Use it for terrain and rock detail, clouds and smoke, marble and wood grain through a colour ramp, dissolve and wipe masks, wind and wobble in shaders, and any material that repeats across a large surface.

## Use it

```js
import * as THREE from 'three';
import {createNoiseTexture, fbmNoise} from './tileable_noise_texture.mjs';

const noise = createNoiseTexture(THREE, 256, 256, {period: 8, octaves: 5, gain: 0.55, seed: 3});
noise.repeat.set(4, 4);
const rock = new THREE.MeshStandardMaterial({color: 0xd8b98c, map: noise, bumpMap: noise, bumpScale: 3});

const height = fbmNoise(x, z, {period: 8, octaves: 4});   // the same field on the CPU, e.g. for placement
```

`demo/scene.mjs` tiles one period three by three across a sandstone slab.

## Exports

- `periodicGradientNoise(x, y, period, seed = 1)`: one octave in [-1, 1]; zero at lattice points; `f(x + period, y) = f(x, y)`.
- `fbmNoise(x, y, options = {})`: the octave sum divided by its total amplitude, in [-1, 1], repeating every `period`.
- `noiseField(width, height, options = {})`: one period sampled at texel centres, `(i + 0.5) * period / width`; row 0 at v = 0.
- `noiseTextureData(width, height, options = {})`: RGBA8 bytes mapped from [-1, 1]; `channels: 'rgba'` gives four independent fields (seeds `seed`, `seed + 101`, `seed + 202`, `seed + 303`).
- `createNoiseTexture(THREE, width, height, options = {})`: a repeat-wrapped, mipmapped `THREE.DataTexture` of linear data.
- `latticeHash(x, y, seed)`: the 32-bit hash behind the gradients.
- `NOISE_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `period` | integer | 8 | 1 to 4096 | Lattice cells per tile at the base octave; more cells give finer features. |
| `octaves` | integer | 4 | 1 to 12 | Layers; each doubles frequency and lattice period. |
| `gain` | number | 0.5 | (0, 1] | Amplitude ratio between octaves. |
| `seed` | integer | 1 | | Selects the gradients; octave `k` uses `seed + k`. |
| `channels` | string | `grey` | `grey`, `rgba` | One field in RGB, or four independent fields. |

Unknown options throw `TypeError`; values out of range throw `RangeError`.

## Checks

- `test_tileable_noise_texture.mjs`: hashes, noise values, fBm values and the first texture byte equal those of an independent Python port of the same construction; the noise is zero at lattice points, periodic in both directions for representable coordinates, within [-1, 1] over 4,000 samples with real contrast, and seeded; the texture's wrap neighbours equal its opposite columns. Known-wrong control: noise whose lattice does not wrap fails the periodicity check.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier samples a 32 x 32 texture twice across a 64 x 32 float target: the two copies must be identical (repeat wrapping) and equal to the CPU bytes; then it renders the tiled slab and compares it with the plain slab.

## Limits

Classic gradient noise with eight gradient directions: it shows faint axis-aligned and diagonal structure and is not isotropic like simplex noise. The range is [-1, 1] by construction but most values fall well inside it, so textures look mid-grey without contrast stretching. Periodicity is exact only for representable coordinates (texel centres of power-of-two sizes); elsewhere it holds within rounding. Generated on the CPU, about width x height x octaves noise evaluations, so large textures take time; there is no GPU version and no 3D or animated noise. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Gradient noise with a quintic fade on a wrapped integer lattice
- Fractal Brownian motion with doubling lattice periods
- Integer avalanche hashing with `Math.imul`
