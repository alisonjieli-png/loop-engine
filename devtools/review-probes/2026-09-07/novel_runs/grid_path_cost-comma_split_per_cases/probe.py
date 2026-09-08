import copy, importlib.util, io, json, math
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
