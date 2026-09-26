"""Checks for tools/generate_item_variations.py: variations of served items as candidates, never approved here.

```text
Item variations
├── the ideas have the shape the lanes read (task_reference, known_wrong, file_kind, seed_excerpt) and name
│   the served item they vary; the batch selects and renders without an occupation source
├── a served item whose licence is off the daily job's accepted list is skipped with its reason, and a
│   licence script without the list refuses
├── the ledger keeps a varied item out of the next run; without the ledger it would be picked again
├── the reviewed folder's provenance carries variation_of, through the real factory, panel and writer
├── the seed origin names the served item in the lane prompt; an owner seed keeps its wording
└── a missing program or a spent review-call cap is recorded as an outage and the run stops cleanly
```

Every fixture bundle is built here; no body of the library is copied, and no model is called.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
for entry in (str(HERE), str(HERE.parent / "src"), str(HERE.parent)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import generate_item_variations as tool  # noqa: E402
import write_reviewed_catalogue as writer  # noqa: E402
from candidate_review import engines, native, native_profile  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.panel import PanelRunRequest, ReviewPanel  # noqa: E402
from candidate_review.reviewers.fixture import FixtureReviewer  # noqa: E402
from test_write_reviewed_catalogue import fixture_panel, verdict_script  # noqa: E402
from tools import native_proposals_from_overnight_candidates as adapter  # noqa: E402
from tools import prepare_harness_candidates as factory  # noqa: E402
from tools.opencode_generation_lanes import _render_prompt  # noqa: E402
from tools.overnight_candidate_batch import BatchError, select_stratified  # noqa: E402

ROOT = HERE.parent
LICENCE_SCRIPT = "#!/usr/bin/env bash\nBATCH=12\nLICENCES=(MIT Apache-2.0 BSD-2-Clause BSD-3-Clause ISC CC0-1.0 CC-BY-4.0)\n"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(repository: Path, *arguments: str) -> str:
    finished = subprocess.run(["git", "-C", str(repository), "-c", "user.name=Fixture",
                               "-c", "user.email=fixture@example.invalid", *arguments],
                              capture_output=True, text=True, check=True, timeout=30)
    return finished.stdout.strip()


def skill_text(name: str) -> bytes:
    return (f"---\nname: {name}\ndescription: Use when a supplied list of integers must be summed and checked.\n"
            f"license: MIT\n---\n\n# Check a sum\n\nRead the supplied integers, recompute their sum and report it only "
            f"when both agree.\n").encode()


def bundle_item(identity: str, kind: str, licence: str, files: list, attributes: dict | None = None) -> tuple:
    """(bundle row, {digest: bytes}) of one served item; files are (path, role, bytes)."""
    entries, blobs = [], {}
    for path, role, body in files:
        digest = _sha(body)
        blobs[digest] = body
        entries.append({"digest": digest, "media_type": "text/markdown" if path.endswith(".md") else "text/plain",
                        "path": path, "role": role, "size_bytes": len(body)})
    if len(entries) == 1:
        digest, size = entries[0]["digest"], entries[0]["size_bytes"]
    else:
        document = json.dumps({"body_form": "package", "files": entries}, sort_keys=True).encode()
        digest, size = _sha(document), len(document)
        blobs[digest] = document
    reference = {"availability": "remote", "body_included": False, "declared_effects": [], "digest": digest,
                 "exposure": "metadata_only", "family": "harness", "identity": identity, "kind": kind,
                 "license": licence, "purpose": f"What {identity} does.", "record_type": "harness_intelligence_item/v1",
                 "size_bytes": size, "source_layer": "harness_local",
                 "source_ref": f"github.com/example/repo/{files[0][0]}@0123456789abcdef0123456789abcdef01234567",
                 "styles": [], "tags": {"language": ["en"], "lifecycle": ["candidate"], "record_type": "intelligence_tags/v1"}}
    row = {"approval": {"approval_ref": f"reviews.json#{identity}", "approved_digest": digest, "tier": "community"},
           "attributes": {"batch": "fixture", "catalogued_on": "2026-09-26", "cited_source": files[0][0],
                          "origin_layer": "context_intelligence", "tier": "community", **(attributes or {})},
           "package": {"body_form": "file" if len(entries) == 1 else "package", "files": entries},
           "record_type": tool.BUNDLE_ITEM_RECORD_TYPE, "reference": reference}
    return row, blobs


ATTRIBUTION = b"# Attribution\n\nCopied without change from github.com/example/repo at 0123456.\n"


def fixture_bundle(root: Path) -> Path:
    bundle = root / "bundles" / "daily-2026-09-26-fixture"
    rows, blobs = [], {}
    for row, found in (
            bundle_item("check_a_sum", "skill", "MIT", [("SKILL.md", "skill_definition", skill_text("check-a-sum"))],
                        {"step_functions": ["verification", "analysis"]}),
            bundle_item("import_skill_prs_abc", "skill", "Apache-2.0",
                        [("ATTRIBUTION.md", "other", ATTRIBUTION), ("LICENSE", "other", b"Apache License 2.0\n"),
                         ("SKILL.md", "skill_definition", skill_text("prs"))]),
            bundle_item("import_instruction_x", "instruction_file", "MIT",
                        [("CLAUDE.md", "instruction_file", b"# Project rules\n\nRun the checks before a commit.\n")]),
            bundle_item("restricted_skill", "skill", "GPL-3.0", [("SKILL.md", "skill_definition", skill_text("restricted"))]),
            bundle_item("some_tool", "tool", "MIT", [("tool.py", "executable_tool", b"print('hi')\n")])):
        rows.append(row)
        blobs.update(found)
    bundle.mkdir(parents=True)
    (bundle / "items.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    (bundle / "bundle.json").write_text(json.dumps({"record_type": "catalogue_release_bundle/v1", "items": len(rows)}))
    for digest, body in blobs.items():
        target = bundle / "blobs" / "sha256" / digest[:2] / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    # An older bundle with nothing in it must not be chosen: the newest name wins.
    (root / "bundles" / "daily-2026-09-25").mkdir()
    return bundle


class VariationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.bundle = fixture_bundle(self.root)
        self.library = self.root / "library"
        (self.library / "release-folders").mkdir(parents=True)
        self.script = self.root / "daily_library_release.sh"
        self.script.write_text(LICENCE_SCRIPT)

    def argv(self, run: str, stage: str, count: int = 10) -> list:
        return ["--run", run, "--stage", stage, "--count", str(count), "--bundle-root", str(self.root / "bundles"),
                "--library", str(self.library), "--ledger", str(self.library / "oracle" / "ledger.jsonl"),
                "--factory", str(self.library / "oracle" / "factory"),
                "--claude-counter", str(self.library / "oracle" / "claude.jsonl"),
                "--folder-list", str(self.library / "release-folders" / "reviewed-folders.txt"),
                "--lane-root", str(self.root / "lanes"), "--licence-script", str(self.script),
                "--authorize-model-calls"]

    def select(self, run: str = "run-1", count: int = 10) -> tuple:
        self.assertEqual(tool.main(self.argv(run, "select", count)), 0)
        folder = self.library / "variations" / run
        selection = json.loads((folder / "selection.json").read_text())
        ideas = json.loads((folder / "ideas.json").read_text()) if (folder / "ideas.json").is_file() else None
        return selection, ideas

    def test_ideas_have_the_lane_shape_and_name_what_they_vary(self):
        selection, batch = self.select()
        self.assertEqual(selection["picked"], 3)
        self.assertEqual(batch["record_type"], tool.BATCH_RECORD_TYPE)
        self.assertEqual(batch["sources"][0]["kind"], tool.SOURCE_KIND)
        self.assertEqual(batch["idea_count"], batch["unique_ids"], 3)
        by_source = {idea["applicability"]["variation_of"]["identity"]: idea for idea in batch["ideas"]}
        self.assertEqual(list(by_source)[0], "check_a_sum", "the item with step-function tags comes first")
        for idea in batch["ideas"]:
            applicability, source = idea["applicability"], idea["applicability"]["variation_of"]
            self.assertEqual(idea["record_type"], tool.IDEA_RECORD_TYPE)
            self.assertIn(idea["file_kind"], ("skill", "harness_routing"))
            self.assertEqual(source["record_type"], tool.VARIATION_RECORD_TYPE)
            self.assertIn(source["axis"], tool.AXES)
            self.assertIn(source["identity"], applicability["task_reference"])
            self.assertIn(source["axis"], applicability["task_reference"])
            self.assertTrue(idea["id"].endswith("-" + tool.AXIS_SLUG[source["axis"]]) or "-for-" in idea["id"])
            self.assertTrue(idea["known_wrong"])
            self.assertEqual(applicability["seed_licence"], source["license"])
            self.assertEqual(applicability["seed_attribution"]["digest"], source["digest"])
        imported = by_source["import_skill_prs_abc"]
        self.assertEqual(imported["applicability"]["seed_excerpt"], skill_text("prs").decode(),
                         "the seed is the package's entry file, not its licence or attribution file")
        self.assertEqual(imported["applicability"]["variation_of"]["entry_path"], "SKILL.md")
        self.assertEqual(imported["applicability"]["variation_of"]["entry_digest"], _sha(skill_text("prs")))
        self.assertIn("Copied without change", imported["applicability"]["seed_attribution"]["attribution_text"])
        self.assertEqual(imported["applicability"]["variation_of"]["license"], "Apache-2.0")
        instruction = by_source["import_instruction_x"]
        self.assertEqual(instruction["applicability"]["seed_excerpt"], "# Project rules\n\nRun the checks before a commit.\n")
        # The batch's own selection accepts a served-bundle source without an occupation rotation.
        picked = select_stratified(batch, batch["idea_count"])
        self.assertEqual(sorted(idea["id"] for idea in picked), sorted(idea["id"] for idea in batch["ideas"]))
        prompt = _render_prompt(picked[0])
        self.assertIn("<<<SEED>>>", prompt)
        self.assertIn("a served library item", prompt)
        self.assertNotIn("owner's own project", prompt)
        rows = [json.loads(line) for line in (self.library / "oracle" / "ledger.jsonl").read_text().splitlines()]
        self.assertEqual({row["source_digest"] for row in rows}, {source["digest"] for source in
                                                                   (idea["applicability"]["variation_of"] for idea in batch["ideas"])})

    def test_a_served_bundle_source_is_self_grounded_and_an_unknown_kind_is_not(self):
        _selection, batch = self.select()
        other = {**batch, "sources": [{**batch["sources"][0], "kind": "some_other_kind"}]}
        with self.assertRaisesRegex(BatchError, "matrix_missing_pinned_source"):
            select_stratified(other, 1)

    def test_a_licence_off_the_accepted_list_is_skipped_and_a_script_without_the_list_refuses(self):
        selection, batch = self.select()
        self.assertEqual(selection["skipped"], {"licence_not_accepted": 1, "kind_without_native_placement": 1})
        self.assertNotIn("restricted_skill", {idea["applicability"]["variation_of"]["identity"] for idea in batch["ideas"]})
        self.script.write_text("#!/usr/bin/env bash\nBATCH=12\n")
        with self.assertRaisesRegex(tool.VariationError, "licence_list_missing"):
            tool.accepted_licences(self.script)
        with self.assertRaisesRegex(tool.VariationError, "licence_list_unreadable"):
            tool.accepted_licences(self.root / "missing.sh")

    def test_the_ledger_keeps_a_varied_item_out_of_the_next_run(self):
        first, batch = self.select("run-1")
        self.assertEqual(first["picked"], 3)
        second, ideas = self.select("run-2")
        self.assertEqual((second["picked"], second["already_varied"], second["skipped"].get("already_varied")), (0, 3, 3))
        self.assertIsNone(ideas, "a run with nothing to vary writes no idea batch")
        self.assertTrue((self.library / "variations" / "run-2" / "nothing-to-do").is_file())
        # Known-wrong case: without the ledger's digests the same items are picked again.
        items = tool.read_bundle_items(self.bundle)
        picked, _skipped = tool.select_items(items, set(), 10, tool.accepted_licences(self.script))
        self.assertEqual(len(picked), 3)
        picked, _skipped = tool.select_items(items, tool.ledger_digests(self.library / "oracle" / "ledger.jsonl"), 10,
                                             tool.accepted_licences(self.script))
        self.assertEqual(picked, [])

    def test_provenance_carries_variation_of_through_the_factory_the_panel_and_the_writer(self):
        _selection, batch = self.select()
        idea = next(idea for idea in batch["ideas"] if idea["applicability"]["variation_of"]["identity"] == "check_a_sum")
        repo = self.root / "factory"
        repo.mkdir()
        _git(repo, "init", "-q")
        shutil.copyfile(ROOT / "LICENSE", repo / "LICENSE")
        idea_source = "runs/run-1/attribution/ideas/" + idea["id"] + ".json"
        (repo / idea_source).parent.mkdir(parents=True)
        idea_bytes = adapter.canonical(idea)
        (repo / idea_source).write_bytes(idea_bytes)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "fixture")
        revision = _git(repo, "rev-parse", "HEAD")
        candidate = skill_text(idea["id"])
        row = {"lane": tool.LANE_ID, "idea_id": idea["id"], "file": "unused", "sha256": _sha(candidate),
               "file_kind": idea["file_kind"]}
        lane = {"provider": "tactical", "model": "gemma-4-coding-abliterated", "family": tool.LANE_FAMILY}
        proposal = adapter.proposal_for(row, candidate, idea, lane, idea_source)
        record = {"record_type": factory.NATIVE_INPUT_TYPE, "source_revision": revision,
                  "license": {"expression": "MIT", "path": "LICENSE", "sha256": _sha((repo / "LICENSE").read_bytes())},
                  "sources": {idea_source: _sha(idea_bytes)}, "proposals": [proposal]}
        proposals = self.root / "proposals.json"
        proposals.write_bytes(adapter.canonical(record))
        candidates = self.root / "candidates"
        factory.prepare(factory.PreparationRequest(repo, proposals, candidates, True))
        identity = proposal["id"]
        configuration = native_profile.configuration(fixture_panel(self.root / "panel.json"))
        criteria, instructions = native_profile.resources()
        catalogue = native.NativeCatalogue.load(candidates, repo)
        first, _other = configuration.installations
        panel = ReviewPanel(configuration, criteria, instructions,
                            {first.installation_id: FixtureReviewer(first, verdict_script("approve"))},
                            engines.build_precheck_engines(configuration), ReviewLedger(self.root / "ledger.jsonl"))
        request = catalogue.request(identity, catalogue.producer_for(identity), criteria, instructions.sha256)
        self.assertEqual(request.producer.family, "google", "the Tactical lane's declared family")
        panel.run(PanelRunRequest(run_id="run-1", requests=(request,), population=catalogue.population_bodies(),
                                  call_ceiling=2, token_ceiling=1_000_000, model_calls_authorized=True, fixture_run=True,
                                  collect_below_quorum_reason="one family in this check"))
        summary = writer.write(argparse.Namespace(
            repository=repo, panel=self.root / "panel.json", catalogue=candidates, ledger=[str(self.root / "ledger.jsonl")],
            reviewer=["fixture.reviewer"], tier="community", output=self.root / "reviewed", recorded_at="2026-09-26",
            allow_fixture=True, scan_record=[], identities_file=None))
        self.assertEqual((summary["approved"], summary["rejected"]), (1, 0))
        [item] = json.loads((self.root / "reviewed" / "items.json").read_text())["items"]
        varied = item["provenance"]["variation_of"]
        self.assertEqual((varied["identity"], varied["digest"], varied["axis"]),
                         ("check_a_sum", idea["applicability"]["variation_of"]["digest"], idea["applicability"]["variation_of"]["axis"]))
        self.assertEqual(item["provenance"]["authoring"], "original_model_authored")
        # Known-wrong case: an idea that varies nothing gives the row no variation_of.
        spec = dict(catalogue._specifications[identity])
        plain = {**idea, "applicability": {key: value for key, value in idea["applicability"].items() if key != "variation_of"}}
        with mock.patch.dict(catalogue._sources, {idea_source: type(catalogue._sources[idea_source])(
                idea_source, revision, "0" * 64, json.dumps(plain))}):
            self.assertEqual(writer.variation_of(catalogue, spec), {})

    def test_the_seed_origin_names_the_served_item_and_an_owner_seed_keeps_its_wording(self):
        idea = {"record_type": tool.IDEA_RECORD_TYPE, "id": "an-idea", "file_kind": "skill", "datatype": "text",
                "operation": "validation", "use_case": "data_cleaning", "lifecycle": "candidate",
                "applicability": {"task_reference": "Vary it.", "seed_excerpt": "Some served text."},
                "method_signature": "x", "brief": "Vary it.", "known_wrong": "It is the same."}
        self.assertIn("owner's own project", _render_prompt(idea))
        named = {**idea, "applicability": {**idea["applicability"], "seed_origin": "a served library item, x, under the MIT licence"}}
        prompt = _render_prompt(named)
        self.assertIn("Seed material from a served library item, x, under the MIT licence follows", prompt)
        self.assertNotIn("owner's own project", prompt)

    def test_a_missing_program_or_a_spent_review_cap_is_an_outage_that_stops_cleanly(self):
        self.select()
        folder = self.library / "variations" / "run-1"
        (folder / "identities.txt").write_text("check_a_sum_alt\n")
        with mock.patch.object(tool.shutil, "which", lambda name: None):
            self.assertEqual(tool.main(self.argv("run-1", "review")), tool.OUTAGE_EXIT)
        counter = self.library / "oracle" / "claude.jsonl"
        counter.write_text(json.dumps({"run": "baseline", "calls": tool.CLAUDE_REVIEW_CALL_CAP}) + "\n")
        with mock.patch.object(tool.shutil, "which", lambda name: "/usr/bin/claude"):
            self.assertEqual(tool.main(self.argv("run-1", "review")), tool.OUTAGE_EXIT)
        events = [json.loads(line) for line in (folder / "journal.jsonl").read_text().splitlines()]
        outages = [(event["stage"], event["reason"]) for event in events if event["event"] == "outage"]
        self.assertEqual(outages, [("review", "program_missing"), ("review", "review_call_cap_reached")])
        self.assertFalse((folder / "review.done").exists())

    def test_a_model_stage_without_the_explicit_authority_stops_before_any_call(self):
        # Known-wrong case: a run that names no model-call authority must not reach the generation lane or the
        # review panel. The check fails if the refusal in main() is removed.
        argv = [value for value in self.argv("run-1", "generate") if value != "--authorize-model-calls"]
        with mock.patch.object(tool.Run, "generate", side_effect=AssertionError("a model stage ran")), \
                mock.patch.object(tool.Run, "review", side_effect=AssertionError("a model stage ran")):
            self.assertEqual(tool.main(argv), 2)
            review = [value for value in self.argv("run-1", "review") if value != "--authorize-model-calls"]
            self.assertEqual(tool.main(review), 2)
        # A stage that calls no model needs no authority.
        self.assertEqual(tool.main([value for value in self.argv("run-1", "select")
                                    if value != "--authorize-model-calls"]), 0)


if __name__ == "__main__":
    unittest.main()
