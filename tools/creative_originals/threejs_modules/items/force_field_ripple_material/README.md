# Force-field shield with impact ripples

An energy-shield material for three.js. The shell glows faintly everywhere, brighter toward its edge through a Fresnel-style facing-ratio term, and blends additively over whatever is behind it. Each hit starts a ring: a Gaussian band whose radius grows at `rippleSpeed` from the hit point and whose brightness falls with the square of its remaining life. Up to eight hits live in two uniform arrays; `addHit` writes the next slot of a ring buffer, so a ninth hit replaces the oldest. The ring formula is a small GLSL function with an exact CPU mirror.

## When to use it

Use it for sci-fi shields and barriers, bubble domes, magic wards, protective auras and as hit feedback on any mesh that should show where it was struck.

## Use it

```js
import * as THREE from 'three';
import {addHit, createForceFieldMaterial} from './force_field_ripple_material.mjs';

const material = createForceFieldMaterial(THREE, {color: [0.25, 0.62, 1], doubleSided: true});
const shield = new THREE.Mesh(new THREE.SphereGeometry(1.4, 96, 48), material);
ship.add(shield);

function onProjectileHit(worldPoint, elapsed) {
  addHit(material, shield.worldToLocal(worldPoint.clone()), elapsed);   // the point in the shield's own space
}
function frame(elapsed) {
  material.uniforms.uTime.value = elapsed;
  renderer.render(scene, camera);
}
```

`demo/scene.mjs` shows a ship inside a shield struck three times.

## Exports

- `createForceFieldMaterial(THREE, options = {})`: the transparent, additive `ShaderMaterial` (depth write off).
- `addHit(material, point, time)`: record a hit at `point` (`[x, y, z]` or a `Vector3`, in the mesh's own space) at `time` on the `uTime` clock; returns the slot written.
- `clearHits(material)`: forget every hit.
- `rippleIntensity(distanceFromHit, age, options = {})`: the CPU mirror of one ring's brightness.
- `FORCE_FIELD_DEFAULTS`: the frozen default options; `FORCE_FIELD_MAX_HITS`: 8.
- `FORCE_FIELD_GLSL`: the GLSL ring function; `FORCE_FIELD_VERTEX`, `FORCE_FIELD_FRAGMENT`: the shader stages.

## Options and uniforms

| Option | Uniform | Type | Default | Range | Effect |
|---|---|---|---|---|---|
| `color` | `uColor` | linear RGB | (0.25, 0.62, 1) | | Shield colour. |
| `hitColor` | `uHitColor` | linear RGB | (1, 0.82, 0.42) | | Colour the rings shift toward. |
| `baseAlpha` | `uBaseAlpha` | number | 0.04 | 0 to 1 | Glow over the whole surface. |
| `fresnelPower` | `uFresnelPower` | number | 3 | 0.1 to 16 | Edge exponent; higher is thinner. |
| `fresnelStrength` | `uFresnelStrength` | number | 0.85 | 0 to 8 | Edge brightness. |
| `rippleSpeed` | `uRippleSpeed` | number | 1.6 | 0 to 1000 | Ring spread in mesh units per second. |
| `rippleWidth` | `uRippleWidth` | number | 0.12 | 0.0001 to 1000 | Ring width in mesh units. |
| `rippleLifetime` | `uRippleLifetime` | number | 1.4 | 0.001 to 1000 | Seconds a ring lasts. |
| `rippleStrength` | `uRippleStrength` | number | 1.4 | 0 to 16 | Ring brightness at the start. |
| `doubleSided` | (side) | boolean | false | | Also draw the far side. |
| | `uTime` | float | 0 | | The clock; set it every frame. |
| | `uHitPoints` | vec3[8] | zeros | | Hit points, written by `addHit`. |
| | `uHitTimes` | float[8] | -1e6 | | Hit times, written by `addHit`. |

## Checks

- `test_force_field_ripple_material.mjs`: ring brightness equals an independent Python port at six points (0.94464 on the ring at 0.25 s, 0.34751 one width outside it, 1.4 at the moment of impact, zero after the lifetime and before the hit); the ring's peak sits at `speed * age`, it is nearly dark just before the end of its life and never brighter than its strength; the material is additive, transparent and declares every uniform; `addHit` fills eight slots oldest first and accepts `Vector3`-like points; `clearHits` empties them. Known-wrong control: a ring that never fades is refused by the lifetime check.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier evaluates the GLSL ring function on the GPU over 1,024 distance and age pairs against `rippleIntensity` (within 1e-4), checks the ring buffer in the browser, then renders the struck shield and compares it with the same shield without hits.

## Limits

Stylized, not a physical simulation. The ring distance is the straight-line distance in the mesh's own space, which follows the surface only approximately (on a sphere the chord is shorter than the arc) and lets rings jump across thin parts of concave meshes. Eight hits at most. Hits are stored in mesh space, so a scaled mesh scales its rings. Additive blending washes out on bright backgrounds. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Facing-ratio (Fresnel-style) edge glow
- Gaussian ring travelling at constant speed with a quadratic fade
- Ring buffer of uniform arrays for recent events
