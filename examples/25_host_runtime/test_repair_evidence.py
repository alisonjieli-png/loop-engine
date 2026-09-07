"""Scoped historical repair context without inherited acceptance or a new store."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

import counterexample_checks as checks
import generalization_probe as probe
from repair_evidence import ProbeRepairRequest, load_repair_bundle, load_repair_evidence
from test_counterexample_checks import FIXED_PRECISION
from test_generalization_probe import fixture_runner, invoke, services
from loop_engine.core.context_artifacts import ContextArtifactStoreSpec
from loop_engine.core.host_runtime import verify_host_result
from loop_engine.core.run_history import RunHistory


def fixture(directory):
    root = Path(directory)
    task = probe.task_population()[1]
    task = replace(task, cases_json=probe.canonical(task.cases[:3]))
    policy = checks.exact_aggregation_policy(task, checks.ExactAggregationProbeConfig(8123, (256,)))
    host = probe.make_host(root, task, completion_policy=policy, runner=fixture_runner)
    state, owner = services(root, host)
    read = invoke(host, state, owner, 0, {})
    invoke(host, state, owner, 1, {'path': 'solution.py', 'content': FIXED_PRECISION,
        'expected_digest': read['value']['digest']})
    result = invoke(host, state, owner, 2, {})
    report = verify_host_result(state.request.task, result, state, owner)
    assert report['status'] == 'failed'
    observed = report['completion_checks'][0]['observations']
    history = RunHistory.from_ledger(owner.ledger.events, run_id='repair-fixture')
    history.commit()
    history.save(str(root / 'history'))
    request = ProbeRepairRequest(str(root / 'history'), history.run_id,
        ContextArtifactStoreSpec(str(root / 'evidence/artifacts')), host.scope_ref,
        str(root / observed['receipt_ref']), observed['receipt_digest'])
    return task, request


class RepairEvidenceChecks(unittest.TestCase):
    def test_reopened_history_returns_only_scoped_negative_advice(self):
        with tempfile.TemporaryDirectory(prefix='repair-source-') as directory:
            task, request = fixture(directory)
            value = load_repair_evidence(task, request)
            packet = value.validate_for(task)
            self.assertFalse(packet['acceptance_inherited'])
            self.assertFalse(packet['grants_promotion'])
            self.assertEqual(packet['current_source_verdict'], 'not_evaluated_by_this_historical_record')
            self.assertTrue(packet['failures'])
            self.assertNotIn('"expected"', value.view_json)
            self.assertNotIn('"arguments"', value.view_json)
            self.assertEqual(value.content_digest, load_repair_evidence(task, request).content_digest)
            with tempfile.TemporaryDirectory(prefix='repair-consumer-') as consumer:
                host = probe.make_host(consumer, task, repair_evidence=(value,), runner=fixture_runner)
                state, owner = services(Path(consumer), host)
                observed = invoke(host, state, owner, 0, {})
                self.assertEqual(observed['value']['repair_evidence'], [packet])
                verdict = verify_host_result(state.request.task, observed, state, owner)
                self.assertFalse(verdict['task_complete'])

    def test_foreign_scope_changed_task_and_wrong_receipt_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='repair-scope-') as directory:
            task, request = fixture(directory)
            for bad in (replace(request, scope_ref='different:scope'),
                        replace(request, receipt_digest='0' * 64),
                        replace(request, maximum_bytes=1)):
                with self.assertRaises((ValueError, RuntimeError)):
                    load_repair_evidence(task, bad)
            with self.assertRaises((ValueError, RuntimeError)):
                load_repair_evidence(replace(task, prompt=task.prompt + ' Another task.'), request)

    def test_uncommitted_or_altered_history_cannot_supply_repair_context(self):
        with tempfile.TemporaryDirectory(prefix='repair-history-integrity-') as directory:
            task, request = fixture(directory)
            manifest = Path(request.history_root) / request.run_id / 'manifest.json'
            body = json.loads(manifest.read_text())
            body['committed'] = False
            manifest.write_text(json.dumps(body))
            with self.assertRaises((ValueError, RuntimeError)):
                load_repair_evidence(task, request)

    def test_changed_evidence_is_rejected_before_model_visible_hydration(self):
        with tempfile.TemporaryDirectory(prefix='repair-stale-input-') as directory:
            task, request = fixture(directory)
            value = load_repair_evidence(task, request)
            with tempfile.TemporaryDirectory(prefix='repair-stale-consumer-') as consumer:
                host = probe.make_host(consumer, task, repair_evidence=(value,), runner=fixture_runner)
                Path(request.receipt_path).write_text('{}')
                with self.assertRaises(ValueError):
                    host.snapshot()
                with self.assertRaises(ValueError):
                    value.validate_for(task)

    def test_context_cannot_claim_acceptance_or_add_unbounded_fields(self):
        with tempfile.TemporaryDirectory(prefix='repair-no-authority-') as directory:
            task, request = fixture(directory)
            value = load_repair_evidence(task, request)
            view = json.loads(value.view_json)
            view['acceptance_inherited'] = True
            with self.assertRaises(ValueError):
                replace(value, view_json=probe.canonical(view)).validate_for(task)

    def test_explicit_bundle_records_its_own_identity(self):
        with tempfile.TemporaryDirectory(prefix='repair-bundle-') as directory:
            task, request = fixture(directory)
            path = Path(directory) / 'request.json'
            body = {'record_type': 'probe_repair_request/v1', 'history_root': request.history_root,
                    'run_id': request.run_id, 'artifact_root': request.artifact_store.root,
                    'artifact_namespace': request.artifact_store.namespace, 'scope_ref': request.scope_ref,
                    'receipt_path': request.receipt_path, 'receipt_digest': request.receipt_digest}
            probe.write_json(path, body)
            value = load_repair_bundle(task, path)
            self.assertIn(str(path), json.loads(value.source_bindings_json))
            path.write_text('{}')
            with self.assertRaises(ValueError):
                value.validate_for(task)


if __name__ == '__main__':
    unittest.main()
