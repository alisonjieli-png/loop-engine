"""Run analytics — quantize what the practitioner actually did, find the pain.

Architectural role: Code Node system (behavioral analysis over ledgers).

Owns:
    - analyze_run: one loop ledger (+ provider usage log) -> per-loop and
      per-step rollups: iterations, semantic calls, tokens, wall seconds,
      fallbacks, deferrals, spawns — the du-style "which loops are most
      troublesome" numbers;
    - hotspots: the ranked worst offenders by tokens / calls / time /
      fallbacks;
    - stuck detection: repeated identical steps, fallback chains, budget
      stops, empty model outputs;
    - digestibility: model outputs that produced NO distilled keys or staged
      candidates (spend that never became reusable memory);
    - marginal-call analysis across paired records (cold vs warm, mode
      arms): did MORE calls actually buy quality?
    - propose_edits: per-hotspot improvement proposals in the housekeeping
      candidate vocabulary (staged only — never self-applied).

Does not own:
    - rendering (run_playback.py turns these numbers into transcripts,
      Mermaid, and HTML);
    - promotion (proposals are candidates through the one gate).

Public entry points:
    - analyze_run(events, usage_log=(), trace=None) -> dict
    - compare_run_records(pairs) -> dict     # marginal value of calls
    - propose_edits(analysis) -> list[dict]

Side effects and authority: pure computation over dicts; no I/O.

Key invariants:
    - a zero is a measurement only when the events could have shown nonzero;
      absent timestamps/usage yield "unknown", never fabricated numbers;
    - proposals cite the exact loop/step evidence that produced them.

Verification: self_test() (folded into the package suite).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

SEMANTIC_MODES = ("hybrid", "non_deterministic")
_RELATIONSHIP_FIELDS = (
    "spawned_by_loop_id", "queried_by_loop_id",
    "retrieved_by_loop_id", "connected_from_loop_ids")
_RELATIONSHIP_LABELS = {
    "starting": "Starting",
    "spawned_by": "Spawned by",
    "queried_by": "Queried by",
    "retrieved_by": "Retrieved by",
    "connected_from": "Connected from",
}
_RELATIONSHIP_ORDER = tuple(_RELATIONSHIP_LABELS)


@dataclass(frozen=True)
class LoopRelationshipRecord:
    """One observed Loop in the semantic relationship projection."""

    loop_id: str
    goal: str = ""
    role: str = ""
    profile_id: str = ""
    mode: str = ""
    relationship_kind: str = "unrecorded"

    def as_dict(self) -> dict:
        return {
            "loop_id": self.loop_id,
            "goal": self.goal,
            "role": self.role,
            "profile_id": self.profile_id,
            "mode": self.mode,
            "relationship_kind": self.relationship_kind,
        }


@dataclass(frozen=True)
class LoopRelationshipEdge:
    """One validated semantic edge directed from source Loop to target Loop."""

    source_loop_id: str
    target_loop_id: str
    relationship_kind: str

    def as_dict(self) -> dict:
        return {
            "source_loop_id": self.source_loop_id,
            "target_loop_id": self.target_loop_id,
            "relationship_kind": self.relationship_kind,
        }


@dataclass(frozen=True)
class LoopRelationshipDiagnostic:
    """One relationship record that could not safely become a graph edge."""

    code: str
    loop_id: str = ""
    endpoint_loop_id: str = ""
    relationship_kind: str = ""
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "loop_id": self.loop_id,
            "endpoint_loop_id": self.endpoint_loop_id,
            "relationship_kind": self.relationship_kind,
            "detail": self.detail,
        }


def _label_text(value: object) -> str:
    return (str(value).replace("&", "&amp;").replace('"', "&quot;")
            .replace("<", "&lt;").replace(">", "&gt;")
            .replace("\n", " ").strip())


@dataclass(frozen=True)
class LoopRelationshipDag:
    """Typed semantic DAG plus visible validation diagnostics."""

    vertices: tuple[LoopRelationshipRecord, ...] = ()
    edges: tuple[LoopRelationshipEdge, ...] = ()
    diagnostics: tuple[LoopRelationshipDiagnostic, ...] = ()
    acyclic: bool = True

    @property
    def complete(self) -> bool:
        return self.acyclic and not self.diagnostics

    def as_dict(self) -> dict:
        return {
            "record_type": "loop_relationship_dag/v1",
            "vertices": [item.as_dict() for item in self.vertices],
            "edges": [item.as_dict() for item in self.edges],
            "diagnostics": [item.as_dict() for item in self.diagnostics],
            "acyclic": self.acyclic,
            "complete": self.complete,
        }

    def text_lines(self) -> list[str]:
        lines = ["SEMANTIC RELATIONSHIP DAG"]
        if not self.vertices:
            return lines + ["  (no Loop relationship records)"]
        for item in self.vertices:
            label = _RELATIONSHIP_LABELS.get(
                item.relationship_kind, item.relationship_kind or "Unrecorded")
            identity = "/".join(
                value for value in (item.role, item.profile_id) if value)
            suffix = f" {identity}" if identity else ""
            lines.append(f"  {item.loop_id} [{label}]{suffix}")
        if self.edges:
            lines.append("  edges:")
            for edge in self.edges:
                label = _RELATIONSHIP_LABELS[edge.relationship_kind]
                lines.append(
                    f"    {edge.source_loop_id} -- {label} --> "
                    f"{edge.target_loop_id}")
        if self.diagnostics:
            lines.append("  diagnostics:")
            for item in self.diagnostics:
                endpoint = (f" endpoint={item.endpoint_loop_id}"
                            if item.endpoint_loop_id else "")
                lines.append(
                    f"    {item.code}: loop={item.loop_id or 'unknown'}"
                    f"{endpoint} {item.detail}".rstrip())
        return lines

    def mermaid(self) -> str:
        lines = ["flowchart TD"]
        identifiers = {
            item.loop_id: f"relationship_loop_{index}"
            for index, item in enumerate(self.vertices)}
        for item in self.vertices:
            relationship = _RELATIONSHIP_LABELS.get(
                item.relationship_kind, item.relationship_kind or "Unrecorded")
            role = f"<br/>{_label_text(item.role)}" if item.role else ""
            label = (f"{_label_text(item.loop_id)}{role}"
                     f"<br/>{_label_text(relationship)}")
            lines.append(f'  {identifiers[item.loop_id]}["{label}"]')
        for edge in self.edges:
            source = identifiers[edge.source_loop_id]
            target = identifiers[edge.target_loop_id]
            label = _label_text(_RELATIONSHIP_LABELS[edge.relationship_kind])
            lines.append(f"  {source} -->|{label}| {target}")
        for item in self.diagnostics:
            detail = _label_text(
                f"{item.code} loop={item.loop_id} "
                f"endpoint={item.endpoint_loop_id}")
            lines.append(f"  %% {detail}")
        return "\n".join(lines)


def _cycle_nodes(vertex_ids: set[str],
                 edges: tuple[LoopRelationshipEdge, ...]) -> tuple[str, ...]:
    adjacency = {loop_id: set() for loop_id in vertex_ids}
    indegree = {loop_id: 0 for loop_id in vertex_ids}
    for edge in edges:
        if edge.target_loop_id not in adjacency[edge.source_loop_id]:
            adjacency[edge.source_loop_id].add(edge.target_loop_id)
            indegree[edge.target_loop_id] += 1
    ready = sorted(loop_id for loop_id, count in indegree.items() if count == 0)
    visited = []
    while ready:
        loop_id = ready.pop(0)
        visited.append(loop_id)
        for target in sorted(adjacency[loop_id]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    return tuple(sorted(vertex_ids - set(visited)))


def loop_relationship_dag(events) -> LoopRelationshipDag:
    """Project current relationship declarations from canonical events only."""
    from ..loop.loop_role import LoopRelationship
    from ..core.run_history import (
        as_ledger_events, to_canonical_events)

    canonical = to_canonical_events(as_ledger_events(events))
    metadata: dict[str, dict[str, str]] = {}
    declarations: dict[str, set[LoopRelationship]] = defaultdict(set)
    relationship_seen = set()
    diagnostics = []
    for item in canonical:
        source = dict(item["source"])
        loop_id = str(source.get("loop_id", "") or "").strip()
        if not loop_id:
            continue
        row = metadata.setdefault(loop_id, {
            "goal": "", "role": "", "profile_id": "", "mode": ""})
        for name in row:
            value = str(source.get(name, "") or "").strip()
            if value and not row[name]:
                row[name] = value
        if "relationship_kind" not in source:
            continue
        relationship_seen.add(loop_id)
        raw_kind = source.get("relationship_kind", "")
        kind = str(getattr(raw_kind, "value", raw_kind) or "")
        payload = {"relationship_kind": kind}
        payload.update({name: source[name] for name in _RELATIONSHIP_FIELDS
                        if name in source})
        try:
            declarations[loop_id].add(LoopRelationship.from_dict(payload))
        except (TypeError, ValueError) as exc:
            diagnostics.append(LoopRelationshipDiagnostic(
                "relationship_record_invalid", loop_id,
                relationship_kind=kind,
                detail=f"{type(exc).__name__}: {str(exc)[:120]}"))

    relationship_kinds = {}
    selected_relationships = {}
    for loop_id in sorted(metadata):
        declared = declarations.get(loop_id, set())
        if len(declared) > 1:
            relationship_kinds[loop_id] = "conflict"
            diagnostics.append(LoopRelationshipDiagnostic(
                "relationship_conflict", loop_id,
                detail=f"{len(declared)} distinct declarations"))
        elif declared:
            selected = next(iter(declared))
            relationship_kinds[loop_id] = selected.kind.value
            selected_relationships[loop_id] = selected
        else:
            relationship_kinds[loop_id] = "unrecorded"
            if loop_id not in relationship_seen:
                diagnostics.append(LoopRelationshipDiagnostic(
                    "relationship_not_recorded", loop_id,
                    detail="no current relationship declaration"))

    vertices = tuple(LoopRelationshipRecord(
        loop_id, **metadata[loop_id],
        relationship_kind=relationship_kinds[loop_id])
        for loop_id in sorted(metadata))
    vertex_ids = {item.loop_id for item in vertices}
    edge_values = set()
    for loop_id, relationship in selected_relationships.items():
        kind = relationship.kind.value
        if kind == "starting":
            continue
        endpoints = {
            "spawned_by": (relationship.spawned_by_loop_id,),
            "queried_by": (relationship.queried_by_loop_id,),
            "retrieved_by": (relationship.retrieved_by_loop_id,),
            "connected_from": relationship.connected_from_loop_ids,
        }[kind]
        for endpoint in endpoints:
            if endpoint == loop_id:
                diagnostics.append(LoopRelationshipDiagnostic(
                    "relationship_self_reference", loop_id, endpoint, kind,
                    "self-referential edge rejected"))
            elif endpoint not in vertex_ids:
                diagnostics.append(LoopRelationshipDiagnostic(
                    "relationship_endpoint_unknown", loop_id, endpoint, kind,
                    "referenced Loop was not observed"))
            else:
                edge_values.add((endpoint, loop_id, kind))
    kind_index = {kind: index for index, kind in enumerate(_RELATIONSHIP_ORDER)}
    edges = tuple(LoopRelationshipEdge(*value) for value in sorted(
        edge_values, key=lambda value: (
            kind_index[value[2]], value[0], value[1])))
    cycles = _cycle_nodes(vertex_ids, edges)
    if cycles:
        diagnostics.append(LoopRelationshipDiagnostic(
            "relationship_cycle", detail=
            f"cycle includes {', '.join(cycles)}"))
    diagnostics = tuple(sorted(
        diagnostics, key=lambda item: (
            item.code, item.loop_id, item.endpoint_loop_id,
            item.relationship_kind, item.detail)))
    return LoopRelationshipDag(vertices, edges, diagnostics, not cycles)


def analyze_run(events, usage_log=(), trace: "dict | None" = None) -> dict:
    """One canonical rollup of a loop ledger (the shared-tree history)."""
    from ..core.run_history import as_ledger_events
    events = as_ledger_events(events)
    per_loop: dict = defaultdict(lambda: {
        "steps": 0, "semantic_calls": 0, "fallbacks": 0, "deferrals": 0,
        "budget_stops": 0, "spawned": 0, "empty_outputs": 0,
        "wall_seconds": None, "first_ts": None, "last_ts": None,
        "step_counts": Counter(), "goal": "", "depth": 0})
    stored_usage = []
    for e in events:
        lid = str(e.get("loop_id", "") or "")
        if not lid:
            continue
        row = per_loop[lid]
        ts = e.get("ts")
        if ts is not None:
            row["first_ts"] = ts if row["first_ts"] is None \
                else min(row["first_ts"], ts)
            row["last_ts"] = ts if row["last_ts"] is None \
                else max(row["last_ts"], ts)
        ev = e.get("event")
        if ev == "init":
            row["goal"] = e.get("goal", "")
            row["depth"] = e.get("depth", 0)
        elif ev == "run_step":
            row["steps"] += 1
            row["step_counts"][e.get("step", "?")] += 1
            if e.get("mode") in SEMANTIC_MODES:
                row["semantic_calls"] += 1
            if not e.get("output"):
                row["empty_outputs"] += 1
        elif ev == "fallback":
            row["fallbacks"] += 1
        elif ev == "model_boundary_deferred":
            row["deferrals"] += 1
        elif ev == "budget_stop":
            row["budget_stops"] += 1
        elif ev == "spawn":
            spawning_loop_id = str(
                e.get("spawning_loop_id", "")
                or e.get("spawned_by_loop_id", "") or "?")
            per_loop[spawning_loop_id]["spawned"] += 1
        elif ev == "model_invocation":
            stored_usage.append({"prompt_tokens": e.get("prompt_tokens", 0),
                                 "eval_tokens": e.get("eval_tokens", 0)})
    for row in per_loop.values():
        if row["first_ts"] is not None and row["last_ts"] is not None:
            row["wall_seconds"] = round(row["last_ts"] - row["first_ts"], 3)
        row["step_counts"] = dict(row["step_counts"])

    tokens = {"prompt": 0, "eval": 0, "calls_with_usage": 0}
    for u in (usage_log or stored_usage):
        tokens["prompt"] += int(u.get("prompt_tokens", 0) or 0)
        tokens["eval"] += int(u.get("eval_tokens", 0) or 0)
        tokens["calls_with_usage"] += 1

    # stuck signals: a step resolved more than twice in one loop, any budget
    # stop, any fallback chain, any empty model output.
    stuck = []
    for lid, row in per_loop.items():
        for step, n in row["step_counts"].items():
            if n > 2:
                stuck.append({"loop": lid, "signal": "repeated_step",
                              "step": step, "count": n})
        if row["budget_stops"]:
            stuck.append({"loop": lid, "signal": "budget_stop"})
        if row["fallbacks"] >= 2:
            stuck.append({"loop": lid, "signal": "fallback_chain",
                          "count": row["fallbacks"]})
        if row["empty_outputs"]:
            stuck.append({"loop": lid, "signal": "empty_model_output",
                          "count": row["empty_outputs"]})

    # digestibility: semantic spend that produced no reusable memory.  From
    # the trace: a research answer whose decide step fell back to the default
    # key means the advice did not distill.
    digest = {"semantic_calls": sum(r["semantic_calls"]
                                    for r in per_loop.values()),
              "undigested": 0, "notes": []}
    if trace:
        keys = trace.get("proposed_keys") or []
        if digest["semantic_calls"] and keys == ["hist_gradient_boosting"]:
            digest["undigested"] += 1
            digest["notes"].append(
                "the model's research answer distilled to nothing beyond the "
                "default estimator — spend without reusable memory")

    # the du-style hotspot ranking: troublesomeness = weighted pain.
    def pain(row):
        return (row["semantic_calls"] * 3 + row["fallbacks"] * 2
                + row["deferrals"] * 2 + row["budget_stops"] * 3
                + row["empty_outputs"] * 2
                + (row["wall_seconds"] or 0) / 10)
    hotspots = sorted(
        ({"loop": lid, **row, "pain": round(pain(row), 3)}
         for lid, row in per_loop.items()),
        key=lambda r: r["pain"], reverse=True)

    return {"record_type": "run_analysis/v1",
            "loops": dict(per_loop), "hotspots": hotspots,
            "tokens": tokens, "stuck": stuck, "digestibility": digest,
            "totals": {"loops": len(per_loop),
                       "steps": sum(r["steps"] for r in per_loop.values()),
                       "semantic_calls": digest["semantic_calls"],
                       "fallbacks": sum(r["fallbacks"]
                                        for r in per_loop.values())}}


def compare_run_records(pairs) -> dict:
    """Marginal value of calls across labeled arms of the SAME task:
    pairs = [(label, {"calls": n, "score": s, "wall": w}), ...].
    Answers 'did more calls buy quality?' — honestly, one comparison per
    pair, never a generalized claim."""
    rows = sorted(((label, d) for label, d in pairs),
                  key=lambda t: t[1].get("calls", 0))
    findings = []
    for (la, a), (lb, b) in zip(rows, rows[1:]):
        dc = b.get("calls", 0) - a.get("calls", 0)
        ds = (b.get("score") or 0) - (a.get("score") or 0)
        findings.append({
            "from": la, "to": lb, "extra_calls": dc,
            "score_delta": round(ds, 6),
            "verdict": ("calls bought quality" if dc > 0 and ds > 0 else
                        "calls bought nothing measurable" if dc > 0 else
                        "no extra calls")})
    return {"record_type": "marginal_calls/v1", "arms": dict(rows),
            "findings": findings}


def propose_edits(analysis: dict) -> list:
    """Per-hotspot improvement proposals (staged candidates, cited)."""
    out = []
    for h in analysis["hotspots"]:
        if h["pain"] <= 0:
            continue
        if h["semantic_calls"]:
            out.append({"loop": h["loop"], "kind": "code_node",
                        "proposal": "serve this loop's semantic step from a "
                                    "code node or the advice store "
                                    f"({h['semantic_calls']} calls here)",
                        "evidence": f"loop {h['loop']} pain {h['pain']}"})
        if h["fallbacks"] or h["deferrals"]:
            out.append({"loop": h["loop"], "kind": "bias",
                        "proposal": "reorder the mode waterfall or add a "
                                    "precondition — this loop fell back "
                                    f"{h['fallbacks']}x, deferred "
                                    f"{h['deferrals']}x",
                        "evidence": f"loop {h['loop']}"})
        if h["budget_stops"]:
            out.append({"loop": h["loop"], "kind": "config",
                        "proposal": "raise power or cut steps: the budget "
                                    "stopped this loop before completion",
                        "evidence": f"loop {h['loop']}"})
    for s in analysis["stuck"]:
        if s["signal"] == "repeated_step":
            out.append({"loop": s["loop"], "kind": "logic_rule",
                        "proposal": f"step '{s['step']}' resolved "
                                    f"{s['count']}x — add a completion "
                                    "precondition or distill a rule",
                        "evidence": f"loop {s['loop']}"})
    return out


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome, \
        default_handler

    # A real run with a semantic step, a fallback, and a spawned Loop.
    def handler(loop, step, context):
        if step == "research" and loop.depth == 0:
            if f"{step}:spawned" not in context:
                return StepOutcome(output="need spawned", mode="deterministic",
                                   spawn_goal="sub-research")
            return StepOutcome(output="advice", mode="hybrid", confidence=0.7)
        if step == "act" and "act" not in context:
            return StepOutcome(output="err", mode="deterministic", failed=True)
        return default_handler(loop, step, context)

    lp = Loop("analyze me", LoopConfig(framework="custom",
                                       custom_steps=("orient", "research",
                                                     "research", "research",
                                                     "act", "verify"),
                                       power="deep"))
    lp.run(handler=handler)
    usage = [{"prompt_tokens": 100, "eval_tokens": 400}]
    a = analyze_run(lp.ledger.events, usage,
                    trace={"proposed_keys": ["hist_gradient_boosting"]})

    # 1. the rollup quantizes calls, tokens, spawns, fallbacks, and wall time.
    root = a["loops"][lp.loop_id]
    check("rollup_quantizes_the_run",
          a["totals"]["semantic_calls"] >= 1
          and a["tokens"] == {"prompt": 100, "eval": 400,
                              "calls_with_usage": 1}
          and root["spawned"] == 1 and root["fallbacks"] >= 1
          and isinstance(root["wall_seconds"], float),
          f"root: {root['steps']} steps, {root['semantic_calls']} calls, "
          f"{root['wall_seconds']}s")

    # 2. hotspots rank by pain; the root (calls+fallbacks) outranks the
    # clean spawned Loop.
    check("hotspots_rank_troublesome_loops_first",
          a["hotspots"][0]["loop"] == lp.loop_id
          and a["hotspots"][0]["pain"] > a["hotspots"][-1]["pain"])

    # 3. stuck + digestibility signals fire on real shapes.
    check("stuck_and_digestibility_signals_fire",
          any(s["signal"] == "repeated_step" and s["step"] == "research"
              for s in a["stuck"])
          and a["digestibility"]["undigested"] == 1,
          "repeated research + advice that distilled to the default")

    # 4. proposals cite their evidence and stay in candidate vocabulary.
    props = propose_edits(a)
    check("proposals_are_cited_candidates",
          props and all(p.get("evidence") for p in props)
          and any(p["kind"] == "code_node" for p in props)
          and any(p["kind"] == "logic_rule" for p in props))

    # 5. marginal-call comparison answers 'did calls buy quality?' honestly.
    cmp = compare_run_records([
        ("deterministic", {"calls": 0, "score": 0.8294}),
        ("hybrid", {"calls": 1, "score": 0.8294}),
        ("model_led", {"calls": 1, "score": 0.8339})])
    verdicts = [f["verdict"] for f in cmp["findings"]]
    check("marginal_call_analysis_is_honest",
          "calls bought nothing measurable" in verdicts[0]
          and len(cmp["findings"]) == 2,
          f"{verdicts}")

    # Service metadata without a Loop identity must not create a blank graph
    # vertex in reports or Mermaid output.
    without_blank = analyze_run((
        {"event": "custom", "loop_id": "", "ts": 1.0},
        {"event": "init", "loop_id": "loop1", "ts": 2.0},
    ))
    check("empty_loop_identity_does_not_create_a_display_vertex",
          tuple(without_blank["loops"]) == ("loop1",)
          and without_blank["totals"]["loops"] == 1)

    # All five semantic relationships survive the saved-history adapter. The
    # connected Solution has two explicit input edges, including an adapter
    # Loop, rather than one hidden connection.
    from ..core.run_history import RunHistory
    relationship_events = (
        {"event": "init", "loop_id": "start", "goal": "build",
         "role": "practitioner", "profile_id": "practitioner.solver",
         "relationship_kind": "starting"},
        {"event": "init", "loop_id": "spawned", "goal": "research",
         "role": "practitioner", "profile_id": "practitioner.research",
         "relationship_kind": "spawned_by",
         "spawned_by_loop_id": "start"},
        {"event": "init", "loop_id": "query", "goal": "search",
         "role": "intelligence", "profile_id": "intelligence.search",
         "relationship_kind": "queried_by",
         "queried_by_loop_id": "start"},
        {"event": "init", "loop_id": "item", "goal": "materialize",
         "role": "intelligence", "profile_id": "intelligence.materialize",
         "relationship_kind": "retrieved_by",
         "retrieved_by_loop_id": "query"},
        {"event": "init", "loop_id": "adapter", "goal": "adapt value",
         "role": "solution", "profile_id": "solution.atomic_component",
         "relationship_kind": "starting"},
        {"event": "init", "loop_id": "solution", "goal": "run solution",
         "role": "solution", "profile_id": "solution.pipeline",
         "relationship_kind": "connected_from",
         "connected_from_loop_ids": ("start", "adapter")},
        {"event": "custom", "loop_id": "", "relationship_kind": "starting"},
    )
    adapted = RunHistory.from_ledger(
        relationship_events, run_id="relationship-adapter")
    relationship_dag = loop_relationship_dag(adapted.event_log)
    relationship_edges = {
        (edge.source_loop_id, edge.target_loop_id, edge.relationship_kind)
        for edge in relationship_dag.edges}
    check("all_five_relationships_and_connection_edges_are_projected",
          relationship_dag.complete and relationship_dag.acyclic
          and len(relationship_dag.vertices) == 6
          and relationship_edges == {
              ("start", "spawned", "spawned_by"),
              ("start", "query", "queried_by"),
              ("query", "item", "retrieved_by"),
              ("start", "solution", "connected_from"),
              ("adapter", "solution", "connected_from"),
          }
          and {item.relationship_kind for item in relationship_dag.vertices}
          == set(_RELATIONSHIP_ORDER)
          and all(item.loop_id for item in relationship_dag.vertices)
          and '["<br/>' not in relationship_dag.mermaid())

    adversarial_dag = loop_relationship_dag((
        {"event": "init", "loop_id": "start",
         "relationship_kind": "starting"},
        {"event": "init", "loop_id": "conflict",
         "relationship_kind": "starting"},
        {"event": "custom", "loop_id": "conflict",
         "relationship_kind": "spawned_by",
         "spawned_by_loop_id": "start"},
        {"event": "init", "loop_id": "orphan",
         "relationship_kind": "queried_by",
         "queried_by_loop_id": "not-observed"},
        {"event": "init", "loop_id": "missing",
         "relationship_kind": "connected_from"},
        {"event": "init", "loop_id": "self",
         "relationship_kind": "connected_from",
         "connected_from_loop_ids": ("self",)},
        {"event": "init", "loop_id": "cycle-a",
         "relationship_kind": "connected_from",
         "connected_from_loop_ids": ("cycle-b",)},
        {"event": "init", "loop_id": "cycle-b",
         "relationship_kind": "connected_from",
         "connected_from_loop_ids": ("cycle-a",)},
        {"event": "custom", "loop_id": ""},
    ))
    diagnostic_codes = {item.code for item in adversarial_dag.diagnostics}
    check("invalid_relationships_are_visible_without_implicit_vertices",
          not adversarial_dag.complete and not adversarial_dag.acyclic
          and {"relationship_conflict", "relationship_endpoint_unknown",
               "relationship_record_invalid", "relationship_self_reference",
               "relationship_cycle"} <= diagnostic_codes
          and all(item.loop_id for item in adversarial_dag.vertices)
          and "not-observed[" not in adversarial_dag.mermaid()
          and any("diagnostics:" in line
                  for line in adversarial_dag.text_lines()))

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
