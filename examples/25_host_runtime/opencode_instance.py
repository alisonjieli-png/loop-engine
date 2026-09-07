"""Compile optional harness instances from a pinned core and selected resources.

This source-checkout prototype consumes host-approved artifact descriptors.
It does not replace the Loop runtime, select resources by task label, register
a harness automatically, or enable the quarantined raw-host OpenCode adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re

from loop_engine.core.context_artifacts import ContextArtifactRef
from loop_engine.core.record_operations_records import canonical_json, content_digest

KINDS = ('context', 'skill', 'plugin', 'tool')


@dataclass(frozen=True)
class BundleResource:
    resource_id: str
    version: str
    kind: str
    relative_path: str
    artifact_ref: ContextArtifactRef
    description: str = ''

    def __post_init__(self):
        path = PurePosixPath(self.relative_path)
        if (not self.resource_id or not self.version or self.kind not in KINDS
                or path.is_absolute() or '..' in path.parts or not path.parts
                or str(path) != self.relative_path or '\\' in self.relative_path
                or not isinstance(self.artifact_ref, ContextArtifactRef)):
            raise ValueError('invalid versioned bundle resource')
        permitted = {'context': 'context/', 'skill': '.opencode/skills/',
                     'plugin': '.opencode/plugins/', 'tool': '.opencode/tools/'}
        if not self.relative_path.startswith(permitted[self.kind]):
            raise ValueError('resource path does not match its declared kind')

    @property
    def reference(self):
        return self.resource_id + '@' + self.version + '#sha256:' + self.artifact_ref.digest

    def card(self):
        return {'resource_id': self.resource_id, 'version': self.version,
                'description': self.description, 'reference': self.reference, 'kind': self.kind,
                'relative_path': self.relative_path, 'artifact_ref': self.artifact_ref.to_dict()}


@dataclass(frozen=True)
class CoreBundle:
    bundle_id: str
    version: str
    resources: tuple[BundleResource, ...]
    required_tools: tuple[str, ...]
    permitted_tools: tuple[str, ...]
    maximum_hydration_bytes: int

    def __post_init__(self):
        for name in ('resources', 'required_tools', 'permitted_tools'):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        if (not self.bundle_id or not self.version
                or type(self.maximum_hydration_bytes) is not int or self.maximum_hydration_bytes < 1
                or not set(self.required_tools) <= set(self.permitted_tools)
                or len(set(self.permitted_tools)) != len(self.permitted_tools)
                or any(type(name) is not str or not re.fullmatch(r'[a-z][a-z0-9_.-]{0,95}', name)
                       for name in self.permitted_tools)
                or any(type(item) is not BundleResource for item in self.resources)):
            raise ValueError('invalid pinned core bundle')
        if len({item.relative_path for item in self.resources}) != len(self.resources):
            raise ValueError('core resource paths must be unique')

    @property
    def digest(self):
        return content_digest({'bundle_id': self.bundle_id, 'version': self.version,
            'resources': [item.card() for item in self.resources],
            'required_tools': self.required_tools, 'permitted_tools': self.permitted_tools,
            'maximum_hydration_bytes': self.maximum_hydration_bytes})


@dataclass(frozen=True)
class InstanceGrant:
    """Host-issued access for one activation/step, separate from core identity."""
    activation_ref: str
    step_ref: str
    authority_ref: str
    allowed_resource_refs: tuple[str, ...]
    permitted_tools: tuple[str, ...]
    maximum_hydration_bytes: int

    def __post_init__(self):
        for name in ('allowed_resource_refs', 'permitted_tools'):
            values = tuple(getattr(self, name))
            if len(set(values)) != len(values) or any(type(value) is not str or not value for value in values):
                raise ValueError('grant lists require exact unique references')
            object.__setattr__(self, name, values)
        if (any(type(value) is not str or not value for value in
                (self.activation_ref, self.step_ref, self.authority_ref))
                or type(self.maximum_hydration_bytes) is not int or self.maximum_hydration_bytes < 1):
            raise ValueError('invalid instance grant')

    @property
    def digest(self):
        return content_digest({'record_type': 'harness_instance_grant/v1', **self.__dict__})


def validate_instance_grant(core, grant, activation_ref, step_ref):
    if (type(core) is not CoreBundle or type(grant) is not InstanceGrant
            or grant.activation_ref != activation_ref or grant.step_ref != step_ref
            or not set(core.required_tools) <= set(grant.permitted_tools)
            or not set(grant.permitted_tools) <= set(core.permitted_tools)
            or grant.maximum_hydration_bytes > core.maximum_hydration_bytes):
        raise ValueError('instance grant does not match its scope or core policy')


@dataclass(frozen=True)
class InstanceSelection:
    backend: str = 'native'
    activation_ref: str = ''
    step_ref: str = ''
    core_digest: str = ''
    selected_resource_refs: tuple[str, ...] = ()
    selected_tools: tuple[str, ...] = ()
    selection_evidence_ref: str = ''
    grant_digest: str = ''

    def __post_init__(self):
        object.__setattr__(self, 'selected_resource_refs', tuple(self.selected_resource_refs))
        object.__setattr__(self, 'selected_tools', tuple(self.selected_tools))
        if self.backend not in ('native', 'opencode'):
            raise ValueError('unknown prototype execution backend')


@dataclass(frozen=True)
class CompiledInstance:
    manifest_json: str
    files: tuple[tuple[str, bytes], ...]

    @property
    def digest(self):
        return hashlib.sha256(self.manifest_json.encode()).hexdigest()


def compile_instance(core, selection, catalog, materialize, *, grant=None):
    """Validate descriptors first, then hydrate only the selected exact bytes."""
    if type(selection) is not InstanceSelection:
        raise TypeError('a typed instance selection is required')
    if selection.backend == 'native':
        return None
    if (not isinstance(core, CoreBundle) or selection.core_digest != core.digest
            or not selection.activation_ref or not selection.step_ref
            or not selection.selection_evidence_ref):
        raise ValueError('OpenCode requires an exact core, activation, step, and selection record')
    validate_instance_grant(core, grant, selection.activation_ref, selection.step_ref)
    if selection.grant_digest != grant.digest:
        raise ValueError('selection is not bound to the exact instance grant')
    refs = selection.selected_resource_refs
    if len(set(refs)) != len(refs) or not set(refs) <= set(grant.allowed_resource_refs):
        raise ValueError('selected resources exceed the host-approved core policy')
    tools = tuple(dict.fromkeys((*core.required_tools, *selection.selected_tools)))
    if not set(tools) <= set(grant.permitted_tools):
        raise ValueError('step selection cannot expand tool authority')
    available = tuple(catalog)
    if any(type(item) is not BundleResource for item in available):
        raise ValueError('host catalog must contain typed resource descriptors')
    by_ref = {item.reference: item for item in available}
    if len(by_ref) != len(available) or not set(refs) <= set(by_ref):
        raise ValueError('selected catalog reference is missing or ambiguous')
    resources = (*core.resources, *(by_ref[ref] for ref in refs))
    if len({item.relative_path for item in resources}) != len(resources):
        raise ValueError('step resources cannot replace core or other selected paths')
    if sum(item.artifact_ref.byte_count for item in resources) > grant.maximum_hydration_bytes:
        raise ValueError('declared hydration exceeds the core policy')
    files = []
    for item in resources:
        body = materialize(item.artifact_ref)
        if (type(body) is not bytes or len(body) != item.artifact_ref.byte_count
                or hashlib.sha256(body).hexdigest() != item.artifact_ref.digest):
            raise ValueError('materialized resource identity differs from its approved reference')
        body.decode('utf-8')
        files.append((item.relative_path, body))
    manifest = {'record_type': 'opencode_instance_plan/v2', 'backend': 'opencode',
                'activation_ref': selection.activation_ref, 'step_ref': selection.step_ref,
                'core_bundle_id': core.bundle_id, 'core_version': core.version, 'core_digest': core.digest,
                'grant_digest': grant.digest, 'grant_authority_ref': grant.authority_ref,
                'selection_evidence_ref': selection.selection_evidence_ref,
                'core_resources': [item.card() for item in core.resources],
                'selected_resources': [by_ref[ref].card() for ref in refs],
                'tools': list(tools), 'permissions': {'*': 'deny', **{name: 'allow' for name in tools}},
                'native_runtime_replaced': False, 'fresh_session_required': True,
                'resource_selection_is_not_promotion': True}
    return CompiledInstance(canonical_json(manifest), tuple(files))


def run_optional(selection, native, prepare_opencode, invoke_opencode):
    """Keep the native call path lazy and unchanged when no harness is selected."""
    if type(selection) is not InstanceSelection:
        raise TypeError('a typed instance selection is required')
    if selection.backend == 'native':
        return native()
    return invoke_opencode(prepare_opencode())
