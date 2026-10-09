# Toon band shading material

A three.js `ShaderMaterial` that cel-shades a mesh. The Lambert term `N.L` is cut into a fixed number of lit bands above a shadow band, each edge softened over a small width so it does not alias. A Blinn half-vector term thresholded into a hard spot adds a specular highlight, and a facing-ratio rim lights the silhouette on the lit side. The band function exists twice, as GLSL and as an exact JavaScript mirror, so tools and tests can predict the shaded level of any surface.

## When to use it

Use it for stylized characters, props, toys and game scenes where a few flat tones read better than smooth shading. Pair it with an outline pass or an inverted-hull outline for an ink look.

## Use it

Copy `toon_band_material.mjs` into your project and pass your three.js namespace in:

```js
import * as THREE from 'three';
import {createToonBandMaterial, toonLightDirection} from './toon_band_material.mjs';

const material = createToonBandMaterial(THREE, {
  bands: 3,
  color: 0xe07040,
  lightDirection: toonLightDirection([4, 6, 3]),
});
scene.add(new THREE.Mesh(new THREE.TorusKnotGeometry(1, 0.3, 160, 24), material));

// Later: follow a moving light or change the look through the uniforms.
material.uniforms.uLightDirection.value.set(...toonLightDirection(light.position.toArray(), light.target.position.toArray()));
material.uniforms.uBands.value = 4;
```

`demo/scene.mjs` is the scene the verifier renders: a torus knot and a sphere with two settings of the material.

## Exports

- `createToonBandMaterial(THREE, options = {})`: the material. Options are the keys of `TOON_BAND_DEFAULTS`; an unknown key throws `TypeError` and an out-of-range value throws `RangeError`.
- `toonBandLevel(nDotL, bands, softness)`: CPU mirror of the band function; the lit level in [0, 1] for a Lambert term in [-1, 1]. Edges sit at `k / bands` for `k = 0 .. bands - 1`, so 3 bands give the levels 0, 1/3, 2/3 and 1.
- `toonLightDirection(lightPosition, targetPosition = [0, 0, 0])`: the unit vector from the target toward the light.
- `TOON_BAND_DEFAULTS`: the frozen default options.
- `TOON_BAND_GLSL`: the GLSL band function, to reuse in your own shaders.
- `TOON_BAND_VERTEX`, `TOON_BAND_FRAGMENT`: the two shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `color` | `uColor` | colour | (0.85, 0.42, 0.26) | | Lit colour. Arrays are linear RGB; hex numbers and CSS strings follow three.js colour management. |
| `shadowColor` | `uShadowColor` | colour | (0.16, 0.11, 0.2) | | Colour of the unlit band. |
| `bands` | `uBands` | integer | 3 | 1 to 16 | Lit bands above the shadow. |
| `softness` | `uSoftness` | number | 0.03 | 0 to 0.5 | Half width of each band edge, in Lambert units. |
| `lightDirection` | `uLightDirection` | vector | (0.55, 0.75, 0.35) | | Direction toward the light in world space; normalized. |
| `specularColor` | `uSpecularColor` | colour | (1, 0.97, 0.9) | | Colour of the specular spot. |
| `specularSize` | `uSpecularSize` | number | 0.06 | 0 to 1 | Spot size as 1 - cos of its angular radius; 0 turns it off. |
| `rimColor` | `uRimColor` | colour | (1, 0.88, 0.76) | | Colour of the rim. |
| `rimWidth` | `uRimWidth` | number | 0.22 | 0 to 1 | Rim width in facing-ratio units. |
| `rimStrength` | `uRimStrength` | number | 0.55 | 0 to 4 | Rim intensity; 0 turns it off. |

## Checks

- `test_toon_band_material.mjs` checks the band levels at band centres, that the level never decreases, the light direction helper and the uniforms the builder makes (with a small stand-in for `THREE`). Known-wrong controls: a floor-quantized band function without the shadow edge is refused, and a misspelt option, an out-of-range value and a two-component colour throw.
- `test_contract.mjs` checks the exports, the contract examples and that every uniform is declared in the GLSL.
- The verifier evaluates the GLSL band function on the GPU across a 128 x 1 float target and requires it to match `toonBandLevel` within 0.001, then renders the demo and compares it with the same meshes in flat colour.

## Limits

Stylized, not physically based. One directional light, given as a direction uniform: three.js scene lights, shadows, fog and environment maps are ignored. Specular and rim are thresholded tricks without energy conservation. Skinned and morphed meshes are not deformed (the vertex stage reads `position` and `normal` only); `InstancedMesh` works. Normals use an inverse-transpose per vertex, so non-uniform scale shades correctly at the cost of a matrix inverse per vertex. Written for three.js r155 or later (the fragment stage includes `tonemapping_fragment` and `colorspace_fragment`); only 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2. Hardware GPUs, other browsers and WebGPU were not run.

## Technique

- Lambert term quantized into bands with smoothstep edges
- Blinn half-vector specular thresholded into a spot
- Facing-ratio rim mask, gated to the lit side
