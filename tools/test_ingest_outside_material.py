"""Known-wrong checks for outside-material ingestion and its staging into the candidate contract."""
from __future__ import annotations

from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore  # noqa: E402
from loop_engine.core.library_ingestion.pipeline_checks import self_test as pipeline_self_test  # noqa: E402
from loop_engine.core.library_ingestion.source_checks import (  # noqa: E402
    COMMIT, FakeGitHubReader, FakeRegistry, registry_entry, repository_table, skill_text)
from loop_engine.core.library_ingestion.licence_checks import MIT_FIXTURE  # noqa: E402
from loop_engine.core.library_ingestion.provenance import OUTLINE_ONLY  # noqa: E402
from loop_engine.core.library_ingestion.provenance_checks import (  # noqa: E402
    fixture_evidence, fixture_provenance)
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog  # noqa: E402
from tools.ingest_outside_material import (  # noqa: E402
    CollectOptions, StagingConflict, collect, stage_populations)
from tools.stage_intelligence_candidates import (  # noqa: E402
    CandidateStageRequest, compile_candidates, review_search)

MANIFEST = ROOT / "examples" / "29_intelligence_service" / "starter-catalogue" / "host-release" / "manifest.json"


def _sources(tmp: Path) -> dict:
    return {"record_type": "library_outside_sources/v1", "curated_on": "2026-09-22",
            "curated_by": "fixture", "schemas": [], "sources": [
                {"source_id": "github.example.skills", "engine": "github_pinned_repositories",
                 "repository": "example-owner/example-skills", "commit": COMMIT, "use": "verbatim",
                 "content_origin": "first_party", "expected_licence": "MIT",
                 "include": ["skills/*/SKILL.md"], "exclude": [], "note": "fixture"},
                {"source_id": "registry.mcp.official", "engine": "mcp_official_registry",
                 "host": "registry.modelcontextprotocol.io", "use": "link", "maximum_entries": 50,
                 "exclude_name_prefixes": [], "note": "fixture"}]}


def _entry_with_package(name: str, identifier: str) -> dict:
    entry = registry_entry(name)
    entry["server"].pop("remotes")
    entry["server"]["packages"] = [{"registryType": "npm", "identifier": identifier, "version": "1.0.0",
                                    "transport": {"type": "stdio"}}]
    return entry


class OutsideIngestionChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        files = {"LICENSE": MIT_FIXTURE.encode(),
                 **{f"skills/{name}/SKILL.md": skill_text(name).encode()
                    for name in ("alpha-check", "bravo-plan", "charlie-review")}}
        # A distinct body for each skill, so none of them is a near duplicate of another.
        for index, name in enumerate(("alpha-check", "bravo-plan", "charlie-review")):
            files[f"skills/{name}/SKILL.md"] = (
                f"---\nname: {name}\ndescription: Use when you need step {index} done.\n---\n# {name}\n\n"
                + "".join(f"Instruction {index}-{step}: measure {name} input {step} and compare it with "
                          f"the stored value {step * index}.\n" for step in range(12))).encode()
        self.table = repository_table(files)
        self.pages = [[_entry_with_package("io.github.one/alpha-server", "alpha-server"),
                       _entry_with_package("io.github.two/beta-server", "beta-server")]]

    def _collect(self, folder_name="run"):
        log = RequestLog()
        github = FakeGitHubReader(self.table, RequestBudget(maximum_requests=200), log)
        registry = FakeRegistry(self.pages, RequestBudget(maximum_requests=20), log)
        options = CollectOptions(run_folder=self.root / folder_name, network_reads_authorized=True)
        return collect(_sources(self.root), options, github_reader=github, registry_transport=registry,
                       request_log=log)

    def _rows(self):
        report = self._collect()
        populations = sorted((self.root / "run" / "populations").glob("specifications-*.json"))
        return report, [json.loads(path.read_text()) for path in populations]

    def _request(self):
        return CandidateStageRequest(ROOT, "library.outside.test", True)

    def test_the_run_report_counts_every_candidate_once_and_stages_nothing_itself(self):
        report, populations = self._rows()
        counts = report["counts"]
        self.assertEqual(counts["candidates"], 5)
        self.assertEqual(counts["staged_rows"], 5)
        self.assertEqual(sum(len(item["specifications"]) for item in populations), 5)
        self.assertFalse(report["approved"])
        self.assertFalse(report["hosted_publication"])
        self.assertTrue(all(len(item["specifications"]) <= 50 for item in populations))

    def test_a_v2_row_without_provenance_is_refused(self):
        _, populations = self._rows()
        broken = deepcopy(populations[0])
        broken["specifications"][0]["outside_provenance"] = []
        with self.assertRaisesRegex(ValueError, "provenance"):
            compile_candidates(broken, self._request())
        missing = deepcopy(populations[0])
        del missing["specifications"][0]["outside_provenance"]
        with self.assertRaises(ValueError):
            compile_candidates(missing, self._request())

    def test_a_v2_row_whose_authoring_disagrees_with_its_licence_evidence_is_refused(self):
        _, populations = self._rows()
        row = next(item for item in populations[0]["specifications"] if item["kind"] == "skill")
        for field, value in (("license_expression", "Apache-2.0"),
                             ("authoring", "generated_from_registry_facts")):
            broken = deepcopy(populations[0])
            target = next(item for item in broken["specifications"] if item["id"] == row["id"])
            target[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_candidates(broken, self._request())

    def test_a_v2_row_whose_merged_provenance_lacks_the_rights_its_authoring_needs_is_refused(self):
        _, populations = self._rows()
        broken = deepcopy(populations[0])
        row = next(item for item in broken["specifications"] if item["kind"] == "skill")
        row["outside_provenance"].append(fixture_provenance(
            path="skills/other/SKILL.md", licence_evidence=fixture_evidence(OUTLINE_ONLY, "NONE")))
        with self.assertRaisesRegex(ValueError, "authoring"):
            compile_candidates(broken, self._request())

    def test_a_v2_row_whose_text_is_not_one_of_its_package_files_is_refused(self):
        _, populations = self._rows()
        broken = deepcopy(populations[0])
        broken["specifications"][0]["text"] += "\nAn added line the package never held.\n"
        with self.assertRaisesRegex(ValueError, "package"):
            compile_candidates(broken, self._request())

    def test_a_v2_row_cannot_carry_a_lifecycle_or_an_approval(self):
        _, populations = self._rows()
        for field, value in (("lifecycle", "active"), ("approval_ref", "review/1")):
            broken = deepcopy(populations[0])
            broken["specifications"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_candidates(broken, self._request())

    def test_staged_outside_records_stay_candidates_with_their_licence_pending_review(self):
        _, populations = self._rows()
        records = compile_candidates(populations[0], self._request())
        with closing(SQLiteRecordStore(str(self.root / "stage.db"))) as store:
            stage_populations(store, populations, self._request())
            stored = [store.get(row["record_id"]) for row in records]
        self.assertTrue(all(row["lifecycle"] == "candidate" for row in stored))
        self.assertTrue(all(row["payload"]["execution_available"] is False for row in stored))
        self.assertTrue(all(row["payload"]["license_state"] == "pending_review" for row in stored))
        self.assertTrue(all(row["payload"]["qualification"] == "not_independently_qualified" for row in stored))

    def test_normal_search_serves_no_staged_outside_candidate(self):
        _, populations = self._rows()
        records = compile_candidates(populations[0], self._request())
        search = review_search(records)
        self.assertEqual(search["normal_search_hits"], 0)
        self.assertEqual(search["normal_search_excluded"], len(records))

    def test_an_identical_rerun_stages_nothing_new(self):
        _, populations = self._rows()
        with closing(SQLiteRecordStore(str(self.root / "stage.db"))) as store:
            first = stage_populations(store, populations, self._request())
            second = stage_populations(store, populations, self._request())
            count = len(store.export()["records"])
        self.assertEqual({row["state"] for row in first}, {"staged"})
        self.assertEqual({row["state"] for row in second}, {"already_staged"})
        self.assertEqual(count, 5)

    def test_a_changed_candidate_refuses_automatic_continuation(self):
        _, populations = self._rows()
        with closing(SQLiteRecordStore(str(self.root / "stage.db"))) as store:
            stage_populations(store, populations, self._request())
            changed = deepcopy(populations)
            changed[0]["specifications"][0]["tags"].append("a changed search label")
            with self.assertRaises(StagingConflict):
                stage_populations(store, changed, self._request())

    def test_one_population_holds_at_most_fifty_rows(self):
        _, populations = self._rows()
        oversized = deepcopy(populations[0])
        row = oversized["specifications"][0]
        oversized["specifications"] = [dict(row, id=f"{row['id'][:60]}_{index}") for index in range(51)]
        with self.assertRaisesRegex(ValueError, "bounded population"):
            compile_candidates(oversized, self._request())

    def test_staging_never_touches_the_served_manifest(self):
        before = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
        _, populations = self._rows()
        with closing(SQLiteRecordStore(str(self.root / "stage.db"))) as store:
            stage_populations(store, populations, self._request())
        self.assertEqual(hashlib.sha256(MANIFEST.read_bytes()).hexdigest(), before)
        written = sorted(str(path.relative_to(self.root)).split("/")[0] for path in self.root.iterdir())
        self.assertEqual(written, ["run", "stage.db"])

    def test_a_rerun_can_reuse_the_verified_bytes_of_an_earlier_run(self):
        first = self._collect("first")
        log = RequestLog()
        github = FakeGitHubReader(self.table, RequestBudget(maximum_requests=200), log)
        registry = FakeRegistry(self.pages, RequestBudget(maximum_requests=20), log)
        options = CollectOptions(run_folder=self.root / "second", network_reads_authorized=True,
                                 reuse_run_folders=(self.root / "first",))
        second = collect(_sources(self.root), options, github_reader=github, registry_transport=registry,
                         request_log=log)
        self.assertEqual([row["target"] for row in log.records if "/contents/" in row["target"]], [])
        self.assertEqual(second["counts"]["staged_rows"], first["counts"]["staged_rows"])
        self.assertGreater(second["reused_fetches"]["hits"], 0)
        self.assertIsNone(first["reused_fetches"])

    def test_the_run_folder_is_never_reused(self):
        self._collect()
        with self.assertRaises(FileExistsError):
            self._collect()

    def test_a_run_that_stops_halfway_keeps_the_record_of_every_model_call_it_made(self):
        sources = _sources(self.root)
        sources["sources"] = [dict(sources["sources"][0], use="outline", expected_licence=None)]
        answers = [SimpleNamespace(ok=True, text="Helps an assistant weigh measurements against saved numbers.",
                                   model="fixture-model", prompt_tokens=40, eval_tokens=9, usage_reported=True,
                                   error="", retry_after_seconds=None, response_received=True)]

        def chat(*args, **kwargs):
            if answers:
                return answers.pop(0)
            raise RuntimeError("the run stopped after its first model call")

        log = RequestLog()
        github = FakeGitHubReader(self.table, RequestBudget(maximum_requests=200), log)
        registry = FakeRegistry(self.pages, RequestBudget(maximum_requests=20), log)
        options = CollectOptions(run_folder=self.root / "halfway", network_reads_authorized=True,
                                 model_calls_authorized=True, outline_model="fixture-model", model_call_ceiling=5)
        with mock.patch("loop_engine.core.library_ingestion.outline_model._chat", return_value=chat):
            with self.assertRaises(RuntimeError):
                collect(sources, options, github_reader=github, registry_transport=registry, request_log=log)
        written = self.root / "halfway" / "model-calls.jsonl"
        self.assertTrue(written.is_file(), "the model call made before the stop was never written down")
        rows = [json.loads(line) for line in written.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([(row["outcome"], row["usage"]) for row in rows],
                         [("ok", {"prompt_tokens": 40, "completion_tokens": 9})])

    def test_the_component_pipeline_checks_pass_here(self):
        result = pipeline_self_test()
        self.assertTrue(result["all_passed"], [row for row in result["tests"] if row["passed"] is False])


if __name__ == "__main__":
    unittest.main()
