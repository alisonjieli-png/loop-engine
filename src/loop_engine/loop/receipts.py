"""Receipts — one causal record per loop iteration, chained for replay (v3 §20).

Every SolverCell iteration produces one ``SolverIterationReceipt`` that links
what was known before, why a decision was open, what was proposed, what was
decided, what ran, what was observed, and what is known after — plus a link to
the previous iteration's receipt.  The chain is content-addressed: each receipt's
digest covers its own causal fields *and* the previous receipt's digest, so a
tampered or reordered history is detectable and a run is replayable.

The receipt keeps the plane separations honest: a proposal is recorded as
advice, a decision as an authorized selection, an observation as what happened —
none is interchangeable, and none silently rewrites another.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class SolverIterationReceipt:
    cell_id: str
    iteration: int
    parent_digest: str
    knowledge_before_digest: str
    decision_need: dict
    proposals: tuple[str, ...]           # move keys proposed
    decision: dict                       # the NextMoveDecision, as a dict
    model_calls_made: int
    model_calls_avoided: int
    observations: tuple[str, ...]        # observation refs
    knowledge_after_digest: str
    resources: dict = field(default_factory=dict)
    terminal_state: str = ""
    receipt_digest: str = ""

    def causal_payload(self) -> dict:
        """The fields the digest covers (everything except the digest itself)."""
        return {"cell_id": self.cell_id, "iteration": self.iteration,
                "parent_digest": self.parent_digest,
                "knowledge_before_digest": self.knowledge_before_digest,
                "decision_need": self.decision_need,
                "proposals": list(self.proposals), "decision": self.decision,
                "model_calls_made": self.model_calls_made,
                "model_calls_avoided": self.model_calls_avoided,
                "observations": list(self.observations),
                "knowledge_after_digest": self.knowledge_after_digest,
                "resources": self.resources,
                "terminal_state": self.terminal_state}

    def to_dict(self) -> dict:
        d = self.causal_payload()
        d["record_type"] = "solver_iteration_receipt/v1"
        d["receipt_digest"] = self.receipt_digest
        return d


def build_iteration_receipt(
        cell_id: str, iteration: int, *, parent: "SolverIterationReceipt | None",
        knowledge_before_digest: str, decision_need: Mapping[str, Any],
        proposals: Sequence[str], decision: Mapping[str, Any],
        model_calls_made: int, model_calls_avoided: int,
        observations: Sequence[str], knowledge_after_digest: str,
        resources: Mapping[str, Any] | None = None,
        terminal_state: str = "") -> SolverIterationReceipt:
    """Build a receipt whose digest chains to its parent."""
    parent_digest = parent.receipt_digest if parent is not None else ""
    receipt = SolverIterationReceipt(
        cell_id=cell_id, iteration=iteration, parent_digest=parent_digest,
        knowledge_before_digest=knowledge_before_digest,
        decision_need=dict(decision_need), proposals=tuple(proposals),
        decision=dict(decision), model_calls_made=model_calls_made,
        model_calls_avoided=model_calls_avoided,
        observations=tuple(observations),
        knowledge_after_digest=knowledge_after_digest,
        resources=dict(resources or {}), terminal_state=terminal_state)
    object.__setattr__(receipt, "receipt_digest",
                       _digest(receipt.causal_payload()))
    return receipt


def verify_chain(chain: Sequence[SolverIterationReceipt]) -> dict:
    """Verify a receipt chain: each digest recomputes, each parent link matches,
    and iterations are contiguous.  Returns the first break if any."""
    for i, r in enumerate(chain):
        if _digest(r.causal_payload()) != r.receipt_digest:
            return {"valid": False, "broken_at": i,
                    "reason": "receipt digest does not recompute (tampered)"}
        expected_parent = chain[i - 1].receipt_digest if i > 0 else ""
        if r.parent_digest != expected_parent:
            return {"valid": False, "broken_at": i,
                    "reason": "parent link does not match the prior receipt"}
        if i > 0 and r.iteration != chain[i - 1].iteration + 1:
            return {"valid": False, "broken_at": i,
                    "reason": "iterations are not contiguous"}
    return {"valid": True, "length": len(chain),
            "head_digest": chain[-1].receipt_digest if chain else ""}


# ---------------------------------------------------------------------------
# Self-test — deterministic.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    r0 = build_iteration_receipt(
        "cell.task", 0, parent=None, knowledge_before_digest="k0",
        decision_need={"mode": "investigate"}, proposals=["run_tests:leakage"],
        decision={"selected": ["run_tests:leakage"]}, model_calls_made=0,
        model_calls_avoided=3, observations=["obs.0"],
        knowledge_after_digest="k1")
    r1 = build_iteration_receipt(
        "cell.task", 1, parent=r0, knowledge_before_digest="k1",
        decision_need={"mode": "route"}, proposals=["add_node:hgb"],
        decision={"selected": ["add_node:hgb"]}, model_calls_made=1,
        model_calls_avoided=2, observations=["obs.1"],
        knowledge_after_digest="k2")

    check("receipts_chain_and_carry_the_causal_fields",
          r0.receipt_digest and r1.parent_digest == r0.receipt_digest
          and r1.knowledge_before_digest == r0.knowledge_after_digest,
          "each receipt links to its parent's digest, and iteration 1's "
          "knowledge-before matches iteration 0's knowledge-after — the causal "
          "chain is intact")

    verdict = verify_chain([r0, r1])
    check("a_valid_chain_verifies",
          verdict["valid"] and verdict["length"] == 2,
          "the two-receipt chain verifies: digests recompute and parent links "
          "match")

    # Tamper: mutate a receipt's decision after the fact -> digest breaks.
    tampered = SolverIterationReceipt(
        **{**r1.causal_payload(),
           "decision": {"selected": ["deploy_now"]},   # secretly changed
           "receipt_digest": r1.receipt_digest})
    bad = verify_chain([r0, tampered])
    check("a_tampered_receipt_is_detected",
          not bad["valid"] and bad["broken_at"] == 1
          and "tampered" in bad["reason"],
          "rewriting a receipt's decision after the fact breaks its digest and "
          "the chain verification catches it — history cannot be silently "
          "rewritten")

    # Reorder: swapping receipts breaks the parent links.
    reordered = verify_chain([r1, r0])
    check("a_reordered_chain_is_detected",
          not reordered["valid"],
          "swapping the order of receipts breaks the parent links and is "
          "caught")

    # Determinism.
    r0b = build_iteration_receipt(
        "cell.task", 0, parent=None, knowledge_before_digest="k0",
        decision_need={"mode": "investigate"}, proposals=["run_tests:leakage"],
        decision={"selected": ["run_tests:leakage"]}, model_calls_made=0,
        model_calls_avoided=3, observations=["obs.0"],
        knowledge_after_digest="k1")
    check("receipt_digests_are_deterministic",
          r0b.receipt_digest == r0.receipt_digest,
          "the same causal fields always produce the identical receipt digest — "
          "replayable")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "receipts_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
