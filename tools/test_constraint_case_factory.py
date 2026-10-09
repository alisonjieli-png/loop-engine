"""Isolated cases, complete closures, native duplicate ownership and restart controls."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from loop_engine import LoopLedger
from component_qualification import checks, qualify
from component_qualification.components import ComponentReadError, from_folder
from supply_lines import api_contract_atoms as atoms, api_contract_run as atomic
from supply_lines import constraint_case_construction as construction
from supply_lines import constraint_case_packages as packages
from supply_lines import constraint_case_run as runner
from supply_lines import constraint_case_runtime as runtime
from test_api_contract_atoms import fixture_spec, LICENSE

ROOT = Path(__file__).resolve().parents[1]
REVISION = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
SCHEMA = {"type": "object", "properties": {"count": {"type": "integer", "minimum": 1, "maximum": 3},
    "name": {"type": "string", "minLength": 1, "maxLength": 3}, "mode": {"enum": ["a", "b"]},
    "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3, "uniqueItems": True}},
    "required": ["count", "name", "mode", "tags"], "additionalProperties": False}
BASELINE = {"count": 2, "name": "ok", "mode": "a", "tags": ["x"]}


def parent_run(root, schema=SCHEMA, baseline=BASELINE, baselines=None):
    spec = fixture_spec()
    spec["document"]["paths"] = {"/fixture": {"post": {"operationId": "fixture", "requestBody": {"content": {
        "application/json": {"schema": schema, "example": baseline}}}, "responses": {}}}}
    atom = next(atoms.atoms(spec["document"]))
    schema = atoms.normalize_schema(atom["schema"], spec["document"])
    with tempfile.TemporaryDirectory() as staging:
        examples = atoms.cases(atom, schema)
        if baselines is not None:
            examples["valid"] = baselines
        payload, bodies = atoms.package(atom, schema, examples, spec, revision=REVISION,
                                        generated_on="2026-10-08", licence_text=LICENSE, staging=Path(staging))
    folder = root / "parent"
    folder.mkdir()
    (folder / "run.json").write_bytes(runtime.encode({"plan": {"record_type": atomic.PLAN_TYPE, "generator_revision": REVISION}}))
    atomic._materialize(folder / "packages" / payload["record_id"], payload, bodies)
    return folder, from_folder(folder / "packages" / payload["record_id"])


class ConstructionTests(unittest.TestCase):
    def setUp(self):
        self.schema_bytes = runtime.encode(SCHEMA)
        self.cases, self.baselines, self.report = construction.construct(self.schema_bytes, [BASELINE])
        self.payloads = {"contract.schema.json": self.schema_bytes, **self.baselines}

    def test_every_case_has_positive_replay_and_exact_independent_error(self):
        self.assertGreater(len(self.cases), 10)
        for case in self.cases:
            result = runtime.replay(case, self.payloads, independent=True)
            self.assertTrue(result["baseline_valid"] and result["isolated_violation"])
            self.assertTrue(result["independent_oracle_checked"])
        self.assertEqual(len({row["job_id"] for row in self.cases}), len(self.cases))

    def test_wrong_error_path_cannot_pass_because_both_checkers_reject_something(self):
        case = deepcopy(self.cases[0])
        case["expected"]["instance_path"] = ["wrong"]
        with self.assertRaises(ValueError):
            runtime.replay(case, self.payloads, independent=True)
        case = deepcopy(self.cases[0])
        case["expected"]["shipped_path"] = "$.__wrong__"
        with self.assertRaises(ValueError):
            runtime.replay(case, self.payloads, independent=True)

    def test_multiple_violations_are_not_an_isolated_case(self):
        schema = {"type": "object", "properties": {"x": {"type": "integer", "minimum": 1, "multipleOf": 2}}, "required": ["x"]}
        cases, _, report = construction.construct(runtime.encode(schema), [{"x": 2}])
        # minimum's constructed zero violates only minimum; type None violates
        # type only, but a root replacement cannot masquerade as that edit.
        case = next(row for row in cases if row["expected"]["validator"] == "required")
        case["edit"] = {"op": "replace", "path": [], "value": {"x": -1, "extra": 0}}
        with self.assertRaises(ValueError):
            runtime.replay(case, {"contract.schema.json": runtime.encode(schema), **construction.construct(runtime.encode(schema), [{"x": 2}])[1]}, independent=True)
        coupled = {"type": "string", "enum": ["a"], "minLength": 1}
        emitted, _, _ = construction.construct(runtime.encode(coupled), ["a"])
        self.assertFalse(any(row["expected"]["validator"] == "minLength" for row in emitted))

    def test_bad_edit_and_resource_paths_are_refused(self):
        for operation in ({"op": "replace", "path": "../x", "value": 0},
                          {"op": "replace", "path": [True], "value": 0},
                          {"op": "replace", "path": ["missing"], "value": 0},
                          {"op": "remove", "path": []},
                          {"op": "add", "path": ["count"], "value": 0}):
            with self.assertRaises(ValueError):
                runtime.edit(BASELINE, operation)
        with self.assertRaises(ValueError):
            runtime.ref({"path": "../outside.json", "sha256": "a" * 64})

    def test_cycle_oversize_duplicate_json_and_external_ref_are_refused(self):
        value = []
        value.append(value)
        with self.assertRaisesRegex(ValueError, "cycle"):
            runtime._bounded(value)
        with self.assertRaises(ValueError):
            construction.construct(b" " * (runtime.MAX_BYTES + 1), [])
        with self.assertRaises(ValueError):
            runtime.decode(b'{"value":1,"value":2}')
        for schema in ({"$ref": "#"}, {"$ref": "https://example.invalid/schema"}):
            with self.assertRaises(ValueError):
                construction.construct(runtime.encode(schema), [{}])

    def test_repeated_baselines_do_not_create_extra_cases(self):
        again, bodies, _ = construction.construct(self.schema_bytes, [BASELINE, deepcopy(BASELINE)])
        self.assertEqual(again, self.cases)
        self.assertEqual(bodies, self.baselines)

    def test_later_valid_baseline_exposes_optional_member_constraint(self):
        schema = {"type": "object", "properties": {"optional": {"type": "integer", "minimum": 1}}}
        cases, baselines, report = construction.construct(runtime.encode(schema), [{}, {"optional": 2}])
        case = next(row for row in cases if row["expected"]["validator"] == "minimum")
        payloads = {"contract.schema.json": runtime.encode(schema), **baselines}
        self.assertEqual(runtime.resource(payloads, case["baseline"]), {"optional": 2})
        self.assertTrue(runtime.replay(case, payloads, independent=True)["isolated_violation"])
        self.assertEqual(report["valid_baselines_considered"], 2)
        self.assertEqual(len({row["job_id"] for row in cases}), len(cases))

    def test_valid_baseline_order_and_duplicates_do_not_change_output(self):
        schema = runtime.encode({"type": "object", "properties": {
            "x": {"type": "integer", "minimum": 1}, "y": {"type": "string", "minLength": 1}}})
        values = [{}, {"x": 2}, {"y": "good"}, {"x": 3, "y": "yes"}]
        first, bodies, _ = construction.construct(schema, values)
        second, repeated, _ = construction.construct(schema, list(reversed(values)) + values)
        self.assertEqual(first, second)
        self.assertEqual(bodies, repeated)

    def test_invalid_baseline_cannot_supply_an_optional_case(self):
        schema = runtime.encode({"type": "object", "properties": {
            "x": {"type": "integer", "minimum": 1}}})
        cases, _, report = construction.construct(schema, [{}, {"x": 0}])
        self.assertFalse(any(row["expected"]["validator"] == "minimum" for row in cases))
        self.assertEqual(report["invalid_baselines_ignored"], 1)


class PackageAndRunTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.folder, self.parent = parent_run(self.root)
        self.cases, self.baselines, self.accounting = construction.construct(self.parent.payloads["contract.schema.json"], [BASELINE])
        self.args = SimpleNamespace(parent_run=[self.folder], run_folder=self.root / "output", maximum_contracts=1,
            maximum_cases=1000, maximum_candidate_bytes=64*1024*1024, batch_size=1, maximum_seconds=60,
            authorize_output_writes=True)

    def groups(self, cases=None, maximum_files=runtime.MAX_FILES):
        staging = self.root / "staging"
        staging.mkdir(exist_ok=True)
        built = packages.generate(self.parent, self.cases if cases is None else cases, self.baselines,
            revision=REVISION, generated_on="2026-10-08", staging=staging, maximum_files=maximum_files)
        result = []
        for payload, bodies in built:
            folder = self.root / "groups" / payload["record_id"]
            atomic._materialize(folder, payload, bodies)
            result.append(from_folder(folder))
        return result

    def invoke(self):
        return runner.run_as_loop(self.args, revision=REVISION, licence_text=LICENSE, generator_digest="b" * 64)

    def test_complete_groups_share_exact_parent_schema_runner_and_licence_bytes(self):
        before = dict(self.parent.payloads)
        groups = self.groups(maximum_files=12)
        self.assertGreater(len(groups), 1)
        found = []
        for component in groups:
            self.assertLessEqual(len(component.package.files), 12)
            group = runtime.read_group(component.payloads, independent=True, replay_cases=True)
            found += [row["job_id"] for row in group["cases"]]
            for path in ("contract.schema.json", "schema_check.py", "LICENSE", "UPSTREAM-LICENSE"):
                self.assertEqual(component.payloads[path], self.parent.payloads[path])
        self.assertEqual(len(found), len(set(found)))
        self.assertEqual(set(found), {row["job_id"] for row in self.cases})
        self.assertEqual(dict(self.parent.payloads), before)
        self.assertEqual(len({component.payloads["README.md"] for component in groups}), 1)
        self.assertEqual(len({component.payloads["constraint_case_runtime.py"] for component in groups}), 1)
        self.assertEqual(len({component.payloads["SKILL.md"] for component in groups}), 1)
        self.assertIn(b"name: replay-isolated-constraint-cases", groups[0].payloads["SKILL.md"])

    def test_multi_baseline_groups_include_only_their_required_closure(self):
        schema = {"type": "object", "properties": {
            f"optional{i}": {"type": "integer", "minimum": 1} for i in range(8)}}
        values = [{}, *({f"optional{i}": 2} for i in range(8))]
        other = self.root / "multi"
        other.mkdir()
        _, parent = parent_run(other, schema=schema, baseline={}, baselines=values)
        cases, baselines, _ = construction.construct(parent.payloads["contract.schema.json"], values)
        stage = self.root / "multi-stage"
        stage.mkdir()
        built = packages.generate(parent, cases, baselines, revision=REVISION,
            generated_on="2026-10-08", staging=stage, maximum_files=14)
        self.assertGreater(len(built), 1)
        found = []
        for payload, blobs in built:
            data = {entry["path"]: blobs[entry["digest"]] for entry in payload["package"]["files"]}
            self.assertLessEqual(len(data), 14)
            group = runtime.read_group(data, independent=True, replay_cases=True)
            references = {runtime.resource(data, {"path": item["path"], "sha256": item["sha256"]})["baseline"]["path"]
                          for item in group["cases"]}
            self.assertEqual(references, {item["path"] for item in group["baselines"]})
            found.extend(item["job_id"] for item in group["cases"])
        self.assertEqual(len(found), len(set(found)))
        self.assertEqual(set(found), {row["job_id"] for row in cases})

    def test_duplicate_cases_and_orphan_case_files_are_refused(self):
        with self.assertRaises(ValueError):
            self.groups(self.cases + self.cases[:1])
        component = self.groups()[0]
        extra = dict(component.payloads)
        extra["cases/" + "a"*64 + ".json"] = b"{}"
        with self.assertRaises(ValueError):
            runtime.read_group(extra)

    def test_group_rename_and_reorder_do_not_create_a_new_native_job(self):
        component = self.groups()[0]
        policy = checks.QualificationContext.load(ROOT).policy
        group = runtime.decode(component.payloads[runtime.GROUP_FILE])
        group["cases"].reverse()
        renamed = component.replaced(identity="renamed", payloads={**component.payloads, runtime.GROUP_FILE: runtime.encode(group)},
            candidate={**component.candidate, "name": "Another label"})
        self.assertEqual(checks.job_key(component, policy), checks.job_key(renamed, policy))
        self.assertNotEqual(checks.job_key(component, policy), checks.job_key(self.parent, policy))

    def test_overlapping_case_jobs_are_found_in_population_and_prior_global_groups(self):
        first = self.groups(self.cases[:4])[0]
        second = self.groups(self.cases[2:6])[0]
        policy = checks.QualificationContext.load(ROOT).policy
        found = checks.duplicate_findings([first, second], policy)
        self.assertTrue(any(code == "overlapping_constraint_case_jobs" for rows in found.values() for code, _ in rows))
        known = {checks.CONSTRAINT_CASE_JOB_PREFIX + job: "earlier-admitted-group" for job in checks.constraint_jobs(first, policy)}
        found = checks.duplicate_findings([second], policy, known_digests=known)
        self.assertEqual(found[second.identity][0][0], "overlapping_constraint_case_jobs")
        disjoint = self.groups(self.cases[6:])[0]
        found = checks.duplicate_findings([first, disjoint], policy)
        self.assertFalse(any(code == "overlapping_constraint_case_jobs" for rows in found.values() for code, _ in rows))

    def test_native_producer_family_must_be_preserved(self):
        component = self.groups()[0]
        checks.require_declared_producer_family(component, "openai")
        with self.assertRaises(ValueError):
            checks.require_declared_producer_family(component, "anthropic")

    def test_case_jobs_survive_native_disk_backed_duplicate_pass(self):
        first = self.groups(self.cases[:4])[0]
        second = self.groups(self.cases[2:6])[0]
        policy = checks.QualificationContext.load(ROOT).policy
        spool = qualify._TokenSpool(self.root / "comparison.bin")
        self.addCleanup(spool.close)
        for component in (first, second):
            spool.add({"identity": component.identity, "package_digest": component.package.package_digest,
                       **qualify._comparison(component, policy)})
        found = checks.duplicate_findings_hashed(spool.subjects(), policy)
        self.assertTrue(any(code == "overlapping_constraint_case_jobs" for rows in found.values() for code, _ in rows))

    def test_prior_group_cli_seeds_jobs_without_writing_to_the_prior_folder(self):
        from tools import qualify_generated_components as cli
        component = self.groups()[0]
        prior = self.root / "groups" / component.identity
        output = self.root / "qualification"
        options = SimpleNamespace(store_root=self.root, line=[], exclude_identities=[], limit=None,
            output_folder=output, known_bundle=None, known_constraint_groups=[prior], engine="bwrap_rlimits",
            python="/usr/bin/python3", work_root=self.root / "work", workers=1, reuse=[], checks="fast")
        summary = dict.fromkeys(("components", "qualified", "refused", "unreadable", "reused", "seconds", "throughput"), 0)
        with patch.object(cli, "StoreReader") as reader, patch.object(cli.qualify, "qualify_rows", return_value=summary) as qualify_rows:
            reader.return_value.listing.return_value = []
            cli.command_qualify(options)
            arguments = qualify_rows.call_args.kwargs
        self.assertEqual(arguments["output"], output / "qualification.jsonl")
        self.assertEqual(len(arguments["known_digests"]), len(self.cases))
        self.assertTrue((output / "run.json").is_file())
        self.assertFalse((prior / "run.json").exists())
        altered = next((prior / "cases").iterdir())
        altered.write_bytes(b"{}")
        with patch.object(cli, "StoreReader") as reader, patch.object(cli.qualify, "qualify_rows") as qualify_rows:
            reader.return_value.listing.return_value = []
            with self.assertRaises(ValueError):
                cli.command_qualify(options)
            qualify_rows.assert_not_called()

    def test_native_folder_reader_refuses_aliases_before_reading_case_bytes(self):
        component = self.groups()[0]
        folder = self.root / "groups" / component.identity
        original = folder / "cases"
        preserved = self.root / "preserved-case-bytes"
        original.rename(preserved)
        original.symlink_to(preserved, target_is_directory=True)
        with self.assertRaises(ComponentReadError):
            from_folder(folder)
        with self.assertRaises(ValueError):
            runtime.load_folder(folder)

    def test_one_loop_per_batch_positive_resume_and_input_immutability(self):
        before = {str(path): path.read_bytes() for path in self.folder.rglob("*") if path.is_file()}
        result = self.invoke()
        self.assertEqual(result["loop_execution"]["attempts"], 1)
        self.assertEqual(result["loop_execution"]["model_calls"], 0)
        self.assertEqual(result["case_jobs"], len(self.cases))
        self.assertEqual(self.invoke()["new_case_jobs"], 0)
        self.assertEqual(before, {str(path): path.read_bytes() for path in self.folder.rglob("*") if path.is_file()})

    def test_partial_event_and_changed_input_refuse_resume(self):
        self.invoke()
        log = self.args.run_folder / "events.jsonl"
        with log.open("ab") as stream:
            stream.write(b'{"partial":')
        with self.assertRaises(atomic.ApiContractBatchError):
            self.invoke()
        self.assertFalse(json.loads(sorted(self.args.run_folder.glob("loop-invocation-*.json"))[-1].read_bytes())["batch_report_produced"])

    def test_changed_parent_bytes_refuse_resume_without_advancing_cursor(self):
        self.invoke()
        log = (self.args.run_folder / "events.jsonl").read_bytes()
        source = next((self.folder / "packages").glob("*/contract.schema.json"))
        source.write_bytes(b"{}")
        with self.assertRaises(atomic.ApiContractBatchError):
            self.invoke()
        self.assertEqual((self.args.run_folder / "events.jsonl").read_bytes(), log)

    def test_last_event_cannot_erase_cases_groups_or_reserved_bytes(self):
        self.invoke()
        journal = self.args.run_folder / "events.jsonl"
        original = json.loads(journal.read_bytes())
        retained = self.args.run_folder / original["record_path"]
        retained_before = retained.read_bytes()
        for changes in ({"case_jobs": [], "groups": [], "retained_and_candidate_bytes": 0},
                        {"retained_and_candidate_bytes": 0}, {"case_accounting": {}},
                        {"parent_record_id": "different-parent"}, {"unrecognized": True}):
            with self.subTest(changes=changes):
                journal.write_bytes(runtime.encode({**original, **changes}).replace(b"\n", b"") + b"\n")
                with self.assertRaises(atomic.ApiContractBatchError):
                    self.invoke()
                self.assertEqual(retained.read_bytes(), retained_before)
        journal.write_bytes(runtime.encode(original).replace(b"\n", b"") + b"\n")
        self.assertEqual(self.invoke()["new_case_jobs"], 0)

    def test_retained_parent_is_bound_to_the_plan_even_with_a_new_record_hash(self):
        self.invoke()
        journal = self.args.run_folder / "events.jsonl"
        event = json.loads(journal.read_bytes())
        path = self.args.run_folder / event["record_path"]
        retained = runtime.decode(path.read_bytes())
        retained["parent"]["package_digest"] = "a" * 64
        raw = runtime.encode(retained)
        path.write_bytes(raw)
        event["record_sha256"] = runtime.sha(raw)
        journal.write_bytes(runtime.encode(event).replace(b"\n", b"") + b"\n")
        with self.assertRaises(atomic.ApiContractBatchError):
            self.invoke()

    def test_all_output_aliases_refuse_before_generation_including_unlisted_paths(self):
        for suffix in ("staging", "packages", "retained", "unlisted/nested"):
            with self.subTest(suffix=suffix):
                self.args.run_folder = self.root / ("output-" + suffix.replace("/", "-"))
                external = self.root / ("outside-" + suffix.replace("/", "-"))
                external.mkdir()
                (external / "unchanged").write_bytes(b"sentinel")
                link = self.args.run_folder / suffix
                link.parent.mkdir(parents=True)
                link.symlink_to(external, target_is_directory=True)
                with patch.object(packages, "generate") as generate:
                    with self.assertRaises(atomic.ApiContractBatchError):
                        self.invoke()
                    generate.assert_not_called()
                self.assertEqual([(path.name, path.read_bytes()) for path in external.iterdir()], [("unchanged", b"sentinel")])

    def test_prior_journal_version_is_refused_without_conversion(self):
        self.invoke()
        journal = self.args.run_folder / "events.jsonl"
        event = json.loads(journal.read_bytes())
        event["record_type"] = "api_constraint_case_event/v1"
        raw = runtime.encode(event).replace(b"\n", b"") + b"\n"
        journal.write_bytes(raw)
        with self.assertRaises(atomic.ApiContractBatchError):
            self.invoke()
        self.assertEqual(journal.read_bytes(), raw)

    def test_completed_cursor_cannot_hide_an_unlisted_valid_group(self):
        self.invoke()
        extra = self.groups(self.cases[:4])[0]
        atomic._materialize(self.args.run_folder / "packages" / extra.identity, dict(extra.candidate),
            {entry.digest: extra.payloads[entry.path] for entry in extra.package.files})
        with self.assertRaises(atomic.ApiContractBatchError):
            self.invoke()

    def test_shared_checker_dirty_state_is_part_of_qualifier_identity(self):
        def status(arguments, **kwargs):
            dirty = "tools/supply_lines/schema_check.py" in arguments
            return SimpleNamespace(returncode=0, stdout=" M tools/supply_lines/schema_check.py\n" if dirty else "")
        with patch.object(qualify.subprocess, "run", side_effect=status):
            self.assertTrue(qualify.qualifier_changed(ROOT))

    def test_unrelated_json_file_does_not_change_existing_schema_job_rule(self):
        policy = checks.QualificationContext.load(ROOT).policy
        modified = self.parent.replaced(payloads={**self.parent.payloads, runtime.GROUP_FILE: b'{"unrelated":true}'})
        self.assertEqual(checks.job_key(self.parent, policy), checks.job_key(modified, policy))

    def test_case_byte_and_count_ceiling_preserves_unprocessed_parent(self):
        self.args.maximum_cases = 1
        report = self.invoke()
        self.assertEqual(report["case_jobs"], 0)
        self.assertEqual(report["next_cursor"], 0)
        self.assertEqual(report["ceiling"], "case_count_or_byte_ceiling")
        self.assertFalse((self.args.run_folder / "packages").exists())

    def test_crash_after_package_write_reconciles_exactly_without_extra_cases(self):
        with patch.object(atomic, "_append", side_effect=OSError("simulated interruption")):
            with self.assertRaises(atomic.ApiContractBatchError):
                self.invoke()
        result = self.invoke()
        self.assertEqual(result["case_jobs"], len(self.cases))
        self.assertEqual(result["parents_processed"], 1)

    def test_output_cannot_overlap_the_immutable_parent(self):
        self.args.run_folder = self.folder / "new-output"
        with self.assertRaises(atomic.ApiContractBatchError):
            self.invoke()
        self.assertFalse(self.args.run_folder.exists())


if __name__ == "__main__":
    unittest.main()
