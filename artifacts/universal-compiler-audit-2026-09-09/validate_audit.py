"""Check this report's links, evidence joins, and preservation claims."""
import hashlib
import json
from pathlib import Path
import re
import argparse

HERE = Path(__file__).resolve().parent

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--final', action='store_true')
    args = parser.parse_args()
    checks = []
    def check(name, result, detail=''):
        checks.append({'name': name, 'passed': bool(result), 'detail': detail})
    for path in sorted(HERE.glob('*.json')):
        json.loads(path.read_text())
        check('parse:' + path.name, True)
    report = (HERE / 'REVIEW.md').read_text()
    for _, target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', report):
        if target.startswith('https://'):
            continue
        check('link:' + target, (HERE / target.split('#')[0]).exists())
    ledger = json.loads((HERE / 'snapshot-01/capability-preservation-ledger.json').read_text())
    ids = [x['capability_id'] for x in ledger['records']]
    check('unique capability inventory identities', len(ids) == len(set(ids)))
    check('no automatic removal disposition', not any(x['consolidation_disposition'] == 'REMOVE_AFTER_PARITY' for x in ledger['records']))
    check('semantic review explicitly incomplete', ledger['semantic_audit_complete'] is False)
    families = json.loads((HERE / 'feature-preservation.json').read_text())
    check('all 15 requested capability families preserved', len(families['families']) == 15 and not families['deletions'])
    deliverables = json.loads((HERE / 'deliverable-status.json').read_text())
    check('20 deliverables accounted for', {x['id'] for x in deliverables['deliverables']} == set(range(1,21)))
    for row in deliverables['deliverables']:
        check('deliverable artifact:' + str(row['id']), (HERE / row['artifact']).is_file())
    for row in json.loads((HERE / 'cold-warm-proof.json').read_text())['pairs']:
        for kind in ('cold', 'warm'):
            path = Path(row[kind + '_record'])
            check(row['peer'] + ':' + kind + ':record digest', hashlib.sha256(path.read_bytes()).hexdigest() == row[kind + '_record_sha256'])
            value = json.loads(path.read_text())
            check(row['peer'] + ':' + kind + ':whole gate', value['whole_gate']['exit_code'] == 0 and value['whole_gate']['integrity_ok'])
        check(row['peer'] + ':warm no attempts', row['warm_harness_instances'] == 0 and row['all_warm_method_gates_pass'])
        check(row['peer'] + ':export replay', row['export_replay_exit'] == 0)
    snapshot = json.loads((HERE / 'snapshot-01/snapshot.json').read_text())
    for ref in snapshot['authority_files']:
        check('preserved authority:' + ref['path'], hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest() == ref['sha256'])
    # Source files already present at the snapshot must remain unchanged. New
    # audit files are deliberately outside that source index.
    changed = []
    for row in json.loads((HERE / 'snapshot-01/source-index.json').read_text()):
        if row['path'].startswith('/home/username/loop-engine/'):
            path = Path(row['path'])
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                changed.append(str(path))
    check('canonical indexed source preserved', not changed, changed)
    check('no decorative dash prose', '\u2014' not in report and '\u2013' not in report)
    result = {'record_type': 'audit_deliverable_checks/v1', 'checks': checks,
              'passed': sum(c['passed'] for c in checks), 'total': len(checks),
              'all_passed': all(c['passed'] for c in checks)}
    with (HERE / ('audit-validation-final.json' if args.final else 'audit-validation.json')).open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'checks'}))
    print(json.dumps([x for x in checks if not x['passed']]))
