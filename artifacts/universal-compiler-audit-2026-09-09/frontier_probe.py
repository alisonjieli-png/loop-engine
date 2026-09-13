"""Read-only behavioral probes of the latest separate frontier implementation."""
import importlib.util
import hashlib
import json
from pathlib import Path
import sys

SOURCE = Path('/home/username/new_overnight_build/poc/frontier.py')
HERE = Path(__file__).resolve().parent

if __name__ == '__main__':
    spec = importlib.util.spec_from_file_location('audited_frontier', SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    findings = []
    item = module.Item('x', module.Kind.QUESTION, 'Need a source', module.Status.VERIFIED,
                       module.Horizon.SHORT, evidence_refs=('',))
    findings.append({'case': 'empty_reference_member', 'observed_status': item.status.value,
                     'finding': 'A nonempty tuple containing an empty string satisfies evidence presence. Reference identity and verifier authority are not established.'})
    frontier = module.Frontier('audit-only')
    question = module.question('Which cutoff applies?')
    frontier.add(question)
    frontier.snapshot()
    frontier.resolve(question.item_id, module.Status.ANSWERED, evidence=('unresolved:made-up',))
    frontier.snapshot()
    findings.append({'case': 'unresolved_evidence_reference', 'observed_status': frontier.snapshots[-1].items[0].status.value,
                     'finding': 'An arbitrary string changes status. No evidence resolver is consulted by this record mechanism.'})
    frontier.snapshots[-1].items = ()
    findings.append({'case': 'last_snapshot_mutation', 'chain_intact': frontier.chain_intact(),
                     'finding': 'Adjacent parent hashes do not authenticate the mutable terminal snapshot; an independently anchored head and immutable history are needed.'})
    report = {'record_type': 'frontier_boundary_probe/v1', 'source': str(SOURCE),
              'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'source_revision_observed': 'ddfedccf4af205b0261941b2e0edf793864136a8',
              'source_modified': False, 'model_calls': 0, 'findings': findings,
              'interpretation': 'These are record/admission limitations, not evidence of a production exploit. This module is not wired into the inspected solver.'}
    with (HERE / 'frontier-probe.json').open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))
