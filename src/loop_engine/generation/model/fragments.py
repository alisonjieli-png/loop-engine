"""Generation model: seeds, fragments, and typed combination semantics.

A seed is data. A fragment is the smallest typed unit a generation
operator may transform or compose. Different artifact kinds have
different combination semantics; there is no generic deep-merge.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

#: Artifact kinds a candidate fragment may target.
FRAGMENT_KINDS = (
    "string", "prompt_block", "context_block", "example_set",
    "config_patch", "query_fragment", "contract_fragment",
    "policy_fragment", "procedure_fragment", "graph_fragment",
    "tool_binding_fragment", "verification_fragment",
    "routing_fragment", "service_binding_fragment",
)

#: Seed source profiles.
SEED_SOURCES = (
    "literal", "core_default", "historical_champion",
    "historical_failure", "current_production", "user_preference",
    "project_preference", "analogy", "first_principles",
    "counterexample", "adversarial", "minimal", "novelty",
)


class GenerationError(ValueError):
    """A generation model violated its contract."""


@dataclass(frozen=True)
class SeedArtifact:
    """Starting material for generation. Data, never a Node."""

    seed_id: str
    source: str
    artifact_kind: str
    content: object
    version: str = "1.0.0"
    provenance: str = ""
    content_hash: str = ""

    def __post_init__(self) -> None:
        if self.source not in SEED_SOURCES:
            raise GenerationError(
                f"seed source must be one of {SEED_SOURCES}")
        if self.artifact_kind not in FRAGMENT_KINDS:
            raise GenerationError(
                f"artifact_kind must be one of {FRAGMENT_KINDS}")

    def digest(self) -> str:
        serialized = json.dumps(
            {"seed_id": self.seed_id, "source": self.source,
             "artifact_kind": self.artifact_kind,
             "content": self.content, "version": self.version},
            sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CandidateFragment:
    """Smallest typed unit a generation operator may transform."""

    fragment_id: str
    artifact_kind: str
    content: object
    version: str = "1.0.0"
    input_contract: str = ""
    output_contract: str = ""
    compatible_targets: tuple[str, ...] = ()
    required_fragments: tuple[str, ...] = ()
    conflicting_fragments: tuple[str, ...] = ()
    ordering_constraints: tuple[str, ...] = ()
    merge_semantics: str = "replace"
    provenance: str = ""
    parent_fragment_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.artifact_kind not in FRAGMENT_KINDS:
            raise GenerationError(
                f"artifact_kind must be one of {FRAGMENT_KINDS}")
        if self.merge_semantics not in ("replace", "overlay", "append",
                                        "conjoin", "explicit"):
            raise GenerationError(
                "merge_semantics must be replace, overlay, append, "
                "conjoin, or explicit")

    def content_digest(self) -> str:
        serialized = json.dumps(
            {"fragment_id": self.fragment_id,
             "artifact_kind": self.artifact_kind,
             "content": self.content, "version": self.version,
             "merge_semantics": self.merge_semantics},
            sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StringFragment:
    """A typed string fragment: ordered assembly, not free concatenation."""

    text: str
    block_role: str = "body"
    priority: int = 0
    constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.block_role not in ("system", "constitution", "role",
                                   "objective", "task", "context", "memory",
                                   "evidence", "constraints", "examples",
                                   "reasoning", "output_contract",
                                   "verification", "body"):
            raise GenerationError(f"unknown block_role {self.block_role!r}")


@dataclass(frozen=True)
class PromptBlock:
    """One structured block of a model invocation prompt."""

    block_id: str
    block_role: str
    fragments: tuple[StringFragment, ...] = ()
    order: int = 0
    optional: bool = False

    def __post_init__(self) -> None:
        if self.block_role not in ("system", "constitution", "role",
                                   "objective", "task", "context", "memory",
                                   "evidence", "constraints", "examples",
                                   "reasoning", "output_contract",
                                   "verification"):
            raise GenerationError(f"unknown block_role {self.block_role!r}")

    def render(self) -> str:
        """Render the block deterministically from its fragments."""
        parts = sorted(self.fragments, key=lambda f: f.priority)
        return "\n".join(f.text for f in parts)


@dataclass(frozen=True)
class ConfigPatch:
    """A typed configuration patch with declared merge semantics."""

    patch_id: str
    values: dict
    merge_semantics: str = "overlay"
    frozen_fields: tuple[str, ...] = ()
    compatible_schema_versions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.merge_semantics not in ("overlay", "replace", "append"):
            raise GenerationError(
                "merge_semantics must be overlay, replace, or append")

    def apply_to(self, base: dict) -> dict:
        """Apply the patch to a base configuration."""
        if self.merge_semantics == "replace":
            return dict(self.values)
        merged = dict(base)
        for key, value in self.values.items():
            if key in self.frozen_fields:
                continue
            if self.merge_semantics == "append" and key in merged \
                    and isinstance(merged[key], list) \
                    and isinstance(value, list):
                merged[key] = merged[key] + value
            else:
                merged[key] = value
        return merged


def self_test() -> dict:
    """Prove seeds, fragments, and patches are typed and deterministic."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    seed = SeedArtifact("seed-1", "core_default", "prompt_block",
                        {"role": "classifier"})
    check("seed_is_typed_data", seed.digest() == seed.digest()
          and seed.source == "core_default")
    try:
        SeedArtifact("x", "bogus_source", "string", "x")
        check("unknown_seed_source_is_refused", False)
    except GenerationError:
        check("unknown_seed_source_is_refused", True)

    fragment = CandidateFragment(
        "frag-1", "prompt_block", {"role": "classifier"},
        parent_fragment_ids=("seed-1",))
    check("fragment_has_deterministic_digest",
          fragment.content_digest() == fragment.content_digest())
    try:
        CandidateFragment("f", "bogus_kind", {})
        check("unknown_fragment_kind_is_refused", False)
    except GenerationError:
        check("unknown_fragment_kind_is_refused", True)

    block = PromptBlock(
        "block-1", "role",
        fragments=(StringFragment("You are a support classifier."),),
        order=0)
    check("prompt_block_renders_deterministically",
          block.render() == "You are a support classifier.")
    try:
        PromptBlock("b", "bogus_role")
        check("unknown_block_role_is_refused", False)
    except GenerationError:
        check("unknown_block_role_is_refused", True)

    patch = ConfigPatch("patch-1",
                        {"temperature": 0.0, "verifier": "schema"},
                        frozen_fields=("verifier",))
    result = patch.apply_to({"temperature": 0.5, "verifier": "none",
                             "model": "a"})
    check("config_patch_overlays_with_frozen_fields",
          result["temperature"] == 0.0
          and result["verifier"] == "none"
          and result["model"] == "a")
    return {"tests": results}
