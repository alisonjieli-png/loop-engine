# Depth-texture fog pass with linearized depth

A post-processing pass that adds fog after the scene is rendered. It reads the frame's `DepthTexture`, turns each depth-buffer value back into the distance along the view axis (`near * far / (far - depth (far - near))` for a perspective camera, `near + depth (far - near)` for an orthographic one) and mixes the pixel toward the fog colour by exponential squared fog, `1 - exp(-(density * max(distance - start, 0))^2)`. Because it works on the finished frame, it fogs materials that ignore scene fog (custom shaders, some addons), can start at a distance, and can change density or colour every frame without recompiling materials. Depth linearization, its inverse and the fog have CPU mirrors, and the two GLSL functions are a reusable chunk.

## When to use it

Use it for atmospheric depth in landscapes and cities, underwater and smoke moods, distance cues in data and architecture views, fog that fades in during a cut, or fog over shader materials that do not include three.js's fog chunks.

## Use it

Render the scene into a target that carries a `DepthTexture`, then draw the pass over a full-screen quad:

```js
import * as THREE from 'three';
import {createDepthFogMaterial} from './post_depth_fog.mjs';

const target = new THREE.WebGLRenderTarget(innerWidth, innerHeight, {type: THREE.HalfFloatType});
target.depthTexture = new THREE.DepthTexture(innerWidth, innerHeight);
const fog = createDepthFogMaterial(THREE, {near: camera.near, far: camera.far, density: 0.04, start: 5,
  color: [0.55, 0.62, 0.72]});
fog.uniforms.tDiffuse.value = target.texture;
fog.uniforms.tDepth.value = target.depthTexture;
const screen = new THREE.Scene();
screen.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), fog));
const screenCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

renderer.setAnimationLoop(() => {
  renderer.setRenderTarget(target);
  renderer.render(scene, camera);
  renderer.setRenderTarget(null);
  renderer.render(screen, screenCamera);
});
```

`createDepthFogShader(options)` gives the same pass as a definition for three.js's `ShaderPass` when the scene is already in such a target; set `tDepth` to that target's depth texture. Keep `cameraNear` and `cameraFar` equal to the camera's. `demo/scene.mjs` fogs an avenue of columns.

## Exports

- `createDepthFogShader(options = {})`: a new `{name, uniforms, vertexShader, fragmentShader}` object with `tDiffuse`, `tDepth`, `cameraNear` and `cameraFar`.
- `createDepthFogMaterial(THREE, options = {})`: the definition as a `THREE.ShaderMaterial` with depth test and write off.
- `linearizeDepth(depth, near, far, orthographic = false)`: the view distance of a [0, 1] depth-buffer value.
- `depthFromDistance(distance, near, far, orthographic = false)`: the inverse, the depth-buffer value at a distance.
- `fogFactor(distance, options = {})`: the fog amount at a view distance.
- `applyDepthFogCpu(rgb, depth, options = {})`: the CPU mirror of the whole pass for one pixel.
- `DEPTH_FOG_DEFAULTS`: the frozen default options.
- `DEPTH_FOG_GLSL`: the GLSL chunk with `fogViewDistance` and `fogAmount`.
- `DEPTH_FOG_VERTEX`, `DEPTH_FOG_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| (input) | `tDiffuse` | sampler2D | null | | The frame. |
| (depth) | `tDepth` | sampler2D | null | | The frame's DepthTexture. |
| `near` | `cameraNear` | number | 0.1 | over 0, under `far` | Camera near plane. |
| `far` | `cameraFar` | number | 100 | over `near` | Camera far plane. |
| `orthographic` | `uOrthographic` | boolean | false | | Depth from an orthographic camera. |
| `color` | `uFogColor` | linear RGB | (0.62, 0.7, 0.8) | | Fog colour. |
| `density` | `uDensity` | number | 0.12 | 0 to 10 | Exponential squared density per scene unit. |
| `start` | `uStart` | number | 0 | 0 or more | Distance where fog begins. |

## Checks

- `test_post_depth_fog.mjs`: perspective linearization at depth 0, 1, 0.5 and for a plane six units away, orthographic linearization, round trips through `depthFromDistance` for both cameras, the fog at known distances with and without a start distance, the fogged colour of that plane, all against values computed independently in python3; the shader definition. Known-wrong controls: reading a perspective depth buffer as linear depth is refused, and invalid cameras, depths and options throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier renders a plane six units away into a target with a `DepthTexture` and requires every pixel the pass writes to equal `applyDepthFogCpu` within 0.0001; it renders a tilted plane and requires the GLSL linearization of the depths the GPU read to equal `linearizeDepth` within a relative 0.0001; then it compares the fogged avenue with the same frame at density 0.

## Limits

Fog is uniform in space and follows planar view depth (distance along the camera axis), as three.js's own fog does, not radial distance, height or noise, and light does not scatter through it. The background (depth 1) is fogged as if it sat at the far plane. The WebGL default depth range is assumed: logarithmic depth buffers and reversed depth are not supported. `cameraNear` and `cameraFar` must match the camera that rendered the depth, and transparent objects that write no depth are fogged by what lies behind them. The output goes through three.js's output colour space conversion. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Inverting the perspective depth mapping, `d = far (z - near) / (z (far - near))`
- Exponential squared fog with a start distance
- Fog as a full-screen pass over a depth texture
