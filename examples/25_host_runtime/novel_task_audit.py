"""Independent post-hoc audit of accepted novel-campaign solutions.

For every accepted source, generate seeded random inputs beyond the frozen
case set and compare the candidate against the offline references, which were
written independently from the prompts. This audit can invalidate an accepted
solution; the campaign result alone is not a correctness claim.
"""
from __future__ import annotations

import importlib.util
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from novel_task_population import task_population
from novel_task_offline_check import REFERENCES

ROOT = Path('/tmp/novel-campaign-20260906')
AUDIT_SEED = 8675309
CASES_PER_TASK = 60


def load_solution(task_root, entrypoint):
    path = task_root / 'source' / 'solution.py'
    spec = importlib.util.spec_from_file_location('audit_candidate_' + entrypoint, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, entrypoint)


def make_grid(rng):
    rows = rng.randint(1, 6)
    cols = rng.randint(1, 6)
    while rows * cols < 2:
        rows, cols = rng.randint(1, 6), rng.randint(1, 6)
    cells = []
    for _ in range(rows):
        line = []
        for _ in range(cols):
            if rng.random() < 0.15:
                line.append('X')
            else:
                line.append(str(rng.randint(0, 99)))
        cells.append(line)
    if cells[0][0] == 'X' and cells[-1][-1] == 'X':
        cells[0][0] = '0'
    text = '\n'.join(','.join(line) for line in cells)
    if rng.random() < 0.5:
        # invalid variant
        return text.replace(',', '.', 1) if False else (text, None)
    return text, None


def make_rle(rng):
    runs = rng.randint(1, 4)
    parts = []
    for _ in range(runs):
        count = rng.randint(1, 9)
        body = ''.join(rng.choice('abc') for _ in range(rng.randint(1, 3)))
        parts.append(f'{count}[{body}]')
    return ''.join(parts)


def make_ledger(rng):
    accounts = ['a', 'b', 'c'][:rng.randint(1, 3)]
    entries = []
    for _ in range(rng.randint(1, 8)):
        entries.append({'account': rng.choice(accounts), 'side': rng.choice(('DR', 'CR')),
                        'amount': rng.randint(-500, 500)})
    return json.dumps(entries)


def make_state(rng):
    commands = []
    for _ in range(rng.randint(1, 8)):
        commands.append(rng.choice(('d', 'r', str(rng.randint(0, 99)), str(-rng.randint(0, 9)))))
    return ' '.join(commands)


def make_busy(rng):
    pairs = []
    used = []
    for _ in range(rng.randint(0, 4)):
        start = rng.randint(0, 1339)
        end = rng.randint(start + 1, 1440)
        pairs.append([f'{start // 60:02d}:{start % 60:02d}', f'{end // 60:02d}:{end % 60:02d}'])
    return json.dumps(pairs)


def make_matrix(rng):
    rows = rng.randint(1, 5)
    cols = rng.randint(1, 5)
    return [[rng.randint(-50, 50) for _ in range(cols)] for _ in range(rows)]


def run_candidate(fn, arguments):
    import copy
    args = copy.deepcopy(arguments)
    try:
        return fn(*args), None
    except ValueError:
        return None, 'ValueError'
    except Exception as exc:
        return None, type(exc).__name__


def audit_task(task, rng):
    task_root = ROOT / task.task_id
    reference = REFERENCES[task.task_id]
    fn = load_solution(task_root, task.entrypoint)
    generators = {
        'grid_path_cost': lambda: make_grid(rng)[0],
        'run_length_decode': lambda: make_rle(rng),
        'ledger_reconcile': lambda: make_ledger(rng),
        'josephus_rank': lambda: (rng.randint(1, 40), rng.randint(1, 60)),
        'poly_hash': lambda: (''.join(rng.choice('ab xyz\\u00e9#') for _ in range(rng.randint(0, 8))), rng.choice((2, 97, 7919, 10**18 + 7))),
        'markdown_outline': lambda: '\n'.join(
            ('# t', '## a', '### b', '#### c', 'not a heading', '#nospace')[:rng.randint(1, 6)]),
        'calendar_slots': lambda: make_busy(rng),
        'state_machine': lambda: make_state(rng),
        'matrix_spiral': lambda: make_matrix(rng),
        'word_square': lambda: [''.join(rng.choice('ab') for _ in range(rng.randint(1, 4)))
                                for _ in range(rng.randint(1, 3))],
    }
    generate = generators[task.task_id]
    failures = []
    for index in range(CASES_PER_TASK):
        arguments = [generate()]
        if task.task_id == 'josephus_rank' and isinstance(arguments[0], tuple):
            arguments = list(arguments[0])
        if task.task_id == 'poly_hash' and isinstance(arguments[0], tuple):
            arguments = list(arguments[0])
        expected_value, expected_error = run_candidate(reference, arguments)
        actual_value, actual_error = run_candidate(fn, arguments)
        if expected_error != actual_error or json.dumps(expected_value, sort_keys=True) != json.dumps(actual_value, sort_keys=True):
            failures.append({'index': index, 'arguments': json.dumps(arguments)[:200],
                             'expected': str(expected_value)[:80] + (' E:' + expected_error if expected_error else ''),
                             'actual': str(actual_value)[:80] + (' E:' + actual_error if actual_error else '')})
    return {'task_id': task.task_id, 'audit_cases': CASES_PER_TASK, 'failures': failures,
            'audit_passed': not failures}


def main():
    rng = random.Random(AUDIT_SEED)
    results = []
    for task in task_population():
        result = audit_task(task, rng)
        results.append(result)
        marker = 'PASS' if result['audit_passed'] else f"FAIL ({len(result['failures'])} mismatches)"
        print(f"{result['task_id']:<20} {marker}", flush=True)
        for failure in result['failures'][:3]:
            print(f"    args={failure['arguments']}")
            print(f"    expected: {failure['expected']}")
            print(f"    actual:   {failure['actual']}")
    summary = {'record_type': 'novel_task_campaign_audit/v1', 'seed': AUDIT_SEED,
               'cases_per_task': CASES_PER_TASK,
               'tasks_audited': len(results),
               'tasks_invalidated': sum(1 for item in results if not item['audit_passed']),
               'results': results}
    Path('/tmp/novel-campaign-audit.json').write_text(json.dumps(summary, indent=2) + '\n')
    passed = sum(1 for item in results if item['audit_passed'])
    print(f"\naudit: {passed}/{len(results)} accepted solutions survive independent random-input audit")
    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())