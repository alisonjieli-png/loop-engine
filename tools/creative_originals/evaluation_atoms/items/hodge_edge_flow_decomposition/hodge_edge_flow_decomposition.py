"""Hodge decomposition of an edge flow on a small graph: gradient + curl + harmonic, mutually orthogonal.

An edge flow assigns a number to each oriented edge (u, v): the flow from u to v, for example how much item v is
preferred to item u. With B1 the node-edge incidence (grad s on edge (u, v) is s_v - s_u) and B2 the edge-triangle
incidence of the declared 2-cells (triangles):

    gradient = B1^T s*,  s* = argmin ||B1^T s - f||        (a global potential explains it)
    curl     = B2 phi*,  phi* = argmin ||B2 phi - f||      (circulation around filled triangles)
    harmonic = f - gradient - curl                         (circulation around holes: cycles no triangle fills)

B1 B2 = 0, so the three parts are orthogonal. A flow built as f(u, v) = x_u - x_v is a gradient by construction (of
the potential -x): it has no curl and no harmonic part, whatever cycles the graph contains. Potentials are the
minimum-norm solution, so they sum to zero on each connected component.

    echo '{"call": "hodge_decomposition", "arguments": {"nodes": [0, 1, 2], "edges": [[0, 1], [1, 2], [0, 2]], "flow": [1, 1, -1], "triangles": [[0, 1, 2]]}}' | python3 hodge_edge_flow_decomposition.py
"""
from __future__ import annotations

import itertools
import math

import atom_cli
import numerics


def _graph(nodes, edges, flow, triangles, fill_triangles):
    names = numerics.labels(nodes, "nodes")
    if len(set(names)) != len(names):
        raise ValueError("nodes must be unique")
    index = {name: position for position, name in enumerate(names)}
    if not isinstance(edges, list) or not edges:
        raise ValueError("edges is a non-empty list of [tail, head] pairs")
    pairs, seen = [], {}
    for position, edge in enumerate(edges):
        if not isinstance(edge, list) or len(edge) != 2 or edge[0] not in index or edge[1] not in index:
            raise ValueError(f"edges[{position}] must be [tail, head] with known nodes")
        if edge[0] == edge[1]:
            raise ValueError(f"edges[{position}] is a self loop")
        key = frozenset(edge)
        if key in seen:
            raise ValueError(f"edges[{position}] repeats an edge between the same two nodes")
        seen[key] = position
        pairs.append((index[edge[0]], index[edge[1]]))
    values = numerics.vector(flow, "flow", minimum_length=len(pairs), maximum_length=len(pairs))
    cells = []
    if fill_triangles:
        if triangles:
            raise ValueError("give triangles or fill_triangles, not both")
        for a, b, c in itertools.combinations(names, 3):
            if {frozenset((a, b)), frozenset((b, c)), frozenset((a, c))} <= set(seen):
                cells.append((a, b, c))
    else:
        for position, cell in enumerate(triangles or []):
            if not isinstance(cell, list) or len(cell) != 3 or len(set(map(repr, cell))) != 3:
                raise ValueError(f"triangles[{position}] must list three different nodes")
            for a, b in ((cell[0], cell[1]), (cell[1], cell[2]), (cell[2], cell[0])):
                if frozenset((a, b)) not in seen:
                    raise ValueError(f"triangles[{position}] uses a missing edge {a}-{b}")
            cells.append(tuple(cell))
        if len({frozenset(cell) for cell in cells}) != len(cells):
            raise ValueError("triangles repeat")
    return names, index, pairs, values, seen, cells


def _project(columns, target):
    """Least-squares projection of target onto the span of the given column vectors (minimum-norm coefficients)."""
    if not columns:
        return [], [0.0] * len(target)
    gram = [[numerics.dot(a, b) for b in columns] for a in columns]
    coefficients = numerics.matvec(numerics.pseudo_inverse_symmetric(gram), [numerics.dot(c, target) for c in columns])
    image = [math.fsum(coefficients[k] * columns[k][e] for k in range(len(columns))) for e in range(len(target))]
    return coefficients, image


def hodge_decomposition(nodes, edges, flow, triangles=None, fill_triangles=False):
    """Split an edge flow into gradient, curl and harmonic parts.

    nodes: unique labels; edges: [[tail, head]] with at most one edge per node pair; flow: one number per edge
    (flow from tail to head); triangles: [[a, b, c]] 2-cells whose three sides are edges, or fill_triangles=true to
    fill every 3-clique. Returns {"gradient", "curl", "harmonic", "potential" (per node), "triangle_circulation"
    (flow summed around each cell a->b->c->a), "norms", "betti_1" (dimension of the harmonic space),
    "max_cross_product" (largest |inner product| between parts)}."""
    names, index, pairs, values, seen, cells = _graph(nodes, edges, flow, triangles, fill_triangles)
    edge_count, node_count = len(pairs), len(names)
    node_columns = []
    for node in range(node_count):
        node_columns.append([(1.0 if head == node else 0.0) - (1.0 if tail == node else 0.0) for tail, head in pairs])
    potential, gradient = _project(node_columns, values)
    cell_columns = []
    for cell in cells:
        column = [0.0] * edge_count
        for a, b in ((cell[0], cell[1]), (cell[1], cell[2]), (cell[2], cell[0])):
            position = seen[frozenset((a, b))]
            column[position] += 1.0 if pairs[position] == (index[a], index[b]) else -1.0
        cell_columns.append(column)
    _phi, curl = _project(cell_columns, values)
    harmonic = [f - g - c for f, g, c in zip(values, gradient, curl)]
    circulation = [numerics.dot(column, values) for column in cell_columns]

    def rank(columns):
        if not columns:
            return 0
        eigenvalues = numerics.symmetric_eigen([[numerics.dot(a, b) for b in columns] for a in columns])[0]
        top = max(abs(value) for value in eigenvalues)
        return sum(1 for value in eigenvalues if value > 1e-9 * max(top, 1.0))

    cross = max(abs(numerics.dot(gradient, curl)), abs(numerics.dot(gradient, harmonic)),
                abs(numerics.dot(curl, harmonic)))
    return {"gradient": gradient, "curl": curl, "harmonic": harmonic,
            "potential": {str(name): potential[index[name]] for name in names}, "triangle_circulation": circulation,
            "norms": {"flow": numerics.vector_norm(values), "gradient": numerics.vector_norm(gradient),
                      "curl": numerics.vector_norm(curl), "harmonic": numerics.vector_norm(harmonic)},
            "betti_1": edge_count - rank(node_columns) - rank(cell_columns), "max_cross_product": cross}


def flow_from_potential(nodes, edges, values):
    """The flow f(u, v) = values[u] - values[v] on each oriented edge (u, v); a gradient of the potential -values."""
    names = numerics.labels(nodes, "nodes")
    numbers = numerics.vector(values, "values", minimum_length=len(names), maximum_length=len(names))
    lookup = dict(zip(names, numbers))
    result = []
    for position, edge in enumerate(edges):
        if not isinstance(edge, list) or len(edge) != 2 or edge[0] not in lookup or edge[1] not in lookup:
            raise ValueError(f"edges[{position}] must be [tail, head] with known nodes")
        result.append(lookup[edge[0]] - lookup[edge[1]])
    return result


FUNCTIONS = {"hodge_decomposition": hodge_decomposition, "flow_from_potential": flow_from_potential}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["hodge_decomposition", "flow_from_potential", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
