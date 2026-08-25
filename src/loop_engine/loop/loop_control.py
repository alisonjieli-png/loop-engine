"""Closed Loop condition and exit condition vocabulary.

This module owns condition names only. The canonical execution behavior stays
in ``recursive_loop.Loop``. A budget or deadline is a safety limit and never a
successful exit condition.
"""
from __future__ import annotations


FRAMEWORKS = ("nine_step", "five_step", "custom", "open")
LOOP_CONDITIONS = ("steps_remain", "chooser_selects_work")
EXIT_CONDITIONS = ("steps_complete", "accepted_success")


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

    passed = sum(1 for test in tests if test["passed"])
    return {"record_type": "loop_control_self_test", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
