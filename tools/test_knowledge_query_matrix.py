"""Offline conformance and wrong controls for research queries, not admission."""
from __future__ import annotations

import json
import itertools
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest import mock

from loop_engine.core.library_ingestion.processes import CommandResult
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog
from knowledge_radar.community_store import CommunityStore
from knowledge_radar.engines_network import RadarNetwork
from knowledge_radar.query_matrix import (
    MATRIX, GATES, cursor_for, default_matrix, page, query_at, read_countries, read_matrix,
)
from knowledge_radar.query_runs import plan_into_store, query_identity, read_query, tick
from knowledge_radar.records import read_contracts

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = read_contracts(json.loads((ROOT / "tools/knowledge_radar/source-contracts-v1.json").read_bytes()))
NOW = "2026-10-01T12:00:00Z"


def small(engine="github_search", values=None):
    return {"record_type": MATRIX, "revision": "test.1", "vocabulary": {"task": values or ["water", "transit", "schema"]},
            "routes": [{"id": "implementation", "engine": engine, "dimensions": ["task"], "purpose": "Find public implementation references; qualification remains pending."}],
            "provenance": ["synthetic fixture; not observed research"]}


def github_result(status=200, *, items=None, partial=False):
    body = {"incomplete_results": partial, "items": [] if items is None else items}
    return CommandResult(0, (f"HTTP/2.0 {status}\ncontent-type: application/json\nx-ratelimit-remaining: 20\n\n" + json.dumps(body)).encode(), "", 3.0, False, False)


ITEM = {"full_name": "example/tool", "html_url": "https://github.com/example/tool", "license": {"spdx_id": "MIT"},
        "description": "DO NOT RETAIN THIS PROSE", "private": False, "archived": False,
        "pushed_at": "2026-09-30T12:00:00Z", "created_at": "2020-01-01T00:00:00Z"}


class MatrixTests(unittest.TestCase):
    def test_bound_matrix_and_contracts_are_defensive_and_deeply_immutable(self):
        document, contracts = small(), dict(CONTRACTS)
        matrix = read_matrix(document, contracts)
        before = page(matrix)
        document["vocabulary"]["task"][0] = "changed outside bound plan"
        contracts["github_search"] = replace(contracts["github_search"], parser_version="0.9.9")
        self.assertEqual(before, page(matrix))
        for mutation in (
            lambda: matrix.document["vocabulary"]["task"].__setitem__(0, "changed"),
            lambda: matrix.contracts.__setitem__("github_search", contracts["github_search"]),
        ):
            with self.assertRaises((TypeError, AttributeError)):
                mutation()

    def test_public_vocabulary_guard_refuses_obvious_sensitive_markers(self):
        from knowledge_radar.query_matrix import words
        for term in ("synthetic-person@example.invalid", "ghp_" + "NOTAREALSECRETFIXTURE" * 2,
                     "github_pat_" + "NOTAREALSECRETFIXTURE" * 2, "/home/example/.ssh/id_rsa",
                     ".aws/credentials", "internal confidential project findings", "AKIA" + "A" * 16):
            with self.subTest(marker=term.split("_")[0]), self.assertRaises(ValueError):
                read_matrix(small(values=[term]), CONTRACTS)
        for term in ("confidential computing", "secret management", "email address validation", "JSON/XML normalization"):
            self.assertTrue(words(term))

    def test_foreign_route_facet_value_and_purpose_are_not_authorized_by_rehashing(self):
        matrix = read_matrix(small(), CONTRACTS)
        row = page(matrix)["queries"][0]
        for field, value in (("route", "absent"), ("engine", "curated_seed"), ("purpose", "changed purpose"),
                             ("facets", {"absent_axis": "water"}), ("facets", {"task": "absent value"}),
                             ("plan_digest", "0" * 64)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                read_query({**row, field: value}, matrix)

    def test_default_reuses_existing_methods_and_exposes_pilot_scope(self):
        document = default_matrix(ROOT)
        matrix = read_matrix(document, CONTRACTS)
        self.assertGreater(matrix.raw_combinations, 1000000)
        self.assertEqual(len(document["vocabulary"]["sdg_target"]), 17)
        self.assertTrue(any("pilot" in row for row in document["provenance"]))
        self.assertIn("MCP server", document["vocabulary"]["source_type"])
        self.assertIn("parameterized function", document["vocabulary"]["artifact_form"])

    def test_every_small_combination_once_with_resumable_cursor(self):
        document = small()
        document["vocabulary"]["country_area"] = ["a", "b", "c", "d"]
        document["routes"][0]["dimensions"].append("country_area")
        matrix = read_matrix(document, CONTRACTS)
        cursor, all_rows = None, []
        while True:
            output = page(matrix, cursor, limit=2)
            all_rows += output["queries"]
            cursor = output["next_cursor"]
            if output["complete"]:
                break
        self.assertEqual(len(all_rows), 12)
        self.assertEqual(len({row["query_id"] for row in all_rows}), 12)
        oracle = {(task, area) for task in document["vocabulary"]["task"] for area in document["vocabulary"]["country_area"]}
        self.assertEqual({(row["facets"]["task"], row["facets"]["country_area"]) for row in all_rows}, oracle)

    def test_dispersed_traversal_matches_independent_product_oracle(self):
        for sizes in ((1, 1), (2, 3), (3, 4, 5), (4, 6, 7, 2), (5, 5, 5)):
            document = small()
            vocabulary = {"axis" + str(axis): [f"axis{axis} value{item}" for item in range(size)] for axis, size in enumerate(sizes)}
            document["vocabulary"] = vocabulary
            document["routes"][0]["dimensions"] = list(vocabulary)
            matrix = read_matrix(document, CONTRACTS)
            actual = [tuple(query_at(matrix, 0, index)[0]["facets"].values()) for index in range(matrix.raw_combinations)]
            oracle = set(itertools.product(*vocabulary.values()))
            self.assertEqual(set(actual), oracle)
            self.assertEqual(len(actual), len(oracle))

    def test_order_rotates_geography_industry_goal_audience_and_sources(self):
        matrix = read_matrix(default_matrix(ROOT), CONTRACTS)
        rows, cursor = [], None
        for _ in range(5):
            result = page(matrix, cursor, limit=20)
            rows.extend(result["queries"])
            cursor = result["next_cursor"]
        for dimension in ("country_area", "industry", "sdg_target", "audience"):
            self.assertGreater(len({row["facets"][dimension] for row in rows if dimension in row["facets"]}), 5, dimension)
        self.assertEqual(len({row["route"] for row in rows}), 7)

    def test_normalized_query_identity_ignores_labels_and_applicability_order(self):
        document = small(values=["WATER   meter"])
        one = page(read_matrix(document, CONTRACTS))["queries"][0]
        document["revision"] = "test.2"
        document["routes"][0]["id"] = "renamed"
        document["vocabulary"]["task"] = ["water meter"]
        two = page(read_matrix(document, CONTRACTS))["queries"][0]
        self.assertEqual(one["query_id"], two["query_id"])
        self.assertEqual(one["work_id"], two["work_id"])
        self.assertNotEqual(one["plan_digest"], two["plan_digest"])

    def test_alias_routes_dedup_before_planned_count(self):
        document = small()
        document["routes"].append({**document["routes"][0], "id": "another"})
        result = page(read_matrix(document, CONTRACTS), limit=20)
        self.assertEqual(result["counts"]["queries_planned"], 3)
        self.assertEqual(result["counts"]["duplicates"], 3)
        self.assertTrue(result["complete"])

    def test_scan_limit_makes_duplicate_heavy_work_bounded(self):
        result = page(read_matrix(small(), CONTRACTS), seen=lambda identity: True, scan_limit=2)
        self.assertEqual(result["counts"]["combinations_examined"], 2)
        self.assertEqual(result["queries"], [])
        self.assertFalse(result["complete"])

    def test_changed_vocabulary_contract_and_compiler_bind_cursor(self):
        matrix = read_matrix(small(), CONTRACTS)
        cursor = cursor_for(matrix)
        changed = small(values=["other"])
        altered_contracts = {**CONTRACTS, "github_search": replace(CONTRACTS["github_search"], maximum_requests_per_run=1)}
        for other in (read_matrix(changed, CONTRACTS), read_matrix(small(), altered_contracts)):
            with self.assertRaisesRegex(ValueError, "cursor_binding"):
                page(other, cursor)

    def test_invalid_cursor_fields_and_bounds_refused(self):
        matrix = read_matrix(small(), CONTRACTS)
        for changes in ({"next_route": True}, {"positions": [-1]}, {"positions": [4]}, {"positions": [0, 0]}, {"extra": 1}, {"record_type": "old/v0"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                page(matrix, {**cursor_for(matrix), **changes})

    def test_invalid_schema_and_query_operator_injection_refused(self):
        cases = []
        for term in ('water" is:private', "path:secret", "water\nsecret", "a\u200bb", "", "x" * 101):
            cases.append(small(values=[term]))
        duplicate = small(values=["water", " WATER "])
        cases.append(duplicate)
        for field, value in (("engine", []), ("engine", "unregistered"), ("dimensions", ["missing"])):
            wrong = small()
            wrong["routes"][0][field] = value
            cases.append(wrong)
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                read_matrix(case, CONTRACTS)

    def test_known_incompatible_method_not_counted_as_query(self):
        document = small(values=["inversion"])
        document["vocabulary"]["data_type"] = ["text"]
        document["routes"][0]["dimensions"].append("data_type")
        result = page(read_matrix(document, CONTRACTS))
        self.assertEqual(result["queries"], [])
        self.assertEqual(result["counts"]["excluded"], {"incompatible_method": 1})

    def test_multibyte_query_is_bounded_before_transport(self):
        document = small(values=["山" * 90])
        document["vocabulary"]["audience"] = ["水" * 90]
        document["routes"][0]["dimensions"].append("audience")
        result = page(read_matrix(document, CONTRACTS))
        self.assertEqual(result["queries"], [])
        self.assertEqual(result["counts"]["excluded"], {"query_transport_length": 1})

    def test_huge_factorized_space_does_not_materialize_product(self):
        document = small()
        document["vocabulary"] = {"dimension_" + str(index): ["value " + str(item) for item in range(100)] for index in range(8)}
        document["routes"][0]["dimensions"] = list(document["vocabulary"])
        matrix = read_matrix(document, CONTRACTS)
        self.assertEqual(matrix.raw_combinations, 100 ** 8)
        result = page(matrix, limit=2, scan_limit=3)
        self.assertLessEqual(result["counts"]["combinations_examined"], 3)
        self.assertEqual(len(result["queries"]), 2)

    def test_deferred_route_does_not_claim_an_installed_web_search(self):
        row = page(read_matrix(small(engine=""), CONTRACTS))["queries"][0]
        self.assertEqual(row["dispatch"], "deferred_adapter")
        self.assertIsNone(row["source_contract_digest"])
        self.assertEqual(row["gates"], GATES)

    def test_read_query_refuses_public_only_removal_and_fake_approval(self):
        matrix = read_matrix(small(), CONTRACTS)
        row = page(matrix)["queries"][0]
        for wrong in ({**row, "query": row["query"].replace("is:public", "is:private")},
                      {**row, "gates": {**GATES, "publication": "approved"}},
                      {**row, "source_contract_digest": "0" * 64}):
            with self.assertRaises(ValueError):
                read_query(wrong, matrix)

    def test_country_inventory_requires_unique_codes_exact_source_and_scope(self):
        record = {"record_type": "knowledge_radar_country_inventory/v1", "source_url": "https://example.org/source",
                  "source_sha256": "a" * 64, "observed_on": "2026-10-01", "rights_basis": "Synthetic fixture",
                  "coverage": "pilot_subset", "entries": [{"m49": "004", "name": "Fixture Area"}]}
        self.assertEqual(read_countries(record), record)
        self.assertEqual(default_matrix(ROOT, record)["vocabulary"]["country_area"], ["Fixture Area"])
        for changes in ({"source_sha256": "unpinned"}, {"observed_on": "2026-99-99"}, {"entries": record["entries"] * 2}, {"coverage": "all_countries_certified"}):
            with self.assertRaises(ValueError):
                read_countries({**record, **changes})


class ManagedQueryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / "state"
        self.matrix = read_matrix(small(), CONTRACTS)

    def network(self, maximum=3, per_source=3):
        contracts = {**CONTRACTS, "github_search": replace(CONTRACTS["github_search"], maximum_requests_per_run=per_source)}
        return RadarNetwork(RequestBudget(maximum, maximum_pause_seconds=0, reserve=0), RequestLog(), contracts, sleep=lambda _: None)

    def run_reads(self, answers, **options):
        network = options.pop("network", self.network())
        with mock.patch("knowledge_radar.engines_network.run_command", side_effect=answers) as calls:
            result = tick(self.matrix, ROOT, self.state, writes_allowed=True, network_allowed=True, execute=True,
                          page_size=3, maximum_queries=3, maximum_requests=3, per_source=3, network=network, now=NOW, **options)
        return result, calls, network

    def test_preview_has_no_files_network_or_claimed_execution(self):
        with mock.patch("knowledge_radar.engines_network.run_command", side_effect=AssertionError("network")):
            result = tick(self.matrix, ROOT, self.state)
        self.assertFalse(self.state.exists())
        self.assertTrue(result["preview"])
        self.assertIsNone(result["execution"])
        self.assertEqual(result["page"]["counts"]["queries_executed"], 0)

    def test_execution_requires_both_separate_authorities(self):
        for options in ({}, {"writes_allowed": True}, {"network_allowed": True}):
            with self.assertRaises(PermissionError):
                tick(self.matrix, ROOT, self.state, execute=True, **options)
        self.assertFalse(self.state.exists())

    def test_exact_queue_dedup_and_cursor_resume_use_managed_store(self):
        first = tick(self.matrix, ROOT, self.state, writes_allowed=True, page_size=1)
        second = tick(self.matrix, ROOT, self.state, writes_allowed=True, page_size=1)
        self.assertEqual(second["plan_totals"]["queries_planned"], 2)
        self.assertNotEqual(first["page"]["queries"][0]["query_id"], second["page"]["queries"][0]["query_id"])
        store = CommunityStore(self.state)
        self.assertEqual(len(store.query(kind="source", state="queued")), 2)
        self.assertEqual(store.query(kind="lead"), [])
        self.assertFalse((self.state / "scheduler.sqlite").exists())

    def test_page_write_ahead_survives_mid_materialization_crash(self):
        store = CommunityStore(self.state, writes_allowed=True)
        real_put = store.put
        written = []

        def fail_second(identity, *args, **kwargs):
            if identity.startswith("community.query.work."):
                written.append(identity)
                if len(written) == 2:
                    raise RuntimeError("synthetic crash")
            return real_put(identity, *args, **kwargs)

        with mock.patch.object(store, "put", fail_second), self.assertRaises(RuntimeError):
            plan_into_store(store, self.matrix, limit=3)
        output, totals = plan_into_store(store, self.matrix, limit=3)
        self.assertEqual(totals["queries_planned"], 3)
        self.assertEqual(len(store.query(kind="source", state="queued")), 3)
        self.assertTrue(output["complete"])

    def test_origin_dedup_empty_and_partial_are_separate_not_rights_approval(self):
        result, calls, network = self.run_reads([github_result(items=[ITEM]), github_result(items=[ITEM], partial=True), github_result()])
        counts = result["execution"]["counts"]
        self.assertEqual(calls.call_count, 3)
        self.assertEqual(network.budget.used, 3)
        self.assertEqual(counts["queries_executed"], 3)
        self.assertEqual(counts["physical_requests_reserved"], 3)
        self.assertEqual(counts["request_records"], 3)
        self.assertEqual(counts["new_origins"], 1)
        self.assertEqual(counts["duplicate_origins"], 1)
        self.assertEqual(counts["empty_queries"], 1)
        self.assertEqual(counts["partial_queries"], 1)
        store = CommunityStore(self.state)
        origins = store.query(kind="source", state="needs_research")
        self.assertEqual(origins[0]["document"]["data"]["gates"], GATES)
        self.assertNotIn("DO NOT RETAIN", json.dumps(origins))
        self.assertEqual(store.query(kind="research_brief"), [])
        self.assertEqual(counts["files_published"], 0)
        again, second_calls, _ = self.run_reads([])
        self.assertEqual(second_calls.call_count, 0)
        self.assertEqual(again["execution"]["counts"]["queries_executed"], 0)

    def test_physical_ceiling_and_per_source_ceiling_refuse_extra_dispatch(self):
        for maximum, source, expected in ((1, 3, 1), (3, 1, 1)):
            with self.subTest(maximum=maximum, source=source), tempfile.TemporaryDirectory() as directory:
                self.state = Path(directory) / "state"
                network = self.network(maximum, source)
                result, calls, _ = self.run_reads([github_result()] * 3, network=network)
                self.assertEqual(calls.call_count, expected)
                self.assertEqual(result["execution"]["counts"]["queries_executed"], expected)

    def test_failure_is_not_empty_success_or_automatically_retried(self):
        result, calls, _ = self.run_reads([github_result(500)] * 3)
        counts = result["execution"]["counts"]
        self.assertEqual(counts["failed_queries"], 3)
        self.assertEqual(counts["empty_queries"], 0)
        again, repeated, _ = self.run_reads([])
        self.assertEqual(repeated.call_count, 0)
        self.assertEqual(again["execution"]["counts"]["queries_executed"], 0)

    def test_access_and_rate_refusals_hold_source_across_runs(self):
        for status in (401, 403, 404, 410, 429):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                self.state = Path(directory) / "state"
                result, calls, _ = self.run_reads([github_result(status)])
                self.assertEqual(calls.call_count, 1)
                self.assertEqual(result["execution"]["held_sources"], ["github_search"])
                again, repeated, _ = self.run_reads([])
                self.assertEqual(repeated.call_count, 0)
                self.assertEqual(again["execution"]["held_sources"], ["github_search"])

    def test_unlogged_transport_exception_preserves_unknown_request_outcome(self):
        result, calls, _ = self.run_reads([RuntimeError("synthetic transport failure")] * 3)
        self.assertEqual(calls.call_count, 3)
        self.assertEqual(result["execution"]["counts"]["unknown_request_outcomes"], 3)
        self.assertEqual(result["execution"]["counts"]["empty_queries"], 0)

    def test_interrupted_external_read_stays_reserved_and_is_not_repeated(self):
        with self.assertRaises(KeyboardInterrupt):
            self.run_reads([KeyboardInterrupt()])
        store = CommunityStore(self.state)
        works = [row for row in store.query(kind="source", state="recorded") if row["document"]["data"].get("outcome") == "reserved_unknown_outcome"]
        self.assertEqual(len(works), 1)
        result, calls, _ = self.run_reads([github_result(), github_result()])
        self.assertEqual(calls.call_count, 2)
        self.assertEqual(len(store.query(kind="run", state="recorded")), 1)

    def test_symlink_state_and_contract_widening_refused(self):
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        self.state.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            tick(self.matrix, ROOT, self.state, writes_allowed=True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_wrong_source_contract_cannot_change_host(self):
        network = self.network()
        network.contracts["github_search"] = replace(network.contracts["github_search"], hosts=("private.example",))
        with mock.patch("knowledge_radar.engines_network.run_command") as calls, self.assertRaisesRegex(ValueError, "source_contract_binding"):
            self.run_reads([], network=network)
        self.assertEqual(calls.call_count, 0)

    def test_stale_queued_contract_is_deferred_before_network(self):
        tick(self.matrix, ROOT, self.state, writes_allowed=True, page_size=3)
        store = CommunityStore(self.state, writes_allowed=True)
        for row in store.query(kind="source", state="queued"):
            data = deepcopy(row["document"]["data"])
            data["query"]["source_contract_digest"] = "0" * 64
            store.put(row["identity"], "source", "query_planner", "queued", data, expected=row)
        network = self.network()
        with mock.patch("knowledge_radar.engines_network.run_command", return_value=github_result()) as calls:
            from knowledge_radar.query_runs import execute_queued
            result = execute_queued(CommunityStore(self.state, writes_allowed=True), self.matrix, ROOT, network)
        self.assertEqual(calls.call_count, 0)
        self.assertEqual(result["counts"]["binding_refusals"], 3)

    def test_execution_does_not_drain_another_plan_in_shared_store(self):
        tick(self.matrix, ROOT, self.state, writes_allowed=True, page_size=3)
        other = read_matrix(small(values=["new task"]), CONTRACTS)
        network = self.network()
        with mock.patch("knowledge_radar.engines_network.run_command", return_value=github_result()) as calls:
            result = tick(other, ROOT, self.state, writes_allowed=True, network_allowed=True, execute=True,
                          maximum_requests=3, per_source=3, network=network, now=NOW)
        self.assertEqual(calls.call_count, 1)
        self.assertEqual(result["execution"]["counts"]["other_plan_pending"], 3)

    def test_valid_query_in_wrong_record_cannot_dispatch(self):
        store = CommunityStore(self.state, writes_allowed=True)
        query = page(self.matrix)["queries"][0]
        store.put("community.query.work." + "0" * 64, "source", "query_planner", "queued",
                  {"record_type": "knowledge_radar_query_work/v1", "query": query, "attempt_id": None, "outcome": "planned"})
        from knowledge_radar.query_runs import execute_queued
        with mock.patch("knowledge_radar.engines_network.run_command") as calls:
            result = execute_queued(store, self.matrix, ROOT, self.network(), per_source=3, now=NOW)
        self.assertEqual(calls.call_count, 0)
        self.assertEqual(result["counts"]["binding_refusals"], 1)

    def test_recovery_journal_tampering_refused_before_enqueue(self):
        from knowledge_radar.query_matrix import digest
        from knowledge_radar.query_runs import JOURNAL
        for corruption in ("purpose", "next_cursor", "counts", "limits"):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as directory:
                store = CommunityStore(Path(directory) / "state", writes_allowed=True)
                held = page(self.matrix)
                if corruption == "purpose":
                    held["queries"][0]["purpose"] = "not the authorized purpose"
                elif corruption == "next_cursor":
                    held["next_cursor"]["positions"] = [0]
                elif corruption == "counts":
                    held["counts"]["queries_planned"] += 1
                else:
                    held["limits"]["scan_limit"] = 999
                store.put("community.query.page." + digest(cursor_for(self.matrix)), "run", "query_planner", "recorded",
                          {"record_type": JOURNAL, "page": held})
                with self.assertRaises(ValueError):
                    plan_into_store(store, self.matrix)
                self.assertEqual(store.query(kind="source", state="queued"), [])

    def test_engine_version_mismatch_refused_before_request_reservation(self):
        from knowledge_radar.engines_network import GitHubSearch
        with mock.patch.object(GitHubSearch, "engine_version", "9.9.9"), self.assertRaisesRegex(ValueError, "engine_version_binding"):
            self.run_reads([])

    def test_unknown_and_access_holds_survive_parser_change(self):
        from knowledge_radar.engines_network import GitHubSearch
        for failure in ("interrupt", "unlogged", "403"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                state = Path(directory) / "state"
                old_contracts = {**CONTRACTS, "github_search": replace(CONTRACTS["github_search"], parser_version="0.9.9", maximum_requests_per_run=1)}
                old = read_matrix(small(values=["water"]), old_contracts)
                old_network = RadarNetwork(RequestBudget(1, reserve=0), RequestLog(), old_contracts, sleep=lambda _: None)
                effect = KeyboardInterrupt() if failure == "interrupt" else RuntimeError("synthetic") if failure == "unlogged" else github_result(403)
                with mock.patch.object(GitHubSearch, "engine_version", "0.9.9"), mock.patch("knowledge_radar.engines_network.run_command", side_effect=[effect]):
                    try:
                        tick(old, ROOT, state, writes_allowed=True, network_allowed=True, execute=True,
                             maximum_requests=1, per_source=1, network=old_network, now=NOW)
                    except KeyboardInterrupt:
                        pass
                new = read_matrix(small(values=["water"]), CONTRACTS)
                with mock.patch("knowledge_radar.engines_network.run_command", return_value=github_result()) as calls:
                    result = tick(new, ROOT, state, writes_allowed=True, network_allowed=True, execute=True,
                                  maximum_requests=1, per_source=1, network=self.network(1, 1), now=NOW)
                self.assertEqual(calls.call_count, 0)
                self.assertTrue(result["execution"]["held_sources"] or result["execution"]["held_queries"])

    def test_saved_access_refusal_holds_other_query_after_crash_before_source_hold(self):
        original_put = CommunityStore.put

        def interrupt_source_hold(store, identity, kind, source_id, state, data, **kwargs):
            if data.get("record_type") == "knowledge_radar_query_source_hold/v1":
                raise KeyboardInterrupt()
            return original_put(store, identity, kind, source_id, state, data, **kwargs)

        with mock.patch.object(CommunityStore, "put", interrupt_source_hold), self.assertRaises(KeyboardInterrupt):
            self.run_reads([github_result(403)])
        other = read_matrix(small(values=["different public query"]), CONTRACTS)
        with mock.patch("knowledge_radar.engines_network.run_command", return_value=github_result()) as calls:
            result = tick(other, ROOT, self.state, writes_allowed=True, network_allowed=True, execute=True,
                          maximum_requests=1, per_source=1, network=self.network(1, 1), now=NOW)
        self.assertEqual(calls.call_count, 0)
        self.assertEqual(result["execution"]["held_sources"], ["github_search"])

    def test_unsupported_sources_stay_deferred_without_request(self):
        self.matrix = read_matrix(small(engine=""), CONTRACTS)
        result, calls, _ = self.run_reads([])
        self.assertEqual(calls.call_count, 0)
        self.assertEqual(result["execution"]["counts"]["queries_executed"], 0)
        self.assertEqual(len(CommunityStore(self.state).query(kind="source", state="deferred")), 3)


if __name__ == "__main__":
    unittest.main()
