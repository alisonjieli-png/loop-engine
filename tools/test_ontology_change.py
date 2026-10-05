"""Checks for the ontology_change_planning component: reader, engines, checker, envelope, store, kit and slot.

Each guard has a known-wrong case beside it. The adapter's own kit run needs the
pinned Open Ontologies v2.0.1 binary named by LOOP_ENGINE_OPEN_ONTOLOGIES_BINARY
and is skipped, with that reason, when it is absent; everything else runs offline.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))

from loop_engine.core.ontology_change import conformance, engines  # noqa: E402
from loop_engine.core.ontology_change.component import HostEngines, plan_change  # noqa: E402
from loop_engine.core.ontology_change.contract import (  # noqa: E402
    OntologyChangeRefused, PlanRequest, plan_digest, request_record)
from loop_engine.core.ontology_change.native_engine import closure  # noqa: E402
from loop_engine.core.ontology_change.rdf_terms import (  # noqa: E402
    RdfSyntaxError, canonical_ntriples, graph_digest, parse_ntriples, parse_turtle)
from loop_engine.core.ontology_change.trace_checker import (  # noqa: E402
    check_step, check_trace, read_certificate, write_certificate)
from loop_engine.core.ontology_change.contract import EngineFailure  # noqa: E402

K = conformance.k
T, DOMAIN, RANGE = conformance.T, conformance.DOMAIN, conformance.RANGE
BINARY = os.environ.get(conformance.BINARY_VARIABLE, "")
CHECKER = os.environ.get(conformance.CHECKER_VARIABLE, "")


def native_host(evidence=None, require=False) -> HostEngines:
    return HostEngines(engines.default_installations(), engines.default_policy(), evidence or {}, require)


def first_case_request(**changes) -> dict:
    return conformance._request(conformance.CASES[0], "owl-rl", **changes)


class ReaderTests(unittest.TestCase):
    def test_turtle_reads_to_the_same_graph_as_its_canonical_ntriples(self):
        graph = parse_turtle(conformance.PREFIXES + 'kit:a kit:p ( kit:b "c"@EN 1.5 ) ; kit:q [ kit:r true ] .')
        self.assertEqual(parse_ntriples(canonical_ntriples(graph)), graph)
        self.assertEqual(graph_digest(parse_ntriples(canonical_ntriples(graph))), graph_digest(graph))
        self.assertIn((K("a"), K("q"), "_:b3"), graph)

    def test_relative_references_resolve_as_rfc_3986_section_5_4_says(self):
        from loop_engine.core.ontology_change.rdf_terms import resolve_reference
        base = "http://a/b/c/d;p?q"
        expected = {"g:h": "g:h", "g": "http://a/b/c/g", "./g": "http://a/b/c/g", "g/": "http://a/b/c/g/",
                    "/g": "http://a/g", "//g": "http://g", "?y": "http://a/b/c/d;p?y", "g?y": "http://a/b/c/g?y",
                    "#s": "http://a/b/c/d;p?q#s", "g#s": "http://a/b/c/g#s", ";x": "http://a/b/c/;x",
                    "": "http://a/b/c/d;p?q", ".": "http://a/b/c/", "..": "http://a/b/", "../g": "http://a/b/g",
                    "../..": "http://a/", "../../g": "http://a/g", "../../../g": "http://a/g",
                    "/./g": "http://a/g", "/../g": "http://a/g", "g.": "http://a/b/c/g.", "..g": "http://a/b/c/..g",
                    "./../g": "http://a/b/g", "./g/.": "http://a/b/c/g/", "g/../h": "http://a/b/c/h",
                    "g;x=1/../y": "http://a/b/c/y", "g?y/../x": "http://a/b/c/g?y/../x",
                    "g#s/../x": "http://a/b/c/g#s/../x"}
        for reference, target in expected.items():
            self.assertEqual(resolve_reference(base, reference), target, reference)

    def test_known_wrong_documents_are_refused_with_their_place(self):
        for text in ("kit:a kit:b kit:c .", conformance.PREFIXES + "kit:a kit:b { kit:c } .",
                     "<relative> <http://e/p> <http://e/o> .", conformance.PREFIXES + 'kit:a kit:b "open .'):
            with self.assertRaises(RdfSyntaxError) as caught:
                parse_turtle(text)
            self.assertIn("line", str(caught.exception))


class NativeEngineTests(unittest.TestCase):
    def test_a_literal_never_becomes_a_subject(self):
        graph = parse_turtle(conformance.PREFIXES + 'kit:a kit:name "x" . kit:name rdfs:range kit:Text .')
        result, derivations = closure(graph, "rdfs", 1000)
        self.assertFalse([triple for triple in result if triple[0].startswith('"')])
        self.assertEqual(derivations, {})

    def test_derivations_do_not_depend_on_the_order_of_reading(self):
        graph = parse_turtle(conformance.PREFIXES + conformance.CASES[7].base)
        first = closure(graph, "owl-rl", 1000)[1]
        second = closure(frozenset(sorted(graph, reverse=True)), "owl-rl", 1000)[1]
        self.assertEqual(first, second)

    def test_known_wrong_a_closure_past_its_bound_is_refused(self):
        graph = parse_turtle(conformance.PREFIXES + conformance.CASES[4].base)
        with self.assertRaises(EngineFailure) as caught:
            closure(graph, "owl-rl", len(graph))
        self.assertEqual(caught.exception.kind, "limit_exceeded")


class CheckerTests(unittest.TestCase):
    STEP = {"rule": "rdfs2", "conclusion": [K("a"), T, K("C")], "premises": [[K("a"), K("p"), K("b")],
                                                                            [K("p"), DOMAIN, K("C")]]}
    ASSERTED = {(K("a"), K("p"), K("b")), (K("p"), DOMAIN, K("C"))}

    def test_a_genuine_step_passes_and_the_w3c_name_is_the_same_rule(self):
        self.assertTrue(check_trace(self.ASSERTED, [self.STEP]).ok)
        self.assertEqual(check_step("prp-dom", self.STEP["conclusion"], self.STEP["premises"]), "")

    def test_known_wrong_steps_are_refused_by_index_and_reason(self):
        wrong = (
            {**self.STEP, "conclusion": [K("a"), T, K("D")]},
            {**self.STEP, "premises": list(reversed(self.STEP["premises"]))},
            {**self.STEP, "rule": "rdfs9"},
            {**self.STEP, "rule": "made-up"},
            {**self.STEP, "conclusion": ['"a"', T, K("C")]},
        )
        for step in wrong:
            verdict = check_trace(self.ASSERTED, [self.STEP, step])
            self.assertFalse(verdict.ok, step)
            self.assertEqual(verdict.first_rejected, 1)
        unsupported = check_trace({(K("p"), DOMAIN, K("C"))}, [self.STEP])
        self.assertEqual((unsupported.ok, unsupported.first_rejected), (False, 0))
        outside = check_trace(self.ASSERTED, [self.STEP], rule_table=("rdfs9",))
        self.assertFalse(outside.ok)

    def test_the_two_file_certificate_reads_back_to_the_same_trace(self):
        asserted, steps = read_certificate(*write_certificate(self.ASSERTED, [self.STEP]))
        self.assertEqual(set(asserted), self.ASSERTED)
        self.assertEqual(steps, [self.STEP])
        with self.assertRaises(ValueError):
            read_certificate("a\tb\n", "")


class EnvelopeTests(unittest.TestCase):
    def test_known_wrong_requests_are_refused_before_any_engine_runs(self):
        cases = ((first_case_request(base_digest=graph_digest(())), "base_digest_mismatch"),
                 ({**first_case_request(), "profile": "owl-dl"}, "profile_unsupported"),
                 ({**first_case_request(), "change": {"added": [], "removed": []}}, "change_invalid"),
                 ({**first_case_request(), "extra": 1}, "request_invalid"))
        with patch("loop_engine.core.ontology_change.native_engine.NativeRuleEngine.plan") as engine:
            for request, code in cases:
                outcome = plan_change(request, native_host())
                self.assertEqual((outcome.failure or {}).get("code"), code, request.get("profile"))
                self.assertEqual(outcome.decisions, ())
            engine.assert_not_called()

    def test_the_plan_is_bound_to_both_digests_and_its_digest_repeats(self):
        first, second = (plan_change(first_case_request(), native_host()).plan for _ in range(2))
        base = parse_turtle(conformance.PREFIXES + conformance.CASES[0].base)
        self.assertEqual(first["base_digest"], graph_digest(base))
        self.assertEqual(first["proposed_digest"], graph_digest(base | set(conformance.CASES[0].added)))
        self.assertEqual(first["plan_digest"], plan_digest(first))
        self.assertEqual(first["plan_digest"], second["plan_digest"])

    def test_blank_nodes_make_the_adapter_ineligible_by_capability(self):
        text = conformance.PREFIXES + "kit:a kit:p [ kit:q kit:r ] ."
        request = request_record(text, graph_digest(parse_turtle(text)), added=((K("a"), DOMAIN, K("C")),))
        adapter_only = HostEngines(engines.default_installations()[1:], engines.default_policy(
            ("open_ontologies_cli",), ()), {}, False)
        outcome = plan_change(request, adapter_only)
        refusals = [refusal["detail"] for entry in outcome.decisions[0]["eligibility"]
                    for refusal in entry["refusals"]]
        self.assertEqual(outcome.failure["code"], "no_eligible_engine")
        self.assertIn("blank nodes in the base or the proposal", refusals)

    def test_selection_follows_declared_order_evidence_and_fallback(self):
        report = conformance.run_conformance_kit(engines.NATIVE_ENGINE_ID)
        self.assertTrue(report["passed"], report)
        for name, passed in conformance._selection_checks(report):
            self.assertTrue(passed, name)

    def test_request_reader_canonicalises_and_refuses_blank_nodes_in_a_change(self):
        request = first_case_request()
        request["change"]["added"] = [[K("a"), K("p"), '"x"^^<http://www.w3.org/2001/XMLSchema#string>']]
        self.assertEqual(PlanRequest.from_dict(request).added[0][2], '"x"')
        request["change"]["added"] = [["_:b0", K("p"), K("o")]]
        with self.assertRaises(OntologyChangeRefused) as caught:
            PlanRequest.from_dict(request)
        self.assertEqual(caught.exception.code, "change_invalid")


class StoreAndKitTests(unittest.TestCase):
    def test_the_native_engine_passes_the_kit_alone_with_every_control(self):
        report = conformance.run_conformance_kit(engines.NATIVE_ENGINE_ID, checker_path=CHECKER or None)
        self.assertTrue(report["passed"], [item for item in report["cases"] + report["controls"]
                                           if not item["passed"]])
        self.assertEqual(len(report["cases"]), 12)
        self.assertEqual({item["control"] for item in report["controls"]}, {
            "a_stale_base_digest_is_refused_before_any_engine_runs",
            "a_change_that_removes_an_absent_triple_is_refused",
            "every_listed_consequence_carries_a_trace_the_independent_checker_accepts",
            "a_forged_derivation_trace_is_refused", "a_locked_term_is_refused_at_apply",
            "a_lock_the_plan_never_checked_is_refused", "apply_requires_an_approval_naming_the_plan",
            "a_changed_plan_is_refused", "apply_is_compare_and_swap_on_the_base_digest",
            "rollback_restores_only_the_state_it_replaced"})

    def test_evidence_is_recorded_by_descriptor_and_read_back(self):
        report = {"record_type": "ontology_change_conformance_report/v1", "descriptor_digest": "a" * 64,
                  "passed": True}
        with tempfile.TemporaryDirectory() as folder:
            conformance.write_report(folder, report)
            Path(folder, "b" * 64 + ".json").write_text('{"record_type": "other/v1"}', encoding="utf-8")
            self.assertEqual(conformance.load_evidence(folder), {"a" * 64: report})

    @unittest.skipUnless(BINARY, f"{conformance.BINARY_VARIABLE} names no pinned Open Ontologies binary")
    def test_the_open_ontologies_adapter_passes_the_kit_alone(self):
        report = conformance.run_conformance_kit(engines.ADAPTER_ENGINE_ID, {"binary_path": BINARY},
                                                 checker_path=CHECKER or None)
        self.assertTrue(report["passed"], [item for item in report["cases"] + report["controls"]
                                           if not item["passed"]])


class AdapterAndSlotTests(unittest.TestCase):
    def test_known_wrong_a_missing_or_changed_binary_is_unavailable_and_starts_nothing(self):
        with tempfile.NamedTemporaryFile() as fake, patch("subprocess.run") as run:
            for settings, expected in (({}, "binary_path"), ({"binary_path": fake.name}, "not the pinned")):
                engine = engines.create_engine(engines.ADAPTER_ENGINE_ID, settings)
                available, reason = engine.availability()
                self.assertFalse(available)
                self.assertIn(expected, reason)
                with self.assertRaises(EngineFailure):
                    engine.plan(None)
            run.assert_not_called()

    def test_descriptors_bind_the_engine_source_and_the_pinned_digest(self):
        native = engines.describe_engine(engines.NATIVE_ENGINE_ID)
        adapter = engines.describe_engine(engines.ADAPTER_ENGINE_ID)
        self.assertEqual((native.effects, adapter.isolation), (("pure",), "os_sandbox"))
        self.assertEqual(adapter.source_revision, "d118719043905132d314611dcee9f0cac5f87868")
        with patch.object(engines, "_SOURCES", {**engines._SOURCES,
                                                engines.NATIVE_ENGINE_ID: ("native_engine.py",)}):
            self.assertNotEqual(engines.describe_engine(engines.NATIVE_ENGINE_ID).content_digest,
                                native.content_digest)

    def test_the_slot_is_catalogued_and_the_index_finds_nothing(self):
        from loop_engine.core.engines.slot_index import slot_index_report
        from loop_engine.core.engines.slots import load_engine_slot_catalog
        catalog = load_engine_slot_catalog()
        slot = next(item for item in catalog.slots if item.slot_id == "ontology_change_planning")
        self.assertEqual((slot.selection_mode, slot.engine_kinds), ("one_of", engines.ENGINE_KINDS))
        report = slot_index_report(catalog)
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["valid"])


if __name__ == "__main__":
    unittest.main()
