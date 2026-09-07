"""Offline verification of population version 2: no model calls, no Docker.

Method. The ten reference implementations below were written from the prompt
text of ``novel_task_population_v2`` before its cases were consulted, then
run against the cases. Every disagreement was resolved by rereading the
prompt and changing the case or the prompt, never the reference to fit a
case; each resolution is recorded in ``RESOLUTIONS`` so the population's
history is visible.

Controls. The version 1 check compared a reference against one wrong
constant, which any function passes. Here the control runs the real campaign
evaluator (``generalization_probe.evaluate`` over the probe ``WORKER``)
against a deliberately wrong ``solution.py`` for every task and requires the
evaluator to fail it. A wrong solution that the evaluator accepts is a check
failure: that evaluator cannot tell right from wrong on that task.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generalization_probe as probe
from novel_task_population_v2 import task_population


# --- references written from the prompts ---------------------------------

def ref_path_cost(text):
    if not isinstance(text, str):
        raise ValueError('nonstring')
    if not text:
        raise ValueError('empty')
    rows = [line.split(',') for line in text.split('\n')]
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError('ragged')
    grid = []
    for row in rows:
        cells = []
        for cell in row:
            if cell == 'X':
                cells.append(None)
            elif cell.isascii() and cell.isdigit():
                cells.append(int(cell))
            else:
                raise ValueError('bad cell')
        grid.append(cells)
    if grid[0][0] is None and grid[-1][-1] is None:
        raise ValueError('walls at both ends')
    if grid[0][0] is None or grid[-1][-1] is None:
        return None
    height = len(grid)
    best = [[None] * width for _ in range(height)]
    for r in range(height):
        for c in range(width):
            if grid[r][c] is None:
                continue
            candidates = []
            if r == 0 and c == 0:
                candidates.append(0)
            if r > 0 and best[r - 1][c] is not None:
                candidates.append(best[r - 1][c])
            if c > 0 and best[r][c - 1] is not None:
                candidates.append(best[r][c - 1])
            if candidates:
                best[r][c] = min(candidates) + grid[r][c]
    return best[-1][-1]


def ref_decode_runs(text):
    if not isinstance(text, str):
        raise ValueError('nonstring')
    pattern = re.compile(r'(\d+)\[([^\[\]]*)\]')
    position, out = 0, []
    while position < len(text):
        match = pattern.match(text, position)
        if not match:
            raise ValueError('stray')
        count, body = match.group(1), match.group(2)
        if not count.isascii() or count == '0' or count.startswith('0'):
            raise ValueError('bad count')
        if not body:
            raise ValueError('empty body')
        out.append(body * int(count))
        position = match.end()
    return ''.join(out)


def ref_reconcile(text):
    if not isinstance(text, str):
        raise ValueError('nonstring')
    entries = json.loads(text)
    if not isinstance(entries, list):
        raise ValueError('not an array')
    totals = {}
    for entry in entries:
        if not isinstance(entry, dict) or {'account', 'side', 'amount'} - set(entry):
            raise ValueError('missing field')
        account, side, amount = entry['account'], entry['side'], entry['amount']
        if not isinstance(account, str) or not account:
            raise ValueError('bad account')
        if side not in ('DR', 'CR'):
            raise ValueError('bad side')
        if type(amount) is not int:
            raise ValueError('bad amount')
        totals[account] = totals.get(account, 0) + (amount if side == 'DR' else -amount)
    result = {account: totals[account] for account in sorted(totals)}
    result['__unbalanced__'] = sum(1 for value in totals.values() if value != 0)
    return result


def ref_survivor_index(n, k):
    if type(n) is not int or type(k) is not int:
        raise ValueError('nonint')
    if n < 1 or k < 1:
        raise ValueError('range')
    people = list(range(n))
    index = 0
    while len(people) > 1:
        index = (index + k - 1) % len(people)
        people.pop(index)
    return people[0]


def ref_poly_hash(text, modulus):
    if not isinstance(text, str):
        raise ValueError('nonstring')
    if type(modulus) is not int or modulus < 2:
        raise ValueError('bad modulus')
    total = 0
    for index, char in enumerate(text):
        total += ord(char) * 256 ** index
    return total % modulus


def ref_outline_depth(text):
    if not isinstance(text, str):
        raise ValueError('nonstring')
    heading = re.compile(r'^(#+) ([^ ].*)$')
    levels = []
    for line in text.split('\n'):
        match = heading.match(line.lstrip(' '))
        if match:
            levels.append(len(match.group(1)) - 1)
    if not levels:
        raise ValueError('no heading')
    return max(levels)


def ref_free_minutes(text):
    if not isinstance(text, str):
        raise ValueError('nonstring')
    pairs = json.loads(text)
    if not isinstance(pairs, list):
        raise ValueError('not an array')
    clock = re.compile(r'^([0-9]{2}):([0-9]{2})$')
    covered = [False] * 1440
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2 or any(not isinstance(v, str) for v in pair):
            raise ValueError('bad pair')
        minutes = []
        for position, value in enumerate(pair):
            match = clock.match(value)
            if not match:
                raise ValueError('bad time')
            hour, minute = int(match.group(1)), int(match.group(2))
            if position == 1 and value == '24:00':
                minutes.append(1440)
            elif hour > 23 or minute > 59:
                raise ValueError('outside day')
            else:
                minutes.append(hour * 60 + minute)
        start, end = minutes
        if end <= start:
            raise ValueError('end not after start')
        for minute in range(start, end):
            covered[minute] = True
    return 1440 - sum(covered)


def ref_final_state(text):
    if not isinstance(text, str) or not text:
        raise ValueError('nonstring or empty')
    integer = re.compile(r'^[+-]?(0|[1-9][0-9]*)$')
    accumulator = 0
    for command in text.split(' '):
        if command == 'd':
            accumulator *= 2
        elif command == 'r':
            accumulator = 0
        elif command.isascii() and integer.match(command):
            accumulator += int(command)
        else:
            raise ValueError('unknown command or spacing')
    return accumulator


def ref_spiral_weighted_sum(matrix):
    if not isinstance(matrix, list):
        raise ValueError('not a list')
    if not matrix:
        return 0
    if any(not isinstance(row, list) for row in matrix):
        raise ValueError('row not list')
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError('ragged')
    for row in matrix:
        for value in row:
            if type(value) is not int:
                raise ValueError('bad element')
    order = []
    top, bottom, left, right = 0, len(matrix) - 1, 0, width - 1
    while top <= bottom and left <= right:
        for column in range(left, right + 1):
            order.append(matrix[top][column])
        for row in range(top + 1, bottom + 1):
            order.append(matrix[row][right])
        if top < bottom:
            for column in range(right - 1, left - 1, -1):
                order.append(matrix[bottom][column])
        if left < right:
            for row in range(bottom - 1, top, -1):
                order.append(matrix[row][left])
        top, bottom, left, right = top + 1, bottom - 1, left + 1, right - 1
    return sum(value * position for position, value in enumerate(order, start=1))


def ref_is_word_square(words):
    if not isinstance(words, list) or not words:
        raise ValueError('not a list or empty')
    for word in words:
        if not isinstance(word, str) or not word:
            raise ValueError('bad element')
    n = len(words)
    if any(len(word) < n for word in words):
        raise ValueError('short word')
    return all(words[i][j] == words[j][i] for i in range(n) for j in range(n))


REFERENCES = {
    'grid_path_cost': ref_path_cost,
    'run_length_decode': ref_decode_runs,
    'ledger_reconcile': ref_reconcile,
    'josephus_rank': ref_survivor_index,
    'poly_hash': ref_poly_hash,
    'markdown_outline': ref_outline_depth,
    'calendar_slots': ref_free_minutes,
    'state_machine': ref_final_state,
    'matrix_spiral': ref_spiral_weighted_sum,
    'word_square': ref_is_word_square,
}

#: Every prompt-versus-case disagreement met while building version 2, and
#: how it was resolved. The reference was never changed to fit a case.
RESOLUTIONS = (
    ('grid_path_cost', 'plain', 'version 1 prompt said period-separated cells; every case used commas',
     'prompt now says comma-separated; cases unchanged'),
    ('grid_path_cost', 'start_wall', 'version 1 left a wall in one corner undefined and its reference crashed',
     'prompt now says return None; cases start_wall and end_wall added'),
    ('calendar_slots', 'full_day', 'version 1 prompt bounded the day at 1439 but two cases required 24:00',
     'prompt now defines 24:00 as the only end-of-day sentinel; sentinel_as_start and zero_length added'),
    ('state_machine', 'leading_zero', 'version 1 prompt allowed any signed integer but a case refused 01',
     'prompt now states the no-leading-zero rule and both signs; plus_sign and signed_leading_zero added'),
    ('matrix_spiral', 'two_by_two', 'a sum in spiral order equals a sum in any order, so no evaluator could tell',
     'task now returns the visit-number weighted sum; every expected value recomputed'),
    ('poly_hash', 'non_ascii_code_point', 'the version 1 "unicode" case was six ASCII characters from a doubled backslash',
     'cases now use a real code point 233 and an astral code point'),
    ('word_square', 'three_by_three_square', 'version 1 had two identical cases, one misnamed, and no positive 3x3 square',
     'duplicate removed, ["cat","are","ted"] added, short-word rule stated as one sentence'),
)

#: A deliberately wrong solution per task. The campaign evaluator must fail it.
WRONG_SOLUTIONS = {
    'grid_path_cost': "def path_cost(grid_text):\n    rows = [r.split('.') for r in grid_text.split('\\n')]\n    return sum(int(c) for r in rows for c in r if c != 'X')\n",
    'run_length_decode': "import re\ndef decode_runs(text):\n    return ''.join(body for _, body in re.findall(r'(\\d+)\\[([^\\[\\]]*)\\]', text))\n",
    'ledger_reconcile': "import json\ndef reconcile(text):\n    totals = {}\n    for e in json.loads(text):\n        totals[e['account']] = totals.get(e['account'], 0) + (e['amount'] if e['side'] == 'DR' else -e['amount'])\n    return totals\n",
    'josephus_rank': "def survivor_index(n, k):\n    people = list(range(n))\n    i = 0\n    while len(people) > 1:\n        i = (i + k) % len(people)\n        people.pop(i)\n    return people[0]\n",
    'poly_hash': "def poly_hash(text, modulus):\n    total = 0\n    for ch in text:\n        total = total * 31 + ord(ch)\n    return total % modulus\n",
    'markdown_outline': "def outline_depth(text):\n    depths = [len(l) - len(l.lstrip('#')) for l in text.split('\\n') if l.startswith('#')]\n    return max(depths)\n",
    'calendar_slots': "import json\ndef free_minutes(text):\n    total = 0\n    for s, e in json.loads(text):\n        total += (int(e[:2]) * 60 + int(e[3:])) - (int(s[:2]) * 60 + int(s[3:]))\n    return 1440 - total\n",
    'state_machine': "def final_state(text):\n    acc = 0\n    for c in text.split(' '):\n        if c == 'r':\n            acc = 0\n        elif c != 'd':\n            acc += int(c)\n    return acc\n",
    'matrix_spiral': "def spiral_weighted_sum(matrix):\n    values = [v for row in matrix for v in row]\n    return sum(v * i for i, v in enumerate(values, start=1))\n",
    'word_square': "def is_word_square(words):\n    n = len(words)\n    return all(words[i][j] == words[j][i] for i in range(n) for j in range(n) if j < len(words[i]) and i < len(words[j]))\n",
}


def host_python_runner(run_root, image):
    """The probe WORKER under the host interpreter; the control needs no container."""
    completed = subprocess.run([sys.executable, '-B', 'probe.py'], cwd=run_root,
                               capture_output=True, text=True, timeout=120)
    return {'ok': completed.returncode == 0, 'exit_code': completed.returncode,
            'stdout': completed.stdout, 'stderr': completed.stderr, 'error_code': None,
            'output_truncated': False, 'image': image, 'backend': 'host_python_control'}


def evaluate_solution(task, source, runner=host_python_runner):
    """Score one solution.py with the campaign evaluator, exactly as the host does."""
    with tempfile.TemporaryDirectory(prefix='novel-v2-control-') as directory:
        root = Path(directory)
        (root / 'solution.py').write_text(source, encoding='utf-8')
        (root / 'probe.py').write_text(probe.WORKER, encoding='utf-8')
        (root / 'probe-input.json').write_text(probe.canonical({
            'entrypoint': task.entrypoint,
            'cases': [{key: item[key] for key in ('case_id', 'arguments', 'python_constants') if key in item}
                      for item in task.cases]}), encoding='utf-8')
        return probe.evaluate(task, runner(root, probe.IMAGE))


def probe_equality(observed, expected):
    if isinstance(observed, bool) or isinstance(expected, bool):
        return type(observed) is type(expected) and observed == expected
    if observed is None or expected is None:
        return observed is None and expected is None
    if isinstance(expected, dict) and isinstance(observed, dict):
        return observed.keys() == expected.keys() and all(
            probe_equality(observed[key], value) for key, value in expected.items())
    return type(observed) is type(expected) and observed == expected


def check_population(population=None, runner=host_python_runner):
    population = population or task_population()
    results = {'record_type': 'novel_task_offline_check/v2', 'population_size': len(population),
               'cases_checked': 0, 'reference_mismatches': [], 'evaluator_control_failures': [],
               'prompt_entrypoint_mismatches': [], 'resolutions_recorded': len(RESOLUTIONS)}
    for task in population:
        if f'Implement {task.entrypoint}(' not in task.prompt:
            results['prompt_entrypoint_mismatches'].append(task.task_id)
        reference = REFERENCES[task.task_id]
        for item in task.cases:
            try:
                value, error = reference(*list(item['arguments'])), None
            except ValueError:
                value, error = None, 'ValueError'
            ok = (error == 'ValueError') if item['error'] == 'ValueError' else (
                error is None and probe_equality(value, item['expected']))
            results['cases_checked'] += 1
            if not ok:
                results['reference_mismatches'].append({
                    'task_id': task.task_id, 'case_id': item['case_id'],
                    'reference': str(value)[:120], 'reference_error': error,
                    'expected': str(item['expected'])[:120], 'expected_error': item['error']})
        control = evaluate_solution(task, WRONG_SOLUTIONS[task.task_id], runner)
        if control['passed'] is not False:
            results['evaluator_control_failures'].append(task.task_id)
    results['passed'] = not (results['reference_mismatches'] or results['evaluator_control_failures']
                             or results['prompt_entrypoint_mismatches'])
    return results


def main():
    results = check_population()
    print(probe.canonical(results))
    return 0 if results['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
