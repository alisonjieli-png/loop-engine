"""Relayed and echoed evidence counts once; a backtracking relay that counts messages is the known-wrong control."""
from __future__ import annotations

import unittest

import numerics
from provenance_evidence_counting import count_independent_evidence, relay_non_backtracking

CYCLE_REPORTS = [{"id": "r1", "agent": "a", "claim": "x", "observed": True},
                 {"id": "r2", "agent": "b", "claim": "x", "sources": ["r1"]},
                 {"id": "r3", "agent": "c", "claim": "x", "sources": ["r2"]},
                 {"id": "r4", "agent": "a", "claim": "x", "sources": ["r3"]}]


def _backtracking_naive(edges, origin, rounds):
    """Known-wrong: flood every message to every neighbour (including back) and count each arrival."""
    neighbours = {}
    for sender, receiver in edges:
        neighbours.setdefault(sender, []).append(receiver)
    counts, frontier = {origin: 1}, [origin]
    for _ in range(rounds):
        nxt = []
        for sender in frontier:
            for receiver in neighbours.get(sender, []):
                counts[receiver] = counts.get(receiver, 0) + 1
                nxt.append(receiver)
        frontier = nxt
    return counts


def _reachable(edges, start):
    seen, stack = {start}, [start]
    while stack:
        node = stack.pop()
        for sender, receiver in edges:
            if sender == node and receiver not in seen:
                seen.add(receiver)
                stack.append(receiver)
    return seen


class EvidenceCountingTests(unittest.TestCase):
    def test_relay_cycle_is_one_observation(self):
        result = count_independent_evidence(CYCLE_REPORTS)
        self.assertEqual(result["claims"][0]["independent_observations"], 1)
        self.assertEqual(result["claims"][0]["reports"], 4)
        holding = next(row for row in result["holdings"] if row["agent"] == "a")
        self.assertEqual((holding["reports_held"], holding["independent_observations"]), (2, 1))

    def test_independent_roots_add_and_circular_reports_support_nothing(self):
        reports = CYCLE_REPORTS + [{"id": "r5", "agent": "d", "claim": "x", "observed": True},
                                   {"id": "r6", "agent": "c", "claim": "x", "sources": ["r3", "r5"]},
                                   {"id": "r7", "agent": "e", "claim": "y", "sources": ["r8"]},
                                   {"id": "r8", "agent": "f", "claim": "y", "sources": ["r7"]}]
        claims = {row["claim"]: row for row in count_independent_evidence(reports)["claims"]}
        self.assertEqual(claims["x"]["roots"], ["r1", "r5"])
        self.assertEqual(claims["y"]["independent_observations"], 0)
        self.assertEqual(claims["y"]["unsupported_reports"], ["r7", "r8"])

    def test_backtracking_message_count_is_caught(self):
        edges = [["a", "b"], ["b", "a"]]
        naive = _backtracking_naive(edges, "a", 2)
        self.assertEqual(naive["a"], 2, "the control counts its own echo")
        result = relay_non_backtracking(edges, {"a": ["o1"]}, 5)
        self.assertEqual((result["independent"]["a"], result["naive"]["a"]), (1, 1))

    def test_relay_reaches_exactly_the_reachable_agents(self):
        generator = numerics.seeded_random(12)
        agents = [f"n{i}" for i in range(7)]
        for trial in range(6):
            edges = []
            for sender in agents:
                for receiver in agents:
                    if sender != receiver and generator.random() < 0.25:
                        edges.append([sender, receiver])
            origins = {"n0": ["o0"], "n3": ["o3"]}
            result = relay_non_backtracking(edges, origins, 50)
            for agent in agents:
                expected = sorted(identity for origin, ids in origins.items() for identity in ids
                                  if agent in _reachable(edges, origin))
                with self.subTest(trial=trial, agent=agent):
                    self.assertEqual(result["held"].get(agent, []), expected)

    def test_invalid_reports_are_refused(self):
        bad_sets = [
            [{"id": "r1", "agent": "a", "claim": "x", "observed": True, "sources": ["r1"]}],
            [{"id": "r1", "agent": "a", "claim": "x"}],
            [{"id": "r1", "agent": "a", "claim": "x", "sources": ["r9"]}],
            [{"id": "r1", "agent": "a", "claim": "x", "observed": True},
             {"id": "r2", "agent": "b", "claim": "z", "sources": ["r1"]}],
            [{"id": "r1", "agent": "a", "claim": "x", "observed": True},
             {"id": "r1", "agent": "b", "claim": "x", "observed": True}],
            [],
        ]
        for reports in bad_sets:
            with self.subTest(reports=reports), self.assertRaises(ValueError):
                count_independent_evidence(reports)
        with self.assertRaises(ValueError):
            relay_non_backtracking([["a", "a"]], {"a": ["o1"]}, 2)
        with self.assertRaises(ValueError):
            relay_non_backtracking([["a", "b"]], {"a": ["o1"]}, 0)


if __name__ == "__main__":
    unittest.main()
