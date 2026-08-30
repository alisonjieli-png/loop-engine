"""Passive plugin bundles resolved through existing skill admission authority.

Bundles distribute skills, profiles, capabilities, and event subscriptions.
They grant no authority and create no runtime. Resolution is deterministic,
full-content digest bound, and can execute through one Intelligence-role Loop.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .event_vocabulary import EVENT_FAMILIES
from .skill_registry import SkillManifest, SkillRegistry


_ID = re.compile(r"^[a-z][a-z0-9_-]{1,79}$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
PLUGIN_MANIFEST_NAME = "loop-engine-plugin.json"


class PluginBundleError(ValueError):
    """Plugin bundle discovery, validation, or resolution failed closed."""


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _names(label: str, values) -> tuple[str, ...]:
    result = tuple(values or ())
    if (any(not isinstance(value, str) or not value.strip() for value in result)
            or len(result) != len(set(result))):
        raise PluginBundleError(
            f"{label} must contain unique non-empty strings")
    return tuple(sorted(result))


@dataclass(frozen=True)
class PluginSkillRef:
    """Exact admitted skill identity required by one plugin bundle."""

    skill_id: str
    version: str
    manifest_digest: str

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.skill_id) or not _SEMVER.fullmatch(self.version):
            raise PluginBundleError("plugin skill identity is invalid")
        if not _DIGEST.fullmatch(self.manifest_digest):
            raise PluginBundleError("plugin skill digest is invalid")

    def to_dict(self) -> dict:
        return {"skill_id": self.skill_id, "version": self.version,
                "manifest_digest": self.manifest_digest}


@dataclass(frozen=True)
class PluginBundleManifest:
    """Small distribution card; referenced skills remain separately admitted."""

    plugin_id: str
    version: str
    description: str
    engine_api_version: str
    skills: tuple[PluginSkillRef, ...]
    profile_refs: tuple[str, ...] = ()
    capability_refs: tuple[str, ...] = ()
    event_subscriptions: tuple[str, ...] = ()
    source: str = "installed"
    root_path: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.plugin_id) or not _SEMVER.fullmatch(self.version):
            raise PluginBundleError("plugin identity is invalid")
        if not self.description.strip() or not self.engine_api_version.strip():
            raise PluginBundleError("plugin description and API version are required")
        skills = tuple(self.skills)
        if (not skills or any(not isinstance(item, PluginSkillRef)
                              for item in skills)
                or len({(item.skill_id, item.version) for item in skills})
                != len(skills)):
            raise PluginBundleError("plugin needs unique exact skill references")
        object.__setattr__(self, "skills", tuple(sorted(
            skills, key=lambda item: (item.skill_id, item.version))))
        object.__setattr__(self, "profile_refs",
                           _names("profile_refs", self.profile_refs))
        object.__setattr__(self, "capability_refs",
                           _names("capability_refs", self.capability_refs))
        subscriptions = _names("event_subscriptions", self.event_subscriptions)
        if any(item not in EVENT_FAMILIES for item in subscriptions):
            raise PluginBundleError("plugin subscription is outside Run History")
        object.__setattr__(self, "event_subscriptions", subscriptions)
        if self.source not in {"installed", "project"}:
            raise PluginBundleError("plugin source must be installed or project")

    def body(self) -> dict:
        return {
            "schema_version": "plugin_bundle/v1", "plugin_id": self.plugin_id,
            "version": self.version, "description": self.description,
            "engine_api_version": self.engine_api_version,
            "skills": [item.to_dict() for item in self.skills],
            "profile_refs": list(self.profile_refs),
            "capability_refs": list(self.capability_refs),
            "event_subscriptions": list(self.event_subscriptions),
        }

    @property
    def content_digest(self) -> str:
        return _digest(self.body())


@dataclass(frozen=True)
class PluginResolutionRequest:
    """Installed and project roots plus the existing admitted skill registry."""

    installed_roots: tuple[str, ...]
    project_roots: tuple[str, ...]
    skill_registry: SkillRegistry = field(repr=False, compare=False)
    engine_api_version: str = "1"


@dataclass(frozen=True)
class PluginDiscoveryRequest:
    installed_roots: tuple[str, ...]
    project_roots: tuple[str, ...]
    engine_api_version: str = "1"


@dataclass(frozen=True)
class PluginDiscoveryResult:
    disposition: str
    manifests: tuple[PluginBundleManifest, ...]
    reasons: tuple[str, ...]

    def to_dict(self):
        return {"record_type":"plugin_discovery_result/v1",
                "disposition":self.disposition,
                "manifests":[{**item.body(),"source":item.source,
                              "content_digest":item.content_digest}
                             for item in self.manifests],
                "reasons":list(self.reasons)}


@dataclass(frozen=True)
class ResolvedPlugin:
    manifest: PluginBundleManifest
    admission_digests: tuple[str, ...]

    @property
    def resolution_digest(self) -> str:
        return _digest({"manifest": self.manifest.body(),
                        "admissions": list(self.admission_digests)})


@dataclass(frozen=True)
class ResolvedPluginSnapshot:
    """Exact deterministic plugin population used by one run."""

    plugins: tuple[ResolvedPlugin, ...]
    resolution_reasons: tuple[str, ...]
    loop_id: str = ""

    @property
    def content_digest(self) -> str:
        return _digest([{"plugin_id": item.manifest.plugin_id,
                         "version": item.manifest.version,
                         "digest": item.resolution_digest}
                        for item in self.plugins])

    def to_dict(self) -> dict:
        return {"record_type": "resolved_plugin_snapshot/v1",
                "content_digest": self.content_digest,
                "loop_id": self.loop_id,
                "plugins": [{"manifest": item.manifest.body(),
                             "manifest_digest": item.manifest.content_digest,
                             "admission_digests": list(item.admission_digests),
                             "resolution_digest": item.resolution_digest}
                            for item in self.plugins],
                "resolution_reasons": list(self.resolution_reasons)}

    def ascii_tree(self) -> str:
        lines = [f"Plugins [{self.content_digest[:12]}]"]
        for p_index, plugin in enumerate(self.plugins):
            last_plugin = p_index == len(self.plugins) - 1
            branch = "└─" if last_plugin else "├─"
            manifest = plugin.manifest
            lines.append(f"{branch} {manifest.plugin_id}@{manifest.version} "
                         f"[{manifest.source}] {manifest.content_digest[:12]}")
            indent = "   " if last_plugin else "│  "
            for index, skill in enumerate(manifest.skills):
                skill_branch = "└─" if index == len(manifest.skills) - 1 else "├─"
                lines.append(f"{indent}{skill_branch} {skill.skill_id}@"
                             f"{skill.version} {skill.manifest_digest[:12]}")
        return "\n".join(lines)


def _load_manifest(root_text: str, source: str) -> PluginBundleManifest:
    root = Path(root_text).expanduser().resolve()
    path = root / PLUGIN_MANIFEST_NAME
    if not path.is_file() or path.is_symlink():
        raise PluginBundleError(f"plugin manifest is unavailable: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PluginBundleError(f"plugin manifest is invalid: {path}") from exc
    expected = {"schema_version", "plugin_id", "version", "description",
                "engine_api_version", "skills", "profile_refs",
                "capability_refs", "event_subscriptions"}
    if (not isinstance(value, dict) or set(value) != expected
            or value["schema_version"] != "plugin_bundle/v1"):
        raise PluginBundleError("plugin manifest shape is invalid")
    skills = tuple(PluginSkillRef(**item) for item in value["skills"])
    return PluginBundleManifest(
        value["plugin_id"], value["version"], value["description"],
        value["engine_api_version"], skills, tuple(value["profile_refs"]),
        tuple(value["capability_refs"]), tuple(value["event_subscriptions"]),
        source, str(root))


def _verify_skill_files(manifest: SkillManifest) -> None:
    root = Path(manifest.root_path).resolve()
    for ref in manifest.files:
        path = (root / ref.relative_path).resolve()
        if not path.is_file() or root not in path.parents:
            raise PluginBundleError("plugin skill file is unavailable or escapes")
        if hashlib.sha256(path.read_bytes()).hexdigest() != ref.digest:
            raise PluginBundleError("plugin skill changed after admission")


def discover_plugin_bundles(request: PluginDiscoveryRequest) \
        -> PluginDiscoveryResult:
    if not isinstance(request,PluginDiscoveryRequest):
        raise PluginBundleError("discovery requires PluginDiscoveryRequest")
    manifests=tuple(sorted(
        [*(_load_manifest(root,"installed") for root in request.installed_roots),
         *(_load_manifest(root,"project") for root in request.project_roots)],
        key=lambda item:(item.plugin_id,item.version,item.source)))
    for manifest in manifests:
        if manifest.engine_api_version!=request.engine_api_version:
            raise PluginBundleError("plugin engine API version is incompatible")
    disposition="resolved_nonempty" if manifests else "resolved_empty"
    return PluginDiscoveryResult(disposition,manifests,
                                 (f"discovered {len(manifests)} bundle(s)",))


def resolve_plugin_snapshot(
        request: PluginResolutionRequest) -> ResolvedPluginSnapshot:
    """Resolve full-content-equivalent bundles or refuse every conflict."""
    if not isinstance(request, PluginResolutionRequest):
        raise PluginBundleError("resolution requires PluginResolutionRequest")
    manifests = [*(_load_manifest(root, "installed")
                   for root in request.installed_roots),
                 *(_load_manifest(root, "project")
                   for root in request.project_roots)]
    grouped: dict[tuple[str, str], PluginBundleManifest] = {}
    reasons = []
    for manifest in manifests:
        if manifest.engine_api_version != request.engine_api_version:
            raise PluginBundleError("plugin engine API version is incompatible")
        key = (manifest.plugin_id, manifest.version)
        previous = grouped.get(key)
        if previous is not None:
            if previous.content_digest != manifest.content_digest:
                raise PluginBundleError("project plugin cannot silently override installed content")
            reasons.append(f"deduplicated exact plugin {key[0]}@{key[1]}")
            continue
        grouped[key] = manifest
    resolved = []
    inventory = {(item.skill_id, item.version): item
                 for item in request.skill_registry.inventory(include_candidates=True)}
    for key, manifest in sorted(grouped.items()):
        admissions = []
        for ref in manifest.skills:
            skill = inventory.get((ref.skill_id, ref.version))
            if (skill is None or skill.lifecycle != "registered"
                    or skill.manifest_digest != ref.manifest_digest):
                raise PluginBundleError("plugin skill is not exactly admitted")
            admission = request.skill_registry.admission(ref.skill_id, ref.version)
            if admission.manifest_digest != ref.manifest_digest:
                raise PluginBundleError("plugin skill admission digest differs")
            _verify_skill_files(skill)
            admissions.append(admission.digest)
        resolved.append(ResolvedPlugin(manifest, tuple(admissions)))
        reasons.append(f"resolved {key[0]}@{key[1]} with {len(admissions)} admitted skill(s)")
    return ResolvedPluginSnapshot(tuple(resolved), tuple(reasons))


def resolve_plugin_snapshot_as_loop(
        request: PluginResolutionRequest, parent=None) -> ResolvedPluginSnapshot:
    """Resolve plugins through one deterministic Intelligence-role Loop."""
    from ..loop.encapsulate import as_loop
    from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    identity = LoopRoleIdentity(LoopRole.INTELLIGENCE,
                                "intelligence.code.resolve")
    relationship = (LoopRelationship.queried_by(parent.loop_id)
                    if parent is not None else LoopRelationship.starting())
    wrapped = as_loop("resolve admitted plugin bundles",
                      lambda: resolve_plugin_snapshot(request), parent=parent,
                      identity=identity, relationship=relationship)
    if wrapped.get("error") is not None:
        raise wrapped["error"]
    snapshot = wrapped["value"]
    return ResolvedPluginSnapshot(snapshot.plugins,
                                  snapshot.resolution_reasons,
                                  wrapped["loop_id"])


__all__ = ("PLUGIN_MANIFEST_NAME", "PluginBundleError",
           "PluginBundleManifest", "PluginDiscoveryRequest",
           "PluginDiscoveryResult", "PluginResolutionRequest",
           "PluginSkillRef", "ResolvedPlugin", "ResolvedPluginSnapshot",
           "discover_plugin_bundles", "resolve_plugin_snapshot",
           "resolve_plugin_snapshot_as_loop")
