"""Use the existing sandbox verifier for the original wikilink candidate."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile

SHARED = Path('/home/username/loop-engine/artifacts')
sys.path.insert(0, str(SHARED/'codex-component-supply-2026-09-23/authored/authors'))
from verify_systems_packages import execute
from jsonschema import Draft202012Validator

BASE = Path(__file__).resolve().parents[1]
PACKAGE = BASE/'audit_wikilink_resolution'
MUTATIONS = {
    'first_ambiguous_note_is_incorrectly_selected': ('candidates.sort()', 'candidates.sort(); candidates = candidates[:1]'),
    'slash_path_uses_source_directory': ('if path[:-3] == key]', 'if path[:-3] == source_path.rsplit("/", 1)[0] + "/" + key]'),
    'fenced_code_becomes_active': ('if marker and not (marker[1][0] == "`"', 'if False and marker and not (marker[1][0] == "`"'),
    'even_escape_run_is_wrongly_hidden': ('return backslashes % 2 == 1', 'return backslashes > 0'),
    'unverified_fragment_claims_verification': ('"not_checked" if fragment_mark else "absent"', '"verified" if fragment_mark else "absent"'),
    'source_offset_becomes_utf8_bytes': ('"start": start, "end": end', '"start": len(source[:start].encode("utf-8")), "end": end'),
    'stale_source_digest_is_ignored': ('need(digest_text(value["expected_sha256"]) == digest, "source_digest_mismatch")', 'need(True)'),
    'repeated_cr_is_silently_stripped': ('return source[start:end]', 'return source[start:end].rstrip("\\r")'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--mutants', action='store_true')
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError('preserve_existing_report')
    script = PACKAGE/'tools/audit_wikilink_resolution.py'
    source = script.read_text()
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(x.name for x in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module)
    if not imported <= {'json', 'sys', 'decimal', 'hashlib', 're'}:
        raise ValueError('undeclared_import')
    for kind in ('input', 'output'):
        Draft202012Validator.check_schema(json.loads((PACKAGE/f'contracts/{kind}.schema.json').read_text()))
    validator = Draft202012Validator(json.loads((PACKAGE/'contracts/output.schema.json').read_text()))
    cases = json.loads((PACKAGE/'verification/cases.json').read_text())
    with tempfile.TemporaryDirectory(prefix='baltor-wikilink-qa-', dir='/home/username/.le-ci-tmp') as folder:
        folder = Path(folder)
        checks = [execute(script, case, folder, validator) for case in cases]
        mutations = []
        if args.mutants:
            for name, (old, new) in MUTATIONS.items():
                if source.count(old) != 1:
                    raise ValueError('mutation_anchor_not_unique:'+name)
                mutant = folder/'mutant.py'
                mutant.write_text(source.replace(old, new, 1))
                failed = [case['name'] for case in cases if not execute(mutant, case, folder, validator)['passed']]
                mutations.append({'name': name, 'detected': bool(failed), 'failing_cases': failed})
    report = {'record_type': 'wikilink_author_sandbox_qa/v1', 'checks': checks, 'mutations': mutations,
              'passed': all(c['passed'] for c in checks) and all(m['detected'] for m in mutations),
              'payloads': {str(p.relative_to(PACKAGE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in PACKAGE.rglob('*') if p.is_file()},
              'sandbox': 'existing bwrap no-network/clearenv/read-only exact mounts; 2 CPU seconds, 256 MiB, 4 wall seconds',
              'approved': False, 'native_client_qualified': False, 'provider_calls': 0}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x') as stream:
        json.dump(report, stream, indent=2); stream.write('\n')
    print(json.dumps({'cases': len(checks), 'passed': report['passed'], 'failures': [c['name'] for c in checks if not c['passed']],
                      'mutants': len(mutations), 'undetected': [m['name'] for m in mutations if not m['detected']]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
