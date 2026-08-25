"""YAML and environment loading for typed Loop Engine settings.

The loader owns syntax, file discovery, precedence, and safe file creation.
``runtime_settings`` owns the types and runtime composition. Unknown keys fail
closed so a misspelled setting cannot silently change a run.
"""
from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import Mapping, Sequence

from ..loop.recursive_loop import MODEL_THINKING_POWER_LEVELS
from .operating_profile import Limits, OperatingProfile
from .runtime_settings import (DEFAULT_SETTINGS_ENV, SETTINGS_VERSION,
                               EscalationSettings, HistorySettings,
                               LoopConfigOverride, LoopDefaults,
                               ModelPolicyRequest, ModelSettings, ModelTask,
                               ModelTier,
                               ProviderSettings, RuntimeSettings,
                               SearchSettings, SettingsError,
                               SettingsLoadResult, SettingsWriteResult)


def _tuple(value, field_name: str) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(part) for part in value)
    raise SettingsError(f"{field_name} must be a list or comma-separated text")


def _mapping(value, field_name: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise SettingsError(f"{field_name} must be a mapping")
    return dict(value)


def _known(mapping: Mapping, allowed: Sequence[str], field_name: str) -> None:
    unknown = sorted(set(mapping) - set(allowed))
    if unknown:
        raise SettingsError(f"unknown {field_name} settings: {unknown}")


def _boolean(value, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    raise SettingsError(f"{field_name} must be true or false")


def _loop(value: Mapping) -> LoopDefaults:
    body = _mapping(value, "loop")
    _known(body, ("framework", "allowable_modes", "preferred_modes",
                  "delegated_modes", "max_depth",
                  "exit_condition", "success_confidence_min"), "loop")
    base = LoopDefaults()
    return LoopDefaults(
        framework=str(body.get("framework", base.framework)),
        allowable_modes=_tuple(body.get(
            "allowable_modes", base.allowable_modes), "loop.allowable_modes"),
        preferred_modes=_tuple(body.get(
            "preferred_modes", base.preferred_modes), "loop.preferred_modes"),
        delegated_modes=_tuple(body.get(
            "delegated_modes", base.delegated_modes), "loop.delegated_modes"),
        max_depth=int(body.get("max_depth", base.max_depth)),
        exit_condition=str(body.get(
            "exit_condition", base.exit_condition)),
        success_confidence_min=float(body.get(
            "success_confidence_min", base.success_confidence_min)))


def _search(value: Mapping) -> SearchSettings:
    body = _mapping(value, "search")
    _known(body, ("mode", "lexical_backend", "vector_backend",
                  "vector_model", "top_k", "zero_model_first"), "search")
    base = SearchSettings()
    return SearchSettings(
        mode=str(body.get("mode", base.mode)),
        lexical_backend=str(body.get(
            "lexical_backend", base.lexical_backend)),
        vector_backend=str(body.get("vector_backend", base.vector_backend)),
        vector_model=str(body.get("vector_model", base.vector_model)),
        top_k=int(body.get("top_k", base.top_k)),
        zero_model_first=_boolean(body.get(
            "zero_model_first", base.zero_model_first),
            "search.zero_model_first"))


def _provider(value: Mapping) -> ProviderSettings:
    body = _mapping(value, "models.providers item")
    _known(body, ("id", "kind", "enabled", "credential_env", "endpoint",
                  "model", "wire", "locality", "counts_as_evidence",
                  "maximum_output_tokens", "maximum_output_source",
                  "purposes"), "provider")
    if not body.get("id"):
        raise SettingsError("each models.providers item needs id")
    return ProviderSettings(
        provider_id=str(body["id"]),
        kind=str(body.get("kind", "builtin")),
        enabled=_boolean(body.get("enabled", True), "provider.enabled"),
        credential_env=str(body.get("credential_env", "")),
        endpoint=str(body.get("endpoint", "")),
        model=str(body.get("model", "")),
        wire=str(body.get("wire", "openai")),
        locality=str(body.get("locality", "cloud")),
        counts_as_evidence=_boolean(body.get(
            "counts_as_evidence", False), "provider.counts_as_evidence"),
        maximum_output_tokens=(
            int(body["maximum_output_tokens"])
            if body.get("maximum_output_tokens") is not None else None),
        maximum_output_source=str(body.get("maximum_output_source", "")),
        purposes=_tuple(body.get(
            "purposes", ("counted_generation", "decide_label")),
            "provider.purposes"))


def _tiers(value: Mapping, base: ModelSettings) -> tuple[ModelTier, ...]:
    raw = _mapping(value, "models.tiers")
    unknown = sorted(set(raw) - set(MODEL_THINKING_POWER_LEVELS))
    if unknown:
        raise SettingsError(f"unknown model tiers: {unknown}")
    by_name = {tier.name: tier for tier in base.tiers}
    for name, raw_item in raw.items():
        item = _mapping(raw_item, f"models.tiers.{name}")
        _known(item, ("routes", "max_output_tokens", "timeout_seconds",
                      "max_attempts"), f"models.tiers.{name}")
        old = by_name[name]
        output_value = item.get(
            "max_output_tokens", old.max_output_tokens)
        by_name[name] = ModelTier(
            name=name,
            routes=_tuple(item.get("routes", old.routes),
                          f"models.tiers.{name}.routes"),
            max_output_tokens=(None if output_value is None
                               else int(output_value)),
            timeout_seconds=float(item.get(
                "timeout_seconds", old.timeout_seconds)),
            max_attempts=int(item.get("max_attempts", old.max_attempts)))
    return tuple(by_name[name] for name in MODEL_THINKING_POWER_LEVELS)


def _models(value: Mapping) -> ModelSettings:
    body = _mapping(value, "models")
    _known(body, ("default_thinking_power", "providers", "tiers",
                  "escalation", "allow_local_counted_generation"), "models")
    base = ModelSettings()
    raw_providers = body.get("providers")
    if raw_providers is None:
        providers = base.providers
    elif isinstance(raw_providers, list):
        providers = tuple(_provider(item) for item in raw_providers)
    else:
        raise SettingsError("models.providers must be a list")
    raw_escalation = _mapping(body.get("escalation", {}),
                              "models.escalation")
    _known(raw_escalation, ("enabled", "order", "on_errors",
                            "max_tier_changes"), "models.escalation")
    escalation = EscalationSettings(
        enabled=_boolean(raw_escalation.get(
            "enabled", base.escalation.enabled), "models.escalation.enabled"),
        order=_tuple(raw_escalation.get(
            "order", base.escalation.order), "models.escalation.order"),
        on_errors=_tuple(raw_escalation.get(
            "on_errors", base.escalation.on_errors),
            "models.escalation.on_errors"),
        max_tier_changes=int(raw_escalation.get(
            "max_tier_changes", base.escalation.max_tier_changes)))
    return ModelSettings(
        default_thinking_power=str(body.get(
            "default_thinking_power", base.default_thinking_power)),
        providers=providers,
        tiers=_tiers(body.get("tiers", {}), base),
        escalation=escalation,
        allow_local_counted_generation=_boolean(body.get(
            "allow_local_counted_generation",
            base.allow_local_counted_generation),
            "models.allow_local_counted_generation"))


def _operating(value: Mapping) -> OperatingProfile:
    body = _mapping(value, "operating")
    _known(body, ("access_mode", "reasoning_and_model_mode",
                  "construction_and_execution_mode", "effort_mode",
                  "optimization_mode", "limits"), "operating")
    raw_limits = _mapping(body.get("limits", {}), "operating.limits")
    limit_names = ("wall_time_seconds", "model_cost",
                   "maximum_parallel_practitioners",
                   "maximum_recursion_depth", "memory_gib")
    _known(raw_limits, limit_names, "operating.limits")
    base = OperatingProfile()
    limits = Limits(**{name: raw_limits.get(name, getattr(base.limits, name))
                       for name in limit_names})
    return OperatingProfile(
        access_mode=str(body.get("access_mode", base.access_mode)),
        reasoning_and_model_mode=str(body.get(
            "reasoning_and_model_mode", base.reasoning_and_model_mode)),
        construction_and_execution_mode=str(body.get(
            "construction_and_execution_mode",
            base.construction_and_execution_mode)),
        effort_mode=str(body.get("effort_mode", base.effort_mode)),
        optimization_mode=str(body.get(
            "optimization_mode", base.optimization_mode)),
        limits=limits)


def _history(value: Mapping) -> HistorySettings:
    body = _mapping(value, "history")
    _known(body, ("runs_dir", "save_run_history"), "history")
    base = HistorySettings()
    return HistorySettings(
        runs_dir=str(body.get("runs_dir", base.runs_dir)),
        save_run_history=_boolean(body.get(
            "save_run_history", base.save_run_history),
            "history.save_run_history"))


def runtime_settings_from_mapping(value: Mapping) -> RuntimeSettings:
    """Parse one mapping and reject unknown settings fail closed."""
    body = _mapping(value, "root")
    _known(body, ("version", "loop", "search", "models", "operating",
                  "history"), "root")
    return RuntimeSettings(
        version=int(body.get("version", SETTINGS_VERSION)),
        loop=_loop(body.get("loop", {})),
        search=_search(body.get("search", {})),
        models=_models(body.get("models", {})),
        operating=_operating(body.get("operating", {})),
        history=_history(body.get("history", {})))


def default_user_settings_path(environ: "Mapping[str, str] | None" = None
                               ) -> Path:
    env = os.environ if environ is None else environ
    configured = str(env.get(DEFAULT_SETTINGS_ENV, "")).strip()
    if configured:
        return Path(configured).expanduser()
    config_root = str(env.get("XDG_CONFIG_HOME", "")).strip()
    root = (Path(config_root).expanduser() if config_root
            else Path.home() / ".config")
    return root / "loop-engine" / "settings.yaml"


def _discover(path, environ: Mapping[str, str], cwd) -> "Path | None":
    if path:
        candidate = Path(path).expanduser()
        if not candidate.is_file():
            raise SettingsError(f"settings file not found: {candidate}")
        return candidate
    configured = str(environ.get(DEFAULT_SETTINGS_ENV, "")).strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_file():
            raise SettingsError(
                f"{DEFAULT_SETTINGS_ENV} points to a missing file: {candidate}")
        return candidate
    local = Path(cwd or os.getcwd()) / ".loop-engine.yaml"
    if local.is_file():
        return local
    user = default_user_settings_path(environ)
    return user if user.is_file() else None


def _environment(settings: RuntimeSettings, environ: Mapping[str, str]
                 ) -> tuple[RuntimeSettings, tuple[str, ...]]:
    changed = []
    loop, search = settings.loop, settings.search
    models, history, operating = settings.models, settings.history, settings.operating
    if environ.get("LOOP_ENGINE_DEFAULT_MODES"):
        modes = _tuple(environ["LOOP_ENGINE_DEFAULT_MODES"],
                       "LOOP_ENGINE_DEFAULT_MODES")
        loop = replace(loop, allowable_modes=modes, preferred_modes=modes)
        changed.append("LOOP_ENGINE_DEFAULT_MODES")
    if environ.get("LOOP_ENGINE_LOOP_EFFORT"):
        requested_effort = environ["LOOP_ENGINE_LOOP_EFFORT"]
        operating_effort = {
            "light": "minimal", "standard": "standard",
            "deep": "deep", "max": "exhaustive",
        }.get(requested_effort, requested_effort)
        operating = replace(operating, effort_mode=operating_effort)
        changed.append("LOOP_ENGINE_LOOP_EFFORT")
    if environ.get("LOOP_ENGINE_THINKING_POWER"):
        models = replace(
            models,
            default_thinking_power=environ["LOOP_ENGINE_THINKING_POWER"])
        changed.append("LOOP_ENGINE_THINKING_POWER")
    if environ.get("LOOP_ENGINE_MODEL_ESCALATION"):
        models = replace(models, escalation=replace(
            models.escalation,
            enabled=_boolean(environ["LOOP_ENGINE_MODEL_ESCALATION"],
                             "LOOP_ENGINE_MODEL_ESCALATION")))
        changed.append("LOOP_ENGINE_MODEL_ESCALATION")
    for env_name, field_name in (
            ("LOOP_ENGINE_SEARCH_MODE", "mode"),
            ("LOOP_ENGINE_LEXICAL_BACKEND", "lexical_backend"),
            ("LOOP_ENGINE_VECTOR_BACKEND", "vector_backend")):
        if environ.get(env_name):
            search = replace(search, **{field_name: environ[env_name]})
            changed.append(env_name)
    if environ.get("LOOP_ENGINE_RUNS_DIR"):
        history = replace(history, runs_dir=environ["LOOP_ENGINE_RUNS_DIR"])
        changed.append("LOOP_ENGINE_RUNS_DIR")
    loaded = replace(settings, loop=loop, search=search, models=models,
                     operating=operating, history=history)
    return loaded, tuple(changed)


def _load_runtime_settings(path=None, *, environ=None, cwd=None
                           ) -> SettingsLoadResult:
    """Load settings inside the public deterministic loop envelope."""
    import yaml

    env = dict(os.environ if environ is None else environ)
    source = _discover(path, env, cwd)
    if source is None:
        settings = RuntimeSettings()
    else:
        try:
            parsed = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise SettingsError(
                f"cannot read settings file {source}: {exc}") from exc
        settings = runtime_settings_from_mapping(parsed)
    settings, changed = _environment(settings, env)
    return SettingsLoadResult(
        settings, str(source.resolve()) if source else "", changed)


def load_runtime_settings(path=None, *, environ=None, cwd=None
                          ) -> SettingsLoadResult:
    """Load settings through one deterministic Practitioner loop."""
    from ..loop.encapsulate import as_practitioner_loop
    from ..loop.recursive_loop import LoopError

    try:
        wrapped = as_practitioner_loop(
            "load and validate runtime settings",
            lambda: _load_runtime_settings(path, environ=environ, cwd=cwd))
    except LoopError as exc:
        if isinstance(exc.__cause__, SettingsError):
            raise exc.__cause__
        raise
    return replace(wrapped["value"], loop_id=wrapped["loop_id"])


def default_settings_yaml() -> str:
    """Return the complete editable settings template."""
    return """# Loop Engine user settings
version: 1

loop:
  framework: nine_step
  allowable_modes: [deterministic, hybrid, non_deterministic]
  preferred_modes: [deterministic, hybrid, non_deterministic]
  delegated_modes: [deterministic, hybrid, non_deterministic]
  max_depth: 3
  exit_condition: steps_complete
  success_confidence_min: 0.5

search:
  mode: hybrid
  lexical_backend: fts5
  vector_backend: hash
  vector_model: ""
  top_k: 10
  zero_model_first: true

models:
  default_thinking_power: medium
  allow_local_counted_generation: false
  providers:
    - {id: ollama_cloud, kind: builtin, credential_env: OLLAMA_API_KEY}
    - {id: mistral, kind: builtin, credential_env: MISTRAL_API_KEY}
    - {id: openrouter, kind: builtin, credential_env: OPENROUTER_API_KEY}
  tiers:
    small:
      routes: [cloud.mistral, cloud.default]
      timeout_seconds: 120
      max_attempts: 2
    medium:
      routes: [cloud.default, cloud.mistral.large, cloud.openrouter]
      timeout_seconds: 300
      max_attempts: 3
    high:
      routes: [cloud.mistral.large, cloud.hard, cloud.openrouter.reasoning]
      timeout_seconds: 600
      max_attempts: 3
    max:
      routes: [cloud.hard, cloud.openrouter.reasoning, cloud.mistral.large]
      timeout_seconds: 900
      max_attempts: 3
    specialized:
      routes: []
      timeout_seconds: 600
      max_attempts: 2
  escalation:
    enabled: false
    order: [small, medium, high, max]
    on_errors: [output_validation_failed]
    max_tier_changes: 1

operating:
  access_mode: approved_external_read
  reasoning_and_model_mode: deterministic_first_local_first
  construction_and_execution_mode: sandbox_generate
  effort_mode: standard
  optimization_mode: quality_first
  limits: {}

history:
  runs_dir: ~/.loop-engine/runs
  save_run_history: true
"""


def _write_default_settings(path=None) -> Path:
    """Create the file inside the public deterministic loop envelope."""
    target = Path(path).expanduser() if path else default_user_settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as stream:
            stream.write(default_settings_yaml())
    except FileExistsError as exc:
        raise SettingsError(
            f"settings file already exists: {target}") from exc
    return target


def write_default_settings(path=None) -> SettingsWriteResult:
    """Create settings through one deterministic Practitioner loop."""
    from ..loop.encapsulate import as_practitioner_loop
    from ..loop.recursive_loop import LoopError

    try:
        wrapped = as_practitioner_loop(
            "create the default runtime settings file",
            lambda: _write_default_settings(path))
    except LoopError as exc:
        if isinstance(exc.__cause__, SettingsError):
            raise exc.__cause__
        raise
    return SettingsWriteResult(str(wrapped["value"]), wrapped["loop_id"])


def self_test() -> dict:
    """Offline precedence, safety, composition, and custom endpoint tests."""
    import tempfile
    import yaml

    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    parsed = runtime_settings_from_mapping(yaml.safe_load(
        default_settings_yaml()))
    config = parsed.loop_config(LoopConfigOverride(
        framework="custom", custom_steps=("load", "act", "check"),
        allowable_modes=("hybrid",), preferred_modes=("hybrid",),
        llm_thinking_power="high"))
    check("one_typed_runtime_object_builds_a_loop_config",
          config.framework == "custom" and config.power == "standard"
          and config.llm_thinking_power == "high"
          and config.allowable_modes == ("hybrid",))

    direct = parsed.models.gateway_config(ModelPolicyRequest(
        thinking_power="small"))
    enabled = replace(parsed.models, escalation=replace(
        parsed.models.escalation, enabled=True, max_tier_changes=2))
    escalated = enabled.gateway_config(ModelPolicyRequest(
        thinking_power="small", max_total_tokens=5000))
    check("thinking_tiers_create_a_bounded_route_plan",
          [item.thinking_power for item in direct.route_plan]
          == ["small", "small"]
          and {item.thinking_power for item in escalated.route_plan}
          == {"small", "medium", "high"}
          and escalated.max_total_tokens == 5000
          and escalated.max_power_escalations == 2)

    with tempfile.TemporaryDirectory(prefix="loop-engine-settings-") as root:
        path = Path(root) / "settings.yaml"
        path.write_text(
            "version: 1\n"
            "operating:\n  effort_mode: deep\n"
            "models:\n  default_thinking_power: small\n",
            encoding="utf-8")
        loaded = load_runtime_settings(path, environ={
            "LOOP_ENGINE_THINKING_POWER": "high",
            "LOOP_ENGINE_SEARCH_MODE": "lexical"}, cwd=root)
        check("yaml_then_environment_precedence_is_visible",
              loaded.settings.operating.effort_mode == "deep"
              and loaded.settings.models.default_thinking_power == "high"
              and loaded.settings.search.mode == "lexical"
              and loaded.environment_overrides == (
                  "LOOP_ENGINE_THINKING_POWER", "LOOP_ENGINE_SEARCH_MODE")
              and loaded.loop_id.startswith("loop"))

        created = write_default_settings(Path(root) / "created.yaml")
        check("settings_file_creation_is_also_a_loop",
              Path(created.path).is_file()
              and created.loop_id.startswith("loop"))

    unknown_refused = False
    try:
        runtime_settings_from_mapping({"loop": {"modess": ["hybrid"]}})
    except SettingsError:
        unknown_refused = True
    safe = parsed.safe_summary()
    check("unknown_keys_fail_closed_and_summaries_use_key_references",
          unknown_refused
          and safe["models"]["providers"][0]["credential_ref"].startswith(
              "env:"))

    local = runtime_settings_from_mapping({"models": {"providers": [{
        "id": "my_local", "kind": "custom",
        "endpoint": "http://localhost:11434/v1", "model": "qwen2.5:7b",
        "locality": "local", "credential_env": "MY_LOCAL_KEY"}],
        "allow_local_counted_generation": True,
        "tiers": {"specialized": {"routes": ["custom.my_local"]}}}})
    gateway = local.build_gateway(environ={"MY_LOCAL_KEY": "test-secret"})
    description = gateway.providers["my_local"].describe()
    check("a_custom_endpoint_is_built_without_serializing_its_key",
          gateway.registry.get("custom.my_local").locality == "local"
          and description["credential_ref"] == "env:MY_LOCAL_KEY"
          and "test-secret" not in str(description))

    locked = runtime_settings_from_mapping({
        "operating": {"reasoning_and_model_mode": "deterministic_only"}})
    locked_request = locked.model_request(ModelTask(
        "this request must have no eligible model locality"))
    check("operating_policy_clamps_model_routes_before_contact",
          locked_request.config.allowed_localities == ())

    passed = sum(1 for test in results if test["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
