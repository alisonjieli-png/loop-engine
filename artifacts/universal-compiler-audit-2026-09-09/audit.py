"""Read-only discovery and evidence projections for this dated audit.

This is an audit script, not a runtime, capability registry, or migration.
It never imports a peer, evaluates its code, or reads runtime prompt bodies.
Only the new output directory is writable through this script.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from collections import Counter, defaultdict

ROOT = Path('/home/username/loop-engine')
LAB = Path('/home/username/solver-lab')
HERE = Path(__file__).resolve().parent
EXCLUDED = {
    '.git', '.venv', 'venv', 'node_modules', '__pycache__', '.cache', '.work',
    'runs', 'results', 'outputs', 'artifacts', 'evidence', 'dist', 'build',
    '.pytest_cache', '.mypy_cache', '.ruff_cache', '.aider', '.opencode',
    'environment', 'datasets', 'data-cache', 'playwright-report', 'test-results',
}
CODE_SUFFIXES = {'.py', '.js', '.ts', '.mjs', '.cjs', '.tsx', '.jsx', '.sh'}
SIGNALS = {
    'provider_or_model': ('ModelGateway', 'chat.completions', 'ollama', 'model_call'),
    'harness': ('opencode', 'pi-coding-agent', 'HarnessRunRequest'),
    'context': ('ContextFrame', 'LLMWorkPacket', 'context_manifest', 'hydrate'),
    'reuse': ('fingerprint', 'CapabilityResolver', 'StepMemory', 'distill'),
    'solution_graph': ('LoopGraphDefinition', 'Canvas', 'compile_solution'),
    'verification': ('verify', 'verifier', 'self_test', 'pytest'),
    'effects_and_storage': ('subprocess', 'write_text', 'sqlite3', 'Approval'),
    'recovery': ('checkpoint', 'retry', 'backtrack', 'incumbent'),
    'triggers': ('TriggerEnvelope', 'scheduler', 'SavedIntent', 'percolat'),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def command(args: list[str], cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True,
                            timeout=30, env={'PATH': os.environ['PATH'], 'GIT_OPTIONAL_LOCKS': '0'})
    return result.stdout.strip() if result.returncode == 0 else f'UNAVAILABLE:{result.returncode}'


def git_snapshot(path: Path) -> dict:
    if not path.exists():
        return {'path': str(path), 'exists': False}
    status = command(['git', 'status', '--porcelain=v1', '--untracked-files=normal'], path)
    return {'path': str(path), 'exists': True,
            'head': command(['git', 'rev-parse', 'HEAD'], path),
            'branch': command(['git', 'branch', '--show-current'], path),
            'worktrees': command(['git', 'worktree', 'list', '--porcelain'], path),
            'status': status.splitlines(), 'owner': None,
            'ownership_state': 'unknown; no ownership inferred from process or mtime'}


def source_index(path: Path) -> tuple[list[dict], list[dict]]:
    entries, exclusions = [], []
    for base, dirs, files in os.walk(path, followlinks=False):
        current = Path(base)
        kept = []
        for name in sorted(dirs):
            child = current / name
            if name in EXCLUDED or child.is_symlink():
                exclusions.append({'path': str(child), 'reason': 'excluded runtime/dependency directory or symlink'})
            else:
                kept.append(name)
        dirs[:] = kept
        for name in sorted(files):
            file = current / name
            if file.suffix not in CODE_SUFFIXES or file.is_symlink():
                continue
            try:
                before = file.stat()
                if before.st_size > 2_000_000:
                    exclusions.append({'path': str(file), 'reason': 'source over 2 MB'})
                    continue
                body = file.read_bytes()
                after = file.stat()
                text = body.decode('utf-8')
                declarations = []
                parse_error = None
                if file.suffix == '.py':
                    try:
                        tree = ast.parse(text)
                        declarations = [{'name': n.name, 'line': n.lineno,
                                         'kind': type(n).__name__}
                                        for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
                    except SyntaxError as error:
                        parse_error = {'line': error.lineno, 'reason': error.msg}
                entries.append({'path': str(file), 'relative_path': str(file.relative_to(path)),
                                'sha256': digest(body), 'bytes': len(body), 'mtime_ns': after.st_mtime_ns,
                                'stable_during_read': (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                                'declarations': declarations, 'parse_error': parse_error,
                                'lexical_signals_only': [k for k, needles in SIGNALS.items() if any(n in text for n in needles)]})
            except (OSError, UnicodeError) as error:
                exclusions.append({'path': str(file), 'reason': type(error).__name__})
    return entries, exclusions


def file_ref(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        return {'path': str(path), 'exists': False}
    data = path.read_bytes()
    return {'path': str(path), 'exists': True, 'sha256': digest(data), 'bytes': len(data)}


def write_new(out: Path, name: str, data: object) -> None:
    with (out / name).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def inventory(out: Path) -> None:
    out.mkdir(parents=False, exist_ok=False)
    import yaml
    architecture = yaml.safe_load((ROOT / 'architecture.yaml').read_text())
    interactions = yaml.safe_load((ROOT / 'src/loop_engine/data/component_interactions.yaml').read_text())
    workspace = json.loads((LAB / 'workspace.json').read_text())
    catalog = json.loads((ROOT / 'embodiments/catalog.json').read_text())
    roots = [ROOT] + [LAB / x['path'] for x in workspace['projects']]
    # Independently developed, currently unindexed peers are still preserved.
    roots += [p for p in sorted(LAB.iterdir()) if p.is_dir() and (p / 'embodiment.json').is_file() and p not in roots]
    all_entries, exclusions, folders, ledger = [], [], [], []
    for root in roots:
        print(json.dumps({'scan': str(root)}), flush=True)
        entries, excluded = source_index(root)
        all_entries.extend(entries)
        exclusions.extend(excluded)
        manifests = [file_ref(root / name) for name in ('README.md', 'embodiment.json', 'provenance.json', 'project.py', 'run.py', 'pyproject.toml', 'package.json')]
        folders.append({'path': str(root), 'source_files': len(entries), 'manifests': manifests,
                        'top_level': [{'name': p.name, 'kind': 'symlink' if p.is_symlink() else 'directory' if p.is_dir() else 'file'} for p in sorted(root.iterdir())],
                        'signal_counts_not_capability_proof': dict(Counter(s for e in entries for s in e['lexical_signals_only'])),
                        'semantic_parity_review': 'incomplete', 'owner': None})
        ledger.append({'capability_id': 'embodiment:' + ('canonical-loop-engine' if root == ROOT else root.name),
                       'source_embodiment': str(root), 'source_paths': [x for x in manifests if x['exists']],
                       'semantic_purpose': None, 'inputs': None, 'outputs': None, 'effects': None,
                       'dependencies': None, 'models': None, 'tools': None, 'memory_dependencies': None,
                       'context_dependencies': None, 'verification': None, 'observability': None,
                       'security_boundary': None, 'evidence': [], 'maturity': 'inventory_only_not_qualification',
                       'known_failures': None, 'canonical_target': None,
                       'consolidation_disposition': 'KEEP_CANONICAL' if root == ROOT else 'EXPERIMENTAL',
                       'disposition_status': 'provisional_preservation_only', 'replacement_refs': [],
                       'parity_tests': [], 'translation_loss': None, 'owner': None,
                       'notes': ['No deletion authorized. Independent peers are not automatically Loop Engine runtime adapters. Null means not reviewed, never absent.']})
    for item in catalog['embodiments']:
        ledger.append({'capability_id': 'canonical-arrangement:' + item['id'],
                       'source_embodiment': str(ROOT / 'embodiments' / item['folder']),
                       'source_paths': [file_ref(ROOT / 'embodiments/catalog.json')],
                       'semantic_purpose': item['title'], 'benefit': item['benefit'],
                       'known_failures_and_limits': item['limitations'], 'maturity': item['status'],
                       'evidence_state': 'catalog_declaration_not_new_execution',
                       'consolidation_disposition': 'KEEP_ADAPTER', 'disposition_status': 'provisional_preservation_only',
                       'parity_tests': [], 'translation_loss': None, 'owner': None})
    for name, value in architecture.items():
        if isinstance(value, dict) and any(k in value for k in ('invariants', 'verified_scope', 'maturity')):
            ledger.append({'capability_id': 'architecture:' + name,
                           'source_paths': [file_ref(ROOT / 'architecture.yaml')],
                           'source_section': name, 'declared_contract': value,
                           'evidence_state': 'architecture_declaration_not_new_execution',
                           'consolidation_disposition': 'KEEP_CANONICAL',
                           'disposition_status': 'preserve_existing_contract_not_parity_approval',
                           'parity_tests': [], 'translation_loss': None, 'owner': None})
    groups = defaultdict(list)
    for entry in all_entries:
        groups[entry['sha256']].append(entry['path'])
    duplicates = [{'sha256': sha, 'paths': paths, 'interpretation': 'byte_identical_only; callers, contracts, environment, and ownership not equivalent by implication'}
                  for sha, paths in groups.items() if len(paths) > 1]
    references = [Path('/home/username') / name for name in ('overnight', 'new_overnight_build', 'speculative_prompting', 'vigil', 'taedri.dev')]
    snapshot = {'record_type': 'local_audit_snapshot/v1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'repositories': [git_snapshot(p) for p in [ROOT] + references],
                'processes_no_arguments_or_environment': command(['ps', '-eo', 'pid,ppid,etime,comm'], ROOT).splitlines(),
                'authority_files': [file_ref(ROOT / p) for p in ('AGENTS.md', 'README.md', 'architecture.yaml', 'terminology.yaml', 'docs/architecture/CONSTITUTION.md')],
                'scope': {'roots': [str(p) for p in roots], 'excluded_directory_names': sorted(EXCLUDED),
                          'other_original_repositories': 'git metadata only; source not semantically re-audited',
                          'filesystem_wide_audit': False, 'snapshot_atomicity': 'per-file read checks, not a transactional filesystem snapshot'}}
    write_new(out, 'snapshot.json', snapshot)
    write_new(out, 'folders.json', folders)
    write_new(out, 'source-index.json', all_entries)
    write_new(out, 'exclusions.json', exclusions)
    write_new(out, 'byte-overlaps.json', duplicates)
    write_new(out, 'capability-preservation-ledger.json', {'record_type': 'capability_preservation_audit/v1', 'authoritative_runtime_registry': False, 'semantic_audit_complete': False, 'records': ledger})
    write_new(out, 'information-transfer.json', {'record_type': 'information_transfer_audit/v1', 'source': file_ref(ROOT / 'src/loop_engine/data/component_interactions.yaml'), 'declared_interactions': interactions, 'new_dynamic_execution_proof': False})
    write_new(out, 'summary.json', {'roots': len(roots), 'source_files': len(all_entries), 'ledger_records': len(ledger), 'byte_identical_groups': len(duplicates), 'unstable_reads': sum(not e['stable_during_read'] for e in all_entries), 'semantic_audit_complete': False})
    print((out / 'summary.json').read_text())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['inventory'])
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    target = Path(args.out).absolute()
    if target.parent != HERE or target.is_symlink():
        raise SystemExit('Output must be a new immediate child of this audit directory')
    inventory(target)
