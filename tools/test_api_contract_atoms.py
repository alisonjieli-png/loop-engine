"""Offline contract atoms and crash-reconciled candidate output; no provider calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from supply_lines import api_contract_atoms as atoms
from supply_lines import api_contract_run as runs
from supply_lines import api_contract_sources as sources
from supply_lines.licences import RepositoryLicence
from supply_lines.records import read_supply_candidate

ROOT = Path(__file__).resolve().parents[1]
LICENSE = (ROOT / "LICENSE").read_bytes()
REVISION = "a" * 40


def document():
    return {"openapi": "3.0.3", "info": {"title": "Fixture", "version": "1"}, "paths": {
        "/widgets/{id}": {"parameters": [{"name": "id", "in": "path", "required": True,
                                           "schema": {"type": "integer", "minimum": 1}}],
            "get": {"operationId": "readWidget", "responses": {"200": {"content": {"application/json": {
                "schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}}}}},
            "post": {"operationId": "updateWidget", "requestBody": {"content": {"application/json": {
                "schema": {"type": "object", "properties": {"enabled": {"type": "boolean"}}, "required": ["enabled"]}}}},
                "responses": {"400": {"content": {"application/json": {
                    "schema": {"type": "object", "properties": {"error": {"type": "string"}}, "required": ["error"]}}}}}}}}}


def fixture_spec():
    doc = document()
    raw = atoms.json_bytes(doc)
    return {"document": doc, "repository": "fixture/api", "path": "openapi.json", "commit": REVISION,
            "bytes": raw, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
            "retrieved_at": "2026-10-05T00:00:00Z", "title": "Fixture API", "version": "1",
            "licence": RepositoryLicence("fixture/api", REVISION, "MIT", "agreed", "LICENSE", LICENSE,
                                         "MIT", "MIT", 1.0), "declared_licence": None, "notices": []}


class SchemaAtomTests(unittest.TestCase):
    def test_parameters_body_and_status_are_separate_real_jobs(self):
        found = list(atoms.atoms(document()))
        self.assertEqual([row["phase"] for row in found], ["parameters", "response:200", "parameters", "request", "response:400"])
        self.assertEqual(found[0]["schema"]["required"], ["path"])
        self.assertEqual(found[0]["schema"]["properties"]["path"]["required"], ["id"])
        self.assertEqual(found[4]["method"], "POST")

    def test_operation_overrides_only_same_location_and_name(self):
        doc = document()
        doc["paths"]["/widgets/{id}"]["get"]["parameters"] = [
            {"name": "id", "in": "path", "schema": {"type": "string"}},
            {"name": "id", "in": "query", "schema": {"type": "integer"}}]
        row = next(atoms.atoms(doc))
        self.assertEqual(row["schema"]["properties"]["path"]["properties"]["id"]["type"], "string")
        self.assertEqual(row["schema"]["properties"]["query"]["properties"]["id"]["type"], "integer")

    def test_local_ref_constraints_are_preserved_not_depth_truncated(self):
        doc = document()
        doc["components"] = {"schemas": {"ID": {"type": "integer", "minimum": 1, "exclusiveMinimum": True}}}
        result = atoms.normalize_schema({"$ref": "#/components/schemas/ID"}, doc)
        self.assertEqual(result, {"type": "integer", "exclusiveMinimum": 1})
        self.assertTrue(atoms.schema_check.errors(1, result))
        self.assertFalse(atoms.schema_check.errors(2, result))

    def test_cyclic_external_unknown_and_deep_constraints_are_not_silently_weakened(self):
        doc = document()
        doc["components"] = {"schemas": {"Loop": {"$ref": "#/components/schemas/Loop"}}}
        deep = {"type": "string"}
        for _ in range(atoms.MAXIMUM_DEPTH + 1):
            deep = {"type": "array", "items": deep}
        for schema in ({"$ref": "#/components/schemas/Loop"}, {"$ref": "https://example.invalid/schema"},
                       {"unknownConstraint": True}, deep):
            with self.subTest(schema_kind=list(schema)), self.assertRaises(ValueError):
                atoms.normalize_schema(schema, doc)

    def test_nullable_enum_keeps_enum_constraint(self):
        result = atoms.normalize_schema({"type": "string", "nullable": True, "enum": ["yes"]}, document())
        self.assertEqual(result["type"], ["null", "string"])
        self.assertTrue(atoms.schema_check.errors(None, result))

    def test_invalid_source_schema_is_a_bounded_finding_not_an_uncaught_exception(self):
        with self.assertRaisesRegex(ValueError, "invalid_json_schema"):
            atoms.normalize_schema({"type": "object", "required": ["name", "name"]}, document())

    def test_malformed_operation_structures_are_recorded(self):
        self.assertEqual(next(atoms.atoms({"paths": []}))["finding"], "paths_shape_unsupported")
        self.assertIn("finding", next(atoms.atoms({"paths": {"/test": None}})))
        self.assertIn("finding", next(atoms.atoms({"paths": {"/test": {"get": None}}})))

    def test_property_names_are_not_treated_as_annotations(self):
        value = {"type": "object", "properties": {"description": {"type": "integer"}, "title": {"type": "boolean"}}}
        result = atoms.normalize_schema(value, document())
        self.assertEqual(set(result["properties"]), {"description", "title"})
        self.assertNotEqual(atoms.semantic_digest(result), atoms.semantic_digest({"type": "object", "properties": {}}))

    def test_semantic_duplicates_ignore_labels_but_not_constraints(self):
        first = {"type": "integer", "minimum": 1, "title": "one", "x-source": "alpha"}
        second = {"type": "integer", "minimum": 1, "title": "two", "description": "other wording"}
        self.assertEqual(atoms.semantic_digest(first), atoms.semantic_digest(second))
        self.assertNotEqual(atoms.semantic_digest(first), atoms.semantic_digest({**second, "minimum": 2}))

    def test_commutative_schema_order_and_repeated_allof_do_not_inflate_count(self):
        a, b = {"type": "integer"}, {"minimum": 1}
        self.assertEqual(atoms.semantic_digest({"allOf": [a, b, a]}), atoms.semantic_digest({"allOf": [b, a]}))
        self.assertEqual(atoms.semantic_digest({"oneOf": [a, b]}), atoms.semantic_digest({"oneOf": [b, a]}))
        self.assertNotEqual(atoms.semantic_digest({"oneOf": [a, b, a]}), atoms.semantic_digest({"oneOf": [a, b]}))

    def test_non_discriminating_contract_stays_a_finding(self):
        with self.assertRaisesRegex(ValueError, "discriminating_cases_unavailable"):
            atoms.cases({}, {})

    def test_full_validator_and_shipped_validator_check_positive_and_wrong(self):
        schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
        examples = atoms.cases({}, schema)
        self.assertTrue(examples["valid"])
        self.assertTrue(examples["invalid"])
        self.assertTrue(all(not atoms.schema_check.errors(value, schema) for value in examples["valid"]))
        self.assertTrue(all(atoms.schema_check.errors(value, schema) for value in examples["invalid"]))


class CacheTests(unittest.TestCase):
    def test_integrity_and_cache_miss_never_fall_back_to_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "cache").mkdir()
            reader = atoms.CachedFacts(root)
            url = "https://example.invalid/facts"
            data = b"fixture"
            body, meta = reader._paths(url)
            body.parent.mkdir()
            body.write_bytes(data)
            meta.write_bytes(atoms.json_bytes({"url": url, "status": 200, "sha256": hashlib.sha256(data).hexdigest(),
                                              "retrieved_at": "2026-10-05T00:00:00Z", "size_bytes": len(data)}))
            with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("no network")):
                self.assertEqual(reader.get(url).body, data)
                body.write_bytes(b"changed")
                with self.assertRaises(LookupError):
                    reader.get(url)
                with self.assertRaises(LookupError):
                    reader.get(url + "/missing")
                self.assertEqual(reader.misses, [url + "/missing"])

    def test_symlinked_cache_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "actual").mkdir()
            (root / "cache").symlink_to(root / "actual", target_is_directory=True)
            with self.assertRaises(ValueError):
                atoms.CachedFacts(root)


class SourceAdapterTests(unittest.TestCase):
    def loaded(self, *, wrong_rights=False, missing_notice=False, limit=10, bytes_limit=1024*1024, wanted=None):
        spec = fixture_spec()
        raw = atoms.json_bytes({"swagger": "2.0", "info": {"title": "Fixture", "version": "1"},
            "host": "example.invalid", "schemes": ["https"], "paths": {"/things": {"get": {
                "operationId": "readThings", "responses": {"200": {"description": "A thing", "schema": {
                    "type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}}}}}})
        answer = atoms.Fetched("https://api.apis.guru/v2/specs/example.invalid/1/swagger.json", 200, raw,
                              hashlib.sha256(raw).hexdigest(), "2026-10-05T00:00:00Z", True)
        listing = {"example.invalid": {"preferred": "1", "versions": {"1": {"swaggerUrl": answer.url,
                   "updated": "2026-10-05", "info": {"title": "Fixture"}}}}}
        observation = atoms.Fetched("https://api.apis.guru/v2/list.json", 200, b"{}", hashlib.sha256(b"{}").hexdigest(),
                                   "2026-10-05T00:00:00Z", True)
        reader = SimpleNamespace(misses=[], get=lambda _url: answer)
        decision = {"decision": "licence_unknown" if wrong_rights else "agreed", "licence": spec["licence"],
                    "basis": sources.directory.ORIGIN_BASIS}
        def notice(*_args):
            if missing_notice:
                reader.misses.append("missing notice metadata")
            return None
        with patch.object(sources.directory, "read_directory", return_value=(listing, observation)), \
             patch.object(sources.directory, "decide", return_value=decision), \
             patch.object(sources, "repository_notice", side_effect=notice), \
             patch.object(sources, "read_sources", return_value=[]):
            return sources.load(reader, "apis-guru", wanted or ["example.invalid"],
                                maximum_specifications=limit, maximum_source_bytes=bytes_limit)

    def test_directory_preserves_native_origin_rights_and_converted_view(self):
        loaded, findings = self.loaded()
        self.assertEqual(findings, [])
        source, spec = loaded[0]
        self.assertEqual(source["source_id"], "example.invalid")
        self.assertEqual(spec["origin"], "apis_guru_directory")
        self.assertEqual(spec["licence_basis"], sources.directory.ORIGIN_BASIS)
        self.assertEqual(spec["pointer_basis"], "normalized_openapi_view")
        self.assertEqual(len(spec["normalized_view_sha256"]), 64)
        self.assertEqual(spec["extra_facts"][0]["role"], "registry_entry")
        self.assertTrue(spec["commit"].startswith("version:"))

    def test_rights_missing_notice_and_source_byte_limit_hold_instead_of_guess(self):
        for options, expected in (({"wrong_rights": True}, "licence_unknown"),
                                   ({"missing_notice": True}, "LookupError"),
                                   ({"bytes_limit": 1}, "declared_source_bound")):
            loaded, findings = self.loaded(**options)
            self.assertEqual(loaded, [])
            self.assertEqual(findings[0]["finding"], expected)

    def test_unknown_selector_is_not_silently_ignored_beside_a_known_one(self):
        with self.assertRaisesRegex(ValueError, "unknown_or_missing_source"):
            self.loaded(wanted=["example.invalid", "misspelled.invalid"])

    def test_directory_package_uses_directory_facts_not_a_forged_github_url(self):
        loaded, _ = self.loaded()
        _source, spec = loaded[0]
        atom = next(atoms.atoms(spec["document"]))
        schema = atoms.normalize_schema(atom["schema"], spec["document"])
        examples = atoms.cases(atom, schema)
        with tempfile.TemporaryDirectory() as temporary:
            payload, bodies = atoms.package(atom, schema, examples, spec, revision=REVISION,
                generated_on="2026-10-08", licence_text=LICENSE, staging=Path(temporary))
        self.assertEqual(payload["provenance"]["origin"], "apis_guru_directory")
        self.assertEqual(payload["provenance"]["facts"][0]["url"], spec["url"])
        row = next(row for row in payload["package"]["files"] if row["path"] == "contract.schema.json")
        bound = json.loads(bodies[row["digest"]])["x-baltor-contract"]
        self.assertEqual(bound["normalized_source_view_sha256"], spec["normalized_view_sha256"])
        self.assertEqual(bound["source_selection_basis"], "normalized_openapi_view")

    def test_inherited_parameters_and_referenced_objects_bind_resolvable_selection(self):
        spec = fixture_spec()
        doc = spec["document"]
        path_item = doc["paths"]["/widgets/{id}"]
        response = path_item["get"]["responses"]["200"]
        request = path_item["post"]["requestBody"]
        doc["components"] = {"pathItems": {"Widgets": path_item},
                             "responses": {"Widget": response}, "requestBodies": {"Widget": request}}
        path_item["get"]["responses"]["200"] = {"$ref": "#/components/responses/Widget"}
        path_item["post"]["requestBody"] = {"$ref": "#/components/requestBodies/Widget"}
        doc["paths"]["/widgets/{id}"] = {"$ref": "#/components/pathItems/Widgets"}
        found = list(atoms.atoms(doc))
        self.assertEqual([row["phase"] for row in found], ["parameters", "response:200", "parameters", "request", "response:400"])
        for atom in found:
            with tempfile.TemporaryDirectory() as temporary:
                schema = atoms.normalize_schema(atom["schema"], doc)
                payload, bodies = atoms.package(atom, schema, atoms.cases(atom, schema), spec, revision=REVISION,
                    generated_on="2026-10-08", licence_text=LICENSE, staging=Path(temporary))
            entry = next(row for row in payload["package"]["files"] if row["path"] == "contract.schema.json")
            metadata = json.loads(bodies[entry["digest"]])["x-baltor-contract"]
            self.assertEqual(metadata["record_type"], "api_operation_contract_atom/v2")
            self.assertNotIn("source_pointer", metadata)
            self.assertEqual(metadata["logical_selector"], atom["pointer"])
            self.assertEqual(metadata["source_selection"]["phase"], atom["phase"])
            for pointer in metadata["source_selection"]["pointers"]:
                self.assertEqual(atoms.Resolver(doc).target(pointer), {"$ref": "#/components/pathItems/Widgets"})
        with self.assertRaises(ValueError):
            atoms.Resolver(doc).target(found[0]["pointer"])

    def test_literal_percent_in_path_does_not_change_pointer_target(self):
        spec = fixture_spec()
        spec["document"]["paths"]["/literal/%2F"] = spec["document"]["paths"].pop("/widgets/{id}")
        atom = next(atoms.atoms(spec["document"]))
        schema = atoms.normalize_schema(atom["schema"], spec["document"])
        with tempfile.TemporaryDirectory() as temporary:
            payload, bodies = atoms.package(atom, schema, atoms.cases(atom, schema), spec, revision=REVISION,
                generated_on="2026-10-08", licence_text=LICENSE, staging=Path(temporary))
        entry = next(row for row in payload["package"]["files"] if row["path"] == "contract.schema.json")
        selection = json.loads(bodies[entry["digest"]])["x-baltor-contract"]["source_selection"]
        self.assertEqual(atoms.Resolver(spec["document"]).target(selection["pointers"][0]),
                         spec["document"]["paths"]["/literal/%2F"])


class RunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.args = SimpleNamespace(maximum_atoms=10, maximum_attempts=30, batch_size=2, maximum_seconds=30,
            maximum_candidate_bytes=64 * 1024 * 1024,
            source=["fixture"], cache_folder=self.root / "cache-input", run_folder=self.root / "run",
            authorize_output_writes=True)
        self.fake_reader = SimpleNamespace(misses=[], receipts={})
        self.spec = fixture_spec()
        self.patches = [patch.object(sources, "read_sources", return_value=[{"source_id": "fixture", "paths": ["openapi.json"]}]),
                        patch.object(sources, "read_specification", side_effect=lambda *_args: deepcopy(self.spec)),
                        patch.object(atoms, "CachedFacts", return_value=self.fake_reader)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def invoke(self, **changes):
        args = SimpleNamespace(**{**vars(self.args), **changes})
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("no network")):
            return runs.run(args, revision=REVISION, licence_text=LICENSE, generator_digest="b" * 64)

    def test_no_authority_only_plans_without_writing(self):
        result = self.invoke(authorize_output_writes=False)
        self.assertFalse(result["written"])
        self.assertFalse(self.args.run_folder.exists())

    def test_whole_batch_is_one_starting_practitioner_loop(self):
        from loop_engine import LoopLedger
        ledger = LoopLedger()
        result = runs.run_as_loop(self.args, revision=REVISION, licence_text=LICENSE,
                                  generator_digest="b" * 64, ledger=ledger)
        execution = result["loop_execution"]
        self.assertEqual((execution["relationship"], execution["role"], execution["mode"]),
                         ("starting", "practitioner", "deterministic"))
        self.assertEqual((execution["attempts"], execution["model_calls"]), (1, 0))
        self.assertIn("spawns_process", execution["effects"])
        self.assertFalse(execution["candidate_approval"])
        self.assertEqual(sum(row.get("event") == "init" for row in ledger.events), 1)
        self.assertEqual(len(list(self.args.run_folder.glob("loop-invocation-*.json"))), 1)

    def test_loop_refusal_is_not_retried_or_relabelled_success(self):
        from loop_engine import LoopLedger
        ledger = LoopLedger()
        marker = "private source excerpt must not enter error reports"
        self.args.run_folder.mkdir()
        with patch.object(runs, "run", side_effect=ValueError(marker)) as called:
            with self.assertRaises(Exception) as caught:
                runs.run_as_loop(self.args, revision=REVISION, licence_text=LICENSE,
                                  generator_digest="b" * 64, ledger=ledger)
        self.assertEqual(called.call_count, 1)
        steps = [row for row in ledger.events if row.get("event") == "run_step"]
        self.assertEqual(len(steps), 1)
        self.assertFalse(steps[0]["accepted"])
        self.assertEqual(steps[0]["accepted_successes"], 0)
        saved = json.loads(next(self.args.run_folder.glob("loop-invocation-*.json")).read_bytes())
        self.assertEqual(saved["failure_class"], "ValueError")
        self.assertTrue(saved["failed"])
        self.assertFalse(saved["batch_report_produced"])
        self.assertNotEqual(saved["loop_terminal_code"], "ACCEPTED")
        self.assertEqual(caught.exception.failure_class, "ValueError")
        self.assertNotIn(marker, str(caught.exception))
        self.assertNotIn(marker, json.dumps(saved))

    def test_batch_cancellation_is_not_converted_into_an_ordinary_failure(self):
        for error in (KeyboardInterrupt(), SystemExit(3)):
            with patch.object(runs, "run", side_effect=error) as called:
                with self.assertRaises(type(error)):
                    runs.run_as_loop(self.args, revision=REVISION, licence_text=LICENSE, generator_digest="b" * 64)
            self.assertEqual(called.call_count, 1)

    def test_loop_preview_keeps_effect_free_discovery(self):
        from loop_engine import LoopLedger
        ledger = LoopLedger()
        self.args.authorize_output_writes = False
        result = runs.run_as_loop(self.args, revision=REVISION, licence_text=LICENSE,
                                  generator_digest="b" * 64, ledger=ledger)
        self.assertFalse(result["written"])
        self.assertEqual(ledger.events, [])
        self.assertFalse(self.args.run_folder.exists())

    def test_byte_ceiling_stops_before_payload_or_cursor_write(self):
        result = self.invoke(maximum_candidate_bytes=1)
        self.assertTrue(result["stopped_by_candidate_byte_ceiling"])
        self.assertEqual(result["attempts_total"], 0)
        self.assertEqual(result["retained_and_candidate_bytes"], 0)
        self.assertFalse((self.args.run_folder / "packages").exists())
        self.assertEqual(result["enumerable_source_atoms"], 5)

    def test_resume_counts_only_new_candidates_and_retains_equivalent_atoms(self):
        first = self.invoke()
        self.assertEqual((first["attempts_total"], first["candidates"], first["package_tests_passed"]), (2, 2, 4))
        second = self.invoke(batch_size=30)
        self.assertEqual((second["attempts_total"], second["candidates"]), (5, 4))
        self.assertEqual(second["outcomes"]["reused_schema"], 1)
        self.assertEqual(len(list((self.args.run_folder / "retained").glob("*.json"))), 5)
        third = self.invoke(batch_size=30)
        self.assertEqual(third["new_candidates_this_invocation"], 0)
        self.assertEqual(third["attempts_this_invocation"], 0)
        self.assertFalse(third["approved"])
        self.assertFalse(third["published"])
        self.assertEqual(third["payload_file_placements"], 32)
        self.assertLess(third["distinct_payload_digests"], third["payload_file_placements"])

    def test_current_native_supply_reader_and_parent_binding(self):
        self.invoke()
        for path in (self.args.run_folder / "packages").glob("*/candidate.json"):
            payload = read_supply_candidate(json.loads(path.read_bytes()))
            self.assertEqual(payload["line"], "json_schemas")
            schema = json.loads((path.parent / "contract.schema.json").read_bytes())
            context = schema["x-baltor-contract"]
            self.assertEqual(context["source_revision"], REVISION)
            self.assertFalse(context["provider_behavior_tested"])
            self.assertEqual(len(context["parent_operation_key"]), 24)
            self.assertNotIn("network", payload["declared_effects"])

    def test_changed_source_or_limit_cannot_silently_resume(self):
        self.invoke()
        with self.assertRaisesRegex(ValueError, "resume_plan_changed"):
            self.invoke(maximum_atoms=20)
        self.spec["sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "resume_plan_changed"):
            self.invoke()

    def test_source_notice_cache_gap_is_retained_not_assumed_absent(self):
        def missing(*_args):
            self.fake_reader.misses.append("missing notice proof")
            return deepcopy(self.spec)
        with patch.object(sources, "read_specification", side_effect=missing):
            result = self.invoke()
        self.assertEqual(result["candidates"], 0)
        self.assertIn("cache_incomplete", result["source_findings"][0]["reason"])

    def test_corrupted_written_payload_refuses_resume(self):
        self.invoke()
        file = next((self.args.run_folder / "packages").glob("*/contract.schema.json"))
        file.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "candidate_file_changed"):
            self.invoke()

    def test_partial_journal_is_not_blindly_replayed(self):
        self.invoke()
        path = self.args.run_folder / "events.jsonl"
        with path.open("ab") as stream:
            stream.write(b'{"partial":')
        with self.assertRaisesRegex(ValueError, "partial_journal_needs_reconciliation"):
            self.invoke()

    def test_last_event_cannot_relabel_a_candidate_or_lower_byte_accounting(self):
        first = self.invoke(batch_size=30)
        self.assertEqual(first["candidates"], 4)
        journal = self.args.run_folder / "events.jsonl"
        rows = [json.loads(line) for line in journal.read_bytes().splitlines()]
        original = deepcopy(rows[-1])
        for changes in ({"outcome": "retained_finding", "retained_and_candidate_bytes": 0},
                        {"retained_and_candidate_bytes": 0}, {"unexpected": True}):
            with self.subTest(changes=changes):
                rows[-1] = {**original, **changes}
                journal.write_text("".join(json.dumps(row) + "\n" for row in rows))
                with self.assertRaisesRegex(ValueError, "journal_retained_event_accounting_mismatch"):
                    self.invoke(batch_size=30)
        rows[-1] = original
        journal.write_text("".join(json.dumps(row) + "\n" for row in rows))
        self.assertEqual(self.invoke(batch_size=30)["new_candidates_this_invocation"], 0)

    def test_retained_atom_source_remains_bound_to_exact_plan_position(self):
        self.invoke(batch_size=1)
        journal = self.args.run_folder / "events.jsonl"
        event = json.loads(journal.read_bytes())
        path = self.args.run_folder / event["record_path"]
        retained = json.loads(path.read_bytes())
        retained["source"]["sha256"] = "a" * 64
        raw = atoms.json_bytes(retained)
        path.write_bytes(raw)
        event["record_sha256"] = hashlib.sha256(raw).hexdigest()
        journal.write_text(json.dumps(event) + "\n")
        with self.assertRaisesRegex(ValueError, "retained_atom_source_binding_changed"):
            self.invoke()

    def test_atomic_staging_and_unlisted_output_aliases_refuse_before_generation(self):
        for suffix in ("staging", "packages", "retained", "unlisted/nested"):
            with self.subTest(suffix=suffix):
                run_folder = self.root / ("refused-" + suffix.replace("/", "-"))
                external = self.root / ("outside-" + suffix.replace("/", "-"))
                external.mkdir()
                (external / "unchanged").write_bytes(b"sentinel")
                link = run_folder / suffix
                link.parent.mkdir(parents=True)
                link.symlink_to(external, target_is_directory=True)
                with patch.object(atoms, "package") as package:
                    with self.assertRaisesRegex(ValueError, "run_path_must_not_follow_symlinks"):
                        self.invoke(run_folder=run_folder)
                    package.assert_not_called()
                self.assertEqual([(path.name, path.read_bytes()) for path in external.iterdir()], [("unchanged", b"sentinel")])

    def test_prior_atomic_event_version_is_not_silently_migrated(self):
        self.invoke(batch_size=1)
        journal = self.args.run_folder / "events.jsonl"
        event = json.loads(journal.read_bytes())
        event["record_type"] = "api_contract_supply_event/v1"
        raw = json.dumps(event).encode() + b"\n"
        journal.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "journal_chain_mismatch"):
            self.invoke()
        self.assertEqual(journal.read_bytes(), raw)

    def test_journal_cannot_redirect_a_retained_read(self):
        self.invoke()
        path = self.args.run_folder / "events.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["record_path"] = "/etc/passwd"
        path.write_text(json.dumps(rows[0]) + "\n")
        with self.assertRaisesRegex(ValueError, "journal_chain_mismatch"):
            self.invoke()

    def test_interruption_after_payload_before_journal_reconciles_exact_bytes(self):
        original = runs._append
        with patch.object(runs, "_append", side_effect=RuntimeError("simulated interruption")):
            with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                self.invoke()
        self.assertEqual(len(list((self.args.run_folder / "packages").iterdir())), 1)
        with patch.object(runs, "_append", side_effect=original):
            result = self.invoke()
        self.assertEqual(result["candidates"], 2)
        self.assertEqual(result["attempts_total"], 2)

    def test_imperfect_atoms_are_retained_with_diagnostics(self):
        self.spec["document"]["paths"]["/widgets/{id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] = {}
        result = self.invoke()
        self.assertEqual(result["outcomes"], {"candidate": 1, "retained_finding": 1})
        retained = json.loads((self.args.run_folder / "retained/00000001.json").read_bytes())
        self.assertIn("diagnostic", retained)
        self.assertEqual(retained["normalized_schema"], {})


if __name__ == "__main__":
    unittest.main()
