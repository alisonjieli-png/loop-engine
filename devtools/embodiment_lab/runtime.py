"""Trusted deterministic workload realization through exact canonical Loops.

This backend measures placement and lifecycle mechanics, not model reasoning.
No model response is simulated or substituted for a failed provider call.
"""

from __future__ import annotations

import os
import time
from collections import Counter

from loop_engine.core.run_history import RunHistory
from loop_engine.loop.loop_contract import LoopContract
from loop_engine.loop.loop_definition import LoopDefinition, LoopStartRequest
from loop_engine.loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from loop_engine.loop.recursive_loop import Loop, LoopConfig, LoopLedger, StepOutcome
from loop_engine.loop.runtime_context import LoopRuntimeContext

from .contracts import WorkPacket, canonical, digest


def definition(role: str = "solution") -> LoopDefinition:
    config = LoopConfig(
        framework="custom",
        custom_steps=("act",),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        max_iterations=1,
        exit_condition="accepted_success",
        power="light",
    )
    profile = (
        "solution.atomic_component" if role == "solution" else "practitioner.verifier"
    )
    return LoopDefinition.from_runtime(
        identity=LoopRoleIdentity(LoopRole(role), profile),
        contract=LoopContract(
            "embodiment mechanism",
            "code_only",
            ("embodiment_work/v1",),
            ("embodiment_result/v1",),
            ("pure",),
            role=role,
        ),
        config=config,
        definition_id="lab." + role + ".mechanism",
        version="1.0.0",
        installed_executor_modes=("deterministic",),
    )


def start_loop(request_id: str, role: str = "solution") -> Loop:
    spec = definition(role)
    return Loop(
        LoopStartRequest(
            "Execute one bounded embodiment mechanism",
            spec,
            LoopRelationship.starting(),
            LoopRuntimeContext.compatibility(
                capabilities=spec.required_capabilities,
                permissions=spec.permissions,
                executor_modes=spec.installed_executor_modes,
            ),
            LoopLedger(id_namespace=request_id),
        )
    )


def compute(packet: WorkPacket) -> object:
    values = packet.task.values
    if packet.task.operation == "sum":
        if packet.method == "batch":
            return sum(values)
        total = 0
        for value in values:
            total += value
        return total
    if packet.task.operation == "histogram":
        counts = Counter(values) if packet.method == "batch" else {}
        if packet.method != "batch":
            for value in values:
                counts[value] = counts.get(value, 0) + 1
        return [[key, counts[key]] for key in sorted(counts)]
    if packet.method == "batch":
        return list(dict.fromkeys(values))
    seen, result = set(), []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def execute(packet: WorkPacket) -> dict:
    active = start_loop(packet.request_id)
    started = time.monotonic()
    holder = {}

    def act(*_):
        holder["output"] = compute(packet)
        return StepOutcome(holder["output"], "deterministic", 1.0)

    active.run_next_iteration(handler=act)
    output = holder["output"]
    # A second call records the normal completed sequence, without repeating act.
    if not active.is_terminal:
        active.run_next_iteration(
            handler=lambda *_: StepOutcome(output, "deterministic", 1.0)
        )
    return {
        "record_type": "embodiment_candidate/v1",
        "request_id": packet.request_id,
        "task_digest": digest(packet.task.to_dict()),
        "packet_digest": digest(packet.to_dict()),
        "method": packet.method,
        "value": output,
        "value_digest": digest(output),
        "pid": os.getpid(),
        "loop_id": active.loop_id,
        "definition_ref": active.definition_ref.to_dict(),
        "elapsed_seconds": time.monotonic() - started,
        "model_calls": 0,
        "evidence_class": "deterministic_mechanism",
        "ledger": active.ledger.events,
    }


def check_candidate(packet: WorkPacket, candidate: dict) -> dict:
    """Independent controller-side oracle; expected answers never enter packets."""
    active = start_loop(packet.request_id + ".verify", "practitioner")
    values = packet.task.values
    if packet.task.operation == "sum":
        expected = sum(values[::2]) + sum(values[1::2])
    elif packet.task.operation == "histogram":
        expected = [[key, values.count(key)] for key in sorted(set(values))]
    else:
        expected = [value for i, value in enumerate(values) if value not in values[:i]]
    reason = ""
    if not isinstance(candidate, dict):
        reason = "candidate_is_not_object"
    elif candidate.get("request_id") != packet.request_id or candidate.get(
        "packet_digest"
    ) != digest(packet.to_dict()):
        reason = "request_binding_mismatch"
    elif candidate.get("task_digest") != digest(packet.task.to_dict()):
        reason = "task_binding_mismatch"
    elif candidate.get("value_digest") != digest(candidate.get("value")):
        reason = "value_digest_mismatch"
    elif canonical(candidate.get("value")) != canonical(expected):
        reason = "oracle_mismatch"
    verdict = {
        "accepted": not reason,
        "reason": reason or "independent_oracle_passed",
        "verifier_loop_id": active.loop_id,
        "task_digest": digest(packet.task.to_dict()),
        "candidate_digest": digest(candidate),
        "value_digest": digest(expected),
    }
    active.run_next_iteration(
        handler=lambda *_: StepOutcome(
            verdict, "deterministic", 1.0, failed=bool(reason)
        )
    )
    if not active.is_terminal:
        active.run_next_iteration(
            handler=lambda *_: StepOutcome(
                verdict, "deterministic", 1.0, failed=bool(reason)
            )
        )
    return {**verdict, "ledger": active.ledger.events}


def save_history(ledger: list, request_id: str, root: str) -> str:
    history = RunHistory.from_ledger(ledger, run_id=request_id)
    history.commit()
    return history.save(root)
