"""Seed ideas come only from the owner's own projects, cite their inventory, and fit the generation lanes.

Roadmap step S-6.207. Known-wrong cases: a third-party project seeds nothing, a project the owner's own index marks as
imported seeds nothing, a README-only folder seeds nothing, an inventory that is not one is refused, an output inside
the repository is refused, and every idea carries the fields the lanes read plus its bounded seed excerpt.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

import build_volume_seed_ideas as seeds  # noqa: E402
import scan_local_volume as scanner  # noqa: E402
from harness_idea_matrix import FILE_KINDS  # noqa: E402
from opencode_generation_lanes import _render_prompt  # noqa: E402
from overnight_candidate_batch import load_matrix, select_stratified  # noqa: E402
from test_scan_local_volume import _write, fixture_volume  # noqa: E402


class SeedIdeasTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.volume = self.root / "volume"
        fixture_volume(self.volume)
        # A README-only organization folder and a project the owner's own index marks as imported.
        _write(self.volume, "PROJECTS/_ORGANIZATION/README.md", "# Moves\n\nFiles were moved.\n")
        _write(self.volume, "PROJECTS/notes-only/README.md", "# Notes\n\nA folder of notes about other folders.\n")
        _write(self.volume, "PROJECTS/notes-only/a.md", "note\n")
        _write(self.volume, "PROJECTS/notes-only/helper.sh", "echo note\n")
        _write(self.volume, "PROJECTS/imported/README.md", "# Imported\n")
        _write(self.volume, "PROJECTS/imported/main.py", "def go():\n    return 1\n")
        (self.volume / "PROJECT_REGISTRY.json").write_text(json.dumps({"items": [
            {"path": str(self.volume / "PROJECTS/imported"), "status": "imported_workspace", "domain": "CODING_PROJECTS"}]}))
        self.inventory = self.root / "inventory"
        self.assertEqual(scanner.main(["--volume", str(self.volume), "--output", str(self.inventory),
                                       "--owner-account", "owner-account", "--owner-name", "amarel"]), 0)
        self.output = self.root / "seeds"
        self.report = seeds.build(self.inventory, self.volume, self.volume / "PROJECT_REGISTRY.json", self.output,
                                  maximum=50, volume_name="fixture")
        self.batch = json.loads((self.output / "seed-ideas.json").read_text())

    def test_only_the_owners_projects_with_an_outline_seed_ideas(self):
        kept = {idea["applicability"]["seed"]["project_path"] for idea in self.batch["ideas"]}
        self.assertEqual(kept, {"PROJECTS/resizer", "PROJECTS/own-remote"})
        excluded = {row["path"]: row["reason"] for row in map(json.loads, (self.output / "excluded.jsonl").read_text().splitlines())}
        self.assertEqual(excluded["PROJECTS/cloned"], "provenance_class:" + scanner.THIRD_PARTY_REMOTE)
        self.assertEqual(excluded["PROJECTS/licensed"], "provenance_class:" + scanner.THIRD_PARTY_LICENCE)
        self.assertEqual(excluded["PROJECTS/copied"], "provenance_class:" + scanner.THIRD_PARTY_COPYRIGHT)
        self.assertEqual(excluded["PROJECTS/imported"], "owner_index_status:imported_workspace")
        self.assertEqual(excluded["PROJECTS/notes-only"], "no_module_outline")
        self.assertEqual(excluded["PROJECTS/_ORGANIZATION"], "organization_folder")
        self.assertEqual(self.report["kept"], 2)

    def test_every_idea_carries_what_the_lanes_read_and_its_seed(self):
        for idea in self.batch["ideas"]:
            self.assertEqual(idea["record_type"], "harness_idea_record/v1")
            self.assertRegex(idea["id"], seeds.IDENTITY)
            self.assertIn(idea["file_kind"], FILE_KINDS)
            seed = idea["applicability"]["seed"]
            self.assertEqual(seed["inventory_sha256"], self.report["inventory_sha256"])
            self.assertEqual(seed["volume"], "fixture")
            self.assertIn("declared on September 26, 2026", seed["authorship_basis"])
            self.assertLessEqual(len(idea["applicability"]["seed_excerpt"]), seeds.EXCERPT_BOUND)
            prompt = _render_prompt(idea)
            self.assertIn("<<<SEED>>>", prompt)
            self.assertIn(idea["known_wrong"], prompt)
        resizer = next(idea for idea in self.batch["ideas"] if idea["applicability"]["seed"]["project_name"] == "resizer")
        self.assertEqual(resizer["datatype"], "image")
        self.assertIn("def resize(path, width)", resizer["applicability"]["seed_excerpt"])
        self.assertIn("Dependencies: pillow", resizer["applicability"]["seed_excerpt"])
        self.assertEqual(resizer["applicability"]["seed"]["modules_read"], ["main.py"])

    def test_the_batch_loads_and_selects_without_an_occupation_rotation(self):
        from overnight_candidate_batch import BatchError
        matrix = load_matrix(self.output / "seed-ideas.json")
        picked = select_stratified(matrix, 2)
        self.assertEqual({idea["id"] for idea in picked}, {idea["id"] for idea in self.batch["ideas"]})
        self.assertTrue(all("seed_excerpt" in idea["applicability"] for idea in picked))
        self.assertEqual(self.batch["sources"][0]["kind"], "owner_volume_inventory")
        # Known wrong: a batch whose sources are neither pinned occupations nor a self-grounded kind is refused.
        unknown = {**matrix, "sources": [{"kind": "somebody_elses_list", "path": "x", "sha256": "0" * 64}]}
        with self.assertRaises(BatchError):
            select_stratified(unknown, 1)

    def test_known_wrong_inputs_are_refused(self):
        with self.assertRaises(seeds.SeedError):
            seeds.build(self.root / "missing", self.volume, None, self.root / "out-1", maximum=5, volume_name="v")
        bad = self.root / "bad-inventory"
        bad.mkdir()
        (bad / "projects.jsonl").write_text(json.dumps({"record_type": "other/v1"}) + "\n")
        with self.assertRaises(seeds.SeedError):
            seeds.build(bad, self.volume, None, self.root / "out-2", maximum=5, volume_name="v")
        code = seeds.main(["--inventory", str(self.inventory), "--volume", str(self.volume),
                           "--output", str(HERE.parent / "seeds-here")])
        self.assertEqual(code, 2)
        self.assertFalse((HERE.parent / "seeds-here").exists())


if __name__ == "__main__":
    unittest.main()
