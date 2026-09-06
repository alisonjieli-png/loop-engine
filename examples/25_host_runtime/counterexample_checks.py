"""Host-owned, finite counterexample plans for the exported regression example.

The policy is passive data. Its execution belongs to the registered host
completion verifier. This file supplies one explicit exact-aggregation
property generator, not a task-category router in the Loop runtime.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
import hashlib
import io
import json
from pathlib import Path
import random
import re


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def integer_text(value):
    """Exact decimal rendering without changing the interpreter's process settings."""
    negative = value < 0
    value = abs(value)
    parts = []
    while value:
        value, part = divmod(value, 10 ** 9)
        parts.append(str(part).zfill(9))
    return ('-' if negative else '') + (''.join(reversed(parts)).lstrip('0') or '0')


def integer_value(text):
    if not isinstance(text, str) or not re.fullmatch(r'[+-]?[0-9]+', text):
        raise ValueError('oracle requires a decimal integer')
    sign = -1 if text.startswith('-') else 1
    digits = text.lstrip('+-')
    value = 0
    for offset in range(0, len(digits), 9):
        part = digits[offset:offset + 9]
        value = value * (10 ** len(part)) + int(part)
    return sign * value


def cents_text(value):
    sign = '-' if value < 0 else ''
    whole, fraction = divmod(abs(value), 100)
    return sign + integer_text(whole) + '.' + str(fraction).zfill(2)


def integer_oracle(text):
    """Independent host calculation using integer cents and bounded chunk conversions."""
    totals = {}
    for row in csv.DictReader(io.StringIO(text)):
        if not row['department'] or not re.fullmatch(r'[0-9]+\.[0-9]{2}', row['unit_price']):
            raise ValueError('invalid generated oracle input')
        count = integer_value(row['quantity'])
        whole, fraction = row['unit_price'].split('.')
        price = integer_value(whole) * 100 + integer_value(fraction)
        quantity, total = totals.get(row['department'], (0, 0))
        totals[row['department']] = quantity + count, total + count * price
    return [{'department': name, 'quantity': values[0], 'total': cents_text(values[1])}
            for name, values in sorted(totals.items())]


def decimal_oracle(text):
    """Cross-check with input-derived Decimal precision, isolated from global context."""
    totals = {}
    with localcontext() as context:
        # The complete input length bounds operand digits and row-count growth.
        context.prec = 2 * len(text) + 10
        for row in csv.DictReader(io.StringIO(text)):
            quantity, total = totals.get(row['department'], (Decimal(0), Decimal(0)))
            count, price = Decimal(row['quantity']), Decimal(row['unit_price'])
            totals[row['department']] = quantity + count, total + count * price
        return [{'department': name, 'quantity': int(values[0]), 'total': format(values[1], '.2f')}
                for name, values in sorted(totals.items())]


@dataclass(frozen=True)
class ProbeCompletionPolicy:
    """Exact host-selected test plan; neither runtime nor promotion authority."""

    task_semantic_digest: str
    cases_json: str
    generator_json: str
    oracle_receipt_json: str
    implementation_digest: str

    def record(self):
        return {'record_type': 'probe_completion_policy/v1',
                'task_semantic_digest': self.task_semantic_digest,
                'cases': json.loads(self.cases_json),
                'generator': json.loads(self.generator_json),
                'oracle_check': json.loads(self.oracle_receipt_json),
                'implementation_digest': self.implementation_digest,
                'coverage': 'finite generated regression evidence, not universal correctness'}

    @property
    def content_digest(self):
        return _digest(self.record())

    def describe(self):
        value = self.record()
        return {key: item for key, item in {
            **value, 'case_count': len(value['cases']), 'case_digest': _digest(value['cases']),
            'policy_digest': self.content_digest,
        }.items() if key != 'cases'}

    def validate_for(self, task):
        from generalization_probe import task_semantics
        if self.task_semantic_digest != _digest(task_semantics(task.manifest())):
            raise ValueError('completion policy belongs to different task semantics')
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != self.implementation_digest:
            raise ValueError('completion oracle or generator implementation changed')
        checked = replace(task, cases_json=self.cases_json)
        expected_receipt = qualify_cases(checked.cases)
        if _json(expected_receipt) != self.oracle_receipt_json:
            raise ValueError('completion oracle qualification does not match its exact cases')
        return checked


@dataclass(frozen=True)
class ExactAggregationProbeConfig:
    """Finite testing effort, not an input limit added to the original task."""

    seed: int
    digit_bands: tuple[int, ...] = (2, 32, 256, 2048, 24000, 40000)
    maximum_case_bytes: int = 196608

    def __post_init__(self):
        if type(self.seed) is not int or not 0 <= self.seed < 2 ** 64:
            raise ValueError('counterexample seed must be a uint64')
        if (not isinstance(self.digit_bands, tuple) or not self.digit_bands
                or any(type(value) is not int or not 1 <= value <= 40000 for value in self.digit_bands)
                or len(set(self.digit_bands)) != len(self.digit_bands)):
            raise ValueError('digit bands must be unique positive finite probe sizes')
        if type(self.maximum_case_bytes) is not int or not 1 <= self.maximum_case_bytes <= 262144:
            raise ValueError('counterexample byte budget is outside the declared local test policy')


def qualify_cases(cases):
    """Reject wrong oracle values by two independent host calculations before dispatch."""
    checks = []
    for item in cases:
        if (item.get('error') is not None or item.get('comparison') != 'exact'
                or len(item.get('arguments', [])) != 1 or type(item['arguments'][0]) is not str):
            raise ValueError('unsupported exact-aggregation property case')
        first = integer_oracle(item['arguments'][0])
        second = decimal_oracle(item['arguments'][0])
        if first != second or _json(first) != _json(item['expected']):
            raise ValueError('independent host oracles disagree with the proposed expected value')
        checks.append({'case_id': item['case_id'], 'input_digest': _digest(item['arguments']),
                       'expected_digest': _digest(first)})
    return {'record_type': 'probe_oracle_check/v1', 'checked_cases': len(checks),
            'checked_digest': _digest(checks),
            'methods': ['integer_cents_chunk_codec', 'input_derived_local_decimal'],
            'independence': 'separate host algorithms, not independent organizations',
            'grants_promotion': False}


def exact_aggregation_policy(task, config):
    """Generate source-independent cancellation cases selected by explicit host configuration."""
    from generalization_probe import case, task_semantics
    if not isinstance(config, ExactAggregationProbeConfig):
        raise TypeError('counterexamples require explicit typed generation configuration')
    if task.entrypoint != 'summarize_sales':
        raise ValueError('the selected example generator requires its declared aggregation interface')
    generator = random.Random(config.seed)
    rows = []
    header = 'department,quantity,unit_price\n'
    note = ('Independent cancellation checks require exact arithmetic on valid input. '
            'Their magnitudes vary independently of the candidate implementation. '
            'A precision chosen only from earlier passing examples does not establish this requirement.')
    for index, band in enumerate(config.digit_bands):
        digits = max(1, band - generator.randrange(min(17, band)))
        magnitude = ('7' if digits == 1 else
                     str(generator.randrange(1, 10)) + '0' * max(0, digits - 4) + '137')
        magnitude = magnitude[:digits]
        count = integer_value(magnitude)
        delta = generator.randrange(1, 10)
        fraction = generator.randrange(1, 99)
        candidates = (
            ('price_cancellation', header + f'A,1,{magnitude}.01\nA,-1,{magnitude}.00\n'),
            ('quantity_cancellation', header + 'A,' + integer_text(count + delta)
             + f',0.{fraction:02d}\nA,-' + magnitude + f',0.{fraction:02d}\n'),
            ('intermediate_product_cancellation', header + 'A,' + integer_text(count + delta)
             + ',' + magnitude + '.01\nA,-' + magnitude + ',' + magnitude + '.01\n'),
        )
        for kind, text in candidates:
            if len(text.encode()) > config.maximum_case_bytes:
                raise ValueError('generated property case exceeds its explicit testing byte budget')
            rows.append(case(f'property_{index}_{kind}_{digits}_digits', [text],
                             integer_oracle(text), failure_note=note))
    record = qualify_cases(rows)
    return ProbeCompletionPolicy(
        _digest(task_semantics(task.manifest())), _json(rows),
        _json({'ref': 'example.exact_aggregation_cancellation@1.0.0', 'seed': config.seed,
               'digit_bands': list(config.digit_bands), 'maximum_case_bytes': config.maximum_case_bytes,
               'candidate_source_used_for_generation': False}),
        _json(record), hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
