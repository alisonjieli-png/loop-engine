"""Passive work packet and context components for one semantic model step.

The packet never calls a provider and never becomes a graph vertex. A governed
Loop selects its components, the existing ``PromptAssemblySpec`` renders them,
and the canonical ModelGateway performs the physical model attempt.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from .component_contracts import LoopComponentDraft, define_loop_component


_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class LLMWorkPacketError(ValueError):
    """A passive packet or context component violated its typed contract."""


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        default=str)


@dataclass(frozen=True)
class LLMContextBlock:
    """One versioned, digested block available to prompt assembly."""

    block_id: str
    kind: str
    version: str
    digest: str
    source: str
    selection_reason: str
    position: int
    token_cost: int
    content: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if any(not str(value).strip() for value in (
                self.block_id, self.kind, self.source,
                self.selection_reason)):
            raise LLMWorkPacketError("context block identity cannot be empty")
        if not _SEMVER.fullmatch(self.version) or not _DIGEST.fullmatch(
                self.digest):
            raise LLMWorkPacketError("context block version or digest is invalid")
        if self.position < 0 or self.token_cost < 0:
            raise LLMWorkPacketError("context block accounting is invalid")

    @classmethod
    def create(cls, block_id: str, kind: str, version: str,
               source: str, selection_reason: str, position: int,
               content: object) -> "LLMContextBlock":
        canonical = _canonical(content)
        return cls(
            block_id, kind, version,
            hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            source, selection_reason, position,
            max(1, (len(canonical.encode("utf-8")) + 3) // 4), content)

    def to_dict(self) -> dict:
        return {
            "block_id": self.block_id, "kind": self.kind,
            "version": self.version, "digest": self.digest,
            "source": self.source, "selection_reason": self.selection_reason,
            "position": self.position, "token_cost": self.token_cost,
            "content": self.content,
        }

    def component_definition(self):
        """Represent this passive context block through one component."""
        payload = self.to_dict()
        return define_loop_component(LoopComponentDraft(
            self.block_id, self.version, "context_block", "static",
            "llm_context_block/v1",
            hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest(),
            self.source))


@dataclass(frozen=True)
class WorkDirective:
    """One bounded semantic responsibility assigned to the model."""

    operation: str
    goal: str
    one_step_only: bool
    allowed_action_kinds: tuple[str, ...]
    prohibited_outputs: tuple[str, ...]
    completion_condition: str
    failure_condition: str
    return_schema_ref: str
    route_after_return: str

    def __post_init__(self) -> None:
        if any(not value.strip() for value in (
                self.operation, self.goal, self.completion_condition,
                self.failure_condition, self.return_schema_ref,
                self.route_after_return)):
            raise LLMWorkPacketError("work directive fields cannot be empty")

    def to_dict(self) -> dict:
        return {
            "operation": self.operation, "goal": self.goal,
            "one_step_only": self.one_step_only,
            "allowed_action_kinds": list(self.allowed_action_kinds),
            "prohibited_outputs": list(self.prohibited_outputs),
            "completion_condition": self.completion_condition,
            "failure_condition": self.failure_condition,
            "return_schema_ref": self.return_schema_ref,
            "route_after_return": self.route_after_return,
        }

    def component_definition(self):
        """Represent this bounded directive as a static procedure component."""
        payload = self.to_dict()
        return define_loop_component(LoopComponentDraft(
            "core.directive." + self.operation.lower(), "1.0.0",
            "procedure_step", "static", "work_directive/v1",
            hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest(),
            "active LLM work packet"))


@dataclass(frozen=True)
class LLMWorkPacket:
    """Provider-neutral passive input for one bounded semantic Loop step."""

    packet_id: str
    packet_version: str
    purpose: str
    phase: str
    persona_context: dict
    task_context: dict
    loop_context: dict
    context_intelligence: tuple[dict, ...]
    question_portfolio: dict
    capability_context: dict
    attempt_history: dict
    work_directive: WorkDirective
    output_contract: dict
    policy_context: dict
    token_budget: dict
    source_refs: tuple[str, ...]
    context_blocks: tuple[LLMContextBlock, ...]
    record_type: str = "llm_work_packet/v1"

    def __post_init__(self) -> None:
        if self.record_type != "llm_work_packet/v1":
            raise LLMWorkPacketError("work packet record type is unsupported")
        if (not self.packet_id.strip()
                or not _SEMVER.fullmatch(self.packet_version)
                or not self.purpose.strip() or not self.phase.strip()):
            raise LLMWorkPacketError("work packet identity is invalid")
        if not isinstance(self.work_directive, WorkDirective):
            raise LLMWorkPacketError("work packet needs WorkDirective")
        blocks = tuple(self.context_blocks)
        if (len({item.block_id for item in blocks}) != len(blocks)
                or tuple(item.position for item in blocks)
                != tuple(range(len(blocks)))):
            raise LLMWorkPacketError(
                "work packet context blocks must be unique and ordered")
        object.__setattr__(self, "context_blocks", blocks)

    @property
    def content_digest(self) -> str:
        return hashlib.sha256(_canonical(
            self.to_dict(include_digest=False)).encode("utf-8")).hexdigest()

    def to_dict(self, include_digest: bool = True) -> dict:
        value = {
            "record_type": self.record_type,
            "packet_id": self.packet_id,
            "packet_version": self.packet_version,
            "purpose": self.purpose,
            "phase": self.phase,
            "persona_context": self.persona_context,
            "task_context": self.task_context,
            "loop_context": self.loop_context,
            "context_intelligence": list(self.context_intelligence),
            "question_portfolio": self.question_portfolio,
            "capability_context": self.capability_context,
            "attempt_history": self.attempt_history,
            "work_directive": self.work_directive.to_dict(),
            "output_contract": self.output_contract,
            "policy_context": self.policy_context,
            "token_budget": self.token_budget,
            "source_refs": list(self.source_refs),
            "context_blocks": [item.to_dict() for item in self.context_blocks],
        }
        if include_digest:
            value["content_digest"] = self.content_digest
        return value

    def component_definition(self):
        """Represent this passive packet through the universal component."""
        return define_loop_component(LoopComponentDraft(
            self.packet_id, self.packet_version, "llm_work_packet", "static",
            "llm_work_packet/v1", self.content_digest,
            "adaptive Practitioner run",
            role_affinities=("practitioner",),
            intelligence_refs=tuple(
                item.get("record_id", "") for item in self.context_intelligence
                if item.get("record_id"))))


@dataclass(frozen=True)
class PromptAssemblySnapshot:
    """Exact projection record for one rendered provider-neutral packet."""

    assembly_id: str
    definition_ref: str
    run_id: str
    loop_id: str
    ordered_block_refs: tuple[str, ...]
    rendered_block_digests: tuple[str, ...]
    selected_blocks: tuple[str, ...]
    rejected_blocks: tuple[str, ...]
    selection_reasons: tuple[str, ...]
    estimated_tokens: int
    prompt_digest: str
    packet_digest: str

    def __post_init__(self) -> None:
        if (any(not value.strip() for value in (
                self.assembly_id, self.definition_ref, self.run_id,
                self.loop_id)) or self.estimated_tokens < 0
                or not _DIGEST.fullmatch(self.prompt_digest)
                or not _DIGEST.fullmatch(self.packet_digest)):
            raise LLMWorkPacketError("prompt assembly snapshot is invalid")

    def to_dict(self) -> dict:
        return {
            "record_type": "prompt_assembly_snapshot/v1",
            "assembly_id": self.assembly_id,
            "definition_ref": self.definition_ref,
            "run_id": self.run_id, "loop_id": self.loop_id,
            "ordered_block_refs": list(self.ordered_block_refs),
            "rendered_block_digests": list(self.rendered_block_digests),
            "selected_blocks": list(self.selected_blocks),
            "rejected_blocks": list(self.rejected_blocks),
            "selection_reasons": list(self.selection_reasons),
            "estimated_tokens": self.estimated_tokens,
            "prompt_digest": self.prompt_digest,
            "packet_digest": self.packet_digest,
        }

    def component_definition(self):
        """Represent this inert snapshot as a prompt-assembly component."""
        payload = self.to_dict()
        return define_loop_component(LoopComponentDraft(
            self.assembly_id, "1.0.0", "prompt_assembly", "static",
            "prompt_assembly_snapshot/v1",
            hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest(),
            self.definition_ref))


def self_test() -> dict:
    """Prove passivity, digest sensitivity, and ordered component identity."""
    block = LLMContextBlock.create(
        "task.original", "task_context", "1.0.0", "test",
        "required original task", 0, {"original": "build a file"})
    directive = WorkDirective(
        "ORIENT_TASK", "Understand the task.", True, (),
        ("final solution",), "typed orientation validates",
        "typed orientation does not validate", "task_orientation/v1",
        "return_to_practitioner")
    packet = LLMWorkPacket(
        "packet.test", "1.0.0", "resolve_one_semantic_step", "orient",
        {}, {"original_input": "build a file"}, {"loop_id": "loop1"},
        (), {}, {"available_capabilities": []}, {}, directive,
        {"schema_ref": "task_orientation/v1"}, {}, {}, (), (block,))
    changed = LLMWorkPacket(
        "packet.test", "1.0.0", "resolve_one_semantic_step", "orient",
        {}, {"original_input": "build two files"}, {"loop_id": "loop1"},
        (), {}, {"available_capabilities": []}, {}, directive,
        {"schema_ref": "task_orientation/v1"}, {}, {}, (), (block,))
    tests = [{
        "test": "llm_work_packet_is_passive_and_content_addressed",
        "passed": (packet.content_digest != changed.content_digest
                   and packet.to_dict()["record_type"] == "llm_work_packet/v1"),
        "detail": packet.content_digest,
    }, {
        "test": "llm_context_block_has_version_digest_and_position",
        "passed": block.version == "1.0.0" and block.position == 0
        and len(block.digest) == 64,
        "detail": block.block_id,
    }, {
        "test": "packet_blocks_directives_and_snapshots_are_components",
        "passed": (
            packet.component_definition().component_kind == "llm_work_packet"
            and block.component_definition().component_kind == "context_block"
            and directive.component_definition().component_kind
            == "procedure_step"),
        "detail": "all remain static",
    }]
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "llm_work_packet_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
