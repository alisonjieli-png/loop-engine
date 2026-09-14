"""Load an explicit host-owned harness embodiment configuration.

Discovery reads bounded passive data and imports no third-party package.
Only the existing registry and canonical semantic binding can execute it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .external_harness import HarnessAdapterInfo, HarnessRegistry, HarnessRunResult
from .harness_execution_contracts import valid_harness_id
from .harness_process import HarnessProcessError, HarnessProcessSpec
from .harness_semantic import GatewayHarnessProcessAdapter, HarnessSemanticBinding
from .harness_fallback import HarnessFallbackPolicy
from .harness_selection_records import HarnessSelectionPolicy


#: The refusals a process spec raises when the software it names is not
#: installed here, as opposed to a malformed declaration. Only these may be
#: registered as an unavailable adapter; everything else stays a refusal.
_INSTALLATION_REFUSALS = (
    "harness executable is unavailable",
    "software mount is absent or too broad",
    "installed harness software changed after binding",
)


@dataclass(frozen=True)
class UnavailableHarnessAdapter:
    """A harness whose configuration was read but whose software is not
    installed on this host.

    It registers with ``available=False`` and the exact reason, so a fallback
    order that names it moves on with ``adapter_unavailable`` (the failure
    kind the fallback policy already knows) instead of failing the whole
    assignment before any attempt. It never runs anything: the executor
    refuses on ``info().available`` before ``run`` is reached.
    """

    harness_id: str
    package_version: str
    reason: str

    def info(self) -> HarnessAdapterInfo:
        return HarnessAdapterInfo(
            harness_id=self.harness_id,
            adapter_version="unavailable+" + hashlib.sha256(self.reason.encode()).hexdigest()[:16],
            package_name=self.harness_id, package_version=self.package_version,
            available=False, availability_reason=self.reason,
            limitations=("not installed on this host: " + self.reason,))

    def run(self, request, services) -> HarnessRunResult:
        return HarnessRunResult(
            request.request_id, request.harness_id, "unavailable",
            error_code="adapter_unavailable", error="harness adapter is unavailable",
            adapter_version=self.info().adapter_version,
            provider_id=request.provider_id, model_id=request.model_id)


def load_harness_fallback_binding(paths: tuple[str, ...], *, policy: HarnessFallbackPolicy,
                                  work_root: str, socket_directory: str,
                                  artifact_store=None, selection_policy=None,
                                  allow_unavailable: bool = False) -> HarnessSemanticBinding:
    """Read exact host configurations in a typed fallback order, without execution.

    Reading configuration is passive. No adapter is installed or launched,
    and none of its native tools, plugins or credentials are authorized here.
    With ``allow_unavailable`` an alternative whose software is not installed
    here is registered as unavailable rather than refusing the whole order.
    """
    if not isinstance(policy, HarnessFallbackPolicy):
        raise TypeError('an explicit typed fallback policy is required')
    if type(paths) not in (tuple, list) or len(paths) != len(policy.harness_ids):
        raise ValueError('one exact configuration is required for each alternative')
    adapters = []
    for path, harness_id in zip(paths, policy.harness_ids):
        selected = load_harness_binding(path, work_root=work_root,
            socket_directory=socket_directory, artifact_store=artifact_store,
            expected_id=harness_id, allow_unavailable=allow_unavailable)
        adapters.append(selected.registry.get(harness_id))
    return HarnessSemanticBinding(policy.harness_ids[0], HarnessRegistry(adapters),
        work_root, artifact_store=artifact_store, socket_directory=socket_directory,
        fallback_policy=policy,selection_policy=selection_policy)


def load_harness_binding(path: str, *, work_root: str, socket_directory: str,
                         artifact_store=None, expected_id: str = '',selection_policy=None,
                         allow_unavailable: bool = False) -> HarnessSemanticBinding:
    """Resolve one explicit config file; no identifier implies installation.

    A declaration whose software is not installed here refuses, as before;
    with ``allow_unavailable`` it is registered as an
    :class:`UnavailableHarnessAdapter` instead, so a campaign can name every
    registered harness in a fallback order on a host that has installed only
    some of them and record the rest as unavailable at attempt time. A
    malformed declaration refuses either way.
    """
    source = Path(path)
    if (not source.is_absolute() or not source.is_file() or source.is_symlink()
            or source.stat().st_size > 1024 * 1024):
        raise ValueError('harness config must be one bounded absolute regular file')

    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate harness configuration key')
            value[key] = item
        return value

    value = json.loads(source.read_text(encoding='utf-8'), object_pairs_hook=unique)
    required = {'schema_version', 'harness_id', 'package_version', 'style',
                'command_prefix', 'read_only_paths'}
    if (type(value) is not dict or set(value) != required
            or type(value['schema_version']) is not int or value['schema_version'] != 1):
        raise ValueError('unsupported harness configuration fields/version')
    if not valid_harness_id(value['harness_id']) or expected_id and expected_id != value['harness_id']:
        raise ValueError('harness configuration identity mismatch')
    for name in ('command_prefix', 'read_only_paths'):
        if type(value[name]) is not list or any(type(part) is not str for part in value[name]):
            raise ValueError('harness command and software paths must be lists of text')
    try:
        spec = HarnessProcessSpec(value['harness_id'], value['package_version'],
                                  tuple(value['command_prefix']), tuple(value['read_only_paths']),
                                  value['style'])
    except HarnessProcessError as exc:
        if not allow_unavailable or str(exc) not in _INSTALLATION_REFUSALS:
            raise
        registry = HarnessRegistry((UnavailableHarnessAdapter(
            value['harness_id'], str(value['package_version']), str(exc)),))
        return HarnessSemanticBinding(value['harness_id'], registry, work_root,
                                      artifact_store=artifact_store,
                                      socket_directory=socket_directory,
                                      selection_policy=selection_policy)
    registry = HarnessRegistry((GatewayHarnessProcessAdapter(spec),))
    return HarnessSemanticBinding(value['harness_id'], registry, work_root,
                                   artifact_store=artifact_store,
                                   socket_directory=socket_directory,selection_policy=selection_policy)


def load_layered_binding(path: str, *, assignment_ref: str, fallback_policy=None):
    """Read one host-authored layering declaration for one assignment.

    The file holds the initial composition, the ordered fallbacks, and the
    control policy as their own records (core.harness_layering); the outer
    fallback policy is the one this run already holds, so the file cannot
    smuggle a different one, and the assignment reference comes from the
    caller for the same reason. Reading is passive: nothing is launched and
    no native control is enabled. The returned binding is the same validated
    record a caller could have built in code, and `HarnessSemanticBinding`
    applies its own refusals when the binding is supplied as `layering`.
    """
    from .harness_layering import (
        CompositionFallback, LayeredHarnessBinding, NativeControlPolicy, WrapperComposition)
    source = Path(path)
    if (not source.is_absolute() or not source.is_file() or source.is_symlink()
            or source.stat().st_size > 1024 * 1024):
        raise ValueError('layering declaration must be one bounded absolute regular file')

    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate layering declaration key')
            value[key] = item
        return value

    value = json.loads(source.read_text(encoding='utf-8'), object_pairs_hook=unique)
    required = {'schema_version', 'initial', 'fallbacks', 'control_policy'}
    if (type(value) is not dict or set(value) != required
            or type(value['schema_version']) is not int or value['schema_version'] != 1):
        raise ValueError('unsupported layering declaration fields/version')
    if type(value['fallbacks']) is not list:
        raise ValueError('layering fallbacks must be a list of records')
    return LayeredHarnessBinding(
        assignment_ref, WrapperComposition.from_dict(value['initial']),
        NativeControlPolicy.from_dict(value['control_policy']),
        tuple(CompositionFallback.from_dict(item) for item in value['fallbacks']),
        fallback_policy)


def load_harness_selection_policy(path: str) -> HarnessSelectionPolicy:
    """Read one explicit host-reviewed policy; loading never dispatches a model."""
    source=Path(path)
    if (not source.is_absolute() or source.is_symlink() or not source.is_file()
            or source.stat().st_size>4*1024*1024):
        raise ValueError('harness selection policy must be one bounded absolute regular file')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate policy key')
            result[key]=value
        return result
    return HarnessSelectionPolicy.from_dict(json.loads(source.read_text(encoding='utf-8'),object_pairs_hook=unique))
