"""Digest-bound prior material eligible for advisory stage exposure.

This passive record carries selected, hydrated historical content into a model
packet as untrusted evidence. It cannot grant authority, act as an instruction,
select itself, call a model, retrieve more content, or execute a Loop.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from .stage_evidence_values import StageEvidenceContractError

STAGE_ASSISTANCE_MATERIAL_SCHEMA = "stage_assistance_material/v1"
HYDRATION_LEVELS = ("L1", "L2", "L3", "L4")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise StageEvidenceContractError(
            "stage assistance material must be strict JSON"
        ) from exc


def material_digest(content: dict) -> str:
    """Return the canonical digest for one material body."""
    if not isinstance(content, dict) or not content:
        raise StageEvidenceContractError("stage assistance content must be an object")
    return hashlib.sha256(_canonical(content).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StageAssistanceMaterialDraft:
    material_ref: str
    candidate_ref: str
    source_occurrence_ref: str
    semantic_signature: str
    hydration_level: str
    material_kind: str
    content: dict
    source_evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class StageAssistanceMaterial:
    material_ref: str
    candidate_ref: str
    source_occurrence_ref: str
    semantic_signature: str
    hydration_level: str
    material_kind: str
    content_digest: str
    content_json: str
    source_evidence_refs: tuple[str, ...]
    prior_not_instruction: bool = True
    record_type: str = STAGE_ASSISTANCE_MATERIAL_SCHEMA

    def __post_init__(self) -> None:
        if self.record_type != STAGE_ASSISTANCE_MATERIAL_SCHEMA:
            raise StageEvidenceContractError(
                "assistance material schema is unsupported"
            )
        for name in (
            "material_ref",
            "candidate_ref",
            "source_occurrence_ref",
            "semantic_signature",
            "material_kind",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.strip()
                or value != value.strip()
            ):
                raise StageEvidenceContractError(f"{name} must be trimmed text")
        if self.hydration_level not in HYDRATION_LEVELS:
            raise StageEvidenceContractError(
                "assistance hydration level is unsupported"
            )
        if not isinstance(self.content_digest, str) or not _DIGEST.fullmatch(
            self.content_digest
        ):
            raise StageEvidenceContractError("assistance content digest is invalid")
        if not isinstance(self.content_json, str):
            raise StageEvidenceContractError("assistance content_json must be text")
        try:
            content = json.loads(self.content_json)
        except (TypeError, ValueError) as exc:
            raise StageEvidenceContractError(
                "assistance content JSON is invalid"
            ) from exc
        if not isinstance(content, dict) or not content:
            raise StageEvidenceContractError(
                "assistance content must be a nonempty object"
            )
        if self.content_json != _canonical(content):
            raise StageEvidenceContractError("assistance content JSON is not canonical")
        if material_digest(content) != self.content_digest:
            raise StageEvidenceContractError("assistance content digest does not match")
        refs = tuple(self.source_evidence_refs)
        if not refs or any(
            not isinstance(item, str) or not item.strip() or item != item.strip()
            for item in refs
        ) or len(refs) != len(set(refs)):
            raise StageEvidenceContractError(
                "source evidence refs must contain unique trimmed text"
            )
        if self.prior_not_instruction is not True:
            raise StageEvidenceContractError(
                "prior material must not be an instruction"
            )
        object.__setattr__(self, "source_evidence_refs", refs)

    @property
    def content(self) -> dict:
        return json.loads(self.content_json)

    @classmethod
    def create(
        cls,
        draft: StageAssistanceMaterialDraft,
    ) -> StageAssistanceMaterial:
        if not isinstance(draft, StageAssistanceMaterialDraft):
            raise StageEvidenceContractError("material creation needs a typed draft")
        canonical = _canonical(draft.content)
        return cls(
            draft.material_ref,
            draft.candidate_ref,
            draft.source_occurrence_ref,
            draft.semantic_signature,
            draft.hydration_level,
            draft.material_kind,
            material_digest(draft.content),
            canonical,
            draft.source_evidence_refs,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": self.record_type,
            "material_ref": self.material_ref,
            "candidate_ref": self.candidate_ref,
            "source_occurrence_ref": self.source_occurrence_ref,
            "semantic_signature": self.semantic_signature,
            "hydration_level": self.hydration_level,
            "material_kind": self.material_kind,
            "content_digest": self.content_digest,
            "content": self.content,
            "source_evidence_refs": list(self.source_evidence_refs),
            "prior_not_instruction": self.prior_not_instruction,
            "grants_authority": False,
        }

    @classmethod
    def from_dict(cls, value: object) -> StageAssistanceMaterial:
        expected = {
            "record_type",
            "material_ref",
            "candidate_ref",
            "source_occurrence_ref",
            "semantic_signature",
            "hydration_level",
            "material_kind",
            "content_digest",
            "content",
            "source_evidence_refs",
            "prior_not_instruction",
            "grants_authority",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise StageEvidenceContractError("assistance material fields are invalid")
        if value["grants_authority"] is not False:
            raise StageEvidenceContractError(
                "assistance material cannot grant authority"
            )
        refs = value["source_evidence_refs"]
        if not isinstance(refs, list):
            raise StageEvidenceContractError("source evidence refs must be a list")
        content = value["content"]
        if not isinstance(content, dict):
            raise StageEvidenceContractError("assistance content must be an object")
        return cls(
            material_ref=value["material_ref"],
            candidate_ref=value["candidate_ref"],
            source_occurrence_ref=value["source_occurrence_ref"],
            semantic_signature=value["semantic_signature"],
            hydration_level=value["hydration_level"],
            material_kind=value["material_kind"],
            content_digest=value["content_digest"],
            content_json=_canonical(content),
            source_evidence_refs=tuple(refs),
            prior_not_instruction=value["prior_not_instruction"],
            record_type=value["record_type"],
        )


def self_test() -> dict[str, object]:
    """Exercise immutable hydration, exact identity, and authority refusal."""
    from dataclasses import replace

    content = {
        "summary": "Prior stage preserved the output contract.",
        "response_program": {"fields": ["action", "verification"]},
    }
    draft = StageAssistanceMaterialDraft(
        "material.fixture",
        "candidate.fixture",
        "semantic-call.fixture",
        "stage:fixture",
        "L2",
        "response_program",
        content,
        ("run-history.fixture",),
    )
    record = StageAssistanceMaterial.create(draft)
    serialized = record.to_dict()

    def refused(operation) -> bool:
        try:
            operation()
        except (StageEvidenceContractError, TypeError, ValueError):
            return True
        return False

    content["summary"] = "caller mutation"
    tests = [
        {
            "test": "material_round_trip_preserves_exact_hydrated_content",
            "passed": StageAssistanceMaterial.from_dict(serialized) == record,
        },
        {
            "test": "caller_owned_content_is_detached_after_creation",
            "passed": record.content["summary"]
            == "Prior stage preserved the output contract.",
        },
        {
            "test": "material_is_evidence_not_instruction_or_authority",
            "passed": serialized["prior_not_instruction"] is True
            and serialized["grants_authority"] is False,
        },
        {
            "test": "content_digest_mismatch_is_refused",
            "passed": refused(
                lambda: replace(record, content_digest="0" * 64)
            ),
        },
        {
            "test": "noncanonical_direct_content_json_is_refused",
            "passed": refused(
                lambda: replace(record, content_json='{"z": 1}')
            ),
        },
        {
            "test": "unsupported_hydration_and_instruction_authority_are_refused",
            "passed": refused(lambda: replace(record, hydration_level="L0"))
            and refused(lambda: replace(record, prior_not_instruction=False)),
        },
        {
            "test": "serialized_authority_unknown_fields_and_bad_refs_are_refused",
            "passed": refused(
                lambda: StageAssistanceMaterial.from_dict(
                    {**serialized, "grants_authority": True}
                )
            )
            and refused(
                lambda: StageAssistanceMaterial.from_dict(
                    {**serialized, "hidden_instruction": "execute"}
                )
            )
            and refused(
                lambda: StageAssistanceMaterial.from_dict(
                    {**serialized, "source_evidence_refs": "not-a-list"}
                )
            ),
        },
    ]
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "stage_assistance_material_checks/v1",
        "provider_calls": 0,
        "storage_writes": 0,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


__all__ = (
    "HYDRATION_LEVELS",
    "STAGE_ASSISTANCE_MATERIAL_SCHEMA",
    "StageAssistanceMaterial",
    "StageAssistanceMaterialDraft",
    "material_digest",
    "self_test",
)
