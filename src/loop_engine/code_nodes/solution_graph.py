"""Typed Solution graphs — ports, edges, and Adapter Loops.

Architectural role: Code Node system (the Solution graph's type layer).

Charter §26.3: every logical graph vertex is a Solution loop, every edge
connects TYPED output and input ports, and when ports are incompatible an
**Adapter Loop** is inserted — never an anonymous conversion function on the
edge.

That last clause is the point of this module. An untyped edge with a lambda on
it is where a graph quietly stops being inspectable: the conversion has no
identity, no test, no failure attribution and no place on the canvas. An
Adapter Loop has all four, because it is a loop like any other.

Owns:
    - LoopPortRef / LoopEdgeSpec / LoopGraphSpec: the typed graph records
      (charter §26.3, and the part of drift D-2 that a live path now needs);
    - validate_graph(): port compatibility, dangling edges, unknown vertices,
      and cycles — the report IS the result, never a raised surprise;
    - adapter_needed() / insert_adapter(): where a conversion is required and
      the Adapter Loop that performs it.

Does not own:
    - execution (solution_canvas.run_solution), the runtime, or contracts.

Key invariants:
    - an edge whose ports disagree is INVALID unless an adapter is named;
    - an adapter is a loop ref, never an inline callable;
    - a vertex not in the graph's loop set is refused rather than inferred;
    - a cycle is reported, because a Solution graph is a DAG.

Verification: self_test() — compatible and incompatible edges, adapter
insertion, dangling/unknown/cyclic refusals, and the adversarial inline-lambda
path.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LoopPortRef:
    """One typed port on one Solution loop."""
    loop_id: str
    port_name: str
    contract: str = "any"

    def label(self) -> str:
        return f"{self.loop_id}.{self.port_name}:{self.contract}"


@dataclass(frozen=True)
class LoopEdgeSpec:
    """A typed connection. ``adapter_loop_ref`` names the Adapter LOOP that
    reconciles the contracts — never a function placed on the edge."""
    source: LoopPortRef
    target: LoopPortRef
    adapter_loop_ref: str = ""

    @property
    def compatible(self) -> bool:
        return (self.source.contract == self.target.contract
                or "any" in (self.source.contract, self.target.contract))


@dataclass
class LoopGraphSpec:
    """A Solution graph whose every executable vertex is a loop ref."""
    graph_id: str
    loop_refs: tuple = ()
    edges: tuple = ()
    root_output_contract: str = "any"
    graph_version: str = "1.0.0"
    _adapters: dict = field(default_factory=dict)

    def validate(self) -> dict:
        """Fail-closed validation; the report IS the result."""
        v = []
        known = set(self.loop_refs)
        if not known:
            v.append("a graph with no loops ships nothing")
        for e in self.edges:
            for side, port in (("source", e.source), ("target", e.target)):
                if port.loop_id not in known:
                    v.append(f"edge {side} {port.label()} names a loop that is "
                             "not a vertex of this graph")
            if not e.compatible and not e.adapter_loop_ref:
                v.append(
                    f"edge {e.source.label()} -> {e.target.label()} connects "
                    "incompatible contracts with no adapter loop — insert an "
                    "Adapter Loop; an anonymous conversion on the edge has no "
                    "identity, test, or failure attribution")
        cyc = self._cycle()
        if cyc:
            v.append(f"cycle detected: {' -> '.join(cyc)} — a Solution graph "
                     "is a DAG; repetition belongs inside a task-semantic loop")
        return {"valid": not v, "violations": v}

    def _cycle(self) -> list:
        adj: dict = {}
        for e in self.edges:
            adj.setdefault(e.source.loop_id, []).append(e.target.loop_id)
        seen, stack = set(), []

        def walk(n):
            if n in stack:
                return stack[stack.index(n):] + [n]
            if n in seen:
                return []
            seen.add(n)
            stack.append(n)
            for m in adj.get(n, ()):
                got = walk(m)
                if got:
                    return got
            stack.pop()
            return []

        for n in list(adj):
            got = walk(n)
            if got:
                return got
        return []

    def adapters_needed(self) -> list:
        """Edges whose contracts disagree — where an Adapter Loop belongs."""
        return [e for e in self.edges if not e.compatible]

    def to_record(self) -> dict:
        return {"record_type": "loop_graph_spec/v1", "graph_id": self.graph_id,
                "graph_version": self.graph_version,
                "loops": list(self.loop_refs),
                "edges": [{"source": e.source.label(),
                           "target": e.target.label(),
                           "adapter": e.adapter_loop_ref} for e in self.edges]}


def insert_adapter(graph: LoopGraphSpec, edge: LoopEdgeSpec, *,
                   adapter_loop_ref: str = "") -> LoopGraphSpec:
    """Reconcile one incompatible edge with a named Adapter Loop.

    The adapter is a LOOP REF, so it appears on the canvas, carries its own
    contract and mode, can fail attributably, and can be replaced — none of
    which is true of a lambda on an edge."""
    ref = adapter_loop_ref or (
        f"loop://code_intelligence/adapt.{edge.source.contract}"
        f".to.{edge.target.contract}")
    edges = tuple(LoopEdgeSpec(e.source, e.target, ref) if e is edge else e
                  for e in graph.edges)
    loops = tuple(graph.loop_refs)
    return LoopGraphSpec(graph_id=graph.graph_id, loop_refs=loops,
                         edges=edges,
                         root_output_contract=graph.root_output_contract,
                         graph_version=graph.graph_version)


def run_adapter_loop(edge: LoopEdgeSpec, value, *, convert=None, ledger=None):
    """Execute the edge's Adapter Loop — as a loop, with a fallback seam."""
    from ..loop.encapsulate import as_component_loop
    if not edge.adapter_loop_ref:
        raise ValueError("this edge names no adapter loop; an anonymous "
                         "conversion is exactly what the graph forbids")
    fn = convert or (lambda v: v)
    return as_component_loop(f"adapter {edge.adapter_loop_ref}",
                             lambda: fn(value), ledger=ledger)["value"]


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    a = LoopPortRef("prep", "out", "feature_matrix")
    b = LoopPortRef("score", "in", "feature_matrix")
    c = LoopPortRef("report", "in", "prediction_frame")

    good = LoopGraphSpec("g.ok", loop_refs=("prep", "score"),
                         edges=(LoopEdgeSpec(a, b),))
    check("a_typed_graph_with_matching_contracts_validates",
          good.validate()["valid"] and not good.adapters_needed(),
          "matching contracts need no adapter")

    # incompatible edge with NO adapter is invalid — this is the rule that
    # keeps an anonymous conversion off the edge.
    bad = LoopGraphSpec("g.bad", loop_refs=("prep", "report"),
                        edges=(LoopEdgeSpec(a, c),))
    rep = bad.validate()
    check("incompatible_contracts_without_an_adapter_are_refused",
          not rep["valid"]
          and any("Adapter Loop" in v for v in rep["violations"])
          and len(bad.adapters_needed()) == 1,
          "an anonymous conversion has no identity, test or attribution")

    fixed = insert_adapter(bad, bad.edges[0])
    check("inserting_an_adapter_loop_makes_the_graph_valid",
          fixed.validate()["valid"]
          and fixed.edges[0].adapter_loop_ref.startswith("loop://")
          and "feature_matrix.to.prediction_frame"
          in fixed.edges[0].adapter_loop_ref,
          f"adapter {fixed.edges[0].adapter_loop_ref}")

    # the adapter RUNS as a loop, with the fallback seam every component has
    from ..loop.recursive_loop import LoopLedger
    lg = LoopLedger()
    out = run_adapter_loop(fixed.edges[0], [1, 2, 3],
                           convert=lambda v: {"rows": len(v)}, ledger=lg)
    envelopes = [e for e in lg.events if e.get("event") == "init"]
    check("the_adapter_executes_as_a_loop_not_an_edge_function",
          out == {"rows": 3} and len(envelopes) == 1,
          "conversion ran inside its own envelope")

    # adversarial: dangling vertex, cycle, and a bare edge with no adapter
    dangling = LoopGraphSpec("g.dangle", loop_refs=("prep",),
                             edges=(LoopEdgeSpec(a, b),)).validate()
    cyc = LoopGraphSpec(
        "g.cyc", loop_refs=("x", "y"),
        edges=(LoopEdgeSpec(LoopPortRef("x", "o"), LoopPortRef("y", "i")),
               LoopEdgeSpec(LoopPortRef("y", "o"),
                            LoopPortRef("x", "i")))).validate()
    bare_refused = False
    try:
        run_adapter_loop(LoopEdgeSpec(a, c), [1])
    except ValueError:
        bare_refused = True
    check("dangling_vertices_cycles_and_bare_edges_are_refused",
          not dangling["valid"] and not cyc["valid"]
          and any("cycle" in v for v in cyc["violations"]) and bare_refused,
          "a graph is a DAG of known vertices with named adapters")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
