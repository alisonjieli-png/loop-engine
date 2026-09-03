"""Public solve command projection over the canonical solve service.

This module parses CLI authority and renders product results. Task semantics,
Loop execution, effects, verification, and Run History remain in their
canonical owners.
"""
from __future__ import annotations

import json
import os
import sys

from .core.option_selection import SELECTION_REPORT_CONTRACT
from .cli_operations import (
    _apply_compile_provider_shortcut, _compile_gateway,
    _compile_provider_key, _task_feedback_from_args,
    _temporary_provider_key, resolve_cli_extensions, task_intake_from_args,
)


class ProviderSetupError(ValueError):
    """The selected onboarding profile has no usable provider reference."""


#: Names whose values never reach the progress stream, whatever an event
#: chooses to call them. This is a denial rather than a permission, and the
#: difference is the point: a permission list can only ever carry what was
#: already imagined, so a run that finds something worth saying is dropped in
#: silence for want of a name nobody wrote down in advance. That cost was
#: paid — the selection report published across whole campaigns with every
#: field of its content removed, the events saying a choice had been made and
#: never what it was.
_CREDENTIAL_MARKERS = (
    "secret", "password", "credential", "authorization", "bearer",
    "api_key", "apikey", "access_token", "refresh_token", "auth_token",
    "private_key", "cookie", "session_key", "passphrase")

#: Raw payload carriers. The exact prompt and output travel only as the two
#: tracing fields below, which the emitter governs and --quiet-model-io
#: suppresses; a bare "prompt" or "content" on some other event is not that
#: and does not travel.
_RAW_PAYLOAD_FIELDS = ("prompt", "content", "messages", "body", "raw")

#: The two fields that carry exact text on purpose, exempt from the value
#: bound because truncating a trace is the same as not having one.
_EXACT_TEXT_FIELDS = ("prompt_text", "output_text")

#: Bytes of any one other value. An event may report something long; the
#: stream should carry the shape of it without becoming the transport for a
#: whole artifact.
_PROGRESS_VALUE_BYTES = 4000


def _withheld(field_name: str) -> bool:
    """Whether a field must not reach the progress stream."""
    lowered = str(field_name).lower()
    return (lowered in _RAW_PAYLOAD_FIELDS
            or any(marker in lowered for marker in _CREDENTIAL_MARKERS))


def _progress_value(field_name: str, value):
    """Bound one reported value without changing what it says."""
    if field_name in _EXACT_TEXT_FIELDS:
        return value
    rendered = value if isinstance(value, str) else None
    if rendered is None:
        try:
            rendered = json.dumps(value, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            rendered = str(value)
        if len(rendered.encode("utf-8", "replace")) <= _PROGRESS_VALUE_BYTES:
            return value
    encoded = rendered.encode("utf-8", "replace")
    if len(encoded) <= _PROGRESS_VALUE_BYTES:
        return rendered
    kept = encoded[:_PROGRESS_VALUE_BYTES].decode("utf-8", "ignore")
    return kept + f"... [{len(encoded)} bytes, bounded for the stream]"


def _solve_progress(event: dict) -> None:
    """Write one secret-safe typed progress event to stderr."""
    if not isinstance(event, dict):
        return
    value = {"record_type": "solve_progress/v1"}
    for field_name, field_value in event.items():
        if field_value in (None, "", 0) or _withheld(field_name):
            continue
        value[field_name] = _progress_value(field_name, field_value)
    print(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False), file=sys.stderr, flush=True)


def _apply_quickstart(args) -> None:
    """Apply one explicit LLM-first onboarding authority profile."""
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
    args.practitioner_mode = "non_deterministic"
    args.authorize_model_calls = True
    if args.max_model_calls == 0:  # compatibility with older callers
        args.max_model_calls = None


def _context_budget_from_args(args):
    """Return an operator context budget, or None for the canonical default."""
    tokens = getattr(args, "context_budget_tokens", None)
    if tokens is None:
        return None
    from .core.context_budget import ContextBudgetPolicy
    return ContextBudgetPolicy(packet_estimated_tokens_max=int(tokens))


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
        _apply_compile_provider_shortcut(args, default_model_calls=None)
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
        maximum_model_calls = (
            args.max_model_calls if args.max_model_calls is not None
            else settings.loop.max_model_calls)
        maximum_passes = (
            args.max_passes if args.max_passes is not None
            else settings.loop.max_iterations)

        def execute_with_gateway(gateway=None, route_names=()):
            model_execution = None
            if args.authorize_model_calls:
                if (maximum_model_calls is not None
                        and maximum_model_calls < 1):
                    raise ValueError(
                        "--max-model-calls must be positive when provided")
                policy = ModelPolicyRequest(
                    thinking_power=(args.thinking_power
                                    or settings.models.default_thinking_power),
                    max_total_tokens=args.max_total_tokens,
                    max_route_attempts=None,
                    route_names=(tuple(route_names)
                                 if route_names else
                                 (args.model_route,) if args.model_route
                                 else ()))
                request = settings.model_request(ModelTask(
                    prompt="solve authorization preflight", policy=policy))
                config = request.config
                if args.model_id:
                    config = replace(config, allowed_models=(args.model_id,))
                model_execution = ModelExecution(
                    gateway or settings.build_gateway(), config,
                    max_model_calls=maximum_model_calls,
                    llm_thinking_power=policy.thinking_power)
            return solve_task(SolveRequest(
                intake=intake, model_execution=model_execution,
                runs_dir=runs_dir,
                save_run_history=settings.history.save_run_history,
                interaction_mode=args.interaction_mode,
                practitioner_mode=args.practitioner_mode,
                feedback=_task_feedback_from_args(args),
                max_passes=maximum_passes,
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
                    extension_application.snapshot.to_dict(),
                quiet_model_io=bool(getattr(args, "quiet_model_io", False)),
                allow_local_execution=bool(
                    getattr(args, "allow_local_execution", False)),
                context_budget=_context_budget_from_args(args),
                progress=_solve_progress))

        if args.compile_provider:
            if not args.authorize_model_calls:
                raise ValueError(
                    "a selected solve provider requires model-call authority")
            env_name, key = _compile_provider_key(args)
            with _temporary_provider_key(env_name, key):
                gateway, route_name = _compile_gateway(args, key)
                route_names = _solve_route_plan(
                    args, gateway, route_name)
                outcome = execute_with_gateway(gateway, route_names)
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
            if value.get("questions"):
                lines.extend(("", "Material questions:"))
                lines.extend(
                    f"  [{item['answer_slot']}] {item['question']}"
                    for item in value["questions"])
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
        from .code_nodes.solve_runtime import SolveError
        refused_by_contract = isinstance(exc, SolveError)
        value = {
            "record_type": "solve_failure/v3", "solved": False,
            "terminal_code": terminal, "status": terminal,
            "error_class": type(exc).__name__,
            "summary": (
                "Solve produced a result its typed outcome contract refused; "
                "inspect Run History for the Practitioner's own terminal."
                if refused_by_contract
                else "Solve was refused before completion."),
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


def self_test() -> dict:
    """Prove progress is typed, stderr-safe, and secret-free."""
    import contextlib
    import io

    stream = io.StringIO()
    with contextlib.redirect_stderr(stream):
        _solve_progress({
            "event_type": "model.step.started",
            "run_id": "adaptive-progress-test",
            "progress_sequence": 4,
            "pass_number": 2,
            "step": "decide_next",
            "loop_count": 17,
            "model_calls_completed": 3,
            "model_call_number": 4,
            "elapsed_seconds": 1.25,
            "prompt": "must-not-appear",
            "content": "must-not-appear",
            "authorization": "must-not-appear",
            "secret": "must-not-appear",
        })
    # A diagnostic must arrive saying what it found. A live campaign
    # produced orientation_invalid on four competitions and the published
    # event carried neither the attempt nor the findings, because the writer
    # keeps only the fields it recognizes. The detail travels as one named
    # field so any allowlist that carries it delivers the whole payload.
    detail_stream = io.StringIO()
    with contextlib.redirect_stderr(detail_stream):
        _solve_progress({
            "event_type": "practitioner.diagnostic",
            "run_id": "adaptive-progress-test",
            "diagnostic_code": "orientation_invalid",
            "diagnostic_detail": '{"attempt": 2, "findings": ["target absent"]}',
            "secret": "must-not-appear",
        })
    detail_raw = detail_stream.getvalue().strip()
    detail_value = json.loads(detail_raw)
    detail_survived = (
        "target absent" in detail_value.get("diagnostic_detail", "")
        and detail_value.get("diagnostic_code") == "orientation_invalid"
        and "must-not-appear" not in detail_raw)

    raw = stream.getvalue().strip()
    value = json.loads(raw)
    safe = (value["record_type"] == "solve_progress/v1"
            and value["event_type"] == "model.step.started"
            and value["pass_number"] == 2
            and value["model_call_number"] == 4
            and "must-not-appear" not in raw
            and not ({"prompt", "content", "authorization", "secret"}
                     & set(value)))
    # A field nobody named in advance must still arrive. The writer used to
    # keep only what it recognised, so the selection report travelled across
    # whole campaigns with all of its content removed: the events said a
    # choice had been made and never what it was.
    from .core.option_selection import admitted_selection
    publishable = set(admitted_selection(
        {"used_perspectives": ["p"], "used_question_refs": ["q"],
         "used_guidance_refs": ["g"], "wanted_but_absent": ["w"],
         "operator_gap": {"needed": "n", "tried": ["t"],
                          "runtime_said": "r"}},
        {"used_perspectives": ["p"], "used_question_refs": ["q"],
         "used_guidance_refs": ["g"]}))
    publishable.discard("named_but_not_offered")
    novel_stream = io.StringIO()
    with contextlib.redirect_stderr(novel_stream):
        _solve_progress({
            "event_type": "practitioner.options.selected",
            "run_id": "adaptive-progress-test",
            **{name: ["kept"] for name in publishable},
            "a_channel_no_one_predefined": "the run had something to say",
            "authorization": "must-not-appear",
            "api_key": "must-not-appear",
            "prompt": "must-not-appear",
        })
    novel_raw = novel_stream.getvalue().strip()
    novel_value = json.loads(novel_raw)
    heard = (not (publishable - set(novel_value))
             and novel_value.get("a_channel_no_one_predefined")
             == "the run had something to say"
             and "must-not-appear" not in novel_raw)
    tests = [{
        "test": "what_a_run_reports_is_heard_even_when_unnamed_in_advance",
        "passed": heard,
        "detail": "" if heard else novel_raw[:300],
    }, {
        "test": "a_credential_shaped_field_never_reaches_the_stream",
        "passed": not ({"authorization", "api_key", "prompt", "secret"}
                       & set(novel_value)),
        "detail": str(sorted(novel_value))[:200],
    }, {
        "test": "a_diagnostic_arrives_saying_what_it_found",
        "passed": detail_survived,
        "detail": ("a code with no payload names a problem and says nothing "
                   "about it"),
    }, {
        "test": "solve_progress_is_typed_stderr_and_secret_safe",
        "passed": safe,
        "detail": raw,
    }]
    from types import SimpleNamespace
    from .core.settings_loader import load_runtime_settings
    gateway = load_runtime_settings(None).settings.build_gateway()
    failover = _solve_route_plan(SimpleNamespace(
        allow_model_failover=True, model_id=""), gateway, "cloud.default")
    pinned = _solve_route_plan(SimpleNamespace(
        allow_model_failover=True,
        model_id="deepseek-v4-flash:0731"), gateway, "cloud.default")
    same_provider = {
        route for route in failover
        if route.startswith("cloud.")}
    providers_reached = {gateway.registry.get(name).provider
                         for name in failover}
    tests.append({
        "test": "solve_failover_is_one_ordered_policy_and_exact_pin_wins",
        "passed": (failover[0] == "cloud.default"
                   and {"cloud.default", "cloud.hard", "cloud.glm"}
                   <= same_provider
                   and len(providers_reached) >= 1
                   and pinned == ("cloud.default",)),
        "detail": ",".join(failover) + " | providers: "
                  + ",".join(sorted(providers_reached)),
    })
    # A settings-declared provider id resolves its key variable from the
    # provider's credential_env instead of failing on the builtin map.
    import tempfile
    from pathlib import Path as _Path
    from .cli_operations import _compile_provider_key
    with tempfile.TemporaryDirectory() as folder:
        settings_path = _Path(folder) / "settings.yaml"
        settings_path.write_text(
            "models:\n  providers:\n"
            "    - id: test_custom\n      kind: custom\n"
            "      credential_env: LOOP_ENGINE_TEST_CUSTOM_KEY\n"
            "      endpoint: https://gateway.example.test/v1/chat/completions\n"
            "      model: test-model\n", encoding="utf-8")
        previous = os.environ.get("LOOP_ENGINE_TEST_CUSTOM_KEY")
        os.environ["LOOP_ENGINE_TEST_CUSTOM_KEY"] = "test-value"
        try:
            custom_env, custom_key = _compile_provider_key(SimpleNamespace(
                compile_provider="test_custom", provider_key_env="",
                prompt_for_provider_key=False,
                settings_file=str(settings_path)))
            unknown_refused = False
            try:
                _compile_provider_key(SimpleNamespace(
                    compile_provider="never_declared", provider_key_env="",
                    prompt_for_provider_key=False,
                    settings_file=str(settings_path)))
            except ValueError:
                unknown_refused = True
        finally:
            if previous is None:
                os.environ.pop("LOOP_ENGINE_TEST_CUSTOM_KEY", None)
            else:
                os.environ["LOOP_ENGINE_TEST_CUSTOM_KEY"] = previous
    tests.append({
        "test": "settings_declared_compile_provider_resolves_its_credential_env",
        "passed": (custom_env == "LOOP_ENGINE_TEST_CUSTOM_KEY"
                   and custom_key == "test-value" and unknown_refused),
        "detail": f"{custom_env} resolved; undeclared provider refused",
    })
    return {"record_type": "solve_cli_progress_test/v1", "tests": tests,
            "passed": sum(item["passed"] for item in tests),
            "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}


def _solve_route_plan(args, gateway, selected_route: str) -> tuple[str, ...]:
    """Return one ordered route policy without creating another solve path.

    Same-provider routes come first: the configured provider keeps its
    existing precedence. Then, still behind the explicit
    ``--allow-model-failover`` authority and still skipping the pinned
    ``--model-id`` case, other configured providers join the ordered policy
    so one provider being unreachable does not end the run. Failover never
    bypasses authentication, permission, effect, output, or verification
    checks; permanent failures are classified per attempt and never retried
    on the same route.
    """
    if (not getattr(args, "allow_model_failover", False) or args.model_id
            or not selected_route):
        return (selected_route,) if selected_route else ()
    selected = gateway.registry.get(selected_route)
    routes = [selected]
    for route in gateway.registry.all():
        if (route.name == selected.name
                or route.provider != selected.provider
                or "counted_generation" not in route.purposes):
            continue
        try:
            gateway.providers[route.provider].output_capability_for(route.model)
        except (LookupError, ValueError):
            continue
        routes.append(route)
    for route in gateway.registry.all():
        if any(item.name == route.name for item in routes):
            continue
        if "counted_generation" not in route.purposes:
            continue
        try:
            gateway.providers[route.provider].output_capability_for(route.model)
        except (LookupError, ValueError):
            continue
        routes.append(route)
    return tuple(route.name for route in routes)


__all__ = ("run_solve",)
