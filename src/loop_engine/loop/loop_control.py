"""Closed Loop conditions and passive mode-policy inspection.

The canonical execution behavior stays
in ``recursive_loop.Loop``. A budget or deadline is a safety limit and never a
successful exit condition.
"""
from __future__ import annotations

from dataclasses import dataclass

FRAMEWORKS = ("nine_step", "five_step", "custom", "open")
LOOP_CONDITIONS = ("steps_remain", "chooser_selects_work")
EXIT_CONDITIONS = ("steps_complete", "accepted_success")
MODES = ("deterministic", "hybrid", "non_deterministic")


class LoopModeUnavailableError(ValueError):
    """A preferred alternative is infeasible or has no declared executor."""


def _mode_sequence(name: str, values, *, allow_empty: bool = False) -> tuple:
    if (type(values) not in (tuple, list)
            or any(type(value) is not str or value not in MODES for value in values)
            or len(values) != len(set(values))
            or (not values and not allow_empty)):
        raise ValueError(f"{name} requires unique known Loop modes")
    return tuple(values)


@dataclass(frozen=True)
class LoopModePolicy:
    """All three interface alternatives, without granting execution authority.

    Preference order can include modes excluded by a profile or run. Installed
    executors remain unknown until supplied by a bound definition. Neither an
    allowed mode nor an installed executor establishes model/effect permission.
    This view adds no fields to serialized LoopConfig or LoopDefinition records.
    """

    preferred_modes: tuple[str, ...] = MODES
    profile_modes: tuple[str, ...] = MODES
    allowable_modes: tuple[str, ...] | None = None
    delegated_modes: tuple[str, ...] | None = None
    installed_executor_modes: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        for name in ("preferred_modes", "profile_modes", "allowable_modes",
                     "delegated_modes", "installed_executor_modes"):
            values = getattr(self, name)
            if values is None and name in (
                    "allowable_modes", "delegated_modes", "installed_executor_modes"):
                continue
            object.__setattr__(self, name, _mode_sequence(
                name, values, allow_empty=name in (
                    "delegated_modes", "installed_executor_modes")))

    def to_dict(self) -> dict:
        """Return detached eligibility facts for every universal mode slot."""
        return {
            "record_type": "loop_mode_policy_view/v1",
            "preferred_modes": list(self.preferred_modes),
            "delegated_modes": (list(self.delegated_modes)
                                if self.delegated_modes is not None else None),
            "executor_evidence": ("supplied_declaration"
                                  if self.installed_executor_modes is not None else "unknown"),
            "execution_authority_granted": False,
            "modes": [{
                "mode": mode,
                "preference_rank": (self.preferred_modes.index(mode)
                                    if mode in self.preferred_modes else None),
                "profile_permitted": mode in self.profile_modes,
                "configured_permitted": (mode in self.allowable_modes
                                         if self.allowable_modes is not None else None),
                "executor_installed": (mode in self.installed_executor_modes
                                       if self.installed_executor_modes is not None else None),
                "model_authority_required": mode != "deterministic",
                "model_authority_checked": False,
                "effect_authority_checked": False,
            } for mode in MODES],
        }

    def _permitted(self, mode: str) -> bool:
        return (self.allowable_modes is not None
                and mode in self.allowable_modes and mode in self.profile_modes)

    def _require_executor(self, mode: str) -> str:
        if (self.installed_executor_modes is None
                or mode not in self.installed_executor_modes):
            raise LoopModeUnavailableError(
                f"preferred Loop mode {mode!r} has no declared installed executor")
        return mode

    def choose(self, *, deterministic_available: bool = True,
               needs_judgement: bool = False) -> str:
        """Select the first feasible permitted preference, never fabricate one."""
        if type(deterministic_available) is not bool or type(needs_judgement) is not bool:
            raise ValueError("mode feasibility flags must be booleans")
        for mode in self.preferred_modes:
            if not self._permitted(mode):
                continue
            if mode == "deterministic" and (
                    not deterministic_available or needs_judgement):
                continue
            return self._require_executor(mode)
        raise LoopModeUnavailableError("no feasible permitted preferred Loop mode")

    def fallback(self, current: str) -> str:
        """Use the next explicit permitted alternative, or exhaust the order."""
        if type(current) is not str or current not in MODES:
            raise ValueError("fallback current mode must be a known Loop mode")
        if current in self.preferred_modes:
            for mode in self.preferred_modes[self.preferred_modes.index(current) + 1:]:
                if self._permitted(mode):
                    return self._require_executor(mode)
        return "abstain"


def default_loop_condition(framework: str) -> str:
    """Return the condition describing when another iteration may run."""
    if framework not in FRAMEWORKS:
        raise ValueError(f"framework must be one of {FRAMEWORKS}")
    return "chooser_selects_work" if framework == "open" else "steps_remain"


def normalize_exit_condition(exit_condition: str = "") -> str:
    """Return a valid current exit condition or the fixed-step default."""
    current = exit_condition or "steps_complete"
    if current not in EXIT_CONDITIONS:
        raise ValueError(f"exit_condition must be one of {EXIT_CONDITIONS}")
    return current


def self_test() -> dict:
    """Check derivation and fail-closed current condition handling."""
    tests: list[dict] = []

    def check(name: str, passed: bool) -> None:
        tests.append({"test": name, "passed": bool(passed)})

    check("fixed_and_custom_shapes_use_steps_remain",
          all(default_loop_condition(value) == "steps_remain"
              for value in ("nine_step", "five_step", "custom")))
    check("open_shape_uses_chooser_selects_work",
          default_loop_condition("open") == "chooser_selects_work")
    check("current_exit_conditions_are_explicit",
          normalize_exit_condition("steps_complete") == "steps_complete"
          and normalize_exit_condition("accepted_success")
          == "accepted_success")
    unknown_loop = unknown_exit = False
    try:
        default_loop_condition("unbounded")
    except ValueError:
        unknown_loop = True
    try:
        normalize_exit_condition("whenever")
    except ValueError:
        unknown_exit = True
    check("unknown_conditions_fail_closed", unknown_loop and unknown_exit)

    from .recursive_loop import Loop, LoopConfig, LoopError
    shape_mismatch = False
    try:
        LoopConfig(framework="open", loop_condition="steps_remain")
    except ValueError:
        shape_mismatch = True
    config = LoopConfig(exit_condition="accepted_success")
    check("config_stores_both_current_condition_fields",
          config.loop_condition == "steps_remain"
          and config.exit_condition == "accepted_success"
          and shape_mismatch)

    unknown_spec = False
    try:
        Loop.initialize({"objective": {"text_or_ref": "x"},
                         "conditions": {"exit_conditon": "steps_complete"}})
    except LoopError:
        unknown_spec = True
    current_loop = Loop.initialize({
        "objective": {"text_or_ref": "current"},
        "conditions": {"loop_condition": "steps_remain",
                       "exit_condition": "accepted_success"}})
    check("initialization_accepts_only_current_condition_fields",
          current_loop.config.exit_condition == "accepted_success"
          and unknown_spec)

    paused = Loop("pause", LoopConfig(framework="five_step")).pause()
    resumed = Loop.resume(paused)
    check("pause_and_resume_use_current_conditions",
          paused["record_type"] == "loop_pause/v2"
          and resumed.config.loop_condition == "steps_remain"
          and resumed.config.exit_condition == "steps_complete")

    tests.extend(_mode_policy_checks())

    passed = sum(1 for test in tests if test["passed"])
    return {"record_type": "loop_control_self_test", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


def _mode_policy_checks() -> list[dict]:
    """Inspect all modes and exercise selection through the sole Loop runtime."""
    from dataclasses import asdict, replace
    from itertools import permutations

    from .loop_definition import LoopStartRequest
    from .loop_profile_catalog import LOOP_PROFILE_ONTOLOGY, profile_catalog
    from .loop_role import LoopRelationship
    from .recursive_loop import (
        Loop,
        LoopConfig,
        LoopExecutorUnavailableError,
        LoopLedger,
        StepOutcome,
    )
    from .runtime_context import LoopRuntimeContext

    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    def refused(operation, exception=LoopExecutorUnavailableError):
        try:
            operation()
        except exception:
            return True
        return False

    config = LoopConfig(allowable_modes=("deterministic",))
    original_config = asdict(config)
    requested_order = ("non_deterministic", "hybrid", "deterministic")
    view = config.mode_policy(preferred_modes=requested_order).to_dict()
    check("all_three_mode_slots_remain_visible_under_single_mode_authority",
          tuple(item["mode"] for item in view["modes"]) == MODES
          and tuple(item["preference_rank"] for item in view["modes"]) == (2, 1, 0)
          and tuple(item["configured_permitted"] for item in view["modes"])
          == (True, False, False)
          and all(item["executor_installed"] is None for item in view["modes"])
          and not view["execution_authority_granted"]
          and all(not item["model_authority_checked"]
                  and not item["effect_authority_checked"] for item in view["modes"]))
    view["modes"][0]["configured_permitted"] = False
    check("mode_policy_views_do_not_mutate_config_or_serialized_contract",
          asdict(config) == original_config and "mode_policy" not in asdict(config)
          and config.mode_policy().to_dict()["modes"][0]["configured_permitted"])
    check("every_registered_profile_exposes_same_three_mode_interface",
          all(tuple(item["mode"] for item in profile.mode_policy().to_dict()["modes"])
              == MODES for profile in LOOP_PROFILE_ONTOLOGY)
          and all(len(item["mode_policy"]["modes"]) == 3 for item in profile_catalog()))
    code_profile = next(item for item in LOOP_PROFILE_ONTOLOGY
                        if item.profile_id == "practitioner.code_execution")
    profile_view = code_profile.mode_policy(preferred_modes=requested_order).to_dict()
    check("profile_permissions_do_not_claim_installed_executors_or_run_authority",
          tuple(item["profile_permitted"] for item in profile_view["modes"])
          == (True, False, False)
          and all(item["configured_permitted"] is None
                  and item["executor_installed"] is None for item in profile_view["modes"]))

    all_orders_work = True
    for order in permutations(MODES):
        owner = Loop("ordered modes", LoopConfig(preferred_modes=order))
        all_orders_work = all_orders_work and (
            owner.choose_mode() == order[0]
            and owner.fallback_mode(order[0]) == order[1]
            and owner.fallback_mode(order[1]) == order[2]
            and owner.fallback_mode(order[2]) == "abstain")
    check("all_six_explicit_preference_and_fallback_orders_are_respected", all_orders_work)
    deterministic = Loop("only a deterministic implementation", config)
    check("unavailable_code_or_required_judgement_never_fabricates_determinism",
          refused(lambda: deterministic.choose_mode(deterministic_available=False))
          and refused(lambda: deterministic.choose_mode(needs_judgement=True)))

    def partially_installed(preferred_modes):
        base = Loop("partial executor installation", LoopConfig(
            preferred_modes=preferred_modes))
        definition = replace(base.definition, installed_executor_modes=("deterministic",))
        context = LoopRuntimeContext.compatibility(
            capabilities=definition.required_capabilities,
            permissions=definition.permissions,
            executor_modes=definition.installed_executor_modes)
        return Loop(LoopStartRequest(
            "partial executor installation", definition, LoopRelationship.starting(),
            context, LoopLedger()))

    absent_primary = partially_installed(("hybrid", "deterministic", "non_deterministic"))
    absent_fallback = partially_installed(MODES)
    check("missing_preferred_executor_refuses_without_silent_mode_demotion",
          refused(absent_primary.choose_mode)
          and absent_fallback.choose_mode() == "deterministic")
    check("missing_fallback_executor_refuses_before_fabricating_alternative",
          refused(lambda: absent_fallback.fallback_mode("deterministic")))
    check("unknown_installation_is_not_executor_availability",
          refused(lambda: config.mode_policy().choose(), LoopModeUnavailableError))
    check("mode_policy_rejects_duplicate_unknown_and_nonsequence_modes",
          all(refused(lambda value=value: LoopConfig(preferred_modes=value), ValueError)
              for value in (("hybrid", "hybrid"), ("llm",), "hybrid", ()))
          and refused(lambda: deterministic.choose_mode(needs_judgement=1), ValueError))

    def wrong_fallback(_loop, _step, context):
        return StepOutcome(
            output="wrong fallback mode" if context.get("requested_mode") else "failed",
            mode="deterministic", failed=not bool(context.get("requested_mode")))

    owner = Loop("wrong deferred fallback", LoopConfig(
        framework="custom", custom_steps=("act",)))
    check("deferred_fallback_cannot_silently_report_different_execution_mode",
          refused(lambda: owner.run(handler=wrong_fallback))
          and any(item.get("failure_kind") == "mode_executor_mismatch"
                  for item in owner.ledger.events))
    owner = Loop("wrong immediate fallback", LoopConfig(
        framework="custom", custom_steps=("act",),
        preferred_modes=("hybrid", "deterministic")))

    def wrong_immediate(_loop, _step, context):
        return StepOutcome(output="wrong immediate fallback", mode="hybrid",
                           failed=not bool(context.get("requested_mode")))

    check("immediate_fallback_cannot_silently_report_different_execution_mode",
          refused(lambda: owner.run(handler=wrong_immediate))
          and any(item.get("failure_kind") == "mode_executor_mismatch"
                  for item in owner.ledger.events))
    return tests
