"""Seed ideas come only from the owner's own projects, cite their inventory, and fit the generation lanes.

Roadmap step S-6.207. Known-wrong cases: a third-party project seeds nothing, a project the owner's own index marks as
imported seeds nothing, a README-only folder seeds nothing, an inventory that is not one is refused, an output inside
the repository is refused, and every idea carries the fields the lanes read plus its bounded seed excerpt.

The media cases of September 26, 2026: media files are counted from the file shards in the deepest project root
above them and never in a project that does not hold them, a media file above every project root counts nowhere,
only a project with thirty or more media files seeds a second media idea, every identity fits the attribution
adapter's pattern, and every idea cites its project path, the projects digest and the shards digest.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import unittest.mock
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
        # Media: the resizer holds 38 media files in a folder that is not a project root, own-remote holds three,
        # and one image sits above every project root.
        for number in range(35):
            _write(self.volume, f"PROJECTS/resizer/renders/frame-{number:03d}.png", "png")
        _write(self.volume, "PROJECTS/resizer/renders/reel.mp4", "mp4")
        _write(self.volume, "PROJECTS/resizer/renders/teaser.mov", "mov")
        _write(self.volume, "PROJECTS/resizer/scene.blend", "blend")
        for name in ("a.jpg", "b.jpg", "c.jpg"):
            _write(self.volume, f"PROJECTS/own-remote/shots/{name}", "jpg")
        _write(self.volume, "PROJECTS/loose.png", "png")
        self.inventory = self.root / "inventory"
        self.assertEqual(scanner.main(["--volume", str(self.volume), "--output", str(self.inventory),
                                       "--owner-account", "owner-account", "--owner-name", "amarel"]), 0)
        self.output = self.root / "seeds"
        self.report = seeds.build(self.inventory, self.volume, self.volume / "PROJECT_REGISTRY.json", self.output,
                                  maximum=50, volume_name="fixture")
        self.batch = json.loads((self.output / "seed-ideas.json").read_text())

    def _idea(self, identity):
        return next(idea for idea in self.batch["ideas"] if idea["id"] == identity)

    def test_media_is_counted_from_the_shards_in_the_deepest_project_root(self):
        resizer = self._idea("vol-fixture-projects-resizer")["applicability"]["seed"]["assets"]
        self.assertEqual(resizer["by_kind"], {"image": 35, "video": 2, "blender": 1})
        self.assertEqual(resizer["media_files"], 38)
        self.assertEqual(resizer["record_type"], seeds.ASSET_RECORD_TYPE)
        own = self._idea("vol-fixture-projects-own-remote")["applicability"]["seed"]["assets"]
        self.assertEqual(own["by_kind"], {"image": 3}, "own-remote's shots are not the resizer's, and loose.png counts nowhere")
        excerpt = self._idea("vol-fixture-projects-resizer")["applicability"]["seed_excerpt"]
        self.assertIn("Assets in this project (from the inventory): images 35, video files 2, Blender files 1.", excerpt)
        self.assertIn("Examples: images: frame-000.png, frame-001.png, frame-002.png; video files: reel.mp4, teaser.mov;"
                      " Blender files: scene.blend.", excerpt, "examples are the first names in name order")
        self.assertNotIn("loose.png", excerpt)
        self.assertLessEqual(len(excerpt), seeds.EXCERPT_BOUND)
        # The shards the counts came from are cited by digest, in the batch and in every idea.
        shards = [source for source in self.batch["sources"] if source["role"] == "files"]
        self.assertEqual([shard["path"] for shard in shards], [str(self.inventory / "files-001.jsonl")])
        self.assertEqual(self.batch["shards_sha256"], seeds.shards_digest(self.report["shards_read"]))
        self.assertTrue(all(source["kind"] == "owner_volume_inventory" for source in self.batch["sources"]))
        self.assertEqual(self.report["media_files_by_kind"], {"image": 38, "video": 2, "blender": 1})
        # Known wrong: a shard line that is not a file row, or is still being written, is skipped and counted.
        with (self.inventory / "files-001.jsonl").open("a") as stream:
            stream.write('{"record_type": "local_volume_file/v1", "path": "PROJECTS/resizer/x.png", "lang')
        per_project, read = seeds.asset_index(self.inventory, ["PROJECTS/resizer", "PROJECTS/own-remote"])
        self.assertEqual(read[0]["unparsed_rows"], 1)
        self.assertEqual(per_project["PROJECTS/resizer"]["by_kind"]["image"], 35)

    def test_a_media_heavy_project_seeds_a_second_media_idea_and_a_light_one_does_not(self):
        ids = {idea["id"] for idea in self.batch["ideas"]}
        self.assertIn("vol-fixture-projects-resizer-media", ids)
        self.assertNotIn("vol-fixture-projects-own-remote-media", ids, "three media files are under the minimum")
        base, media = self._idea("vol-fixture-projects-resizer"), self._idea("vol-fixture-projects-resizer-media")
        self.assertEqual(media["file_kind"], "skill")
        self.assertEqual((media["datatype"], media["operation"], media["use_case"]), ("image", "transformation", base["use_case"]))
        self.assertNotEqual(media["method_signature"], base["method_signature"])
        self.assertIn("produce or edit images the way the owner's project resizer does", media["brief"])
        self.assertIn("holds 38 media files (images 35, video files 2, Blender files 1), mostly images", media["applicability"]["task_reference"])
        self.assertEqual(media["applicability"]["seed"]["idea_role"], "media")
        self.assertEqual(media["applicability"]["seed"]["dominant_media_kind"], "image")
        self.assertEqual(base["applicability"]["seed"]["idea_role"], "project")
        self.assertEqual(media["applicability"]["seed_excerpt"], base["applicability"]["seed_excerpt"])
        self.assertIn("<<<SEED>>>", _render_prompt(media))
        self.assertEqual(self.report["media_ideas"], 1)
        self.assertEqual(self.report["kept"], 2, "a media idea is a second idea of a kept project, not a kept project")
        self.assertEqual(self.batch["idea_count"], 3)
        self.assertEqual(self.batch["unique_method_signatures"], 3)
        # Known wrong: with the minimum above the resizer's count, no media idea is seeded.
        with unittest.mock.patch.object(seeds, "MEDIA_HEAVY_MINIMUM", 39):
            report = seeds.build(self.inventory, self.volume, None, self.root / "seeds-high", maximum=50,
                                 volume_name="fixture")
        self.assertEqual(report["media_ideas"], 0)

    def test_every_identity_fits_the_attribution_adapter_and_every_idea_cites_its_inventory(self):
        from native_proposals_from_overnight_candidates import IDEA_IDENTITY
        for idea in self.batch["ideas"]:
            self.assertTrue(IDEA_IDENTITY.fullmatch(idea["id"]), idea["id"])
            self.assertLessEqual(len(idea["id"]), seeds.IDENTITY_BOUND)
            seed = idea["applicability"]["seed"]
            self.assertEqual(seed["project_path"].split("/")[-1], seed["project_name"])
            self.assertEqual(seed["inventory_sha256"], self.report["inventory_sha256"])
            self.assertEqual(seed["assets"]["shards_sha256"], self.batch["shards_sha256"])
        # Known wrong: a part cut at a hyphen must not leave two hyphens in a row or a trailing one.
        self.assertEqual(seeds._identity("vol", "fixture", "parent-", "-name-"), "vol-fixture-parent-name")
        self.assertTrue(IDEA_IDENTITY.fullmatch(seeds._identity("vol", "x-", "media")))
        self.assertFalse(seeds.IDENTITY.match("vol--x"))
        self.assertFalse(seeds.IDENTITY.match("vol-x-"))

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
        picked = select_stratified(matrix, self.batch["idea_count"])
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
