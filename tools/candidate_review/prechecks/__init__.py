"""The pre-check edge: six deterministic kinds that can only refuse, run before any reviewer.

Every kind must be decided for every item: licence, format, safety, effects,
secrets and duplicates. A kind names one or more engines in the panel policy
and every available engine of it runs, so the record shows each engine's
result. A kind that no engine completed refuses the item, and an engine that
fails refuses the item: nothing is skipped silently.

A pre-check never approves anything. Passing every kind only means the item
may be put to the independent reviewers. A finding never repeats a secret or
the text that matched a secret pattern.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from ..configuration import PRECHECK_KINDS
from ..records import PRECHECK_RECORD, CandidateReviewError

PASSED, REFUSED, UNAVAILABLE = "passed", "refused", "unavailable"
COMPLETED_STATUSES = (PASSED, REFUSED)
#: A kind that no engine completed refuses the item. The mutant control in the checks turns
#: this off to prove that the refusal comes from this rule.
KIND_REQUIRES_A_COMPLETED_ENGINE = True
NO_ENGINE = "none"
DETAIL_LIMIT = 600


@dataclass(frozen=True)
class PrecheckFinding:
    code: str
    detail: str

    def to_dict(self) -> dict:
        return {"code": self.code, "detail": self.detail[:DETAIL_LIMIT]}


@dataclass(frozen=True)
class PrecheckResult:
    """One engine's answer for one kind: passed, refused with findings, or unavailable with its reason."""

    kind: str
    engine_id: str
    engine_version: str
    status: str
    findings: tuple = ()

    def to_dict(self) -> dict:
        return {"record_type": PRECHECK_RECORD, "kind": self.kind, "engine_id": self.engine_id,
                "engine_version": self.engine_version, "status": self.status,
                "findings": [finding.to_dict() for finding in self.findings]}


@dataclass(frozen=True)
class PrecheckContext:
    """What a pre-check may compare an item with: the policy and the bodies of the population."""

    policy: object
    population: Mapping


class PrecheckEngine(Protocol):
    """The small surface every pre-check engine implements."""

    kind: str
    engine_id: str

    def availability(self) -> tuple: ...

    def check(self, request, context: PrecheckContext) -> PrecheckResult: ...


@dataclass(frozen=True)
class PrecheckOutcome:
    results: tuple

    @property
    def refused(self) -> bool:
        return any(result.status == REFUSED for result in self.results)

    @property
    def reasons(self) -> tuple:
        return tuple(f"{result.kind}:{finding.code}" for result in self.results if result.status == REFUSED
                     for finding in result.findings)

    def to_dict(self) -> dict:
        return {"refused": self.refused, "reasons": list(self.reasons),
                "results": [result.to_dict() for result in self.results]}


def passed(kind: str, engine_id: str, version: str) -> PrecheckResult:
    return PrecheckResult(kind, engine_id, version, PASSED, ())


def refused(kind: str, engine_id: str, version: str, findings) -> PrecheckResult:
    """A refusal with at least one finding. ``findings`` is a sequence of (code, detail) pairs."""
    built = tuple(PrecheckFinding(code, detail) for code, detail in findings)
    if not built:
        raise ValueError("a refusal names at least one finding")
    return PrecheckResult(kind, engine_id, version, REFUSED, built)


def result_of(kind: str, engine_id: str, version: str, findings) -> PrecheckResult:
    findings = list(findings)
    return refused(kind, engine_id, version, findings) if findings else passed(kind, engine_id, version)


def run_prechecks(request, engines: Mapping, context: PrecheckContext) -> PrecheckOutcome:
    """Run every engine of every kind and fail closed when a kind was not decided."""
    results = []
    for kind in PRECHECK_KINDS:
        completed = False
        for engine in engines.get(kind, ()):
            engine_id = str(getattr(engine, "engine_id", "unknown"))
            try:
                available, reason, version = engine.availability()
            except Exception as error:  # noqa: BLE001 - a failing probe is recorded, never trusted
                available, reason, version = False, f"the availability probe failed: {type(error).__name__}", ""
            if not available:
                results.append(PrecheckResult(kind, engine_id, version, UNAVAILABLE,
                                              (PrecheckFinding("engine_unavailable", reason),)))
                continue
            try:
                result = engine.check(request, context)
            except CandidateReviewError as error:
                result = refused(kind, engine_id, version, [(error.code, str(error))])
            except Exception as error:  # noqa: BLE001 - an engine that fails refuses the item
                result = refused(kind, engine_id, version, [("engine_failed", type(error).__name__)])
            if not isinstance(result, PrecheckResult) or result.kind != kind or result.status not in COMPLETED_STATUSES:
                result = refused(kind, engine_id, version, [("engine_failed", "the engine answered outside the edge")])
            results.append(result)
            completed = True
        if not completed and KIND_REQUIRES_A_COMPLETED_ENGINE:
            results.append(PrecheckResult(kind, NO_ENGINE, "", REFUSED, (PrecheckFinding(
                "precheck_kind_unavailable", f"no {kind} engine completed, so the {kind} pre-check was not decided"),)))
    return PrecheckOutcome(tuple(results))
