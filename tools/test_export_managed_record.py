"""Use real record CRUD and workspace services to test the export boundary."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import export_managed_record as exporting
from loop_engine.core.record_operations_checks import _service, _request, _approve
from loop_engine.core.workspace_contracts import WorkspaceSpec
from loop_engine.core.workspace_local import RestrictedLocalWorkspace


class ExportChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='managed-export-')
        self.root = Path(self.directory.name)
        self.service, _ = _service(self.root)
        request = _request('create')
        created = self.service.execute(request, approval_id=_approve(self.service, request))
        self.assertIs(created.committed, True)
        self.record_id = request.record_id
        self.workspace = RestrictedLocalWorkspace(WorkspaceSpec('export-test', str(self.root)))
        self.request = exporting.ExportRequest(self.record_id, '1', 'view.json', '2026-09-06T19:00:00Z')

    def tearDown(self):
        self.directory.cleanup()

    def plan(self, request=None):
        return exporting.export_record(self.service, self.workspace, request or self.request)

    def test_plan_has_no_output_write(self):
        plan = self.plan()
        self.assertFalse(plan['effects_executed'])
        self.assertFalse((self.root / 'view.json').exists())

    def test_exact_approval_exports_version_and_provenance(self):
        plan = self.plan()
        result = exporting.export_record(self.service, self.workspace, self.request,
            approved_effect_digest=plan['effect_digest'])
        self.assertTrue(result['output_verified'])
        body = json.loads((self.root / 'view.json').read_text())
        self.assertEqual(body['source_record']['record_version'], '1')
        self.assertTrue(body['generated_view'])
        self.assertFalse(body['grants_authority'])
        self.assertEqual(body['view_digest'], exporting.content_digest({
            key: value for key, value in body.items() if key != 'view_digest'}))

    def test_changed_target_or_generation_time_invalidates_approval(self):
        plan = self.plan()
        for request in (replace(self.request, output_path='elsewhere.json'),
                        replace(self.request, generated_at='2026-09-06T19:00:01Z')):
            with self.assertRaisesRegex(ValueError, 'approved export effect'):
                exporting.export_record(self.service, self.workspace, request,
                    approved_effect_digest=plan['effect_digest'])

    def test_overwrite_requires_exact_current_digest(self):
        plan = self.plan()
        exporting.export_record(self.service, self.workspace, self.request,
            approved_effect_digest=plan['effect_digest'])
        before = (self.root / 'view.json').read_bytes()
        stale = replace(self.request, expected_output_digest='0' * 64)
        with self.assertRaisesRegex(ValueError, 'export refused'):
            exporting.export_record(self.service, self.workspace, stale,
                approved_effect_digest=self.plan(stale)['effect_digest'])
        self.assertEqual((self.root / 'view.json').read_bytes(), before)
        current = replace(self.request, expected_output_digest=hashlib.sha256(before).hexdigest())
        self.assertTrue(exporting.export_record(self.service, self.workspace, current,
            approved_effect_digest=self.plan(current)['effect_digest'])['output_verified'])

    def test_missing_revision_and_path_escape_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'managed revision'):
            self.plan(replace(self.request, record_version='99'))
        escape = replace(self.request, output_path='../outside.json')
        with self.assertRaisesRegex(ValueError, 'export refused'):
            exporting.export_record(self.service, self.workspace, escape,
                approved_effect_digest=self.plan(escape)['effect_digest'])

    def test_generation_time_requires_timezone_and_exact_revision(self):
        with self.assertRaises(ValueError):
            replace(self.request, generated_at='2026-09-06T19:00:00')
        with self.assertRaises(ValueError):
            replace(self.request, record_version='')


if __name__ == '__main__':
    unittest.main()
