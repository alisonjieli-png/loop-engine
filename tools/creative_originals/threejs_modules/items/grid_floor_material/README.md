# Anti-aliased editor grid floor material

A three.js `ShaderMaterial` that draws the ground grid of an editor on a large horizontal plane. For each pixel it measures the distance to the nearest grid line in world units, converts it to pixels with the screen-space derivative of the world coordinate (`fwidth`), and covers the pixel by a smoothstep across one pixel at the line edge. Lines therefore keep the same width on screen near and far, and stay smooth instead of stair-stepped. Minor and major spacings are drawn together, the line along X (z = 0) is red and the line along Z (x = 0) is blue, grids whose cells shrink under about four pixels fade out instead of turning into moire, and the whole grid fades with distance from the camera. The coverage functions have exact CPU mirrors.

## When to use it

Use it for level and scene editors, model and product viewers, debug and measuring views, and any 3D tool where people need a sense of scale and orientation.

## Use it

```js
import * as THREE from 'three';
import {createGridFloorMaterial} from './grid_floor_material.mjs';

const plane = new THREE.PlaneGeometry(1000, 1000);
plane.rotateX(-Math.PI / 2);
const grid = new THREE.Mesh(plane, createGridFloorMaterial(THREE, {minorSpacing: 0.5, majorSpacing: 5, fadeEnd: 60}));
grid.renderOrder = -1;
scene.add(grid);
```

`demo/scene.mjs` renders an editor viewport with three props on the grid; the verifier compares it with the same viewport without the grid.

## Exports

- `createGridFloorMaterial(THREE, options = {})`: the material, transparent, double-sided and without depth write. Options are the keys of `GRID_FLOOR_DEFAULTS`; an unknown key throws `TypeError`, a value out of range `RangeError`.
- `gridLineCoverage(coordinate, spacing, lineWidthPixels, pixelFootprint)`: CPU mirror of the coverage of the nearest line of a grid, for pixels `pixelFootprint` world units wide, including the moire fade.
- `gridAxisCoverage(coordinate, lineWidthPixels, pixelFootprint)`: CPU mirror of the coverage of the axis line through 0.
- `gridFade(distanceToCamera, fadeStart, fadeEnd)`: CPU mirror of the distance fade.
- `GRID_FLOOR_DEFAULTS`: the frozen default options.
- `GRID_FLOOR_GLSL`: the GLSL `gridLineCoverage`, `gridAxisCoverage` and `gridFade`, to reuse in your own shaders.
- `GRID_FLOOR_VERTEX`, `GRID_FLOOR_FRAGMENT`: the two shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `minorSpacing` | `uMinorSpacing` | number | 1 | above 0 | World units between minor lines. |
| `majorSpacing` | `uMajorSpacing` | number | 10 | above 0 | World units between major lines. |
| `minorLineWidth` | `uMinorLineWidth` | number | 1 | 0.01 to 64 | Minor line width in pixels. |
| `majorLineWidth` | `uMajorLineWidth` | number | 1.6 | 0.01 to 64 | Major line width in pixels. |
| `axisLineWidth` | `uAxisLineWidth` | number | 2.2 | 0.01 to 64 | Axis line width in pixels. |
| `minorColor` | `uMinorColor` | colour | (0.33, 0.35, 0.4) | | Minor lines. |
| `majorColor` | `uMajorColor` | colour | (0.55, 0.58, 0.64) | | Major lines. |
| `xAxisColor` | `uXAxisColor` | colour | (0.85, 0.2, 0.2) | | The line along X, where z = 0. |
| `zAxisColor` | `uZAxisColor` | colour | (0.2, 0.4, 0.95) | | The line along Z, where x = 0. |
| `fadeStart` | `uFadeStart` | number | 15 | 0 and up | Camera distance where the fade starts. |
| `fadeEnd` | `uFadeEnd` | number | 45 | at least `fadeStart` | Camera distance where the grid is gone. |
| `opacity` | `uOpacity` | number | 1 | 0 to 1 | Overall opacity. |

## Checks

- `test_grid_floor_material.mjs`: the coverage on a line, between lines, half a pixel off, on negative coordinates, under the moire fade, for a sub-pixel width and for major lines, against values computed independently; axis lines; the distance fade; and the transparency, side, depth write and uniforms the builder sets (with a small stand-in for `THREE`). Known-wrong controls: a grid whose width is measured in world units instead of pixels is refused, and invalid inputs and options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL coverage on the GPU with a known derivative (a coordinate of 40 units across 256 pixels, so `fwidth` is 0.15625), requires the measured derivative to equal it and the line and axis coverage to match the CPU mirrors within 0.002, then renders the viewport and compares it with the same scene without the grid.

## Limits

A flat plane in world x and z: the grid does not follow a curved or tilted mesh, and because it writes no depth it never hides objects below it; place it at the height you want. Line widths come from per-pixel derivatives of world coordinates, so at grazing angles lines blur and the moire fade removes dense lines early. There is no switch to coarser spacings as the camera rises, only the fade. Transparent sorting follows three.js object order. Written for three.js r155 or later; only 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Screen-space line width from `fwidth` of world coordinates
- Distance to the nearest grid line with `fract`
- Cells-per-pixel fade against moire
- Smoothstep fade with distance from the camera
