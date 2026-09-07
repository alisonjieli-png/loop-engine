"""Offline model selection contracts with explicitly labeled gateway fixtures."""
import hashlib
import json
import unittest

from loop_engine.code_nodes.solution_model_port import FixtureModelExecutionRequest, fixture_model_execution
from loop_engine.core.context_artifacts import ContextArtifactRef
from opencode_instance import BundleResource, CoreBundle, InstanceGrant
from opencode_resource_selection import SelectionRequest, select_resources, access_inventory, assess_resource_needs


class SelectionChecks(unittest.TestCase):
    def setUp(self):
        body = b'PRIVATE_BODY_NOT_DISCLOSED'
        self.resource = BundleResource('step.check', '1.0.0', 'skill', '.opencode/skills/check/SKILL.md',
            ContextArtifactRef(hashlib.sha256(body).hexdigest(), len(body)), 'Arithmetic checking guidance.')
        self.core = CoreBundle('core', '1.0.0', (), (), ('read', 'skill'), 4096)
        self.grant = InstanceGrant('activation.1', 'inspect@1', 'host.fixture', (self.resource.reference,), ('read', 'skill'), 4096)
        self.request = SelectionRequest('Check a small arithmetic result.', 'activation.1', 'inspect@1', True, True)

    def model(self, text):
        return fixture_model_execution(FixtureModelExecutionRequest((text,), max_model_calls=1,
            forbidden_prompt_fragments=('PRIVATE_BODY_NOT_DISCLOSED',)))

    def test_fenced_selection_resolves_compact_ids_to_exact_refs(self):
        raw = '```json\n' + json.dumps({'resource_ids': ['step.check'], 'tools': ['skill'], 'reason': 'Relevant check.'}) + '\n```'
        selected, evidence, _ = select_resources(self.core, (self.resource,), self.request, self.model(raw), grant=self.grant)
        self.assertEqual(selected.selected_resource_refs, (self.resource.reference,))
        self.assertEqual(selected.core_digest, self.core.digest)
        self.assertFalse(evidence['resource_bodies_disclosed'])
        self.assertFalse(evidence['harness_started'])
        self.assertEqual(evidence['physical_model_calls'], 1)
        self.assertEqual(evidence['terminal_code'], 'ACCEPTED')

    def test_empty_selection_is_valid(self):
        selected, _, _ = select_resources(self.core, (self.resource,), self.request,
            self.model('{"resource_ids":[],"tools":[],"reason":"No optional material needed."}'), grant=self.grant)
        self.assertEqual(selected.selected_resource_refs, ())

    def test_unknown_id_tool_or_core_override_refused(self):
        cases = [
            {'resource_ids': ['unknown'], 'tools': [], 'reason': 'Wrong reference.'},
            {'resource_ids': [], 'tools': ['bash'], 'reason': 'Unapproved tool.'},
            {'resource_ids': [], 'tools': [], 'reason': 'Override.', 'core_digest': 'changed'},
        ]
        for value in cases:
            with self.assertRaises(ValueError):
                select_resources(self.core, (self.resource,), self.request, self.model(json.dumps(value)), grant=self.grant)

    def test_missing_model_or_disclosure_grant_refused(self):
        from dataclasses import replace
        for request in (replace(self.request, authorize_model_calls=False),
                        replace(self.request, allow_descriptor_disclosure=False)):
            with self.assertRaises(PermissionError):
                select_resources(self.core, (self.resource,), request, self.model('{}'), grant=self.grant)

    def test_duplicate_model_fields_are_not_silently_overwritten(self):
        with self.assertRaises(ValueError):
            select_resources(self.core, (self.resource,), self.request,
                self.model('{"resource_ids":[],"resource_ids":["step.check"],"tools":[],"reason":"Ambiguous."}'), grant=self.grant)

    def test_access_inventory_is_grant_scoped_and_body_free(self):
        inventory = access_inventory(self.core, (self.resource,), self.grant)
        self.assertEqual(inventory['permitted_tools'], ['read', 'skill'])
        self.assertEqual(inventory['body_materializations'], 0)
        self.assertNotIn('PRIVATE_BODY_NOT_DISCLOSED', json.dumps(inventory))

    def test_assessment_can_proceed_search_or_ask_without_granting_access(self):
        for disposition in ('READY', 'SEARCH', 'REQUEST_ACCESS', 'ASK_USER', 'ABSTAIN'):
            raw = json.dumps({'disposition': disposition, 'tool_needs': [], 'context_needs': [],
                'search_queries': ['arithmetic check'] if disposition == 'SEARCH' else [],
                'user_questions': ['Which input is intended?'] if disposition == 'ASK_USER' else [],
                'reason': 'Explicit resource assessment.'})
            result, _ = assess_resource_needs(self.core, (self.resource,), self.request, self.model(raw), grant=self.grant)
            self.assertEqual(result['disposition'], disposition)
            self.assertFalse(result['grants_authority'])
            self.assertEqual(result['physical_model_calls'], 1)

    def test_assessment_rejects_extra_permission_field(self):
        raw = json.dumps({'disposition': 'READY', 'tool_needs': [], 'context_needs': [],
            'search_queries': [], 'user_questions': [], 'reason': 'Malformed authority.', 'permit_bash': True})
        with self.assertRaises(ValueError):
            assess_resource_needs(self.core, (self.resource,), self.request, self.model(raw), grant=self.grant)


if __name__ == '__main__':
    unittest.main()
