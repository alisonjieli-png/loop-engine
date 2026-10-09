# Pointer rays and plane dragging

Everything between a pointer and an object you drag across the floor. `ndcFromPointer` maps a pointer over an element to normalized device coordinates. `rayFromCamera` unprojects the near and far clip planes under that point through the inverse projection and the camera's world matrix, so the same code serves perspective and orthographic cameras and the ray starts on the near plane. `intersectRayPlane` returns the distance to a plane. `PlaneDrag` remembers where the ray first met the plane and the object's offset from that point, so the object does not jump to the pointer, keeps its height above the plane, and can snap to a grid laid in the plane itself.

## When to use it

Use it for level and scene editors, board and strategy games, furniture and building placement, sliders and handles in 3D, and anything that drags objects on the ground or on a wall.

## Use it

```js
import * as THREE from 'three';
import {PlaneDrag, ndcFromPointer, rayFromCamera} from './ray_plane_drag.mjs';

const drag = new PlaneDrag({normal: [0, 1, 0], constant: 0, snap: 0.5});   // the floor, half-unit grid
const rayAt = (event) => {
  const [x, y] = ndcFromPointer(event.clientX, event.clientY, renderer.domElement.getBoundingClientRect());
  return rayFromCamera(x, y, camera.projectionMatrixInverse.elements, camera.matrixWorld.elements);
};
renderer.domElement.addEventListener('pointerdown', (event) => drag.begin(rayAt(event), selected.position.toArray()));
renderer.domElement.addEventListener('pointermove', (event) => {
  const position = drag.move(rayAt(event));
  if (position) selected.position.fromArray(position);
});
renderer.domElement.addEventListener('pointerup', () => drag.end());
```

`demo/scene.mjs` drags two blocks along simulated pointer paths, one snapped to the grid.

## Exports

- `ndcFromPointer(clientX, clientY, rect)`: `[x, y]` in [-1, 1] with +y up, from `rect = {left, top, width, height}`.
- `rayFromCamera(ndcX, ndcY, inverseProjection, cameraWorld, nearDepth = -1)`: `{origin, direction}` with the origin on the near plane and a unit direction. `nearDepth` is -1 for WebGL projections and 0 for WebGPU ones.
- `intersectRayPlane(origin, direction, normal, constant)`: the distance `t >= 0` to the plane `normal . p + constant = 0`, or `null` when the ray is parallel to it or points away.
- `planeFromNormalAndPoint(normal, point)`: `{normal, constant}` with a unit normal.
- `invertMatrix(matrix)`: the inverse of a column-major 4 x 4 matrix; a singular matrix throws `RangeError`.
- `PlaneDrag`: `new PlaneDrag(options)`; `begin(ray, objectPosition)` returns whether the ray met the plane; `move(ray)` returns the new position or `null`; `end()` stops; `active` tells whether a drag is running; `hit(ray)` is the plane point under a ray; `snapToGrid(position)` snaps any point.
- `PLANE_DRAG_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Meaning |
|---|---|---|---|
| `normal` | vector | [0, 1, 0] | Plane normal; normalized by the controller. |
| `constant` | number | 0 | Plane constant in `normal . p + constant = 0`. |
| `snap` | number | 0 | Grid step in the plane; 0 for no snapping. |

An unknown option throws `TypeError`; a zero normal, a negative step or a malformed vector or matrix throws `RangeError`.

## Checks

- `test_ray_plane_drag.mjs`: pointer corners and centre map to their NDC; `invertMatrix` equals the closed-form inverses of a perspective and an orthographic projection and of a camera transform; rays for a 90 degree camera point at `(2x, y, -1)` normalized, an orthographic ray starts on the near plane and points down -z, and a camera looking straight down casts down from 4.5 units up; plane distances, parallel and receding rays; the drag keeps its offset, misses parallel rays, snaps to a 1 unit grid on the floor and to a 0.5 grid on a tilted plane without changing the height above it. Known-wrong controls: a ray left in view space is refused by the ray check, and invalid planes, rays and options throw.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and compares, in the browser, 50 rays from a perspective and an orthographic camera with three.js `Raycaster.setFromCamera` and the floor hits with `Ray.intersectPlane`, then checks the drag offset, the height and the grid.

## Limits

Planes only: no dragging over a curved surface, along an axis gizmo or on a sphere. A ray parallel to the plane or pointing away from it returns `null`, so at very flat camera angles over a ground plane the drag pauses until the pointer comes back. Snapping rounds in the plane's own two-axis grid, which for a tilted plane is not the world grid. Rays start on the near plane. No pointer capture or event wiring is included. The module needs no three.js; the demo was rendered with three.js 0.186.1 in headless Chrome on SwiftShader WebGL 2.

## Technique

- Unprojecting clip-space points through the inverse projection and the camera world matrix
- Ray and plane intersection, `t = -(n . o + c) / (n . d)`
- Matrix inverse by cofactors (the adjugate)
- Grid snapping in an orthonormal basis of the plane
