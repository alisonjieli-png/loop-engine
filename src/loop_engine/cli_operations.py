"""Focused command implementations for the public Loop Engine CLI.

Argument parsing remains in ``__main__``. These functions own typed doctor,
model-routing, solve, and learning workflows so the CLI stays a thin adapter.
"""
from __future__ import annotations

import contextlib
import getpass
import json
import os
import re
import sys
from pathlib import Path


_COMPILE_PROVIDER_ENV = {
    "ollama_cloud": "OLLAMA_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "opencode_zen": "OPENCODE_ZEN_API_KEY",
    "opencode_go": "OPENCODE_GO_API_KEY",
}
_COMPILE_PROVIDER_ROUTE = {
    "ollama_cloud": "cloud.default",
    "mistral": "cloud.mistral",
    "openrouter": "cloud.openrouter",
    "opencode_zen": "cloud.opencode_zen.zero_cost",
    "opencode_go": "cloud.opencode_go",
}
_KEY_PROMPT_SENTINEL = "__prompt__"


def _emit_cli_result(args, record: dict, lines: list[str]) -> None:
    if args.format == "json":
        print(json.dumps(record, indent=1))
    else:
        print("\n".join(lines))


def _credential_is_present(description: dict) -> bool:
    reference = str(description.get("credential_ref") or "")
    return bool(reference.startswith("env:")
                and os.environ.get(reference[4:], "").strip())


def _safe_provider_description(provider) -> dict:
    description = provider.describe()
    loader = getattr(provider.adapter, "load_api_key", None)
    description["credential_present"] = (
        bool(loader()) if callable(loader)
        else _credential_is_present(description))
    description["credential_tested"] = False
    return description


def resolve_cli_extensions(args, settings, *, environ=None):
    """Apply recognized provider files and return the exact safe snapshot."""
    from .core.extension_discovery import (
        ExtensionApplicationRequest, ExtensionDiscoveryRequest,
        apply_provider_extensions,
        discover_extensions_as_loop)

    selected_env = os.environ if environ is None else environ
    snapshot = discover_extensions_as_loop(
        ExtensionDiscoveryRequest(
            explicit_roots=tuple(getattr(args, "extension_root", ()) or ()),
            project_root=os.getcwd(),
            include_defaults=not bool(getattr(
                args, "no_default_extensions", False))),
        selected_env)
    return apply_provider_extensions(ExtensionApplicationRequest(
        settings, snapshot, allow_paid=bool(getattr(
            args, "allow_paid_extension_routes", False))), selected_env)


def run_extensions_action(args) -> int:
    """Inspect added files without probing providers or executing code."""
    from .core.settings_loader import load_runtime_settings

    loaded = load_runtime_settings(args.settings_file or None)
    application = resolve_cli_extensions(args, loaded.settings)
    snapshot = application.snapshot
    value = snapshot.to_dict()
    value["provider_application"] = application.to_dict()
    action = args.extensions_action
    if action != "discover":
        field = {
            "providers": "providers", "capabilities": "capabilities",
            "intelligence": "intelligence_entries", "plugins": "plugins",
            "skills": "skills"}[action]
        value = {
            "record_type": f"extension_{action}_view/v1",
            "snapshot_digest": snapshot.content_digest,
            field: value[field],
            "provider_application": application.to_dict(),
        }
    if args.format == "json":
        print(json.dumps(value, indent=1))
    else:
        lines = [snapshot.ascii_tree(), "",
                 f"Activated provider routes: {len(application.activated_routes)}"]
        lines.extend(f"  {item}" for item in application.activated_routes)
        if application.inactive_routes:
            lines.append("Inactive provider routes:")
            lines.extend(f"  {route}: {reason}"
                         for route, reason in application.inactive_routes)
        lines.append("Use --format json for exact file and digest records.")
        print("\n".join(lines))
    return 0


def _task_compile_lines(output: dict) -> list[str]:
    compiled = output["compiled_task"]
    binding = compiled.get("binding") or {}
    work_item = compiled["work_item"]
    dispositions = binding.get("requirement_dispositions", ())
    delegated = [item["requirement_id"] for item in dispositions
                 if item.get("state") == "delegated_choice"]
    blocking = [item["requirement_id"] for item in dispositions
                if item.get("state") in (
                    "needs_clarification", "abstain_required")]
    status = (
        "OPEN" if not binding else
        "ABSTAIN" if binding.get("requires_abstention") else
        "NEEDS INPUT" if binding.get("requires_clarification") else
        "READY")
    pattern_id = str(binding.get("template_id") or "")
    pattern_name = (
        pattern_id.rsplit(".", 1)[-1].replace("_", " ")
        if pattern_id else "open task for LLM orientation")
    operation = str(work_item["coordinates"]["operator"]).replace("_", " ")
    response = str(
        work_item["coordinates"]["response_topology"]).replace("_", " ")
    if response == "artifact":
        response = "file or report"
    details = (
        "awaiting LLM orientation" if status == "OPEN" else
        "enough to continue" if status == "READY" else
        "required input is missing" if status == "NEEDS INPUT" else
        "cannot continue safely")
    lines = [
        f"Task build: {status}",
        f"Task type: {pattern_name}",
        f"Task details: {details}",
        f"Main work: {operation}",
        f"Expected output: {response}",
        f"Model calls before optional review: {output.get('model_calls', 0)}",
    ]
    if delegated:
        lines.append("Choices the Solution may make: "
                     + ", ".join(item.replace("_", " ")
                                 for item in delegated))
    if blocking:
        lines.append("Required details still missing: "
                     + ", ".join(item.replace("_", " ")
                                 for item in blocking))
    review = output.get("model_assisted_orientation")
    if isinstance(review, dict):
        reviewed = review.get("review") or {}
        ceiling_source = (
            "user override" if review.get("total_token_ceiling_source")
            == "user_override" else
            "derived from model maximum and exact prompt")
        lines.extend([
            "",
            "Model review:",
            f"  Status: {'ACCEPTED' if review.get('ok') else 'FAILED'}",
            f"  Provider: {review.get('provider') or 'unknown'}",
            f"  Model: {review.get('model') or 'unknown'}",
            f"  Provider calls: {review.get('model_calls')}",
            f"  Provider-reported tokens: {review.get('total_tokens')}",
            f"  Token ceiling: {review.get('total_token_ceiling')} "
            f"({ceiling_source})",
            "  Task type: " + str(
                reviewed.get("task_family") or "unknown").replace("_", " "),
            f"  Next action: {reviewed.get('next_action') or 'none'}",
            "  Ran the Solution: no",
        ])
    lines.extend(["", "Use --format json for the complete typed record."])
    return lines


def task_intake_from_args(args):
    from dataclasses import replace
    from .templates.intake import TaskIntakeRequest, intake_task

    external = tuple(value for value in (
        args.dataset, args.repository, args.url, args.task_pack) if value)
    if len(external) > 1:
        raise ValueError(
            "supply only one dataset, repository, URL, or task pack")
    instruction_file = None
    instruction = args.text
    if args.file and external:
        if args.text:
            raise ValueError(
                "use --text or --file for the task instruction, not both")
        instruction_file = intake_task(TaskIntakeRequest(file=args.file))
        instruction = instruction_file.original_input
    if args.dataset:
        request = TaskIntakeRequest(dataset=args.dataset, goal=instruction)
    elif args.repository:
        request = TaskIntakeRequest(repository=args.repository, goal=instruction)
    elif args.url:
        request = TaskIntakeRequest(url=args.url, goal=instruction)
    elif args.task_pack:
        if args.file or args.text:
            raise ValueError(
                "task packs already contain their task instruction")
        request = TaskIntakeRequest(task_pack=args.task_pack)
    elif args.file:
        if args.text:
            raise ValueError("use --text or --file, not both")
        request = TaskIntakeRequest(file=args.file)
    else:
        request = TaskIntakeRequest(text=args.text)
    result = intake_task(request)
    if instruction_file is not None:
        result = replace(result, metadata=(
            *result.metadata,
            ("task_file_ref", instruction_file.source_refs[0]),
            ("task_file_digest", instruction_file.content_digest)))
    return result


def completed_learning_producer(goal: str):
    from .loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    from .loop.recursive_loop import Loop, LoopConfig, StepOutcome

    loop = Loop(
        goal,
        LoopConfig(
            framework="custom", custom_steps=("act",), power="light",
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            exit_condition="accepted_success"),
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.self_improvement"),
        relationship=LoopRelationship.starting())
    loop.run(handler=lambda active, step, context: StepOutcome(
        output="candidate:prepared", mode="deterministic", confidence=0.95),
        max_steps=2)
    return loop


def run_configure(args) -> int:
    """Inspect provider configuration and print one safe next action."""
    from .core.settings_loader import load_runtime_settings

    loaded = load_runtime_settings(args.settings_file or None)
    extensions = resolve_cli_extensions(args, loaded.settings)
    gateway = extensions.settings.build_gateway()
    providers = [_safe_provider_description(provider)
                 for provider in gateway.providers.values()]
    shortcuts = []
    configured_ids = {item["provider_id"] for item in providers}
    for provider_id, environment_name in _COMPILE_PROVIDER_ENV.items():
        if provider_id in configured_ids:
            continue
        shortcuts.append({
            "provider_id": provider_id,
            "credential_ref": f"env:{environment_name}",
            "credential_present": bool(os.environ.get(
                environment_name, "").strip()),
            "credential_tested": False,
            "route_materialization": "per_invocation",
        })
    all_routes = [*providers, *shortcuts]
    present = [item for item in all_routes
               if item.get("credential_present")]
    if not present:
        next_action = (
            "Set one provider environment variable, then run configure again. "
            "For Ollama Cloud: export OLLAMA_API_KEY=your-key")
    elif len(present) == 1 and present[0]["provider_id"] == "ollama_cloud":
        next_action = (
            "loop-engine models probe ollama_cloud --model-route "
            "cloud.default --model-id deepseek-v4-flash:0731 "
            "--authorize-model-calls --max-model-calls 1 "
            "--max-total-tokens 70000")
    elif len(present) == 1 and present[0]["provider_id"] == "openrouter":
        next_action = (
            "Use --openrouter-api-key on solve to select a current exact "
            "zero-price route, or probe an explicitly configured paid route.")
    elif len(present) == 1 and present[0]["provider_id"] == "opencode_zen":
        next_action = (
            "Use --opencode-zen-api-key on solve. The command stops if the "
            "live catalog has no compatible zero-cost route.")
    else:
        next_action = (
            "Choose one exact provider and run models probe with bounded "
            "model-call authority before solve.")
    report = {
        "record_type": "provider_configuration/v1",
        "providers": all_routes,
        "credentials_present": [item["provider_id"] for item in present],
        "credentials_tested": False,
        "provider_calls_made": 0,
        "settings_source": loaded.file_path or "registered defaults",
        "extension_snapshot_digest": extensions.snapshot.content_digest,
        "next_action": next_action,
    }
    _emit_cli_result(args, report, [
        "Loop Engine provider configuration",
        "Provider calls made: 0",
        "Credentials present: " + (
            ", ".join(report["credentials_present"])
            if report["credentials_present"] else "none"),
        "Credentials tested: no",
        "",
        f"Next: {next_action}",
    ])
    return 0


def run_doctor(args) -> int:
    import os
    import platform
    import shutil
    from importlib.metadata import PackageNotFoundError, version

    from .architecture_contract import run_architecture_contract_checks
    from .core.settings_loader import load_runtime_settings

    try:
        distribution_version = version("loop-engine")
    except PackageNotFoundError:
        distribution_version = "source-tree"
    architecture = run_architecture_contract_checks()
    loaded = load_runtime_settings(args.settings_file or None)
    extensions = resolve_cli_extensions(args, loaded.settings)
    gateway = extensions.settings.build_gateway()
    providers = [_safe_provider_description(provider)
                 for provider in gateway.providers.values()]
    credential_ready = [item for item in providers
                        if item.get("credential_present")]
    docker_path = shutil.which("docker")
    report = {
        "record_type": "loop_engine_doctor/v1", "ok": architecture["passed"],
        "distribution_version": distribution_version,
        "python": platform.python_version(),
        "canonical_runtime": "loop_engine.loop.recursive_loop.Loop",
        "architecture_contract": architecture,
        "settings": extensions.settings.safe_summary(),
        "extensions": extensions.snapshot.to_dict(),
        "extension_provider_application": extensions.to_dict(),
        "providers_configured": providers,
        "provider_calls_made": 0,
        "deterministic_no_key_lane": "available",
        "solve_readiness": {
            "provider_credentials_present": [
                item["provider_id"] for item in credential_ready],
            "provider_credentials_tested": False,
            "docker_binary": docker_path or "",
            "generated_project_execution": (
                "dependency_detected_not_runtime_verified" if docker_path
                else "docker_not_found"),
            "preferred_probe": (
                "loop-engine models probe ollama_cloud --model-route "
                "cloud.default --model-id deepseek-v4-flash:0731 "
                "--authorize-model-calls --max-model-calls 1 "
                "--max-total-tokens 70000"),
        },
    }
    _emit_cli_result(args, report, [
        f"Loop Engine doctor: {'CONFIGURATION VALID' if report['ok'] else 'FAILED'}",
        f"Version: {distribution_version}",
        f"Python: {report['python']}",
        "Runtime: Loop",
        f"Architecture contract: {'passed' if architecture['passed'] else 'failed'}",
        "No-key demonstration: available",
        "Provider calls made: 0",
        "Provider definitions: "
        f"{len(providers)} configured, credentials not tested",
        "Added-file extensions: "
        f"{len(extensions.snapshot.roots)} root(s), "
        f"{len(extensions.activated_routes)} provider route(s) activated",
        "Credential references present: " + (
            ", ".join(item["provider_id"] for item in credential_ready)
            if credential_ready else "none"),
        "Generated-project sandbox: " + (
            "Docker command found; runtime and image not tested"
            if docker_path else "Docker command not found"),
        "",
        "This command checks configuration only. It does not prove that a "
        "provider key works.",
        "Run the exact provider probe shown in JSON before a model-backed solve.",
        "Use --format json for the complete typed record.",
    ])
    return 0 if report["ok"] else 1


def run_models_action(args) -> int:
    from hashlib import sha256

    from .core.model_routing_intelligence import (
        MODEL_ROUTING_PORTFOLIO_ID, ModelRouteBootstrapSelector,
        ModelRoutingEvidence, ModelSelectionRequest, ModelSelectorConfig,
        select_model_as_loop)
    from .core.settings_loader import load_runtime_settings
    from .templates.compiler import TaskCompileRequest, compile_task_value

    loaded = load_runtime_settings(args.settings_file or None)
    extensions = resolve_cli_extensions(args, loaded.settings)
    settings = extensions.settings
    gateway = settings.build_gateway()
    routes = gateway.registry.all()
    if args.models_action in ("inventory", "routes"):
        providers = [_safe_provider_description(provider)
                     for provider in gateway.providers.values()]
        report = {
            "record_type": ("model_routes/v1"
                            if args.models_action == "routes"
                            else "model_inventory/v1"),
            "providers": providers,
            "routes": [{
                "route_id": route.name, "provider_id": route.provider,
                "exact_model_id": route.model, "locality": route.locality,
                "purposes": list(route.purposes),
            } for route in routes],
            "task_compile_shortcuts": [
                {"flag": "--ollama-api-key", "provider": "ollama_cloud",
                 "credential_env": "OLLAMA_API_KEY"},
                {"flag": "--mistral-api-key", "provider": "mistral",
                 "credential_env": "MISTRAL_API_KEY"},
                {"flag": "--openrouter-api-key", "provider": "openrouter",
                 "credential_env": "OPENROUTER_API_KEY"},
                {"flag": "--opencode-zen-api-key",
                 "provider": "opencode_zen",
                 "credential_env": "OPENCODE_ZEN_API_KEY",
                 "route_materialization": "live_zero_cost_catalog"},
                {"flag": "--opencode-go-api-key", "provider": "opencode_go",
                 "credential_env": "OPENCODE_GO_API_KEY",
                 "route_materialization": "per_invocation"},
            ],
            "provider_calls_made": 0,
            "extensions": extensions.snapshot.to_dict(),
            "extension_provider_application": extensions.to_dict(),
        }
        provider_lines = [
            f"  {item['provider_id']}: key "
            f"{'present' if item['credential_present'] else 'not present'}; "
            "not tested"
            for item in providers]
        route_lines = [
            f"  {route.name}: {route.provider} / {route.model} "
            f"({route.locality})" for route in routes]
        _emit_cli_result(args, report, [
            "Model inventory: CONFIGURATION ONLY",
            "No provider was contacted.",
            "",
            "Providers:",
            *provider_lines,
            "",
            "Routes:",
            *route_lines,
            "",
            "Task-compilation shortcuts:",
            "  --ollama-api-key",
            "  --mistral-api-key",
            "  --openrouter-api-key",
            "  --opencode-zen-api-key (current zero-cost route)",
            "  --opencode-go-api-key (direct route created for the call)",
            "",
            "Use models probe PROVIDER with explicit authorization to test a "
            "credential.",
            "Use --format json for the complete typed record.",
        ])
        return 0
    if args.models_action == "benchmark":
        from .core.model_routing_intelligence_checks import run_frozen_benchmark
        result = run_frozen_benchmark()
        print(json.dumps(result, indent=1))
        return 0 if result["all_passed"] else 1
    if not args.text:
        print(json.dumps({"record_type": "model_explain_failure/v1",
                          "error": "models explain requires --text"}, indent=1))
        return 2
    compiled = compile_task_value(TaskCompileRequest(args.text))
    coordinates = compiled["work_item"]["coordinates"]
    operator = args.operator or coordinates["operator"]
    topology = args.response_topology or coordinates["response_topology"]
    selector = ModelRouteBootstrapSelector.from_gateway(
        gateway, ModelRoutingEvidence(), ModelSelectorConfig(settings))
    request = ModelSelectionRequest(
        request_id="explain:" + sha256(args.text.encode()).hexdigest()[:16],
        run_id="explain:not-executed", loop_id="explain:selection",
        role="practitioner", profile="practitioner.solver",
        run_mode=("deterministic" if args.deterministic_sufficient else "hybrid"),
        compiled_task_ref=compiled["compiled_task_id"],
        task_fingerprint=sha256(json.dumps(
            compiled["work_item"], sort_keys=True).encode()).hexdigest(),
        operator=operator, response_topology=topology,
        output_contract="compiled-task output contract",
        model_purpose=args.model_purpose,
        structured_output_required=topology not in ("text", "artifact"),
        input_context_estimate=max(1, len(args.text) // 4),
        expected_output_estimate=1024,
        verification_plan="typed output plus independent verification",
        allowed_localities=(("local",) if args.local_only
                            else ("local", "organization", "cloud")),
        deterministic_sufficient=args.deterministic_sufficient,
        deterministic_evidence_refs=(
            ("user-declared:verified-deterministic-procedure",)
            if args.deterministic_sufficient else ()),
        require_suitability_evidence=True)
    selected = select_model_as_loop(selector, request)
    print(json.dumps({
        "record_type": "model_selection_explanation/v1",
        "compiled_task": compiled, "portfolio_id": MODEL_ROUTING_PORTFOLIO_ID,
        "selection_loop_id": selected["loop_id"],
        "decision": selected["decision_record"], "provider_calls_made": 0,
        "note": ("unprobed routes remain rejected; run models probe with "
                 "explicit provider-call authority before live use"),
    }, indent=1))
    return 0 if selected["decision"].status != "abstained" else 1


def _task_feedback_from_args(args) -> tuple:
    from .templates.model import TaskFeedback

    feedback = []
    for raw in args.task_feedback:
        if "=" not in raw:
            raise ValueError(
                "--task-feedback must use registered_slot=value")
        slot_ref, value = raw.split("=", 1)
        feedback.append(TaskFeedback(slot_ref, value))
    return tuple(feedback)


def _custom_provider_credential_env(args, provider: str) -> str:
    """Resolve the credential variable for a settings-declared provider.

    Builtin providers use the fixed map above. Any other provider id must be
    declared in the settings file; its ``credential_env`` is the variable the
    provider adapter reads, so the key can only reach the endpoint through it.
    """
    from .core.settings_loader import load_runtime_settings

    loaded = load_runtime_settings(getattr(args, "settings_file", "") or None)
    for configured in loaded.settings.models.providers:
        if configured.provider_id != provider:
            continue
        if not configured.credential_env:
            raise ValueError(
                f"provider {provider!r} declares no credential_env in the "
                "settings file, so a key cannot reach its endpoint")
        return configured.credential_env
    known = ", ".join(sorted(_COMPILE_PROVIDER_ENV))
    raise ValueError(
        f"--compile-provider {provider!r} is neither a builtin provider "
        f"({known}) nor a provider declared in the settings file")


def _compile_provider_key(args) -> tuple[str, str]:
    provider = args.compile_provider
    standard_env = _COMPILE_PROVIDER_ENV.get(provider)
    if standard_env is None:
        standard_env = _custom_provider_credential_env(args, provider)
    explicit_key = getattr(args, "_provider_key_value", "")
    if explicit_key:
        return standard_env, explicit_key
    if args.prompt_for_provider_key and args.provider_key_env:
        raise ValueError(
            "use --prompt-for-provider-key or --provider-key-env, not both")
    if args.prompt_for_provider_key:
        if not sys.stdin.isatty():
            raise ValueError(
                "--prompt-for-provider-key requires an interactive terminal")
        key = getpass.getpass(f"{provider} API key: ").strip()
    else:
        source_env = args.provider_key_env or standard_env
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", source_env):
            raise ValueError("--provider-key-env is not a valid environment name")
        key = os.environ.get(source_env, "").strip()
        if not key:
            raise ValueError(
                f"provider key environment variable {source_env} is empty")
    if not key:
        raise ValueError("provider key is empty")
    return standard_env, key


def _apply_compile_provider_shortcut(
        args, default_model_calls: "int | None" = 1) -> None:
    selected = [
        ("ollama_cloud", args.ollama_api_key),
        ("mistral", args.mistral_api_key),
        ("openrouter", args.openrouter_api_key),
        ("opencode_zen", args.opencode_zen_api_key),
        ("opencode_go", args.opencode_go_api_key),
    ]
    active = [(provider, value)
              for provider, value in selected if value is not None]
    if not active:
        return
    provider, supplied_value = active[0]
    if args.compile_provider and args.compile_provider != provider:
        raise ValueError(
            "provider-specific key flag conflicts with --compile-provider")
    if args.provider_key_env or args.prompt_for_provider_key:
        raise ValueError(
            "provider-specific key flag already selects a hidden prompt")
    if args.max_model_calls == 0:
        args.max_model_calls = None
    if (default_model_calls is not None and default_model_calls < 1) \
            or (args.max_model_calls is not None
                and args.max_model_calls < 1):
        raise ValueError("model-call budget must be positive when provided")
    args.compile_provider = provider
    args._provider_key_value = (
        supplied_value if supplied_value != _KEY_PROMPT_SENTINEL else "")
    standard_env = _COMPILE_PROVIDER_ENV[provider]
    args.prompt_for_provider_key = (
        supplied_value == _KEY_PROMPT_SENTINEL
        and not bool(os.environ.get(standard_env, "").strip()))
    args.authorize_model_calls = True
    if args.max_model_calls is None and default_model_calls is not None:
        args.max_model_calls = default_model_calls


@contextlib.contextmanager
def _temporary_provider_key(env_name: str, key: str):
    previous = os.environ.get(env_name)
    os.environ[env_name] = key
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(env_name, None)
        else:
            os.environ[env_name] = previous


def _compile_gateway(args, key: str):
    from .core.settings_loader import load_runtime_settings
    from .core.task_compile_model import (
        OPENCODE_GO_DEFAULT_MODEL, opencode_go_gateway,
        opencode_zen_gateway, openrouter_zero_cost_gateway)

    provider = args.compile_provider
    if provider == "opencode_go":
        if args.model_id and args.model_id != OPENCODE_GO_DEFAULT_MODEL:
            raise ValueError(
                "the current OpenCode Go compile route is pinned to "
                f"{OPENCODE_GO_DEFAULT_MODEL}")
        route_name = args.model_route or _COMPILE_PROVIDER_ROUTE[provider]
        if route_name != _COMPILE_PROVIDER_ROUTE[provider]:
            raise ValueError(
                "the current OpenCode Go compile route is cloud.opencode_go")
        return opencode_go_gateway(key), route_name
    if provider == "opencode_zen":
        route_name = args.model_route or _COMPILE_PROVIDER_ROUTE[provider]
        if route_name != _COMPILE_PROVIDER_ROUTE[provider]:
            raise ValueError(
                "the OpenCode Zen shortcut materializes "
                "cloud.opencode_zen.zero_cost")
        return opencode_zen_gateway(key, args.model_id), route_name
    if provider == "openrouter":
        route_name = args.model_route or "cloud.openrouter.zero_cost"
        if route_name != "cloud.openrouter.zero_cost":
            raise ValueError(
                "the OpenRouter key shortcut materializes "
                "cloud.openrouter.zero_cost; configure a named settings "
                "route for an explicitly paid model")
        return openrouter_zero_cost_gateway(
            key, args.model_id,
            maximum_output_tokens=args.max_total_tokens), route_name

    loaded = load_runtime_settings(args.settings_file or None)
    gateway = loaded.settings.build_gateway()
    candidates = [
        route for route in gateway.registry.all()
        if route.provider == provider
        and "counted_generation" in route.purposes
        and (not args.model_route or route.name == args.model_route)
        and (not args.model_id or route.model == args.model_id)
    ]
    if not candidates:
        raise ValueError(
            "no configured counted-generation route matches the selected "
            "compile provider, route, and model")
    preferred = _COMPILE_PROVIDER_ROUTE.get(provider, "")
    route = next(
        (item for item in candidates if item.name == preferred), candidates[0])
    return gateway, route.name


def run_task_compile(args) -> int:
    from .templates.compiler import TaskCompileRequest, compile_task
    from .templates.intake import TaskIntakeError
    try:
        intake = task_intake_from_args(args)
        result = compile_task(TaskCompileRequest(
            text=intake.original_input, source_kind=intake.kind,
            source_refs=intake.source_refs,
            interaction_mode=args.interaction_mode,
            feedback=_task_feedback_from_args(args)))
        _apply_compile_provider_shortcut(args)
        output = {"record_type": "task_compile_result/v1",
                  "intake": intake.to_dict(), **result}
        if not args.compile_provider:
            if (args.prompt_for_provider_key or args.provider_key_env
                    or args.authorize_model_calls):
                raise ValueError(
                    "provider key and model-call options require "
                    "--compile-provider")
            _emit_cli_result(args, output, _task_compile_lines(output))
            return 0
        if not args.authorize_model_calls:
            raise ValueError(
                "--compile-provider requires --authorize-model-calls")
        if args.max_model_calls != 1:
            raise ValueError(
                "provider-assisted compilation requires --max-model-calls 1")

        from .core.task_compile_model import (
            ModelAssistedCompileRequest, review_compiled_task)

        env_name, key = _compile_provider_key(args)
        with _temporary_provider_key(env_name, key):
            gateway, route_name = _compile_gateway(args, key)
            review = review_compiled_task(ModelAssistedCompileRequest(
                compiled_task=result["compiled_task"],
                provider=args.compile_provider,
                route_name=route_name,
                interaction_mode=args.interaction_mode,
                max_physical_model_calls=args.max_model_calls,
                max_total_tokens=args.max_total_tokens,
                timeout_seconds=args.live_timeout,
                thinking_power=args.thinking_power or "medium",
            ), gateway)
        output["model_assisted_orientation"] = review
        output["total_model_calls"] = (
            result["model_calls"] + review["model_calls"])
        _emit_cli_result(args, output, _task_compile_lines(output))
        return 0 if review["ok"] else 1
    except (TaskIntakeError, ValueError) as exc:
        failure = {"record_type": "task_compile_failure/v1",
                   "error": str(exc)}
        _emit_cli_result(args, failure, [
            "Task build: FAILED",
            str(exc),
            "Use --format json for the complete typed failure.",
        ])
        return 2


def run_learn(args) -> int:
    import hashlib
    import os

    from .core.run_history import (
        default_runs_dir, saved_run_ids, verify_saved_run)
    from .memory.model.memory_type import (MemoryIdentity, MemoryLifecycle,
                                           MemoryScope, MemoryType)
    from .memory.semantic.record import SemanticMemoryRecord
    from .memory.storage.repository import CandidateJournal, LearningPolicy

    if not args.lesson.strip():
        print(json.dumps({"record_type": "learning_candidate_failure/v1",
                          "error": "learn requires --lesson; Loop Engine does "
                                   "not invent a reusable claim"}, indent=1))
        return 2
    runs_dir = default_runs_dir(args.runs_dir or "")
    saved = sorted(
        saved_run_ids(runs_dir),
        key=lambda name: os.path.getmtime(os.path.join(runs_dir, name)))
    if not saved:
        print(json.dumps({"record_type": "learning_candidate_failure/v1",
                          "error": "no saved Run History exists"}, indent=1))
        return 1
    source_run = verify_saved_run(runs_dir, saved[-1])
    lesson_digest = hashlib.sha256(args.lesson.encode()).hexdigest()
    journal = CandidateJournal()
    producer = completed_learning_producer(
        f"derive candidate from verified run {source_run['run_id']}")
    transition = journal.stage(SemanticMemoryRecord(
        identity=MemoryIdentity(
            f"candidate.learn.{lesson_digest[:16]}", "1.0.0",
            lesson_digest, MemoryType.SEMANTIC),
        subject=f"run:{source_run['run_id']}", predicate="suggests",
        object_value=args.lesson, claim_type="derived", scope=MemoryScope.PROJECT,
        lifecycle=MemoryLifecycle.CANDIDATE), producer_loop=producer,
        policy=LearningPolicy(), evidence_refs=(
            f"run_history:{source_run['run_id']}:{source_run['head_digest']}",
            *tuple(args.evidence)))
    print(json.dumps({"record_type": "learning_candidates/v1",
                      "staged": [transition.to_dict()],
                      "storage": str(journal.journal),
                      "note": "candidate staged; independent review required"},
                     indent=1))
    return 0


def run_candidate_action(args) -> int:
    from .memory.model.memory_type import MemoryType
    from .memory.storage.repository import (
        CandidateJournal, LearningDecision, LearningPolicy,
        LearningRecordRef, LearningTransitionResult)
    if not all((args.candidate_id, args.candidate_version,
                args.candidate_digest, args.decision_reason, args.evidence)):
        print(json.dumps({
            "record_type": "learning_governance_failure/v1",
            "error": ("candidate governance requires exact identity, reason, "
                      "and at least one evidence reference")}, indent=1))
        return 2
    journal = CandidateJournal()
    policy = LearningPolicy()
    ref = LearningRecordRef(args.candidate_id, args.candidate_version,
                            args.candidate_digest, MemoryType.SEMANTIC)
    evidence = tuple(args.evidence)
    try:
        if args.candidate_action == "review":
            transition = journal.review(
                ref, policy=policy,
                evaluator=lambda record: LearningDecision(
                    args.decision == "accept", args.decision_reason, evidence))
        elif args.candidate_action == "promote":
            reviewed = LearningTransitionResult(
                journal.get_exact(ref),
                journal.governance_history(ref.record_id)[-1])
            transition = journal.promote(
                reviewed, policy=policy,
                authorizer=lambda record, review: LearningDecision(
                    args.decision == "accept", args.decision_reason, evidence))
        else:
            transition = journal.rollback(
                ref, policy=policy,
                authorizer=lambda record: LearningDecision(
                    args.decision == "accept", args.decision_reason, evidence))
        print(json.dumps({
            "record_type": "learning_governance_transition/v1",
            "action": args.candidate_action,
            "transition": transition.to_dict(),
            "journal_validation": journal.validate_journal()}, indent=1))
        return 0
    except (OSError, TypeError, ValueError, PermissionError) as exc:
        print(json.dumps({"record_type": "learning_governance_failure/v1",
                          "action": args.candidate_action,
                          "error": str(exc)}, indent=1))
        return 1


def run_five_step_demo(args) -> int:
    """Run a real no-key compile, solve, verify, history, and candidate stage."""
    import hashlib
    import tempfile
    from pathlib import Path

    from .code_nodes.solve_runtime import (
        SolveRequest, StructuredNormalizationResolver, solve_task)
    from .core.settings_loader import load_runtime_settings
    from .memory.model.memory_type import (MemoryIdentity, MemoryLifecycle,
                                           MemoryScope, MemoryType)
    from .memory.semantic.record import SemanticMemoryRecord
    from .memory.storage.repository import CandidateJournal, LearningPolicy
    from .templates.intake import TaskIntakeRequest, intake_task

    settings = load_runtime_settings(args.settings_file or None).settings
    goal = args.text or "Validate and normalize a structured customer record."
    with tempfile.TemporaryDirectory(prefix="loop-engine-five-step-") as root:
        source = Path(root) / "customer.json"
        source.write_text(json.dumps({
            " customer_id ": " C-100 ", " status ": " active ",
        }), encoding="utf-8")
        outcome = solve_task(SolveRequest(
            intake=intake_task(TaskIntakeRequest(
                dataset=str(source), goal=goal)),
            runs_dir=(args.runs_dir or settings.history.resolved_runs_dir()),
            save_run_history=True,
            deterministic_resolvers=(
                StructuredNormalizationResolver(source),)))
    if not outcome.solved:
        failure = {"record_type": "five_step_demo/v2",
                   "solved": False, "failure": outcome.to_dict()}
        _emit_cli_result(args, failure, [
            "Five-step demonstration: FAILED",
            f"Failure: {outcome.failure_code or 'unknown'}",
            "Use --format json for the complete typed failure.",
        ])
        return 1
    lesson = "Normalize surrounding whitespace without changing typed values."
    digest = hashlib.sha256(lesson.encode()).hexdigest()
    transition = CandidateJournal().stage(SemanticMemoryRecord(
        identity=MemoryIdentity(
            f"candidate.demo.{outcome.run_id[-16:]}", "1.0.0", digest,
            MemoryType.SEMANTIC),
        subject="structured_normalization", predicate="suggests",
        object_value=lesson, claim_type="derived", scope=MemoryScope.PROJECT,
        lifecycle=MemoryLifecycle.CANDIDATE),
        producer_loop=completed_learning_producer(
            f"stage candidate from {outcome.run_id}"),
        policy=LearningPolicy(), evidence_refs=(
            f"run_history:{outcome.run_id}:"
            f"{outcome.run_history['head_digest']}",))
    report = {
        "record_type": "five_step_demo/v2", "solved": True,
        "steps": {
            "1_install_and_verify": "loop-engine doctor",
            "2_configure": "deterministic no-key settings",
            "3_compile": outcome.compiled_task["compiled_task_id"],
            "4_solve_and_verify": {
                "run_id": outcome.run_id,
                "mode": outcome.selected_mode,
                "verified": outcome.verification["passed"],
                "run_history": outcome.run_history,
            },
            "5_stage_learning_candidate": {
                "candidate": transition.to_dict(),
                "state": "candidate_only",
                "next": "independent candidates review then promote",
            },
        },
        "provider_calls": 0,
    }
    history = outcome.run_history
    _emit_cli_result(args, report, [
        "Five-step demonstration: PASSED",
        f"Compiled task: {outcome.compiled_task['compiled_task_id']}",
        f"Solution mode: {outcome.selected_mode}",
        f"Verified: {'yes' if outcome.verification['passed'] else 'no'}",
        f"Run History: {history['events']} events; "
        f"chain {'intact' if history['chain_intact'] else 'broken'}",
        f"Saved run: {history['path']}",
        "Learning candidate: staged, not promoted",
        "Provider calls: 0",
        "",
        "Next: start Studio with a free port:",
        f"  loop-engine studio --port 0 --runs-dir "
        f"{args.runs_dir or settings.history.resolved_runs_dir()}",
        "Use --format json for the complete typed record.",
    ])
    return 0


def run_plugin_action(args) -> int:
    """Discover, inspect, or resolve exact plugin bundles."""
    from .core.plugin_bundles import (
        PluginBundleError, PluginDiscoveryRequest, PluginResolutionRequest,
        discover_plugin_bundles, resolve_plugin_snapshot_as_loop)
    from .core.skill_registry import (
        SkillAdmissionRecord, SkillRegistry)
    installed=tuple(args.plugin_root or ())
    project=tuple(args.project_plugin_root or ())
    try:
        discovery=discover_plugin_bundles(PluginDiscoveryRequest(
            installed,project,args.engine_api_version))
        if args.plugin_action in ("discover","inspect"):
            manifests=discovery.manifests
            if args.plugin_id:
                manifests=tuple(x for x in manifests if x.plugin_id==args.plugin_id)
                if not manifests:
                    raise PluginBundleError("requested plugin was not discovered")
            result={**discovery.to_dict(),
                    "manifests":[{**x.body(),"source":x.source,
                                  "content_digest":x.content_digest}
                                 for x in manifests]}
            if args.format=="json": print(json.dumps(result,indent=1))
            else:
                print(f"Plugins: {len(manifests)} candidate bundle(s)")
                for item in manifests:
                    print(f"  {item.plugin_id}@{item.version} [{item.source}] "
                          f"{item.content_digest[:12]}")
            return 0
        registry=SkillRegistry()
        for root in tuple(args.skill_root or ()):
            registry.discover((root,))
        for path in tuple(args.skill_admission or ()):
            value=json.loads(Path(path).read_text(encoding="utf-8"))
            records=value if isinstance(value,list) else [value]
            for record in records:
                registry.admit(SkillAdmissionRecord.from_dict(record))
        snapshot=resolve_plugin_snapshot_as_loop(PluginResolutionRequest(
            installed,project,registry,args.engine_api_version))
        if args.format=="json": print(json.dumps(snapshot.to_dict(),indent=1))
        else: print(snapshot.ascii_tree())
        return 0
    except (PluginBundleError,ValueError,OSError,KeyError) as exc:
        if args.format=="json":
            print(json.dumps({"record_type":"plugin_cli_failure/v1",
                              "status":"FAILED","reason":str(exc)},indent=1))
        else: print(f"Plugin operation failed: {exc}")
        return 2
