"""Counting checks for tools/inventory_harness_library.py on fixture folders.

Each test builds a small fixture tree in a temporary folder. Each one also
states the known-wrong answer that a shortcut would give: counting candidate
files on disk instead of journaled outcomes, taking a kind from a file name,
trusting the oldest pre-check report, defaulting an unknown kind to skill, or
summing units across sources without deduplicating identities.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import inventory_harness_library as inventory  # noqa: E402


def write(path: Path, content: object) -> str:
    """Write text or JSON and return the sha256 of the bytes written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = content if isinstance(content, str) else json.dumps(content)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_source(name: str, units: list) -> inventory.Source:
    return inventory.Source(
        name=name, label=name, scope="requested", library=True, roots=[],
        unit_definition="fixture", kind_basis="fixture", state_basis="fixture", units=units)


def make_unit(identity: str, kind: str, state: str, aliases: tuple = ()) -> inventory.Unit:
    return inventory.Unit(identity=identity, kind=kind, kind_value="fixture", state=state,
                          state_detail="fixture", files=[], aliases=aliases)


class OvernightBatchCounting(unittest.TestCase):
    def test_counts_journaled_candidates_not_files_on_disk(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch = root / "batch"
            events = [
                {"event": "dispatch", "idea_id": "idea-a", "lane_id": "lane-x"},
                {"event": "outcome", "idea_id": "idea-a", "lane_id": "lane-x",
                 "outcome": "candidate_written"},
                {"event": "outcome", "idea_id": "idea-b", "lane_id": "lane-x",
                 "outcome": "failed_candidate_shape"},
                {"event": "outcome", "idea_id": "idea-c", "lane_id": "lane-y",
                 "outcome": "candidate_written"},
            ]
            journal = "".join(json.dumps(event) + "\n" for event in events)
            # The batch is still writing this line: valid JSON, no newline yet.
            journal += json.dumps({"event": "outcome", "idea_id": "idea-d", "lane_id": "lane-x",
                                   "outcome": "candidate_written"})
            write(batch / "journal.jsonl", journal)
            for lane, idea in (("lane-x", "idea-a"), ("lane-y", "idea-c"),
                               ("lane-x", "idea-d"), ("lane-x", "idea-z")):
                write(batch / "candidates" / lane / f"{idea}.md", f"---\nname: {idea}\n---\n")
            write(root / "matrix.json", {"ideas": [
                {"id": "idea-a", "file_kind": "skill"},
                {"id": "idea-c", "file_kind": "subagent"},
                {"id": "idea-d", "file_kind": "skill"},
                {"id": "idea-z", "file_kind": "skill"},
            ]})

            source = inventory.read_overnight_batch(batch, root / "matrix.json")

            markdown_files_on_disk = 4
            self.assertNotEqual(len(source.units), markdown_files_on_disk)  # known-wrong count
            self.assertEqual(sorted(unit.identity for unit in source.units), ["idea-a", "idea-c"])
            self.assertEqual(Counter(unit.kind for unit in source.units),
                             Counter({"skill": 1, "subagent definition": 1}))
            self.assertEqual({unit.state for unit in source.units}, {"candidate"})
            self.assertEqual(source.attempts["failed_candidate_shape"], 1)
            self.assertEqual(source.extra["candidate_files_on_disk_without_a_journaled_outcome"], 2)
            self.assertGreater(source.extra["journal_snapshot"]["bytes_after_last_complete_line"], 0)


class WaveFiveCounting(unittest.TestCase):
    def make_package(self, folder: Path, assignment: str, identity: str, file_class: str,
                     files: dict[str, str]) -> None:
        package = folder / "packages" / assignment / identity
        declared = [{"path": relative, "digest": write(package / "payload" / relative, content)}
                    for relative, content in files.items()]
        write(package / "package.json", {
            "record_type": "wave5_candidate_package/v1",
            "proposal": {"id": identity, "files": declared, "producer": {"family": "anthropic"}},
            "wave5": {"assignment_id": assignment, "file_class": file_class,
                      "package_digest": f"fixture-{identity}"},
        })

    def test_kind_comes_from_the_record_and_state_from_the_newest_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "wave-5"
            # The hook package carries a file named SKILL.md; its record says hook.
            self.make_package(folder, "a04_hooks", "guard_writes", "hook_with_script",
                              {"SKILL.md": "not the entry\n", "hooks/guard.py": "print(1)\n"})
            self.make_package(folder, "a01_tools", "flag_outliers", "skill_with_scripts_and_tests",
                              {"SKILL.md": "---\nname: flag-outliers\n---\n"})
            write(folder / "reports" / "precheck-all-20260924T010000000000Z.json", {
                "checked_at": "2026-09-24T01:00:00+00:00",
                "passed_for_wave_gate": ["guard_writes", "flag_outliers"], "refused": []})
            write(folder / "reports" / "precheck-all-20260924T020000000000Z.json", {
                "checked_at": "2026-09-24T02:00:00+00:00",
                "passed_for_wave_gate": ["flag_outliers"], "refused": ["guard_writes"]})
            write(folder / "packages" / "a04_hooks" / "guard_writes" / "review"
                  / "precheck-20260924T020000000000Z.json",
                  {"passed_for_wave_gate": False, "refused": True})
            write(folder / "packages" / "a01_tools" / "flag_outliers" / "review"
                  / "precheck-20260924T020000000000Z.json",
                  {"passed_for_wave_gate": True, "refused": False})

            units = {unit.identity: unit for unit in inventory.read_wave5(folder).units}

            self.assertNotEqual(units["guard_writes"].kind, "skill")  # known-wrong: file name
            self.assertEqual(units["guard_writes"].kind, "hook")
            self.assertEqual(units["flag_outliers"].kind, "skill")
            self.assertNotEqual(units["guard_writes"].state, "passed a precheck")  # oldest report
            self.assertEqual(units["guard_writes"].state, "refused by a precheck")
            self.assertEqual(units["flag_outliers"].state, "passed a precheck")
            self.assertEqual(sum(len(unit.files) for unit in units.values()), 3)

    def test_an_unmapped_declared_value_stays_unknown(self):
        self.assertEqual(inventory.map_kind("wave 5 file class", "a_class_nobody_mapped"), "unknown")
        self.assertEqual(inventory.map_kind("idea file kind", None), "unknown")
        self.assertEqual(inventory.map_kind("proposal family", "original_native_hook"), "hook")


class TotalsDeduplication(unittest.TestCase):
    def test_an_identity_in_two_sources_counts_once(self):
        first = make_source("first", [
            make_unit("flag-outliers", "skill", "candidate"),
            make_unit("only-in-first", "skill", "candidate"),
        ])
        second = make_source("second", [
            make_unit("flag_outliers", "tool or script", "passed a precheck"),
        ])

        totals = inventory.aggregate([first, second])

        self.assertEqual(totals["units_sum"], 3)
        self.assertNotEqual(totals["distinct_identities"], 3)  # known-wrong: summed sources
        self.assertEqual(totals["distinct_identities"], 2)
        self.assertEqual(totals["overlap_count"], 1)
        counted = totals["overlaps"][0]["counted_as"]
        self.assertEqual((counted["source"], counted["state"]), ("second", "passed a precheck"))
        self.assertEqual(totals["by_state_deduplicated"]["candidate"], 1)
        self.assertEqual(totals["by_state_deduplicated"]["passed a precheck"], 1)

    def test_a_declared_alias_joins_two_names(self):
        fixture = make_source("fixture", [
            make_unit("focused_brief_plugin", "plugin manifest", "candidate",
                      aliases=("baltor-focused-brief-candidate",)),
        ])
        original = make_source("original", [
            make_unit("baltor-focused-brief-candidate", "plugin manifest", "candidate"),
        ])

        totals = inventory.aggregate([fixture, original])

        self.assertEqual(totals["distinct_identities"], 1)
        self.assertEqual(totals["overlap_count"], 1)


if __name__ == "__main__":
    unittest.main()
