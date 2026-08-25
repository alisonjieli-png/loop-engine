"""Acceptance — the v3 universal invariants, checked across the contracts.

The per-module self-tests prove each piece.  This suite proves the pieces uphold
the v3 *universal invariants* (§29.1) when composed — the properties that must
hold no matter which resolver, context, or plane is involved.  Each check names
the invariant it defends (I-1 … I-15) and exercises more than one module, so a
regression that breaks a cross-cutting guarantee is caught here even if every
unit test still passes.
"""

from __future__ import annotations

from ..strings.knowledge import Knowledge
from ..strings.knowledge_state import Claim, EpistemicState
from ..loop.decision_need import detect_decision_need
from ..loop.moves import move, is_valid_move_kind, family_of
from ..strings.context import build_view
from ..loop.arbiter import Candidate, arbitrate, HARD_GATES
from ..loop.iteration_records import build_iteration_record, verify_chain, SolverIterationRecord
from ..strings.notes import NoteTemplate, fill_note, NoteStore
from ..loop.context_shuffle import shuffle_lanes
from .hybrid_dimension_lattice import pairwise_cover, DEFAULT_AXES

from .decision_slates import Proposal
from .research_to_capability import ResearchFinding, resolve_capability
from .escalation_governor import resolve_decision as _resolve_decision


def exploration_reachable() -> bool:
    """A history-blind / random lane is reachable at every layer: the governor
    accepts an exploration_rate, the shuffle always yields a relaxed lane, and
    the lattice always appends a blind lane."""
    import inspect
    gov_has_floor = "exploration_rate" in inspect.signature(
        _resolve_decision).parameters
    relaxed = any(f.cognition_mode == "relaxed_defocused"
                  for f in shuffle_lanes("x", n=2))
    blind = any(lane.get("_lane") == "blind_random"
                for lane in pairwise_cover(DEFAULT_AXES)["lanes"])
    return gov_has_floor and relaxed and blind


def self_test() -> dict:
    results: list[dict] = []

    def inv(iid: str, name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": f"{iid}: {name}", "passed": bool(ok),
                        "detail": detail})

    # I-2: incidental collection order cannot change semantics.
    k_a = Knowledge(goal="g", facts={"a": 1, "b": 2})
    k_b = Knowledge(goal="g", facts={"b": 2, "a": 1})
    inv("I-2", "collection_order_does_not_change_the_decision_signature",
        k_a.as_signals()["id"] == k_b.as_signals()["id"],
        "two knowledge states with the same facts in a different insertion order "
        "produce the identical decision signature — order is not semantics")

    # I-3 / I-4: search/LLM cannot legalize or authorize an invalid candidate.
    unauthorized = Candidate(
        move=Proposal("move.constructive.add", "deploy_now"),
        gates={g: True for g in HARD_GATES} | {"authority_ok": False},
        estimates={"goal_progress": 0.99})
    ok_move = Candidate(move=Proposal("run_tests", "probe"),
                        gates={g: True for g in HARD_GATES},
                        estimates={"information_value": 0.4})
    dec = arbitrate([unauthorized, ok_move])
    inv("I-4", "a_proposal_cannot_grant_itself_authority",
        dec.selected and dec.selected[0].move.action_key == "probe"
        and any(g["move"] == "deploy_now" for g in dec.gate_excluded),
        "a maximal-utility but unauthorized proposal is excluded by the hard "
        "authority gate before scoring — proposing does not authorize")

    # I-5: the evaluator cannot leak into candidate construction.
    k_sealed = Knowledge(goal="g", facts={"has_model": True,
                                          "sealed_holdout_score": 0.99})
    view = build_view(k_sealed, "sealed_evaluator_safe")
    inv("I-5", "sealed_evaluator_data_never_enters_a_context_view",
        "sealed_holdout_score" not in view.included["facts"]["keys"],
        "the sealed-evaluator-safe context strips the holdout fact, so protected "
        "evaluator data never reaches a resolver")

    # I-6 / I-9: runtime cannot mutate a frozen record invisibly; decisions are
    # replayable.
    r0 = build_iteration_record("c", 0, parent=None, knowledge_before_digest="k0",
                                 decision_need={"mode": "route"},
                                 proposals=["m"], decision={"selected": ["m"]},
                                 model_calls_made=0, model_calls_avoided=1,
                                 observations=[], knowledge_after_digest="k1")
    tampered = SolverIterationRecord(
        **{**r0.causal_payload(), "decision": {"selected": ["evil"]},
           "record_digest": r0.record_digest})
    inv("I-6", "a_frozen_record_cannot_be_mutated_invisibly",
        not verify_chain([tampered])["valid"],
        "rewriting a record's decision breaks its content-addressed digest and "
        "chain verification catches it — history cannot be silently rewritten")

    # I-7: every effect is authorized (and recorded).
    tmpl = NoteTemplate("t", "observation", required_fields=("x",))
    note = fill_note(tmpl, "practitioner", {"x": "y"})
    store = NoteStore()
    store.add(note)
    store.review(note.id, [{"quality": 0.9, "stability": 0.9, "fragility": 0.1}])
    store.promote(note.id)
    unauth = store.publish(note.id, authorized=False)
    inv("I-7", "an_external_effect_requires_authorization",
        not unauth["published"],
        "publishing an institutional note (an external effect) is refused "
        "without authorization")

    # I-8: an accepted claim carries lineage.
    claim = Claim("c1", "the split is leakage-free", "verified",
                  source_refs=("record://diag-4",))
    inv("I-8", "an_accepted_claim_carries_evidence_lineage",
        claim.is_ground() and claim.source_refs,
        "a verified (ground) claim carries a source ref — accepted knowledge has "
        "lineage")

    # I-11: semantic completion is distinct from a budget/ceiling stop.
    terminate = detect_decision_need(EpistemicState(), goal_satisfied=True)
    inv("I-11", "a_semantic_stop_is_a_distinct_mode_from_a_ceiling",
        terminate.mode == "terminate" and terminate.kind == "stop_continue",
        "a satisfied goal frames a TERMINATE decision need — a semantic stop, "
        "distinct from a runaway iteration ceiling")

    # I-13: unknown mandatory semantics fail closed.
    finding = ResearchFinding("package", "x", "cap.y", ecosystem="pypi")
    outcome = resolve_capability(finding, registry={}, verifiers={})
    inv("I-13", "unverifiable_capability_fails_closed",
        outcome.resolution == "named_gap" and not outcome.executable,
        "a nominated package with no verifier available fails closed to a named "
        "gap, never a usable capability")

    # I-14: old capabilities remain (legacy move kinds still valid).
    inv("I-14", "legacy_move_kinds_remain_valid",
        is_valid_move_kind("add_node") and family_of("add_node") == "constructive"
        and is_valid_move_kind("move.epistemic.test"),
        "the legacy flat move kind add_node is still valid and maps to its "
        "family, alongside the new namespaced kinds")

    # I-15: promotion is scoped, evidence-based, and reversible.
    fragile = fill_note(tmpl, "graph", {"x": "z"})
    store.add(fragile)
    store.review(fragile.id, [{"quality": 0.9, "stability": 0.3,
                              "fragility": 0.9}])
    frag = store.promote(fragile.id)
    inv("I-15", "promotion_is_evidence_gated",
        not frag["promoted"],
        "a fragile note fails the fragility gate and is not promoted — promotion "
        "requires evidence, it is not automatic")

    # Exploration floor: a blind/random lane is always reachable.
    inv("EXP", "a_blind_random_exploration_lane_is_always_reachable",
        exploration_reachable(),
        "the governor's exploration floor, the shuffle's relaxed lane, and the "
        "lattice's blind lane keep a history-blind path reachable at every layer")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "acceptance_invariants", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
