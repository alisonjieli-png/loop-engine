"""Offline verification of the sealed novel population: no model calls, no Docker.

Each reference implementation is written independently from the prompt. Every
case must match the reference's verdict, and every evaluator must be shown to
fail at least one deliberately wrong solution (an evaluator that cannot fail
is not an evaluator).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from novel_task_population import task_population


def _raise(error):
    if error:
        raise ValueError(error)


def ref_path_cost(text):
    if not isinstance(text, str):
        raise ValueError('nonstring')
    lines = text.split('\n')
    if not text or not lines:
        raise ValueError('empty')
    # The prompt says period-separated cells. Version 1 of this reference split
    # on commas, which is how it agreed with 109 of 109 cases and caught nothing.
    rows = [line.split('.') for line in lines]
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError('ragged')
    grid = []
    for row in rows:
        cells = []
        for cell in row:
            if cell == 'X':
                cells.append(None)
            elif cell.isdigit() and cell.isascii():
                cells.append(int(cell))
            else:
                raise ValueError('bad cell')
        grid.append(cells)
    if grid[0][0] is None and grid[-1][-1] is None:
        raise ValueError('walls at both ends')
    import heapq
    if grid[0][0] is None:
        return None
    heap = [(grid[0][0], 0, 0)]
    best = {}
    while heap:
        cost, r, c = heapq.heappop(heap)
        if (r, c) in best and best[(r, c)] <= cost:
            continue
        best[(r, c)] = cost
        if (r, c) == (len(grid) - 1, width - 1):
            return cost
        for dr, dc in ((0, 1), (1, 0)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < len(grid) and 0 <= nc < width and grid[nr][nc] is not None:
                heapq.heappush(heap, (cost + grid[nr][nc], nr, nc))
    return None


def ref_decode_runs(text):
    if not isinstance(text, str):
        raise ValueError('nonstring')
    import re
    pattern = re.compile(r'(\d+)\[([^\[\]]*)\]')
    pos, out = 0, []
    while pos < len(text):
        match = pattern.match(text, pos)
        if not match:
            raise ValueError('stray')
        count, body = match.group(1), match.group(2)
        if count != count.lstrip('0') or count.startswith('0') or count == '0':
            raise ValueError('bad count')
        if not body:
            raise ValueError('empty body')
        out.append(body * int(count))
        pos = match.end()
    return ''.join(out)


def ref_reconcile(text):
    if not isinstance(text, str):
        raise ValueError('nonstring')
    entries = json.loads(text)
    if not isinstance(entries, list):
        raise ValueError('not a list')
    totals = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(('account', 'side', 'amount')) - set(entry):
            raise ValueError('missing')
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
    if type(n) is not int or type(k) is not int or isinstance(n, bool) or isinstance(k, bool):
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
    if type(modulus) is not int or isinstance(modulus, bool) or modulus < 2:
        raise ValueError('bad modulus')
    total = 0
    for index, char in enumerate(text):
        total += ord(char) * 256 ** index
    return total % modulus


def ref_outline_depth(text):
    if not isinstance(text, str):
        raise ValueError('nonstring')
    import re
    depths = []
    for line in text.split('\n'):
        match = re.match(r'^(#+) (\S.*)$', line.lstrip(' ') if line.startswith(' ') else line, re.M)
        stripped = line.lstrip(' ')
        match = re.match(r'^(#+) (\S.*)$', stripped)
        if match:
            depths.append(len(match.group(1)) - 1)
    if not depths:
        raise ValueError('no heading')
    return max(depths)


def ref_free_minutes(text):
    if not isinstance(text, str):
        raise ValueError('nonstring')
    pairs = json.loads(text)
    if not isinstance(pairs, list):
        raise ValueError('not a list')
    import re
    minutes = []
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError('bad pair')
        values = []
        for value in pair:
            if not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
                raise ValueError('bad time')
            hour, minute = value.split(':')
            values.append(int(hour) * 60 + int(minute))
        # The prompt forbids an end BEFORE its start; a zero-length interval is
        # allowed and covers nothing. Version 1 raised on it.
        if values[1] < values[0]:
            raise ValueError('end before start')
        minutes.append(values)
    covered = [False] * 1440
    for start, end in minutes:
        for minute in range(start, end):
            covered[minute] = True
    return 1440 - sum(covered[:1440])


def ref_final_state(text):
    if not isinstance(text, str) or not text:
        raise ValueError('nonstring or empty')
    if '  ' in text or text != text.strip(' '):
        raise ValueError('bad spacing')
    import re
    accumulator = 0
    for command in text.split(' '):
        if command == 'd':
            accumulator *= 2
        elif command == 'r':
            accumulator = 0
        elif re.fullmatch(r'[+-]?[0-9]+', command):
            accumulator += int(command)
        else:
            raise ValueError('unknown command')
    return accumulator


def ref_spiral_sum(matrix):
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
            if type(value) is not int or isinstance(value, bool):
                raise ValueError('bad element')
    total, top, bottom, left, right = 0, 0, len(matrix) - 1, 0, width - 1
    while top <= bottom and left <= right:
        for column in range(left, right + 1):
            total += matrix[top][column]
        top += 1
        for row in range(top, bottom + 1):
            total += matrix[row][right]
        right -= 1
        if top <= bottom:
            for column in range(right, left - 1, -1):
                total += matrix[bottom][column]
            bottom -= 1
        if left <= right:
            for row in range(bottom, top - 1, -1):
                total += matrix[row][left]
            left += 1
    return total


def ref_is_word_square(words):
    """One consistent rule, taken literally from the prompt.

    The prompt raises ValueError for "lists whose lengths exceed every element
    length": the list is longer than each of its words. Version 1 raised
    "too short" only when its nested loop reached a missing character before
    it found a mismatch, so ['ab','a'] returned False while ['aa','a'] raised:
    same shape, different verdicts, and the campaign's one "invalidation"
    rested on that. Here the error condition is decided first and once; a pair
    that cannot be compared because one word is shorter (but not all are) is
    simply not a square.
    """
    if not isinstance(words, list) or not words:
        raise ValueError('not a list or empty')
    for word in words:
        if not isinstance(word, str) or not word:
            raise ValueError('bad element')
    size = len(words)
    if all(size > len(word) for word in words):
        raise ValueError('list longer than every word')
    for a in range(size):
        for b in range(size):
            if b >= len(words[a]) or a >= len(words[b]):
                return False
            if words[a][b] != words[b][a]:
                return False
    return True


REFERENCES = {
    'grid_path_cost': ref_path_cost,
    'run_length_decode': ref_decode_runs,
    'ledger_reconcile': ref_reconcile,
    'josephus_rank': ref_survivor_index,
    'poly_hash': ref_poly_hash,
    'markdown_outline': ref_outline_depth,
    'calendar_slots': ref_free_minutes,
    'state_machine': ref_final_state,
    'matrix_spiral': ref_spiral_sum,
    'word_square': ref_is_word_square,
}

WRONG_SOLUTIONS = {
    'grid_path_cost': ('1.2.3\n4.5.6\n7.8.9', 22),
    'run_length_decode': ('3[ab]', 'abab'),
    'ledger_reconcile': ('[{"account":"cash","side":"DR","amount":5},{"account":"cash","side":"CR","amount":5}]', None),
    'josephus_rank': ((7, 3), 2),
    'poly_hash': (('ab', 1000000007), (97 + 98) % 1000000007),
    'markdown_outline': ('# t\n## a\n### b\n# c', 1),
    'calendar_slots': ('["09:00","10:00"]', 1370),
    'state_machine': ('3 d', 7),
    'matrix_spiral': ([[1, 2], [3, 4]], 9),
    'word_square': ([['ball', 'area', 'lead', 'lady']], False),
}


def main():
    population = task_population()
    results = {'population_size': len(population), 'cases_checked': 0,
               'reference_mismatches': [], 'evaluator_control_failures': [],
               'prompt_entrypoint_mismatches': []}
    import generalization_probe as probe

    for task in population:
        reference = REFERENCES[task.task_id]
        for item in task.cases:
            arguments = list(item['arguments'])
            try:
                value = reference(*arguments)
                error = None
            except ValueError:
                value, error = None, 'ValueError'
            if item['error'] == 'ValueError':
                ok = error == 'ValueError'
            else:
                ok = error is None and probe_equality(value, item['expected'])
            results['cases_checked'] += 1
            if not ok:
                results['reference_mismatches'].append({
                    'task_id': task.task_id, 'case_id': item['case_id'],
                    'reference': probe_safe(value), 'expected': probe_safe(item['expected'])})
        # The control the review asked for: a deliberately wrong SOLUTION, run
        # through the same case loop the reference just passed. Version 1
        # compared the reference against one wrong constant, which tests the
        # reference's arithmetic and says nothing about whether the evaluator
        # can reject a wrong program.
        _, wrong_value = WRONG_SOLUTIONS[task.task_id]

        def wrong_solution(*_arguments, _value=wrong_value):
            return _value

        rejected = 0
        for item in task.cases:
            try:
                value = wrong_solution(*list(item['arguments']))
                error = None
            except ValueError:
                value, error = None, 'ValueError'
            if item['error'] == 'ValueError':
                ok = error == 'ValueError'
            else:
                ok = error is None and probe_equality(value, item['expected'])
            if not ok:
                rejected += 1
        if rejected == 0:
            results['evaluator_control_failures'].append(task.task_id)
        # The prompt names the entry point ("Implement X(...) in solution.py"); it
        # must be the one the case runner calls. Initialised and never populated
        # in version 1, and not part of the exit code.
        match = re.search(r'Implement (\w+)\(', task.prompt)
        if not match or match.group(1) != task.entrypoint:
            results['prompt_entrypoint_mismatches'].append({
                'task_id': task.task_id, 'prompt': match.group(1) if match else None,
                'entrypoint': task.entrypoint})
    print(probe.canonical(results))
    return 0 if not (results['reference_mismatches'] or results['evaluator_control_failures']
                     or results['prompt_entrypoint_mismatches']) else 1


def probe_equality(observed, expected):
    if isinstance(observed, bool) or isinstance(expected, bool):
        return type(observed) is type(expected) and observed == expected
    if observed is None or expected is None:
        return observed is None and expected is None
    if isinstance(expected, dict) and isinstance(observed, dict):
        return observed.keys() == expected.keys() and all(probe_equality(observed[key], value) for key, value in expected.items())
    return type(observed) is type(expected) and observed == expected


def probe_safe(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True)[:120]
    return str(value)[:120]


if __name__ == '__main__':
    raise SystemExit(main())