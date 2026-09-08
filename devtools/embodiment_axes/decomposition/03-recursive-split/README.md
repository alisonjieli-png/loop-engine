# recursive_split

Keep halving until a piece is small enough, then merge back up.

Family: `decomposition`  |  Status: measured

## How it works

- Split a piece larger than a threshold into halves.
- Handle each half the same way.
- Combine partial results pairwise on the way back up.

## What it gives you

- The threshold is about the work, not about the machine, so the same setting travels between deployments.
- The tree shape follows the input size without anyone choosing a group count.
- A depth guard bounds the tree even at a threshold that asks for an unbounded one.

## What it costs you

- Combines pairwise up the tree, so the merge must be associative and not merely correct once at the end.
- Deeper than a flat split for the same number of leaves, and depth is coordination.
- Same per-leaf call overhead as the fixed split, plus a tree to reason about.

## Pick this when

- Input size varies a lot between runs.
- You want one threshold that means the same thing everywhere.

## Avoid it when

- The merge is not associative. Then the tree is unsafe in a way a flat split is not.

## Run it

```bash
python3 decomposition/03-recursive-split/embodiment.py        # its own self-check
python3 registry.py run --family decomposition
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.
