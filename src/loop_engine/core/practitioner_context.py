"""Versioned question and persona context for the universal Practitioner.

This module loads passive Context Intelligence. It contains no task classifier,
domain workflow, tool choice, dataset choice, or executable solution. The same
portfolio is supplied to every task; a Practitioner and its model executor use
the questions to interpret the current task and state.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from importlib.resources import files

import yaml

from .reasoning_call import PROMPT_LAYOUT_POLICIES
from .component_contracts import (
    LoopComponentDraft, component_payload_digest, define_loop_component)


_CORE_STEP_IDS = (
    "orient", "standardize_task", "reconcile_horizon", "assess_prepare",
    "decide_next", "how", "act", "verify", "integrate_commit", "route")
_RECOVERY_STEP_IDS = (
    "diagnose_stall", "propose_recovery", "adjudicate_recovery")
_STEP_IDS = _CORE_STEP_IDS + _RECOVERY_STEP_IDS
_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class PractitionerContextError(ValueError):
    """Question or persona Context Intelligence has an invalid contract."""


class ContextIntelligenceAvailability(str, Enum):
    """Observed availability of the primary Context Intelligence source."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class ContextFallbackPolicy(str, Enum):
    """Whether a declared outage may use the packaged minimum portfolio."""

    REFUSE = "refuse"
    USE_PACKAGED_MINIMUM = "use_packaged_minimum"


@dataclass(frozen=True)
class PractitionerContextLoadRequest:
    """Typed request for primary or explicitly degraded context loading."""

    availability: ContextIntelligenceAvailability = (
        ContextIntelligenceAvailability.AVAILABLE)
    fallback_policy: ContextFallbackPolicy = (
        ContextFallbackPolicy.USE_PACKAGED_MINIMUM)

    def __post_init__(self) -> None:
        if not isinstance(self.availability, ContextIntelligenceAvailability):
            raise PractitionerContextError(
                "context availability must use its typed enum")
        if not isinstance(self.fallback_policy, ContextFallbackPolicy):
            raise PractitionerContextError(
                "context fallback policy must use its typed enum")


@dataclass(frozen=True)
class PractitionerContextLoadRecord:
    """Evidence of which immutable question portfolio entered the run."""

    portfolio: "PractitionerContextPortfolio"
    source_ref: str
    availability: ContextIntelligenceAvailability
    fallback_used: bool
    degradation_reason: str = ""
    record_type: str = "practitioner_context_load/v1"

    def __post_init__(self) -> None:
        if self.record_type != "practitioner_context_load/v1":
            raise PractitionerContextError(
                "unsupported practitioner context load record")
        if not isinstance(self.portfolio, PractitionerContextPortfolio):
            raise PractitionerContextError(
                "context load record requires a validated portfolio")
        if not self.source_ref.strip():
            raise PractitionerContextError(
                "context load record requires a source reference")
        if not isinstance(self.availability, ContextIntelligenceAvailability):
            raise PractitionerContextError(
                "context load record availability is invalid")
        if self.fallback_used and not self.degradation_reason.strip():
            raise PractitionerContextError(
                "fallback context requires a degradation reason")
        if not self.fallback_used and self.degradation_reason:
            raise PractitionerContextError(
                "primary context cannot carry a degradation reason")

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "portfolio_id": self.portfolio.portfolio_id,
            "portfolio_version": self.portfolio.version,
            "portfolio_digest": component_payload_digest(
                self.portfolio.to_dict()),
            "source_ref": self.source_ref,
            "availability": self.availability.value,
            "fallback_used": self.fallback_used,
            "degradation_reason": self.degradation_reason,
        }


@dataclass(frozen=True)
class PractitionerPersona:
    """One model-facing viewpoint with no execution authority."""

    persona_id: str
    version: str
    instruction: str

    def __post_init__(self) -> None:
        if not self.persona_id.strip() or not _SEMVER.fullmatch(self.version):
            raise PractitionerContextError("persona identity is invalid")
        if not self.instruction.strip():
            raise PractitionerContextError("persona instruction is empty")

    def to_dict(self) -> dict:
        return {
            "persona_id": self.persona_id,
            "version": self.version,
            "instruction": self.instruction,
        }

    def component_definition(self):
        """Represent this passive persona through the universal component."""
        payload = self.to_dict()
        return define_loop_component(LoopComponentDraft(
            self.persona_id, self.version, "persona", "static",
            "practitioner_persona/v1", component_payload_digest(payload),
            "core Context Intelligence",
            role_affinities=("practitioner",)))


@dataclass(frozen=True)
class PractitionerGuidance:
    """One small static Context Intelligence guidance component."""

    record_id: str
    version: str
    intelligence_functions: tuple[str, ...]
    step_affinities: tuple[str, ...]
    content: str

    def __post_init__(self) -> None:
        if (not self.record_id.strip() or not _SEMVER.fullmatch(self.version)
                or not self.content.strip()):
            raise PractitionerContextError("guidance identity is invalid")
        if (not self.intelligence_functions
                or any(not item.strip() for item in self.intelligence_functions)
                or any(item not in _STEP_IDS for item in self.step_affinities)):
            raise PractitionerContextError("guidance affinities are invalid")

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id, "version": self.version,
            "intelligence_functions": list(self.intelligence_functions),
            "step_affinities": list(self.step_affinities),
            "content": self.content,
        }

    def component_definition(self):
        """Represent this passive guidance through the universal component."""
        payload = self.to_dict()
        return define_loop_component(LoopComponentDraft(
            self.record_id, self.version, "guidance", "static",
            "practitioner_guidance/v1", component_payload_digest(payload),
            "core Context Intelligence",
            role_affinities=("practitioner", "intelligence")))


@dataclass(frozen=True)
class PromptAssemblyProfile:
    """One static selection of the existing provider-neutral layout policy."""

    profile_id: str
    version: str
    layout_policy: str
    activation: str

    def __post_init__(self) -> None:
        if (not self.profile_id.strip() or not _SEMVER.fullmatch(self.version)
                or self.layout_policy not in PROMPT_LAYOUT_POLICIES
                or not self.activation.strip()):
            raise PractitionerContextError(
                "prompt assembly profile is invalid")

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id, "version": self.version,
            "layout_policy": self.layout_policy,
            "activation": self.activation,
        }

    def component_definition(self):
        """Represent this passive prompt profile through one component."""
        payload = self.to_dict()
        return define_loop_component(LoopComponentDraft(
            self.profile_id, self.version, "prompt_assembly", "static",
            "prompt_assembly_profile/v1", component_payload_digest(payload),
            "core Context Intelligence",
            role_affinities=("practitioner", "intelligence"),
            mode_support=("deterministic",)))


@dataclass(frozen=True)
class PractitionerStepQuestions:
    """Questions and expected answer contract for one universal step."""

    step_id: str
    output_contract: str
    questions: tuple[str, ...]
    persona_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.step_id not in _STEP_IDS:
            raise PractitionerContextError(
                f"unknown Practitioner step {self.step_id!r}")
        if not self.output_contract.strip():
            raise PractitionerContextError("step output contract is empty")
        questions = tuple(self.questions)
        if (not questions or any(not item.strip() for item in questions)
                or len(questions) != len(set(questions))):
            raise PractitionerContextError(
                "step questions must be unique non-empty text")
        object.__setattr__(self, "questions", questions)
        refs = tuple(self.persona_refs)
        if len(refs) != len(set(refs)) or any(not item.strip() for item in refs):
            raise PractitionerContextError("step persona refs must be unique")
        object.__setattr__(self, "persona_refs", refs)

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "output_contract": self.output_contract,
            "questions": list(self.questions),
            "persona_refs": list(self.persona_refs),
        }

    def component_definition(self):
        """Represent this passive question portfolio as one component."""
        payload = self.to_dict()
        return define_loop_component(LoopComponentDraft(
            f"core.questions.default.{self.step_id}", "1.0.0",
            "question_portfolio", "static", "step_question_portfolio/v1",
            component_payload_digest(payload), "core Context Intelligence",
            role_affinities=("practitioner", "intelligence")))


@dataclass(frozen=True)
class PractitionerContextPortfolio:
    """Exact passive context supplied to every adaptive Practitioner run."""

    portfolio_id: str
    version: str
    persona: PractitionerPersona
    steps: tuple[PractitionerStepQuestions, ...]
    guidance: tuple[PractitionerGuidance, ...]
    assembly_profiles: tuple[PromptAssemblyProfile, ...]
    perspectives: tuple[PractitionerPersona, ...] = ()
    record_type: str = "practitioner_context_intelligence/v1"

    def __post_init__(self) -> None:
        if self.record_type != "practitioner_context_intelligence/v1":
            raise PractitionerContextError("context record type is unsupported")
        if not self.portfolio_id.strip() or not _SEMVER.fullmatch(self.version):
            raise PractitionerContextError("context portfolio identity is invalid")
        if not isinstance(self.persona, PractitionerPersona):
            raise PractitionerContextError("context portfolio needs a persona")
        guidance = tuple(self.guidance)
        profiles = tuple(self.assembly_profiles)
        if (not guidance or len({item.record_id for item in guidance})
                != len(guidance)
                or len(profiles) < 2
                or len({item.profile_id for item in profiles}) != len(profiles)):
            raise PractitionerContextError(
                "context guidance and assembly profiles must be unique")
        perspectives = tuple(self.perspectives)
        if (any(not isinstance(item, PractitionerPersona)
                for item in perspectives)
                or len({item.persona_id for item in perspectives})
                != len(perspectives)):
            raise PractitionerContextError(
                "context perspectives must be unique personas")
        steps = tuple(self.steps)
        if tuple(item.step_id for item in steps) != _STEP_IDS:
            raise PractitionerContextError(
                "context portfolio must define every semantic step in order")
        object.__setattr__(self, "steps", steps)
        object.__setattr__(self, "guidance", guidance)
        object.__setattr__(self, "assembly_profiles", profiles)
        object.__setattr__(self, "perspectives", perspectives)

    def for_step(self, step_id: str) -> PractitionerStepQuestions:
        try:
            return next(item for item in self.steps if item.step_id == step_id)
        except StopIteration as exc:
            raise PractitionerContextError(
                f"question portfolio has no step {step_id!r}") from exc

    def persona_candidates(self, step_id: str) -> tuple[dict, ...]:
        """Return every perspective with affinity metadata and no selection."""
        affinities = set(self.for_step(step_id).persona_refs)
        return tuple({
            **item.to_dict(),
            "step_affinity_match": item.persona_id in affinities,
            "selection_authority": "model",
        } for item in (self.persona, *self.perspectives))

    def guidance_candidates(self, step_id: str) -> tuple[dict, ...]:
        """Return all guidance with step affinity as advisory metadata."""
        self.for_step(step_id)
        return tuple({
            **item.to_dict(),
            "step_affinity_match": step_id in item.step_affinities,
            "selection_authority": "model",
        } for item in self.guidance)

    def question_candidates(self, step_id: str) -> tuple[dict, ...]:
        """Return every question set; the current step is a hint, not a gate."""
        self.for_step(step_id)
        return tuple({
            **item.to_dict(),
            "active_step_match": item.step_id == step_id,
            "selection_authority": "model",
        } for item in self.steps)

    def assembly_profile(self, has_failures: bool) -> PromptAssemblyProfile:
        activation = "active_failures" if has_failures else "default"
        try:
            return next(item for item in self.assembly_profiles
                        if item.activation == activation)
        except StopIteration as exc:
            raise PractitionerContextError(
                f"no prompt assembly profile for {activation}") from exc

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "portfolio_id": self.portfolio_id,
            "version": self.version,
            "persona": self.persona.to_dict(),
            "perspectives": [item.to_dict() for item in self.perspectives],
            "guidance": [item.to_dict() for item in self.guidance],
            "prompt_assembly_profiles": [
                item.to_dict() for item in self.assembly_profiles],
            "steps": [item.to_dict() for item in self.steps],
        }

    def component_definition(self):
        """Represent this passive Context Intelligence portfolio uniformly."""
        payload = self.to_dict()
        return define_loop_component(LoopComponentDraft(
            self.portfolio_id, self.version, "intelligence_portfolio",
            "static", "practitioner_context_intelligence/v1",
            component_payload_digest(payload), "package Core catalog",
            role_affinities=("practitioner", "intelligence"),
            intelligence_refs=tuple(
                item.record_id for item in self.guidance)))


def _load_practitioner_context_resource(
        relative_path: str) -> PractitionerContextPortfolio:
    path = files("loop_engine").joinpath(relative_path)
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PractitionerContextError("context portfolio root must be an object")
    persona_value = value.get("persona")
    perspectives_value = value.get("perspectives") or []
    guidance_value = value.get("guidance") or []
    profiles_value = value.get("prompt_assembly_profiles") or []
    steps_value = value.get("steps")
    if (not isinstance(persona_value, dict)
            or not isinstance(perspectives_value, list)
            or not isinstance(guidance_value, list)
            or not isinstance(profiles_value, list)
            or not isinstance(steps_value, dict)):
        raise PractitionerContextError(
            "context portfolio needs persona and steps objects")
    persona = PractitionerPersona(
        str(persona_value.get("persona_id", "")),
        str(persona_value.get("version", "")),
        str(persona_value.get("instruction", "")),
    )
    perspectives = tuple(PractitionerPersona(
        str(item.get("persona_id", "")), str(item.get("version", "")),
        str(item.get("instruction", "")))
        for item in perspectives_value if isinstance(item, dict))
    guidance = tuple(PractitionerGuidance(
        str(item.get("record_id", "")), str(item.get("version", "")),
        tuple(str(value) for value in item.get("intelligence_functions", ())),
        tuple(str(value) for value in item.get("step_affinities", ())),
        str(item.get("content", "")))
        for item in guidance_value if isinstance(item, dict))
    profiles = tuple(PromptAssemblyProfile(
        str(item.get("profile_id", "")), str(item.get("version", "")),
        str(item.get("layout_policy", "")), str(item.get("activation", "")))
        for item in profiles_value if isinstance(item, dict))
    steps = tuple(PractitionerStepQuestions(
        step_id,
        str((steps_value.get(step_id) or {}).get("output_contract", "")),
        tuple(str(item) for item in (
            (steps_value.get(step_id) or {}).get("questions") or ())),
        tuple(str(item) for item in (
            (steps_value.get(step_id) or {}).get("persona_refs") or ())),
    ) for step_id in _STEP_IDS)
    return PractitionerContextPortfolio(
        str(value.get("portfolio_id", "")),
        str(value.get("version", "")), persona, steps, guidance, profiles,
        perspectives,
        str(value.get("record_type", "")),
    )


def load_practitioner_context_with_record(
        request: "PractitionerContextLoadRequest | None" = None
        ) -> PractitionerContextLoadRecord:
    """Load primary Context Intelligence or an explicitly allowed minimum.

    The fallback is a separate immutable package resource. It is used only
    when the caller declares the Context Intelligence source unavailable. A
    malformed primary portfolio still fails closed because corruption is not
    equivalent to an operational outage.
    """
    selected = request or PractitionerContextLoadRequest()
    if not isinstance(selected, PractitionerContextLoadRequest):
        raise PractitionerContextError(
            "context load request has the wrong contract")
    primary_ref = (
        "intelligence/context/core/practitioner_context_intelligence.yaml")
    if selected.availability is ContextIntelligenceAvailability.AVAILABLE:
        return PractitionerContextLoadRecord(
            _load_practitioner_context_resource(primary_ref),
            primary_ref, selected.availability, False)
    if selected.fallback_policy is ContextFallbackPolicy.REFUSE:
        raise PractitionerContextError(
            "Context Intelligence is unavailable and fallback is refused")
    fallback_ref = "data/practitioner_context_fallback.yaml"
    return PractitionerContextLoadRecord(
        _load_practitioner_context_resource(fallback_ref),
        fallback_ref, selected.availability, True,
        "primary Context Intelligence was declared unavailable")


def load_practitioner_context(
        request: "PractitionerContextLoadRequest | None" = None
        ) -> PractitionerContextPortfolio:
    """Load the validated portfolio while retaining a detailed record API."""
    return load_practitioner_context_with_record(request).portfolio


def self_test() -> dict:
    portfolio = load_practitioner_context()
    degraded = load_practitioner_context_with_record(
        PractitionerContextLoadRequest(
            ContextIntelligenceAvailability.UNAVAILABLE,
            ContextFallbackPolicy.USE_PACKAGED_MINIMUM))
    refused = False
    try:
        load_practitioner_context_with_record(PractitionerContextLoadRequest(
            ContextIntelligenceAvailability.UNAVAILABLE,
            ContextFallbackPolicy.REFUSE))
    except PractitionerContextError:
        refused = True
    tests = [
        {
            "test": "one_general_portfolio_covers_every_practitioner_step",
            "passed": tuple(item.step_id for item in portfolio.steps) == _STEP_IDS,
            "detail": f"{len(portfolio.steps)} universal step question sets",
        },
        {
            "test": "persona_has_no_task_specific_dataset_or_solution",
            "passed": not any(word in portfolio.persona.instruction.lower()
                              for word in ("iris", "openml", "kaggle",
                                           "linear model", "pdf report")),
            "detail": portfolio.persona.persona_id,
        },
        {
            "test": "general_portfolio_exposes_review_perspectives",
            "passed": len(portfolio.perspectives) >= 8,
            "detail": f"{len(portfolio.perspectives)} optional perspectives",
        },
        {
            "test": "perspectives_guidance_and_questions_are_model_candidates",
            "passed": (
                len(portfolio.persona_candidates("decide_next"))
                == 1 + len(portfolio.perspectives)
                and len(portfolio.guidance_candidates("decide_next"))
                == len(portfolio.guidance)
                and len(portfolio.question_candidates("decide_next"))
                == len(portfolio.steps)
                and all(item["selection_authority"] == "model"
                        for item in portfolio.persona_candidates(
                            "decide_next")
                        + portfolio.guidance_candidates("decide_next")
                        + portfolio.question_candidates("decide_next"))),
            "detail": "step affinity is metadata and selects nothing",
        },
        {
            "test": "orientation_asks_for_inputs_outputs_and_subcomponents",
            "passed": all(term in " ".join(
                portfolio.for_step("orient").questions).lower()
                for term in ("inputs", "outputs", "subcomponents")),
            "detail": portfolio.for_step("orient").output_contract,
        },
        {
            "test": "guidance_is_small_versioned_context_intelligence",
            "passed": len(portfolio.guidance) >= 10
            and all(item.version == "1.0.0" for item in portfolio.guidance),
            "detail": f"{len(portfolio.guidance)} guidance components",
        },
        {
            "test": "prompt_assembly_profiles_select_default_and_repair",
            "passed": (
                portfolio.assembly_profile(False).layout_policy == "canonical"
                and portfolio.assembly_profile(True).layout_policy
                == "failure_focused"),
            "detail": "selection is data driven",
        },
        {
            "test": "personas_guidance_and_prompt_profiles_are_components",
            "passed": (
                portfolio.persona.component_definition().operationality
                == "static"
                and portfolio.guidance[0].component_definition().component_kind
                == "guidance"
                and portfolio.assembly_profiles[0].component_definition()
                .component_kind == "prompt_assembly"
                and portfolio.steps[0].component_definition().component_kind
                == "question_portfolio"
                and portfolio.component_definition().component_kind
                == "intelligence_portfolio"),
            "detail": "all remain passive and content addressed",
        },
        {
            "test": "declared_intelligence_outage_uses_separate_minimum_file",
            "passed": (
                degraded.fallback_used
                and degraded.source_ref
                == "data/practitioner_context_fallback.yaml"
                and degraded.portfolio.portfolio_id
                == "fallback.context.practitioner.minimum"
                and len(degraded.portfolio.steps) == len(_STEP_IDS)),
            "detail": degraded.to_dict(),
        },
        {
            "test": "fallback_policy_can_fail_closed",
            "passed": refused,
            "detail": "declared outage plus refuse policy raises",
        },
    ]
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "practitioner_context_test/v1",
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }
