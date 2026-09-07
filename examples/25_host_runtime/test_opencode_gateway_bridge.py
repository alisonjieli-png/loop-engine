"""Offline guard tests for the explicit read-only model-message bridge."""
import unittest
from dataclasses import replace
from types import SimpleNamespace

from opencode_gateway_bridge import (BridgeRequest, validate_model_request, validate_message, normalize_tool_envelope,
                                     bridge_loop_config, record_side_frame)
from opencode_instance import CompiledInstance


class BridgeChecks(unittest.TestCase):
    def test_harness_text_and_unknown_frames_are_counted_not_dropped(self):
        harness_text, unknown = [], []
        self.assertTrue(record_side_frame({'bridge_record': 'harness_text', 'text_digest': 'a' * 64}, harness_text, unknown))
        self.assertTrue(record_side_frame({'bridge_record': 'later_protocol_addition'}, harness_text, unknown))
        self.assertFalse(record_side_frame({'bridge_record': 'harness_event', 'value': {}}, harness_text, unknown))
        self.assertFalse(record_side_frame({'bridge_record': 'finished'}, harness_text, unknown))
        self.assertEqual(harness_text, ['a' * 64])
        self.assertEqual(unknown, ['later_protocol_addition'])

    def setUp(self):
        self.manifest = {'tools': ['read', 'skill']}
        self.body = {'model': 'loop-model', 'messages': [{'role': 'user', 'content': 'data'}],
            'tools': [{'type': 'function', 'function': {'name': 'read', 'parameters': {
                'type': 'object', 'properties': {'filePath': {'type': 'string'}}, 'required': ['filePath'], 'additionalProperties': False}}},
                {'type': 'function', 'function': {'name': 'skill', 'parameters': {
                    'type': 'object', 'properties': {'name': {'type': 'string'}}, 'required': ['name'], 'additionalProperties': False}}}]}
        self.definitions = validate_model_request(self.body, self.manifest)

    def test_valid_selected_read_and_skill(self):
        value = {'content': None, 'tool_calls': [{'name': 'read', 'arguments': {'filePath': '/workspace/context/task.txt'}},
                                               {'name': 'skill', 'arguments': {'name': 'selected'}}]}
        self.assertIs(validate_message(value, self.definitions, {'/workspace/context/task.txt'}, {'selected'}), value)

    def test_advertised_unapproved_tool_and_model_are_refused(self):
        import copy
        changed = copy.deepcopy(self.body); changed['model'] = 'other'
        with self.assertRaises(ValueError): validate_model_request(changed, self.manifest)
        changed = copy.deepcopy(self.body); changed['tools'][0]['function']['name'] = 'bash'
        with self.assertRaises(ValueError): validate_model_request(changed, self.manifest)

    def test_tool_schema_cannot_fetch_external_references(self):
        import copy
        changed = copy.deepcopy(self.body)
        changed['tools'][0]['function']['parameters'] = {'$ref': 'https://unapproved.invalid/schema'}
        with self.assertRaises(ValueError): validate_model_request(changed, self.manifest)

    def test_path_escape_and_unselected_skill_are_refused(self):
        for call in ({'name': 'read', 'arguments': {'filePath': '/etc/passwd'}},
                     {'name': 'read', 'arguments': {'filePath': '/workspace/context/../secret'}},
                     {'name': 'skill', 'arguments': {'name': 'ambient-skill'}},
                     {'name': 'bash', 'arguments': {'command': 'unapproved'}}):
            with self.assertRaises(ValueError):
                validate_message({'content': None, 'tool_calls': [call]}, self.definitions, set(), {'selected'})

    def test_empty_or_extra_reply_fields_are_refused(self):
        with self.assertRaises(ValueError):
            validate_message({'content': None, 'tool_calls': []}, {}, set())
        with self.assertRaises(Exception):
            validate_message({'content': 'answer', 'tool_calls': [], 'approved': True}, {}, set())

    def test_immutable_image_and_finite_supervision_required(self):
        instance = CompiledInstance('{}', ())
        request = BridgeRequest('goal', instance, '/fixture', 'image@sha256:' + 'a' * 64, 'route')
        for fields in ({'image': 'image:latest'}, {'image': 'image@sha256:' + 'x' * 64},
                       {'supervision_seconds': float('inf')}, {'supervision_seconds': float('nan')}):
            with self.assertRaises(ValueError): replace(request, **fields)

    def test_observed_xml_tool_envelope_preserves_typed_values(self):
        import json
        raw = '<tool_calls>\n<invoke name="read"><parameter name="filePath">/workspace/context/task.txt</parameter></invoke>\n</tool_calls>'
        normalized, record = normalize_tool_envelope(raw, self.definitions)
        self.assertEqual(json.loads(normalized), {'content': None, 'tool_calls': [
            {'name': 'read', 'arguments': {'filePath': '/workspace/context/task.txt'}}]})
        self.assertEqual(record['model_calls'], 0)
        self.assertFalse(record['semantic_values_changed'])

    def test_xml_cannot_inject_entities_duplicate_arguments_or_unknown_tools(self):
        samples = (
            '<tool_calls><!DOCTYPE x><invoke name="read"/></tool_calls>',
            '<tool_calls><invoke name="bash"><parameter name="command">bad</parameter></invoke></tool_calls>',
            '<tool_calls><invoke name="read"><parameter name="filePath">a</parameter><parameter name="filePath">b</parameter></invoke></tool_calls>',
            '<tool_calls><invoke name="read"><parameter name="filePath"><value>a</value></parameter></invoke></tool_calls>',
            '<tool_calls><invoke name="read"><parameter name="filePath">a</parameter></invoke></tool_calls> trailing',
        )
        for raw in samples:
            with self.assertRaises(Exception): normalize_tool_envelope(raw, self.definitions)

    def test_one_step_bridge_configuration_accepts_without_reinvocation(self):
        from loop_engine.loop.recursive_loop import Loop, StepOutcome
        calls = []
        owner = Loop('Capture one candidate', bridge_loop_config())
        def handle(*_args):
            calls.append('one physical invocation')
            return StepOutcome('candidate captured', mode='non_deterministic')
        result = owner.run(handler=handle, max_steps=1)
        self.assertEqual(result.terminal_code, 'ACCEPTED')
        self.assertEqual(len(calls), 1)

    def test_complete_json_array_after_provider_tool_marker_is_admitted(self):
        import json
        body = '[{"name":"skill","arguments":{"name":"selected"}}]'
        for raw in ('<tool_calls>\n' + body, '<tool_calls>\n' + body + '\n</tool_calls>'):
            normalized, record = normalize_tool_envelope(raw, self.definitions)
            value = json.loads(normalized)
            validate_message(value, self.definitions, set(), {'selected'})
            self.assertTrue(record['payload_complete'])
            self.assertEqual(record['model_calls'], 0)

    def test_tool_marker_does_not_repair_truncated_or_ambiguous_json(self):
        for payload in ('[{"name":"skill"', '[{"name":"skill","name":"read"}]',
                        '[{"name":"skill"}] trailing'):
            with self.assertRaises(ValueError):
                normalize_tool_envelope('<tool_calls>\n' + payload, self.definitions)


if __name__ == '__main__':
    unittest.main()
