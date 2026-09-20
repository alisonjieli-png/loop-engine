"""Check the limits that keep the source graph from becoming false evidence."""
from __future__ import annotations

import sys
import unittest
import json
import tempfile
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import architecture_audit as audit
from architecture_audit_view import render
from architecture_audit_evidence import check_evidence, component_rows, source_identity
from architecture_report_data import historical_comparison, report_sections
from website_comparison import website_comparison


class StructureTests(unittest.TestCase):
    def test_candidate_review_is_embedded_without_promoting_a_new_layer(self):
        result = report_sections(audit.REPOSITORY)["candidate_review"]
        self.assertEqual(len(result["records"]), 12)
        self.assertEqual({row["intelligence_layer"] for row in result["records"]},
                         {"context", "code", "runtime_history_solution", "user_feedback"})
        self.assertTrue(all(row["lifecycle"] == "candidate" for row in result["records"]))
        self.assertFalse(result["report"]["hosted_publication"])
        self.assertEqual(result["report"]["review_search"]["normal_search_hits"], 0)

    def test_new_comparisons_cross_the_final_html_serialization_boundary(self):
        inventory = {"source_revision": "a"*40, "files": [], "python": {}, "relationships": [],
                     **report_sections(audit.REPOSITORY)}
        rendered = render(inventory, {})
        self.assertIn('"website_comparison": {"state": "dated_public_website_review"', rendered)
        self.assertIn('"candidate_review": {"state": "review_only_not_published"', rendered)
        self.assertIn('"normal_search_excluded": 12', rendered)

    def test_website_population_covers_every_known_historical_vendor_without_claiming_superiority(self):
        result = website_comparison(audit.REPOSITORY)
        self.assertEqual(len(result["rows"]), 24)
        self.assertEqual(sum(row["cohort"] == "historical_comparison" for row in result["rows"]), 19)
        self.assertEqual(set(result["unresolved_identities"]), {"Overmind", "Lemma"})
        self.assertIn("No overall superiority", result["ranking"])
        self.assertTrue(all(row["scope"] == "signed_out_homepage_only" for row in result["rows"]))

    def test_website_unknowns_are_not_negative_feature_claims(self):
        result = website_comparison(audit.REPOSITORY)
        states = {signal["state"] for row in result["rows"] for signal in row["page_signals"].values()}
        self.assertEqual(states, {"link_observed", "not_observed_in_sample"})
        self.assertTrue(all(link["url"].startswith("https://") for row in result["rows"]
                            for signal in row["page_signals"].values() for link in signal["links"]))
        self.assertIn("website_comparison", report_sections(audit.REPOSITORY))

    def test_original_feature_tables_preserve_all_cells_and_measured_denominator(self):
        result = historical_comparison(audit.REPOSITORY / "docs/research/COMPETITIVE-LANDSCAPE-AND-MONETIZATION-2026-09-18.md")
        self.assertEqual(len(result["tables"]), 6)
        self.assertEqual(result["feature_count"], 77)
        self.assertTrue(all(len(table["rows"]) == 21 for table in result["tables"]))
        memory = next(table for table in result["tables"] if table["title"] == "Memory")
        self.assertEqual(memory["rows"][0][memory["columns"].index("One task working folder")], "P")
        self.assertIn("not a verified absence", result["limits"])
        self.assertIn("Context Intelligence served as records", result["definitions"])
        self.assertIn("Loop Engine (this repository)", result["notes"])

    def test_malformed_historical_cell_or_row_is_not_silently_reinterpreted(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "comparison.md"
            for row in ("| Fixture | YES |", "| Fixture | Y | unexpected |"):
                source.write_text("### Memory\n\n| Company | Persistent memory |\n|---|---|\n"+row+"\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    historical_comparison(source)

    def test_single_file_report_embeds_styles_library_and_data_without_external_assets(self):
        inventory = {"source_revision": "a"*40, "files": [], "python": {}, "relationships": [],
                     "questions": [{"question": "@@SCRIPT@@ </script><script>bad()</script>"}]}
        rendered = render(inventory, {})
        class Assets(HTMLParser):
            def __init__(self):
                super().__init__(); self.external = []
            def handle_starttag(self, tag, attributes):
                attrs = dict(attributes)
                if tag in {"script", "img", "iframe"} and attrs.get("src"):
                    self.external.append(attrs["src"])
                if tag == "link" and attrs.get("rel") == "stylesheet":
                    self.external.append(attrs.get("href"))
        parser = Assets(); parser.feed(rendered)
        self.assertEqual(parser.external, [])
        self.assertIn('id="elk-library"', rendered)
        self.assertIn("Eclipse Public License", rendered)
        self.assertNotIn("</script><script>bad()", rendered)
        self.assertIn('"question": "@@SCRIPT@@ \\u003c', rendered)

    def test_report_has_every_level_journey_and_an_authoritative_plan_snapshot(self):
        result = report_sections(audit.REPOSITORY)
        self.assertEqual({view["id"] for view in result["architecture"]["views"]},
                         {"system", "runtime", "practitioner", "solution", "intelligence", "retrieval",
                          "engines", "capabilities", "assurance", "history", "resources", "improvement",
                          "high", "medium", "low", "access", "execution", "website"})
        self.assertEqual(result["architecture"]["default_view"], "system")
        self.assertEqual(result["roadmap"]["source"], "docs/roadmap/roadmap.yaml")
        self.assertEqual(len(result["roadmap"]["source_sha256"]), 64)
        self.assertTrue(any(step["id"] == "S-6.21" for step in result["roadmap"]["steps"]))
        self.assertTrue(all("Not verified" in gate["state"] for gate in result["roadmap"]["gates"]))
        self.assertIn("owner_checklist", result["documents"])
        self.assertIn("developer_handoff", result["documents"])
        self.assertIn("launch_benefits", result["documents"])
        self.assertEqual(len(result["roadmap"]["delivery_batches"]), 17)
        self.assertEqual(sum(len(row["verification_cases"]) for row in result["roadmap"]["delivery_batches"]), 85)
        self.assertIn("D-17", [row["id"] for row in result["roadmap"]["delivery_batches"]])
        self.assertEqual(len(result["roadmap"]["launch_benefits"]), 3)

    def test_hosting_and_full_architecture_are_embedded_not_external_handoffs(self):
        result = report_sections(audit.REPOSITORY)
        self.assertIn("Fly.io", result["hosting"]["title"])
        self.assertEqual(len(result["hosting"]["do_now"]), 6)
        self.assertTrue(all(row["send"] and row["wait"] and row["steps"] for row in result["hosting"]["do_now"]))
        self.assertTrue({"runtime_guide", "practitioner_guide", "solution_guide", "intelligence_guide",
                         "configuration_dimensions", "wrapper_direction"} <= set(result["documents"]))
        self.assertIn("SQLite", result["hosting"]["status"])
        self.assertIn("not a qualified paid release", result["hosting"]["status"])

    def test_relative_imports_and_test_only_imports_are_distinct(self):
        source = '''from ..loop.runtime_context import LoopRuntimeContext
def run(value: str) -> dict:
    return dict(value=value)
def self_test():
    from .guardrail_intelligence import Guardrail
    check("a_known_wrong_result_is_refused", True)
'''
        result = audit.python_structure("src/loop_engine/core/example.py", source)
        self.assertEqual(result["imports"][0]["module"], "loop_engine.loop.runtime_context")
        self.assertFalse(result["imports"][0]["test_context"])
        self.assertEqual(result["imports"][1]["module"], "loop_engine.core.guardrail_intelligence")
        self.assertTrue(result["imports"][1]["test_context"])
        self.assertEqual(result["symbols"][0]["arguments"][0], {"name": "value", "type": "str"})
        self.assertEqual(result["symbols"][0]["returns"], "dict")
        self.assertTrue(any(row["kind"] == "named_check" for row in result["tests"]))

    def test_class_fields_methods_and_dynamic_calls_remain_inspectable(self):
        result = audit.python_structure("src/loop_engine/catalog/example.py", '''class Store:
    version: str
    def get(self, ref: str) -> object:
        return self.adapter.get(ref)
''')
        self.assertEqual(result["symbols"][0]["fields"], [{"name": "version", "type": "str"}])
        self.assertEqual(result["symbols"][1]["name"], "Store.get")
        self.assertEqual(result["calls"][0]["expression"], "self.adapter.get")
        self.assertNotIn("resolved_target", result["calls"][0])

    def test_invalid_python_is_not_silently_counted_as_parsed(self):
        with self.assertRaises(SyntaxError):
            audit.python_structure("broken.py", "def broken(:")

    def test_comparison_keeps_documented_absence_distinct_from_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "comparison.md"
            source.write_text("## A dated comparison\n\n| Product | Capability |\n|---|---|\n"
                              "| Fixture | Not documented |\n| Second fixture | Unverified |\n", encoding="utf-8")
            result = audit.comparison_tables(source)
            self.assertEqual(result["tables"][0]["rows"],
                             [["Fixture", "Not documented"], ["Second fixture", "Unverified"]])
            self.assertEqual(result["state"], "dated_primary_source_documentation_review")

    def test_call_expressions_do_not_copy_literal_bodies(self):
        result = audit.python_structure("example.py", '(lambda: "PRIVATE_FIXTURE_BODY")()')
        self.assertEqual(result["calls"][0]["expression"], "<Lambda>")
        self.assertNotIn("PRIVATE_FIXTURE_BODY", str(result))

    def test_rendered_source_data_cannot_close_its_script_element(self):
        inventory = {"source_revision": "a" * 40,
                     "files": [{"path": "readme.md", "folder": ".", "inspection": "text_read_structurally",
                                "semantic_review": "not_yet_recorded", "headings": ["</script><script>bad()</script>"]}],
                     "python": {}, "relationships": []}
        text = render(inventory, {"files": 1, "python_files": 0, "entities": 1,
                                  "relationships": 0, "call_sites": 0})
        self.assertNotIn("</script><script>bad()", text)
        self.assertIn("\\u003c/script>", text)
        self.assertIn("not a Loop execution graph", text)

    def test_component_rows_never_infer_invocation_or_passes_from_source(self):
        path = "src/loop_engine/example.py"
        parsed = audit.python_structure(path, '"""A measured fixture."""\ndef self_test():\n    pass\n')
        result = component_rows({"files": [{"path": path, "folder": "src/loop_engine",
                                             "semantic_review": "not_yet_recorded"}],
                                 "python": {path: parsed},
                                 "entry_points": {"solve_path": {"modules": [parsed["module"]]}}})
        self.assertEqual(result[0]["static_import_paths"], ["solve_path"])
        self.assertIsNone(result[0]["offline_checks"])
        self.assertEqual(result[0]["observed_invocation"], "not_measured_by_this_inventory")
        self.assertEqual(result[0]["test_declarations"], 1)

    def test_evidence_binds_the_complete_source_and_counts_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/loop_engine/example.py"
            source.parent.mkdir(parents=True)
            source.write_text("value = 1\n", encoding="utf-8")
            identity = source_identity(root)
            capture = {"record_type": "architecture_check_capture/v1",
                       "source_before": identity, "source_after": identity,
                       "suite": {"tests": [
                           {"owner_module": "loop_engine.example", "passed": True},
                           {"owner_module": "loop_engine.example", "passed": False},
                           {"owner_module": "loop_engine.example", "passed": None, "not_tested": True}]}}
            evidence = root / "verification.json"
            evidence.write_text(json.dumps(capture), encoding="utf-8")
            result = check_evidence(root, evidence)
            self.assertEqual(result["modules"]["loop_engine.example"],
                             {"passed": 1, "failed": 1, "not_tested": 1})
            self.assertFalse(result["provider_qualification"])
            source.write_text("value = 2\n", encoding="utf-8")
            self.assertEqual(check_evidence(root, evidence)["state"], "stale_source")
            self.assertEqual(check_evidence(root, evidence)["modules"], {})

    def test_missing_and_malformed_evidence_never_becomes_a_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "verification.json"
            self.assertEqual(check_evidence(root, evidence)["state"], "not_recorded")
            evidence.write_text('{"record_type":"obsolete/v0"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                check_evidence(root, evidence)

    def test_a_symbolic_link_cannot_hide_executable_source_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "src/loop_engine"
            package.mkdir(parents=True)
            (package / "fixture.py").symlink_to(root / "not-hashed.py")
            with self.assertRaises(ValueError):
                source_identity(root)

    def test_source_identity_includes_non_python_runtime_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "src/loop_engine"
            package.mkdir(parents=True)
            prompt = package / "resource.md"
            prompt.write_text("current instructions", encoding="utf-8")
            before = source_identity(root)
            prompt.write_text("changed instructions", encoding="utf-8")
            self.assertNotEqual(before, source_identity(root))


if __name__ == "__main__":
    unittest.main()
