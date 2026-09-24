"""Offline checks for the adapter from overnight batch candidates to native proposals.

```text
Overnight candidate adapter
├── attribute
│   ├── the lane is the one the journal records as having written the file
│   ├── the idea record comes from the matrix in effect at the recorded write,
│   │   with the grounding the batch's own selection gave the producer
│   ├── a matrix whose pinned source changed is refused
│   └── a file no journal write names is excluded with its reason
└── proposals
    ├── only a committed attribution record is read
    ├── a skill becomes SKILL.md and a routing file AGENTS.md; other kinds are left out
    ├── bytes changed after attribution are left out
    └── a candidate the factory refuses is left out alone, with the factory's code
```
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "src"))

from unittest import mock  # noqa: E402

from tools import native_proposals_from_overnight_candidates as adapter  # noqa: E402
from tools import prepare_harness_candidates as factory  # noqa: E402
from tools.test_prepare_harness_candidates import _git  # noqa: E402

LANE, OTHER_LANE = "lane-fixture-model", "lane-other-model"
SWITCH = "2026-09-24T07:45:19Z"


def idea(identity, kind):
    return {"record_type": adapter.IDEA_TYPE, "id": identity, "file_kind": kind, "datatype": "numeric_column",
            "operation": "aggregation", "use_case": "data_cleaning", "lifecycle": "candidate",
            "applicability": {"occupation_code": "15-2051.00", "occupation_title": "Data Scientists",
                              "task_reference": "Clean and aggregate survey data."},
            "brief": "Propose one original method.", "known_wrong": "A sentinel value is averaged as data."}


def rotated(record, count):
    """A stand-in for the batch's selection: each picked idea gets the next task of a rotation."""
    return [{**entry, "applicability": {**entry["applicability"], "task_reference": f"Rotated task {number}"}}
            for number, entry in enumerate(record["ideas"][:count])]


def skill(identity, extra=""):
    return (f"---\nname: {identity}\ndescription: Use when a numeric column is aggregated for a report.\n"
            f"license: MIT\n---\n\n# Aggregate a numeric column\n\nRecompute the aggregate from the raw values."
            f"{extra}\n").encode()


class AdapterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.batch = root / "batch"
        (self.batch / "candidates" / LANE).mkdir(parents=True)
        (self.batch / "candidates" / OTHER_LANE).mkdir(parents=True)
        self.repo = root / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.name", "Fixture")
        _git(self.repo, "config", "user.email", "fixture@example.invalid")
        shutil.copyfile(HERE.parent / "LICENSE", self.repo / "LICENSE")
        _git(self.repo, "add", "LICENSE")
        _git(self.repo, "commit", "-q", "-m", "licence")
        early = {"record_type": "harness_idea_batch/v1",
                 "ideas": [idea(name, "skill") for name in ("first-idea", "second-idea", "third-idea",
                                                            "fourth-idea", "secret-idea")]}
        late = {"record_type": "harness_idea_batch/v1",
                "ideas": [idea("first-idea", "subagent"), idea("second-idea", "harness_routing"),
                          idea("third-idea", "subagent"), idea("fourth-idea", "skill"),
                          idea("secret-idea", "skill")]}
        (root / "early.json").write_text(json.dumps(early))
        (root / "late.json").write_text(json.dumps(late))
        self.matrices = [f"{root / 'early.json'}@2026-09-24T04:00:00Z@5", f"{root / 'late.json'}@{SWITCH}@5"]
        self.root = root
        writes = {("first-idea", LANE): "2026-09-24T05:00:00Z",  # before the switch: asked for a skill
                  ("second-idea", LANE): "2026-09-24T08:00:00Z",  # after: a harness routing file
                  ("third-idea", LANE): "2026-09-24T08:10:00Z",  # after: a subagent, not placed
                  ("secret-idea", LANE): "2026-09-24T08:20:00Z",
                  ("fourth-idea", OTHER_LANE): "2026-09-24T08:30:00Z"}
        journal = [{"record_type": adapter.JOURNAL_EVENT_TYPE, "event": "outcome", "outcome": "candidate_written",
                    "lane_id": lane, "idea_id": name, "ts": moment} for (name, lane), moment in writes.items()]
        (self.batch / "journal.jsonl").write_text("".join(json.dumps(row) + "\n" for row in journal) + '{"partial')
        status = {"record_type": adapter.STATUS_TYPE, "updated_at": "2026-09-24T09:00:00Z",
                  "lanes": {LANE: {"provider": "fixture-cloud", "model": "fixture-model"},
                            OTHER_LANE: {"provider": "fixture-cloud", "model": "other-model"}}}
        (self.batch / "status.json").write_text(json.dumps(status))
        for name in ("first-idea", "second-idea", "third-idea"):
            (self.batch / "candidates" / LANE / f"{name}.md").write_bytes(skill(name))
        # A secret-shaped value, built here so this file never holds one.
        (self.batch / "candidates" / LANE / "secret-idea.md").write_bytes(
            skill("secret-idea", "\n\nUse the key " + "AKIA" + "Q" * 16 + " to read the bucket."))
        (self.batch / "candidates" / LANE / "unjournaled-idea.md").write_bytes(skill("unjournaled-idea"))
        (self.batch / "candidates" / OTHER_LANE / "fourth-idea.md").write_bytes(skill("fourth-idea"))
        self.folder = self.repo / "artifacts" / "attribution"

    def attribute(self):
        with mock.patch.object(adapter, "batch_selection", rotated):
            return adapter.attribute(self.batch, self.matrices, {LANE: "zhipu", OTHER_LANE: "nvidia"}, self.folder)

    def commit(self):
        _git(self.repo, "add", ".")
        _git(self.repo, "commit", "-q", "-m", "attribution")

    def proposals(self):
        output = self.repo / "proposals.json"
        summary = adapter.proposals(self.repo, self.folder / "attribution.json", self.batch, output)
        return summary, json.loads(output.read_text()), json.loads((self.repo / "proposals-report.json").read_text())

    def test_attribution_follows_the_journal_and_the_matrix_in_effect(self):
        self.assertEqual(self.attribute(), {"candidates": 5, "excluded": 1})
        record = json.loads((self.folder / "attribution.json").read_text())
        kinds = {row["idea_id"]: (row["lane"], row["file_kind"]) for row in record["candidates"]}
        self.assertEqual(kinds["first-idea"], (LANE, "skill"), "written before the switch, asked for a skill")
        self.assertEqual(kinds["second-idea"], (LANE, "harness_routing"))
        self.assertEqual(kinds["fourth-idea"], (OTHER_LANE, "skill"))
        self.assertEqual(record["excluded"], [{"lane": LANE, "file": "unjournaled-idea.md",
                                               "reason": "the journal records no write by this lane"}])
        self.assertEqual(record["lanes"][OTHER_LANE], {"family": "nvidia", "provider": "fixture-cloud",
                                                       "model": "other-model"})
        brief = json.loads((self.folder / "ideas" / "first-idea.json").read_text())
        self.assertEqual(brief["applicability"]["task_reference"], "Rotated task 0",
                         "the source is the brief the batch's selection gave the producer, not the raw record")
        self.assertEqual([matrix["selected"] for matrix in record["matrices"]], [5, 5])

    def test_a_matrix_whose_pinned_source_changed_is_refused(self):
        changed = {"record_type": "harness_idea_batch/v1", "ideas": [idea("first-idea", "skill")],
                   "sources": [{"kind": "onet_pinned", "path": "LICENSE", "sha256": "0" * 64}]}
        (self.root / "changed.json").write_text(json.dumps(changed))
        with self.assertRaisesRegex(adapter.ConversionError, "pinned_source_changed"):
            adapter.attribute(self.batch, [f"{self.root / 'changed.json'}@2026-09-24T04:00:00Z@1"], {LANE: "zhipu"},
                              self.folder)

    def test_a_matrix_without_its_selection_count_is_refused(self):
        with self.assertRaisesRegex(adapter.ConversionError, "matrix_declaration_invalid"):
            adapter.attribute(self.batch, [f"{self.root / 'early.json'}@2026-09-24T04:00:00Z"], {LANE: "zhipu"},
                              self.folder)

    def test_an_uncommitted_attribution_is_refused(self):
        self.attribute()
        with self.assertRaisesRegex(adapter.ConversionError, "attribution_not_committed"):
            self.proposals()

    def test_proposals_convert_placed_kinds_and_leave_out_the_rest_with_reasons(self):
        self.attribute()
        self.commit()
        (self.batch / "candidates" / OTHER_LANE / "fourth-idea.md").write_bytes(skill("fourth-idea", " Changed."))
        summary, batch, report = self.proposals()
        self.assertEqual(summary, {"converted": 2, "left_out": 3})
        placed = {row["id"]: (row["kind"], row["files"][0]["path"], row["producer"]["family"])
                  for row in batch["proposals"]}
        self.assertEqual(placed, {"first_idea": ("skill", "SKILL.md", "zhipu"),
                                  "second_idea": ("instruction_file", "AGENTS.md", "zhipu")})
        reasons = {row["idea_id"]: row["reason"] for row in report["left_out"]}
        self.assertIn("no qualified native placement", reasons["third-idea"])
        self.assertEqual(reasons["fourth-idea"], "the candidate bytes changed after attribution")
        self.assertEqual(reasons["secret-idea"], "the factory refuses it: native_secret_pattern_refused")
        self.assertEqual(batch["source_revision"], _git(self.repo, "rev-parse", "HEAD"))
        prepared = factory.prepare(factory.PreparationRequest(self.repo, self.repo / "proposals.json",
                                                              self.repo / "prepared", True))
        self.assertEqual(prepared["candidates"], 2, "the factory prepares every converted proposal together")


if __name__ == "__main__":
    unittest.main()
