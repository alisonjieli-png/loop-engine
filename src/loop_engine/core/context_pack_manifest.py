"""Context pack manifest: the exact record of what one model call could see.

Architectural role: one passive, digest-addressed record per assembled work
packet. It answers, for every model invocation, which context items entered
the packet, which were compacted, which were excluded, why, and how the
estimated input compares with the route context window and the requested
output reservation. The adaptive Practitioner builds one manifest at the single
point where a work packet leaves the process; the manifest is stored as an
artifact and referenced from the owner Loop's ledger. It never selects
context, never calls a provider, and never executes.

Owns:
    - ContextItemDecision: one included, compacted, or excluded item with its
      digest, byte counts, and reason.
    - ContextPackManifest: the versioned per-call record with counts, a fit
      verdict against the declared context window, and a content digest.
    - build_context_pack_manifest(): the deterministic projection from a work
      packet, its assembly snapshot, and the recorded context trims.

Does not own: trimming policy (core.context_budget), packet layout
(core.llm_work_packet, core.adaptive_practitioner_prompting), route context
limits (core.model_routes), or the gateway preflight (core.model_gateway).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .context_budget import ContextBudgetPolicy, ContextTrim

CONTEXT_PACK_MANIFEST_RECORD_TYPE = "context_pack_manifest/v1"

#: Decision vocabulary. ``included`` items entered the packet whole,
#: ``compacted`` items entered with a head and tail, ``excluded`` items entered
#: as a digest marker only, ``deduplicated`` items pointed at an earlier copy.
CONTEXT_DECISIONS = ("included", "compacted", "excluded", "deduplicated")

#: Trust class of an item's provenance. ``curated_intelligence`` is reviewed
#: portfolio material, ``user_input`` is the original task and answers,
#: ``run_history`` is this run's own recorded state, ``model_candidate`` is
#: unverified model output carried forward, and ``untrusted_external`` is
#: fetched or third-party text. Nothing below ``curated_intelligence`` is an
#: instruction to the model; it is data the packet quotes.
TRUST_CLASSES = ("curated_intelligence", "user_input", "run_history",
                 "model_candidate", "untrusted_external")

_BLOCK_KIND_TRUST = {
    "persona_context": "curated_intelligence",
    "context_intelligence": "curated_intelligence",
    "question_portfolio": "curated_intelligence",
    "capability_context": "curated_intelligence",
    "policy_context": "curated_intelligence",
    "task_context": "user_input",
    "attempt_trace": "run_history",
    "loop_context": "run_history",
    "web_evidence": "untrusted_external",
    "source_inspection": "untrusted_external",
}

#: Trust class of a trimmed state field, keyed by the field's first path
#: segment as the context budget records it.
_STATE_FIELD_TRUST = {
    "web_evidence": "untrusted_external",
    "source_inspections": "untrusted_external",
    "available_input_text": "user_input",
    "files_already_generated": "model_candidate",
    "project_attempts": "run_history",
}


def _state_path_trust(path: str) -> str:
    field_name = path.split(".", 1)[0].split("[", 1)[0]
    return _STATE_FIELD_TRUST.get(field_name, "run_history")

_TRIM_METHOD_TO_DECISION = {
    "head_tail": "compacted",
    "digest_only": "excluded",
    "duplicate": "deduplicated",
}


class ContextPackManifestError(ValueError):
    """A manifest or item decision violated its typed contract."""


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _estimate(byte_count: int) -> int:
    return (max(0, int(byte_count)) + 3) // 4


@dataclass(frozen=True)
class ContextItemDecision:
    """One item that was included, compacted, excluded, or deduplicated."""

    item_ref: str
    kind: str
    digest: str
    decision: str
    reason: str
    original_bytes: int
    kept_bytes: int
    trust_class: str = "run_history"

    def __post_init__(self) -> None:
        if not self.item_ref.strip() or not self.kind.strip():
            raise ContextPackManifestError("item identity cannot be empty")
        if self.trust_class not in TRUST_CLASSES:
            raise ContextPackManifestError(
                f"trust_class must be one of {TRUST_CLASSES}")
        if self.decision not in CONTEXT_DECISIONS:
            raise ContextPackManifestError(
                f"decision must be one of {CONTEXT_DECISIONS}")
        if not self.reason.strip():
            raise ContextPackManifestError("an item decision needs a reason")
        if len(self.digest) != 64 or any(
                ch not in "0123456789abcdef" for ch in self.digest):
            raise ContextPackManifestError("item digest must be sha256 hex")
        for name in ("original_bytes", "kept_bytes"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ContextPackManifestError(
                    f"{name} must be a non-negative integer")

    @property
    def removed_bytes(self) -> int:
        return max(0, self.original_bytes - self.kept_bytes)

    @property
    def kept_estimated_tokens(self) -> int:
        return _estimate(self.kept_bytes)

    def to_dict(self) -> dict:
        return {
            "item_ref": self.item_ref, "kind": self.kind,
            "digest": self.digest, "decision": self.decision,
            "reason": self.reason, "original_bytes": self.original_bytes,
            "kept_bytes": self.kept_bytes,
            "removed_bytes": self.removed_bytes,
            "kept_estimated_tokens": self.kept_estimated_tokens,
            "trust_class": self.trust_class,
        }


@dataclass(frozen=True)
class ContextPackManifest:
    """What one model call was allowed to see, and why."""

    context_pack_id: str
    run_id: str
    loop_id: str
    step_id: str
    packet_id: str
    packet_digest: str
    prompt_digest: str
    assembly_id: str
    policy_id: str
    policy_version: str
    estimated_input_tokens: int
    context_limit_tokens: "int | None"
    reserved_output_tokens: "int | None"
    operator_ceiling_tokens: "int | None"
    items: tuple[ContextItemDecision, ...]
    record_type: str = CONTEXT_PACK_MANIFEST_RECORD_TYPE

    def __post_init__(self) -> None:
        if self.record_type != CONTEXT_PACK_MANIFEST_RECORD_TYPE:
            raise ContextPackManifestError("manifest record type is unsupported")
        for name in ("context_pack_id", "run_id", "loop_id", "step_id",
                     "packet_id", "assembly_id", "policy_id",
                     "policy_version"):
            if not str(getattr(self, name)).strip():
                raise ContextPackManifestError(f"{name} cannot be empty")
        for name in ("packet_digest", "prompt_digest"):
            value = getattr(self, name)
            if len(value) != 64 or any(
                    ch not in "0123456789abcdef" for ch in value):
                raise ContextPackManifestError(f"{name} must be sha256 hex")
        if (isinstance(self.estimated_input_tokens, bool)
                or not isinstance(self.estimated_input_tokens, int)
                or self.estimated_input_tokens < 0):
            raise ContextPackManifestError(
                "estimated_input_tokens must be a non-negative integer")
        for name in ("context_limit_tokens", "reserved_output_tokens",
                     "operator_ceiling_tokens"):
            value = getattr(self, name)
            if value is not None and (
                    isinstance(value, bool) or not isinstance(value, int)
                    or value < 0):
                raise ContextPackManifestError(
                    f"{name} must be a non-negative integer or None")
        items = tuple(self.items)
        if any(not isinstance(item, ContextItemDecision) for item in items):
            raise ContextPackManifestError("items must be ContextItemDecision")
        object.__setattr__(self, "items", items)

    # --- projections -------------------------------------------------------

    def counts(self) -> dict:
        counts = {decision: 0 for decision in CONTEXT_DECISIONS}
        for item in self.items:
            counts[item.decision] += 1
        return counts

    def trust_counts(self) -> dict:
        counts = {trust: 0 for trust in TRUST_CLASSES}
        for item in self.items:
            counts[item.trust_class] += 1
        return counts

    @property
    def bytes_removed(self) -> int:
        return sum(item.removed_bytes for item in self.items)

    @property
    def fits_declared_context(self) -> "bool | None":
        """True when input plus reserved output fits the declared window.

        None when the route window is unknown at assembly time; the gateway
        preflight remains the authority for the exact selected route.
        """
        if self.context_limit_tokens is None:
            return None
        reserved = self.reserved_output_tokens or 0
        return self.estimated_input_tokens + reserved <= self.context_limit_tokens

    @property
    def within_operator_ceiling(self) -> "bool | None":
        if self.operator_ceiling_tokens is None:
            return None
        return self.estimated_input_tokens <= self.operator_ceiling_tokens

    def to_dict(self, include_digest: bool = True) -> dict:
        value = {
            "record_type": self.record_type,
            "context_pack_id": self.context_pack_id,
            "run_id": self.run_id, "loop_id": self.loop_id,
            "step_id": self.step_id, "packet_id": self.packet_id,
            "packet_digest": self.packet_digest,
            "prompt_digest": self.prompt_digest,
            "assembly_id": self.assembly_id,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "estimated_input_tokens": self.estimated_input_tokens,
            "context_limit_tokens": self.context_limit_tokens,
            "reserved_output_tokens": self.reserved_output_tokens,
            "operator_ceiling_tokens": self.operator_ceiling_tokens,
            "fits_declared_context": self.fits_declared_context,
            "within_operator_ceiling": self.within_operator_ceiling,
            "counts": self.counts(),
            "trust_counts": self.trust_counts(),
            "bytes_removed": self.bytes_removed,
            "items": [item.to_dict() for item in self.items],
        }
        if include_digest:
            value["pack_digest"] = self.pack_digest
        return value

    @property
    def pack_digest(self) -> str:
        return hashlib.sha256(_canonical(
            self.to_dict(include_digest=False)).encode("utf-8")).hexdigest()

    def summary(self) -> dict:
        """The ledger-sized projection: counts and digests, no item bodies."""
        return {
            "context_pack_id": self.context_pack_id,
            "pack_digest": self.pack_digest,
            "packet_digest": self.packet_digest,
            "prompt_digest": self.prompt_digest,
            "estimated_input_tokens": self.estimated_input_tokens,
            "context_limit_tokens": self.context_limit_tokens,
            "reserved_output_tokens": self.reserved_output_tokens,
            "fits_declared_context": self.fits_declared_context,
            "within_operator_ceiling": self.within_operator_ceiling,
            "bytes_removed": self.bytes_removed,
            **{f"{decision}_count": count
               for decision, count in self.counts().items()},
        }


def build_context_pack_manifest(
        *, run_id: str, loop_id: str, step_id: str, packet,
        snapshot: dict, trims, policy: ContextBudgetPolicy,
        context_limit_tokens: "int | None" = None,
        reserved_output_tokens: "int | None" = None) -> ContextPackManifest:
    """Project one work packet, its assembly snapshot, and its trims.

    ``packet`` is an ``LLMWorkPacket``; every context block it carries is an
    included item. ``snapshot`` is ``PromptAssemblySnapshot.to_dict()``.
    ``trims`` are the ``ContextTrim`` records the context budget produced for
    the state view that entered this packet; each becomes a compacted,
    excluded, or deduplicated item. The manifest id derives from the prompt
    digest so a replay of the same packet yields the same id.
    """
    if not isinstance(policy, ContextBudgetPolicy):
        raise ContextPackManifestError("policy must be a ContextBudgetPolicy")
    items = []
    for block in packet.context_blocks:
        block_bytes = len(_canonical(block.content).encode("utf-8"))
        items.append(ContextItemDecision(
            block.block_id, block.kind, block.digest, "included",
            block.selection_reason or "packet_block", block_bytes,
            block_bytes, _BLOCK_KIND_TRUST.get(block.kind, "run_history")))
    for trim in trims:
        if not isinstance(trim, ContextTrim):
            raise ContextPackManifestError("trims must be ContextTrim records")
        try:
            decision = _TRIM_METHOD_TO_DECISION[trim.method]
        except KeyError:
            raise ContextPackManifestError(
                f"unknown trim method {trim.method!r}") from None
        items.append(ContextItemDecision(
            trim.path, "state_text", trim.sha256, decision,
            f"context_budget.{trim.method}", trim.original_bytes,
            trim.kept_bytes, _state_path_trust(trim.path)))
    prompt_digest = str(snapshot.get("prompt_digest", ""))
    return ContextPackManifest(
        context_pack_id=f"context-pack.{prompt_digest[:16]}",
        run_id=run_id, loop_id=loop_id, step_id=step_id,
        packet_id=packet.packet_id, packet_digest=packet.content_digest,
        prompt_digest=prompt_digest,
        assembly_id=str(snapshot.get("assembly_id", "")),
        policy_id=policy.policy_id, policy_version=policy.version,
        estimated_input_tokens=int(snapshot.get("estimated_tokens", 0) or 0),
        context_limit_tokens=context_limit_tokens,
        reserved_output_tokens=reserved_output_tokens,
        operator_ceiling_tokens=policy.packet_estimated_tokens_max,
        items=tuple(items))


def self_test() -> dict:
    """Prove passivity, complete accounting, digest stability, and fit logic."""
    from .llm_work_packet import LLMContextBlock, LLMWorkPacket, WorkDirective

    block = LLMContextBlock.create(
        "task.original", "task_context", "1.0.0", "test",
        "required original task", 0, {"original": "build a file"})
    directive = WorkDirective(
        "ORIENT_TASK", "Understand the task.", True, (), ("final solution",),
        "typed orientation validates", "typed orientation does not validate",
        "task_orientation/v1", "return_to_practitioner")
    packet = LLMWorkPacket(
        "packet.test", "1.0.0", "resolve_one_semantic_step", "orient",
        {}, {"original_input": "build a file"}, {"loop_id": "loop1"},
        (), {}, {"available_capabilities": []}, {}, directive,
        {"schema_ref": "task_orientation/v1"}, {}, {}, (), (block,))
    big = "x" * 9_000
    digest = hashlib.sha256(big.encode("utf-8")).hexdigest()
    trims = (
        ContextTrim("state.selected[0].content", 9_000, 6_100, digest,
                    "head_tail"),
        ContextTrim("state.project_attempts[0].stdout", 9_000, 120, digest,
                    "digest_only"),
        ContextTrim("state.available_input_text[1].content", 9_000, 130,
                    digest, "duplicate"),
    )
    snapshot = {"prompt_digest": "a" * 64, "assembly_id": "assembly.1",
                "estimated_tokens": 2_500}
    policy = ContextBudgetPolicy()
    manifest = build_context_pack_manifest(
        run_id="run-1", loop_id="loop1", step_id="orient", packet=packet,
        snapshot=snapshot, trims=trims, policy=policy,
        context_limit_tokens=4_000, reserved_output_tokens=1_000)
    tight = build_context_pack_manifest(
        run_id="run-1", loop_id="loop1", step_id="orient", packet=packet,
        snapshot=snapshot, trims=trims, policy=policy,
        context_limit_tokens=3_000, reserved_output_tokens=1_000)
    unknown = build_context_pack_manifest(
        run_id="run-1", loop_id="loop1", step_id="orient", packet=packet,
        snapshot=snapshot, trims=trims, policy=policy)
    replay = build_context_pack_manifest(
        run_id="run-1", loop_id="loop1", step_id="orient", packet=packet,
        snapshot=snapshot, trims=trims, policy=policy,
        context_limit_tokens=4_000, reserved_output_tokens=1_000)
    counts = manifest.counts()
    rejected = 0
    for bad in (
            lambda: ContextItemDecision("x", "k", "zz", "included", "r", 1, 1),
            lambda: ContextItemDecision("x", "k", digest, "kept", "r", 1, 1),
            lambda: ContextItemDecision("x", "k", digest, "included", "", 1, 1),
            lambda: ContextItemDecision("x", "k", digest, "included", "r", -1, 1),
    ):
        try:
            bad()
        except ContextPackManifestError:
            rejected += 1
    executing = [name for name in dir(ContextPackManifest)
                 if name in ("run", "execute", "apply", "dispatch", "invoke",
                             "fetch", "write", "call")]
    trust = manifest.trust_counts()
    tests = [{
        "test": "every_item_carries_a_trust_class_and_the_task_block_is_user_input",
        "passed": (manifest.items[0].trust_class == "user_input"
                   and trust["run_history"] == 3
                   and sum(trust.values()) == len(manifest.items)
                   and manifest.to_dict()["trust_counts"] == trust),
        "detail": str(trust),
    }, {
        "test": "every_block_and_trim_becomes_exactly_one_item_decision",
        "passed": (len(manifest.items) == 4
                   and counts == {"included": 1, "compacted": 1,
                                  "excluded": 1, "deduplicated": 1}),
        "detail": str(counts),
    }, {
        "test": "bytes_removed_and_reasons_are_accounted",
        "passed": (manifest.bytes_removed == (9_000 - 6_100) + (9_000 - 120)
                   + (9_000 - 130)
                   and {item.reason for item in manifest.items
                        if item.kind == "state_text"}
                   == {"context_budget.head_tail",
                       "context_budget.digest_only",
                       "context_budget.duplicate"}),
        "detail": str(manifest.bytes_removed),
    }, {
        "test": "fit_verdict_uses_input_plus_reserved_output",
        "passed": (manifest.fits_declared_context is True
                   and tight.fits_declared_context is False
                   and unknown.fits_declared_context is None
                   and manifest.within_operator_ceiling is None),
        "detail": f"{manifest.fits_declared_context} {tight.fits_declared_context} "
                  f"{unknown.fits_declared_context}",
    }, {
        "test": "manifest_identity_is_stable_for_the_same_packet_and_trims",
        "passed": (manifest.pack_digest == replay.pack_digest
                   and manifest.context_pack_id == replay.context_pack_id
                   and manifest.pack_digest != tight.pack_digest
                   and manifest.context_pack_id.startswith("context-pack.")),
        "detail": manifest.pack_digest,
    }, {
        "test": "invalid_item_decisions_fail_closed",
        "passed": rejected == 4,
        "detail": f"{rejected}/4 rejected",
    }, {
        "test": "manifest_is_passive_and_its_summary_carries_no_bodies",
        "passed": (not executing
                   and "items" not in manifest.summary()
                   and manifest.summary()["compacted_count"] == 1
                   and manifest.to_dict()["record_type"]
                   == CONTEXT_PACK_MANIFEST_RECORD_TYPE),
        "detail": str(sorted(manifest.summary())),
    }]
    return {"module": "core.context_pack_manifest",
            "passed": all(item["passed"] for item in tests),
            "tests": tests}
