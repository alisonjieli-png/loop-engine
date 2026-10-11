# Spherical harmonics light probe from radiance

Projects incoming light (a function of direction, or an equirectangular float image) onto the nine real spherical harmonics of bands 0 to 2, one coefficient per colour channel, summing over a latitude-longitude grid whose cells carry their exact solid angles. From the coefficients it evaluates the diffuse irradiance at any normal with the cosine-lobe factors pi, 2 pi / 3 and pi / 4, and builds a three.js `LightProbe`, whose shader applies the same factors. Coefficients follow three.js's `SphericalHarmonics3` order (1, y, z, x, xy, yz, 3z^2 - 1, xz, x^2 - y^2), so they drop straight into it.

## When to use it

Use it to light a scene softly from a procedural sky without baking, to match ambient light to a time of day, to turn an HDR environment into a few numbers for many objects, and to compute irradiance on the CPU for gameplay or for placing objects in light.

## Use it

```js
import * as THREE from 'three';
import {evaluateIrradiance, projectRadiance, toLightProbe} from './spherical_harmonics_probe.mjs';

const sky = ([x, y, z]) => {
  const up = Math.max(y, 0);
  return [0.25 + 0.55 * up, 0.32 + 0.6 * up, 0.45 + 0.8 * up];
};
const coefficients = projectRadiance(sky);
scene.add(toLightProbe(THREE, coefficients, 1));
const [r, g, b] = evaluateIrradiance(coefficients, [0, 1, 0]);   // light falling on an upward face
```

`demo/scene.mjs` lights three matte spheres with a probe of a sky with a sun lobe and nothing else.

## Exports

- `projectRadiance(radiance, options = {})`: `radiance(direction)` returns `[r, g, b]` for a unit direction (+Y up); the result is a `Float64Array` of 27 values, coefficient by coefficient.
- `projectEquirect(pixels, width, height, channels = 4)`: the same from a `Float32Array` equirectangular image, rows from +Y to -Y, columns in three.js's mapping (`u = atan2(z, x) / 2 pi + 0.5`).
- `evaluateIrradiance(coefficients, normal)`: irradiance `[r, g, b]` at a normal; a Lambert surface of albedo `a` reflects `a * irradiance / pi`.
- `evaluateRadiance(coefficients, direction)`: the band-limited radiance the coefficients reconstruct.
- `shBasis(direction)`: the nine basis values for a unit direction.
- `toLightProbe(THREE, coefficients, intensity = 1)`: a `THREE.LightProbe` holding the coefficients.
- `SH_BASIS`, `SH_COSINE_LOBE`: the basis normalization constants and the per-band convolution factors.
- `SH_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `latitudeSamples` | integer | 64 | 4 to 4096 | Rows of the integration grid. |
| `longitudeSamples` | integer | 128 | 4 to 4096 | Columns of the integration grid. |

## Checks

- `test_spherical_harmonics_probe.mjs`, against closed forms computed independently with Python: the nine basis constants; a constant radiance `L` projects to `c0 = 2 sqrt(pi) L` within 1e-9 with every other coefficient below 1e-3, and gives irradiance `pi L` at every normal; the top light `max(y, 0)` projects to `sqrt(pi) / 2`, 1.0233267, -0.2477080 and -0.4290428 within 1e-3 and gives the band-limited irradiance 2.0780326 at +Y; an equirectangular image projects like the function it samples, and its column u = 0.75 points along +Z. Known-wrong control: a projection without solid-angle weights is refused.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier requires three.js's own `SphericalHarmonics3.getIrradianceAt` to agree with `evaluateIrradiance` within 1e-4 relative, renders matte spheres lit only by the probe, requires the white sphere's top to be clearly brighter than its bottom, and compares the frame with the same scene without the probe.

## Limits

Nine coefficients hold only low-frequency light: sharp suns, shadows and occlusion are lost, and the band-limited result rings, so irradiance can dip slightly below zero opposite a strong light (about -0.016 for a top light). Diffuse only: no specular reflections. The projection is a midpoint sum over a latitude-longitude grid with exact cell solid angles: a constant integrates exactly, other functions within about 1e-3 on the default 64 x 128 grid, and a light smaller than a cell is undersampled. Equirectangular rows must run from +Y to -Y. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Real spherical harmonics of bands 0 to 2
- Irradiance from the cosine-lobe convolution (Ramamoorthi and Hanrahan's irradiance environment maps)
- Latitude-longitude quadrature with exact cell solid angles
