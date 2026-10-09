# Hodge decomposition of edge flows

Splits a flow on the edges of a graph into three orthogonal parts. The gradient part is explained by one score per node. The curl part circulates around filled triangles. The harmonic part circulates around holes, cycles that no triangle fills. For pairwise comparisons this shows how much of the data a single ranking can explain.

## When to use it

- You have pairwise preferences or score differences between systems, answers or items and want to know how consistent they are with one global ranking.
- You suspect cyclic preferences (A over B, B over C, C over A) and want to measure them.
- You want to check the trap: differences `x_u - x_v` built from scores look cyclic on a cycle of comparisons, but they are a pure gradient.

## Formula

With `B1` the node-edge incidence (`(B1^T s)` on edge `(u, v)` is `s_v - s_u`) and `B2` the edge-triangle incidence of the 2-cells:

    gradient = B1^T s*,  s* = argmin ||B1^T s - f||
    curl     = B2 phi*,  phi* = argmin ||B2 phi - f||
    harmonic = f - gradient - curl

Because `B1 B2 = 0`, the three parts are orthogonal. `betti_1 = |E| - rank(B1) - rank(B2)` is the number of independent holes. Potentials are the minimum-norm solution and sum to zero on each connected component.

## Assumptions and what it does not establish

- A flow on edge `(u, v)` is the flow from `u` to `v`. Reversing an edge negates its value.
- Which 3-cycles are filled is a choice: declare `triangles` or set `fill_triangles` for every 3-clique. A cycle is curl when filled and harmonic when not.
- The decomposition is unweighted and descriptive. It does not test whether the curl part is larger than noise.

## Parameters

| Name | Meaning |
|---|---|
| `nodes` | unique labels |
| `edges` | `[[tail, head]]`, at most one edge per node pair, no self loops |
| `flow` | one number per edge |
| `triangles` | `[[a, b, c]]` whose three sides are edges |
| `fill_triangles` | fill every 3-clique instead of declaring triangles |

The result holds `gradient`, `curl`, `harmonic` (per edge), `potential` (per node), `triangle_circulation`, `norms`, `betti_1` and `max_cross_product`.

## Example

```python
from hodge_edge_flow_decomposition import hodge_decomposition, flow_from_potential

nodes, edges = [0, 1, 2], [[0, 1], [1, 2], [0, 2]]
hodge_decomposition(nodes, edges, [1, 1, -1])["harmonic"]                      # [1, 1, -1]: a hole
hodge_decomposition(nodes, edges, [1, 1, -1], triangles=[[0, 1, 2]])["curl"]    # [1, 1, -1]: filled
flow = flow_from_potential(nodes, edges, [3, 1, 0])                             # [2, 1, 3]
hodge_decomposition(nodes, edges, flow)["norms"]["harmonic"]                    # 0.0: a gradient
```

Command line:

```bash
echo '{"call": "hodge_decomposition", "arguments": {"nodes": [0, 1, 2], "edges": [[0, 1], [1, 2], [0, 2]], "flow": [1, 1, -1], "triangles": [[0, 1, 2]]}}' | python3 hodge_edge_flow_decomposition.py
```

## Limits

- Dense pseudo-inverses: up to about a hundred edges.
- Triangles are the only 2-cells.
- No edge weights.

## Files

- `hodge_edge_flow_decomposition.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_hodge_edge_flow_decomposition.py`, `test_package.py`: run with `python3 -m unittest`.
