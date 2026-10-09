# Hologram material with scanlines, flicker and glitch bands

A three.js `ShaderMaterial` that turns any mesh into a projected hologram. Horizontal scanlines run through the object in world space and scroll with time; a facing-ratio edge brightens the silhouette; the whole projection dims in random steps (flicker); and every so often a few horizontal bands of the mesh jump sideways in the vertex stage (glitch). It draws additively, transparent and double-sided, so overlapping parts glow brighter. Flicker and glitch come from a 32-bit integer hash rather than a sine trick, so the JavaScript mirrors predict exactly which bands jump and how far.

## When to use it

Use it for sci-fi displays and map tables, projected characters and messages, ghosts and spirits, scanned or loading objects, and UI elements in 3D scenes.

## Use it

```js
import * as THREE from 'three';
import {createHologramMaterial, glitchOffset} from './hologram_scanline_material.mjs';

const material = createHologramMaterial(THREE, {color: 0x40d8ff, scanDensity: 24, glitchChance: 0.2});
const figure = new THREE.Mesh(figureGeometry, material);
scene.add(figure);

renderer.setAnimationLoop((time) => {
  material.uniforms.uTime.value = time / 1000;
  renderer.render(scene, camera);
});

// The same offset on the CPU, for example to jitter a label beside the figure in step with it:
const shift = glitchOffset(labelHeight, time / 1000, 6, 4, 0.2, 0.06, 3);
```

`demo/scene.mjs` renders a hologram of a torus knot and a crystal over a projector disc at a moment when glitch bands are displaced.

## Exports

- `createHologramMaterial(THREE, options = {})`: the material, additive, transparent, without depth write and double-sided. Options are the keys of `HOLOGRAM_DEFAULTS`; an unknown key throws `TypeError`, a value out of range `RangeError`.
- `scanlineIntensity(height, time, density, speed, sharpness)`: CPU mirror of the scanline profile, `(0.5 + 0.5 cos(2 pi (height * density - time * speed)))^sharpness`.
- `hologramFlicker(time, rate, depth, seed)`: CPU mirror of the flicker factor, held for each `1 / rate` seconds.
- `glitchOffset(height, time, bands, rate, chance, strength, seed)`: CPU mirror of the sideways offset of the band that holds a height at a time.
- `HOLOGRAM_DEFAULTS`: the frozen default options.
- `HOLOGRAM_GLSL`: the GLSL hash, `scanlineIntensity`, `hologramFlicker` and `glitchOffset`, to reuse in your own shaders.
- `HOLOGRAM_VERTEX`, `HOLOGRAM_FRAGMENT`: the two shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `color` | `uColor` | colour | (0.25, 0.85, 1) | | Hologram colour. |
| `scanDensity` | `uScanDensity` | number | 30 | 0 to 1000 | Scanlines per world unit of height. |
| `scanSpeed` | `uScanSpeed` | number | 0.5 | -100 to 100 | Lines passing a point per second. |
| `scanSharpness` | `uScanSharpness` | number | 6 | 0.1 to 64 | Higher gives thinner lines. |
| `baseGlow` | `uBaseGlow` | number | 0.25 | 0 to 1 | Brightness between lines. |
| `fresnelPower` | `uFresnelPower` | number | 2 | 0.1 to 16 | Edge glow exponent. |
| `fresnelStrength` | `uFresnelStrength` | number | 1.2 | 0 to 8 | Edge glow strength. |
| `flickerRate` | `uFlickerRate` | number | 12 | 0 to 120 | Flicker steps per second. |
| `flickerDepth` | `uFlickerDepth` | number | 0.25 | 0 to 1 | Largest dimming of a step. |
| `glitchBands` | `uGlitchBands` | number | 6 | 0 to 1000 | Glitch bands per world unit of height. |
| `glitchRate` | `uGlitchRate` | number | 4 | 0 to 120 | Glitch pattern changes per second. |
| `glitchChance` | `uGlitchChance` | number | 0.12 | 0 to 1 | Share of bands displaced at a time. |
| `glitchStrength` | `uGlitchStrength` | number | 0.06 | 0 to 10 | Largest sideways shift in world units. |
| `opacity` | `uOpacity` | number | 0.9 | 0 to 1 | Alpha scale of the additive output. |
| | `uTime` | number | 0 | | Seconds; set it every frame. |
| `seed` | `uSeed` | integer | 3 | 0 to 16777215 | Picks another flicker and glitch sequence. |

## Checks

- `test_hologram_scanline_material.mjs`: the scanline profile on and between lines and its scroll speed, the flicker and glitch values at seven inputs against values computed independently from a Python transcription of the same hash, a glitch that holds within a band and time step and stays within its strength, and the blending, transparency, depth write, side and uniforms the builder sets (with a small stand-in for `THREE`). Known-wrong controls: shifted band keys and a shifted flicker seed are refused, and invalid inputs and options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL scanline, glitch and flicker functions on the GPU at 1,024 points and requires them to match the CPU mirrors within 0.001, 0.000001 and 0.000001, then renders the demo and compares it with plain additive colour.

## Limits

Stylized, not a physical light field: additive blending only brightens, so the hologram vanishes over white backgrounds, and transparent sorting follows three.js object order. Scanlines are horizontal world-space bands; they do not follow the screen or the surface. Glitch offsets move whole vertices sideways, so coarse meshes shear in steps and a band edge never splits a triangle. The edge term needs smooth normals. Nothing animates until `uniforms.uTime` is updated. Requires WebGL 2 for unsigned integers in GLSL. Written for three.js r155 or later; only 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Raised-cosine scanline profile scrolled by time
- A 32-bit integer hash (lowbias32 style) for flicker steps and glitch band keys
- Facing-ratio edge glow with additive blending
