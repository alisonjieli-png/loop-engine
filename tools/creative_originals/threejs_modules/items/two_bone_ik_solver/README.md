# Analytic two-bone IK with a pole target

Closed-form inverse kinematics for a chain of two bones, such as an upper arm and forearm or a thigh and shin. The distance from the root to the target, clamped between the shortest and the longest reach, fixes the end; the law of cosines gives the angle at the root; the mid joint goes into the plane that holds the root-target line and leans toward a pole point, so you choose which way the elbow or knee points. When the target is out of reach the chain straightens toward it; when it is too close the chain folds as far as it can.

## When to use it

Use it for feet that stay on uneven ground, hands that grab handles and ledges, aiming arms, robot arms and any two-segment limb that should end at a point you choose.

## Use it

On a three.js skeleton or any `Object3D` chain:

```js
import * as THREE from 'three';
import {applyTwoBoneIK} from './two_bone_ik_solver.mjs';

const thigh = skeleton.getBoneByName('thigh_L');
const shin = skeleton.getBoneByName('shin_L');
const foot = skeleton.getBoneByName('foot_L');
const solution = applyTwoBoneIK(THREE, thigh, shin, foot, footTarget.toArray(), kneePole.toArray());
if (!solution.reached) console.info('stretched toward the target', solution.distance);
```

Without three.js, solve on plain arrays:

```js
import {solveTwoBoneIK} from './two_bone_ik_solver.mjs';

const {mid, end, rootRotation, midRotation} = solveTwoBoneIK([0, 0, 0], [0, 1, 0], [0, 2, 0], [0, 1, 1], [0, 0, 5]);
// mid = [0, 0, 1], end = [0, 1, 1]
```

`demo/scene.mjs` bends one arm to a target and stretches another toward a target out of reach.

## Exports

- `solveTwoBoneIK(root, mid, end, target, pole, options = {})`: `{root, mid, end, rootRotation, midRotation, reached, distance, upperLength, lowerLength}`. `rootRotation` and `midRotation` are world-space shortest-arc rotations that turn the old upper and lower bone directions onto the new ones; `reached` says whether the target was within reach; `distance` is what is left between the end and the target.
- `applyTwoBoneIK(THREE, upper, lower, end, target, pole, options = {})`: rotates `upper` and `lower` about their own origins so `end` reaches the target, and returns the solution.
- `rotationBetween(from, to)`: the shortest-arc quaternion between two directions; opposite directions give a half turn about a perpendicular axis.
- `TWO_BONE_IK_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `reachMargin` | number | 0 | 0 to under 0.5 | Keep the chain this fraction short of full extension. |

An unknown option throws `TypeError`; a value out of range, or a bone of zero length, throws `RangeError`.

## Checks

- `test_two_bone_ik_solver.mjs`: two hand-solved chains bend toward their poles (the knee at (0, 1, 0) or (0, 0, 1)); an unreachable target gives a straight chain at full extension; a too-close target folds the chain to the shortest reach; `reachMargin` shortens the reach; `rotationBetween` gives a quarter turn about Z and a correct half turn; over 300 seeded random chains the end reaches its target within 1e-9, both bones keep their length and the mid joint is on the pole's side; the returned rotations turn the old bones onto the new ones. Known-wrong control: a solver that always bends toward +Y instead of the pole is refused by the pole-side check.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier poses two three.js `Object3D` arms with `applyTwoBoneIK` in the browser and checks that the hand touches the target, both bones keep their lengths, the hierarchy matches the solver, and the arm aimed out of reach is straight.

## Limits

Two bones only: no joint angle limits, no twist control beyond the pole, no stretching. The rotations are shortest arcs, so a bone's roll about its own axis is not preserved when the bend plane turns. `applyTwoBoneIK` rotates about the objects' own origins and assumes uniform scale on the chain and its parents; pose a skinned mesh through its bones. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Law of cosines for the angle at the root of a two-segment chain
- Pole vector projected onto the plane perpendicular to the root-target line
- Shortest-arc quaternion between two directions; world-to-local rotation through the parent's world quaternion
