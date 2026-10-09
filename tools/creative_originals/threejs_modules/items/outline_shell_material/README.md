# Inverted-hull outline with constant pixel width

Ink outlines for three.js meshes by the inverted-hull method. A second mesh shares the original's geometry but draws only back faces, and its vertex stage pushes every vertex along the direction of its normal as seen on screen, by a fixed number of pixels, in clip space. The pushed back faces show as a band around the silhouette while the original mesh hides the rest, and because the push is measured in pixels the band keeps its width near and far. The offset is a small GLSL function with an exact CPU mirror.

## When to use it

Use it for toon and comic styles, selection and hover highlights, readability outlines on characters and props, and any look where silhouettes should read as drawn lines. It works on `InstancedMesh` crowds, where every instance gets its outline from the shared instance matrices.

## Use it

```js
import * as THREE from 'three';
import {createOutlineShell, setOutlineResolution} from './outline_shell_material.mjs';

const hero = new THREE.Mesh(geometry, new THREE.MeshToonMaterial({color: 0xe76f51}));
scene.add(hero);
const size = renderer.getDrawingBufferSize(new THREE.Vector2());
const shell = createOutlineShell(THREE, hero, {width: 3, color: [0.02, 0.02, 0.03], resolution: size.toArray()});

addEventListener('resize', () => {
  renderer.getDrawingBufferSize(size);
  setOutlineResolution(shell.material, size.x, size.y);
});
// hero.remove(shell) takes the outline off again.
```

`demo/scene.mjs` outlines three toon-shaded shapes at 2, 3 and 5 pixels.

## Exports

- `createOutlineShell(THREE, mesh, options = {})`: the hull, added as a child of `mesh` so it follows it; an `InstancedMesh` gets an `InstancedMesh` hull that shares its instance matrices; the hull ignores raycasts.
- `createOutlineMaterial(THREE, options = {})`: the back-face `ShaderMaterial` alone, to build your own hull.
- `setOutlineResolution(material, width, height)`: update `uResolution`.
- `outlineClipOffset(clipPosition, clipNormal, widthPixels, resolution)`: the CPU mirror of the offset.
- `OUTLINE_SHELL_DEFAULTS`: the frozen default options.
- `OUTLINE_GLSL`: the GLSL offset function; `OUTLINE_VERTEX`, `OUTLINE_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `color` | `uColor` | linear RGB | (0.02, 0.02, 0.03) | | Outline colour. |
| `width` | `uWidth` | number | 3 | 0 to 256 | Width in drawing-buffer pixels. |
| `opacity` | `uOpacity` | number | 1 | 0 to 1 | Below 1 the material is transparent. |
| `resolution` | `uResolution` | [w, h] | (1024, 1024) | at least 1 | Drawing buffer size in pixels. |

## Checks

- `test_outline_shell_material.mjs`: the offset worked by hand (0.04 in clip x for 2 pixels on a 200 x 100 buffer at w = 2), a normal facing the camera leaves the vertex in place, and over 500 seeded random clip positions, normals, widths and non-square buffers the offset is exactly `width` pixels long and parallel to the normal in pixels, with depth unchanged; the material draws back faces with the four uniforms; the shell shares the geometry, becomes a child, ignores raycasts and shares instance matrices. Known-wrong control: an offset whose direction is taken in clip units instead of pixels is refused by the direction check.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL offset on the GPU over a 16 x 16 grid against `outlineClipOffset` (within 1e-4), renders a magenta 4-pixel outline around a sphere and requires a 3 to 5 pixel band on all four sides with none over the sphere, then renders the demo and compares it with the same scene without outlines.

## Limits

Stylized. The hull follows the vertex normals, so on hard-edged meshes with split normals it tears open at creases; weld or smooth the normals first. Only silhouettes get a line, not inner creases or intersections. Width is in drawing-buffer pixels, so `uResolution` must follow the renderer on resize and pixel ratio changes. Skinned and morphed meshes are not followed. Each outline is one more draw call. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Inverted hull (back-face shell) outlining
- Clip-space vertex offset along the projected normal for a constant width in pixels
- Inverse-transpose normal matrix for non-uniform scale
