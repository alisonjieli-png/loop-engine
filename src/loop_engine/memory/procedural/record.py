"""Procedural memory: contracted, versioned, evidence-backed know-how.

A procedural record is reusable know-how: applicability conditions,
typed contracts, permissions, verification, and evidence. Retrieving a
procedure never bypasses runtime checks. A remembered procedure still
passes current contracts, permissions, effect approvals, and
compatibility validation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from ..model.memory_type import (MemoryIdentity, MemoryProvenance,
                                 MemoryRef, MemoryScope, MemoryType,
                                 MemoryLifecycle, MemoryEvidenceRef)


@dataclass(frozen=True)
class ProceduralMemoryRecord:
    """One immutable, versioned procedural record."""

    identity: MemoryIdentity
    name: str
    purpose: str = ""
    trigger: str = ""
    applicability: str = ""
    preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    input_contract: str = ""
    output_contract: str = ""
    loop_definition_ref: str = ""
    required_capabilities: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
    allowed_effects: tuple[str, ...] = ()
    resource_requirements: dict = field(default_factory=dict)
    provider_requirements: dict = field(default_factory=dict)
    run_mode_policy: str = ""
    verification_procedure: str = ""
    rollback_behavior: str = ""
    retry_behavior: str = ""
    fallback_routes: tuple[str, ...] = ()
    repair_routes: tuple[str, ...] = ()
    idempotent: bool = False
    concurrency_requirements: str = ""
    compatibility_constraints: dict = field(default_factory=dict)
    known_limitations: tuple[str, ...] = ()
    known_failure_modes: tuple[str, ...] = ()
    performance_evidence: tuple[str, ...] = ()
    successful_episodes: tuple[str, ...] = ()
    failed_episodes: tuple[str, ...] = ()
    confidence: float = 1.0
    scope: MemoryScope = MemoryScope.PROJECT
    lifecycle: MemoryLifecycle = MemoryLifecycle.CANDIDATE
    provenance: MemoryProvenance = field(default_factory=MemoryProvenance)

    def __post_init__(self) -> None:
        if self.identity.memory_type is not MemoryType.PROCEDURAL:
            raise ValueError(
                "procedural records require memory_type 'procedural'")
        if not self.name:
            raise ValueError("procedural record needs a name")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")

    def applicable(self, context: dict) -> bool:
        """Deterministic applicability check from typed context."""
        if self.applicability:
            required = self.applicability.split(",")
            for item in required:
                key, _, want = item.partition("=")
                if context.get(key.strip()) != want.strip():
                    return False
        if self.lifecycle is not MemoryLifecycle.ACTIVE:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "identity": {
                "record_id": self.identity.record_id,
                "version": self.identity.version,
                "content_digest": self.identity.content_digest,
                "memory_type": self.identity.memory_type.value,
            },
            "name": self.name,
            "purpose": self.purpose,
            "trigger": self.trigger,
            "applicability": self.applicability,
            "preconditions": list(self.preconditions),
            "postconditions": list(self.postconditions),
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
            "loop_definition_ref": self.loop_definition_ref,
            "required_capabilities": list(self.required_capabilities),
            "required_permissions": list(self.required_permissions),
            "allowed_effects": list(self.allowed_effects),
            "resource_requirements": dict(self.resource_requirements),
            "provider_requirements": dict(self.provider_requirements),
            "run_mode_policy": self.run_mode_policy,
            "verification_procedure": self.verification_procedure,
            "rollback_behavior": self.rollback_behavior,
            "retry_behavior": self.retry_behavior,
            "fallback_routes": list(self.fallback_routes),
            "repair_routes": list(self.repair_routes),
            "idempotent": self.idempotent,
            "concurrency_requirements": self.concurrency_requirements,
            "compatibility_constraints": dict(
                self.compatibility_constraints),
            "known_limitations": list(self.known_limitations),
            "known_failure_modes": list(self.known_failure_modes),
            "performance_evidence": list(self.performance_evidence),
            "successful_episodes": list(self.successful_episodes),
            "failed_episodes": list(self.failed_episodes),
            "confidence": self.confidence,
            "scope": self.scope.value,
            "lifecycle": self.lifecycle.value,
        }

    def content_digest(self) -> str:
        serialized = json.dumps(self.to_dict(), sort_keys=True,
                                default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def self_test() -> dict:
    """Prove procedures are contracted, applicable, and evidence-backed."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    procedure = ProceduralMemoryRecord(
        identity=MemoryIdentity("mem.proc.1", "1.0.0", "a" * 64,
                                MemoryType.PROCEDURAL),
        name="repository-migration",
        purpose="migrate a package path safely",
        applicability="engine=0.9.0",
        preconditions=("clean worktree",),
        postconditions=("imports rewritten",),
        input_contract="repository_path",
        output_contract="migration_report",
        loop_definition_ref="core.proc.migrate@1.0.0",
        required_permissions=("filesystem.write",),
        verification_procedure="run full self-test",
        rollback_behavior="git restore",
        idempotent=True,
        successful_episodes=("mem.ep.success",),
        failed_episodes=("mem.ep.failure",),
        lifecycle=MemoryLifecycle.ACTIVE)
    check("procedure_is_applicable_in_matching_context",
          procedure.applicable({"engine": "0.9.0"}))
    check("procedure_is_not_applicable_in_mismatched_context",
          not procedure.applicable({"engine": "0.8.0"}))
    check("procedure_preserves_success_and_failure_evidence",
          procedure.successful_episodes == ("mem.ep.success",)
          and procedure.failed_episodes == ("mem.ep.failure",))
    check("procedure_declares_contracts",
          procedure.input_contract == "repository_path"
          and procedure.output_contract == "migration_report"
          and procedure.verification_procedure == "run full self-test")
    check("procedure_declares_permissions",
          procedure.required_permissions == ("filesystem.write",))

    inactive = ProceduralMemoryRecord(
        identity=MemoryIdentity("mem.proc.2", "1.0.0", "b" * 64,
                                MemoryType.PROCEDURAL),
        name="revoked-procedure",
        applicability="engine=0.9.0",
        lifecycle=MemoryLifecycle.REVOKED)
    check("revoked_procedure_is_not_applicable",
          not inactive.applicable({"engine": "0.9.0"}))

    try:
        ProceduralMemoryRecord(
            identity=MemoryIdentity("x", "1.0.0", "c" * 64,
                                    MemoryType.SEMANTIC),
            name="x")
        check("non_procedural_identity_is_rejected", False)
    except ValueError:
        check("non_procedural_identity_is_rejected", True)
    return {"tests": results}
