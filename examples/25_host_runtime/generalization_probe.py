"""Five frozen host tasks using one manifest-driven operation surface.

The default command prints the proposed population without model calls or file
writes. Live execution requires both explicit grant flags and a new work root.
Verifiers are host-owned; only solution.py is model-editable. This is a small
task-shape regression probe, not evidence of pretraining-unseen generalization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import threading
from dataclasses import dataclass, field, replace
from html.parser import HTMLParser
from pathlib import Path

from loop_engine import SolveRequest, solve_task
from loop_engine.code_nodes.solution_model_port import ModelExecution
from loop_engine.core.capability_directory import CapabilityDirectory, CapabilityHandshake, Endpoint
from loop_engine.core.host_runtime import HostOperationBinding, HostRuntimeBinding
from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig
from loop_engine.core.workspace_backends import (
    CommandRequest, DockerResourceLimits, DockerWorkspace, DockerWorkspaceDeclaration,
    FileOperation, FileRequest, RestrictedLocalWorkspace, WorkspaceSpec,
)
from loop_engine.loop.effect_approval import ApprovalDecision, EffectClass, EffectSpec
from loop_engine.templates.intake import TaskIntakeRequest, intake_task

IMAGE = 'python@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3'
OPERATIONS = ('workspace_inspect', 'workspace_replace', 'workspace_run')
SOURCE_DIGEST_PURPOSE = (
    'Copy the exact current source digest returned by workspace_inspect. '
    'This precondition refers to existing solution.py bytes, not the proposed new content hash.')
HOST_INSTRUCTIONS = (
    ' Use the same registered workspace_inspect, workspace_replace, and workspace_run host operations. '
    'Keep work in the declared host-managed source. The host independently verifies outputs. '
    'Return the verified host execution result.')
PYTHON_CONSTANT_NAMES = ('nan', 'positive_infinity', 'negative_infinity')
WORKER = '''import copy, importlib.util, io, json, math
from contextlib import redirect_stdout
from pathlib import Path
constants = {'nan': float('nan'), 'positive_infinity': float('inf'),
             'negative_infinity': float('-inf')}
def observed_value(value):
    if type(value) is float and not math.isfinite(value):
        return {'probe_nonfinite_float': repr(value)}
    if type(value) is tuple:
        return {'probe_tuple': [observed_value(item) for item in value]}
    if type(value) is list:
        return [observed_value(item) for item in value]
    if type(value) is dict:
        return {key: observed_value(item) for key, item in value.items()}
    return value
contract = json.loads(Path('probe-input.json').read_text())
spec = importlib.util.spec_from_file_location('candidate_solution', 'solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
function = getattr(module, contract['entrypoint'])
observations = []
for case in contract['cases']:
    arguments = copy.deepcopy(case['arguments'])
    for binding in case.get('python_constants', []):
        target = arguments
        for position in binding['path'][:-1]:
            target = target[position]
        target[binding['path'][-1]] = constants[binding['name']]
    before = copy.deepcopy(arguments)
    captured = io.StringIO()
    try:
        with redirect_stdout(captured):
            value = function(*arguments)
        error = None
    except Exception as exc:
        value, error = None, type(exc).__name__
    observations.append({'case_id': case['case_id'], 'value': observed_value(value), 'error': error,
        'input_unchanged': observed_value(arguments) == observed_value(before), 'stdout': captured.getvalue()})
print(json.dumps({'cases': observations}, ensure_ascii=False, allow_nan=False))
'''


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate observation key')
        result[key] = value
    return result


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(canonical(value) + '\n')


@dataclass(frozen=True)
class ProbeTask:
    task_id: str
    shape: str
    prompt: str
    entrypoint: str
    initial_source: str
    cases_json: str

    def __post_init__(self):
        if not re.fullmatch(r'[a-z][a-z0-9_]*', self.task_id):
            raise ValueError('invalid task identity')
        if not re.fullmatch(r'[a-z][a-z0-9_]*', self.entrypoint):
            raise ValueError('invalid entrypoint')
        cases = json.loads(self.cases_json)
        if not cases or len({case['case_id'] for case in cases}) != len(cases):
            raise ValueError('test cases must be nonempty with unique IDs')
        for item in cases:
            validate_python_constants(item)
            validate_failure_note(item)
        object.__setattr__(self, 'cases_json', canonical(cases))

    @property
    def cases(self):
        return json.loads(self.cases_json)

    def manifest(self):
        return {key: value for key, value in {
                **self.__dict__, 'cases': self.cases, 'effective_prompt': self.prompt + HOST_INSTRUCTIONS,
                'editable_files': ['solution.py'],
                'worker_digest': hashlib.sha256(WORKER.encode()).hexdigest(),
                'argument_codec': 'trusted_python_float_constants/v1',
                'evaluator': 'host_fixed_comparisons/v3'}.items() if key != 'cases_json'}

    @property
    def content_digest(self):
        return digest(self.manifest())


def validate_python_constants(value):
    bindings = value.get('python_constants', [])
    if not isinstance(bindings, list):
        raise ValueError('python_constants must be an array')
    paths = set()
    for binding in bindings:
        if (not isinstance(binding, dict) or set(binding) != {'name', 'path'}
                or binding['name'] not in PYTHON_CONSTANT_NAMES
                or not isinstance(binding['path'], list) or not binding['path']
                or any(type(index) is not int or index < 0 for index in binding['path'])):
            raise ValueError('unsupported trusted Python constant binding')
        path = tuple(binding['path'])
        if path in paths:
            raise ValueError('duplicate trusted Python constant path')
        paths.add(path)
        target = value['arguments']
        for index in path:
            if not isinstance(target, list) or index >= len(target):
                raise ValueError('Python constant path must select an existing list position')
            target = target[index]
        if target is not None:
            raise ValueError('Python constants replace only explicit null placeholders')


def validate_failure_note(value):
    if 'failure_note' in value and (type(value['failure_note']) is not str
            or not value['failure_note'].strip() or len(value['failure_note']) > 1024):
        raise ValueError('failure_note must be bounded nonempty host-authored text')


def case(name, arguments, expected=None, *, error=None, comparison='exact', artifact='', python_constants=(),
         failure_note=None):
    value = {'case_id': name, 'arguments': arguments, 'expected': expected,
             'error': error, 'comparison': comparison, 'artifact': artifact}
    if python_constants:
        value['python_constants'] = list(python_constants)
    if failure_note is not None:
        value['failure_note'] = failure_note
    validate_python_constants(value)
    validate_failure_note(value)
    return value


def task_population():
    """Authored after the targeted core changes; names never choose runtime behavior."""
    def task(task_id, shape, prompt, entrypoint, cases, seed=None):
        return ProbeTask(task_id, shape, prompt, entrypoint,
                         seed or f'def {entrypoint}(*args):\n    raise NotImplementedError\n', canonical(cases))
    schedule = {'a': [0, 2], 'b': [2, 7], 'c': [2, 3], 'd': [7, 9]}
    tasks = [
        {'id': 'd', 'duration': 2, 'dependencies': ['b', 'c']},
        {'id': 'b', 'duration': 5, 'dependencies': ['a']},
        {'id': 'a', 'duration': 2, 'dependencies': []},
        {'id': 'c', 'duration': 1, 'dependencies': ['a']},
    ]
    html_items = {'<img src=x onerror=alert(1)>': [2, 5], 'A&B': [0, 2]}
    population = (
        task('duration_utility', 'text_to_scalar',
             'Implement to_seconds(text) in solution.py. Accept stripped MM:SS or HH:MM:SS using '
             'one or more ASCII digits per component. Hours are unbounded nonnegative integers; '
             'minutes and seconds are integers from 0 through 59. Return total seconds as an integer. '
             'Raise ValueError for nonstrings, signs, decimals, missing fields, non-ASCII digits, '
             'or any out-of-range component. Do not print from the function.', 'to_seconds', [
                 case('minutes', ['02:03'], 123), case('hours', ['125:04:05'], 450245),
                 case('trimmed', [' 0:00 '], 0), case('bad_minutes', ['60:01'], error='ValueError'),
                 case('bad_seconds', ['1:02:60'], error='ValueError'),
                 case('empty_component', ['1::2'], error='ValueError'),
                 case('negative', ['-1:02'], error='ValueError'),
                 case('wrong_type', [None], error='ValueError'),
                 case('unicode_digits', ['١:02'], error='ValueError'),
             ]),
        task('sales_aggregation', 'tabular_to_grouped_records',
             'Implement summarize_sales(csv_text) in solution.py. Parse CSV with exact required columns '
             'department,quantity,unit_price (additional columns may be ignored). Sum integer quantities '
             'and quantity times unit_price per department. Negative quantities are valid returns. '
             'Prices must be nonnegative decimal strings with exactly two fractional digits. Use exact '
             'decimal arithmetic. Return a department-sorted list of dictionaries with department, '
             'quantity, and total (a two-decimal string). Empty data returns []. Reject missing columns, '
             'empty department, malformed quantity/price, and nonstring input with ValueError. Do not '
             'print from the function.', 'summarize_sales', [
                 case('groups', ['department,quantity,unit_price\nB,2,1.10\nA,3,0.10\nB,-1,1.10\n'],
                      [{'department': 'A', 'quantity': 3, 'total': '0.30'},
                       {'department': 'B', 'quantity': 1, 'total': '1.10'}]),
                 case('quoted', ['department,quantity,unit_price\n"A,B",7,0.10\n'],
                      [{'department': 'A,B', 'quantity': 7, 'total': '0.70'}]),
                 case('empty', ['department,quantity,unit_price\n'], []),
                 case('columns', ['department,quantity\nA,1\n'], error='ValueError'),
                 case('price', ['department,quantity,unit_price\nA,1,NaN\n'], error='ValueError'),
                 case('quantity', ['department,quantity,unit_price\nA,1.5,1.00\n'], error='ValueError'),
                 case('negative_price', ['department,quantity,unit_price\nA,1,-1.00\n'], error='ValueError'),
                 case('wrong_type', [None], error='ValueError'),
                 case('empty_department', ['department,quantity,unit_price\n,1,1.00\n'], error='ValueError'),
                 case('price_precision', ['department,quantity,unit_price\nA,1,1.0\n'], error='ValueError'),
             ]),
        task('dependency_schedule', 'constraints_to_schedule',
             'Implement schedule(tasks) in solution.py. Each task is a dictionary with unique nonempty '
             'string id, positive integer duration (not bool), and a list of unique dependency IDs. '
             'Unlimited tasks may run in parallel. Return {id: [earliest_start, earliest_end]} with '
             'time zero as the origin and every dependency finished before its dependent starts. '
             'Input order is irrelevant and input must not be mutated. Empty input returns {}. '
             'Raise ValueError on wrong input shapes, duplicate IDs/dependencies, unknown dependencies, '
             'nonpositive/bool durations, or cycles. Do not print from the function.', 'schedule', [
                 case('fork_join', [tasks], schedule),
                 case('renamed', [[{'id': 'finish', 'duration': 4, 'dependencies': ['early']},
                                  {'id': 'early', 'duration': 3, 'dependencies': []}]],
                      {'early': [0, 3], 'finish': [3, 7]}),
                 case('empty', [[]], {}),
                 case('cycle', [[{'id': 'x', 'duration': 1, 'dependencies': ['x']}]], error='ValueError'),
                 case('unknown', [[{'id': 'x', 'duration': 1, 'dependencies': ['y']}]], error='ValueError'),
                 case('bool_duration', [[{'id': 'x', 'duration': True, 'dependencies': []}]], error='ValueError'),
                 case('duplicate', [[{'id': 'x', 'duration': 1, 'dependencies': []}] * 2], error='ValueError'),
                 case('wrong_shape', [None], error='ValueError'),
                 case('duplicate_dependencies', [[{'id': 'a', 'duration': 1, 'dependencies': []},
                     {'id': 'b', 'duration': 1, 'dependencies': ['a', 'a']}]], error='ValueError'),
                 case('zero_duration', [[{'id': 'x', 'duration': 0, 'dependencies': []}]], error='ValueError'),
                 case('negative_duration', [[{'id': 'x', 'duration': -2, 'dependencies': []}]], error='ValueError'),
             ]),
        task('schedule_html', 'structured_data_to_safe_document',
             'Implement render_schedule(schedule, title) in solution.py. Input schedule maps nonempty '
             'task names to [start, end] integer pairs with 0 <= start <= end, excluding booleans. '
             'Return a complete HTML document string with one h1 whose text is exactly title and '
             'one element per task with data-task, data-start, and data-end attributes. Include the '
             'task name as visible text. Order task elements by start then task name. Escape all '
             'task names and title for their HTML context. Do not include scripts, external resources, '
             'embedded objects, event-handler attributes, or javascript URLs. Empty schedules are '
             'valid. Invalid inputs raise ValueError. Inputs must not be mutated. The host captures '
             'the first returned document as schedule.html; return HTML itself, not a generator script.',
             'render_schedule', [
                 case('hostile_labels', [html_items, '<Review & plan>'],
                      {'schedule': html_items, 'title': '<Review & plan>'},
                      comparison='schedule_html', artifact='schedule.html'),
                 case('empty', [{}, 'Empty'], {'schedule': {}, 'title': 'Empty'}, comparison='schedule_html'),
                 case('reversed', [{'x': [3, 2]}, 'Bad'], error='ValueError'),
                 case('bool_time', [{'x': [False, 2]}, 'Bad'], error='ValueError'),
                 case('wrong_title', [{'x': [0, 2]}, None], error='ValueError'),
             ]),
        task('interval_repair', 'existing_source_repair',
             'Repair merge_intervals(intervals) in the existing solution.py. Input is a list of '
             'two-item lists of finite integers or floats, excluding booleans, with start <= end. '
             'Return sorted merged intervals, merging overlaps and touching endpoints. Empty input '
             'returns []. Never mutate the caller input. Raise ValueError for invalid outer/inner '
             'shapes, booleans, nonnumbers, nonfinite values, or reversed intervals. Preserve the '
             'function name and do not print.', 'merge_intervals', [
                 case('unsorted_touching', [[[5, 7], [1, 3], [3, 6], [10, 11]]], [[1, 7], [10, 11]]),
                 case('nested', [[[1, 10], [2, 3]]], [[1, 10]]), case('empty', [[]], []),
                 case('point', [[[2, 2], [2, 4]]], [[2, 4]]),
                 case('reversed', [[[5, 1]]], error='ValueError'),
                 case('bool', [[[False, 2]]], error='ValueError'),
                 case('bad_shape', [[[1, 2, 3]]], error='ValueError'),
             ], seed='''def merge_intervals(intervals):
    intervals.sort()
    result = []
    for start, end in intervals:
        if result and start < result[-1][1]:
            result[-1][1] = end
        else:
            result.append([start, end])
    return result
'''),
    )
    additional = audit_regression_cases()
    return tuple(replace(item, cases_json=canonical(
        item.cases + additional.get(item.task_id, []))) for item in population)


def audit_regression_cases():
    """Post-run counterexamples and clear controls; original prompts stay unchanged."""
    header = 'department,quantity,unit_price\n'
    large = 10 ** 28
    sales = [
        case('quoted_embedded_newline', [header + '"North\nWest",2,1.25\n'],
             [{'department': 'North\nWest', 'quantity': 2, 'total': '2.50'}]),
        case('reordered_columns_with_ignored_extra', [
            'ignored,unit_price,department,quantity\nanything,1.20,West,2\n'],
             [{'department': 'West', 'quantity': 2, 'total': '2.40'}]),
        case('quoted_quote_in_department', [header + '"A""B",1,0.50\n'],
             [{'department': 'A"B', 'quantity': 1, 'total': '0.50'}]),
        case('row_permutation', [header + 'West,-2,1.20\nEast,3,0.20\nWest,5,1.20\n'],
             [{'department': 'East', 'quantity': 3, 'total': '0.60'},
              {'department': 'West', 'quantity': 3, 'total': '3.60'}]),
        case('zero_net_quantity_retains_group', [header + 'West,3,0.10\nWest,-3,0.10\n'],
             [{'department': 'West', 'quantity': 0, 'total': '0.00'}]),
        case('exact_large_integer_cancellation', [
            header + f'West,{large + 1},0.01\nWest,{-large},0.01\n'],
             [{'department': 'West', 'quantity': 1, 'total': '0.01'}]),
        case('exact_long_decimal_price', [header + 'West,1,1234567890123456789012345678.90\n'],
             [{'department': 'West', 'quantity': 1, 'total': '1234567890123456789012345678.90'}]),
        case('missing_row_price', [header + 'West,2\n'], error='ValueError'),
    ]
    exactness_note = (
        'The existing contract requires exact arithmetic for valid quantities and two-decimal prices; '
        'it states no significant-digit ceiling. A fixed precision cap merely moves the failure boundary. '
        'An exact representation or input-derived precision is compatible with the contract; '
        'required totals must preserve all significant digits, cancellation, and two-decimal formatting.')

    def total_text(cents):
        return ('-' if cents < 0 else '') + str(abs(cents) // 100) + '.' + str(abs(cents) % 100).zfill(2)

    for digits, quantity, fraction in ((231, 3, 17), (517, 7, 43), (1021, 11, 89)):
        magnitude = 10 ** (digits - 1) + 12345
        price = str(magnitude) + '.' + str(fraction).zfill(2)
        sales.extend((
            case(f'exact_magnitude_price_{digits}_digits', [header + f'West,{quantity},{price}\n'],
                 [{'department': 'West', 'quantity': quantity,
                   'total': total_text(quantity * (magnitude * 100 + fraction))}], failure_note=exactness_note),
            case(f'exact_price_cancellation_{digits}_digits', [
                header + f'West,{quantity},{price}\nWest,-1,{quantity * magnitude}.00\n'],
                 [{'department': 'West', 'quantity': quantity - 1, 'total': total_text(quantity * fraction)}],
                 failure_note=exactness_note),
            case(f'exact_quantity_cancellation_{digits}_digits', [
                header + f'West,{magnitude + quantity},0.07\nWest,{-magnitude},0.07\n'],
                 [{'department': 'West', 'quantity': quantity, 'total': total_text(quantity * 7)}],
                 failure_note=exactness_note),
        ))
    padding = '0' * 5000
    duration_length_note = (
        'The supplied duration components contain only ASCII digits and their values satisfy the '
        'original range constraints. Leading zeros do not change those values. The task declares '
        'no representation-length ceiling, so rejecting this valid representation violates the contract.')
    sales_length_note = (
        'This field is a valid integer quantity or nonnegative two-decimal price. Leading zeros '
        'do not change its mathematical value. The original task declares no field-length ceiling; '
        'the required exact result still applies to this representation.')
    durations = [case('zero_padded_hours_5001_digits', [padding + '1:00:00'], 3600,
                      failure_note=duration_length_note)]
    sales.extend((
        case('zero_padded_integer_quantity_5001_digits', [header + 'A,' + padding + '1,1.00\n'],
             [{'department': 'A', 'quantity': 1, 'total': '1.00'}], failure_note=sales_length_note),
        case('zero_padded_decimal_whole_5001_digits', [header + 'A,1,' + padding + '1.00\n'],
             [{'department': 'A', 'quantity': 1, 'total': '1.00'}], failure_note=sales_length_note),
        case('significant_quantity_cancellation_5001_digits', [
            header + 'A,1' + '0' * 4999 + '1,0.01\nA,-1' + '0' * 5000 + ',0.01\n'],
             [{'department': 'A', 'quantity': 1, 'total': '0.01'}],
             failure_note=(
                 'The quantities are valid decimal integers and the exact result after cancellation '
                 'is within the required output contract. The original task declares no significant-digit '
                 'ceiling; rejection of these valid inputs violates the same exact-arithmetic requirement.')),
    ))
    significant_price = '1' + '0' * 4298 + '83'
    product_operand = '1' + '0' * 2597 + '83'
    # (10**2599 + 83)**2, written exactly without a guarded int-to-string conversion.
    product_total = '1' + '0' * 2596 + '166' + '0' * 2595 + '6889.00'
    sales.extend((
        case('significant_price_cancellation_4301_digits', [
            header + 'A,1,' + significant_price + '.01\nA,-1,' + significant_price + '.00\n'],
             [{'department': 'A', 'quantity': 0, 'total': '0.01'}],
             failure_note=(
                 'Both prices satisfy the original nonnegative two-decimal format. Their required '
                 'net total remains exact after cancellation. The task declares no price-digit ceiling.')),
        case('large_product_decimal_formatting_2600_digits', [
            header + 'A,' + product_operand + ',' + product_operand + '.00\n'],
             [{'department': 'A', 'quantity': 10 ** 2599 + 83, 'total': product_total}],
             failure_note=(
                 'The quantity and price satisfy the original input contract. The exact total must '
                 'be returned as a two-decimal string; the task declares no output-digit ceiling. '
                 'This expected output is a finite string within the declared probe transport capacity.')),
    ))
    dag = [
        {'id': 'end', 'duration': 3, 'dependencies': ['left', 'right']},
        {'id': 'right', 'duration': 7, 'dependencies': ['start']},
        {'id': 'start', 'duration': 2, 'dependencies': []},
        {'id': 'left', 'duration': 4, 'dependencies': ['start']},
    ]
    expected = {'start': [0, 2], 'left': [2, 6], 'right': [2, 9], 'end': [9, 12]}
    schedules = [
        case('diamond_with_new_durations', [dag], expected),
        case('input_permutation', [list(reversed(dag))], expected),
        case('duration_scaling', [[{**item, 'duration': item['duration'] * 3} for item in dag]],
             {key: [value * 3 for value in times] for key, times in expected.items()}),
        case('independent_component', [dag + [{'id': 'separate', 'duration': 10, 'dependencies': []}]],
             {**expected, 'separate': [0, 10]}),
        case('unhashable_list_dependency', [[{'id': 'task', 'duration': 1, 'dependencies': [[]]}]],
             error='ValueError'),
        case('unhashable_object_dependency', [[{'id': 'task', 'duration': 1, 'dependencies': [{}]}]],
             error='ValueError'),
        case('three_vertex_cycle', [[{'id': 'a', 'duration': 1, 'dependencies': ['c']},
             {'id': 'b', 'duration': 1, 'dependencies': ['a']},
             {'id': 'c', 'duration': 1, 'dependencies': ['b']}]], error='ValueError'),
        case('fractional_duration', [[{'id': 'task', 'duration': 1.5, 'dependencies': []}]],
             error='ValueError'),
    ]
    ranges = [[7, 8], [-3, 0], [-5, -4], [-4, -3], [0, 3], [8, 8]]
    huge = 10 ** 400
    intervals = [
        case('negative_touching_and_disconnected', [ranges], [[-5, 3], [7, 8]]),
        case('input_permutation', [list(reversed(ranges))], [[-5, 3], [7, 8]]),
        case('fractional_endpoints', [[[0.5, 1.25], [1.25, 2.0], [-0.5, 0.5]]], [[-0.5, 2.0]]),
        case('already_merged_union', [[[-5, 3], [7, 8]]], [[-5, 3], [7, 8]]),
        case('large_finite_integer_endpoints', [[[huge, huge + 2]]], [[huge, huge + 2]]),
    ]
    for constant in PYTHON_CONSTANT_NAMES:
        for endpoint in (0, 1):
            bounds = [0.0, 1.0]
            bounds[endpoint] = None
            intervals.append(case(f'{constant}_endpoint_{endpoint}', [[bounds]], error='ValueError',
                python_constants=({'name': constant, 'path': [0, 0, endpoint]},)))
    return {'duration_utility': durations, 'sales_aggregation': sales,
            'dependency_schedule': schedules, 'interval_repair': intervals}


class _ScheduleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tasks, self.text, self.headings, self.stack, self.unsafe = [], [], [], [], False
        self.has_html = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.has_html |= tag == 'html'
        self.unsafe |= tag in ('script', 'iframe', 'object', 'embed', 'img', 'svg', 'link', 'base', 'form')
        self.unsafe |= any(key.lower().startswith('on') or key.lower() in ('src', 'href')
                           or 'javascript:' in str(value).lower()
                           or re.search(r'@import|url\s*\(', str(value), re.IGNORECASE)
                           for key, value in attributes)
        self.unsafe |= tag == 'meta' and attrs.get('http-equiv', '').lower() == 'refresh'
        self.unsafe |= len(attrs) != len(attributes)
        if 'data-task' in attrs:
            self.tasks.append((attrs['data-task'], attrs.get('data-start'), attrs.get('data-end')))
        self.stack.append(tag)
        if tag == 'h1':
            self.headings.append('')

    def handle_endtag(self, tag):
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]

    def handle_data(self, data):
        self.text.append(data)
        if 'style' in self.stack and re.search(r'@import|url\s*\(', data, re.IGNORECASE):
            self.unsafe = True
        if 'h1' in self.stack and self.headings:
            self.headings[-1] += data


def compare_html(value, expected):
    if (not isinstance(value, str) or not value.strip().lower().startswith('<!doctype html')
            or not value.rstrip().lower().endswith('</html>')):
        return False
    document = _ScheduleHTML()
    try:
        document.feed(value)
        document.close()
    except (ValueError, TypeError):
        return False
    items = sorted(expected['schedule'].items(), key=lambda item: (item[1][0], item[0]))
    return (document.has_html and not document.unsafe and document.headings == [expected['title']]
            and document.tasks == [(key, str(times[0]), str(times[1])) for key, times in items]
            and all(key in ''.join(document.text) for key, _ in items))


def evaluate(task, execution):
    """Compare observations outside the candidate container, with frozen expectations."""
    if (execution.get('ok') is not True or execution.get('exit_code') != 0
            or execution.get('output_truncated') is not False):
        return {'passed': False, 'checks': [], 'failure_kind': 'execution_failed'}
    try:
        raw = json.loads(execution['stdout'], object_pairs_hook=_unique_object,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        actual = raw['cases']
        if set(raw) != {'cases'} or not isinstance(actual, list) or len(actual) != len(task.cases):
            raise ValueError('observation shape')
        checks = []
        for expected, observed in zip(task.cases, actual):
            shape = (isinstance(observed, dict) and set(observed) ==
                     {'case_id', 'value', 'error', 'input_unchanged', 'stdout'})
            base = (shape and observed['case_id'] == expected['case_id']
                    and observed['input_unchanged'] is True and observed['stdout'] == ''
                    and observed['error'] == expected['error'])
            matches = (compare_html(observed['value'], expected['expected'])
                       if expected['comparison'] == 'schedule_html' and expected['error'] is None
                       else canonical(observed['value']) == canonical(expected['expected'])) if shape else False
            check = {'case_id': expected['case_id'], 'passed': bool(base and matches),
                     'observed': observed, 'expected': expected['expected'],
                     'expected_error': expected['error']}
            if not check['passed'] and expected.get('failure_note'):
                check['failure_note'] = expected['failure_note']
            checks.append(check)
        return {'passed': all(item['passed'] for item in checks), 'checks': checks,
                'failure_kind': '' if all(item['passed'] for item in checks) else 'contract_failed'}
    except (ValueError, TypeError, KeyError):
        return {'passed': False, 'checks': [], 'failure_kind': 'invalid_observation'}


def feedback(comparison):
    """Model-visible observations without the host's expected-answer values."""
    return {'passed': comparison['passed'], 'failure_kind': comparison['failure_kind'],
            'checks': [{key: value for key, value in item.items()
                        if key not in ('expected', 'expected_error')
                        and (key != 'failure_note' or item.get('passed') is False)}
                       for item in comparison['checks']]}


def model_usage_summary(outcome):
    rows = outcome.model_usage
    known = {name: sum(row[name] for row in rows if type(row.get(name)) is int)
             for name in ('input_tokens', 'output_tokens')}
    count = sum(row['physical_model_calls'] for row in rows if type(row.get('physical_model_calls')) is int)
    complete = (outcome.model_call_accounting_complete is True and count == outcome.model_calls
                and all(row.get('accounting_complete') is True
                        and all(type(row.get(name)) is int for name in known) for row in rows))
    return {'input_tokens': known['input_tokens'] if complete else None,
            'output_tokens': known['output_tokens'] if complete else None,
            'known_input_tokens_subtotal': known['input_tokens'],
            'known_output_tokens_subtotal': known['output_tokens'], 'token_accounting_complete': complete,
            'cost_usd': None, 'cost_state': 'unknown_no_qualified_price_accounting'}


def docker_workspace(workspace, image):
    return DockerWorkspace(WorkspaceSpec(
        'generalization-probe', str(workspace), backend_kind='docker', execution_enabled=True,
        allowed_commands=('python',), network_access=False), DockerWorkspaceDeclaration(
            image, workspace_read_only=True, limits=DockerResourceLimits(
                memory='512m', cpus=1.0, pids=64, temporary_bytes=64 * 1024 * 1024)))


def docker_probe(workspace, image):
    backend = docker_workspace(workspace, image)
    availability = backend.availability()
    if not availability.available:
        raise RuntimeError('Pinned Python Docker image unavailable; no image download is authorized.')
    result = backend.command(CommandRequest(
        ('python', '-B', 'probe.py'), timeout_seconds=30, max_output_bytes=262144,
        execution_authorized=True))
    return {'ok': result.ok, 'exit_code': result.exit_code, 'stdout': result.stdout,
            'stderr': result.stderr, 'error_code': result.error_code,
            'output_truncated': result.output_truncated, 'image': image,
            'backend': 'docker', 'workspace_read_only': True, 'network': False}


EVALUATOR_FIELDS = frozenset({'cases', 'worker_digest', 'evaluator', 'argument_codec'})


def task_semantics(manifest):
    return {key: value for key, value in manifest.items() if key not in EVALUATOR_FIELDS}


def evaluator_digest(manifest):
    return digest({key: manifest.get(key) for key in sorted(EVALUATOR_FIELDS)})


def ordinary_file(path):
    """Read existing local provenance without following a declared symlink."""
    path = Path(path).absolute()
    if any(item.is_symlink() for item in (path, *path.parents)) or not path.is_file():
        raise ValueError('follow-up provenance must be an existing ordinary file')
    backend = RestrictedLocalWorkspace(WorkspaceSpec('probe-followup-read', str(path.parent)))
    result = backend.file(FileRequest(FileOperation.READ, path.name))
    if not result.ok or hashlib.sha256(result.content).hexdigest() != result.digest:
        raise ValueError('follow-up provenance could not be read with exact identity')
    return path, result.content, result.digest


def require_file_bindings(bindings):
    for path, expected in bindings.items():
        if ordinary_file(path)[2] != expected:
            raise ValueError('follow-up source or provenance changed after capture')


@dataclass(frozen=True)
class ProbeSeedSource:
    """Exact prior working bytes; reuse grants no verification or acceptance."""

    content: bytes = field(repr=False)
    source_path: str
    source_digest: str
    semantic_digest: str
    parent_task_digest: str
    provenance_json: str

    def __post_init__(self):
        if (not isinstance(self.content, bytes) or len(self.content) > 65536
                or hashlib.sha256(self.content).hexdigest() != self.source_digest):
            raise ValueError('seed source requires exact bounded bytes')
        self.content.decode('utf-8')
        if any(not re.fullmatch(r'[a-f0-9]{64}', value)
               for value in (self.source_digest, self.semantic_digest, self.parent_task_digest)):
            raise ValueError('seed source requires exact source and task identities')
        provenance = json.loads(self.provenance_json)
        if (not isinstance(provenance, dict) or not isinstance(provenance.get('file_hashes'), dict)
                or provenance['file_hashes'].get(self.source_path) != self.source_digest):
            raise ValueError('seed provenance must bind the prior source path and digest')
        object.__setattr__(self, 'provenance_json', canonical(provenance))

    def record(self):
        return {'record_type': 'generalization_probe_seed/v1', 'status': 'UNVERIFIED',
                'source_path': self.source_path, 'source_digest': self.source_digest,
                'byte_count': len(self.content), 'task_semantic_digest': self.semantic_digest,
                'parent_task_digest': self.parent_task_digest,
                'provenance': json.loads(self.provenance_json),
                'acceptance_inherited': False}

    def validate_for(self, task):
        if hashlib.sha256(self.content).hexdigest() != self.source_digest:
            raise ValueError('seed source bytes differ from their captured identity')
        if self.semantic_digest != digest(task_semantics(task.manifest())):
            raise ValueError('seed source belongs to a different task contract')
        require_file_bindings(json.loads(self.provenance_json)['file_hashes'])


def bind_parent_followup(report_path, tasks, *, allow_evaluator_revision=False,
                        revision_reason='', reuse_source=False):
    """Bind a reviewable follow-up to immutable prior task and source evidence."""
    if allow_evaluator_revision and not revision_reason.strip():
        raise ValueError('an evaluator revision requires an explicit nonempty rationale')
    if revision_reason and not allow_evaluator_revision:
        raise ValueError('revision rationale requires explicit evaluator-revision authorization')
    path, raw, report_sha = ordinary_file(report_path)
    previous_report = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(previous_report, dict) or previous_report.get('record_type') != 'generalization_probe_report/v1':
        raise ValueError('parent report type is unsupported')

    def indexed(items):
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise ValueError('parent task records must be an array of objects')
        result = {item['task_id']: item for item in items}
        if len(result) != len(items):
            raise ValueError('parent task identities repeat')
        return result

    previous = indexed(previous_report['outcomes'])
    file_hashes = {str(path): report_sha}
    metadata = {'path': str(path), 'sha256': report_sha,
                'population_digest': previous_report['population_digest'],
                'previous_statuses': {task.task_id: previous[task.task_id]['terminal_code'] for task in tasks},
                'evaluation_revisions': [], 'file_hashes': file_hashes}
    seeds = {}
    if not allow_evaluator_revision and not reuse_source:
        if any(previous[task.task_id]['task_digest'] != task.content_digest for task in tasks):
            raise ValueError('selected task changed; use explicit evaluator revision for evaluator-only changes')
        return metadata, seeds

    population_path, population_raw, population_sha = ordinary_file(path.parent / 'population.json')
    population = json.loads(population_raw, object_pairs_hook=_unique_object)
    if (not isinstance(population, dict) or population.get('record_type') != 'generalization_probe_population/v1'
            or digest(population) != previous_report['population_digest']):
        raise ValueError('parent population does not match its recorded digest')
    old_tasks = indexed(population['tasks'])
    file_hashes[str(population_path)] = population_sha
    for task in tasks:
        old = old_tasks[task.task_id]
        new = task.manifest()
        old_digest = digest(old)
        if previous[task.task_id]['task_digest'] != old_digest:
            raise ValueError('parent outcome does not bind its frozen task')
        task_root = path.parent / task.task_id
        frozen_path, frozen_raw, frozen_sha = ordinary_file(task_root / 'frozen-task.json')
        if json.loads(frozen_raw, object_pairs_hook=_unique_object) != old:
            raise ValueError('prior frozen task differs from the parent population')
        file_hashes[str(frozen_path)] = frozen_sha
        if task_semantics(old) != task_semantics(new):
            raise ValueError('evaluator revision cannot change prompt, entrypoint, editable files, or task semantics')
        if old_digest != task.content_digest and not allow_evaluator_revision:
            raise ValueError('changed evaluator requires --allow-evaluator-revision')
        metadata['evaluation_revisions'].append({
            'task_id': task.task_id, 'changed': old_digest != task.content_digest,
            'scope': 'evaluator_only', 'rationale': revision_reason,
            'old_task_digest': old_digest, 'new_task_digest': task.content_digest,
            'old_evaluator_digest': evaluator_digest(old), 'new_evaluator_digest': evaluator_digest(new),
            'unchanged_semantic_digest': digest(task_semantics(new)),
            'old_case_count': len(old['cases']), 'new_case_count': len(new['cases'])})
        if not reuse_source:
            continue
        source_path, source_bytes, source_sha = ordinary_file(task_root / 'source' / 'solution.py')
        source_identity = 'CAPTURED_UNVERIFIED_WORKING_SOURCE'
        outcome_path = task_root / 'outcome.json'
        if outcome_path.exists() or outcome_path.is_symlink():
            outcome_path, outcome_raw, outcome_sha = ordinary_file(outcome_path)
            outcome = json.loads(outcome_raw, object_pairs_hook=_unique_object)
            if (not isinstance(outcome, dict)
                    or outcome.get('run_id') != previous[task.task_id].get('run_id')
                    or outcome.get('status', outcome.get('terminal_code'))
                    != previous[task.task_id]['terminal_code']):
                raise ValueError('prior source outcome identity does not match the parent report')
            result = outcome.get('result')
            value = result.get('value', {}) if isinstance(result, dict) else {}
            value = value if isinstance(value, dict) else {}
            bound_digest = (value.get('source_digest') if value.get('kind') == 'execution_observation'
                            else value.get('digest') if value.get('kind') in (
                                'source_replacement', 'source_inspection') else None)
            if bound_digest is not None:
                if bound_digest != source_sha:
                    raise ValueError('previous source differs from the source bound by its outcome')
                source_identity = 'MATCHED_PREVIOUS_RESULT_SOURCE_DIGEST'
            file_hashes[str(outcome_path)] = outcome_sha
        file_hashes[str(source_path)] = source_sha
        seeds[task.task_id] = ProbeSeedSource(
            source_bytes, str(source_path), source_sha, digest(task_semantics(new)), old_digest,
            canonical({'parent_report': str(path), 'parent_report_sha256': report_sha,
                       'parent_run_id': previous[task.task_id].get('run_id'),
                       'source_identity': source_identity, 'file_hashes': dict(file_hashes)}))
    return metadata, seeds


def object_schema(properties=None, required=()):
    return {'type': 'object', 'properties': properties or {}, 'required': list(required),
            'additionalProperties': False}


def make_host(root, task, *, image=IMAGE, runner=docker_probe, seed_source=None):
    """One operation catalog for every manifest; host policy owns all paths and gates."""
    root = Path(root).absolute()
    if any(path.is_symlink() for path in (root, *root.parents)) or not root.is_dir():
        raise ValueError('host root must be an existing ordinary directory')
    seed_record = None
    if seed_source is not None:
        if not isinstance(seed_source, ProbeSeedSource):
            raise TypeError('seed_source requires ProbeSeedSource configuration')
        seed_source.validate_for(task)
        snapshot_path = root / 'seed-source.py'
        with snapshot_path.open('xb') as stream:
            stream.write(seed_source.content)
        snapshot_path.chmod(0o444)
        seed_record = {**seed_source.record(), 'snapshot_ref': str(snapshot_path),
                       'snapshot_digest': seed_source.source_digest}
        write_json(root / 'seed-source.json', seed_record)
        (root / 'seed-source.json').chmod(0o444)
        seed_receipt_digest = ordinary_file(root / 'seed-source.json')[2]
    project = root / 'source'
    project.mkdir()
    with (project / 'solution.py').open('xb') as stream:
        stream.write(seed_source.content if seed_source is not None else task.initial_source.encode('utf-8'))
    write_json(root / 'frozen-task.json', task.manifest())
    frozen_digest = hashlib.sha256((root / 'frozen-task.json').read_bytes()).hexdigest()
    backend = RestrictedLocalWorkspace(WorkspaceSpec('generalization-source', str(project)))
    lock = threading.RLock()
    records = {}

    def checked_artifacts():
        checked = []
        for saved in records.values():
            for artifact in json.loads(saved)['artifacts']:
                path = Path(artifact['path'])
                if (not path.is_relative_to(root) or any(item.is_symlink() for item in (path, *path.parents))
                        or not path.is_file() or path.stat().st_size != artifact['byte_count']
                        or hashlib.sha256(path.read_bytes()).hexdigest() != artifact['digest']):
                    raise ValueError('delivered artifact changed after execution')
                checked.append(artifact)
        return checked

    def source():
        if (root / 'frozen-task.json').is_symlink() or hashlib.sha256(
                (root / 'frozen-task.json').read_bytes()).hexdigest() != frozen_digest:
            raise ValueError('frozen task or verifier changed')
        if seed_record is not None:
            require_file_bindings({str(root / 'seed-source.json'): seed_receipt_digest,
                                   seed_record['snapshot_ref']: seed_record['snapshot_digest']})
        result = backend.file(FileRequest(FileOperation.READ, 'solution.py'))
        if not result.ok or result.byte_count > 65536:
            raise ValueError('managed source unavailable or too large')
        return result

    def snapshot():
        with lock:
            return digest({'source': source().digest, 'task': task.content_digest,
                           'image': image, 'observations': sorted(records), 'artifacts': checked_artifacts()})

    def require_state(request):
        if request.state_ref != snapshot():
            raise ValueError('host state changed before operation')

    def inspect(request):
        with lock:
            require_state(request)
            value = source()
            return {'kind': 'source_inspection', 'path': 'solution.py', 'digest': value.digest,
                    'digest_purpose': SOURCE_DIGEST_PURPOSE,
                    'content': value.content.decode(), 'entrypoint': task.entrypoint,
                    'editable_files': ['solution.py'], 'verification_cases': len(task.cases),
                    'seed_material': ({'status': 'UNVERIFIED', 'acceptance_inherited': False,
                                       'snapshot_ref': seed_record['snapshot_ref'],
                                       'source_digest': seed_record['snapshot_digest']}
                                      if seed_record is not None else None),
                    'visibility': {'source': 'model_visible', 'oracle_definition': 'host_only',
                                   'probe_arguments': 'tool_only', 'actual_observation_feedback': 'model_visible_after_execution'}}

    def replace_source(request):
        with lock:
            require_state(request)
            value = request.arguments
            if value['path'] != 'solution.py' or len(value['content'].encode()) > 65536:
                raise ValueError('source path or byte allowance refused')
            result = backend.file(FileRequest(
                FileOperation.WRITE, 'solution.py', content=value['content'].encode(),
                replace_existing=True, expected_digest=value['expected_digest']))
            if not result.ok:
                if result.error_code == 'digest_mismatch':
                    return {'kind': 'source_replacement_refused', 'write_applied': False,
                            'error_code': 'source_digest_mismatch', 'reason': SOURCE_DIGEST_PURPOSE}
                raise ValueError('source replacement refused: ' + result.error_code)
            return {'kind': 'source_replacement', 'path': 'solution.py', 'digest': result.digest}

    def run(request):
        with lock:
            require_state(request)
            selected = source()
            run_root = root / f'observation-{len(records) + 1:04d}'
            run_root.mkdir()
            (run_root / 'solution.py').write_bytes(selected.content)
            (run_root / 'probe.py').write_text(WORKER, encoding='utf-8')
            write_json(run_root / 'probe-input.json', {'entrypoint': task.entrypoint,
                'cases': [{key: item[key] for key in ('case_id', 'arguments', 'python_constants')
                           if key in item} for item in task.cases]})
            before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in run_root.iterdir()}
            execution = runner(run_root, image)
            after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in run_root.iterdir()}
            if before != after or source().digest != selected.digest:
                raise ValueError('candidate execution changed frozen subject or probes')
            comparison = evaluate(task, execution)
            artifacts = []
            if comparison['passed']:
                observations = json.loads(execution['stdout'])['cases']
                for expected, observed in zip(task.cases, observations):
                    if expected['artifact']:
                        artifact = run_root.parent / (run_root.name + '-' + expected['artifact'])
                        with artifact.open('x', encoding='utf-8') as stream:
                            stream.write(observed['value'])
                        raw = artifact.read_bytes()
                        artifacts.append({'path': str(artifact), 'digest': hashlib.sha256(raw).hexdigest(),
                                          'byte_count': len(raw)})
            record = {'record_type': 'generalization_probe_observation/v1', 'source_digest': selected.digest,
                      'task_digest': task.content_digest, 'execution': execution, 'comparison': comparison,
                      'artifacts': artifacts}
            run_ref = digest(record)
            write_json(root / (run_root.name + '.json'), record)
            records[run_ref] = canonical(record)
            return {'kind': 'execution_observation', 'run_ref': run_ref, 'source_digest': selected.digest,
                    'comparison': feedback(comparison), 'artifacts': artifacts,
                    'execution': {key: execution.get(key) for key in ('ok', 'exit_code', 'error_code', 'stderr')}}

    def verify(request):
        with lock:
            require_state(request)
            value = request.arguments['result']['value']
            if value.get('kind') == 'source_replacement_refused':
                return {'passed': False, 'task_complete': False, 'observations': value,
                        'notes': value['reason']}
            if value.get('kind') != 'execution_observation':
                return {'passed': True, 'task_complete': False, 'observations': {'state_valid': True},
                        'notes': 'Intermediate source observation only; run the host probe before completion.'}
            record = json.loads(records.get(value.get('run_ref'), '{}'))
            if not record or record['source_digest'] != source().digest or record['task_digest'] != task.content_digest:
                raise ValueError('verification has no matching current execution')
            checked_artifacts()
            comparison = evaluate(task, record['execution'])
            return {'passed': comparison['passed'], 'task_complete': comparison['passed'],
                    'observations': feedback(comparison), 'notes': 'Fixed independent host comparisons passed.'
                    if comparison['passed'] else 'Fixed independent host comparisons failed; repair from observations.'}

    directory = CapabilityDirectory()
    descriptions = (
        ('workspace_inspect', inspect, 'Read the host-managed implementation and current digest.', ('reads_fs',)),
        ('workspace_replace', replace_source, 'Replace only solution.py when its current digest matches the digest returned by workspace_inspect.', ('writes_fs',)),
        ('workspace_run', run, 'Run the fixed read-only Python probe and record observed outputs.', ('reads_fs', 'writes_fs', 'spawns_process')),
        ('workspace_verifier', verify, 'Independently compare exact observed outputs with fixed host criteria.', ('reads_fs',)),
    )
    for name, callback, purpose, effects in descriptions:
        directory.register(CapabilityHandshake(name, 'static_component', purpose, ('invoke',), effects=effects,
            input_schema='host_arguments/v1', output_schema='host_observation/v1', max_response_bytes=1048576),
            [Endpoint('invoke', callback)])

    def binding(name, kind, permissions, inputs):
        return HostOperationBinding(name, 'invoke', inputs, {'type': 'object'},
            lambda request: EffectSpec(kind, name, 'managed-probe:' + str(root),
                                      (('state', request.state_ref), ('task_digest', task.content_digest))),
            'generalization_probe.' + name + '@1.0.0', permission_names=permissions)

    operations = (
        binding('workspace_inspect', EffectClass.LOCAL_READ, ('source_read',), object_schema()),
        binding('workspace_replace', EffectClass.LOCAL_WRITE, ('workspace_write',), object_schema({
            'path': {'const': 'solution.py'}, 'content': {'type': 'string', 'maxLength': 65536},
            'expected_digest': {'type': 'string', 'pattern': '^[a-f0-9]{64}$',
                                'title': 'Current source digest precondition',
                                'description': SOURCE_DIGEST_PURPOSE}}, ('path', 'content', 'expected_digest'))),
        binding('workspace_run', EffectClass.COMMAND_EXECUTION, ('sandbox_command', 'workspace_write'), object_schema()),
    )
    verifier = binding('workspace_verifier', EffectClass.LOCAL_READ, ('source_read',), {'type': 'object'})

    def authorize(request):
        return ApprovalDecision.approve(request.request_id, 'frozen_probe_host_policy',
            reason='Exact registered operation within the declared isolated probe workspace.')

    return HostRuntimeBinding(directory, operations, verifier, authorize, snapshot,
                              'generalization-probe:' + str(root), share_outputs_with_model=True)


def population_manifest(tasks, *, model_route='cloud.default', model_id='deepseek-v4-flash:0731'):
    return {'record_type': 'generalization_probe_population/v1', 'tasks': [task.manifest() for task in tasks],
            'selection': 'all provided task manifests in declared order; every selected task remains in the denominator',
            'source_digest': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'image': IMAGE,
            'model_route': model_route, 'model_id': model_id,
            'authority': {'model_calls': 'requires_explicit_flag', 'source_to_model': 'requires_explicit_flag',
                          'max_model_calls': None, 'max_passes': None, 'max_total_tokens': None,
                          'model_failover': False, 'candidate_network': False, 'candidate_workspace_read_only': True},
            'visibility': {'implementation_and_actual_test_feedback': 'model_visible', 'oracle_definition': 'host_only',
                           'expected_answers': 'host_only',
                           'credentials': 'provider_resolver_only'},
            'limitations': ['five task shapes, not a full-system benchmark',
                            'not claimed pretraining-unseen or a statistically powered comparison',
                            'fixed test feedback may guide repair; these cases are not untouched holdouts',
                            'post-run audit cases strengthen evaluation but are not untouched holdouts',
                            'nonfinite arguments use a fixed trusted constant codec, never model-supplied Python expressions']}


def main(argv=None):
    all_tasks = task_population()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir')
    parser.add_argument('--authorize-model-calls', action='store_true')
    parser.add_argument('--allow-source-to-model', action='store_true')
    parser.add_argument('--model-route', default='cloud.default')
    parser.add_argument('--model-id', default='deepseek-v4-flash:0731')
    parser.add_argument('--task', action='append', choices=[task.task_id for task in all_tasks])
    parser.add_argument('--selection-reason', default='All declared regression tasks.')
    parser.add_argument('--parent-report')
    parser.add_argument('--allow-evaluator-revision', action='store_true')
    parser.add_argument('--evaluation-revision-reason', default='')
    parser.add_argument('--reuse-parent-source', action='store_true')
    args = parser.parse_args(argv)
    if args.task and len(args.task) != len(set(args.task)):
        parser.error('--task entries must be unique.')
    tasks = tuple(task for task in all_tasks if not args.task or task.task_id in args.task)
    manifest = population_manifest(tasks, model_route=args.model_route, model_id=args.model_id)
    manifest['selection_reason'] = args.selection_reason
    manifest['requested_task_ids'] = args.task or [task.task_id for task in all_tasks]
    seeds = {}
    if (args.allow_evaluator_revision or args.evaluation_revision_reason or args.reuse_parent_source) and not args.parent_report:
        parser.error('Evaluator revision and source reuse require --parent-report.')
    if args.parent_report:
        try:
            manifest['parent_report'], seeds = bind_parent_followup(
                args.parent_report, tasks, allow_evaluator_revision=args.allow_evaluator_revision,
                revision_reason=args.evaluation_revision_reason, reuse_source=args.reuse_parent_source)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            parser.error('--parent-report could not bind the selected task contracts: ' + str(exc))
    manifest['source_reuse'] = {task_id: seed.record() for task_id, seed in seeds.items()}
    if not args.authorize_model_calls:
        print(canonical({'plan': manifest, 'model_calls': 0, 'files_written': 0}))
        return 0
    if not args.allow_source_to_model or not args.work_dir:
        parser.error('Live execution requires --allow-source-to-model and a new --work-dir.')
    root = Path(args.work_dir).absolute()
    if root.exists() or any(path.is_symlink() for path in (root, *root.parents)):
        parser.error('--work-dir must not already exist.')
    gateway = ModelGateway()
    route = gateway.registry.get(args.model_route)
    if route.model != args.model_id or route.provider != 'ollama_cloud':
        parser.error('Use the exact configured Ollama Cloud route and model for this probe.')
    capability = gateway.providers[route.provider].output_capability_for(args.model_id)
    if capability.declared_maximum is None:
        parser.error('The exact route lacks known source-backed output capacity.')
    manifest['output_capacity'] = capability.summary()
    root.mkdir(parents=True)
    write_json(root / 'population.json', manifest)
    outcomes = []

    def report():
        calls_complete = all(item['model_call_accounting_complete'] is True for item in outcomes)
        tokens_complete = all(item['model_usage']['token_accounting_complete'] is True for item in outcomes)
        known_input = sum(item['model_usage'].get('known_input_tokens_subtotal', 0) for item in outcomes)
        known_output = sum(item['model_usage'].get('known_output_tokens_subtotal', 0) for item in outcomes)
        return {'record_type': 'generalization_probe_report/v1', 'population_digest': digest(manifest),
                'selected': len(tasks), 'attempted': len(outcomes),
                'verified_completed': sum(item['solved'] for item in outcomes),
                'not_started': [task.task_id for task in tasks if task.task_id not in {item['task_id'] for item in outcomes}],
                'usage_scope': 'attempted_tasks',
                'model_calls': sum(item['model_calls'] for item in outcomes) if calls_complete else None,
                'model_calls_known_subtotal': sum(item['model_calls_known_subtotal'] for item in outcomes),
                'model_call_accounting_complete': calls_complete,
                'input_tokens': known_input if tokens_complete else None,
                'output_tokens': known_output if tokens_complete else None,
                'known_input_tokens_subtotal': known_input, 'known_output_tokens_subtotal': known_output,
                'token_accounting_complete': tokens_complete, 'cost_usd': None, 'cost_state': 'unknown',
                'outcomes': outcomes, 'limitations': manifest['limitations'],
                'evaluation_revisions': manifest.get('parent_report', {}).get('evaluation_revisions', []),
                'reused_source_digests': {task_id: seed.source_digest for task_id, seed in seeds.items()}}

    for task in tasks:
        task_root = root / task.task_id
        task_root.mkdir()
        started = False
        phase = 'host_preparation'
        try:
            if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != manifest['source_digest']:
                raise ValueError('frozen runner source changed')
            require_file_bindings(manifest.get('parent_report', {}).get('file_hashes', {}))
            host = make_host(task_root, task, seed_source=seeds.get(task.task_id))
            if not docker_workspace(task_root / 'source', IMAGE).availability().available:
                raise RuntimeError('pinned sandbox unavailable before model dispatch')
            model = ModelExecution(gateway, ModelGatewayConfig(
                route_names=(args.model_route,), allowed_models=(args.model_id,), allow_failover=False))
            prompt = task.manifest()['effective_prompt']

            def progress(value):
                if value.get('event_type') in ('model.step.started', 'model.step.completed', 'practitioner.diagnostic'):
                    print(canonical({'task_id': task.task_id, **{key: value.get(key) for key in (
                        'event_type', 'run_id', 'step', 'model_calls_completed', 'elapsed_seconds', 'diagnostic_code')}}), flush=True)

            started = True
            phase = 'solve'
            outcome = solve_task(SolveRequest(intake_task(TaskIntakeRequest(text=prompt)), model_execution=model,
                host_runtime=host, runs_dir=str(task_root / 'runs'), interaction_mode='autonomous', quiet_model_io=True,
                progress=progress))
            phase = 'save_outcome'
            write_json(task_root / 'outcome.json', outcome.to_dict())
            entry = {'task_id': task.task_id, 'shape': task.shape, 'task_digest': task.content_digest,
                     'terminal_code': outcome.status, 'solved': outcome.solved, 'run_id': outcome.run_id,
                     'model_calls': outcome.model_calls, 'model_calls_known_subtotal': outcome.model_calls_known_subtotal,
                     'model_call_accounting_complete': outcome.model_call_accounting_complete,
                     'model_usage': model_usage_summary(outcome),
                     'elapsed_seconds': outcome.elapsed_seconds, 'outcome_path': str(task_root / 'outcome.json')}
            if task.task_id in seeds:
                entry['seed_source_ref'] = str(task_root / 'seed-source.json')
                entry['seed_source_digest'] = seeds[task.task_id].source_digest
        except BaseException as exc:
            entry = {'task_id': task.task_id, 'shape': task.shape, 'task_digest': task.content_digest,
                     'terminal_code': 'RUNNER_EXCEPTION', 'solved': False, 'error_type': type(exc).__name__,
                     'phase': phase,
                     'model_calls': None if started else 0, 'model_call_accounting_complete': not started,
                     'model_usage': {'input_tokens': None if started else 0, 'output_tokens': None if started else 0,
                                     'token_accounting_complete': not started, 'cost_usd': None, 'cost_state': 'unknown'},
                     'model_calls_known_subtotal': 0, 'run_id': None}
            write_json(task_root / 'runner-failure.json', entry)
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                outcomes.append(entry)
                write_json(root / 'report.json', report())
                raise
        outcomes.append(entry)
        write_json(root / f'progress-{len(outcomes):04d}.json', report())
        print(canonical(outcomes[-1]), flush=True)
    write_json(root / 'report.json', report())
    print(canonical(report()))
    return 0 if all(item['solved'] for item in outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
