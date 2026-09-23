"""Offline fault controls. Mutated modules exist only in memory."""
from __future__ import annotations

import hashlib
import json
import types
from pathlib import Path

from loop_engine.core import custom_endpoint as original
from loop_engine.core import custom_endpoint_checks as checks

path = Path(original.__file__)
source = path.read_text()
changes = {
    'requested_model_fills_missing_buffered_identity': (
        '_response_model(body.get("model"))', '_response_model(body.get("model", ep.model))'),
    'request_model_fills_missing_openai_stream_identity': (
        'finish_reason = ""\n    reported_model, invalid_model = "", False',
        'finish_reason = ""\n    reported_model, invalid_model = ep.model, False'),
    'later_stream_identity_erases_conflict': (
        'if not observed or (reported and observed != reported):', 'if not observed:'),
    'nonstring_provider_identity_is_coerced': (
        'return value if type(value) is str and value.strip() else ""',
        'return str(value) if value is not None else ""'),
    'identity_refusal_does_not_refuse_adapter_answer': (
        'and done is not False and not identity_invalid,', 'and done is not False,'),
    'missing_stream_usage_fabricates_zero': (
        'final.get("prompt_eval_count")', 'final.get("prompt_eval_count", 0)'),
    'preflight_refusal_invents_physical_request': (
        'error=str(exc), physical_requests=0)', 'error=str(exc), physical_requests=1)'),
}
exports = ('ce', 'CustomEndpoint', 'EndpointError', 'forget_learned_stream_modes',
           'learned_stream_mode', 'make_adapter')
saved = {name: getattr(checks, name) for name in exports}
rows = []
for identity, (before, after) in changes.items():
    if before not in source:
        raise SystemExit(f'missing mutation target: {identity}')
    module = types.ModuleType('loop_engine.core.custom_endpoint_mutant')
    module.__package__ = 'loop_engine.core'
    module.__file__ = str(path)
    # Dataclass annotation resolution consults sys.modules during construction.
    import sys
    sys.modules[module.__name__] = module
    try:
        exec(compile(source.replace(before, after), str(path), 'exec'), module.__dict__)  # noqa: S102 - fixed in-memory fault controls
        for name in exports:
            setattr(checks, name, module if name == 'ce' else getattr(module, name))
        failed = [row['test'] for row in checks.run_checks() if not row['passed']]
        rows.append({'mutation': identity, 'detected': bool(failed), 'failed_checks': failed})
    finally:
        for name, value in saved.items():
            setattr(checks, name, value)
        sys.modules.pop(module.__name__, None)
record = {'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
          'mutations': rows, 'all_detected': all(row['detected'] for row in rows),
          'provider_calls': 0}
print(json.dumps(record, indent=2))
raise SystemExit(0 if record['all_detected'] else 1)
