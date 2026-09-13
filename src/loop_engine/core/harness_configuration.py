"""Load an explicit host-owned harness embodiment configuration.

Discovery reads bounded passive data and imports no third-party package.
Only the existing registry and canonical semantic binding can execute it.
"""
from __future__ import annotations

import json
from pathlib import Path

from .external_harness import HarnessRegistry
from .harness_execution_contracts import valid_harness_id
from .harness_process import HarnessProcessSpec
from .harness_semantic import GatewayHarnessProcessAdapter, HarnessSemanticBinding
from .harness_fallback import HarnessFallbackPolicy
from .harness_selection_records import HarnessSelectionPolicy


def load_harness_fallback_binding(paths: tuple[str, ...], *, policy: HarnessFallbackPolicy,
                                  work_root: str, socket_directory: str,
                                  artifact_store=None, selection_policy=None) -> HarnessSemanticBinding:
    """Read exact host configurations in a typed fallback order, without execution.

    Reading configuration is passive. No adapter is installed or launched,
    and none of its native tools, plugins or credentials are authorized here.
    """
    if not isinstance(policy, HarnessFallbackPolicy):
        raise TypeError('an explicit typed fallback policy is required')
    if type(paths) not in (tuple, list) or len(paths) != len(policy.harness_ids):
        raise ValueError('one exact configuration is required for each alternative')
    adapters = []
    for path, harness_id in zip(paths, policy.harness_ids):
        selected = load_harness_binding(path, work_root=work_root,
            socket_directory=socket_directory, artifact_store=artifact_store,
            expected_id=harness_id)
        adapters.append(selected.registry.get(harness_id))
    return HarnessSemanticBinding(policy.harness_ids[0], HarnessRegistry(adapters),
        work_root, artifact_store=artifact_store, socket_directory=socket_directory,
        fallback_policy=policy,selection_policy=selection_policy)


def load_harness_binding(path: str, *, work_root: str, socket_directory: str,
                         artifact_store=None, expected_id: str = '',selection_policy=None) -> HarnessSemanticBinding:
    """Resolve one explicit config file; no identifier implies installation."""
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
    spec = HarnessProcessSpec(value['harness_id'], value['package_version'],
                              tuple(value['command_prefix']), tuple(value['read_only_paths']),
                              value['style'])
    registry = HarnessRegistry((GatewayHarnessProcessAdapter(spec),))
    return HarnessSemanticBinding(value['harness_id'], registry, work_root,
                                   artifact_store=artifact_store,
                                   socket_directory=socket_directory,selection_policy=selection_policy)


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
