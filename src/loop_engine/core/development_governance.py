"""Resume, publication, contribution isolation, and self-hosting contracts.

These passive records and deterministic checks reuse Run History, workspace,
verification, and effect-approval authority. They do not commit, push, publish,
migrate, or execute product work themselves.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from .development_planning import TerminalPlanCode


class DevelopmentGovernanceError(ValueError):
    """Governed development state or authority is invalid."""


class PublicationEffect(str, Enum):
    COMMIT = "commit"
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    PACKAGE_PUBLISH = "package_publish"
    DEPLOY = "deploy"


class LegacyAuthorityDisposition(str, Enum):
    ABSENT = "absent"
    DETECTED_BLOCKING = "detected_blocking"
    MIGRATION_AVAILABLE = "migration_available"
    MIGRATED = "migrated"
    REMOVAL_VERIFIED = "removal_verified"


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class TaskReality:
    task_id: str
    projected_status: str
    artifact_exists: bool
    verification_passed: bool
    blocked_reason: str = ""


@dataclass(frozen=True)
class ResumeReconciliationRequest:
    plan_id: str
    checkpoint_digest: str
    observed_state_digest: str
    tasks: tuple[TaskReality, ...]


@dataclass(frozen=True)
class ResumeReconciliationResult:
    plan_id: str
    checkpoint_digest: str
    observed_state_digest: str
    verified_completed: tuple[str, ...]
    reopened_tasks: tuple[str, ...]
    blocked_tasks: tuple[str, ...]
    terminal_code: TerminalPlanCode | str


def reconcile_resume(request: ResumeReconciliationRequest) \
        -> ResumeReconciliationResult:
    if not isinstance(request, ResumeReconciliationRequest):
        raise DevelopmentGovernanceError("typed resume request required")
    completed=[]; reopened=[]; blocked=[]
    for task in request.tasks:
        if task.blocked_reason:
            blocked.append(task.task_id)
        elif task.projected_status == "completed" \
                and task.artifact_exists and task.verification_passed:
            completed.append(task.task_id)
        else:
            reopened.append(task.task_id)
    terminal=(TerminalPlanCode.TASKS_BLOCKED if blocked and not reopened
              else TerminalPlanCode.COMPLETED_VERIFIED
              if len(completed)==len(request.tasks)
              else TerminalPlanCode.COMPLETED_PARTIAL)
    return ResumeReconciliationResult(
        request.plan_id,request.checkpoint_digest,request.observed_state_digest,
        tuple(completed),tuple(reopened),tuple(blocked),terminal)


@dataclass(frozen=True)
class PublicationAuthorization:
    authorization_id: str
    effect: PublicationEffect | str
    exact_target_digest: str
    verification_digest: str
    requested_by_loop_id: str
    approved_by: str
    approved: bool

    def __post_init__(self):
        try: object.__setattr__(self,"effect",PublicationEffect(self.effect))
        except ValueError as exc: raise DevelopmentGovernanceError("effect invalid") from exc
        for value in (self.exact_target_digest,self.verification_digest):
            if len(value)!=64: raise DevelopmentGovernanceError("digest invalid")
        if self.approved and (not self.approved_by
                              or self.approved_by==self.requested_by_loop_id):
            raise DevelopmentGovernanceError("publication needs independent authority")

    @property
    def content_digest(self):
        return _digest(self.__dict__)


@dataclass(frozen=True)
class ContributionIsolationResult:
    baseline_passed: bool
    implementation_passed: bool
    extension_passed: bool
    combined_passed: bool
    responsible_contributions: tuple[str, ...]
    conclusion: str


@dataclass(frozen=True)
class ContributionIsolationRequest:
    baseline_passed: bool
    implementation_passed: bool
    extension_passed: bool
    combined_passed: bool


def isolate_contribution(request: ContributionIsolationRequest) \
        -> ContributionIsolationResult:
    if not isinstance(request, ContributionIsolationRequest):
        raise DevelopmentGovernanceError(
            "typed contribution isolation request required")
    baseline = request.baseline_passed
    implementation = request.implementation_passed
    extension = request.extension_passed
    combined = request.combined_passed
    responsible=[]
    if baseline and not implementation: responsible.append("implementation")
    if baseline and not extension: responsible.append("extension")
    if implementation and extension and not combined:
        responsible.append("interaction")
    conclusion=("no isolated regression" if not responsible
                else "regression localized by replay matrix")
    return ContributionIsolationResult(
        baseline,implementation,extension,combined,tuple(responsible),conclusion)


@dataclass(frozen=True)
class SelfHostingProfile:
    profile_id: str
    repository_specific: bool
    generated_template: bool
    production_workflow_allowed: bool
    maximum_recursion_depth: int

    def __post_init__(self):
        if self.repository_specific and self.generated_template:
            raise DevelopmentGovernanceError(
                "repository config cannot masquerade as generated template")
        if self.maximum_recursion_depth < 0:
            raise DevelopmentGovernanceError("recursion depth invalid")
        if self.repository_specific and self.production_workflow_allowed \
                and self.maximum_recursion_depth != 1:
            raise DevelopmentGovernanceError(
                "self-hosted production workflow must be explicitly depth one")


@dataclass(frozen=True)
class LegacyAuthorityState:
    legacy_ref: str
    current_ref: str
    disposition: LegacyAuthorityDisposition | str
    migration_ref: str

    def __post_init__(self):
        try: object.__setattr__(self,"disposition",
                               LegacyAuthorityDisposition(self.disposition))
        except ValueError as exc: raise DevelopmentGovernanceError("legacy state invalid") from exc
        if self.disposition is LegacyAuthorityDisposition.DETECTED_BLOCKING \
                and not self.migration_ref:
            raise DevelopmentGovernanceError("blocking legacy authority needs migration path")


__all__=("ContributionIsolationRequest","ContributionIsolationResult",
         "DevelopmentGovernanceError",
         "LegacyAuthorityDisposition","LegacyAuthorityState",
         "PublicationAuthorization","PublicationEffect",
         "ResumeReconciliationRequest","ResumeReconciliationResult",
         "SelfHostingProfile","TaskReality","isolate_contribution",
         "reconcile_resume")
