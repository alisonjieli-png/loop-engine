"""Real SQLite CRUD, search, revocation, and one-shot process parity."""
from dataclasses import replace
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from loop_engine.core.context_artifacts import ContextArtifactStore, ContextArtifactStoreSpec
from loop_engine.core.record_operations_records import RecordOperationRequest, canonical_json
from loop_engine.loop.effect_approval import ApprovalDecision, ApprovalRequest
from intelligence_resource_catalog import ManagedResourceCatalog, record_id
from loop_step_transport import StepPlacement, run_search_step, _execute, implementation_manifest
from run_opencode_instance import demo_bundle
from code_catalog_index import SourceIndexRequest, index_sources


def authorize(request):
    return ApprovalDecision.approve(request.request_id, 'fixture.explicit_scoped_authority')


class ResourceCatalogChecks(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='loop-managed-resource-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = ContextArtifactStore(ContextArtifactStoreSpec(str(self.root / 'bodies')))
        self.core, self.resources = demo_bundle(self.store)
        self.catalog = ManagedResourceCatalog(self.root / 'catalog')

    def publish(self, resource):
        return self.catalog.publish({**resource.card(), 'source_metadata': {'provenance': 'authored_fixture',
            'license': 'test-only', 'entrypoints': []}}, authorize)

    def test_unapproved_write_creates_no_catalog(self):
        with self.assertRaises(Exception):
            self.catalog.publish({**self.resources[0].card(), 'source_metadata': {}},
                lambda request: ApprovalDecision.reject(request.request_id, 'fixture.denied'))
        self.assertFalse((self.root / 'catalog').exists())

    def test_publish_read_hydrate_exact_candidate_without_direct_row_edit(self):
        resource = self.resources[0]
        created = self.publish(resource)
        self.assertTrue(created.committed)
        self.assertEqual(created.records[0]['lifecycle'], 'candidate')
        snap = self.catalog.snapshot((resource.reference,))
        self.assertEqual(self.catalog.loader(snap, self.store)(resource.artifact_ref), self.store.get(resource.artifact_ref))
        duplicate = self.publish(resource)
        self.assertEqual(duplicate.records[0]['record_version'], '1')
        self.assertFalse(duplicate.committed)

    def test_retired_selected_reference_cannot_hydrate(self):
        resource = self.resources[0]
        self.publish(resource)
        snap = self.catalog.snapshot((resource.reference,))
        service = self.catalog.services['context_intelligence']
        request = RecordOperationRequest('retire', record_id(resource.reference), expected_record_version='1')
        approval = ApprovalRequest.create('fixture.retire', service.effect_for(request), 'Retire exact fixture descriptor.')
        pending = self.catalog.approvals.create(approval)
        self.catalog.approvals.resume(pending.pending, pending.resume_token, authorize(approval))
        self.assertTrue(service.execute(request, approval_id=approval.request_id).committed)
        with self.assertRaises(PermissionError):
            self.catalog.loader(snap, self.store)(resource.artifact_ref)
        with self.assertRaises(ValueError):
            self.catalog.snapshot((resource.reference,))

    def test_descriptor_update_requires_expected_revision_and_invalidates_old_view(self):
        resource = self.resources[0]
        self.publish(resource)
        snap = self.catalog.snapshot((resource.reference,))
        revised = {**resource.card(), 'description': 'Changed description.', 'source_metadata': {}}
        with self.assertRaises(ValueError):
            self.catalog.publish(revised, authorize)
        self.catalog.publish(revised, authorize, expected_record_version='1')
        with self.assertRaises(PermissionError):
            self.catalog.revalidate(snap)
        with self.assertRaises(RuntimeError):
            self.catalog.publish({**revised, 'description': 'A stale second writer.'}, authorize, expected_record_version='1')

    def test_ungranted_body_and_missing_descriptor_refused(self):
        self.publish(self.resources[0])
        snap = self.catalog.snapshot((self.resources[0].reference,))
        with self.assertRaises(PermissionError):
            self.catalog.loader(snap, self.store)(self.resources[1].artifact_ref)
        with self.assertRaises(ValueError):
            self.catalog.snapshot((self.resources[1].reference,))

    def test_metadata_search_has_real_process_parity_and_no_body_exposure(self):
        for item in self.resources:
            self.publish(item)
        # Restrict before search, not after a wider result has reached the model.
        snapshot = self.catalog.snapshot(tuple(item.reference for item in self.resources[:2]))
        payload = {'snapshot_json': snapshot.records_json, 'need': 'numeric input sum checking', 'limit': 2}
        local = run_search_step(payload)
        remote = run_search_step(payload, StepPlacement('python_process'), authorize=authorize)
        self.assertEqual(local['value'], remote['value'])
        self.assertEqual(local['worker_pid'], os.getpid())
        self.assertNotEqual(remote['worker_pid'], os.getpid())
        self.assertEqual(remote['terminal_code'], 'ACCEPTED')
        self.assertTrue(remote['worker_events'])
        self.assertEqual(remote['value']['body_materializations'], 0)
        self.assertNotIn('SELECTED_SKILL_BODY_73', canonical_json(remote))
        self.assertNotIn('writing.style', canonical_json(remote))

    def test_process_needs_approval_and_unknown_or_changed_entrypoint_refused(self):
        payload = {'snapshot_json': '[]', 'need': 'anything', 'limit': 1}
        with self.assertRaises(PermissionError):
            run_search_step(payload, StepPlacement('python_process'))
        manifest = implementation_manifest()
        manifest['entrypoint'] = 'os:system'
        with self.assertRaises(ValueError):
            _execute({'record_type': 'loop_step_invocation/v1', 'invocation_id': 'test',
                'upstream_loop_ref': 'test.owner', 'implementation': manifest, 'payload': payload})

    def test_process_input_is_bounded_and_nonfinite_options_refused(self):
        for duration in (float('inf'), float('nan'), 0):
            with self.assertRaises(ValueError):
                StepPlacement(timeout_seconds=duration)
        with self.assertRaises(ValueError):
            run_search_step({'snapshot_json': '[]', 'need': 'anything', 'limit': 1},
                StepPlacement(maximum_message_bytes=1))

    def test_real_source_paths_versions_cli_entries_and_symbols_are_searchable(self):
        repo = Path(__file__).resolve().parents[2]
        indexed = index_sources(SourceIndexRequest(str(repo), 'test:working-source',
            ('pyproject.toml', 'src/loop_engine/core/record_operations.py')),
            self.catalog, self.store, authorize)
        self.assertFalse(indexed['code_imported'])
        self.assertFalse(indexed['execution_authorized'])
        self.assertTrue(any(item['command'] == 'loop-engine' for item in indexed['records'][0]['source_metadata']['entrypoints']))
        self.assertTrue(any(item['name'] == 'RecordOperationService' for item in indexed['records'][1]['source_metadata']['symbols']))
        snapshot = self.catalog.snapshot(tuple(item['reference'] for item in indexed['records']))
        result = run_search_step({'snapshot_json': snapshot.records_json, 'need': 'RecordOperationService loop-engine CLI', 'limit': 10})
        self.assertTrue(result['value']['hits'])
        self.assertTrue(all(hit['layer'] == 'code_intelligence' for hit in result['value']['hits']))

    def test_source_inventory_refuses_traversal_before_any_publication(self):
        with self.assertRaises(ValueError):
            index_sources(SourceIndexRequest(str(self.root), 'fixture', ('../outside.py',)),
                self.catalog, self.store, authorize)
        self.assertFalse((self.root / 'catalog').exists())


if __name__ == '__main__':
    unittest.main()
