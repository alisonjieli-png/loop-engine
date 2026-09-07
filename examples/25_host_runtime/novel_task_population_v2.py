"""Novel-task population, version 2: prompts and oracles agree.

These are textbook problems with contract twists (minimum path sum, run-length
decoding, ledger totals, the Josephus circle, a polynomial hash, heading
depth, busy-interval union, an accumulator machine, a spiral walk, word
squares). They are novel to this repository, not to any model. Version 1 of
this population is the sealed record of the 2026-09-06 run and stays as it
is; version 2 repairs the three prompts that contradicted their own cases,
replaces the spiral sum (which no evaluator could tell from a plain sum) with
an order-sensitive weighted sum, tests a real non-ASCII code point, removes a
duplicated word-square case, and states the short-word rule in one sentence.

This module makes no model call and writes no file. The runner freezes the
population digest and its own source digests before any dispatch.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generalization_probe import ProbeTask, case, canonical

POPULATION_RECORD_TYPE = 'novel_task_campaign_population/v2'


def task(task_id, shape, prompt, entrypoint, cases, seed=None):
    return ProbeTask(task_id, shape, prompt, entrypoint,
                     seed or f'def {entrypoint}(*args):\n    raise NotImplementedError\n',
                     canonical(cases))


def task_population():
    """Ten tasks across text, data, stateful, numeric, and structural domains."""
    e_acute = 'é'
    population = (
        task('grid_path_cost', 'grid_semantics_to_scalar',
             'Implement path_cost(grid_text) in solution.py. The input is one or more lines separated '
             'by newline characters; each line holds comma-separated cells, where every cell is a '
             'nonnegative integer written in ASCII digits or the single character X (an impassable '
             'wall). Starting at the top-left cell and moving only right or down to the bottom-right '
             'cell, return the minimal sum of cell values along a valid path as an integer. If no path '
             'exists, including when the top-left or the bottom-right cell is a wall, return None. '
             'The grid must have at least one line and every line must have the same number of cells. '
             'Raise ValueError for nonstring input, empty input, ragged grids, malformed cell values, '
             'negative integers, or a wall in both the top-left and bottom-right corners. Do not print '
             'from the function.', 'path_cost', [
                 case('plain', ['1,2,3\n4,5,6\n7,8,9'], 21),
                 case('cheaper_detour', ['1,100,1\n1,100,1\n1,1,1'], 5),
                 case('wall_detour', ['1,X,9\n2,3,9\n9,9,1'], 16),
                 case('blocked', ['1,X\nX,1'], None),
                 case('start_wall', ['X,1\n1,1'], None),
                 case('end_wall', ['1,1\n1,X'], None),
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
             'string. Raise ValueError for nonstring input, a zero count, a count with a leading zero, '
             'empty or missing bracket contents, unbalanced or nested brackets, or any character '
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
             'amount (may be negative; booleans are not integers). Accounts reconcile when their total '
             '(DR adds, CR subtracts) is exactly zero. Return a dictionary mapping every account to its '
             'integer total, sorted by account name. Also include the key "__unbalanced__" whose value '
             'is the number of accounts whose total is not zero. Raise ValueError for nonstring input, '
             'malformed JSON, a top-level value that is not an array, missing or wrong-typed fields, or '
             'an unknown side. Do not print from the function.', 'reconcile', [
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
                 case('bool_amount', ['[{"account":"a","side":"DR","amount":true}]'], error='ValueError'),
                 case('missing_field', ['[{"account":"a","side":"DR"}]'], error='ValueError'),
                 case('empty_account', ['[{"account":"","side":"DR","amount":1}]'], error='ValueError'),
                 case('not_an_array', ['{"account":"a"}'], error='ValueError'),
                 case('not_json', ['nope'], error='ValueError'),
                 case('nonstring', [None], error='ValueError'),
             ]),
        task('josephus_rank', 'algorithmic_indexing',
             'Implement survivor_index(n, k) in solution.py. n people stand in a circle numbered 0 '
             'through n-1. Starting at person 0 and counting around the circle, every k-th person '
             'leaves until one remains; the count includes the person you start on as 1, and after '
             'each removal the count restarts at the next remaining person. Return the number of the '
             'last remaining person as an integer. Raise ValueError for non-integers (booleans count '
             'as non-integers), n below 1, or k below 1. Do not print from the function.',
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
             'a non-integer modulus (booleans count as non-integers), or a modulus below 2. Do not '
             'print from the function.', 'poly_hash', [
                 case('single_char', ['a', 97], 97 % 97),
                 case('two_chars', ['ab', 1000000007], (97 + 98 * 256) % 1000000007),
                 case('empty_string', ['', 13], 0),
                 case('non_ascii_code_point', [e_acute, 97], ord(e_acute) % 97),
                 case('ascii_then_non_ascii', ['a' + e_acute, 97], (97 + ord(e_acute) * 256) % 97),
                 case('astral_code_point', ['\U0001F600', 1000], 0x1F600 % 1000),
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
             'Implement outline_depth(text) in solution.py. The input is Markdown text split into lines '
             'by newline characters. A heading line is: zero or more spaces, then one or more # '
             'characters, then exactly one space, then title text whose first character is not a '
             'space. The heading level is the number of # characters minus one: # is level 0, ## is '
             'level 1, and so on. Return the maximum heading level in the text as an integer. Lines '
             'that are not heading lines are ignored, including lines whose hashes are followed by no '
             'space or by more than one space. Raise ValueError for nonstring input or for text with '
             'no heading line. Do not print from the function.', 'outline_depth', [
                 case('flat', ['# a\n# b'], 0),
                 case('nested', ['# t\n## a\n### b\n# c'], 2),
                 case('deepest_last', ['# t\n#### d'], 3),
                 case('indented_heading', ['  ## x'], 1),
                 case('ignores_prose', ['hello\n# real\nworld'], 0),
                 case('no_space_ignored', ['#nospace\n# real'], 0),
                 case('two_spaces_ignored', ['##  double\n# single'], 0),
                 case('hash_only_ignored', ['# \n## real'], 1),
                 case('no_heading', ['just text'], error='ValueError'),
                 case('empty', [''], error='ValueError'),
                 case('nonstring', [None], error='ValueError'),
             ]),
        task('calendar_slots', 'interval_arithmetic',
             'Implement free_minutes(busy_text) in solution.py. The input is a JSON array of '
             '[start, end] pairs of strings in 24-hour HH:MM format with two digits each, representing '
             'busy intervals on one day whose minutes are numbered 0 through 1439. A start names a '
             'minute from 00:00 through 23:59. An end names a minute from 00:01 through 23:59, or the '
             'single sentinel 24:00, which means the end of the day (minute 1440) and is the only '
             'time outside 00:00 through 23:59 that is accepted anywhere; it is not accepted as a '
             'start. An interval covers the minutes from its start up to but not including its end, '
             'and the end must be after the start. Return the total number of minutes in the day not '
             'covered by any busy interval, counting overlapping minutes only once. Raise ValueError '
             'for nonstring input, malformed JSON, a top-level value that is not an array, pairs that '
             'are not two strings, badly formatted times, an end that is not after its start, or times '
             'outside the ranges above. Do not print from the function.', 'free_minutes', [
                 case('empty_day', ['[]'], 1440),
                 case('full_day', ['[["00:00","24:00"]]'], 0),
                 case('one_hour', ['[["09:00","10:00"]]'], 1380),
                 case('overlapping', ['[["09:00","10:30"],["10:00","11:00"]]'], 1320),
                 case('adjacent', ['[["08:00","09:00"],["09:00","10:00"]]'], 1320),
                 case('unsorted', ['[["14:00","15:00"],["08:00","09:00"]]'], 1320),
                 case('end_midnight', ['[["23:00","24:00"]]'], 1380),
                 case('bad_format', ['[["9:00","10:00"]]'], error='ValueError'),
                 case('end_before_start', ['[["10:00","09:00"]]'], error='ValueError'),
                 case('zero_length', ['[["09:00","09:00"]]'], error='ValueError'),
                 case('sentinel_as_start', ['[["24:00","24:00"]]'], error='ValueError'),
                 case('outside_day', ['[["00:00","25:00"]]'], error='ValueError'),
                 case('bad_pair_shape', ['[["09:00"]]'], error='ValueError'),
                 case('malformed', ['not json'], error='ValueError'),
                 case('nonstring', [17], error='ValueError'),
             ]),
        task('state_machine', 'stepwise_state_transition',
             'Implement final_state(text) in solution.py. The input is a string of commands over an '
             'accumulator that starts at 0. Each command is one of: an integer written in ASCII '
             'decimal digits with an optional leading + or - sign and no leading zeros (the single '
             'digit 0 is allowed, alone or signed), which adds to the accumulator; the single '
             'character "d", which doubles the accumulator; or the single character "r", which resets '
             'the accumulator to 0. Commands are separated by exactly one space. Return the final '
             'accumulator value as an integer. Raise ValueError for nonstring input, unknown commands, '
             'an integer with a leading zero, double spaces, leading or trailing spaces, or empty '
             'input. Do not print from the function.', 'final_state', [
                 case('add_only', ['5 7'], 12),
                 case('double', ['3 d'], 6),
                 case('reset', ['5 r 2'], 2),
                 case('combined', ['2 3 d r 1 d'], 2),
                 case('negative', ['5 -3'], 2),
                 case('plus_sign', ['+5 2'], 7),
                 case('signed_zero', ['+0 -0 4'], 4),
                 case('big_integers', ['99999999999999999999 1'], 100000000000000000000),
                 case('leading_zero', ['5 01'], error='ValueError'),
                 case('signed_leading_zero', ['5 -01'], error='ValueError'),
                 case('double_space', ['5  7'], error='ValueError'),
                 case('trailing_space', ['5 '], error='ValueError'),
                 case('unknown_command', ['5 x'], error='ValueError'),
                 case('empty', [''], error='ValueError'),
                 case('nonstring', [3.5], error='ValueError'),
             ]),
        task('matrix_spiral', 'structural_iteration',
             'Implement spiral_weighted_sum(matrix) in solution.py. The input is a list of lists of '
             'integers forming a rectangle. Walk the matrix in spiral order: right across the first '
             'row, down the right column, left across the bottom row, up the left column, then inward '
             'the same way until every element has been visited exactly once. Number the visited '
             'elements 1, 2, 3, ... in visiting order and return the sum of each element multiplied '
             'by its visit number, as an integer. Return 0 for an empty list. Raise ValueError for '
             'non-list input, rows that are not lists, ragged matrices, or non-integer elements '
             '(booleans count as non-integers). Do not print from the function.', 'spiral_weighted_sum', [
                 case('two_by_two', [[[1, 2], [3, 4]]], 1 * 1 + 2 * 2 + 4 * 3 + 3 * 4),
                 case('three_by_three', [[[1, 2, 3], [4, 5, 6], [7, 8, 9]]],
                      1 * 1 + 2 * 2 + 3 * 3 + 6 * 4 + 9 * 5 + 8 * 6 + 7 * 7 + 4 * 8 + 5 * 9),
                 case('two_by_three', [[[1, 2, 3], [4, 5, 6]]],
                      1 * 1 + 2 * 2 + 3 * 3 + 6 * 4 + 5 * 5 + 4 * 6),
                 case('three_by_two', [[[1, 2], [3, 4], [5, 6]]],
                      1 * 1 + 2 * 2 + 4 * 3 + 6 * 4 + 5 * 5 + 3 * 6),
                 case('single_row', [[[1, 2, 3]]], 1 * 1 + 2 * 2 + 3 * 3),
                 case('single_column', [[[1], [2], [3]]], 1 * 1 + 2 * 2 + 3 * 3),
                 case('single_cell', [[[7]]], 7),
                 case('empty', [[]], 0),
                 case('negative_values', [[[-1, -2], [-3, -4]]], -1 * 1 + -2 * 2 + -4 * 3 + -3 * 4),
                 case('non_rectangle', [[[1, 2], [3]]], error='ValueError'),
                 case('bool_element', [[[True]]], error='ValueError'),
                 case('float_element', [[[1.5]]], error='ValueError'),
                 case('row_not_list', [[1, 2]], error='ValueError'),
                 case('not_a_list', ['no'], error='ValueError'),
             ]),
        task('word_square', 'string_combinatorics',
             'Implement is_word_square(words) in solution.py. The input is a list of nonempty strings. '
             'Let n be the number of words. Every word must have at least n characters; if any word '
             'is shorter than n, raise ValueError. The list is a word square when words[i][j] equals '
             'words[j][i] for every i and j from 0 through n-1; characters at index n or beyond are '
             'ignored. Return True for a word square and False otherwise. Raise ValueError for non-list '
             'input, an empty list, or elements that are not nonempty strings. Do not print from the '
             'function.', 'is_word_square', [
                 case('four_by_four_square', [['ball', 'area', 'lead', 'lady']], True),
                 case('single_word', [['a']], True),
                 case('two_words', [['ab', 'ba']], True),
                 case('three_by_three_square', [['cat', 'are', 'ted']], True),
                 case('three_by_three_not_square', [['cat', 'art', 'tie']], False),
                 case('longer_words_ignore_extra_characters', [['abc', 'bcd']], True),
                 case('longer_words_still_compared', [['abc', 'xbd']], False),
                 case('empty_list', [[]], error='ValueError'),
                 case('empty_string_element', [['', 'a']], error='ValueError'),
                 case('nonstring_element', [['a', 5]], error='ValueError'),
                 case('not_a_list', ['abc'], error='ValueError'),
                 case('short_word', [['ab', 'a']], error='ValueError'),
                 case('all_too_short', [['a', 'a', 'a']], error='ValueError'),
             ]),
    )
    return population
