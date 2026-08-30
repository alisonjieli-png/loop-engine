"""Procedure-scoped lifecycle extensions and execution-context fingerprints.

Definitions are passive and exact. Resolution is deterministic Intelligence
work over the canonical LoopDefinition registry and Run History vocabulary.
No global hook list or extension runtime is introduced.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum

from ..code_nodes.solution_graph import LoopDefinitionRegistry
from ..loop.loop_definition import LoopDefinitionRef
from .development_planning import ResolutionDisposition


class LifecycleExtensionError(ValueError):
    """Lifecycle extension or fingerprint resolution failed closed."""


class ExtensionExecutionMode(str, Enum):
    SINGLE = "single"
    BATCH = "batch"


class DriftDisposition(str, Enum):
    UNCHANGED = "unchanged"
    COMPATIBLE_CHANGE = "compatible_change"
    REQUIRES_REVALIDATION = "requires_revalidation"
    REQUIRES_REPLAN = "requires_replan"
    REQUIRES_APPROVAL = "requires_approval"
    HARD_STOP = "hard_stop"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class ProcedureLifecycleDefinition:
    procedure_id: str
    version: str
    supported_events: tuple[str, ...]

    def __post_init__(self):
        if not self.procedure_id or not self.version or not self.supported_events:
            raise LifecycleExtensionError("procedure lifecycle is incomplete")
        if len(self.supported_events) != len(set(self.supported_events)):
            raise LifecycleExtensionError("procedure lifecycle events repeat")


@dataclass(frozen=True)
class LifecycleExtensionDefinition:
    extension_id: str
    version: str
    lifecycle_event: str
    order: int
    execution_mode: ExtensionExecutionMode | str
    loop_definition_ref: LoopDefinitionRef
    input_contract_ref: str
    output_contract_ref: str
    permissions: tuple[str, ...]
    failure_policy_ref: str
    empty_behavior: str
    scope: str
    applicability_ref: str = "core.applicability.always"

    def __post_init__(self):
        if not self.extension_id or not self.version or not self.lifecycle_event:
            raise LifecycleExtensionError("extension identity is incomplete")
        if not isinstance(self.order, int) or isinstance(self.order, bool):
            raise LifecycleExtensionError("extension order must be an integer")
        try:
            object.__setattr__(self, "execution_mode",
                               ExtensionExecutionMode(self.execution_mode))
        except ValueError as exc:
            raise LifecycleExtensionError("extension mode is invalid") from exc
        if not isinstance(self.loop_definition_ref, LoopDefinitionRef):
            raise LifecycleExtensionError("extension needs exact LoopDefinitionRef")
        if any(not value for value in (
                self.input_contract_ref, self.output_contract_ref,
                self.failure_policy_ref, self.empty_behavior, self.scope,
                self.applicability_ref)):
            raise LifecycleExtensionError("extension contract is incomplete")

    @property
    def content_digest(self):
        return _digest(asdict(self))


@dataclass(frozen=True)
class ResolvedExtensionSetSnapshot:
    procedure_id: str
    procedure_version: str
    lifecycle_event: str
    disposition: ResolutionDisposition | str
    extensions: tuple[LifecycleExtensionDefinition, ...]
    resolution_reasons: tuple[str, ...]

    def __post_init__(self):
        try:
            object.__setattr__(self, "disposition",
                               ResolutionDisposition(self.disposition))
        except ValueError as exc:
            raise LifecycleExtensionError("extension resolution state invalid") from exc
        if self.disposition is ResolutionDisposition.RESOLVED_EMPTY \
                and self.extensions:
            raise LifecycleExtensionError("empty resolution cannot contain extensions")
        if self.disposition is ResolutionDisposition.RESOLVED_NONEMPTY \
                and not self.extensions:
            raise LifecycleExtensionError("nonempty resolution needs extensions")

    @property
    def content_digest(self):
        return _digest({"procedure": [self.procedure_id, self.procedure_version],
                        "event": self.lifecycle_event,
                        "extensions": [item.content_digest
                                       for item in self.extensions]})

    def to_dict(self):
        return {"record_type": "resolved_extension_set/v1",
                "procedure_id": self.procedure_id,
                "procedure_version": self.procedure_version,
                "lifecycle_event": self.lifecycle_event,
                "disposition": self.disposition.value,
                "content_digest": self.content_digest,
                "extensions": [{**asdict(item),
                                "execution_mode": item.execution_mode.value,
                                "loop_definition_ref":
                                    item.loop_definition_ref.to_dict(),
                                "content_digest": item.content_digest}
                               for item in self.extensions],
                "resolution_reasons": list(self.resolution_reasons)}


@dataclass(frozen=True)
class ExtensionResolutionRequest:
    procedure: ProcedureLifecycleDefinition
    lifecycle_event: str
    candidates: tuple[LifecycleExtensionDefinition, ...]
    definition_registry: LoopDefinitionRegistry


def resolve_extensions(request: ExtensionResolutionRequest) \
        -> ResolvedExtensionSetSnapshot:
    if not isinstance(request, ExtensionResolutionRequest):
        raise LifecycleExtensionError("typed extension request required")
    if request.lifecycle_event not in request.procedure.supported_events:
        raise LifecycleExtensionError("procedure does not support lifecycle event")
    selected = []
    seen = set()
    for extension in request.candidates:
        if extension.lifecycle_event != request.lifecycle_event:
            continue
        key = (extension.extension_id, extension.version)
        if key in seen:
            raise LifecycleExtensionError("duplicate extension identity")
        seen.add(key)
        request.definition_registry.resolve(extension.loop_definition_ref)
        selected.append(extension)
    selected.sort(key=lambda item: (item.order, item.extension_id.casefold()))
    disposition = (ResolutionDisposition.RESOLVED_NONEMPTY if selected
                   else ResolutionDisposition.RESOLVED_EMPTY)
    reasons = ((f"resolved {len(selected)} extension(s)",) if selected
               else ("no applicable extension",))
    return ResolvedExtensionSetSnapshot(
        request.procedure.procedure_id, request.procedure.version,
        request.lifecycle_event, disposition, tuple(selected), reasons)


@dataclass(frozen=True)
class ExecutionContextFingerprint:
    plan_digest: str
    extension_digest: str
    capability_digest: str
    settings_digest: str
    context_digest: str
    intelligence_digest: str
    environment_digest: str
    verification_digest: str

    def __post_init__(self):
        for name, value in self.__dict__.items():
            if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise LifecycleExtensionError(f"{name} must be SHA-256")

    @property
    def content_digest(self):
        return _digest(asdict(self))


@dataclass(frozen=True)
class FingerprintComparison:
    disposition: DriftDisposition
    changed_dimensions: tuple[str, ...]
    reason: str


def compare_fingerprints(previous: ExecutionContextFingerprint,
                         current: ExecutionContextFingerprint) \
        -> FingerprintComparison:
    changed = tuple(name for name in previous.__dict__
                    if getattr(previous, name) != getattr(current, name))
    if not changed:
        return FingerprintComparison(DriftDisposition.UNCHANGED, (), "exact match")
    hard = {"extension_digest", "capability_digest", "settings_digest"}
    if hard & set(changed):
        return FingerprintComparison(
            DriftDisposition.REQUIRES_REPLAN, changed,
            "material execution authority changed")
    if "verification_digest" in changed:
        return FingerprintComparison(
            DriftDisposition.REQUIRES_REVALIDATION, changed,
            "verification requirements changed")
    return FingerprintComparison(
        DriftDisposition.COMPATIBLE_CHANGE, changed,
        "non-authority context changed under current policy")


__all__ = ("DriftDisposition", "ExecutionContextFingerprint",
           "ExtensionExecutionMode", "ExtensionResolutionRequest",
           "FingerprintComparison", "LifecycleExtensionDefinition",
           "LifecycleExtensionError", "ProcedureLifecycleDefinition",
           "ResolvedExtensionSetSnapshot", "compare_fingerprints",
           "resolve_extensions")
