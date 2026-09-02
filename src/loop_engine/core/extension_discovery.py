"""Added-file extension discovery over existing Loop Engine authorities.

One extension root may contain providers, capability candidates, skills,
plugin bundles, and plugin-provenance intelligence.  This module discovers and
resolves those files; it does not execute plugin code, admit skills, promote
intelligence, grant effects, or create another registry or runtime.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import string
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Mapping

import yaml

from .plugin_bundles import (
    PLUGIN_MANIFEST_NAME, PluginDiscoveryRequest, PluginBundleManifest,
    discover_plugin_bundles)
from .runtime_settings import (
    MODEL_THINKING_POWER_LEVELS, ProviderSettings,
    RuntimeSettings)
from .skill_registry import SkillManifest, SkillRegistry


EXTENSION_ROOTS_ENV = "LOOP_ENGINE_EXTENSION_ROOTS"
EXTENSION_FOLDER = Path(".loop-engine") / "extensions"
PROVIDER_SCHEMA = "provider_route_bundle/v2"
CAPABILITY_SCHEMA = "capability_candidate/v1"
PROVIDER_PROTOCOLS = (
    "openai_chat", "openai_responses", "anthropic_messages",
    "gemini_generate_content", "ollama_chat", "cohere_chat",
    "bedrock_converse", "bedrock_invoke", "async_generate_poll",
    "browser_user_pays")
PROVIDER_AUTH_KINDS = (
    "bearer_env", "header_env", "none", "aws_sigv4", "google_adc",
    "azure_entra", "browser_session", "plugin")
PROVIDER_ACCESS_CLASSES = (
    "zero_price", "recurring_quota", "rolling_credit", "trial_credit",
    "community", "local", "user_pays", "paid", "unknown")
PROVIDER_QUOTA_SCOPES = (
    "none", "account", "key", "project", "model", "ip", "region",
    "unknown")
PROVIDER_CAPABILITIES = (
    "text", "structured_output", "tools", "reasoning", "streaming",
    "vision", "audio", "embeddings", "reranking")
PROVIDER_SOURCE_KINDS = (
    "protocol", "model", "pricing", "quota", "data_policy",
    "model_metadata")
_ID = re.compile(r"^[a-z][a-z0-9_]{1,79}$")
_DOTTED = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\."
                     r"(0|[1-9][0-9]*)$")


class ExtensionDiscoveryError(ValueError):
    """An explicit root or added-file contract failed closed."""


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False,
                      default=lambda item: (
                          item.isoformat() if isinstance(item, date)
                          else _raise_non_json(item)))


def _raise_non_json(value: object):
    raise TypeError(
        f"extension value {type(value).__name__} is not JSON-compatible")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _mapping(value: object, label: str) -> dict:
    if not isinstance(value, Mapping):
        raise ExtensionDiscoveryError(f"{label} must be a mapping")
    return dict(value)


def _keys(body: dict, expected: set[str], label: str) -> None:
    if set(body) != expected:
        missing = sorted(expected - set(body))
        extra = sorted(set(body) - expected)
        raise ExtensionDiscoveryError(
            f"{label} fields differ; missing={missing}, extra={extra}")


def _strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ExtensionDiscoveryError(f"{label} must be a list")
    result = tuple(str(item) for item in value)
    if (any(not item.strip() for item in result)
            or len(result) != len(set(result))):
        raise ExtensionDiscoveryError(
            f"{label} needs unique non-empty strings")
    return result


def _template_names(template: str) -> set[str]:
    return {
        match[1] or match[2]
        for match in string.Template.pattern.findall(template)
        if (match[1] or match[2])}


def _validate_nonsecret_headers(headers: tuple[tuple[str, str], ...]) -> None:
    forbidden = {"authorization", "proxy-authorization", "cookie",
                 "set-cookie", "x-api-key", "api-key", "x-goog-api-key"}
    if any(not isinstance(item, tuple) or len(item) != 2
           or not all(isinstance(value, str) for value in item)
           for item in headers):
        raise ExtensionDiscoveryError(
            "provider headers must contain text name/value pairs")
    if (len(headers) != len({item[0].casefold() for item in headers})
            or any(not item[0].strip() or not item[1].strip()
                   or item[0].casefold() in forbidden
                   or "\n" in item[0] or "\r" in item[0]
                   or "\n" in item[1] or "\r" in item[1]
                   for item in headers)):
        raise ExtensionDiscoveryError(
            "provider headers must be unique non-secret HTTP headers")


@dataclass(frozen=True)
class ProviderAuthDefinition:
    """How a credential is supplied without containing the credential."""

    kind: str
    credential_env: str = ""
    header: str = ""
    plugin_ref: str = ""

    def __post_init__(self) -> None:
        if self.kind not in PROVIDER_AUTH_KINDS:
            raise ExtensionDiscoveryError("provider auth kind is invalid")
        if (self.credential_env and not re.fullmatch(
                r"[A-Z][A-Z0-9_]*", self.credential_env)):
            raise ExtensionDiscoveryError(
                "provider credential_env is invalid")
        if self.kind in {"bearer_env", "header_env"}:
            if not self.credential_env:
                raise ExtensionDiscoveryError(
                    "environment authentication needs credential_env")
        elif self.credential_env:
            raise ExtensionDiscoveryError(
                "only environment authentication may name credential_env")
        if self.kind == "header_env":
            if (not self.header or not re.fullmatch(
                    r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", self.header)
                    or self.header.casefold() in {
                        "authorization", "proxy-authorization", "cookie",
                        "set-cookie"}):
                raise ExtensionDiscoveryError(
                    "header_env authentication needs a valid header")
        elif self.header:
            raise ExtensionDiscoveryError(
                "provider auth header is only valid for header_env")
        if self.kind == "plugin":
            if not _DOTTED.fullmatch(self.plugin_ref):
                raise ExtensionDiscoveryError(
                    "plugin authentication needs a dotted plugin_ref")
        elif self.plugin_ref:
            raise ExtensionDiscoveryError(
                "plugin_ref is only valid for plugin authentication")

    @property
    def executable_by_generic_gateway(self) -> bool:
        return self.kind in {"bearer_env", "header_env", "none"}

    def to_dict(self) -> dict:
        credential_ref = (
            f"env:{self.credential_env}" if self.credential_env
            else "not_required" if self.kind == "none"
            else f"plugin:{self.plugin_ref}" if self.kind == "plugin"
            else f"managed:{self.kind}")
        return {
            "kind": self.kind,
            "credential_ref": credential_ref,
            "header": self.header,
            "plugin_ref": self.plugin_ref,
        }


@dataclass(frozen=True)
class ExtensionRoot:
    """One resolved directory and why it was considered."""

    path: str
    source: str

    def __post_init__(self) -> None:
        if self.source not in {"explicit", "environment", "project", "user"}:
            raise ExtensionDiscoveryError("extension root source is invalid")
        root = Path(self.path)
        if not root.is_absolute() or not root.is_dir() or root.is_symlink():
            raise ExtensionDiscoveryError(
                f"extension root is not a regular directory: {self.path}")

    def to_dict(self) -> dict:
        return {"path": self.path, "source": self.source}


@dataclass(frozen=True)
class ProviderEndpointDefinition:
    """Provider wire and model facts independent from installed executors."""

    provider_id: str
    enabled: bool
    auth: ProviderAuthDefinition
    endpoint: str
    model: str
    protocol: str
    locality: str
    counts_as_evidence: bool
    maximum_output_tokens: int
    maximum_output_source: str
    purposes: tuple[str, ...]
    headers: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if (not _ID.fullmatch(self.provider_id)
                or not isinstance(self.auth, ProviderAuthDefinition)
                or self.protocol not in PROVIDER_PROTOCOLS
                or self.locality not in {"cloud", "organization", "local"}
                or not self.endpoint.strip() or not self.model.strip()
                or self.maximum_output_tokens < 1
                or not self.maximum_output_source.strip()):
            raise ExtensionDiscoveryError(
                "provider endpoint definition is invalid")
        _validate_nonsecret_headers(self.headers)
        secret_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH",
                          "CREDENTIAL")
        unsafe = sorted(name for name in _template_names(self.endpoint)
                        if any(marker in name.upper()
                               for marker in secret_markers))
        if unsafe:
            raise ExtensionDiscoveryError(
                "provider endpoint templates cannot interpolate credentials: "
                + ", ".join(unsafe))

    @property
    def route_name(self) -> str:
        return f"custom.{self.provider_id}"

    @property
    def executable_by_generic_gateway(self) -> bool:
        return (self.protocol in {"openai_chat", "ollama_chat"}
                and self.auth.executable_by_generic_gateway)

    def to_provider_settings(self, endpoint: str) -> "ProviderSettings | None":
        if not self.executable_by_generic_gateway:
            return None
        auth_scheme = {
            "bearer_env": "bearer", "header_env": "header",
            "none": "none"}[self.auth.kind]
        return ProviderSettings(
            provider_id=self.provider_id, kind="custom",
            enabled=self.enabled, credential_env=self.auth.credential_env,
            endpoint=endpoint, model=self.model,
            wire=("openai" if self.protocol == "openai_chat" else "ollama"),
            locality=self.locality,
            counts_as_evidence=self.counts_as_evidence,
            maximum_output_tokens=self.maximum_output_tokens,
            maximum_output_source=self.maximum_output_source,
            purposes=self.purposes, headers=self.headers,
            auth_scheme=auth_scheme, auth_header=self.auth.header)

    def safe_summary(self) -> dict:
        return {
            "provider_id": self.provider_id, "enabled": self.enabled,
            "auth": self.auth.to_dict(),
            "endpoint": self.endpoint, "model": self.model,
            "protocol": self.protocol, "locality": self.locality,
            "counts_as_evidence": self.counts_as_evidence,
            "maximum_output_tokens": self.maximum_output_tokens,
            "maximum_output_source": self.maximum_output_source,
            "purposes": list(self.purposes),
            "header_names": [item[0] for item in self.headers],
            "executor_installed": self.executable_by_generic_gateway,
        }


@dataclass(frozen=True)
class ProviderQuota:
    """Declared provider allowance dimensions; missing values stay unknown."""

    scope: str
    requests_per_minute: "int | None" = None
    requests_per_day: "int | None" = None
    tokens_per_minute: "int | None" = None
    tokens_per_day: "int | None" = None
    concurrency: "int | None" = None
    credit_amount: "float | None" = None
    reset: str = "unknown"

    def __post_init__(self) -> None:
        if self.scope not in PROVIDER_QUOTA_SCOPES or not self.reset.strip():
            raise ExtensionDiscoveryError("provider quota is invalid")
        for value in (self.requests_per_minute, self.requests_per_day,
                      self.tokens_per_minute, self.tokens_per_day,
                      self.concurrency):
            if value is not None and value < 1:
                raise ExtensionDiscoveryError(
                    "provider quota limits must be positive")
        if self.credit_amount is not None and self.credit_amount < 0:
            raise ExtensionDiscoveryError(
                "provider credit amount cannot be negative")

    def to_dict(self) -> dict:
        return {
            "scope": self.scope,
            "requests_per_minute": self.requests_per_minute,
            "requests_per_day": self.requests_per_day,
            "tokens_per_minute": self.tokens_per_minute,
            "tokens_per_day": self.tokens_per_day,
            "concurrency": self.concurrency,
            "credit_amount": self.credit_amount, "reset": self.reset,
        }


@dataclass(frozen=True)
class ProviderDataPolicy:
    """Declared privacy facts; unknown is preserved rather than guessed."""

    confidential_allowed: "bool | None"
    training_use: str
    retention: str
    regions: tuple[str, ...]

    def __post_init__(self) -> None:
        if (self.confidential_allowed not in {True, False, None}
                or self.training_use not in {
                    "yes", "no", "opt_out", "unknown"}
                or not self.retention.strip()):
            raise ExtensionDiscoveryError("provider data policy is invalid")

    def to_dict(self) -> dict:
        return {
            "confidential_allowed": self.confidential_allowed,
            "training_use": self.training_use,
            "retention": self.retention, "regions": list(self.regions),
        }


@dataclass(frozen=True)
class ProviderHealthPolicy:
    """How often a later authorized operation may refresh and probe."""

    catalog_refresh_seconds: int
    probe_timeout_seconds: float

    def __post_init__(self) -> None:
        if self.catalog_refresh_seconds < 1 or self.probe_timeout_seconds <= 0:
            raise ExtensionDiscoveryError(
                "provider health policy limits must be positive")

    def to_dict(self) -> dict:
        return {"catalog_refresh_seconds": self.catalog_refresh_seconds,
                "probe_timeout_seconds": self.probe_timeout_seconds}


@dataclass(frozen=True)
class ProviderSourceRef:
    """One exact first-party or declared metadata source for route facts."""

    kind: str
    url: str
    observed_at: str

    def __post_init__(self) -> None:
        if (self.kind not in PROVIDER_SOURCE_KINDS
                or not self.url.startswith(("https://", "http://"))
                or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
                                    self.observed_at)):
            raise ExtensionDiscoveryError(
                "provider source needs a known kind, HTTP URL, and date")

    def to_dict(self) -> dict:
        return {"kind": self.kind, "url": self.url,
                "observed_at": self.observed_at}


@dataclass(frozen=True)
class ProviderRouteBundle:
    """One exact provider/model route loaded from an added YAML file."""

    bundle_id: str
    version: str
    description: str
    provider: ProviderEndpointDefinition
    tiers: tuple[str, ...]
    access_class: str
    input_cost_per_million: "float | None"
    output_cost_per_million: "float | None"
    quota: ProviderQuota
    capabilities: tuple[str, ...]
    data_policy: ProviderDataPolicy
    health: ProviderHealthPolicy
    sources: tuple[ProviderSourceRef, ...]
    source_path: str
    source_root: str
    content_digest: str

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.bundle_id) or not _SEMVER.fullmatch(
                self.version):
            raise ExtensionDiscoveryError(
                "provider bundle identity or version is invalid")
        if not self.description.strip() or not isinstance(
                self.provider, ProviderEndpointDefinition):
            raise ExtensionDiscoveryError(
                "provider bundle needs description and ProviderSettings")
        if self.provider.provider_id != self.bundle_id:
            raise ExtensionDiscoveryError(
                "provider bundle id must equal its provider id")
        if (not self.tiers or any(
                item not in MODEL_THINKING_POWER_LEVELS for item in self.tiers)):
            raise ExtensionDiscoveryError(
                "provider bundle tiers are invalid")
        for value in (self.input_cost_per_million,
                      self.output_cost_per_million):
            if value is not None and value < 0:
                raise ExtensionDiscoveryError(
                    "provider bundle prices cannot be negative")
        if self.access_class not in PROVIDER_ACCESS_CLASSES:
            raise ExtensionDiscoveryError(
                "provider route access_class is invalid")
        if self.access_class == "zero_price" and (
                self.input_cost_per_million != 0
                or self.output_cost_per_million != 0):
            raise ExtensionDiscoveryError(
                "a free-eligible route needs explicit zero input/output cost")
        if (not isinstance(self.quota, ProviderQuota)
                or not isinstance(self.data_policy, ProviderDataPolicy)
                or not isinstance(self.health, ProviderHealthPolicy)
                or not self.sources
                or any(not isinstance(item, ProviderSourceRef)
                       for item in self.sources)
                or len({(item.kind, item.url) for item in self.sources})
                    != len(self.sources)
                or any(item not in PROVIDER_CAPABILITIES
                       for item in self.capabilities)
                or len(self.capabilities) != len(set(self.capabilities))):
            raise ExtensionDiscoveryError(
                "provider quota, capabilities, data policy, or health is invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", self.content_digest):
            raise ExtensionDiscoveryError(
                "provider bundle digest is invalid")

    def to_dict(self) -> dict:
        return {
            "record_type": PROVIDER_SCHEMA,
            "bundle_id": self.bundle_id, "version": self.version,
            "description": self.description,
            "provider": self.provider.safe_summary(),
            "tiers": list(self.tiers), "access_class": self.access_class,
            "input_cost_per_million": self.input_cost_per_million,
            "output_cost_per_million": self.output_cost_per_million,
            "quota": self.quota.to_dict(),
            "capabilities": list(self.capabilities),
            "data_policy": self.data_policy.to_dict(),
            "health": self.health.to_dict(),
            "sources": [item.to_dict() for item in self.sources],
            "source_path": self.source_path, "source_root": self.source_root,
            "content_digest": self.content_digest,
        }


@dataclass(frozen=True)
class CapabilityCandidate:
    """Passive capability description; never an executable registration."""

    capability_ref: str
    version: str
    description: str
    input_roles: tuple[str, ...]
    output_roles: tuple[str, ...]
    permissions: tuple[str, ...]
    effects: tuple[str, ...]
    implementation_kind: str
    implementation_ref: str
    tags: tuple[str, ...]
    source_path: str
    source_root: str
    content_digest: str
    lifecycle: str = "candidate"

    def __post_init__(self) -> None:
        if not _DOTTED.fullmatch(self.capability_ref) or not _SEMVER.fullmatch(
                self.version):
            raise ExtensionDiscoveryError(
                "capability identity or version is invalid")
        if (not self.description.strip()
                or self.implementation_kind not in {
                    "skill", "mcp", "external_service", "sandbox_command"}
                or not self.implementation_ref.strip()):
            raise ExtensionDiscoveryError(
                "capability implementation reference is invalid")
        if self.lifecycle != "candidate":
            raise ExtensionDiscoveryError(
                "added capability files always enter as candidates")
        if not re.fullmatch(r"[0-9a-f]{64}", self.content_digest):
            raise ExtensionDiscoveryError("capability digest is invalid")

    def to_dict(self) -> dict:
        return {
            "record_type": CAPABILITY_SCHEMA,
            "capability_ref": self.capability_ref, "version": self.version,
            "description": self.description,
            "input_roles": list(self.input_roles),
            "output_roles": list(self.output_roles),
            "permissions": list(self.permissions),
            "effects": list(self.effects),
            "implementation": {"kind": self.implementation_kind,
                               "ref": self.implementation_ref},
            "tags": list(self.tags), "lifecycle": self.lifecycle,
            "source_path": self.source_path, "source_root": self.source_root,
            "content_digest": self.content_digest,
        }


@dataclass(frozen=True)
class ExtensionDiscoveryRequest:
    """Explicit roots plus optional conventional project/user discovery."""

    explicit_roots: tuple[str, ...] = ()
    project_root: str = ""
    include_defaults: bool = True


@dataclass(frozen=True)
class ExtensionSnapshot:
    """One immutable, secret-free view over every recognized added file."""

    roots: tuple[ExtensionRoot, ...]
    providers: tuple[ProviderRouteBundle, ...]
    capabilities: tuple[CapabilityCandidate, ...]
    skills: tuple[SkillManifest, ...]
    plugins: tuple[PluginBundleManifest, ...]
    intelligence_entries: tuple[dict, ...]
    reasons: tuple[str, ...]
    loop_id: str = ""

    @property
    def content_digest(self) -> str:
        return _digest({
            "root_sources": [item.source for item in self.roots],
            "providers": [{"bundle_id": item.bundle_id,
                           "version": item.version,
                           "content_digest": item.content_digest}
                          for item in self.providers],
            "capabilities": [{"capability_ref": item.capability_ref,
                              "version": item.version,
                              "content_digest": item.content_digest}
                             for item in self.capabilities],
            "skills": [{"skill_id": item.skill_id,
                        "version": item.version,
                        "manifest_digest": item.manifest_digest}
                       for item in self.skills],
            "plugins": [{"plugin_id": item.plugin_id,
                         "version": item.version,
                         "content_digest": item.content_digest}
                        for item in self.plugins],
            "intelligence": list(self.intelligence_entries),
        })

    def to_dict(self) -> dict:
        return {
            "record_type": "extension_snapshot/v1",
            "content_digest": self.content_digest, "loop_id": self.loop_id,
            "roots": [item.to_dict() for item in self.roots],
            "providers": [item.to_dict() for item in self.providers],
            "capabilities": [item.to_dict() for item in self.capabilities],
            "skills": [{"skill_id": item.skill_id,
                        "version": item.version,
                        "description": item.description,
                        "lifecycle": item.lifecycle,
                        "manifest_digest": item.manifest_digest}
                       for item in self.skills],
            "plugins": [{**item.body(), "source": item.source,
                         "content_digest": item.content_digest}
                        for item in self.plugins],
            "intelligence_entries": list(self.intelligence_entries),
            "reasons": list(self.reasons),
        }

    def ascii_tree(self) -> str:
        lines = [f"Extensions [{self.content_digest[:12]}]"]
        branches = (
            ("providers", self.providers), ("capabilities", self.capabilities),
            ("skills", self.skills), ("plugins", self.plugins),
            ("intelligence", self.intelligence_entries))
        nonempty = [(name, items) for name, items in branches if items]
        if not nonempty:
            return lines[0] + "\n└─ empty"
        for index, (name, items) in enumerate(nonempty):
            last = index == len(nonempty) - 1
            lines.append(("└─" if last else "├─") + f" {name} ({len(items)})")
        return "\n".join(lines)


@dataclass(frozen=True)
class ExtensionApplication:
    """Resolved provider settings and why routes did or did not auto-activate."""

    settings: RuntimeSettings
    snapshot: ExtensionSnapshot
    activated_routes: tuple[str, ...]
    inactive_routes: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict:
        return {
            "record_type": "extension_application/v1",
            "snapshot_digest": self.snapshot.content_digest,
            "activated_routes": list(self.activated_routes),
            "inactive_routes": [list(item) for item in self.inactive_routes],
        }


@dataclass(frozen=True)
class ExtensionApplicationRequest:
    """Settings, exact snapshot, and nonzero-cost route policy."""

    settings: RuntimeSettings
    snapshot: ExtensionSnapshot
    allow_paid: bool = False

    def __post_init__(self) -> None:
        if (not isinstance(self.settings, RuntimeSettings)
                or not isinstance(self.snapshot, ExtensionSnapshot)):
            raise ExtensionDiscoveryError(
                "extension application request is invalid")


def _resolved_roots(request: ExtensionDiscoveryRequest,
                    environ: Mapping[str, str]) -> tuple[ExtensionRoot, ...]:
    candidates: list[tuple[Path, str, bool]] = []
    candidates.extend((Path(item).expanduser(), "explicit", True)
                      for item in request.explicit_roots)
    raw = str(environ.get(EXTENSION_ROOTS_ENV, ""))
    candidates.extend((Path(item).expanduser(), "environment", True)
                      for item in raw.split(os.pathsep) if item.strip())
    if request.include_defaults:
        project = Path(request.project_root or os.getcwd()).resolve()
        candidates.append((project / EXTENSION_FOLDER, "project", False))
        config = str(environ.get("XDG_CONFIG_HOME", "")).strip()
        config_root = (Path(config).expanduser() if config
                       else Path.home() / ".config")
        candidates.append((config_root / "loop-engine" / "extensions",
                           "user", False))
    roots = []
    seen = set()
    for candidate, source, required in candidates:
        expanded = candidate.expanduser()
        if expanded.exists() and expanded.is_symlink():
            raise ExtensionDiscoveryError(
                f"extension root cannot be a symlink: {expanded}")
        path = expanded.resolve()
        if not path.exists():
            if required:
                raise ExtensionDiscoveryError(
                    f"explicit extension root is missing: {path}")
            continue
        if not path.is_dir() or path.is_symlink():
            raise ExtensionDiscoveryError(
                f"extension root is not a regular directory: {path}")
        if str(path) in seen:
            continue
        seen.add(str(path))
        roots.append(ExtensionRoot(str(path), source))
    return tuple(roots)


def _yaml(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ExtensionDiscoveryError(f"extension file is unavailable: {path}")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ExtensionDiscoveryError(
            f"extension file is invalid: {path}") from exc
    return _mapping(value, str(path))


def _provider(path: Path, root: ExtensionRoot) -> ProviderRouteBundle:
    value = _yaml(path)
    expected = {"schema_version", "bundle_id", "version", "description",
                "provider", "routing", "pricing", "quota", "capabilities",
                "data_policy", "health", "sources"}
    _keys(value, expected, "provider bundle")
    if value["schema_version"] != PROVIDER_SCHEMA:
        raise ExtensionDiscoveryError("provider schema version is unsupported")
    provider = _mapping(value["provider"], "provider")
    _keys(provider, {"enabled", "auth", "endpoint",
                     "model", "protocol", "locality", "counts_as_evidence",
                     "maximum_output_tokens", "maximum_output_source",
                     "purposes", "headers"}, "provider")
    headers = _mapping(provider["headers"], "provider.headers")
    auth = _mapping(provider["auth"], "provider.auth")
    _keys(auth, {"kind", "credential_env", "header", "plugin_ref"},
          "provider.auth")
    auth_record = ProviderAuthDefinition(
        str(auth["kind"]), str(auth["credential_env"]),
        str(auth["header"]), str(auth["plugin_ref"]))
    endpoint = ProviderEndpointDefinition(
        provider_id=str(value["bundle_id"]),
        enabled=bool(provider["enabled"]),
        auth=auth_record,
        endpoint=str(provider["endpoint"]), model=str(provider["model"]),
        protocol=str(provider["protocol"]), locality=str(provider["locality"]),
        counts_as_evidence=bool(provider["counts_as_evidence"]),
        maximum_output_tokens=int(provider["maximum_output_tokens"]),
        maximum_output_source=str(provider["maximum_output_source"]),
        purposes=_strings(provider["purposes"], "provider.purposes"),
        headers=tuple(sorted((str(key), str(item))
                             for key, item in headers.items())))
    routing = _mapping(value["routing"], "routing")
    _keys(routing, {"tiers", "access_class"}, "routing")
    pricing = _mapping(value["pricing"], "pricing")
    _keys(pricing, {"input_cost_per_million", "output_cost_per_million"},
          "pricing")
    quota = _mapping(value["quota"], "quota")
    _keys(quota, {"scope", "requests_per_minute", "requests_per_day",
                  "tokens_per_minute", "tokens_per_day", "concurrency",
                  "credit_amount", "reset"}, "quota")
    quota_record = ProviderQuota(
        str(quota["scope"]),
        *(None if quota[name] is None else int(quota[name]) for name in (
            "requests_per_minute", "requests_per_day", "tokens_per_minute",
            "tokens_per_day", "concurrency")),
        credit_amount=(None if quota["credit_amount"] is None
                       else float(quota["credit_amount"])),
        reset=str(quota["reset"]))
    policy = _mapping(value["data_policy"], "data_policy")
    _keys(policy, {"confidential_allowed", "training_use", "retention",
                   "regions"}, "data_policy")
    data_policy = ProviderDataPolicy(
        policy["confidential_allowed"], str(policy["training_use"]),
        str(policy["retention"]),
        _strings(policy["regions"], "data_policy.regions"))
    health = _mapping(value["health"], "health")
    _keys(health, {"catalog_refresh_seconds", "probe_timeout_seconds"},
          "health")
    health_policy = ProviderHealthPolicy(
        int(health["catalog_refresh_seconds"]),
        float(health["probe_timeout_seconds"]))
    raw_sources = value["sources"]
    if not isinstance(raw_sources, list):
        raise ExtensionDiscoveryError("provider sources must be a list")
    sources = []
    for raw_source in raw_sources:
        source = _mapping(raw_source, "provider source")
        _keys(source, {"kind", "url", "observed_at"}, "provider source")
        sources.append(ProviderSourceRef(
            str(source["kind"]), str(source["url"]),
            str(source["observed_at"])))
    relative = path.relative_to(Path(root.path)).as_posix()
    body = dict(value)
    return ProviderRouteBundle(
        str(value["bundle_id"]), str(value["version"]),
        str(value["description"]), endpoint,
        _strings(routing["tiers"], "routing.tiers"),
        str(routing["access_class"]),
        (None if pricing["input_cost_per_million"] is None
         else float(pricing["input_cost_per_million"])),
        (None if pricing["output_cost_per_million"] is None
         else float(pricing["output_cost_per_million"])),
        quota_record,
        _strings(value["capabilities"], "capabilities"),
        data_policy, health_policy, tuple(sources),
        relative, root.path, _digest(body))


def _capability(path: Path, root: ExtensionRoot) -> CapabilityCandidate:
    value = _yaml(path)
    expected = {"schema_version", "capability_ref", "version", "description",
                "input_roles", "output_roles", "permissions", "effects",
                "implementation", "tags", "lifecycle"}
    _keys(value, expected, "capability candidate")
    if value["schema_version"] != CAPABILITY_SCHEMA:
        raise ExtensionDiscoveryError(
            "capability schema version is unsupported")
    implementation = _mapping(value["implementation"], "implementation")
    _keys(implementation, {"kind", "ref"}, "implementation")
    relative = path.relative_to(Path(root.path)).as_posix()
    body = dict(value)
    return CapabilityCandidate(
        str(value["capability_ref"]), str(value["version"]),
        str(value["description"]),
        _strings(value["input_roles"], "input_roles"),
        _strings(value["output_roles"], "output_roles"),
        _strings(value["permissions"], "permissions"),
        _strings(value["effects"], "effects"),
        str(implementation["kind"]), str(implementation["ref"]),
        _strings(value["tags"], "tags"), relative, root.path,
        _digest(body), str(value["lifecycle"]))


def _deduplicate(items, identity, label: str):
    selected = {}
    for item in items:
        key = identity(item)
        previous = selected.get(key)
        if previous is not None:
            if previous.content_digest != item.content_digest:
                raise ExtensionDiscoveryError(
                    f"conflicting {label} identity {key!r}")
            continue
        selected[key] = item
    return tuple(selected[key] for key in sorted(selected))


def discover_extensions(
        request: ExtensionDiscoveryRequest,
        environ: "Mapping[str, str] | None" = None) -> ExtensionSnapshot:
    """Discover added files without probing providers or executing code."""
    if not isinstance(request, ExtensionDiscoveryRequest):
        raise ExtensionDiscoveryError(
            "extension discovery needs ExtensionDiscoveryRequest")
    env = os.environ if environ is None else environ
    roots = _resolved_roots(request, env)
    providers = []
    capabilities = []
    skill_registry = SkillRegistry()
    plugins = []
    for root in roots:
        base = Path(root.path)
        providers.extend(_provider(path, root) for path in sorted(
            (base / "providers").glob("*.yaml"))
            if (base / "providers").is_dir())
        capabilities.extend(_capability(path, root) for path in sorted(
            (base / "capabilities").glob("*.yaml"))
            if (base / "capabilities").is_dir())
        skill_root = base / "skills"
        if skill_root.is_dir():
            skill_registry.discover((str(skill_root),))
        plugin_parent = base / "plugins"
        if plugin_parent.is_dir():
            plugin_roots = tuple(str(path.parent) for path in sorted(
                plugin_parent.glob(f"*/{PLUGIN_MANIFEST_NAME}")))
            if plugin_roots:
                plugins.extend(discover_plugin_bundles(
                    PluginDiscoveryRequest(
                        installed_roots=(plugin_roots
                                         if root.source != "project" else ()),
                        project_roots=(plugin_roots
                                       if root.source == "project" else ()),
                        engine_api_version="1")).manifests)
    provider_items = _deduplicate(
        providers, lambda item: (item.bundle_id, item.version), "provider")
    capability_items = _deduplicate(
        capabilities,
        lambda item: (item.capability_ref, item.version), "capability")
    intelligence = []
    intelligence_roots = tuple(
        root for root in roots
        if (Path(root.path) / "intelligence").is_dir())
    if intelligence_roots:
        from ..ontology.catalog import UnifiedCatalog
        catalog = UnifiedCatalog(plugin_roots=tuple(
            root.path for root in intelligence_roots)).discover()
        plugin_root_names = {
            f"plugin:{index}" for index in range(len(intelligence_roots))}
        for problem in catalog.problems:
            raise ExtensionDiscoveryError(problem)
        for entry in catalog.entries:
            if entry.physical_root not in plugin_root_names:
                continue
            if entry.node.lifecycle not in {"draft", "candidate", "validated"}:
                raise ExtensionDiscoveryError(
                    "added intelligence cannot self-register or self-promote")
            intelligence.append(entry.to_dict())
    skills = skill_registry.inventory(include_candidates=True)
    plugin_items = tuple(sorted(
        plugins, key=lambda item: (item.plugin_id, item.version, item.source)))
    reasons = (f"resolved {len(roots)} extension root(s)",
               f"discovered {len(provider_items)} provider route(s)",
               f"discovered {len(capability_items)} capability candidate(s)",
               f"discovered {len(skills)} skill candidate(s)",
               f"discovered {len(plugin_items)} plugin bundle(s)",
               f"discovered {len(intelligence)} intelligence candidate(s)")
    return ExtensionSnapshot(
        roots, provider_items, capability_items, skills, plugin_items,
        tuple(sorted(intelligence, key=lambda item: (
            item["node"]["identity"]["object_id"]))), reasons)


def discover_extensions_as_loop(
        request: ExtensionDiscoveryRequest,
        environ: "Mapping[str, str] | None" = None,
        parent=None) -> ExtensionSnapshot:
    """Resolve added files inside one deterministic Intelligence Loop."""
    from ..loop.encapsulate import as_loop
    from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    identity = LoopRoleIdentity(LoopRole.INTELLIGENCE,
                                "intelligence.code.resolve")
    relationship = (LoopRelationship.queried_by(parent.loop_id)
                    if parent is not None else LoopRelationship.starting())
    wrapped = as_loop(
        "discover added extension files",
        lambda: discover_extensions(request, environ), parent=parent,
        identity=identity, relationship=relationship)
    if wrapped.get("error") is not None:
        raise wrapped["error"]
    snapshot = wrapped["value"]
    return replace(snapshot, loop_id=wrapped["loop_id"])


def _render_endpoint(template: str, environ: Mapping[str, str]) -> str:
    names = _template_names(template)
    secret_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH",
                      "CREDENTIAL")
    unsafe = sorted(name for name in names
                    if any(marker in name.upper()
                           for marker in secret_markers))
    if unsafe:
        raise ExtensionDiscoveryError(
            "provider endpoint templates cannot interpolate credentials: "
            + ", ".join(unsafe))
    missing = sorted(name for name in names if not environ.get(name))
    if missing:
        raise ExtensionDiscoveryError(
            "provider endpoint template needs environment values: "
            + ", ".join(missing))
    return string.Template(template).substitute(environ)


def apply_provider_extensions(
        request: ExtensionApplicationRequest,
        environ: "Mapping[str, str] | None" = None) -> ExtensionApplication:
    """Compose provider files into RuntimeSettings without calling them.

    Free routes with present credentials are prepended to their declared tiers.
    Paid routes require explicit opt-in. Missing credentials keep a provider
    inspectable but do not make it an automatic route.
    """
    if not isinstance(request, ExtensionApplicationRequest):
        raise ExtensionDiscoveryError(
            "provider application needs ExtensionApplicationRequest")
    settings = request.settings
    snapshot = request.snapshot
    env = os.environ if environ is None else environ
    existing = {item.provider_id: item for item in settings.models.providers}
    providers = list(settings.models.providers)
    tiers = {item.name: item for item in settings.models.tiers}
    activated = []
    inactive = []
    for bundle in snapshot.providers:
        try:
            resolved_endpoint = _render_endpoint(
                bundle.provider.endpoint, env)
        except ExtensionDiscoveryError as exc:
            inactive.append((bundle.provider.route_name, str(exc)))
            continue
        configured = bundle.provider.to_provider_settings(resolved_endpoint)
        if configured is None:
            inactive.append((
                bundle.provider.route_name,
                "executor unavailable for protocol/auth: "
                f"{bundle.provider.protocol}/{bundle.provider.auth.kind}"))
            continue
        previous = existing.get(configured.provider_id)
        if previous is not None and previous != configured:
            raise ExtensionDiscoveryError(
                f"provider {configured.provider_id!r} conflicts with settings")
        if previous is None:
            providers.append(configured)
            existing[configured.provider_id] = configured
        if not configured.enabled:
            inactive.append((configured.route_name, "provider is disabled"))
            continue
        credential_present = (not configured.credential_env or bool(
            str(env.get(configured.credential_env, "")).strip()))
        eligible = (bundle.access_class in {"zero_price", "local"}
                    or request.allow_paid)
        if not eligible:
            inactive.append((
                configured.route_name,
                f"{bundle.access_class} route needs nonzero-cost opt-in"))
            continue
        if not credential_present:
            inactive.append((configured.route_name,
                             f"missing {configured.credential_env}"))
            continue
        for tier_name in bundle.tiers:
            tier = tiers[tier_name]
            routes = tuple(item for item in tier.routes
                           if item != configured.route_name)
            tiers[tier_name] = replace(
                tier, routes=(configured.route_name, *routes))
        activated.append(configured.route_name)
    models = replace(
        settings.models, providers=tuple(providers),
        tiers=tuple(tiers[name] for name in MODEL_THINKING_POWER_LEVELS))
    return ExtensionApplication(
        replace(settings, models=models), snapshot, tuple(activated),
        tuple(inactive))


def self_test() -> dict:
    """Prove added files resolve, activate safely, and never execute code."""
    import tempfile

    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory(prefix="loop-engine-extensions-") as tmp:
        root = Path(tmp) / "extensions"
        (root / "providers").mkdir(parents=True)
        (root / "capabilities").mkdir()
        skill = root / "skills" / "fixture-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: fixture-skill\nversion: 1.0.0\n"
            "description: Fixture candidate skill.\n---\n"
            "Return one typed summary candidate.\n", encoding="utf-8")
        intelligence = root / "intelligence" / "context" / "plugin"
        intelligence.mkdir(parents=True)
        payload = intelligence / "records.jsonl"
        payload.write_text('{"text":"candidate guidance"}\n',
                           encoding="utf-8")
        intelligence_manifest = {
            "schema": "catalog_manifest/v1",
            "folder_id": "intelligence.context.plugin",
            "source_class": "plugin",
            "objects": [{
                "id": "plugin.fixture.guidance", "version": "1.0.0",
                "artifact_kind": "intelligence_record",
                "lifecycle": "candidate",
                "content_digest": hashlib.sha256(
                    payload.read_bytes()).hexdigest(),
                "payload": "file:records.jsonl"}]}
        (intelligence / "manifest.yaml").write_text(
            yaml.safe_dump(intelligence_manifest, sort_keys=False),
            encoding="utf-8")
        provider = {
            "schema_version": PROVIDER_SCHEMA,
            "bundle_id": "fixture_free", "version": "1.0.0",
            "description": "Fixture free OpenAI-compatible route.",
            "sources": [{"kind": "protocol",
                         "url": "https://fixture.invalid/docs",
                         "observed_at": "2026-08-29"}],
            "provider": {
                "enabled": True,
                "auth": {"kind": "bearer_env",
                         "credential_env": "FIXTURE_KEY",
                         "header": "", "plugin_ref": ""},
                "endpoint": "https://fixture.invalid/v1", "model": "m",
                "protocol": "openai_chat", "locality": "cloud",
                "counts_as_evidence": True,
                "maximum_output_tokens": 4096,
                "maximum_output_source": "fixture metadata",
                "purposes": ["counted_generation", "decide_label"],
                "headers": {"X-Route": "free"}},
            "routing": {"tiers": ["medium"],
                        "access_class": "zero_price"},
            "pricing": {"input_cost_per_million": 0,
                        "output_cost_per_million": 0},
            "quota": {"scope": "none", "requests_per_minute": None,
                      "requests_per_day": None, "tokens_per_minute": None,
                      "tokens_per_day": None, "concurrency": None,
                      "credit_amount": None, "reset": "not_applicable"},
            "capabilities": ["text", "structured_output"],
            "data_policy": {"confidential_allowed": None,
                            "training_use": "unknown",
                            "retention": "unknown", "regions": []},
            "health": {"catalog_refresh_seconds": 86400,
                       "probe_timeout_seconds": 30}}
        (root / "providers" / "fixture.yaml").write_text(
            yaml.safe_dump(provider, sort_keys=False), encoding="utf-8")
        capability = {
            "schema_version": CAPABILITY_SCHEMA,
            "capability_ref": "plugin.fixture.summarize",
            "version": "1.0.0", "description": "Candidate summarizer.",
            "input_roles": ["text"], "output_roles": ["summary"],
            "permissions": [], "effects": [],
            "implementation": {"kind": "skill", "ref": "fixture-skill"},
            "tags": ["summary"], "lifecycle": "candidate"}
        (root / "capabilities" / "summary.yaml").write_text(
            yaml.safe_dump(capability, sort_keys=False), encoding="utf-8")
        initial = discover_extensions(
            ExtensionDiscoveryRequest((str(root),), include_defaults=False),
            environ={})
        skill_manifest = initial.skills[0]
        plugin = root / "plugins" / "fixture-plugin"
        plugin.mkdir(parents=True)
        (plugin / PLUGIN_MANIFEST_NAME).write_text(json.dumps({
            "schema_version": "plugin_bundle/v1",
            "plugin_id": "fixture-plugin", "version": "1.0.0",
            "description": "Fixture passive plugin bundle.",
            "engine_api_version": "1",
            "skills": [{"skill_id": skill_manifest.skill_id,
                        "version": skill_manifest.version,
                        "manifest_digest": skill_manifest.manifest_digest}],
            "profile_refs": [],
            "capability_refs": ["plugin.fixture.summarize"],
            "event_subscriptions": ["loop.completed"]}, indent=2),
            encoding="utf-8")
        snapshot = discover_extensions_as_loop(
            ExtensionDiscoveryRequest((str(root),), include_defaults=False),
            environ={})
        check("added_files_resolve_through_one_intelligence_loop",
              snapshot.loop_id.startswith("loop")
              and len(snapshot.providers) == 1
              and len(snapshot.capabilities) == 1
              and len(snapshot.skills) == 1
              and len(snapshot.plugins) == 1
              and len(snapshot.intelligence_entries) == 1)
        inactive = apply_provider_extensions(
            ExtensionApplicationRequest(RuntimeSettings(), snapshot), {})
        check("missing_credential_keeps_route_inactive_but_inspectable",
              not inactive.activated_routes
              and inactive.inactive_routes[0][1] == "missing FIXTURE_KEY"
              and any(item.provider_id == "fixture_free"
                      for item in inactive.settings.models.providers))
        active = apply_provider_extensions(
            ExtensionApplicationRequest(RuntimeSettings(), snapshot),
            {"FIXTURE_KEY": "secret"})
        medium = next(item for item in active.settings.models.tiers
                      if item.name == "medium")
        description = active.settings.build_gateway(
            {"FIXTURE_KEY": "secret"}).providers["fixture_free"].describe()
        check("free_route_with_key_auto_activates_without_serializing_key",
              medium.routes[0] == "custom.fixture_free"
              and active.activated_routes == ("custom.fixture_free",)
              and "secret" not in json.dumps(description))
        check("capability_file_is_candidate_only",
              snapshot.capabilities[0].lifecycle == "candidate"
              and not hasattr(snapshot.capabilities[0], "execute"))
        project = Path(tmp) / "project"
        conventional = project / EXTENSION_FOLDER
        conventional.mkdir(parents=True)
        automatic = discover_extensions(
            ExtensionDiscoveryRequest(project_root=str(project)), {})
        check("conventional_project_folder_is_recognized_without_cli_roots",
              len(automatic.roots) == 1
              and automatic.roots[0].source == "project")
        secret_header_refused = False
        try:
            ProviderSettings(
                "unsafe_header", kind="custom",
                endpoint="https://fixture.invalid/v1", model="m",
                maximum_output_tokens=10,
                maximum_output_source="fixture",
                headers=(("Authorization", "Bearer secret"),))
        except Exception:
            secret_header_refused = True
        check("provider_files_cannot_define_secret_headers",
              secret_header_refused)
        header_auth = replace(
            snapshot.providers[0].provider,
            auth=ProviderAuthDefinition(
                "header_env", "FIXTURE_KEY", "x-api-key", ""))
        header_settings = header_auth.to_provider_settings(
            "https://fixture.invalid/v1")
        header_description = RuntimeSettings(
            models=replace(RuntimeSettings().models,
                           providers=(header_settings,))).build_gateway(
                               {"FIXTURE_KEY": "secret"}
                           ).providers["fixture_free"].describe()
        check("header_environment_authentication_is_secret_safe",
              header_settings.auth_scheme == "header"
              and header_settings.auth_header == "x-api-key"
              and "secret" not in json.dumps(header_description))
        signed = replace(
            snapshot.providers[0].provider,
            auth=ProviderAuthDefinition("aws_sigv4"))
        check("signed_auth_is_declared_but_not_falsely_executable",
              not signed.executable_by_generic_gateway
              and signed.to_provider_settings(signed.endpoint) is None)
        provider["description"] = "changed"
        second = root / "duplicate"
        (second / "providers").mkdir(parents=True)
        (second / "providers" / "fixture.yaml").write_text(
            yaml.safe_dump(provider, sort_keys=False), encoding="utf-8")
        conflict = False
        try:
            discover_extensions(
                ExtensionDiscoveryRequest(
                    (str(root), str(second)), include_defaults=False), {})
        except ExtensionDiscoveryError:
            conflict = True
        check("conflicting_added_identity_fails_closed", conflict)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "extension_discovery_self_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


__all__ = (
    "CAPABILITY_SCHEMA", "EXTENSION_FOLDER", "EXTENSION_ROOTS_ENV",
    "PROVIDER_SCHEMA", "CapabilityCandidate", "ExtensionApplication",
    "ExtensionApplicationRequest", "ExtensionDiscoveryError",
    "ExtensionDiscoveryRequest", "ExtensionRoot",
    "ExtensionSnapshot", "ProviderAuthDefinition",
    "ProviderEndpointDefinition", "ProviderRouteBundle",
    "ProviderSourceRef",
    "apply_provider_extensions",
    "discover_extensions", "discover_extensions_as_loop")
