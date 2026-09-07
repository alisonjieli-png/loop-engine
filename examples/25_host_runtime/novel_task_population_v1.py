"""Sealed novel-task population for unseen-task evaluation.

Every task here is authored for this campaign and has never been run through
the engine before. They use invented domains and deliberately unusual
contracts so that passing them cannot come from memorizing the five
regression shapes. Expected answers are host-only; the runner imports the
host machinery from the generalization probe and adds no new runtime type.

This module makes no model call and writes no file. The campaign runner
freezes the population digest before any dispatch.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generalization_probe import ProbeTask, case, canonical


def task(task_id, shape, prompt, entrypoint, cases, seed=None):
    return ProbeTask(task_id, shape, prompt, entrypoint,
                     seed or f'def {entrypoint}(*args):\n    raise NotImplementedError\n',
                     canonical(cases))


def task_population():
    """Ten novel tasks across text, data, stateful, numeric, and structural domains."""
    population = (
        task('grid_path_cost', 'grid_semantics_to_scalar',
             'Implement path_cost(grid_text) in solution.py. The input is one or more lines of '
             'period-separated cells, where every cell is a nonnegative integer or the single character X '
             '(an impassable wall). Starting at the top-left cell and moving only right or down to the '
             'bottom-right cell, return the minimal sum of cell values along a valid path as an integer. '
             'If no path exists (all routes blocked by X), return None. The grid must have at least one '
             'line and every line must have the same number of cells. Raise ValueError for nonstring '
             'input, empty grids, ragged grids, malformed cell values, negative integers, or a wall in '
             'both the top-left and bottom-right corners. Do not print from the function.', 'path_cost', [
                 case('plain', ['1,2,3\n4,5,6\n7,8,9'], 21),
                 case('cheaper_detour', ['1,100,1\n1,100,1\n1,1,1'], 5),
                 case('wall_detour', ['1,X,9\n2,3,9\n9,9,1'], 16),
                 case('blocked', ['1,X\nX,1'], None),
                 case('single_cell', ['5'], 5),
                 case('single_row', ['1,2,3,4'], 10),
                 case('ragged', ['1,2\n1,2,3'], error='ValueError'),
                 case('bad_cell', ['1,b\n2,3'], error='ValueError'),
                 case('negative', ['1,-2\n3,4'], error='ValueError'),
                 case('nonstring', [None], error='ValueError'),
                 case('empty_grid', [''], error='ValueError'),
                 case('wall_at_both_ends', ['X,1\n1,X'], error='ValueError'),
             ]),
        task('run_length_decode', 'encoded_text_transform',
             'Implement decode_runs(text) in solution.py. The input is a run-length encoding where each '
             'run is written as a positive integer count immediately followed by that count of characters '
             'inside one pair of square brackets, for example 3[ab] means ababab. Counts are ASCII digits '
             'without leading zeros and may be arbitrarily large. Runs concatenate. Nested brackets are '
             'not allowed: the text inside brackets must not contain brackets. Return the fully decoded '
             'string. Raise ValueError for nonstring input, zero or multi-digit counts with a leading '
             'zero, empty or missing bracket contents, unbalanced or nested brackets, or any character '
             'outside a run pattern. Do not print from the function.', 'decode_runs', [
                 case('basic', ['3[ab]'], 'ababab'),
                 case('concat', ['2[a]3[b]'], 'aabbb'),
                 case('large_count', ['12[z]'], 'z' * 12),
                 case('single', ['1[q]'], 'q'),
                 case('spaces_inside', ['2[a b]'], 'a ba b'),
                 case('empty_content', ['2[]'], error='ValueError'),
                 case('leading_zero', ['01[a]'], error='ValueError'),
                 case('zero_count', ['0[a]'], error='ValueError'),
                 case('unbalanced', ['3[ab'], error='ValueError'),
                 case('nested', ['2[a3[b]]'], error='ValueError'),
                 case('stray_char', ['3[ab]c'], error='ValueError'),
                 case('nonstring', [123], error='ValueError'),
             ]),
        task('ledger_reconcile', 'structured_records_to_report',
             'Implement reconcile(entries_text) in solution.py. The input is a JSON array of objects, '
             'each with string account (nonempty), string side that is exactly "DR" or "CR", and integer '
             'amount (may be negative). Accounts reconcile when their total (DR adds, CR subtracts) is '
             'exactly zero. Return a dictionary mapping every account to its integer total, sorted by '
             'account name. Also include the key "__unbalanced__" whose value is the number of accounts '
             'whose total is not zero. Raise ValueError for nonstring input, malformed JSON, missing or '
             'wrong-typed fields, or an unknown side. Do not print from the function.', 'reconcile', [
                 case('balanced_pair', ['[{"account":"cash","side":"DR","amount":5},'
                                        '{"account":"cash","side":"CR","amount":5}]'],
                      {'__unbalanced__': 0, 'cash': 0}),
                 case('unbalanced', ['[{"account":"a","side":"DR","amount":3},'
                                     '{"account":"b","side":"CR","amount":1}]'],
                      {'__unbalanced__': 2, 'a': 3, 'b': -1}),
                 case('negative_amount', ['[{"account":"x","side":"DR","amount":-4}]'],
                      {'__unbalanced__': 1, 'x': -4}),
                 case('empty_array', ['[]'], {'__unbalanced__': 0}),
                 case('sort_order', ['[{"account":"z","side":"DR","amount":1},'
                                     '{"account":"a","side":"DR","amount":2}]'],
                      {'__unbalanced__': 2, 'a': 2, 'z': 1}),
                 case('bad_side', ['[{"account":"a","side":"dr","amount":1}]'], error='ValueError'),
                 case('wrong_amount_type', ['[{"account":"a","side":"DR","amount":"1"}]'], error='ValueError'),
                 case('missing_field', ['[{"account":"a","side":"DR"}]'], error='ValueError'),
                 case('empty_account', ['[{"account":"","side":"DR","amount":1}]'], error='ValueError'),
                 case('not_json', ['nope'], error='ValueError'),
                 case('nonstring', [None], error='ValueError'),
             ]),
        task('josephus_rank', 'algorithmic_indexing',
             'Implement survivor_index(n, k) in solution.py. n people stand in a circle numbered 0 '
             'through n-1. Starting at person 0 and counting around the circle, every k-th person '
             'leaves until one remains; the count includes the person you start on as 1. Return the '
             'number of the last remaining person as an integer. Raise ValueError for non-integers '
             '(bools count as non-integers), n below 1, or k below 1. Do not print from the function.',
             'survivor_index', [
                 case('classic', [7, 3], 3),
                 case('two_people', [2, 2], 0),
                 case('one_person', [1, 9], 0),
                 case('k_one', [5, 1], 4),
                 case('k_larger_than_n', [3, 7], 2),
                 case('n_two_k_one', [2, 1], 1),
                 case('bool_rejected', [True, 3], error='ValueError'),
                 case('float_rejected', [7.0, 3], error='ValueError'),
                 case('n_zero', [0, 3], error='ValueError'),
                 case('k_zero', [5, 0], error='ValueError'),
             ]),
        task('poly_hash', 'numeric_horner',
             'Implement poly_hash(text, modulus) in solution.py. Treat the text as a sequence of '
             'characters whose values are their Unicode code points. Compute the polynomial hash '
             'sum over i of value(text[i]) * 256**i, where i is the position from the left starting '
             'at 0, then return that sum reduced modulo the given modulus. Use exact integer '
             'arithmetic; modulus may be arbitrarily large. Raise ValueError for a nonstring text, '
             'a non-integer modulus (bools count as non-integers), or a modulus below 2. Do not '
             'print from the function.', 'poly_hash', [
                  case('single_char', ['a', 97], 97 % 97),
                  case('two_chars', ['ab', 1000000007], (97 + 98 * 256) % 1000000007),
                  case('empty_string', ['', 13], 0),
                  case('unicode', ['\\u00e9', 97], 2),
                 case('large_modulus', ['hello', 10**30],
                      sum(ord('hello'[i]) * 256**i for i in range(5)) % 10**30),
                 case('small_modulus', ['xyz', 2],
                      sum(ord('xyz'[i]) * 256**i for i in range(3)) % 2),
                 case('nonstring_text', [5, 97], error='ValueError'),
                 case('bool_modulus', ['a', True], error='ValueError'),
                 case('float_modulus', ['a', 97.0], error='ValueError'),
                 case('modulus_one', ['a', 1], error='ValueError'),
             ]),
        task('markdown_outline', 'nested_text_structure',
             'Implement outline_depth(text) in solution.py. The input is Markdown where heading lines '
             'start with zero or more spaces, then one or more # characters, then a single space, '
             'then title text. The leading # count minus one is the heading level: the first line '
             'has level 0, ## is level 1, and so on. Given the full text, return the maximum heading '
             'level that appears. Non-heading lines are ignored. If the text contains no heading, '
             'raise ValueError. Raise ValueError for nonstring input. A heading with zero or more '
             'than one space after the hashes, or hashes not followed by a space, is not a heading '
             'line and is ignored. Do not print from the function.', 'outline_depth', [
                 case('flat', ['# a\n# b'], 0),
                 case('nested', ['# t\n## a\n### b\n# c'], 2),
                 case('deepest_last', ['# t\n#### d'], 3),
                 case('indented_heading', ['  ## x'], 1),
                 case('ignores_prose', ['hello\n# real\nworld'], 0),
                 case('no_space_ignored', ['#nospace\n# real'], 0),
                 case('two_spaces_ignored', ['##  double\n# single'], 0),
                 case('no_heading', ['just text'], error='ValueError'),
                 case('empty', [''], error='ValueError'),
                 case('nonstring', [None], error='ValueError'),
             ]),
        task('calendar_slots', 'interval_arithmetic',
             'Implement free_minutes(busy_text) in solution.py. The input is a JSON array of '
             '[start, end] pairs of strings in 24-hour HH:MM format, representing busy intervals on '
             'one day (minutes 0 through 1439). Return the total number of minutes in the day not '
             'covered by any busy interval, counting overlapping intervals only once. Raise '
             'ValueError for nonstring input, malformed JSON, badly formatted times, end before '
             'start, or times outside the day. Do not print from the function.', 'free_minutes', [
                 case('empty_day', ['[]'], 1440),
                 case('full_day', ['[["00:00","24:00"]]'], 0),
                 case('one_hour', ['[["09:00","10:00"]]'], 1380),
                 case('overlapping', ['[["09:00","10:30"],["10:00","11:00"]]'], 1320),
                 case('adjacent', ['[["08:00","09:00"],["09:00","10:00"]]'], 1320),
                 case('unsorted', ['[["14:00","15:00"],["08:00","09:00"]]'], 1320),
                 case('end_midnight', ['[["23:00","24:00"]]'], 1380),
                 case('bad_format', ['[["9:00","10:00"]]'], error='ValueError'),
                 case('end_before_start', ['[["10:00","09:00"]]'], error='ValueError'),
                 case('outside_day', ['[["00:00","25:00"]]'], error='ValueError'),
                 case('malformed', ['not json'], error='ValueError'),
                 case('nonstring', [17], error='ValueError'),
             ]),
        task('state_machine', 'stepwise_state_transition',
             'Implement final_state(text) in solution.py. The input is a string of commands over an '
             'accumulator that starts at 0. Each command is one of: an optionally signed ASCII '
             'decimal integer, which adds to the accumulator; the single character "d", which doubles '
             'the accumulator; or the single character "r", which resets the accumulator to 0. '
             'Commands are separated by single spaces. Return the final accumulator value. Raise '
             'ValueError for nonstring input, unknown commands, double spaces, leading or trailing '
             'spaces, or empty input. Do not print from the function.', 'final_state', [
                 case('add_only', ['5 7'], 12),
                 case('double', ['3 d'], 6),
                 case('reset', ['5 r 2'], 2),
                 case('combined', ['2 3 d r 1 d'], 2),
                 case('negative', ['5 -3'], 2),
                 case('big_integers', ['99999999999999999999 1'], 100000000000000000000),
                 case('leading_zero', ['5 01'], error='ValueError'),
                 case('double_space', ['5  7'], error='ValueError'),
                 case('trailing_space', ['5 '], error='ValueError'),
                 case('unknown_command', ['5 x'], error='ValueError'),
                 case('empty', [''], error='ValueError'),
                 case('nonstring', [3.5], error='ValueError'),
             ]),
        task('matrix_spiral', 'structural_iteration',
             'Implement spiral_sum(matrix) in solution.py. The input is a list of lists of integers '
             'forming a rectangle. Walk the matrix in spiral order (right across the first row, down '
             'the right column, left across the bottom row, up the left column, then inward) and '
             'return the sum of elements in the order visited. Return 0 for an empty list. Raise '
             'ValueError for non-list input, rows that are not lists, ragged matrices, or non-integer '
             'elements (bools count as non-integers). Do not print from the function.', 'spiral_sum', [
                 case('two_by_two', [[[1, 2], [3, 4]]], 10),
                 case('three_by_three', [[[1, 2, 3], [4, 5, 6], [7, 8, 9]]], 45),
                 case('single_row', [[[1, 2, 3]]], 6),
                 case('single_column', [[[1], [2], [3]]], 6),
                 case('empty', [[]], 0),
                 case('negative_values', [[[-1, -2], [-3, -4]]], -10),
                 case('non_rectangle', [[[1, 2], [3]]], error='ValueError'),
                 case('bool_element', [[[True]]], error='ValueError'),
                 case('float_element', [[[1.5]]], error='ValueError'),
                 case('not_a_list', ['no'], error='ValueError'),
             ]),
        task('word_square', 'string_combinatorics',
             'Implement is_word_square(words) in solution.py. The input is a list of nonempty strings. '
             'It is a word square if reading the k-th character of the k-th word spells the same '
             'sequence as the k-th word itself for every k: that is, words[i][j] must equal '
             'words[j][i] for all valid i and j. Return True if the list forms a word square, False '
             'if it does not, and raise ValueError for non-list input, empty lists, nonstring or '
             'empty elements, or lists whose lengths exceed every element length (so that some pair '
             'i, j would need characters that do not exist). Do not print from the function.',
             'is_word_square', [
                  case('square', [['ball', 'area', 'lead', 'lady']], True),
                  case('single_word', [['a']], True),
                  case('two_words', [['ab', 'ba']], True),
                  case('three_by_three_square', [['cat', 'art', 'tie']], False),
                  case('false_case', [['cat', 'art', 'tie']], False),
                  case('empty_list', [[]], error='ValueError'),
                  case('empty_string_element', [['', 'a']], error='ValueError'),
                  case('nonstring_element', [['a', 5]], error='ValueError'),
                 case('not_a_list', ['abc'], error='ValueError'),
                  case('too_short', [['a', 'a', 'a']], error='ValueError'),
             ]),
    )
    return population