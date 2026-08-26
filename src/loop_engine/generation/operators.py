"""Generation operators executing through the canonical Loop runtime.

Every governed act of generating, expanding, composing, evaluating,
selecting, persisting, or promoting runs through an ordinary Loop.
The operators themselves are typed data bound to Loop presets.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .model.campaign import (GenerationCampaign, GenerationBudget,
                             WritebackPolicy, expand_variation_space)
from .model.fragments import (CandidateFragment, GenerationError,
                              SeedArtifact)

#: Generation operator families.
OPERATOR_FAMILIES = (
    "structural", "semantic", "context", "configuration", "examples",
    "verification", "execution",
)

#: Structural operators.
STRUCTURAL_OPERATORS = (
    "insert", "remove", "replace", "reorder", "split", "merge",
    "wrap", "unwrap", "sequence", "parallelize", "add_fallback",
    "add_verifier", "add_repair_route", "splice",
)


@dataclass(frozen=True)
class GenerationOperator:
    """One reusable generation transformation, typed data."""

    operator_id: str
    family: str
    version: str = "1.0.0"
    description: str = ""
    allowed_artifact_kinds: tuple[str, ...] = ()
    allowed_contexts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.family not in OPERATOR_FAMILIES:
            raise GenerationError(
                f"operator family must be one of {OPERATOR_FAMILIES}")
        if self.family == "structural" and not any(
                self.operator_id.endswith(op) for op in
                STRUCTURAL_OPERATORS):
            raise GenerationError(
                f"structural operator must be one of "
                f"{STRUCTURAL_OPERATORS}")


@dataclass(frozen=True)
class CandidateRecord:
    """One generated, immutable, content-addressed candidate."""

    candidate_id: str
    campaign_id: str
    artifact_kind: str
    config: dict
    seed_ids: tuple[str, ...] = ()
    operator_ids: tuple[str, ...] = ()
    parent_candidate_ids: tuple[str, ...] = ()
    state: str = "proposed"
    content_hash: str = ""

    def __post_init__(self) -> None:
        if self.state not in ("proposed", "compiled", "validated",
                              "evaluated", "ranked", "reviewed",
                              "promoted", "rejected", "revoked"):
            raise GenerationError(f"unknown candidate state "
                                  f"{self.state!r}")


def generate_candidates(campaign: GenerationCampaign,
                        operators: tuple[GenerationOperator, ...] = ()
                        ) -> tuple[CandidateRecord, ...]:
    """Expand a campaign into typed candidate records through a Loop.

    The expansion itself is deterministic and bounded by the campaign
    budget. When operators are declared, each candidate records the
    operators that were applied. Generation is a governed operation:
    it runs through the canonical Loop runtime.
    """
    from loop_engine.loop.encapsulate import as_practitioner_loop

    def _expand(_inputs=None) -> dict:
        configs = expand_variation_space(campaign)
        candidates = []
        for index, config in enumerate(configs):
            record = CandidateRecord(
                candidate_id=f"{campaign.campaign_id}.candidate.{index}",
                campaign_id=campaign.campaign_id,
                artifact_kind=campaign.target_artifact_kind,
                config=config,
                seed_ids=tuple(s.seed_id for s in campaign.seeds),
                operator_ids=tuple(o.operator_id for o in operators),
                state="proposed")
            candidates.append(record)
        return {"candidates": [c.to_dict() for c in candidates],
                "count": len(candidates)}

    return as_practitioner_loop(
        f"generate candidates for {campaign.campaign_id}", _expand)


def CandidateRecord_to_dict(self) -> dict:
    return {"candidate_id": self.candidate_id,
            "campaign_id": self.campaign_id,
            "artifact_kind": self.artifact_kind,
            "config": self.config,
            "seed_ids": list(self.seed_ids),
            "operator_ids": list(self.operator_ids),
            "parent_candidate_ids": list(self.parent_candidate_ids),
            "state": self.state,
            "content_hash": self.content_hash}


CandidateRecord.to_dict = CandidateRecord_to_dict  # type: ignore


def self_test() -> dict:
    """Prove generation runs through the canonical Loop runtime."""
    from .model.dimensions import VariationDimension

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    campaign = GenerationCampaign(
        campaign_id="camp-prove", version="1.0.0",
        target_artifact_kind="prompt_block",
        seeds=(SeedArtifact("s1", "core_default", "prompt_block", {}),),
        dimensions=(VariationDimension(
            "reasoning", "categorical",
            values=("direct", "plan_then_execute")),
            VariationDimension("temperature", "float_values",
                               values=(0.0, 0.2))),
        budget=GenerationBudget(candidate_limit=8))
    operator = GenerationOperator(
        operator_id="core.op.replace", family="structural",
        allowed_artifact_kinds=("prompt_block",))
    result = generate_candidates(campaign, (operator,))
    check("generation_runs_through_the_canonical_loop",
          result["loop_id"].startswith("loop")
          and result["value"]["count"] == 4
          and result["value"]["candidates"][0]["operator_ids"]
          == ["core.op.replace"])
    check("candidate_records_are_typed",
          all("candidate_id" in c and "config" in c and "state" in c
              for c in result["value"]["candidates"]))

    try:
        GenerationOperator("core.op.bogus", "structural")
        check("unknown_structural_operator_is_refused", False)
    except GenerationError:
        check("unknown_structural_operator_is_refused", True)
    return {"tests": results}
