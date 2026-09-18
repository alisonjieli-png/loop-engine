# Optimize a node grid

This example walks a declared grid over one node's parameters, scores every
cell on a frozen suite, and accepts a cell only when the gain is honest.

The node is the text conformance resolver from example 26. Its grid has
three parameters: the apply threshold and two catalog confidences. The
twelve-case company-name suite is split by case digest into a training
side and a held-out side. Every cell is counted as represented, applicable,
proposed, dispatched, and evaluated; a cell replaces the baseline only when
it gains on training cases and does not lose a held-out case. Promotion is
left to an independent review, so the promoted count stays at zero.

Install Loop Engine directly from GitHub:

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
```

Run the example from the repository directory:

```bash
python examples/27_optimize_a_node_grid/run.py
```

The output includes:

- the baseline solver's exact counts on the full suite with its failures;
- the grid's represented count and the split sizes;
- every evaluated cell with its training and held-out net changes;
- the decision with its reason; and
- the separate stage counts, with exhaustive coverage stated honestly.

The same run is available from the command line:

```bash
loop-engine evaluate examples/27_optimize_a_node_grid/inputs/suite.json --solver-spec examples/27_optimize_a_node_grid/inputs/solver.json
loop-engine optimize examples/27_optimize_a_node_grid/inputs/suite.json --solver-spec examples/27_optimize_a_node_grid/inputs/solver.json --space examples/27_optimize_a_node_grid/inputs/space.json
```

No network, no external service, no model calls.
