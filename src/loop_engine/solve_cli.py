"""Public solve command projection over the canonical solve service.

This module parses CLI authority and renders product results. Task semantics,
Loop execution, effects, verification, and Run History remain in their
canonical owners.
"""
from __future__ import annotations

import json
import os

from .cli_operations import (
    _apply_compile_provider_shortcut, _compile_gateway,
    _compile_provider_key, _task_feedback_from_args,
    _temporary_provider_key, resolve_cli_extensions, task_intake_from_args,
)


class ProviderSetupError(ValueError):
    """The selected onboarding profile has no usable provider reference."""


def _apply_quickstart(args) -> None:
    """Apply one explicit bounded onboarding authority profile."""
    if not args.quickstart:
        return
    selected_flags = [value for value in (
        args.ollama_api_key, args.mistral_api_key, args.openrouter_api_key,
        args.opencode_zen_api_key, args.opencode_go_api_key)
                      if value is not None]
    if not args.compile_provider and not selected_flags:
        priority = (
            ("openrouter", "OPENROUTER_API_KEY"),
            ("opencode_zen", "OPENCODE_ZEN_API_KEY"),
            ("ollama_cloud", "OLLAMA_API_KEY"),
            ("mistral", "MISTRAL_API_KEY"),
            ("opencode_go", "OPENCODE_GO_API_KEY"),
        )
        present = [provider for provider, environment_name in priority
                   if os.environ.get(environment_name, "").strip()]
        if not present:
            raise ProviderSetupError(
                "--quickstart needs one supported provider environment "
                "variable; run `loop-engine configure` for exact names")
        args.compile_provider = present[0]
    args.interaction_mode = "autonomous"
    args.authorize_model_calls = True
    if args.max_model_calls == 0:
        args.max_model_calls = 16
    if args.max_total_tokens is None:
        args.max_total_tokens = 1_000_000


def run_solve(args) -> int:
    """Perform and verify real work through the canonical Practitioner."""
    from dataclasses import replace
    from pathlib import Path

    from .code_nodes.solve_runtime import SolveRequest, solve_task
    from .code_nodes.solution_model_port import ModelExecution
    from .core.runtime_settings import ModelPolicyRequest, ModelTask
    from .core.settings_loader import load_runtime_settings

    try:
        _apply_quickstart(args)
        intake = task_intake_from_args(args)
        loaded = load_runtime_settings(args.settings_file or None)
        extension_application = resolve_cli_extensions(args, loaded.settings)
        settings = extension_application.settings
        _apply_compile_provider_shortcut(args, default_model_calls=16)
        if args.allow_source_to_model and not args.authorize_model_calls:
            raise ValueError(
                "--allow-source-to-model requires --authorize-model-calls")
        if (intake.kind in {"dataset", "repository", "task_pack"}
                and args.authorize_model_calls
                and not args.allow_source_to_model):
            raise PermissionError(
                "local source tasks require --allow-source-to-model")
        workspace = ""
        if args.workspace:
            selected = Path(args.workspace).expanduser().resolve()
            if selected.exists() and not selected.is_dir():
                raise ValueError("--workspace must name a directory")
            if selected.exists() and any(selected.iterdir()):
                raise ValueError(
                    "--workspace must be empty or not yet created")
            workspace = str(selected)
        runs_dir = args.runs_dir or settings.history.resolved_runs_dir()

        def execute_with_gateway(gateway=None, route_name=""):
            model_execution = None
            if args.authorize_model_calls:
                if args.max_model_calls < 1:
                    raise ValueError(
                        "authorized solve requires --max-model-calls >= 1")
                policy = ModelPolicyRequest(
                    thinking_power=(args.thinking_power
                                    or settings.models.default_thinking_power),
                    max_total_tokens=args.max_total_tokens,
                    max_route_attempts=args.max_model_calls,
                    route_names=((route_name or args.model_route,)
                                 if (route_name or args.model_route) else ()))
                request = settings.model_request(ModelTask(
                    prompt="solve authorization preflight", policy=policy))
                config = request.config
                if args.model_id:
                    config = replace(config, allowed_models=(args.model_id,))
                model_execution = ModelExecution(
                    gateway or settings.build_gateway(), config,
                    max_model_calls=args.max_model_calls,
                    llm_thinking_power=policy.thinking_power)
            return solve_task(SolveRequest(
                intake=intake, model_execution=model_execution,
                runs_dir=runs_dir,
                save_run_history=settings.history.save_run_history,
                interaction_mode=args.interaction_mode,
                feedback=_task_feedback_from_args(args),
                max_passes=args.max_passes,
                allow_network_reads=settings.operating.access_mode in (
                    "approved_external_read", "broad_external_read",
                    "approved_external_write"),
                allow_workspace_writes=(
                    settings.operating.construction_and_execution_mode
                    in ("sandbox_generate", "promotion_authorized")),
                allow_sandbox_commands=(
                    settings.operating.construction_and_execution_mode
                    in ("sandbox_generate", "promotion_authorized")),
                workspace_root=workspace,
                allow_source_materialization_to_model=
                    args.allow_source_to_model,
                extension_snapshot=
                    extension_application.snapshot.to_dict()))

        if args.compile_provider:
            if not args.authorize_model_calls:
                raise ValueError(
                    "a selected solve provider requires model-call authority")
            env_name, key = _compile_provider_key(args)
            with _temporary_provider_key(env_name, key):
                gateway, route_name = _compile_gateway(args, key)
                outcome = execute_with_gateway(gateway, route_name)
        else:
            if (args.provider_key_env or args.prompt_for_provider_key
                    or any(value is not None for value in (
                        args.ollama_api_key, args.openrouter_api_key,
                        args.mistral_api_key,
                        args.opencode_zen_api_key,
                        args.opencode_go_api_key))):
                raise ValueError(
                    "provider key options need a selected provider")
            outcome = execute_with_gateway()

        value = outcome.to_dict()
        if args.format == "json":
            print(json.dumps(value, indent=1))
        else:
            lines = [
                value["terminal_code"],
                value["summary"],
                "",
                "Artifacts:",
            ]
            artifacts = value["artifacts"]
            lines.extend(
                f"  {item['path']} ({'verified' if item.get('verified') else 'unverified'})"
                for item in artifacts)
            if not artifacts:
                lines.append("  none")
            lines.extend([
                "",
                f"Workspace: {value['workspace'] or 'none'}",
                "Verification: " + (
                    "passed" if value["verification"].get("passed")
                    else "not passed"),
                f"Run ID: {value['run_id']}",
                f"Run History: {value['run_history'].get('path', 'unavailable')}",
                f"Loops: {value['loop_count']}",
                f"Model calls: {value['model_calls']}",
                f"Tool calls: {value['tool_calls']}",
            ])
            if value["limitations"]:
                lines.extend(("", "Limitations:"))
                lines.extend(f"  {item}" for item in value["limitations"])
            if value["inspect_commands"]:
                lines.extend(("", "Inspect:"))
                lines.extend(f"  {item}" for item in value["inspect_commands"])
            if value["next_action"]:
                lines.extend(("", f"Next: {value['next_action']}"))
            print("\n".join(lines))
        return 0 if outcome.solved else 1
    except (OSError, RuntimeError, ValueError) as exc:
        terminal = ("AUTHORITY_REQUIRED" if isinstance(exc, PermissionError)
                    else "PROVIDER_UNAVAILABLE"
                    if isinstance(exc, ProviderSetupError)
                    else "VERIFICATION_FAILED")
        value = {
            "record_type": "solve_failure/v3", "solved": False,
            "terminal_code": terminal, "status": terminal,
            "summary": "Solve was refused before completion.",
            "artifacts": [], "workspace": args.workspace or "",
            "verification": {"passed": False},
            "limitations": [str(exc)],
            "next_action": (
                "Grant the exact requested authority and retry."
                if isinstance(exc, PermissionError)
                else "Run `loop-engine configure`, set one provider key, "
                     "and retry."
                if isinstance(exc, ProviderSetupError)
                else "Correct the request or configuration and retry."),
            "error": str(exc),
        }
        if args.format == "json":
            print(json.dumps(value, indent=1))
        else:
            print("\n".join((
                terminal, value["summary"], f"Reason: {exc}",
                f"Next: {value['next_action']}")))
        return 2


__all__ = ("run_solve",)
