"""Provenance-aware evidence counting: count independent observations, not messages.

A claim that travels A -> B -> C -> A arrives back at A as a message, but it is still the one observation A made.
Counting messages (or reports) double counts relayed and echoed evidence. Two tools:

- count_independent_evidence(reports): every report is either a root observation or rests on earlier reports
  (its sources). The independent evidence for a claim is the set of root observations reachable through sources.
  Reports whose sources never reach a root (circular reporting) support nothing and are listed.
- relay_non_backtracking(edges, origins, rounds): a message-passing simulation. Each agent forwards an observation
  identifier it has just learned to its out-neighbours, except the ones it learned it from (non-backtracking), and
  a receiver keeps an identifier once. The naive count adds one per received message instead.

    echo '{"call": "relay_non_backtracking", "arguments": {"edges": [["a", "b"], ["b", "c"], ["c", "a"]], "origins": {"a": ["o1"]}, "rounds": 3}}' | python3 provenance_evidence_counting.py
"""
from __future__ import annotations

import atom_cli
import numerics


def _reports(reports):
    if not isinstance(reports, list) or not reports:
        raise ValueError("reports is a non-empty list")
    table = {}
    for index, report in enumerate(reports):
        if not isinstance(report, dict) or not {"id", "agent", "claim"} <= set(report):
            raise ValueError(f"reports[{index}] needs id, agent and claim")
        if set(report) - {"id", "agent", "claim", "observed", "sources"}:
            raise ValueError(f"reports[{index}] has unknown fields")
        identity = report["id"]
        if not isinstance(identity, str) or not identity or identity in table:
            raise ValueError(f"reports[{index}] id must be unique non-empty text")
        observed = report.get("observed", False)
        sources = numerics.labels(report.get("sources", []), f"reports[{index}].sources", minimum_length=0)
        if not isinstance(observed, bool):
            raise ValueError(f"reports[{index}].observed must be true or false")
        if observed and sources:
            raise ValueError(f"reports[{index}] is an observation and cannot rest on sources")
        if not observed and not sources:
            raise ValueError(f"reports[{index}] is neither an observation nor rests on sources")
        table[identity] = {"agent": report["agent"], "claim": report["claim"], "observed": observed,
                           "sources": list(sources)}
    for identity, report in table.items():
        for source in report["sources"]:
            if source not in table:
                raise ValueError(f"report {identity} cites unknown report {source}")
            if table[source]["claim"] != report["claim"]:
                raise ValueError(f"report {identity} cites {source}, a report about another claim")
    return table


def _roots(table, identity):
    seen, stack, roots = set(), [identity], set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if table[current]["observed"]:
            roots.add(current)
        stack.extend(table[current]["sources"])
    return roots


def count_independent_evidence(reports):
    """Independent root observations per claim and per (agent, claim), next to the naive report counts.

    reports: [{"id", "agent", "claim", "observed": bool, "sources": [report ids]}]; an observation has no sources and
    every other report has at least one. Returns {"claims": [{"claim", "reports", "independent_observations",
    "roots", "unsupported_reports"}], "holdings": [{"agent", "claim", "reports_held", "independent_observations"}]}."""
    table = _reports(reports)
    roots = {identity: _roots(table, identity) for identity in table}
    claims, holdings = {}, {}
    for identity, report in table.items():
        claims.setdefault(report["claim"], []).append(identity)
        holdings.setdefault((report["agent"], report["claim"]), []).append(identity)
    claim_rows = []
    for claim in sorted(claims, key=str):
        members = claims[claim]
        union = set().union(*(roots[identity] for identity in members))
        claim_rows.append({"claim": claim, "reports": len(members), "independent_observations": len(union),
                           "roots": sorted(union), "unsupported_reports": sorted(i for i in members if not roots[i])})
    holding_rows = []
    for agent, claim in sorted(holdings, key=lambda pair: (str(pair[0]), str(pair[1]))):
        members = holdings[(agent, claim)]
        union = set().union(*(roots[identity] for identity in members))
        holding_rows.append({"agent": agent, "claim": claim, "reports_held": len(members),
                             "independent_observations": len(union)})
    return {"claims": claim_rows, "holdings": holding_rows}


def relay_non_backtracking(edges, origins, rounds):
    """Simulate relaying observation identifiers over directed edges for a number of rounds.

    edges: [[sender, receiver], ...]; origins: {agent: [observation ids]}; rounds: 1 to 10000.
    Returns {"held": {agent: sorted ids}, "independent": {agent: count}, "naive": {agent: own observations plus
    every message received}, "messages": total messages sent, "rounds_used"}."""
    if not isinstance(edges, list) or not isinstance(origins, dict):
        raise ValueError("edges is a list of [sender, receiver] pairs and origins an object")
    neighbours, agents = {}, set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, list) or len(edge) != 2 or edge[0] == edge[1]:
            raise ValueError(f"edges[{index}] must be [sender, receiver] with two different agents")
        sender, receiver = numerics.labels(edge, f"edges[{index}]")
        neighbours.setdefault(sender, set()).add(receiver)
        agents.update((sender, receiver))
    rounds = numerics.integer(rounds, "rounds", minimum=1, maximum=10000)
    held, naive, fresh = {}, {}, {}
    for agent, observations in origins.items():
        ids = numerics.labels(observations, f"origins[{agent!r}]", minimum_length=0)
        agents.add(agent)
        held[agent] = set(ids)
        naive[agent] = len(set(ids))
        fresh[agent] = {identity: set() for identity in ids}
    for agent in agents:
        held.setdefault(agent, set())
        naive.setdefault(agent, 0)
        fresh.setdefault(agent, {})
    messages, used = 0, 0
    for step in range(1, rounds + 1):
        incoming = {}
        for sender in sorted(agents, key=str):
            for identity, sources in sorted(fresh[sender].items(), key=lambda pair: str(pair[0])):
                for receiver in sorted(neighbours.get(sender, ()), key=str):
                    if receiver in sources:
                        continue  # non-backtracking: never send an identifier back where it came from
                    messages += 1
                    naive[receiver] += 1
                    incoming.setdefault(receiver, {}).setdefault(identity, set()).add(sender)
        fresh = {agent: {} for agent in agents}
        for receiver, items in incoming.items():
            for identity, senders in items.items():
                if identity not in held[receiver]:
                    held[receiver].add(identity)
                    fresh[receiver][identity] = senders
        used = step
        if not any(fresh.values()):
            break
    return {"held": {agent: sorted(held[agent], key=str) for agent in sorted(agents, key=str)},
            "independent": {agent: len(held[agent]) for agent in sorted(agents, key=str)},
            "naive": {agent: naive[agent] for agent in sorted(agents, key=str)}, "messages": messages,
            "rounds_used": used}


FUNCTIONS = {"count_independent_evidence": count_independent_evidence,
             "relay_non_backtracking": relay_non_backtracking}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["count_independent_evidence", "relay_non_backtracking", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
