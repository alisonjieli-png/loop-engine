"""Offline bundle selection and native-path invariants; no harness is invoked."""
from dataclasses import replace
import hashlib
import json
import unittest

from loop_engine.core.context_artifacts import ContextArtifactRef
import opencode_instance as instances


class InstanceChecks(unittest.TestCase):
    def setUp(self):
        self.bytes = {}
        self.reads = []
        self.core_resource = self.resource('core.context', 'context', 'context/core.txt', b'core')
        self.selected = self.resource('step.skill', 'skill', '.opencode/skills/step/SKILL.md', b'step')
        self.unselected = self.resource('other.context', 'context', 'context/other.txt', b'unrelated')
        self.catalog = (self.selected, self.unselected)
        self.core = instances.CoreBundle('fixture.core', '1.0.0', (self.core_resource,),
            ('read',), ('read', 'skill'), 1000)
        self.grant = instances.InstanceGrant('activation:1', 'step:orient@1', 'host.scope@1',
            (self.selected.reference, self.unselected.reference), ('read', 'skill'), 1000)
        self.selection = instances.InstanceSelection('opencode', 'activation:1', 'step:orient@1',
            self.core.digest, (self.selected.reference,), ('skill',), 'selection:user-fixture@1', self.grant.digest)

    def resource(self, name, kind, path, body):
        digest = hashlib.sha256(body).hexdigest()
        self.bytes[digest] = body
        return instances.BundleResource(name, '1.0.0', kind, path,
            ContextArtifactRef(digest, len(body)))

    def load(self, reference):
        self.reads.append(reference.digest)
        return self.bytes[reference.digest]

    def compile(self, selection=None, core=None, catalog=None, loader=None, grant=None):
        return instances.compile_instance(core or self.core, selection or self.selection,
            self.catalog if catalog is None else catalog, loader or self.load, grant=grant or self.grant)

    def test_native_never_prepares_harness_or_hydrates_context(self):
        native_result = object()
        def forbidden():
            raise AssertionError('native mode touched optional harness')
        native = instances.InstanceSelection()
        self.assertIsNone(instances.compile_instance(None, native, None, forbidden))
        self.assertIs(instances.run_optional(native, lambda: native_result, forbidden, forbidden), native_result)
        self.assertFalse(self.reads)

    def test_core_is_pinned_and_only_selected_optional_material_is_loaded(self):
        result = self.compile()
        manifest = json.loads(result.manifest_json)
        self.assertEqual(self.reads, [self.core_resource.artifact_ref.digest, self.selected.artifact_ref.digest])
        self.assertEqual(manifest['core_digest'], self.core.digest)
        self.assertEqual(manifest['permissions'], {'*': 'deny', 'read': 'allow', 'skill': 'allow'})
        self.assertTrue(manifest['fresh_session_required'])

    def test_step_selection_changes_manifest_without_changing_core(self):
        first = self.compile()
        grant = replace(self.grant, step_ref='step:verify@1', allowed_resource_refs=(self.unselected.reference,))
        second = self.compile(replace(self.selection, step_ref='step:verify@1', grant_digest=grant.digest,
            selected_resource_refs=(self.unselected.reference,), selected_tools=()), grant=grant)
        self.assertNotEqual(first.digest, second.digest)
        self.assertEqual(json.loads(first.manifest_json)['core_digest'], json.loads(second.manifest_json)['core_digest'])

    def test_unapproved_reference_refused_before_any_hydration(self):
        with self.assertRaises(ValueError):
            self.compile(replace(self.selection, selected_resource_refs=('unknown@1',)))
        self.assertFalse(self.reads)

    def test_stale_core_refused_before_hydration(self):
        with self.assertRaises(ValueError):
            self.compile(replace(self.selection, core_digest='0' * 64))
        self.assertFalse(self.reads)

    def test_step_cannot_expand_tool_authority(self):
        with self.assertRaises(ValueError):
            self.compile(replace(self.selection, selected_tools=('bash',)))
        self.assertFalse(self.reads)

    def test_step_cannot_overwrite_a_core_path(self):
        collision = self.resource('step.overwrite', 'context', 'context/core.txt', b'changed')
        grant = replace(self.grant, allowed_resource_refs=(collision.reference,))
        selection = replace(self.selection, grant_digest=grant.digest, selected_resource_refs=(collision.reference,))
        with self.assertRaises(ValueError):
            self.compile(selection, catalog=(collision,), grant=grant)
        self.assertFalse(self.reads)

    def test_changed_bytes_refused(self):
        with self.assertRaises(ValueError):
            self.compile(loader=lambda _ref: b'changed')

    def test_duplicate_or_missing_catalog_reference_refused(self):
        for catalog in ((), (self.selected, self.selected)):
            with self.assertRaises(ValueError):
                self.compile(catalog=catalog)
        self.assertFalse(self.reads)

    def test_hydration_size_refused_before_loading(self):
        grant = replace(self.grant, maximum_hydration_bytes=1)
        with self.assertRaises(ValueError):
            self.compile(replace(self.selection, grant_digest=grant.digest), grant=grant)
        self.assertFalse(self.reads)

    def test_path_escape_and_wrong_kind_paths_refused(self):
        for path in ('../outside', '/etc/passwd', 'context/../other', '.opencode/plugins/override.js'):
            with self.assertRaises(ValueError):
                self.resource('invalid', 'context', path, b'body')

    def test_wildcard_tool_names_and_untyped_selection_refused(self):
        with self.assertRaises(ValueError):
            replace(self.core, permitted_tools=('read', '*'))
        with self.assertRaises(TypeError):
            instances.run_optional({'backend': 'native'}, lambda: None, lambda: None, lambda: None)

    def test_changed_or_wrong_scope_grant_is_refused_before_loading(self):
        for grant in (replace(self.grant, step_ref='another@1'),
                      replace(self.grant, permitted_tools=('read', 'skill', 'bash')),
                      replace(self.grant, maximum_hydration_bytes=1001),
                      replace(self.grant, authority_ref='changed-authority')):
            with self.assertRaises(ValueError): self.compile(grant=grant)
        self.assertFalse(self.reads)


if __name__ == '__main__':
    unittest.main()
