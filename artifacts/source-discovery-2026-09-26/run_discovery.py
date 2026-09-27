"""Run the existing watcher and extended discovery under one bounded timer."""
import argparse
import fcntl
import json
import os
from pathlib import Path

import collector
import coverage_rotation
import extended_sources


def run(core_config, extra_config, state, rotation=None):
    collector.validate_config(core_config)
    extended_sources.validate(extra_config)
    if core_config['maximum_requests'] + extra_config['maximum_requests'] > 20:
        raise ValueError('combined_request_bound')
    state = state.absolute()
    if state.resolve() != state:
        raise ValueError('state_not_plain')
    descriptor = os.open(state / 'combined.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'status': 'already_running'}
        coverage_path = state / 'coverage-state.json'
        proposal = None
        if rotation is not None:
            if coverage_path.is_symlink():
                raise ValueError('coverage_state_not_plain')
            previous = None
            if coverage_path.exists():
                if not coverage_path.is_file() or coverage_path.stat().st_size > 65536:
                    raise ValueError('coverage_state_size')
                previous = json.loads(coverage_path.read_bytes())
            extra_config, proposal = coverage_rotation.prepare(rotation, extra_config, previous)
        core = collector.run(core_config, state)
        parent = state / 'extended-runs'
        if parent.is_symlink():
            raise ValueError('extended_state_not_plain')
        parent.mkdir(exist_ok=True, mode=0o700)
        run_id = collector.now().replace(':', '').replace('-', '') + '-' + str(os.getpid())
        folder = parent / run_id
        extra = extended_sources.run(extra_config, folder)
        if proposal is not None:
            # Persist the resolved plan and outcome before advancing the pointer.
            collector.write_json(folder / 'coverage-plan.json', proposal)
            completed = coverage_rotation.complete(proposal, extra)
            collector.write_json(folder / 'coverage-completed.json', completed)
        result = {'record_type': 'combined_source_discovery_run/v2' if proposal is not None else 'combined_source_discovery_run/v1',
                  'finished_at': collector.now(), 'core_run': core, 'extended_report': str(folder / 'report.json'),
                  'extended_observations': extra['observations'], 'extended_families': extra['families'],
                  'status': 'complete' if core['status'] == extra['status'] == 'complete' else 'partial',
                  'maximum_requests': core_config['maximum_requests'] + extra_config['maximum_requests'],
                  'model_calls': 0, 'component_approvals': 0, 'publications': 0}
        if proposal is not None:
            result['coverage'] = {'selected_topic_ids': proposal['selected_topic_ids'],
                                  'completed_runs': completed['runs'], 'complete_catalogue': False,
                                  'findings': completed['last_findings']}
        collector.write_json(folder / 'combined-report.json', result)
        if proposal is not None:
            collector.write_json(coverage_path, completed)
        collector.write_json(state / 'combined-latest.json', result)
        return result
    finally:
        os.close(descriptor)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--core-configuration', type=Path, required=True)
    p.add_argument('--extended-configuration', type=Path, required=True)
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--rotation-configuration', type=Path)
    p.add_argument('--authorize-network-reads', action='store_true')
    p.add_argument('--authorize-local-writes', action='store_true')
    a = p.parse_args()
    core = collector.validate_config(json.loads(a.core_configuration.read_bytes()))
    extra = extended_sources.validate(json.loads(a.extended_configuration.read_bytes()))
    rotation = coverage_rotation.validate(json.loads(a.rotation_configuration.read_bytes())) if a.rotation_configuration else None
    if not (a.authorize_network_reads and a.authorize_local_writes):
        print(json.dumps({'preview': True, 'maximum_requests': core['maximum_requests'] + extra['maximum_requests']}))
    else:
        print(json.dumps(run(core, extra, a.state, rotation)))
