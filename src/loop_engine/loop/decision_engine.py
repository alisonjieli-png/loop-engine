"""Decision engine — the sub-layer under each of the nine kernel nodes: how should
THIS node be answered?

Owner design (2026-08-23): the practitioner loop has nine main nodes; the immediate
sub-node under each is a DECISION ENGINE (a path engine) that asks "can we solve
this node deterministically or non-deterministically?" and branches into three:

  * DETERMINISTIC — logic, embeddings, if/thens, calculations: CODE NODES only.
    Exact, zero model tokens.
  * DETERMINISTIC_WITH_LLM_REPAIR — try the deterministic path; if it errors or
    simply lacks the logic, an LLM repairs or enhances it.  A hybrid.
  * NON_DETERMINISTIC — an LLM (or another non-deterministic process).

This refines the two-rail choice (see [[asset_class.py]]: code vs string) into
three, adding the hybrid middle.  The engine decides from HEURISTICS, MEMORY (was
this node-type solved deterministically before?), POLICY (settings — model access,
internet, deterministic-first), and, when it must, a MODEL call — but the engine
itself is a deterministic code node so the choice is inspectable.  Every node gets
the same three branches, which keeps the whole architecture very organized: nine
nodes, one decision engine each, three paths under each.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..loop.kernel import KERNEL_NODES

# The three resolution paths under every node.
RESOLUTION_PATHS = ("deterministic", "deterministic_with_llm_repair",
                    "non_deterministic")
# How the engine reached its decision (recorded on every PathDecision).
DECISION_BASES = ("heuristic", "memory", "policy", "model")


@dataclass
class PathPolicy:
    """Settings that gate the paths (resolved from config / model_routes)."""
    deterministic_first: bool = True    # prefer the exact zero-token path
    allow_llm_repair: bool = True       # may an LLM repair a deterministic result?
    allow_non_deterministic: bool = True  # is any model call allowed at all?
    internet: bool = True
    det_threshold: float = 0.6          # confidence needed to go straight-deterministic


@dataclass
class PathSignals:
    """What the engine reads about ONE node's situation."""
    has_code_node: bool = False         # a deterministic method is available
    deterministic_confidence: float = 0.0  # 0..1 confidence it fully solves the node
    task_open_ended: bool = False       # inherently a judgement/open-ended node
    seen_deterministic_before: bool = False  # memory: solved deterministically before
    deterministic_may_be_incomplete: bool = False  # exists but might miss cases


@dataclass
class PathDecision:
    node: str
    path: str
    basis: str
    reason: str
    fallback_path: str = ""
    unresolved: bool = False            # no viable path under the current policy

    def __post_init__(self):
        if self.node not in KERNEL_NODES:
            raise ValueError(f"node must be one of {KERNEL_NODES}")
        if self.path not in RESOLUTION_PATHS:
            raise ValueError(f"path must be one of {RESOLUTION_PATHS}")
        if self.basis not in DECISION_BASES:
            raise ValueError(f"basis must be one of {DECISION_BASES}")


def resolve_path(node: str, signals: PathSignals, *,
                 policy: "PathPolicy | None" = None) -> PathDecision:
    """The decision engine for one node.  Deterministic and inspectable: prefer
    the exact zero-token path when a confident code node exists; fall to the
    hybrid (deterministic + LLM repair) when a deterministic method exists but may
    be incomplete; use the non-deterministic path for open-ended nodes or when no
    code node exists; and when model access is off, stay deterministic (flagging
    an unresolved gap when there is also no code node)."""
    if node not in KERNEL_NODES:
        raise ValueError(f"node must be one of {KERNEL_NODES}")
    pol = policy or PathPolicy()

    # 1. MEMORY: this node-type was solved deterministically before → deterministic.
    if signals.seen_deterministic_before and signals.has_code_node:
        return PathDecision(node, "deterministic", "memory",
                            "a code node solved this node-type before (reuse)")

    # 2. a CONFIDENT deterministic method → deterministic (exact, zero-token).
    if signals.has_code_node and not signals.deterministic_may_be_incomplete \
            and signals.deterministic_confidence >= pol.det_threshold:
        return PathDecision(node, "deterministic", "heuristic",
                            "a confident code node fully answers this node")

    # 3. a deterministic method that MAY be incomplete → deterministic + LLM repair.
    if signals.has_code_node and signals.deterministic_may_be_incomplete \
            and pol.allow_llm_repair and pol.allow_non_deterministic:
        return PathDecision(node, "deterministic_with_llm_repair", "heuristic",
                            "run the deterministic path; an LLM repairs its errors "
                            "or fills the missing logic",
                            fallback_path="non_deterministic")

    # 4. open-ended, or no code node → non-deterministic (if model access allowed).
    if (signals.task_open_ended or not signals.has_code_node) \
            and pol.allow_non_deterministic:
        # if a partial code node exists, prefer the hybrid so the LLM is anchored.
        if signals.has_code_node and pol.allow_llm_repair:
            return PathDecision(node, "deterministic_with_llm_repair", "heuristic",
                                "a partial deterministic method anchors the LLM",
                                fallback_path="non_deterministic")
        return PathDecision(node, "non_deterministic", "heuristic",
                            "open-ended or no deterministic method — use the LLM")

    # 5. model access OFF → deterministic only (or an honest unresolved gap).
    if signals.has_code_node:
        return PathDecision(node, "deterministic", "policy",
                            "model access disabled by policy — deterministic only")
    return PathDecision(node, "deterministic", "policy",
                        "no model access and no code node — abstain / build a "
                        "deterministic node first", unresolved=True)


def policy_from(config=None, route_policy=None) -> PathPolicy:
    """Resolve the path policy from the solver config (model access) and route
    policy (local/cloud) — settings like internet and model access gate the paths."""
    allow_models = True
    internet = True
    if config is not None:
        allow_models = getattr(config, "allowed_models", None) != ()
        internet = getattr(config, "internet_access", True)
    return PathPolicy(allow_non_deterministic=allow_models,
                      allow_llm_repair=allow_models, internet=internet)


def node_engines() -> dict:
    """The decision engine attached to every node — the sub-layer map: nine nodes,
    each with the same three branches.  Used by the architecture map / visual."""
    return {node: {"decision_engine": "resolve_path",
                   "branches": list(RESOLUTION_PATHS)}
            for node in KERNEL_NODES}


def engine_records() -> list:
    """The per-node decision engine as searchable node records."""
    from ..static_architecture.store_serve import StoreRecord
    recs = []
    for node in KERNEL_NODES:
        recs.append(StoreRecord(
            record_id=f"pathengine.{node}", kind="node",
            title=f"Decision engine for the '{node}' node",
            body={"node": node, "branches": list(RESOLUTION_PATHS),
                  "bases": list(DECISION_BASES),
                  "question": "deterministic, deterministic+LLM-repair, or "
                  "non-deterministic?"},
            tags=("decision_engine", "path_engine", f"step:{node}"), tier="core"))
    return recs


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. every node has the SAME three-branch sub-layer.
    eng = node_engines()
    check("every_node_has_a_three_branch_decision_engine",
          len(eng) == len(KERNEL_NODES)
          and all(e["branches"] == list(RESOLUTION_PATHS) for e in eng.values())
          and RESOLUTION_PATHS == ("deterministic",
                                   "deterministic_with_llm_repair",
                                   "non_deterministic"),
          f"{len(eng)} nodes, three paths each")

    # 2. a CONFIDENT code node → deterministic (exact, zero-token).
    d = resolve_path("verify", PathSignals(has_code_node=True,
                                           deterministic_confidence=0.9))
    check("confident_code_node_resolves_deterministic",
          d.path == "deterministic" and d.basis == "heuristic",
          f"{d.path} ({d.reason})")

    # 3. a deterministic method that MAY be incomplete → deterministic + LLM repair.
    d2 = resolve_path("how", PathSignals(has_code_node=True,
                                         deterministic_confidence=0.5,
                                         deterministic_may_be_incomplete=True))
    check("incomplete_deterministic_resolves_to_llm_repair",
          d2.path == "deterministic_with_llm_repair"
          and d2.fallback_path == "non_deterministic",
          "run deterministic, let an LLM repair errors/gaps")

    # 4. open-ended / no code node → non-deterministic (with model access).
    d3 = resolve_path("decide_next", PathSignals(has_code_node=False,
                                                 task_open_ended=True))
    check("open_ended_resolves_non_deterministic",
          d3.path == "non_deterministic",
          "no deterministic method for an open-ended node → the LLM")

    # 5. THE SETTINGS GATE: model access OFF forbids the non-deterministic path.
    off = PathPolicy(allow_non_deterministic=False, allow_llm_repair=False)
    d4 = resolve_path("decide_next", PathSignals(has_code_node=True,
                                                 task_open_ended=True), policy=off)
    d5 = resolve_path("decide_next", PathSignals(has_code_node=False,
                                                 task_open_ended=True), policy=off)
    check("model_access_off_forbids_non_deterministic",
          d4.path == "deterministic" and d4.basis == "policy"
          and d5.unresolved,
          "no models → deterministic only; no code node either → unresolved gap")

    # 6. MEMORY: solved deterministically before → deterministic (reuse).
    d6 = resolve_path("act", PathSignals(has_code_node=True,
                                         seen_deterministic_before=True,
                                         deterministic_confidence=0.3))
    check("memory_biases_toward_the_deterministic_reuse_path",
          d6.path == "deterministic" and d6.basis == "memory",
          "a node-type solved deterministically before is reused, zero-token")

    # 7. the policy is resolved from settings (model access from the config).
    class _Cfg:
        allowed_models = ()
        internet_access = True
    pol = policy_from(_Cfg())
    check("policy_reflects_settings",
          pol.allow_non_deterministic is False,
          "a no-models config disables the non-deterministic path")

    # 8. per-node decision engines are searchable.
    from ..static_architecture.store_serve import SolverStore
    store = SolverStore(core_records=engine_records())
    hit = store.search("deterministic or non deterministic path for the verify node",
                       kind="node")
    check("decision_engines_are_searchable",
          hit["hits"] and any("pathengine." in h["record_id"]
                              for h in hit["hits"]),
          "the sub-layer flows through the one search DAG")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "decision_engine_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
