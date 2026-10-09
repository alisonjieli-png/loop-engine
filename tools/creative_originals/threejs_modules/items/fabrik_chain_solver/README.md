# FABRIK solver for chains of any length

Inverse kinematics for a chain of any number of joints with a fixed root, by forward and backward reaching (FABRIK). Each pass first pulls the end onto the target and walks back toward the root, placing every joint at its segment length along the line to the next; then it puts the root back on its base and walks out again. Segment lengths never change, the passes repeat until the end is within tolerance or the cap is reached, and a target beyond the chain's reach straightens the chain toward it in one step. Starting from the previous frame's pose keeps the motion coherent.

## When to use it

Use it for tails, tentacles, snakes, cables and hoses, spines, multi-segment robot arms, and any chain longer than two bones that should end at a point.

## Use it

```js
import * as THREE from 'three';
import {applyFabrikChain} from './fabrik_chain_solver.mjs';

// tail[0] is the root bone; each next bone is a child of the previous one; the last is the tip.
const tail = ['tail_0', 'tail_1', 'tail_2', 'tail_3', 'tail_4'].map((name) => skeleton.getBoneByName(name));
function frame() {
  const solution = applyFabrikChain(THREE, tail, lure.position.toArray(), {maxIterations: 16});
  if (!solution.reachable) lure.material.color.set(0xff0000);
}
```

On plain arrays:

```js
import {solveFabrik, chainReach} from './fabrik_chain_solver.mjs';

const {joints, reached} = solveFabrik([[0, 0, 0], [0, 1, 0], [0, 2, 0], [0, 3, 0]], [1.2, 1.5, 0.4]);
const {shortest, longest} = chainReach(joints);
```

`demo/scene.mjs` curls one tentacle down to a ring near the floor and stretches another toward a ring out of reach.

## Exports

- `solveFabrik(joints, target, options = {})`: `{joints, iterations, error, reached, reachable}`; the root stays where it is, `error` is the end's distance from the target, `reached` is `error <= tolerance`, `reachable` says whether the target's distance from the root is within `chainReach`.
- `applyFabrikChain(THREE, objects, target, options = {})`: rotates each object except the last about its own origin, root first, so the last reaches the target; returns the solution.
- `chainLengths(joints)`: the segment lengths; a zero-length segment throws `RangeError`.
- `chainReach(joints)`: `{shortest, longest}`, the end's reachable distances from the root.
- `FABRIK_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `tolerance` | number | 0.0001 | above 0 | End-to-target distance that counts as reached. |
| `maxIterations` | integer | 32 | 1 to 10,000 | Cap on forward and backward passes. |

## Checks

- `test_fabrik_chain_solver.mjs`: a target at exactly full reach and one beyond it give hand-computed straight chains (an error of exactly 7 for the far one); over 300 seeded random chains of 3 to 9 joints with targets inside their reach, the end is within 1e-4 of the target, every segment keeps its length within 1e-9 and the root never moves; a pose already at the target takes no pass; a target closer than the chain can fold is unreachable and the chain folds to within 1e-3 of the best it can do; the iteration cap holds. Known-wrong control: a solver that skips the backward pass, so its root drifts, is refused.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier poses two nine-joint three.js chains in the browser and checks the tip on the target, the segment lengths, the fixed root, the hierarchy against the solver and the straightened chain.

## Limits

Positions only: no joint angle limits, no twist control and no preferred bend direction, so the result depends on the starting pose. Convergence slows near both ends of the reach: on 300 seeded random chains, with targets kept a tenth of the range away from either end, the median was 4 passes, 95 percent needed 17 or fewer, the slowest 80, and 3 were not within 1e-4 after the default 32. `applyFabrikChain` rotates by shortest arcs about each object's origin and assumes uniform scale. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- FABRIK: forward and backward reaching inverse kinematics
- Reachable distance interval of a polygonal chain
- Shortest-arc quaternion per segment, applied from the root outward
