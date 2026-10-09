"""Exactness and orthogonality on random graphs, the pairwise-difference trap, and hole versus filled cycles."""
from __future__ import annotations

import itertools
import unittest

import numerics
from hodge_edge_flow_decomposition import flow_from_potential, hodge_decomposition


def _random_graph(generator, size, probability):
    nodes = list(range(size))
    edges = [[a, b] if generator.random() < 0.5 else [b, a] for a, b in itertools.combinations(nodes, 2)
             if generator.random() < probability]
    return nodes, edges


def _divergence(nodes, edges, flow):
    return [sum(f for (tail, head), f in zip(edges, flow) if head == node) -
            sum(f for (tail, head), f in zip(edges, flow) if tail == node) for node in nodes]


class HodgeTests(unittest.TestCase):
    def test_parts_sum_to_the_flow_and_are_orthogonal(self):
        generator = numerics.seeded_random(8)
        for trial in range(5):
            nodes, edges = _random_graph(generator, 6, 0.6)
            if len(edges) < 3:
                continue
            flow = numerics.standard_normals(generator, len(edges))
            result = hodge_decomposition(nodes, edges, flow, fill_triangles=True)
            with self.subTest(trial=trial):
                for f, g, c, h in zip(flow, result["gradient"], result["curl"], result["harmonic"]):
                    self.assertAlmostEqual(f, g + c + h, places=12)
                self.assertLess(result["max_cross_product"], 1e-9)
                for value in _divergence(nodes, edges, result["curl"]) + _divergence(nodes, edges, result["harmonic"]):
                    self.assertAlmostEqual(value, 0.0, places=9)

    def test_pairwise_differences_are_a_gradient(self):
        generator = numerics.seeded_random(9)
        nodes, edges = _random_graph(generator, 7, 0.7)
        values = numerics.standard_normals(generator, 7)
        flow = flow_from_potential(nodes, edges, values)
        for fill in (False, True):
            result = hodge_decomposition(nodes, edges, flow, fill_triangles=fill)
            self.assertLess(result["norms"]["curl"] + result["norms"]["harmonic"], 1e-9)
        result = hodge_decomposition(nodes, edges, flow)
        component = {node: node for node in nodes}

        def root(node):
            while component[node] != node:
                node = component[node]
            return node

        for tail, head in edges:
            component[root(tail)] = root(head)
        for node, value in zip(nodes, values):
            members = [other for other in nodes if root(other) == root(node)]
            mean = sum(values[other] for other in members) / len(members)
            self.assertAlmostEqual(result["potential"][str(node)], mean - value, places=9)

    def test_cycle_is_curl_when_filled_and_harmonic_around_a_hole(self):
        nodes, edges, cycle = [0, 1, 2], [[0, 1], [1, 2], [0, 2]], [1.0, 1.0, -1.0]
        filled = hodge_decomposition(nodes, edges, cycle, triangles=[[0, 1, 2]])
        hole = hodge_decomposition(nodes, edges, cycle)
        self.assertEqual((filled["norms"]["harmonic"], hole["norms"]["curl"]), (0.0, 0.0))
        self.assertEqual((filled["betti_1"], hole["betti_1"]), (0, 1))
        # known-wrong: calling every circulation "curl" misreads the hole
        self.assertNotEqual(hole["harmonic"], [0.0, 0.0, 0.0])

    def test_betti_numbers(self):
        two_triangles = [[0, 1], [1, 2], [0, 2], [3, 4], [4, 5], [3, 5]]
        self.assertEqual(hodge_decomposition(list(range(6)), two_triangles, [0.0] * 6)["betti_1"], 2)
        self.assertEqual(hodge_decomposition(list(range(6)), two_triangles, [0.0] * 6,
                                             fill_triangles=True)["betti_1"], 0)

    def test_invalid_input_is_refused(self):
        bad = [([0, 1], [[0, 0]], [1.0], None), ([0, 1], [[0, 1], [1, 0]], [1.0, 2.0], None),
               ([0, 1], [[0, 2]], [1.0], None), ([0, 1, 2], [[0, 1], [1, 2]], [1.0, 2.0], [[0, 1, 2]]),
               ([0, 1], [[0, 1]], [1.0, 2.0], None), ([0, 0], [[0, 1]], [1.0], None)]
        for nodes, edges, flow, triangles in bad:
            with self.subTest(edges=edges), self.assertRaises(ValueError):
                hodge_decomposition(nodes, edges, flow, triangles)


if __name__ == "__main__":
    unittest.main()
