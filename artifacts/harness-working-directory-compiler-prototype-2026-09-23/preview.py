"""Pure mechanical experiment for the existing material-install-layout owner.

Not imported by runtime or installer. No registry, filesystem, execution,
credential, model or admission operations. A future active implementation must
migrate ClientLayoutProfile/preview to v2 and register the existing slot edge.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Protocol

from tools.install_selected_material import ClientLayoutProfile, InstallRefusal, native_name
from loop_engine.core.facets import EFFECTS
from loop_engine.core.service_runtime.catalogue_packages import (
    CataloguePackage, FILE_ROLES, placement_path,
)
from loop_engine.core.service_runtime.records import ServiceRuntimeError


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


class PreviewRefusal(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _require(condition, code):
    if not condition:
        raise PreviewRefusal(code)


@dataclass(frozen=True)
class DraftPackageProfile:
    """Experiment-only role extension around the existing passive profile.

    This wrapper is not a native_client_layout_profile/v2 wire reader. Its
    fields must be folded into that owner's reviewed v2 change, not retained
    as a parallel profile registry or a legacy compatibility adapter.
    """
    layout: ClientLayoutProfile
    supported_roles: tuple[str, ...]

    def __post_init__(self):
        _require(isinstance(self.layout, ClientLayoutProfile), "profile_invalid")
        _require(type(self.supported_roles) is tuple and bool(self.supported_roles)
                 and len(set(self.supported_roles)) == len(self.supported_roles)
                 and all(role in FILE_ROLES for role in self.supported_roles), "profile_invalid")

    @property
    def digest(self):
        return _digest({"experiment_profile": "existing_owner_role_extension/v1", "layout": asdict(self.layout),
                        "supported_roles": self.supported_roles})


@dataclass(frozen=True)
class Authority:
    installation: tuple[str, ...]
    worker: tuple[str, ...]

    def __post_init__(self):
        for values in (self.installation, self.worker):
            _require(type(values) is tuple and len(set(values)) == len(values)
                     and all(value in EFFECTS for value in values)
                     and not ("pure" in values and len(values) > 1), "authority_invalid")


@dataclass(frozen=True)
class ExistingState:
    """Host observation only. Constructing a record does not inspect a real path."""
    path: str
    kind: str
    digest: str | None = None
    managed: bool = False

    def __post_init__(self):
        placement_path(self.path)
        _require(self.kind in ("absent", "file", "directory", "symlink", "other")
                 and type(self.managed) is bool, "workspace_state_invalid")
        if self.kind == "file":
            _require(type(self.digest) is str and len(self.digest) == 64
                     and all(c in "0123456789abcdef" for c in self.digest), "workspace_state_invalid")
        else:
            _require(self.digest is None and not self.managed, "workspace_state_invalid")


@dataclass(frozen=True)
class PackageInput:
    identity: str
    kind: str
    package: CataloguePackage
    payloads: tuple[tuple[str, bytes], ...]
    declared_effects: tuple[str, ...] = ()

    def __post_init__(self):
        _require(isinstance(self.package, CataloguePackage) and type(self.payloads) is tuple, "package_input_invalid")
        _require(type(self.declared_effects) is tuple and len(set(self.declared_effects)) == len(self.declared_effects)
                 and all(value in EFFECTS for value in self.declared_effects)
                 and not ("pure" in self.declared_effects and len(self.declared_effects) > 1), "package_effects_invalid")
        _require(not self.package.executable or "spawns_process" in self.declared_effects,
                 "package_executable_effect_missing")


@dataclass(frozen=True)
class PreviewRequest:
    profile: DraftPackageProfile
    packages: tuple[PackageInput, ...]
    authority: Authority
    expected: tuple[ExistingState, ...]
    observed: tuple[ExistingState, ...]

    def __post_init__(self):
        _require(isinstance(self.profile, DraftPackageProfile) and isinstance(self.authority, Authority)
                 and type(self.packages) is tuple and 1 <= len(self.packages) <= 32
                 and all(isinstance(p, PackageInput) for p in self.packages), "request_invalid")
        _state_index(self.expected)
        _state_index(self.observed)


@dataclass(frozen=True)
class CompiledFile:
    package_identity: str
    package_digest: str
    source_path: str
    target_path: str
    role: str
    media_type: str
    digest: str
    payload: bytes = field(repr=False)

    def reference(self):
        return {"package_identity": self.package_identity, "package_digest": self.package_digest,
                "source_path": self.source_path, "target_path": self.target_path, "role": self.role,
                "media_type": self.media_type, "digest": self.digest, "size_bytes": len(self.payload)}


@dataclass(frozen=True)
class PreviewResult:
    status: str
    engine: str
    profile_digest: str
    files: tuple[CompiledFile, ...] = ()
    expected: tuple[ExistingState, ...] = ()
    authority_digest: str = ""
    refusal: str = ""
    installation_authorized: bool = False

    @property
    def required_installation_effects(self):
        return ("writes_fs",)

    @property
    def native_qualified(self):
        return False

    @property
    def writes_performed(self):
        return False

    @property
    def digest(self):
        return _digest({"record_type": "working_directory_compiler_experiment_result/v1",
                        "status": self.status, "engine": self.engine, "profile_digest": self.profile_digest,
                        "files": [f.reference() for f in self.files], "expected": [asdict(s) for s in self.expected],
                        "authority_digest": self.authority_digest, "refusal": self.refusal,
                        "required_installation_effects": self.required_installation_effects,
                        "installation_authorized": self.installation_authorized,
                        "native_qualified": False, "writes_performed": False})


class PreviewCompiler(Protocol):
    """Experiment interface only; not an advertised runtime edge."""
    def compile(self, request: PreviewRequest) -> PreviewResult: ...


def _state_index(states):
    _require(type(states) is tuple and len(states) <= 4096 and all(isinstance(s, ExistingState) for s in states), "workspace_state_invalid")
    index = {s.path: s for s in states}
    _require(len(index) == len(states) and len({s.path.casefold() for s in states}) == len(states), "workspace_state_duplicate")
    return index


def _snapshots_match(expected, observed):
    return _state_index(expected) == _state_index(observed)


def _roles_supported(profile, package):
    return all(file.role in profile.supported_roles for file in package.files)


def _effects_within(item, authority):
    return set(item.declared_effects) - {"pure"} <= set(authority.worker)


def _payloads_bound(item):
    rows = item.payloads
    if any(type(row) is not tuple or len(row) != 2 or type(row[0]) is not str or type(row[1]) is not bytes for row in rows):
        raise PreviewRefusal("package_inventory_mismatch")
    bodies = dict(rows)
    _require(len(bodies) == len(rows) and set(bodies) == {e.path for e in item.package.files}, "package_inventory_mismatch")
    _require(all(len(bodies[e.path]) == e.size_bytes and _sha(bodies[e.path]) == e.digest
                 for e in item.package.files), "package_bytes_mismatch")
    return bodies


def _paths_disjoint(files):
    paths = [f.target_path.casefold() for f in files]
    _require(len(set(paths)) == len(paths), "target_collision")
    named = set(paths)
    for path in paths:
        parts = path.split("/")
        _require(not any("/".join(parts[:end]) in named for end in range(1, len(parts))), "parent_file_collision")


def _placement_state(files, expected):
    index = _state_index(expected)
    for file in files:
        _require(file.target_path in index, "workspace_observation_missing")
        old = index[file.target_path]
        _require(old.kind == "absent" or (old.kind == "file" and old.managed), "foreign_file_collision")
        parts = file.target_path.split("/")
        for end in range(1, len(parts)):
            parent = "/".join(parts[:end])
            _require(parent in index, "workspace_observation_missing")
            _require(index[parent].kind in ("directory", "absent"), "unsafe_parent_state")


class BaltorPreviewEngine:
    """Copies complete package bytes into a scoped plan, without applying it."""
    identity = "baltor.package_copy_experiment@1"

    def compile(self, request):
        _require(isinstance(request, PreviewRequest), "request_invalid")
        try:
            _require(_snapshots_match(request.expected, request.observed), "stale_workspace_state")
            files = []
            for item in request.packages:
                bodies = _payloads_bound(item)
                _require(_roles_supported(request.profile, item.package), "unsupported_mandatory_role")
                _require(_effects_within(item, request.authority), "worker_authority_exceeded")
                try:
                    location = request.profile.layout.location_for(item.kind)
                    name = native_name(item.identity)
                except InstallRefusal:
                    raise PreviewRefusal("kind_has_no_native_location") from None
                _require(location.file_name in bodies, "native_entrypoint_missing")
                # Existing location identifies the package entrypoint's parent;
                # the complete declared relative tree stays intact beneath it.
                prefix = (*location.directory_segments, name)
                for entry in item.package.files:
                    target = "/".join((*prefix, *entry.path.split("/")))
                    try:
                        placement_path(target)
                    except ServiceRuntimeError:
                        raise PreviewRefusal("projected_path_invalid") from None
                    files.append(CompiledFile(item.identity, item.package.package_digest, entry.path, target,
                                              entry.role, entry.media_type, entry.digest, bodies[entry.path]))
            _require(len(files) <= 2048, "preview_too_large")
            _paths_disjoint(files)
            _placement_state(files, request.expected)
            return PreviewResult("compiled", self.identity, request.profile.digest,
                                 tuple(sorted(files, key=lambda f: f.target_path)),
                                 tuple(sorted(request.expected, key=lambda s: s.path)), _digest(asdict(request.authority)),
                                 installation_authorized="writes_fs" in request.authority.installation)
        except PreviewRefusal as error:
            return PreviewResult("refused", self.identity, request.profile.digest, refusal=error.code)


class UnavailableAgentHarnessEngine:
    """A proposed interface can honestly report the absence of an implementation."""
    identity = "madebywild.adapter_not_implemented"

    def compile(self, request):
        return PreviewResult("refused", self.identity, request.profile.digest, refusal="engine_unavailable")


def revalidate(plan: PreviewResult, observed: tuple[ExistingState, ...]) -> str:
    """Pure comparison only; a future writer must obtain fresh confined observations."""
    if plan.status != "compiled":
        return "plan_not_compiled"
    return "" if _snapshots_match(plan.expected, observed) else "stale_workspace_state"
