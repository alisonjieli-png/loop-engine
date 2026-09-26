"""The well-known served attributes are valid schema declarations, and an item's harness kind is derived by rule.

Roadmap steps S-6.205 and S-6.206. Known-wrong cases: a style that names no harness kind is ignored, an unknown served
kind falls to code_module, and a declaration that broke the schema rules would be refused by the schema reader.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

from loop_engine.core.service_runtime import catalogue_attributes as attributes  # noqa: E402
from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema  # noqa: E402
from loop_engine.core.service_runtime.records import ServiceRuntimeError  # noqa: E402


class CatalogueAttributeTest(unittest.TestCase):
    def test_every_well_known_attribute_is_a_valid_declaration(self):
        schema = CatalogueAttributeSchema.from_dict(attributes.declare({"record_type": "catalogue_attribute_schema/v1",
                                                                        "attributes": []}))
        self.assertEqual([item.name for item in schema.attributes], ["harness_kind", "step_functions", "tier"])
        values = schema.validate_values({"tier": "community", "harness_kind": "hook", "step_functions": ["acting"]})
        self.assertEqual(values["harness_kind"], "hook")
        self.assertEqual(schema.shown_values(values), values)
        self.assertEqual(schema.filter_request({"harness_kind": {"any_of": ["hook", "command"]}}),
                         (("harness_kind", "any_of", ("hook", "command")),))
        with self.assertRaises(ServiceRuntimeError):
            schema.validate_values({"harness_kind": "dance"})

    def test_declare_replaces_an_earlier_declaration_of_the_same_name_once(self):
        older = {"record_type": "catalogue_attribute_schema/v1",
                 "attributes": [{"name": "tier", "type": "keyword"}, {"name": "cited_source", "type": "keyword"}]}
        declared = attributes.declare(older, attributes.TIER_ATTRIBUTE)
        self.assertEqual([item["name"] for item in declared["attributes"]], ["cited_source", "tier"])
        self.assertEqual(declared["attributes"][-1]["type"], "choice")
        twice = attributes.declare(attributes.declare(older))
        self.assertEqual(len(twice["attributes"]), 4)

    def test_the_harness_kind_comes_from_provenance_then_styles_then_roles_then_the_served_kind(self):
        kind = attributes.harness_kind_of
        self.assertEqual(kind("tool", ("plugin_manifest", "plugin_manifest"), ()), "plugin_manifest")
        self.assertEqual(kind("instruction_file", ("subagent", "plugin_agent"), ()), "subagent")
        self.assertEqual(kind("skill", ("claude", "codex"), ("skill_definition", "skill_script")), "skill")
        self.assertEqual(kind("instruction_file", ("claude",), ("hook",)), "hook")
        self.assertEqual(kind("tool", (), ()), "code_module")
        self.assertEqual(kind("skill", (), ()), "skill")
        self.assertEqual(kind("anything", (), ()), "code_module")
        self.assertEqual(kind("skill", ("claude",), (), declared="rules"), "rules")
        self.assertEqual(kind("skill", ("claude",), (), declared="dance"), "skill")
        for name in attributes.HARNESS_KINDS:
            self.assertTrue(attributes.harness_kind_label(name))
        self.assertEqual(attributes.harness_kind_label("protocol_server_configuration"), "Protocol server configuration")


if __name__ == "__main__":
    unittest.main()
