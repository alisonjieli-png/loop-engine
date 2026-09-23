"""Evaluate fixed, in-memory adapter-source faults against the new owning checks."""
import hashlib
import inspect
import io
import json
import unittest

from tools import generate_original_native_candidates as generation
from tools.test_generate_original_native_candidates import GenerationTest

original = generation.implementation_digests
source = inspect.getsource(original)
changes = {
    'class_adapter_is_misread_as_its_metaclass': (' or inspect.isclass(spec.adapter)', ''),
    'adapter_digest_is_not_bound_to_source_bytes': ('result[path.name] = digest(read_file(path, MAX_PLAN_BYTES))',
                                                 'result[path.name] = "0" * 64'),
    'missing_source_escapes_as_unclassified_type_error': ('except (TypeError, OSError):', 'except OSError:'),
}
records = []
for name, (before, after) in changes.items():
    if before not in source:
        raise SystemExit('mutation target missing: ' + name)
    namespace = dict(generation.__dict__)
    exec(compile(source.replace(before, after), '<fixed-adapter-source-mutant>', 'exec'), namespace)  # noqa: S102 - fixed offline mutants
    generation.implementation_digests = namespace['implementation_digests']
    stream = io.StringIO()
    try:
        suite = unittest.TestSuite(GenerationTest(method) for method in (
            'test_class_adapter_hashes_owning_source_and_changed_source_refuses_resume',
            'test_adapter_without_source_file_is_explicitly_unqualified'))
        result = unittest.TextTestRunner(stream=stream).run(suite)
        records.append({'mutation': name, 'detected': not result.wasSuccessful(),
                        'failed': [test.id() for test, _ in result.failures + result.errors],
                        'output': stream.getvalue()})
    finally:
        generation.implementation_digests = original
record = {'source_function_sha256': hashlib.sha256(source.encode()).hexdigest(),
          'all_detected': all(row['detected'] for row in records), 'controls': records,
          'provider_calls': 0}
print(json.dumps(record, indent=2))
raise SystemExit(0 if record['all_detected'] else 1)
