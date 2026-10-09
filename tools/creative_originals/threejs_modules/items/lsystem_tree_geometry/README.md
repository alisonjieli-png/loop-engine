# L-system tree builder with a 3D turtle

Trees, bushes and other branching shapes for three.js from Lindenmayer systems. `rewriteLSystem` replaces every symbol of a string at once, `iterations` times, using your rules; a rule can list weighted choices, picked by a seeded generator so one seed always grows the same tree. `interpretTurtle` walks the result with a 3D turtle that carries a heading, a left and an up vector: it turns, pitches and rolls by `angle`, pushes and pops its state at brackets, tapers its radius and shortens its step. `lsystemTreeData` turns each drawn step into a tapered open cylinder, merges them into one mesh and returns leaf anchor points where the string says `L`.

## When to use it

Use it for procedural trees and bushes, forests with one seed per tree, coral, roots, lightning-like branching, vines and decorative fractals (Koch curves, dragon curves) in 3D.

## Use it

```js
import * as THREE from 'three';
import {createLsystemTreeGeometry, rewriteLSystem} from './lsystem_tree_geometry.mjs';

const rules = {
  A: [
    {successor: '!"F[&+FLA]\\\\[&-FLA]\\\\[^FLA]', weight: 3},  // three branches, rolled apart
    {successor: '!"F[&FLA]\\\\\\[&FLA]', weight: 2},          // two branches
    {successor: '!"FL', weight: 1},                           // stop
  ],
};
const commands = rewriteLSystem('FFA', rules, 6, 42);  // the seed picks the tree
const geometry = createLsystemTreeGeometry(THREE, commands, {angle: 30, length: 0.42, radius: 0.07, taper: 0.74});
scene.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: 0x6b4a2f})));
const leafPositions = geometry.userData.leafPositions;  // x, y, z per leaf for an InstancedMesh
```

The backslashes are doubled because they sit in JavaScript strings; each pair is one roll command.

`demo/scene.mjs` grows the tree above with instanced foliage; the verifier compares it with a cone placeholder.

## Exports

- `rewriteLSystem(axiom, rules, iterations, seed = 1, maxLength = 1000000)`: the rewritten string. Rules map one character to a successor string or to `[{successor, weight}, ...]`.
- `interpretTurtle(commands, options = {})`: `{segments, leaves}` as plain arrays; each segment is `{start, end, startRadius, endRadius, left, up}` and each leaf `{position, heading}`. The turtle starts at the origin heading +Y with left -X and up +Z.
- `lsystemTreeData(commands, options = {})`: `{positions, normals, uvs, indices, segmentCount, leafPositions, leafDirections}`; two rings of `radialSegments + 1` vertices per branch, normals tilted by the taper, u around and v along each branch.
- `createLsystemTreeGeometry(THREE, commands, options = {})`: the branches in a `THREE.BufferGeometry` with the leaf anchors in `userData`.
- `LSYSTEM_TREE_DEFAULTS`: the frozen default options.

## Commands

| Command | Turtle action |
|---|---|
| `F` | Move forward one step and draw a branch. |
| `f` | Move forward without drawing. |
| `+`, `-` | Turn left, right about the up vector. |
| `&`, `^` | Pitch down, up about the left vector. |
| backslash, `/` | Roll left, right about the heading. |
| `\|` | Turn around. |
| `[`, `]` | Push and pop position, orientation, radius and step. |
| `!` | Multiply the radius by `taper`. |
| `"` | Multiply the step by `lengthScale`. |
| `L` | Record a leaf anchor. |
| anything else | A variable for rewriting; draws nothing. |

## Options

| Option | Type | Default | Meaning |
|---|---|---|---|
| `angle` | number | 25 | Degrees per turn, pitch or roll. |
| `length` | number | 1 | First step length. |
| `lengthScale` | number | 0.8 | Step multiplier for `"`. |
| `radius` | number | 0.1 | First branch radius. |
| `taper` | number | 0.7 | Radius multiplier for `!`. |
| `segmentTaper` | number | 1 | Radius multiplier along every `F`. |
| `radialSegments` | integer | 6 | Sides of each branch, 3 to 64. |
| `maxSegments` | integer | 200000 | Refuse strings that draw more branches. |

An unknown option or a rule key longer than one character throws `TypeError`; a bad number, more than 64 iterations, a string past `maxLength`, too many branches or an unmatched `]` throws `RangeError`.

## Checks

- `test_lsystem_tree_geometry.mjs`: the algae system `A -> AB, B -> A` gives the Fibonacci lengths 1, 2, 3, 5, 8, 13, 21, 34 and the string `ABAABABA`; a Koch rule gives 25 `F`s in 49 characters after two steps; stochastic rules repeat by seed, differ between seeds and follow zero weights; the turtle's first segment ends where each of ten commands should put it at 90 degrees; a branch is two rings with outward faces and the lateral area `N 2 r sin(pi / N) h`; tapered normals tilt by the slope; branch and leaf counts follow the string. Known-wrong controls: a rewrite that replaces symbols rule by rule in place, and a turtle with yaw and pitch swapped, are refused.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks, in the browser, that the seed repeats, that there is one branch per `F` (at least 60 of them) and one leaf per `L`, that the tree rises above its trunk and that its crown spreads sideways at least 30 percent of its height along both X and Z.

## Limits

Context-free, non-parametric L-systems only: no context-sensitive or parametric rules, tropism, collision or pruning. Each `F` is a separate open cylinder; joints overlap rather than weld and branch ends are open, so very large forests should be instanced. Leaves are anchors with a heading; drawing them is up to you. Strings grow exponentially; `maxLength` and `maxSegments` refuse runaway grammars. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Parallel rewriting of bracketed L-systems (Lindenmayer)
- 3D turtle with heading, left and up vectors (Prusinkiewicz and Lindenmayer's conventions)
- Weighted stochastic productions with a seeded Weyl-sequence generator
- Rodrigues rotation of the turtle frame
