# Gradient sky dome material with sun disc and halo

A three.js `ShaderMaterial` for a sky dome: a large sphere drawn from the inside, without depth write, behind everything else. The colour depends only on the view direction. Above the horizon it runs from `horizonColor` to `zenithColor` along a power curve of the elevation's sine; below, from `horizonColor` to `groundColor`; and a smoothstep blends the two across the horizon. A sun disc of a given angular radius, with a soft edge, and a cosine-power halo are added on top. The same colour has an exact CPU mirror, so fog, hemisphere light, UI and loading screens can be matched to the sky, and a helper turns elevation and azimuth angles into the sun direction.

## When to use it

Use it for outdoor scenes, games and toy worlds, product and architecture shots that need a calm backdrop, day-to-dusk mood changes, and anywhere an HDR environment map would be too heavy.

## Use it

```js
import * as THREE from 'three';
import {createSkyDomeMaterial, skyColor, sunDirectionFromAngles} from './gradient_sky_dome_material.mjs';

const sunDirection = sunDirectionFromAngles(12, -30);
const sky = new THREE.Mesh(new THREE.SphereGeometry(400, 64, 32), createSkyDomeMaterial(THREE, {
  horizonColor: [0.95, 0.6, 0.35], zenithColor: [0.08, 0.16, 0.42], sunDirection,
}));
scene.add(sky);

// Match the light and the fog to the sky.
const sun = new THREE.DirectionalLight(0xffe0b0, 3);
sun.position.set(...sunDirection.map((value) => value * 100));
scene.fog = new THREE.Fog(new THREE.Color(...skyColor([1, 0, 0], {horizonColor: [0.95, 0.6, 0.35]})), 50, 380);
renderer.setAnimationLoop(() => { sky.position.copy(camera.position); renderer.render(scene, camera); });
```

`demo/scene.mjs` renders an evening sky with a low sun over dark hills; the verifier compares it with a flat horizon colour.

## Exports

- `createSkyDomeMaterial(THREE, options = {})`: the material, rendering back faces with no depth write and no fog. Options are the keys of `SKY_DOME_DEFAULTS`; an unknown key throws `TypeError`, a value out of range `RangeError`.
- `skyColor(direction, options = {})`: CPU mirror, the linear RGB colour seen in a direction of any length, sun and halo included.
- `sunDirectionFromAngles(elevationDegrees, azimuthDegrees)`: the unit direction for an elevation above the horizon and an azimuth measured from -Z (three.js's default forward) toward +X.
- `SKY_DOME_DEFAULTS`: the frozen default options.
- `SKY_DOME_GLSL`: the GLSL `skyGradient` and `skySun`, to reuse in your own shaders (for example to tint fog or water by the sky).
- `SKY_DOME_VERTEX`, `SKY_DOME_FRAGMENT`: the two shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `zenithColor` | `uZenithColor` | linear RGB | (0.12, 0.3, 0.68) | | Straight up. |
| `horizonColor` | `uHorizonColor` | linear RGB | (0.62, 0.74, 0.86) | | At the horizon. |
| `groundColor` | `uGroundColor` | linear RGB | (0.16, 0.15, 0.14) | | Straight down. |
| `skyExponent` | `uShape.x` | number | 0.8 | 0.05 to 16 | Curve above the horizon; below 1 keeps the horizon colour low. |
| `groundExponent` | `uShape.y` | number | 0.6 | 0.05 to 16 | Curve below the horizon. |
| `horizonSoftness` | `uShape.z` | number | 0.04 | 0 to 1 | Half width of the horizon blend, in sine of elevation. |
| `sunDirection` | `uSunDirection` | vector | (0.35, 0.18, -0.92) | | Toward the sun; normalized. |
| `sunColor` | `uSunColor` | linear RGB | (1, 0.86, 0.62) | | Disc and halo colour. |
| `sunAngularRadius` | `uSunDisc.x` (cosine) | degrees | 1.2 | 0 to 45 | Radius of the full disc. |
| `sunEdgeSoftness` | `uSunDisc.y` (cosine) | degrees | 0.4 | 0.01 to 45 | Width of the disc edge. |
| `sunIntensity` | `uSunDisc.z` | number | 12 | 0 to 1000 | Disc brightness. |
| `haloSharpness` | `uSunDisc.w` | number | 64 | 1 to 4096 | Halo exponent; higher is tighter. |
| `haloStrength` | `uHaloStrength` | number | 0.35 | 0 to 100 | Halo brightness. |

## Checks

- `test_gradient_sky_dome_material.mjs`: the colour straight up, at the horizon, straight down, at the default sun, at a pointed sun and in between, against values computed independently; the sun angle helper; and the side, depth write, fog flag and packed disc the builder sets (with a small stand-in for `THREE`). Known-wrong controls: a linear elevation gradient without the horizon blend is refused, and a zero direction, unknown options, a zero edge, hex colours and a zero exponent throw.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL sky on the GPU for all 2,048 directions of a 64 x 32 equirectangular grid, with a large sun so the disc edge spans several samples, and requires the colour to match the CPU mirror within 0.1 percent; then renders the evening scene and compares it with a flat horizon colour.

## Limits

A stylized gradient, not atmospheric scattering: colours do not change with sun elevation by themselves, there are no clouds, stars or moon, and the halo is a cosine power, not Mie scattering. It does not light the scene; match a `DirectionalLight`, fog or hemisphere light to it yourself. The dome is a mesh, so keep it inside the camera's far plane and centred near the camera; it is not an environment map for reflections. Colours are linear RGB triples only. Written for three.js r155 or later; only 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Power-curve gradients from the horizon to the zenith and to the ground
- Smoothstep horizon blend in sine of elevation
- Sun disc by smoothstep on the cosine of the angle to the sun, cosine-power halo
