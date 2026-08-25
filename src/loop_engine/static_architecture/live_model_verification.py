"""Opt-in verification of one real provider call against repository data.

Ordinary self-tests never contact a model provider.  This module is the only
verification path that may claim provider integration.  It requires explicit
authorization, one physical call, a source-backed model output maximum, a
declared total-token budget, exact grading, and a secret-safe saved result.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import distribution
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # Python 3.10 package dependency
    import tomli as tomllib

from .model_capabilities import UnknownModelOutputLimit


ALLOWED_BUILTIN_LIVE_PROVIDERS = ("ollama_cloud", "mistral")


class LiveModelVerificationError(RuntimeError):
    """A live verification precondition or evidence rule was not satisfied."""


@dataclass(frozen=True)
class RepositoryProbe:
    """Small public metadata record read from the actual repository."""

    source_path: str
    source_sha256: str
    source_bytes: int
    distribution_name: str
    import_name: str
    python_requirement: str

    def expected(self) -> dict:
        return {
            "distribution_name": self.distribution_name,
            "import_name": self.import_name,
            "python_requirement": self.python_requirement,
        }


@dataclass(frozen=True)
class LiveModelVerificationRequest:
    """Authorization, route, and budgets for exactly one real provider call."""

    provider: str
    repository_root: str
    settings_file: str = ""
    route_name: str = ""
    model: str = ""
    authorize_model_calls: bool = False
    max_physical_model_calls: int = 0
    max_total_tokens: "int | None" = None
    timeout_seconds: float = 300.0
    evidence_path: str = ""

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise LiveModelVerificationError("provider is required")
        if self.max_physical_model_calls < 0:
            raise LiveModelVerificationError(
                "max_physical_model_calls cannot be negative")
        if self.max_total_tokens is not None and self.max_total_tokens < 1:
            raise LiveModelVerificationError(
                "max_total_tokens must be positive when set")
        if self.timeout_seconds <= 0:
            raise LiveModelVerificationError("timeout_seconds must be positive")


@dataclass(frozen=True)
class LiveModelVerificationPlan:
    provider: str
    model: str
    route_name: str
    maximum_output_tokens: int
    maximum_output_source: str
    minimum_total_token_ceiling: int
    credential_present: bool
    probe: RepositoryProbe
    prompt: str
    gateway: object

    def safe_summary(self) -> dict:
        return {
            "record_type": "live_model_verification_plan/v1",
            "network_calls": 0,
            "provider_integration_proven": False,
            "provider": self.provider,
            "model": self.model,
            "route_name": self.route_name,
            "maximum_output_tokens": self.maximum_output_tokens,
            "maximum_output_source": self.maximum_output_source,
            "minimum_total_token_ceiling": self.minimum_total_token_ceiling,
            "credential_present": self.credential_present,
            "repository_input": {
                "source_path": self.probe.source_path,
                "source_sha256": self.probe.source_sha256,
                "source_bytes": self.probe.source_bytes,
            },
            "prompt_sha256": _sha256(self.prompt.encode("utf-8")),
        }


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _repository_probe(repository_root: str) -> RepositoryProbe:
    root = Path(repository_root).expanduser().resolve()
    source = root / "pyproject.toml"
    if not source.is_file():
        raise LiveModelVerificationError(
            f"actual repository input is missing: {source}")
    raw = source.read_bytes()
    try:
        data = tomllib.loads(raw.decode("utf-8"))
        project = data["project"]
        includes = data["tool"]["setuptools"]["packages"]["find"]["include"]
        import_name = str(includes[0]).rstrip("*")
        distribution = str(project["name"])
        python_requirement = str(project["requires-python"])
    except (KeyError, IndexError, TypeError, UnicodeDecodeError,
            tomllib.TOMLDecodeError) as exc:
        raise LiveModelVerificationError(
            "pyproject.toml does not contain the expected package metadata") from exc
    if not all((distribution, import_name, python_requirement)):
        raise LiveModelVerificationError(
            "repository package metadata contains an empty required value")
    return RepositoryProbe(
        source_path="pyproject.toml",
        source_sha256=_sha256(raw),
        source_bytes=len(raw),
        distribution_name=distribution,
        import_name=import_name,
        python_requirement=python_requirement)


def _installed_distribution_probe() -> RepositoryProbe:
    """Read the installed wheel metadata without assuming a source checkout."""
    installed = distribution("loop-engine")
    name = str(installed.metadata.get("Name") or "")
    python_requirement = str(
        installed.metadata.get("Requires-Python") or "")
    top_level = (installed.read_text("top_level.txt") or "").splitlines()
    import_name = next((line.strip() for line in top_level
                        if line.strip()), "")
    body = "\n".join((name, import_name, python_requirement)).encode("utf-8")
    if not all((name, import_name, python_requirement)):
        raise LiveModelVerificationError(
            "installed distribution metadata is incomplete")
    return RepositoryProbe(
        source_path="installed:loop-engine/METADATA+top_level.txt",
        source_sha256=_sha256(body),
        source_bytes=len(body),
        distribution_name=name,
        import_name=import_name,
        python_requirement=python_requirement)


def _prompt(probe: RepositoryProbe) -> str:
    source = json.dumps(probe.expected(), sort_keys=True, separators=(",", ":"))
    return (
        "Read the repository metadata record below. Return only one JSON object "
        "with exactly these string fields: distribution_name, import_name, "
        "python_requirement. Copy the values exactly.\n"
        f"Repository metadata: {source}")


def _parse_json_object(text: str):
    start, end = str(text).find("{"), str(text).rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(str(text)[start:end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _provider_settings(loaded, provider: str):
    for item in loaded.settings.models.providers:
        if item.provider_id == provider and item.enabled:
            return item
    raise LiveModelVerificationError(
        f"provider {provider!r} is not enabled in Loop Engine settings")


def _credential_present(configured, gateway) -> bool:
    if configured.kind == "builtin":
        adapter = gateway.providers[configured.provider_id].adapter
        loader = getattr(adapter, "load_api_key", None)
        return bool(loader and loader())
    if not configured.credential_env:
        return True
    return bool(os.environ.get(configured.credential_env, "").strip())


def plan_live_model_verification(
        request: LiveModelVerificationRequest) -> LiveModelVerificationPlan:
    """Resolve a real route and its maximum without contacting the provider."""
    from .settings_loader import load_runtime_settings

    loaded = load_runtime_settings(request.settings_file or None,
                                   cwd=request.repository_root)
    configured = _provider_settings(loaded, request.provider)
    if (configured.kind == "builtin"
            and request.provider not in ALLOWED_BUILTIN_LIVE_PROVIDERS):
        raise LiveModelVerificationError(
            "live integration evidence accepts Ollama Cloud, Mistral, or an "
            "explicitly configured custom endpoint")
    gateway = loaded.settings.build_gateway()
    candidates = [
        route for route in gateway.registry.all()
        if route.provider == request.provider
        and "counted_generation" in route.purposes
        and (not request.route_name or route.name == request.route_name)
        and (not request.model or route.model == request.model)
    ]
    if not candidates:
        raise LiveModelVerificationError(
            "no counted-generation route matches the requested provider, "
            "route, and model")
    route = candidates[0]
    provider_spec = gateway.providers[request.provider]
    try:
        capability = provider_spec.output_capability_for(route.model)
    except UnknownModelOutputLimit as exc:
        raise LiveModelVerificationError(str(exc)) from exc
    probe = _repository_probe(request.repository_root)
    prompt = _prompt(probe)
    # The provider may add protocol tokens that are not visible locally.  A
    # total budget smaller than the declared output maximum plus the complete
    # UTF-8 input cannot be a physical upper bound, so refuse it before use.
    minimum_total = (capability.maximum_output_tokens
                     + len(prompt.encode("utf-8")))
    return LiveModelVerificationPlan(
        provider=request.provider,
        model=route.model,
        route_name=route.name,
        maximum_output_tokens=capability.maximum_output_tokens,
        maximum_output_source=capability.source,
        minimum_total_token_ceiling=minimum_total,
        credential_present=_credential_present(configured, gateway),
        probe=probe, prompt=prompt, gateway=gateway)


def _default_evidence_path(provider: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (Path.home() / ".loop-engine" / "evidence"
            / f"live-model-{provider}-{stamp}.json")


def _write_new_evidence(path: Path, value: dict) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists():
        raise LiveModelVerificationError(
            f"evidence path already exists and will not be overwritten: {path}")
    body = json.dumps(value, indent=1, sort_keys=True) + "\n"
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def run_live_model_verification(request: LiveModelVerificationRequest) -> dict:
    """Perform one authorized physical call and save secret-safe evidence."""
    if not request.authorize_model_calls:
        raise LiveModelVerificationError(
            "live verification requires authorize_model_calls=True")
    if request.max_physical_model_calls != 1:
        raise LiveModelVerificationError(
            "live verification requires max_physical_model_calls=1")
    if request.max_total_tokens is None:
        raise LiveModelVerificationError(
            "live verification requires an explicit max_total_tokens budget")
    plan = plan_live_model_verification(request)
    if not plan.credential_present:
        raise LiveModelVerificationError(
            "the selected provider credential is not present; no call made")
    if request.max_total_tokens < plan.minimum_total_token_ceiling:
        raise LiveModelVerificationError(
            "max_total_tokens is too small to permit the model's declared "
            "maximum output without imposing an arbitrary lower cap; required "
            f"minimum is {plan.minimum_total_token_ceiling}")

    from .model_gateway import ModelGatewayConfig, ModelGatewayRequest

    started = time.monotonic()
    result = plan.gateway.invoke(
        ModelGatewayRequest(
            prompt=plan.prompt,
            config=ModelGatewayConfig(
                route_names=(plan.route_name,),
                allow_failover=False,
                max_route_attempts=1,
                timeout_seconds=request.timeout_seconds,
                max_output_tokens=None,
                max_total_tokens=request.max_total_tokens),
            temperature=0.0,
            output_contract=(
                "JSON object with exact distribution_name, import_name, and "
                "python_requirement strings"),
            trace_id=f"live-model-verification.{time.time_ns()}"),
        validate=lambda text: _parse_json_object(text) == plan.probe.expected())
    elapsed = round(time.monotonic() - started, 6)
    physical_calls = sum(1 for attempt in result.attempts if attempt.loop_id)
    output_digest = (_sha256(result.text.encode("utf-8"))
                     if result.text else "")
    accounting_complete = result.accounting_complete
    accepted = bool(
        result.ok and result.provider_responded and physical_calls == 1
        and accounting_complete
        and result.total_tokens is not None
        and result.total_tokens <= request.max_total_tokens)
    evidence = {
        "record_type": "live_model_verification/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "accepted" if accepted else "failed",
        "provider_integration_proven": accepted,
        "provider": result.provider or plan.provider,
        "model": result.model or plan.model,
        "route_name": result.route or plan.route_name,
        "authorized": True,
        "physical_model_call_ceiling": 1,
        "physical_model_calls": physical_calls,
        "timeout_seconds": request.timeout_seconds,
        "elapsed_seconds": elapsed,
        "maximum_output_tokens": plan.maximum_output_tokens,
        "maximum_output_source": plan.maximum_output_source,
        "total_token_ceiling": request.max_total_tokens,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "total_tokens": result.total_tokens,
        "usage_accounting_complete": accounting_complete,
        "provider_responded": result.provider_responded,
        "output_accepted_by_exact_grader": result.ok,
        "repository_input": {
            "source_path": plan.probe.source_path,
            "source_sha256": plan.probe.source_sha256,
            "source_bytes": plan.probe.source_bytes,
        },
        "prompt_sha256": _sha256(plan.prompt.encode("utf-8")),
        "output_sha256": output_digest,
        "failure_code": "" if accepted else result.error_code,
        "failure_detail_sha256": (
            "" if accepted else _sha256(result.error.encode("utf-8"))),
        "secret_policy": "raw prompt, raw output, credentials, and provider "
                         "error text are not saved",
    }
    path = (Path(request.evidence_path) if request.evidence_path
            else _default_evidence_path(plan.provider))
    _write_new_evidence(path, evidence)
    return {**evidence, "evidence_path": str(path.expanduser().resolve())}


def self_test() -> dict:
    """Offline policy checks over installed package metadata. No model call."""
    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    probe = _installed_distribution_probe()
    check("the_probe_reads_installed_distribution_metadata",
          probe.distribution_name == "loop-engine"
          and probe.import_name == "loop_engine"
          and probe.source_bytes > 0)

    request = LiveModelVerificationRequest(
        provider="ollama_cloud", repository_root="not-read-before-auth")
    refused = False
    try:
        run_live_model_verification(request)
    except LiveModelVerificationError as exc:
        refused = "authorize_model_calls" in str(exc)
    check("an_unauthorized_live_check_refuses_before_provider_use", refused)

    safe = _prompt(probe)
    check("the_prompt_contains_only_public_repository_metadata",
          probe.distribution_name in safe
          and "API_KEY" not in safe and "secret" not in safe.lower())

    passed = sum(1 for test in results if test["passed"])
    return {"record_type": "live_model_verification_contract_test/v1",
            "scope": "offline_contract_only",
            "provider_integration_proven": False,
            "tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
