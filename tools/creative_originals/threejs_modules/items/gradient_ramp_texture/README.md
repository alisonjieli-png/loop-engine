# Gradient ramp and toon gradient map textures

Samples colour stops into an RGBA8 ramp. Colours are interpolated in linear light, so the middle of a black-to-white ramp is the even grey 188 rather than the dark 128 a byte-wise blend gives, and red to blue passes through a bright magenta instead of a muddy one. The bytes are stored sRGB-encoded for colour textures or as linear values for data such as `MeshToonMaterial` gradient maps, and the texture builders set the matching three.js colour space and filtering: linear filtering for smooth ramps, nearest for stepped ones.

## When to use it

Use it for colour ramps in custom shaders (heat maps, sky and water depth colours, palette lookups), for `MeshToonMaterial.gradientMap` bands, and anywhere a designer's colour stops must become a texture without a paint tool.

## Use it

```js
import * as THREE from 'three';
import {createGradientTexture, createToonGradientMap, sampleGradient} from './gradient_ramp_texture.mjs';

const sunset = [{position: 0, color: 0x1b1f4a}, {position: 0.45, color: 0xd9465f}, {position: 1, color: 0xfbe6a2}];
const ramp = createGradientTexture(THREE, sunset, {width: 256});          // sRGB colour texture
const bands = createToonGradientMap(THREE, [0.16, 0.52, 1]);              // three toon bands
const toon = new THREE.MeshToonMaterial({color: 0xe8794a, gradientMap: bands});
const [r, g, b] = sampleGradient(sunset, 0.6);                            // linear light, on the CPU
```

`demo/scene.mjs` shades a torus knot and a sphere with the toon bands and shows the sunset ramp as a strip.

## Exports

- `gradientRamp(stops, options = {})`: RGBA8 bytes, `width` texels; texel `i` samples `t = (i + 0.5) / width`.
- `sampleGradient(stops, t, options = {})`: the gradient at `t` as linear-light `[r, g, b, a]`.
- `createGradientTexture(THREE, stops, options = {})`: a `width` x 1 `THREE.DataTexture`, `SRGBColorSpace` for encoding `srgb` and `NoColorSpace` for `linear`, `NearestFilter` in stepped mode, clamped, no mipmaps.
- `createToonGradientMap(THREE, levels)`: a gradient map with one nearest-filtered texel per linear level, darkest first.
- `srgbToLinear(value)`, `linearToSrgb(value)`: the sRGB transfer functions.
- `GRADIENT_DEFAULTS`: the frozen default options.

## Stops and options

Stops are `{position, color}` with positions in [0, 1] that never decrease and colours as `0xRRGGBB` numbers or `[r, g, b]` or `[r, g, b, a]` arrays in [0, 1].

| Option | Type | Default | Values | Meaning |
|---|---|---|---|---|
| `width` | integer | 256 | 1 to 4096 | Texels in the ramp. |
| `mode` | string | `smooth` | `smooth`, `stepped` | Interpolate between stops, or hold each stop until the next. |
| `input` | string | `srgb` | `srgb`, `linear` | How stop colours are read: sRGB-encoded (as colour pickers and hex give them) or already linear. |
| `encoding` | string | `srgb` | `srgb`, `linear` | How bytes are stored: sRGB for colour textures, linear for gradient maps and data. |

Unknown options throw `TypeError`; values out of range throw `RangeError`.

## Checks

- `test_gradient_ramp_texture.mjs`, against values computed independently with Python from the sRGB transfer functions: sRGB 0.5 is linear 0.21404; linear 0.5 encodes as 0.73536 (byte 188); a 3-texel black-to-white ramp is (113, 188, 235); red to blue meets at (188, 0, 188); linear encoding stores 64 and 191 for 0.25 and 0.75; stepped mode holds each stop; the textures carry the right colour space and filters; a toon map of (0.2, 0.55, 1) stores 51, 140 and 255. Known-wrong control: a ramp blended on the sRGB values is refused.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier samples the sRGB ramp texture on the GPU, where three.js decodes it to linear light, and requires every texel to match `sampleGradient` within 0.006; then it renders the toon shapes and the strip and compares them with three.js's built-in two-tone toon shading.

## Limits

Piecewise linear interpolation in linear-light sRGB: no perceptual spaces such as OKLab, no easing between stops and no dithering, so long dark ramps can band in 8 bits. Alpha is interpolated linearly and stored unpremultiplied. The `input` setting applies to hex numbers and arrays alike. The textures are one texel high, without mipmaps. `MeshToonMaterial` reads only the red channel of a gradient map. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- sRGB transfer functions (IEC 61966-2-1)
- Interpolation in linear light
- Stepped gradient maps for toon shading
