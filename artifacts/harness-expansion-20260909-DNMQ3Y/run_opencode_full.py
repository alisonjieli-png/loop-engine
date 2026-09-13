"""Gated OpenCode public solve qualification and one authorized real run.

Run only after the parent explicitly confirms the shared-source freeze. All
real model inference is pinned by the public CLI to Ollama Cloud. Fixture
replies remain separately labeled and do not establish live model quality.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
REPO = Path('/home/username/loop-engine')
OUT = ROOT / 'full-live/opencode-escaped-01'
PYTHON = REPO / '.venv/bin/python'
TASK = REPO / 'embodiments/qualification/tasks/escaped_fields_tool.txt'
STDOUT = ROOT / 'full-live-opencode-escaped-01.json'
PROGRESS = ROOT / 'full-live-opencode-escaped-01.progress.jsonl'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def identities():
    paths = [path for boundary in ('core', 'code_nodes', 'loop', 'templates')
             for path in (REPO / 'src/loop_engine' / boundary).rglob('*.py')]
    paths += [REPO / 'src/loop_engine/solve_cli.py', REPO / 'src/loop_engine/__main__.py']
    paths += [Path(__file__), TASK, REPO / 'embodiments/opencode/harness.json',
              REPO / 'embodiments/opencode/runtime/opencode',
              REPO / 'devtools/embodiment_lab/full_solve_qualification.py',
              REPO / 'devtools/embodiment_lab/audit_harness_run.py',
              REPO / 'examples/22_product_quickstart/acceptance_oracles.py',
              REPO / 'examples/22_product_quickstart/run_acceptance.py']
    return {str(path.relative_to(REPO)): sha(path) for path in sorted(set(paths))}


def save(path, value):
    with path.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze-confirmed', action='store_true')
    args = parser.parse_args()
    if not args.freeze_confirmed:
        raise SystemExit('Parent source-freeze confirmation is required before these runs.')
    os.umask(0o077)
    if OUT.exists() or STDOUT.exists() or PROGRESS.exists():
        raise SystemExit('Refusing to overwrite an existing qualification or live-run record.')
    OUT.mkdir(parents=True)
    before = identities()
    manifest = {'record_type': 'opencode_complete_solve_allocation/v1',
                'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                'git_branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=REPO, text=True).strip(),
                'dirty_paths': subprocess.check_output(['git', 'status', '--short'], cwd=REPO, text=True),
                'source_identities_before': before, 'task': str(TASK), 'task_sha256': sha(TASK),
                'harness': 'opencode', 'provider': 'ollama_cloud', 'model': 'deepseek-v4-flash:0731',
                'max_model_calls': 45, 'max_passes': 4,
                'comparison_limit': 'Pi v2 used 30 model calls and 3 passes as allocation; this run uses 45 and 4, so not an allocation-controlled head-to-head',
                'scope': 'Complete public solve integration run, not a full-system benchmark',
                'source_freeze': 'parent_explicitly_confirmed'}
    save(OUT / 'allocation-and-source-before.json', manifest)
    environment = dict(os.environ)
    environment.update(PYTHONPATH=str(REPO / 'src'), PYTHONDONTWRITEBYTECODE='1',
                       TMPDIR=str(REPO / '.loop-engine-dev/harness-tmp'))
    # The exact public provider selection remains authoritative. Unrelated
    # provider keys are not needed by this run and never enter child harnesses.
    for name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OPENROUTER_API_KEY', 'MISTRAL_API_KEY',
                 'OPENCODE_GO_API_KEY', 'OPENCODE_ZEN_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY'):
        environment.pop(name, None)
    for name, control in (('fixture-positive', ''), ('fixture-wrong-math', 'wrong_math')):
        command = [str(PYTHON), str(REPO / 'devtools/embodiment_lab/full_solve_qualification.py'),
                   '--harness', 'opencode', '--case', 'a', '--out', str(OUT / name)]
        if control:
            command += ['--control', control]
        print(json.dumps({'phase': name, 'state': 'started', 'real_model_calls': 0}), flush=True)
        with (OUT / (name + '.stdout.json')).open('x') as stdout, (OUT / (name + '.stderr.log')).open('x') as stderr:
            proc = subprocess.run(command, cwd=REPO, env=environment, stdout=stdout, stderr=stderr)
        result_path = OUT / name / 'result.json'
        report = json.loads(result_path.read_text()) if result_path.exists() else {}
        independent = [row['report']['status'] for row in report.get('independent_verification', [])]
        passed = proc.returncode == 0 and report.get('all_passed') is True
        if control:
            passed = passed and 'failed' in independent
        print(json.dumps({'phase': name, 'passed': passed, 'exit_code': proc.returncode,
                          'terminal_code': report.get('terminal_code'), 'independent': independent}), flush=True)
        if not passed:
            save(OUT / 'prelive-refusal.json', {'phase': name, 'reason': 'fixture_gate_did_not_pass',
                                               'real_model_calls': 0, 'exit_code': proc.returncode})
            return 1
    if identities() != before:
        save(OUT / 'prelive-refusal.json', {'reason': 'source_identity_changed_before_live', 'real_model_calls': 0})
        return 1
    command = [str(PYTHON), '-m', 'loop_engine', 'solve', '--file', str(TASK), '--quickstart',
               '--compile-provider', 'ollama_cloud', '--model-id', 'deepseek-v4-flash:0731',
               '--embodiment', 'opencode', '--unattended', '--max-model-calls', '45', '--max-passes', '4',
               '--workspace', str(OUT / 'workspace'), '--runs-dir', str(OUT / 'runs'),
               '--format', 'json', '--quiet-model-io']
    save(OUT / 'live-command.json', {'argv': command, 'provider': 'ollama_cloud', 'model': 'deepseek-v4-flash:0731'})
    print(json.dumps({'phase': 'live-public-solve', 'state': 'started', 'stdout': str(STDOUT), 'progress': str(PROGRESS)}), flush=True)
    started = time.monotonic()
    with STDOUT.open('x') as stdout, PROGRESS.open('x') as stderr:
        proc = subprocess.run(command, cwd=REPO, env=environment, stdout=stdout, stderr=stderr)
    after = identities()
    save(OUT / 'process-completion.json', {'exit_code': proc.returncode, 'elapsed_seconds': time.monotonic()-started,
         'source_identities_unchanged': before == after, 'source_identities_after': after})
    print(json.dumps({'phase': 'live-public-solve', 'state': 'finished', 'exit_code': proc.returncode,
                      'source_identities_unchanged': before == after}), flush=True)
    audit = subprocess.run([str(PYTHON), str(REPO / 'devtools/embodiment_lab/audit_harness_run.py'),
            '--outcome', str(STDOUT), '--runs-dir', str(OUT / 'runs'), '--out', str(OUT / 'saved-run-audit.json')],
            cwd=REPO, env=environment, capture_output=True, text=True)
    save(OUT / 'audit-command-result.json', {'exit_code': audit.returncode, 'stdout': audit.stdout, 'stderr': audit.stderr})
    print(json.dumps({'phase': 'saved-run-audit', 'exit_code': audit.returncode}), flush=True)
    return 0 if audit.returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
