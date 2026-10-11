# Stateless GPU particle fountain

A particle system that keeps no state. Each particle is one point with two attributes, a seed and a birth offset; the vertex stage works out where it is from those and the time uniform alone. A particle loops over its lifetime, and on every loop it draws fresh random numbers from an integer hash of its seed, the loop number and a channel: a launch direction uniform over a cone around +Y, a speed, a spawn point on a disc. It then flies ballistically under gravity, its position swirls about the Y axis with age, and it grows or shrinks and fades in and out over its life. Birth offsets follow the golden ratio, so particles leave evenly instead of in bursts, and the system starts already full. Nothing is uploaded per frame except the time, and the whole computation has an exact CPU mirror.

## When to use it

Use it for fountains, sparks, embers, magic auras, exhaust and ambient motes: effects with thousands of particles that follow a fixed recipe and must cost nothing on the CPU. The CPU mirror tells you where any particle is, for example to place a light or sync a sound.

## Use it

```js
import * as THREE from 'three';
import {createParticlePoints} from './stateless_gpu_particles.mjs';

const size = renderer.getDrawingBufferSize(new THREE.Vector2());
const pointScale = size.y / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2));
const sparks = createParticlePoints(THREE, {count: 5000, lifetime: 2.5, coneAngle: 0.3, pointScale});
scene.add(sparks);

function frame(elapsed) {
  sparks.material.uniforms.uTime.value = elapsed;
  renderer.render(scene, camera);
}
```

Move, rotate or scale the `Points` object to place the emitter; the motion is in its own space. `demo/scene.mjs` renders a fountain of 4,000 sparks.

## Exports

- `createParticlePoints(THREE, options = {})`: a `THREE.Points` with the geometry and the material.
- `createParticleGeometry(THREE, options = {})`: `count` particles with `position` (zeros), `aSeed` (the index) and `aBirth`, and a bounding sphere that holds every path, so frustum culling works.
- `createParticleMaterial(THREE, options = {})`: the additive `ShaderMaterial` (transparent, no depth write).
- `particleState(index, time, options = {})`: the CPU mirror, `{position, life, size, alpha, cycle}`.
- `particleBirth(index, lifetime = 2.5)`: the birth offset of a particle as the attribute stores it.
- `GPU_PARTICLES_DEFAULTS`: the frozen default options.
- `PARTICLE_UNIFORMS_GLSL`, `PARTICLE_GLSL`: the uniforms and functions, to evaluate particles in your own shader; `PARTICLE_VERTEX`, `PARTICLE_FRAGMENT`: the stages.

## Options and uniforms

| Option | Uniform | Default | Range | Effect |
|---|---|---|---|---|
| (clock) | `uTime` | 0 | | Seconds; set every frame. |
| `count` | (geometry) | 2000 | 1 to 4,194,304 | Particles. |
| `lifetime` | `uLifetime` | 2.5 | 0.01 to 10,000 | Seconds per loop. |
| `coneAngle` | `uConeAngle` | 0.35 | 0 to pi | Launch cone half angle around +Y. |
| `speedMin` | `uSpeedMin` | 1.8 | 0 to `speedMax` | Slowest launch. |
| `speedMax` | `uSpeedMax` | 3.2 | `speedMin` up | Fastest launch. |
| `gravity` | `uGravity` | (0, -2.4, 0) | | Constant acceleration. |
| `swirl` | `uSwirl` | 0.8 | -100 to 100 | Radians per second about Y. |
| `emitterRadius` | `uEmitterRadius` | 0.15 | 0 up | Spawn disc radius on y = 0. |
| `startSize` | `uStartSize` | 0.18 | 0 up | Size at birth, world units. |
| `endSize` | `uEndSize` | 0.04 | 0 up | Size at the end of life. |
| `fadeIn` | `uFadeIn` | 0.08 | 0.001 to 1 | Fraction of life fading in. |
| `fadeOut` | `uFadeOut` | 0.35 | 0.001 to 1 | Fraction of life fading out. |
| `startColor` | `uStartColor` | (1, 0.72, 0.3) | | Colour at birth (linear RGB). |
| `endColor` | `uEndColor` | (0.85, 0.18, 0.28) | | Colour at the end. |
| `pointScale` | `uPointScale` | 600 | above 0 | Buffer height / (2 tan(fov / 2)). |

## Checks

- `test_stateless_gpu_particles.mjs`: birth offsets and four particle states equal an independent Python port of the same integer hash and motion (positions within 1e-12, loop numbers, opacity and size); with gravity, swirl and the spawn disc off, every one of 3,000 launches lies inside the cone with a speed in range; a particle draws a new path on its next loop; opacity is 0 at birth, 1 mid-life and gone at the end; birth offsets fill every tenth of the lifetime evenly; the geometry, material and points carry what they should. Known-wrong control: launches spread over the whole sphere are refused by the cone check.
- `test_contract.mjs`: the exports, the contract examples and the uniform declarations.
- The verifier reads 1,024 seeds and births from a float texture, evaluates the GLSL particle state on the GPU and requires positions within 0.001 and life within 0.0001 of `particleState` (particles within 1e-5 of a loop boundary are skipped, at most 3), then renders the fountain and compares it with the stage alone.

## Limits

Stateless means nothing can collide, react to the scene, spawn on an event or change course mid-flight. Particles are not sorted; additive blending hides that. `gl_PointSize` is capped by the implementation (often 64 to 1024 pixels). GPU and CPU agree within float32 error, except at the instant a particle loops. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2; frame time was not measured.

## Technique

- Stateless particles from seed, birth offset and time
- PCG-style integer hash with 24-bit outputs, identical on GPU and CPU
- Uniform directions on a spherical cap from a uniform cosine; uniform points on a disc from a square-root radius
- Golden-ratio birth offsets
