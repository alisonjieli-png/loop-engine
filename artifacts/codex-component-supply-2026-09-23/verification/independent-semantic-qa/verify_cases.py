"""Run independent JSON case data against frozen package bytes, inside Bubblewrap."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, DecimalException
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from jsonschema import Draft202012Validator
from sandbox import TRUSTED_SOURCE, RUNNER, bindings, digest, run_bytes, strict_loads

HERE = Path(__file__).resolve().parent
SUPPLY = HERE.parents[1]


def refuse_external_references(value):
    if isinstance(value, dict):
        for name, content in value.items():
            if name in ('$ref', '$dynamicRef') and (not isinstance(content, str) or not content.startswith('#')):
                raise ValueError('nonlocal_schema_reference')
            refuse_external_references(content)
    elif isinstance(value, list):
        for item in value:
            refuse_external_references(item)


def semantic_json_equal(left, right):
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    if type(left) in (int, float) and type(right) in (int, float):
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(semantic_json_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(semantic_json_equal(a, b) for a, b in zip(left, right))
    return left == right


def exact_decimal_for_schema(token):
    # A mathematically zero coefficient is independent of exponent magnitude.
    coefficient = token.lower().split('e', 1)[0].replace('-', '').replace('.', '')
    if coefficient and set(coefficient) <= {'0'}:
        return Decimal(0)
    try:
        return Decimal(token)
    except DecimalException:
        raise ValueError('numeric_schema_observation_unavailable') from None


def exact_schema_numbers(value):
    if isinstance(value, Decimal) and value == value.to_integral_value() and value.adjusted() <= 24:
        return int(value)
    if isinstance(value, dict):
        return {key: exact_schema_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [exact_schema_numbers(item) for item in value]
    return value


def check_case(case, script, input_validator, output_validator, output_limit_bytes=65536):
    raw = bytes.fromhex(case['raw_hex']) if 'raw_hex' in case else json.dumps(case['input'], ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode()
    try:
        parsed_input = exact_schema_numbers(strict_loads(raw, parse_float=exact_decimal_for_schema))
        input_schema_valid = input_validator.is_valid(parsed_input)
    except (ValueError, UnicodeError):
        input_schema_valid = None
    observed = run_bytes(script, raw, output_limit_bytes=output_limit_bytes)
    expected = case['expected']
    compared_output = observed['output']
    if case.get('compare_fields'):
        compared_output = {name: compared_output[name] for name in case['compare_fields'] if isinstance(compared_output, dict) and name in compared_output}
    output_schema_valid = output_validator.is_valid(observed['output']) if observed['exit_code'] == 0 else None
    checks = {
        'exit_matches': observed['exit_code'] == case['expected_exit'],
        'semantic_output_matches': semantic_json_equal(compared_output, expected),
        'successful_output_schema_valid': observed['exit_code'] != 0 or output_schema_valid is True,
        'bounded_execution': not observed['timed_out'] and not observed['launcher_truncated']
                             and observed['stdout_bytes'] <= output_limit_bytes and observed['stderr_bytes'] <= output_limit_bytes,
    }
    if 'input_schema_valid' in case:
        checks['input_schema_expectation_matches'] = input_schema_valid is case['input_schema_valid']
    return {'name': case['name'], 'rationale': case['rationale'], 'checks': checks,
            'passed': all(checks.values()), 'input_schema_valid': input_schema_valid,
            'output_schema_valid': output_schema_valid, 'observation': observed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError('preserve_existing_report')
    inputs = strict_loads(args.cases.read_bytes())
    if inputs['record_type'] != 'independent_component_cases/v1':
        raise ValueError('unsupported_qa_case_record')
    report = {'record_type': 'independent_component_execution/v1', 'at': datetime.now(timezone.utc).isoformat(),
              'case_source_sha256': digest(args.cases.read_bytes()), 'trusted_runner_sha256': digest(RUNNER.encode()),
              'process_owner_source_sha256': digest((TRUSTED_SOURCE / 'src/loop_engine/core/library_ingestion/processes.py').read_bytes()),
              'network': 'unshared_namespace', 'home': 'absent', 'cpu_seconds': 2,
              'address_space_bytes': 268435456, 'wall_seconds_per_case': 4,
              'maximum_each_output_file_bytes': 'per-package explicit bound, default 65536, allowed maximum 1048576', 'packages': [],
              'admission': 'not_performed', 'model_calls': 0}
    for package in inputs['packages']:
        folder = (SUPPLY / 'authored' / package['identity']).resolve()
        if folder.parent != (SUPPLY / 'authored').resolve():
            raise ValueError('package_path_outside_assignment')
        before = bindings(folder)
        script_path = folder / 'tools' / (package['identity'] + '.py')
        script = script_path.read_bytes()
        input_schema = strict_loads((folder / 'contracts/input.schema.json').read_bytes())
        output_schema = strict_loads((folder / 'contracts/output.schema.json').read_bytes())
        for schema in (input_schema, output_schema):
            refuse_external_references(schema)
            Draft202012Validator.check_schema(schema)
        input_validator, output_validator = Draft202012Validator(input_schema), Draft202012Validator(output_schema)
        output_limit = package.get('sandbox_output_bytes', 65536)
        rows = [check_case(case, script, input_validator, output_validator, output_limit) for case in package['cases']]
        after = bindings(folder)
        report['packages'].append({'identity': package['identity'], 'bindings': before,
                                   'bytes_unchanged_during_check': before == after, 'cases': rows,
                                   'passed': before == after and all(row['passed'] for row in rows)})
    report['case_count'] = sum(len(package['cases']) for package in report['packages'])
    report['passed'] = all(package['passed'] for package in report['packages'])
    with args.report.open('x') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'packages': len(report['packages']), 'cases': report['case_count'], 'passed': report['passed']}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
