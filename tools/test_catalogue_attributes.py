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
        self.assertEqual([item.name for item in schema.attributes],
                         ["component_form", "geographies", "harness_kind", "industries", "job_titles", "languages",
                          "levels", "step_functions", "tier"])
        self.assertEqual(tuple(item["name"] for item in attributes.WELL_KNOWN_ATTRIBUTES),
                         attributes.WELL_KNOWN_ATTRIBUTE_NAMES)
        values = schema.validate_values({"tier": "community", "harness_kind": "hook", "step_functions": ["acting"],
                                         "job_titles": ["Software Developers"], "industries": ["healthcare"],
                                         "levels": ["senior"], "languages": ["english"], "geographies": ["Canada"]})
        self.assertEqual(values["harness_kind"], "hook")
        self.assertEqual(schema.shown_values(values), values)
        self.assertEqual(schema.filter_request({"harness_kind": {"any_of": ["hook", "command"]}}),
                         (("harness_kind", "any_of", ("hook", "command")),))
        self.assertEqual(schema.filter_request({"industries": {"any_of": ["healthcare"]}, "levels": {"equals": "senior"}}),
                         (("industries", "any_of", ("healthcare",)), ("levels", "any_of", ("senior",))))
        # The language is filtered and shown but not searched, so the default does not enter every item's index.
        self.assertNotIn("english", schema.search_text(values).split())
        self.assertIn("Software Developers", schema.search_text(values))
        with self.assertRaises(ServiceRuntimeError):
            schema.validate_values({"harness_kind": "dance"})
        self.assertEqual(schema.validate_values({"component_form": "api_operation"}), {"component_form": "api_operation"})
        self.assertIn("api_operation", schema.search_text({"component_form": "api_operation"}))
        with self.assertRaises(ServiceRuntimeError):
            schema.validate_values({"component_form": "binary"})

    def test_declare_replaces_an_earlier_declaration_of_the_same_name_once(self):
        older = {"record_type": "catalogue_attribute_schema/v1",
                 "attributes": [{"name": "tier", "type": "keyword"}, {"name": "cited_source", "type": "keyword"}]}
        declared = attributes.declare(older, attributes.TIER_ATTRIBUTE)
        self.assertEqual([item["name"] for item in declared["attributes"]], ["cited_source", "tier"])
        self.assertEqual(declared["attributes"][-1]["type"], "choice")
        twice = attributes.declare(attributes.declare(older))
        self.assertEqual(len(twice["attributes"]), 1 + len(attributes.WELL_KNOWN_ATTRIBUTES))

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



class ComponentFormTest(unittest.TestCase):
    """component_form/v1: a typed, versioned second axis beside the harness kind (September 27, 2026)."""

    def test_every_form_has_a_label_and_at_least_one_served_harness_kind(self):
        self.assertEqual(attributes.COMPONENT_FORM_VERSION, "component_form/v1")
        self.assertEqual(len(attributes.COMPONENT_FORMS), len(set(attributes.COMPONENT_FORMS)))
        for form in attributes.COMPONENT_FORMS:
            self.assertTrue(attributes.component_form_label(form))
            self.assertTrue(attributes.COMPONENT_FORM_KINDS[form])
            self.assertTrue(set(attributes.COMPONENT_FORM_KINDS[form]) <= set(attributes.HARNESS_KINDS))
        for name in ("function", "library_module", "program", "api_operation", "binary_install", "mcp_server",
                     "plugin", "data_table", "evaluation_set"):
            self.assertIn(name, attributes.COMPONENT_FORMS)
        # The served vocabulary of harness kinds is unchanged: clients depend on it.
        self.assertEqual(len(attributes.HARNESS_KINDS), 12)
        self.assertNotIn("component_form", attributes.HARNESS_KINDS)

    def test_the_form_is_derived_from_kind_roles_and_native_format(self):
        form = attributes.component_form_of
        self.assertEqual(form("skill", ("skill_definition",)), "skill")
        self.assertEqual(form("skill", ("skill_definition", "skill_script")), "skill_with_scripts")
        self.assertEqual(form("code_module", ("executable_tool",), "opencode_tool"), "function")
        self.assertEqual(form("code_module", ("executable_tool",), "opencode_plugin"), "plugin")
        self.assertEqual(form("code_module", ("executable_tool",), "code_module"), "library_module")
        self.assertEqual(form("protocol_server_configuration"), "mcp_server")
        self.assertEqual(form("instruction_file"), "instructions")
        self.assertEqual(form("subagent"), "agent")
        self.assertEqual(form("contract_schema"), "schema")
        self.assertEqual(form("harness_settings"), "settings")
        # An unknown harness kind is treated as a code module, the served kind's own fallback.
        self.assertEqual(form("dance"), "library_module")
        for kind in attributes.HARNESS_KINDS:
            self.assertIn(kind, attributes.COMPONENT_FORM_KINDS[form(kind)])

    def test_a_declaration_wins_only_when_the_harness_kind_may_carry_it(self):
        form = attributes.component_form_of
        self.assertEqual(form("code_module", declared="api_operation"), "api_operation")
        self.assertEqual(form("code_module", declared="data_table"), "data_table")
        self.assertEqual(form("contract_schema", declared="data_table"), "data_table")
        # Known wrong: a skill filed as executable code, a server configuration filed as a function, an unknown form.
        for kind, declared, code in (("skill", "data_table", "component_form_kind_mismatch"),
                                     ("skill", "function", "component_form_kind_mismatch"),
                                     ("protocol_server_configuration", "function", "component_form_kind_mismatch"),
                                     ("code_module", "binary", "component_form_unknown"),
                                     ("dance", "function", "harness_kind_unknown")):
            with self.assertRaises(attributes.ComponentFormError) as caught:
                form(kind, declared=declared)
            self.assertEqual(caught.exception.code, code)

    def test_the_record_is_versioned_and_read_strictly(self):
        record = attributes.component_form_record("api_operation", "code_module", attributes.FORM_DECLARED)
        self.assertEqual(record, {"record_type": "component_form/v1", "form": "api_operation",
                                  "basis": "declared_by_supply_line"})
        self.assertEqual(attributes.read_component_form(record, "code_module"), "api_operation")
        wrong = [({**record, "record_type": "component_form/v2"}, "code_module", "component_form_version_unsupported"),
                 ({**record, "note": "x"}, "code_module", "component_form_record_invalid"),
                 ({key: value for key, value in record.items() if key != "basis"}, "code_module",
                  "component_form_record_invalid"),
                 ({**record, "basis": "guessed_from_the_readme"}, "code_module", "component_form_basis_unknown"),
                 (record, "skill", "component_form_kind_mismatch"),
                 ("api_operation", "code_module", "component_form_record_invalid")]
        for value, kind, code in wrong:
            with self.assertRaises(attributes.ComponentFormError) as caught:
                attributes.read_component_form(value, kind)
            self.assertEqual(caught.exception.code, code)
        with self.assertRaises(attributes.ComponentFormError):
            attributes.component_form_record("api_operation", "code_module", "guessed")


if __name__ == "__main__":
    unittest.main()
