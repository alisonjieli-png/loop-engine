"""Post-campaign audit, version 2: candidates run only inside the pinned container.

Version 1 imported each accepted ``solution.py`` into the host interpreter,
took its campaign root from a constant under ``/tmp``, generated mostly valid
inputs, and left its invalid-input branch as dead code. Version 2:

- takes the campaign root and the output path as arguments;
- executes every candidate through the probe ``WORKER`` inside the pinned
  container (``generalization_probe.docker_probe``), never by importing it;
  the runner is a parameter so a unit test can substitute a host-Python
  fixture runner for fixture code it wrote itself;
- generates seeded valid and invalid inputs for every task and scores them
  with the version 2 references through the real campaign evaluator;
- checks that the audited source is the exact source the campaign accepted,
  by digest, before spending a container run on it.

An audit can invalidate an accepted solution. It grants nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generalization_probe as probe
from generalization_probe import ProbeTask, canonical, case, digest, docker_probe, write_json
from novel_task_offline_check_v2 import REFERENCES
from novel_task_population_v2 import task_population

AUDIT_RECORD_TYPE = 'novel_task_campaign_audit/v2'
DEFAULT_SEED = 8675309
DEFAULT_CASES_PER_TASK = 60


def _clock(minute):
    return f'{minute // 60:02d}:{minute % 60:02d}'


def generators(rng):
    """Seeded input generators; roughly one input in four is deliberately invalid."""

    def grid():
        rows, cols = rng.randint(1, 6), rng.randint(1, 6)
        cells = [[('X' if rng.random() < 0.15 else str(rng.randint(0, 99))) for _ in range(cols)]
                 for _ in range(rows)]
        if cells[0][0] == 'X' and cells[-1][-1] == 'X' and rng.random() < 0.5:
            cells[0][0] = '0'
        text = '\n'.join(','.join(row) for row in cells)
        choice = rng.random()
        if choice < 0.08 and cols > 1:
            text = text.replace(',', '', 1)
        elif choice < 0.16:
            text = text.replace(',', ',-', 1) if ',' in text else '-1'
        elif choice < 0.22:
            text = text.replace(',', ',b', 1) if ',' in text else 'b'
        return [text]

    def rle():
        parts = []
        for _ in range(rng.randint(1, 4)):
            count = rng.randint(1, 12)
            body = ''.join(rng.choice('abc ') for _ in range(rng.randint(1, 3)))
            parts.append(f'{count}[{body}]')
        text = ''.join(parts)
        choice = rng.random()
        if choice < 0.08:
            text = '0' + text
        elif choice < 0.16:
            text = text.replace('[', '[2[', 1) + ']'
        elif choice < 0.22:
            text = text + 'x'
        elif choice < 0.26:
            text = text.replace('[', '[]', 1)
        return [text]

    def ledger():
        accounts = ['a', 'b', 'c'][:rng.randint(1, 3)]
        entries = [{'account': rng.choice(accounts), 'side': rng.choice(('DR', 'CR')),
                    'amount': rng.randint(-500, 500)} for _ in range(rng.randint(0, 8))]
        choice = rng.random()
        if choice < 0.08 and entries:
            entries[0]['side'] = 'dr'
        elif choice < 0.16 and entries:
            entries[0]['amount'] = str(entries[0]['amount'])
        elif choice < 0.22 and entries:
            del entries[0]['account']
        elif choice < 0.26:
            return ['{"account": "a"}']
        return [json.dumps(entries)]

    def josephus():
        choice = rng.random()
        if choice < 0.08:
            return [0, rng.randint(1, 5)]
        if choice < 0.16:
            return [rng.randint(1, 20), 0]
        if choice < 0.22:
            return [float(rng.randint(1, 20)), 3]
        return [rng.randint(1, 40), rng.randint(1, 60)]

    def poly():
        alphabet = 'ab xyz#é中\U0001F600'
        text = ''.join(rng.choice(alphabet) for _ in range(rng.randint(0, 8)))
        modulus = rng.choice((2, 97, 7919, 10**18 + 7))
        choice = rng.random()
        if choice < 0.08:
            modulus = 1
        elif choice < 0.16:
            modulus = float(modulus)
        elif choice < 0.22:
            return [5, modulus]
        return [text, modulus]

    def outline():
        lines = ['# t', '## a', '### b', '#### c', 'not a heading', '#nospace', '##  double', '  ## indented', '# ']
        rng.shuffle(lines)
        selected = lines[:rng.randint(1, len(lines))]
        if rng.random() < 0.2:
            selected = [line for line in selected if not line.lstrip(' ').startswith('# ')
                        and not line.lstrip(' ').startswith('## ') and not line.lstrip(' ').startswith('### ')
                        and not line.lstrip(' ').startswith('#### ')]
        return ['\n'.join(selected)]

    def calendar():
        pairs = []
        for _ in range(rng.randint(0, 4)):
            start = rng.randint(0, 1339)
            end = rng.randint(start + 1, 1440)
            pairs.append([_clock(start), _clock(end)])
        choice = rng.random()
        if choice < 0.08 and pairs:
            pairs[0] = [pairs[0][1], pairs[0][0]]
        elif choice < 0.16 and pairs:
            pairs[0][1] = pairs[0][0]
        elif choice < 0.22:
            pairs.append(['24:00', '24:00'])
        elif choice < 0.26:
            pairs.append(['9:00', '10:00'])
        elif choice < 0.30:
            pairs.append(['00:00', '25:00'])
        return [json.dumps(pairs)]

    def state():
        commands = [rng.choice(('d', 'r', str(rng.randint(0, 99)), str(-rng.randint(1, 9)), '+' + str(rng.randint(1, 9))))
                    for _ in range(rng.randint(1, 8))]
        text = ' '.join(commands)
        choice = rng.random()
        if choice < 0.08:
            text = text + ' 07'
        elif choice < 0.16:
            text = text.replace(' ', '  ', 1) if ' ' in text else text + ' '
        elif choice < 0.22:
            text = text + ' q'
        return [text]

    def spiral():
        rows, cols = rng.randint(1, 5), rng.randint(1, 5)
        matrix = [[rng.randint(-50, 50) for _ in range(cols)] for _ in range(rows)]
        choice = rng.random()
        if choice < 0.08 and cols > 1:
            matrix[0] = matrix[0][:-1]
        elif choice < 0.16:
            matrix[0][0] = True
        elif choice < 0.22:
            matrix[0][0] = 1.5
        return [matrix]

    def square():
        n = rng.randint(1, 4)
        length = rng.randint(1, 5)
        words = [''.join(rng.choice('ab') for _ in range(length)) for _ in range(n)]
        if rng.random() < 0.4 and length >= n:
            for i in range(n):
                for j in range(i):
                    words[i] = words[i][:j] + words[j][i] + words[i][j + 1:]
        choice = rng.random()
        if choice < 0.08:
            words.append('')
        elif choice < 0.16 and words:
            words[0] = 5
        return [words]

    return {'grid_path_cost': grid, 'run_length_decode': rle, 'ledger_reconcile': ledger,
            'josephus_rank': josephus, 'poly_hash': poly, 'markdown_outline': outline,
            'calendar_slots': calendar, 'state_machine': state, 'matrix_spiral': spiral,
            'word_square': square}


def audit_cases(task, rng, count):
    """Seeded cases with verdicts from the version 2 reference for this task."""
    generate = generators(rng)[task.task_id]
    reference = REFERENCES[task.task_id]
    cases = []
    for index in range(count):
        arguments = generate()
        try:
            expected, error = reference(*arguments), None
        except ValueError:
            expected, error = None, 'ValueError'
        cases.append(case(f'audit-{index:03d}', arguments, expected, error=error))
    return cases


def accepted_source(task_root):
    """The accepted solution and the digest the campaign recorded for it."""
    source_path = task_root / 'source' / 'solution.py'
    outcome_path = task_root / 'outcome.json'
    if not source_path.is_file() or not outcome_path.is_file():
        raise ValueError(f'{task_root.name}: no accepted source or outcome to audit')
    source = source_path.read_bytes()
    outcome = json.loads(outcome_path.read_text(encoding='utf-8'))
    value = ((outcome.get('result') or {}).get('value') or {}) if isinstance(outcome.get('result'), dict) else {}
    recorded = value.get('source_digest') if isinstance(value, dict) else None
    actual = hashlib.sha256(source).hexdigest()
    if outcome.get('solved') is not True:
        raise ValueError(f'{task_root.name}: campaign did not accept this task')
    if recorded != actual:
        raise ValueError(f'{task_root.name}: audited source differs from the accepted source digest')
    return source.decode('utf-8'), actual


def task_roots(campaign_root):
    """Task directories of a single-pass root, or of every pass under a multi-pass root."""
    campaign_root = Path(campaign_root)
    passes = sorted(item for item in campaign_root.glob('pass-*') if item.is_dir())
    roots = passes or [campaign_root]
    found = []
    for pass_root in roots:
        for item in sorted(pass_root.iterdir()):
            if item.is_dir() and (item / 'source' / 'solution.py').is_file():
                found.append((pass_root.name if passes else '', item))
    return found


def audit_task(task, source, run_root, rng, count, runner):
    """Score one accepted source on fresh seeded cases, through the container."""
    cases = audit_cases(task, rng, count)
    audit = ProbeTask(task.task_id, task.shape, task.prompt, task.entrypoint, task.initial_source,
                      canonical(cases))
    run_root.mkdir(parents=True, exist_ok=False)
    (run_root / 'solution.py').write_text(source, encoding='utf-8')
    (run_root / 'probe.py').write_text(probe.WORKER, encoding='utf-8')
    write_json(run_root / 'probe-input.json', {'entrypoint': audit.entrypoint, 'cases': [
        {key: item[key] for key in ('case_id', 'arguments', 'python_constants') if key in item}
        for item in audit.cases]})
    execution = runner(run_root, probe.IMAGE)
    comparison = probe.evaluate(audit, execution)
    failures = [{'case_id': item['case_id'], 'arguments': canonical(
        next(c['arguments'] for c in audit.cases if c['case_id'] == item['case_id']))[:200],
        'expected': str(item['expected'])[:80], 'expected_error': item['expected_error'],
        'observed': str((item.get('observed') or {}).get('value'))[:80],
        'observed_error': (item.get('observed') or {}).get('error')}
        for item in comparison['checks'] if not item['passed']]
    return {'task_id': task.task_id, 'audit_cases': len(cases),
            'invalid_inputs': sum(1 for item in cases if item['error'] == 'ValueError'),
            'execution_ok': execution.get('ok') is True, 'failure_kind': comparison['failure_kind'],
            'failures': failures, 'audit_passed': comparison['passed'],
            'audit_task_digest': audit.content_digest}


def audit_campaign(campaign_root, *, seed=DEFAULT_SEED, count=DEFAULT_CASES_PER_TASK,
                   runner=docker_probe, population=None, scratch=None):
    population = {task.task_id: task for task in (population or task_population())}
    campaign_root = Path(campaign_root)
    scratch = Path(scratch) if scratch is not None else campaign_root / 'audit-v2'
    results = []
    for pass_name, task_root in task_roots(campaign_root):
        task = population.get(task_root.name)
        if task is None:
            continue
        rng = random.Random(f'{seed}:{pass_name}:{task.task_id}')
        label = f'{pass_name}/{task.task_id}' if pass_name else task.task_id
        try:
            source, source_digest = accepted_source(task_root)
            entry = audit_task(task, source, scratch / (pass_name or 'pass') / task.task_id, rng, count, runner)
            entry.update(pass_name=pass_name, source_digest=source_digest)
        except ValueError as exc:
            entry = {'task_id': task.task_id, 'pass_name': pass_name, 'audit_passed': False,
                     'refused': str(exc), 'failures': []}
        entry['label'] = label
        results.append(entry)
    return {'record_type': AUDIT_RECORD_TYPE, 'seed': seed, 'cases_per_task': count,
            'campaign_root': str(campaign_root), 'runner': getattr(runner, '__name__', 'runner'),
            'tasks_audited': len(results),
            'tasks_invalidated': sum(1 for item in results if not item['audit_passed']),
            'results': results, 'grants': 'none; an audit can only invalidate'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign-root', required=True)
    parser.add_argument('--out', required=True, help='summary JSON path; must not exist')
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED)
    parser.add_argument('--cases-per-task', type=int, default=DEFAULT_CASES_PER_TASK)
    args = parser.parse_args(argv)
    out = Path(args.out).absolute()
    if out.exists():
        parser.error('--out must not already exist.')
    if args.cases_per_task < 1:
        parser.error('--cases-per-task must be at least 1.')
    summary = audit_campaign(args.campaign_root, seed=args.seed, count=args.cases_per_task)
    write_json(out, summary)
    for item in summary['results']:
        marker = 'PASS' if item['audit_passed'] else 'FAIL'
        detail = item.get('refused') or ('failures=' + str(len(item['failures'])))
        print(f"{item['label']:<28} {marker} {detail}")
    print(canonical({key: summary[key] for key in ('tasks_audited', 'tasks_invalidated', 'seed', 'cases_per_task')}))
    return 0 if summary['tasks_invalidated'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
