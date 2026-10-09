# Gooch cool-to-warm illustration material

A three.js `ShaderMaterial` in the Gooch technical illustration style. Instead of darkening toward black away from the light, the colour shifts in hue: surfaces facing the light take a warm tone (`warm + beta * base`), surfaces facing away a cool tone (`cool + alpha * base`), and the blend factor is `(1 + N.L) / 2`. Shape stays readable across the whole object, including the side away from the light, and black is kept free for outlines. A white Phong highlight and a dark band where the surface turns edge-on to the camera complete the look. The tone and the band have exact CPU mirrors.

## When to use it

Use it for product diagrams, CAD and engineering previews, assembly and repair guides, scientific and architectural models, and any stylized scene where form matters more than realism.

## Use it

```js
import * as THREE from 'three';
import {createGoochMaterial} from './gooch_shading_material.mjs';

const part = new THREE.Mesh(partGeometry, createGoochMaterial(THREE, {baseColor: [0.25, 0.45, 0.7]}));
scene.background = new THREE.Color(0xeeeae2);
scene.add(part);

// No outline band, stronger cool shift:
const plain = createGoochMaterial(THREE, {silhouetteWidth: 0, alpha: 0.1, coolColor: [0, 0.05, 0.7]});
```

`demo/scene.mjs` renders a torus knot, a turned vase and a capsule on a paper-coloured background; the verifier compares it with the same scene in Lambert shading.

## Exports

- `createGoochMaterial(THREE, options = {})`: the material. Options are the keys of `GOOCH_DEFAULTS`; an unknown key throws `TypeError`, a value out of range `RangeError`.
- `goochColor(nDotL, base, cool, warm, alpha, beta)`: CPU mirror of the tone, a linear RGB triple.
- `goochSilhouette(nDotV, width, softness)`: CPU mirror of the outline band, 1 where `|N.V|` is below `width`, fading to 0 by `width + softness`, and 0 everywhere when `width` is 0.
- `GOOCH_DEFAULTS`: the frozen default options.
- `GOOCH_GLSL`: the GLSL `goochColor` and `goochSilhouette`, to reuse in your own shaders.
- `GOOCH_VERTEX`, `GOOCH_FRAGMENT`: the two shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `baseColor` | `uBaseColor` | colour | (0.75, 0.3, 0.2) | | Object colour mixed into both tones. |
| `coolColor` | `uCoolColor` | colour | (0, 0, 0.55) | | Cool tone, facing away from the light. |
| `warmColor` | `uWarmColor` | colour | (0.3, 0.3, 0) | | Warm tone, facing the light. |
| `alpha` | `uAlpha` | number | 0.25 | 0 to 1 | Share of the base colour in the cool tone. |
| `beta` | `uBeta` | number | 0.5 | 0 to 1 | Share of the base colour in the warm tone. |
| `highlightColor` | `uHighlightColor` | colour | (1, 1, 1) | | Highlight colour. |
| `shininess` | `uShininess` | number | 32 | 1 to 1024 | Phong exponent. |
| `highlightStrength` | `uHighlightStrength` | number | 0.6 | 0 to 4 | Highlight strength; 0 turns it off. |
| `silhouetteWidth` | `uSilhouetteWidth` | number | 0.18 | 0 to 1 | Outline band width in absolute N.V; 0 turns it off. |
| `silhouetteSoftness` | `uSilhouetteSoftness` | number | 0.06 | 0 to 1 | Fade at the inside of the band. |
| `silhouetteColor` | `uSilhouetteColor` | colour | (0.03, 0.03, 0.05) | | Outline colour. |
| `lightDirection` | `uLightDirection` | vector | (0.5, 0.8, 0.4) | | Direction toward the light; normalized. |

## Checks

- `test_gooch_shading_material.mjs`: the tone at the lit pole, the dark pole, the terminator and a tilted case against values computed independently, the band inside, outside and on its fade on both sides of the silhouette and at width 0, and the uniforms the builder sets (with a small stand-in for `THREE`). Known-wrong controls: plain Lambert darkening toward black is refused, and out-of-range inputs, two-component colours, misspelt options and a zero light direction throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL tone and band on the GPU across `N.L` and `N.V` in [-1, 1] and requires them to match the CPU mirrors within 0.00001 and 0.0001, then renders the demo and compares it with Lambert shading.

## Limits

A non-photorealistic illustration model, not physically based. The silhouette is a band in `N.V`, so its screen width varies with curvature (thick where a broad surface turns edge-on, thin on tight curves) and flat faces only get it when seen nearly edge-on; it is not a true outline pass, and creases are not drawn. One light, given as a direction uniform; three.js scene lights, shadows and fog are ignored, and skinned or morphed meshes are not deformed. Tones are linear colours passed through three.js output conversion, so they look lighter than values chosen for display space. Written for three.js r155 or later; only 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Cool-to-warm tone shading (Gooch, Gooch, Shirley and Cohen, 1998)
- Phong reflection highlight
- Facing-ratio silhouette band
