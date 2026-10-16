"""The preflight layer of an envelope Loop: self-check and self-repair before the engine, within declared bounds.

```text
run_preflight(component, checks, repairs, context, grant)
├── each declared check, in order, reads only the immutable preflight context
│   ├── passes                  -> the next check
│   └── answers a refusal       -> its code must be one of the check's declared diagnoses
│       ├── no declared repair  -> refused with the check's own refusal
│       ├── a repair whose declared effects the grant does not hold
│       │                       -> repair_refused, never run; refused with the check's refusal
│       ├── a repair past its declared number of applications -> refused
│       └── the repair returns a new context, the same check runs once more
│           ├── passes          -> repaired
│           └── still refused   -> refused with the refusal it gives now
└── envelope_preflight_report/v1: every step, the verdict (ready, repaired or refused) and the refusal
```

A check diagnoses and changes nothing: it reads the context it is given and answers None or an
envelope refusal, so every diagnosis carries its code, what happened, the next action and the retry
rule. A self-repair is declared with the diagnoses it fixes, its effects and how often it may run in
one attempt. A repair that declares only the pure effect changes nothing outside the attempt's own
memory; any other effect needs the attempt's own grant (``EnvelopePreflightGrant``, from the owning
Loop's authority), and without it the repair is refused before it runs. A repair never produces its own
evidence, changes a policy or a grant, or repeats an effect. The runner is pure: it holds no state
between calls, imports no engine and opens nothing.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable

from .envelope import (
    PURE_EFFECT, EnvelopeError, EnvelopeRefusal, _CODE, _count, _effects, _identifier, _names)

PREFLIGHT_REPORT_RECORD_TYPE = "envelope_preflight_report/v1"
STEP_PASSED, STEP_REPAIRED, STEP_FAILED, STEP_REPAIR_REFUSED = "passed", "repaired", "failed", "repair_refused"
PREFLIGHT_STEP_OUTCOMES = (STEP_PASSED, STEP_REPAIRED, STEP_FAILED, STEP_REPAIR_REFUSED)
VERDICT_READY, VERDICT_REPAIRED, VERDICT_REFUSED = "ready", "repaired", "refused"
PREFLIGHT_VERDICTS = (VERDICT_READY, VERDICT_REPAIRED, VERDICT_REFUSED)
#: How often one self-repair may run in one attempt. A repair that has not fixed its check after two
#: tries will not fix it on a third, and the bound keeps preflight from becoming a loop of its own.
MAXIMUM_REPAIR_APPLICATIONS = 2
REPAIR_EFFECT_NOT_GRANTED, REPAIR_BOUND_REACHED, NO_DECLARED_REPAIR, STILL_FAILING = (
    "repair_effect_not_granted", "repair_bound_reached", "no_declared_repair", "still_failing_after_repair")


@dataclass(frozen=True)
class EnvelopePreflightCheck:
    """One declared self-check: an identity, the diagnosis codes it may answer and the function that reads."""

    check_id: str
    diagnoses: tuple
    run: Callable = field(compare=False)

    def __post_init__(self):
        _identifier(self.check_id, "check_id")
        object.__setattr__(self, "diagnoses", _names(self.diagnoses, "diagnoses", _CODE))
        if not self.diagnoses:
            raise EnvelopeError("check_without_diagnoses", f"{self.check_id} declares the codes it may answer")
        if not callable(self.run):
            raise EnvelopeError("check_without_a_function", f"{self.check_id} declares the function it runs")


@dataclass(frozen=True)
class EnvelopeSelfRepair:
    """One declared self-repair: the diagnoses it fixes, its effects and its bound for one attempt."""

    repair_id: str
    fixes: tuple
    effects: tuple
    maximum_applications: int
    apply: Callable = field(compare=False)

    def __post_init__(self):
        _identifier(self.repair_id, "repair_id")
        object.__setattr__(self, "fixes", _names(self.fixes, "fixes", _CODE))
        object.__setattr__(self, "effects", _effects(self.effects, "effects"))
        if not self.fixes or not self.effects:
            raise EnvelopeError("repair_declaration_incomplete",
                                f"{self.repair_id} names what it fixes and its effects, pure when it has none")
        if PURE_EFFECT in self.effects and len(self.effects) > 1:
            raise EnvelopeError("repair_declaration_incomplete", "a pure repair declares no other effect")
        _count(self.maximum_applications, "maximum_applications", 1, MAXIMUM_REPAIR_APPLICATIONS)
        if not callable(self.apply):
            raise EnvelopeError("repair_without_a_function", f"{self.repair_id} declares the function it runs")

    @property
    def needed_effects(self) -> frozenset:
        return frozenset(self.effects) - {PURE_EFFECT}


@dataclass(frozen=True)
class EnvelopePreflightGrant:
    """The effects this attempt's self-repairs may use, taken from the owning Loop's grants and nothing else."""

    effects: tuple = ()

    def __post_init__(self):
        object.__setattr__(self, "effects", _effects(self.effects, "grant effects"))


@dataclass(frozen=True)
class EnvelopePreflightStep:
    """What happened to one check: its outcome, its diagnosis and the repair applied or refused."""

    check_id: str
    outcome: str
    diagnosis: str = ""
    repair_id: str = ""
    detail: str = ""

    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "outcome": self.outcome, "diagnosis": self.diagnosis,
                "repair_id": self.repair_id, "detail": self.detail}


@dataclass(frozen=True)
class EnvelopePreflightReport:
    """One ``envelope_preflight_report/v1``; the repaired context travels beside it and is never recorded."""

    component: str
    steps: tuple
    verdict: str
    refusal: "EnvelopeRefusal | None"
    context: Mapping = field(compare=False, default_factory=lambda: MappingProxyType({}))
    record_type: str = PREFLIGHT_REPORT_RECORD_TYPE

    def __post_init__(self):
        if self.verdict not in PREFLIGHT_VERDICTS or (self.verdict == VERDICT_REFUSED) != (self.refusal is not None):
            raise EnvelopeError("invalid_preflight_report", "a refused preflight, and only one, names its refusal")

    @property
    def ready(self) -> bool:
        return self.verdict != VERDICT_REFUSED

    def to_dict(self) -> dict:
        return {"record_type": self.record_type, "component": self.component,
                "steps": [step.to_dict() for step in self.steps], "verdict": self.verdict,
                "refusal": None if self.refusal is None else self.refusal.to_dict()}


def _diagnose(check: EnvelopePreflightCheck, context: Mapping) -> "EnvelopeRefusal | None":
    answer = check.run(MappingProxyType(dict(context)))
    if answer is None:
        return None
    if not isinstance(answer, EnvelopeRefusal):
        raise EnvelopeError("untyped_diagnosis", f"{check.check_id} answers None or an envelope refusal")
    if answer.code not in check.diagnoses:
        raise EnvelopeError("undeclared_diagnosis", f"{check.check_id} answered {answer.code}, which it does "
                                                    "not declare")
    return answer


def _repairs_by_diagnosis(repairs) -> dict:
    found: dict = {}
    for repair in repairs:
        if not isinstance(repair, EnvelopeSelfRepair):
            raise EnvelopeError("invalid_repair", "a self-repair is an EnvelopeSelfRepair")
        for code in repair.fixes:
            if code in found:
                raise EnvelopeError("two_repairs_for_one_diagnosis", f"{code} has one declared repair")
            found[code] = repair
    return found


def run_preflight(component: str, checks, repairs=(), context: "Mapping | None" = None,
                  grant: "EnvelopePreflightGrant | None" = None) -> EnvelopePreflightReport:
    """Run every declared check in order, repairing only what a declared, granted repair may fix."""
    _identifier(component, "component")
    checks, grant = tuple(checks), grant or EnvelopePreflightGrant()
    if not checks or any(not isinstance(check, EnvelopePreflightCheck) for check in checks):
        raise EnvelopeError("invalid_preflight", "preflight runs at least one declared check")
    if len({check.check_id for check in checks}) != len(checks):
        raise EnvelopeError("repeated_value", "each check is declared once")
    if not isinstance(grant, EnvelopePreflightGrant):
        raise EnvelopeError("invalid_preflight", "a grant is an EnvelopePreflightGrant")
    by_diagnosis, applications = _repairs_by_diagnosis(repairs), {}
    current = dict(context or {})
    steps, repaired = [], False

    def refused(step, refusal):
        steps.append(step)
        return EnvelopePreflightReport(component, tuple(steps), VERDICT_REFUSED, refusal,
                                       MappingProxyType(dict(current)))
    for check in checks:
        refusal = _diagnose(check, current)
        if refusal is None:
            steps.append(EnvelopePreflightStep(check.check_id, STEP_PASSED))
            continue
        repair = by_diagnosis.get(refusal.code)
        if repair is None:
            return refused(EnvelopePreflightStep(check.check_id, STEP_FAILED, refusal.code, "",
                                                 NO_DECLARED_REPAIR), refusal)
        missing = sorted(repair.needed_effects - set(grant.effects))
        if missing:
            return refused(EnvelopePreflightStep(check.check_id, STEP_REPAIR_REFUSED, refusal.code, repair.repair_id,
                                                 f"{REPAIR_EFFECT_NOT_GRANTED}:{','.join(missing)}"), refusal)
        if applications.get(repair.repair_id, 0) >= repair.maximum_applications:
            return refused(EnvelopePreflightStep(check.check_id, STEP_FAILED, refusal.code, repair.repair_id,
                                                 REPAIR_BOUND_REACHED), refusal)
        repaired_context = repair.apply(MappingProxyType(dict(current)))
        if not isinstance(repaired_context, Mapping):
            raise EnvelopeError("untyped_repair", f"{repair.repair_id} returns the repaired context")
        applications[repair.repair_id] = applications.get(repair.repair_id, 0) + 1
        current = dict(repaired_context)
        again = _diagnose(check, current)
        if again is not None:
            return refused(EnvelopePreflightStep(check.check_id, STEP_FAILED, again.code, repair.repair_id,
                                                 STILL_FAILING), again)
        repaired = True
        steps.append(EnvelopePreflightStep(check.check_id, STEP_REPAIRED, refusal.code, repair.repair_id))
    return EnvelopePreflightReport(component, tuple(steps), VERDICT_REPAIRED if repaired else VERDICT_READY, None,
                                   MappingProxyType(dict(current)))
