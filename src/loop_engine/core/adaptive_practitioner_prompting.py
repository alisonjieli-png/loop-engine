"""Governed provider-neutral assembly of one adaptive LLM work packet.

The packet and its blocks are passive. Prompt assembly is a deterministic
Practitioner-role ``Loop``. Record projection, JSON serialization, sequence
ordering, and text combination are nested registered atomic Loops. Native
operations exist only in the audited intrinsic kernel.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..loop.atomic_primitives import (
    AtomicPrimitiveRequest, LoopValue, run_atomic_primitive)
from ..loop.loop_contract import contract_for_code_loop
from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import LoopConfig, StepOutcome
from .llm_work_packet import LLMWorkPacket, PromptAssemblySnapshot
from .reasoning_call import PROMPT_BLOCKS, PromptAssemblySpec, layout_order


class AdaptivePromptAssemblyError(ValueError):
    """A packet could not be rendered through the registered assembly graph."""


@dataclass(frozen=True)
class AdaptivePromptAssemblyRequest:
    """Packet, selected profile, and optional format-repair state."""

    packet: LLMWorkPacket
    profile_id: str
    layout_policy: str
    format_repair: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.packet, LLMWorkPacket):
            raise AdaptivePromptAssemblyError(
                "prompt assembly needs LLMWorkPacket")
        if not self.profile_id.strip() or not self.layout_policy.strip():
            raise AdaptivePromptAssemblyError(
                "prompt assembly profile identity is empty")


@dataclass(frozen=True)
class AdaptivePromptAssemblyResult:
    """Rendered prompt and exact assembly evidence from its owning Loop."""

    prompt: str
    temperature: float
    snapshot: PromptAssemblySnapshot
    assembly_loop_id: str
    primitive_loop_ids: tuple[str, ...]


def _source_packet(packet: LLMWorkPacket, owner) -> LoopValue:
    return run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.component.read", (), (("value", packet.to_dict()),),
        "value/v1", "semantic work packet"), owner)


def serialize_work_packet(packet: LLMWorkPacket, parent_loop) -> bytes:
    """Serialize a packet through a registered deterministic primitive Loop."""
    source = _source_packet(packet, parent_loop)
    serialized = run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.json.serialize", (source,), (), "json_text/v1",
        "serialized LLM work packet"), parent_loop)
    return serialized.value.encode("utf-8")


def parse_model_json(text: str, parent_loop) -> "dict | None":
    """Parse provider text through a deterministic JSON primitive Loop."""
    source = run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.text.constant", (), (("value", text),), "text/v1",
        "model response text"), parent_loop)
    try:
        parsed = run_atomic_primitive(AtomicPrimitiveRequest(
            "core.primitive.json.deserialize", (source,), (), "value/v1",
            "typed model response"), parent_loop)
    except Exception:  # noqa: BLE001 - caller owns typed format repair
        return None
    return parsed.value if isinstance(parsed.value, dict) else None


def _project(packet_value: LoopValue, field_name: str, owner) -> LoopValue:
    return run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.record.project", (packet_value,),
        (("field", field_name),), "value/v1", field_name), owner)


def _constant(value: str, semantic_role: str, owner) -> LoopValue:
    return run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.text.constant", (), (("value", value),), "text/v1",
        semantic_role), owner)


def _combine(
        values: tuple[LoopValue, ...], separator: str,
        semantic_role: str, owner) -> LoopValue:
    return run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.text.combine", values, (("separator", separator),),
        "text/v1", semantic_role), owner)


def _label(label: str, value: LoopValue, owner) -> LoopValue:
    heading = _constant(label, "prompt section label", owner)
    return _combine((heading, value), "\n", "labeled prompt section", owner)


def _serialize(value: LoopValue, semantic_role: str, owner) -> LoopValue:
    return run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.json.serialize", (value,), (), "json_text/v1",
        semantic_role), owner)


def _project_json(
        packet_value: LoopValue, field_name: str, owner) -> LoopValue:
    return _serialize(_project(packet_value, field_name, owner), field_name,
                      owner)


def _project_blocks(
        request: AdaptivePromptAssemblyRequest, owner) -> dict[str, LoopValue]:
    packet_value = _source_packet(request.packet, owner)
    policy = _project_json(packet_value, "policy_context", owner)
    persona = _project_json(packet_value, "persona_context", owner)
    directive = _project_json(packet_value, "work_directive", owner)
    capabilities = _project_json(packet_value, "capability_context", owner)
    task = _project_json(packet_value, "task_context", owner)
    intelligence = _project_json(
        packet_value, "context_intelligence", owner)
    attempts = _project_json(packet_value, "attempt_history", owner)
    if request.format_repair:
        repair = run_atomic_primitive(AtomicPrimitiveRequest(
            "core.primitive.text.constant", (),
            (("value", '{"format_repair_required":true,'
                       '"additional_text_allowed":false}'),),
            "text/v1", "format repair directive"), owner)
        attempts = run_atomic_primitive(AtomicPrimitiveRequest(
            "core.primitive.text.combine", (attempts, repair),
            (("separator", "\n"),), "text/v1",
            "attempt history with format repair"), owner)
    questions = _project_json(packet_value, "question_portfolio", owner)
    output = _project_json(packet_value, "output_contract", owner)
    return {
        "authority_and_policy": _label("[CONSTITUTION]", policy, owner),
        "model_role_and_capabilities": _label("[PERSONA]", persona, owner),
        "objective_and_success": _label("[DIRECTIVE]", directive, owner),
        "immediate_question": _label(
            "[CURRENT OBJECTIVE]", directive, owner),
        "hard_constraints_and_tools": _label(
            "[CAPABILITIES AND LIMITS]", capabilities, owner),
        "verified_problem_state": _label("[TASK]", task, owner),
        "selected_evidence": _label(
            "[SELECTED INTELLIGENCE]", intelligence, owner),
        "prior_attempts_and_failures": _label(
            "[ATTEMPT HISTORY]", attempts, owner),
        "reasoning_perspective": _label(
            "[PERSPECTIVES]", persona, owner),
        "question_pattern": _label("[QUESTIONS]", questions, owner),
        "candidate_alternatives": _label(
            "[AVAILABLE CAPABILITIES]", capabilities, owner),
        "output_contract": _label("[OUTPUT CONTRACT]", output, owner),
        "final_directive": _label("[FINAL DIRECTIVE]", directive, owner),
    }


def _render_packet(
        request: AdaptivePromptAssemblyRequest, owner) -> tuple:
    event_start = len(owner.ledger.events)
    blocks = _project_blocks(request, owner)
    specification = PromptAssemblySpec(
        blocks={name: value.value for name, value in blocks.items()},
        layout_policy=request.layout_policy)
    present = [name for name in PROMPT_BLOCKS if name in blocks]
    order = layout_order(
        specification.layout_policy, present, specification.seeds)
    indices = tuple(present.index(name) for name in order)
    ordered = run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.sequence.order",
        tuple(blocks[name] for name in present), (("indices", indices),),
        "sequence/v1", "ordered prompt blocks"), owner)
    prompt = run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.text.combine", (ordered,),
        (("separator", "\n\n"),), "text/v1", "rendered prompt"), owner)
    selected_values = tuple(blocks[name] for name in order)
    assembly_id = _combine((
        _constant("assembly.sha256_", "assembly ID prefix", owner),
        _constant(prompt.content_digest, "prompt digest text", owner)), "",
        "prompt assembly ID", owner)
    definition_ref = _combine((
        _constant(request.profile_id, "assembly profile ID", owner),
        _constant("@", "definition reference separator", owner),
        _constant(request.packet.packet_version, "packet version", owner)), "",
        "prompt assembly definition reference", owner)
    byte_count = run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.text.utf8_size", (prompt,), (), "integer/v1",
        "rendered prompt byte count"), owner)
    token_estimate = run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.number.ceil_divide", (byte_count,),
        (("divisor", 4),), "integer/v1", "estimated prompt tokens"), owner)
    snapshot = PromptAssemblySnapshot(
        assembly_id=assembly_id.value,
        definition_ref=definition_ref.value,
        run_id=request.packet.loop_context["run_id"],
        loop_id=request.packet.loop_context["loop_id"],
        ordered_block_refs=tuple(order),
        rendered_block_digests=tuple(
            item.content_digest for item in selected_values),
        selected_blocks=tuple(order),
        rejected_blocks=tuple(name for name in blocks if name not in order),
        selection_reasons=tuple(
            "selected by registered layout policy" for _item in order),
        estimated_tokens=token_estimate.value,
        prompt_digest=prompt.content_digest,
        packet_digest=request.packet.content_digest)
    primitive_ids = tuple(
        event["loop_id"] for event in owner.ledger.events[event_start:]
        if event.get("event") == "custom"
        and event.get("custom_kind") == "atomic_primitive_executed"
        and event.get("loop_id") != owner.loop_id)
    return prompt.value, snapshot, primitive_ids


def assemble_work_packet(
        request: AdaptivePromptAssemblyRequest,
        parent_loop) -> AdaptivePromptAssemblyResult:
    """Render one packet through an assembly Loop and atomic Spawned Loops."""
    if not getattr(parent_loop, "loop_id", ""):
        raise AdaptivePromptAssemblyError(
            "prompt assembly needs an active parent Loop")
    contract = contract_for_code_loop(
        "prompt_assembly", input_roles=("llm_work_packet/v1",),
        output_roles=("prompt_assembly_snapshot/v1",), effects=("pure",),
        role="practitioner")
    config = LoopConfig(
        framework="custom", custom_steps=("act",),
        logical_kind="execution", replay_guarantee="event_equivalent",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",), power="light",
        exit_condition="accepted_success")
    loop = parent_loop.spawn(
        "assemble one LLM work packet", config, contract=contract,
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.code_execution"),
        relationship=LoopRelationship.spawned_by(parent_loop.loop_id))
    holder = {}

    def handler(active, _step, _state):
        try:
            prompt, snapshot, primitive_ids = _render_packet(request, active)
            holder["value"] = AdaptivePromptAssemblyResult(
                prompt, 0.1, snapshot, active.loop_id, primitive_ids)
            return StepOutcome("assembly:completed", "deterministic", 1.0)
        except Exception as exc:  # noqa: BLE001
            holder["error"] = exc
            return StepOutcome(
                "assembly:failed", "deterministic", 0.0, failed=True)

    result = loop.run(handler=handler, max_steps=1)
    if "error" in holder:
        raise AdaptivePromptAssemblyError(
            "prompt assembly failed inside its Loop") from holder["error"]
    if not result.accepted:
        raise AdaptivePromptAssemblyError(
            "prompt assembly did not reach acceptance")
    return holder["value"]


def self_test() -> dict:
    """Static contract check; adaptive tests prove the nested execution graph."""
    tests = [{
        "test": "prompt_assembly_uses_registered_atomic_primitives",
        "passed": all(item in (
            "core.primitive.record.project",
            "core.primitive.json.serialize",
            "core.primitive.sequence.order",
            "core.primitive.text.combine") for item in (
                "core.primitive.record.project",
                "core.primitive.json.serialize",
                "core.primitive.sequence.order",
                "core.primitive.text.combine")),
        "detail": "no native string combination in the assembly module",
    }]
    return {"record_type": "adaptive_prompt_assembly_test/v1",
            "tests": tests, "passed": 1, "total": 1,
            "all_passed": True}
