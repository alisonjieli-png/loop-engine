"""Bounded topic rotation and registry paging for the existing source scout.

Pure scheduling helpers. They grant no effects and write no catalogue items.
The caller saves a complete run report before advancing this rebuildable state.
"""
import copy

import collector
import extended_sources


def validate(configuration):
    fields = {'record_type', 'per_run', 'topics'}
    if type(configuration) is not dict or set(configuration) != fields or configuration['record_type'] != 'source_discovery_rotation/v1':
        raise ValueError('unsupported_coverage_configuration')
    if type(configuration['per_run']) is not int or not 1 <= configuration['per_run'] <= 2:
        raise ValueError('coverage_request_bound')
    topics = configuration['topics']
    if type(topics) is not list or not configuration['per_run'] <= len(topics) <= 200:
        raise ValueError('coverage_topic_bound')
    identities = set()
    for topic in topics:
        extended_sources.validate({'record_type': extended_sources.TYPE, 'maximum_requests': 1,
                                   'timeout_seconds': 12, 'sources': [topic]})
        if topic['kind'] != 'github_search' or topic['id'] in identities:
            raise ValueError('coverage_topic_identity')
        if set(topic['query']) != {'q', 'sort', 'order', 'per_page'} or len(topic['query']['q']) > 256:
            raise ValueError('coverage_query_scope')
        identities.add(topic['id'])
    return configuration


def _cursor(value):
    if value is not None and (type(value) is not str or not 1 <= len(value) <= 4096 or any(ord(c) < 32 for c in value)):
        raise ValueError('invalid_registry_cursor')
    return value


def prepare(rotation, extra, previous):
    """Resolve one explicit plan without writing or consuming a request."""
    validate(rotation)
    extended_sources.validate(extra)
    original_ids = {s['id'] for s in extra['sources']}
    if original_ids.intersection(s['id'] for s in rotation['topics']):
        raise ValueError('coverage_source_collision')
    digest = collector.sha(collector.canonical({'rotation': rotation, 'extra': extra}))
    registries = {s['id'] for s in extra['sources'] if s['kind'] == 'mcp_registry'}
    for source in extra['sources']:
        if source['kind'] == 'mcp_registry' and 'cursor' in source['query']:
            raise ValueError('cursor_must_be_owned_by_coverage_state')
    if previous is None:
        previous = {'record_type': 'source_discovery_coverage_state/v1', 'configuration_sha256': digest,
                    'runs': 0, 'topic_offset': 0, 'registry_cursors': dict.fromkeys(registries),
                    'last_findings': [], 'complete_catalogue': False}
    fields = {'record_type', 'configuration_sha256', 'runs', 'topic_offset', 'registry_cursors', 'last_findings', 'complete_catalogue'}
    if type(previous) is not dict or set(previous) != fields or previous['record_type'] != 'source_discovery_coverage_state/v1':
        raise ValueError('unsupported_coverage_state')
    if previous['configuration_sha256'] != digest:
        raise ValueError('coverage_configuration_changed')
    if type(previous['runs']) is not int or previous['runs'] < 0 or type(previous['topic_offset']) is not int or not 0 <= previous['topic_offset'] < len(rotation['topics']):
        raise ValueError('invalid_coverage_position')
    if type(previous['registry_cursors']) is not dict or set(previous['registry_cursors']) != registries:
        raise ValueError('invalid_registry_state')
    for cursor in previous['registry_cursors'].values():
        _cursor(cursor)
    if previous['complete_catalogue'] is not False or type(previous['last_findings']) is not list or any(type(f) is not str or len(f) > 200 for f in previous['last_findings']):
        raise ValueError('invalid_coverage_evidence')
    config = copy.deepcopy(extra)
    for source in config['sources']:
        if source['id'] in registries and previous['registry_cursors'][source['id']] is not None:
            source['query']['cursor'] = previous['registry_cursors'][source['id']]
    offset = previous['topic_offset']
    selected = [copy.deepcopy(rotation['topics'][(offset + i) % len(rotation['topics'])]) for i in range(rotation['per_run'])]
    config['sources'].extend(selected)
    extended_sources.validate(config)
    proposal = {'completed_state': copy.deepcopy(previous), 'selected_topic_ids': [s['id'] for s in selected],
                'next_topic_offset': (offset + rotation['per_run']) % len(rotation['topics'])}
    return config, proposal


def complete(proposal, report):
    """Advance only from persisted outcomes; failures keep their registry page."""
    state = copy.deepcopy(proposal['completed_state'])
    state['runs'] += 1
    state['topic_offset'] = proposal['next_topic_offset']
    findings = []
    for result in report['sources']:
        identity = result['source_id']
        if identity not in state['registry_cursors'] or result['outcome'] != 'ok':
            continue
        try:
            cursor = _cursor(result['coverage']['next_cursor'])
        except (KeyError, ValueError):
            findings.append(identity + ':invalid_cursor_kept_previous_page')
            continue
        if cursor is not None and cursor == state['registry_cursors'][identity]:
            findings.append(identity + ':cursor_did_not_advance')
            # Record the broken cursor and begin a fresh bounded traversal next run.
            cursor = None
        state['registry_cursors'][identity] = cursor
    state['last_findings'] = findings
    return state
