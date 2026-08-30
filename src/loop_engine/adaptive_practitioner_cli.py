"""Public CLI adapter for the adaptive Practitioner task-build path.

This module turns parsed CLI authority into one adaptive Practitioner request,
streams bounded progress on stderr, and renders the final typed run result.
"""
from __future__ import annotations

import sys

from .cli_operations import (
    _apply_compile_provider_shortcut, _compile_gateway,
    _compile_provider_key, _emit_cli_result, _temporary_provider_key,
    _task_feedback_from_args, task_intake_from_args)

def _task_build_progress(event: dict) -> None:
    """Render one typed adaptive event at the public CLI boundary."""
    event_type = str(event.get("event_type") or "event")
    step = str(event.get("step") or "")
    objective = str(event.get("objective") or "")
    diagnostic = str(event.get("diagnostic_code") or "")
    detail = " ".join(
        item for item in (step, objective, diagnostic) if item)
    detail = f" {detail}" if detail else ""
    print(f"[{event_type}]{detail}", file=sys.stderr, flush=True)


def _task_build_lines(result: dict) -> list[str]:
    solved = bool(result.get("solved"))
    lines = [
        "Task build: " + ("VERIFIED WORKING" if solved else "NOT COMPLETED"),
        f"Run: {result.get('run_id')}",
        f"Mode: {result.get('mode')}",
        f"Practitioner passes: {result.get('passes')}",
        f"Final route: {result.get('final_route') or 'none'}",
        f"Physical model calls: {result.get('model_calls', 0)}",
    ]
    attempts = result.get("project_attempts") or []
    if attempts:
        latest = attempts[-1]
        lines.append(
            "Deterministic artifact checks: "
            + ("passed" if latest.get("deterministic_checks_passed")
               else "failed"))
        verified = [item.get("path") for item in latest.get("artifacts", ())
                    if item.get("verified")]
        if verified:
            lines.append("Verified artifacts: " + ", ".join(map(str, verified)))
    history = result.get("run_history") or {}
    if history:
        lines.append(
            f"Run History: {history.get('events')} events; chain "
            f"{'intact' if history.get('chain_intact') else 'broken'}")
        lines.append(f"Saved run: {history.get('path')}")
    if result.get("result_path"):
        lines.append(f"Full result: {result['result_path']}")
    lines.extend(["", "Loops executed:"])
    for loop in result.get("loop_details") or []:
        steps = loop.get("steps") or []
        modes = sorted({str(item.get("mode")) for item in steps
                        if item.get("mode")})
        lines.append(
            f"  {loop.get('loop_id')} | {loop.get('role')} | "
            f"{loop.get('profile_id')} | {loop.get('relationship')} | "
            f"{','.join(modes) or 'not run'}")
        lines.append(f"    goal: {loop.get('goal')}")
        lines.append(
            f"    input: {loop.get('input_roles') or []} -> "
            f"output: {loop.get('output_roles') or []}")
        for step in steps:
            lines.append(
                f"    {step.get('step')}: {step.get('output')} "
                f"[{step.get('mode')}; "
                f"{'accepted' if step.get('accepted') else 'not accepted'}]")
    if result.get("failures"):
        lines.extend(["", "Remaining failures:"])
        lines.extend(f"  {item}" for item in result["failures"])
    lines.append("Use --format json for every typed decision and context block.")
    return lines


def run_task_build(args) -> int:
    """Run a freeform task through the complete adaptive Practitioner."""
    from .code_nodes.solution_model_port import ModelExecution
    from .core.adaptive_practitioner import run_adaptive_practitioner
    from .core.adaptive_practitioner_records import (
        AdaptivePractitionerDependencies, AdaptivePractitionerRequest)
    from .core.model_gateway import ModelGatewayConfig
    from .core.settings_loader import load_runtime_settings
    from .templates.intake import TaskIntakeError

    try:
        intake = task_intake_from_args(args)
        calls_per_pass = 14
        _apply_compile_provider_shortcut(
            args, default_model_calls=calls_per_pass * args.max_passes)
        model_execution = None
        settings = load_runtime_settings(args.settings_file or None).settings
        if not args.compile_provider:
            from .templates.compiler import TaskCompileRequest, compile_task_value
            compiled = compile_task_value(TaskCompileRequest(
                text=intake.original_input, source_kind=intake.kind,
                source_refs=intake.source_refs,
                interaction_mode=args.interaction_mode,
                feedback=_task_feedback_from_args(args)))
            result = {
                "record_type": "task_build/v2",
                "status": "COMPILED_NEEDS_SEMANTIC_REVIEW",
                "build_complete": True, "solved": False,
                "execution_performed": False,
                "original_task": intake.original_input,
                "compiled_task": compiled,
                "model_calls": 0, "provider_calls": 0,
                "artifacts": [], "run_history": {},
                "next_action": (
                    "Run solve to perform work. Add one provider key option "
                    "when semantic review is required."),
            }
            _emit_cli_result(args, result, [
                "Task build: COMPILED",
                "Execution performed: no",
                "Provider calls: 0",
                f"Task type: {compiled.get('task_type')}",
                f"Output kind: {compiled.get('output_kind')}",
                "",
                f"Next: {result['next_action']}",
            ])
            return 0
        if args.practitioner_mode != "deterministic":
            if not args.authorize_model_calls or args.max_model_calls < 1:
                raise ValueError("task build needs a positive model-call budget")
            env_name, key = _compile_provider_key(args)
            with _temporary_provider_key(env_name, key):
                gateway, route_name = _compile_gateway(args, key)
                model_execution = ModelExecution(
                    gateway,
                    ModelGatewayConfig(
                        route_names=(route_name,), allow_failover=False,
                        max_route_attempts=1,
                        timeout_seconds=args.live_timeout,
                        max_total_tokens=args.max_total_tokens,
                        thinking_power=args.thinking_power or "medium"),
                    max_model_calls=args.max_model_calls,
                    llm_thinking_power=args.thinking_power or "medium")
                result = run_adaptive_practitioner(
                    AdaptivePractitionerRequest(
                        intake.original_input,
                        mode=args.practitioner_mode,
                        runs_dir=(args.runs_dir
                                  or settings.history.resolved_runs_dir()),
                        max_passes=args.max_passes,
                        interaction_mode=args.interaction_mode,
                        allow_network_reads=settings.operating.access_mode in (
                            "approved_external_read", "broad_external_read",
                            "approved_external_write"),
                        allow_workspace_writes=(
                            settings.operating.construction_and_execution_mode
                            in ("sandbox_generate", "promotion_authorized")),
                        allow_sandbox_commands=(
                            settings.operating.construction_and_execution_mode
                            in ("sandbox_generate", "promotion_authorized")),
                        source_kind=intake.kind,
                        source_refs=intake.source_refs,
                        feedback=_task_feedback_from_args(args)),
                    AdaptivePractitionerDependencies(
                        model_execution=model_execution,
                        progress=_task_build_progress))
        else:
            result = run_adaptive_practitioner(
                AdaptivePractitionerRequest(
                    intake.original_input, mode="deterministic",
                    runs_dir=(args.runs_dir
                              or settings.history.resolved_runs_dir()),
                    max_passes=args.max_passes,
                    interaction_mode=args.interaction_mode,
                    allow_network_reads=False,
                    allow_workspace_writes=False,
                    allow_sandbox_commands=False,
                    source_kind=intake.kind,
                    source_refs=intake.source_refs,
                    feedback=_task_feedback_from_args(args)),
                AdaptivePractitionerDependencies(
                    progress=_task_build_progress))
        _emit_cli_result(args, result, _task_build_lines(result))
        return 0 if result.get("solved") else 1
    except (TaskIntakeError, OSError, RuntimeError, ValueError) as exc:
        failure = {
            "record_type": "adaptive_task_build_failure/v1",
            "status": "NOT_YET_PROVEN", "solved": False,
            "error_type": type(exc).__name__, "error": str(exc),
        }
        _emit_cli_result(args, failure, [
            "Task build: FAILED",
            f"{type(exc).__name__}: {exc}",
            "No READY or PLANNED state is reported as completion.",
        ])
        return 2
