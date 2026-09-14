"""Source-freeze controls using temporary declared inputs, never task data."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from embodiment_lab.campaign_sources import (
    SourceIdentityError, TaskSourceAvailability, TaskSourceSnapshot,
    snapshot_available_task_sources, snapshot_task_sources,
    verify_available_task_sources, verify_task_sources)


class CampaignSourceChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="campaign-source-check-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.task = self.root / "tasks" / "example"
        self.task.mkdir(parents=True)
        self.data = self.root / "data"
        self.data.mkdir()
        (self.data / "rows.txt").write_text("source rows")
        (self.data / ".metadata").write_text("hidden source metadata")
        (self.task / "task.md").write_text("Use the supplied dataset.")
        (self.task / "attachment.txt").write_text("original attachment")
        self.declaration = {"id": "example", "attachments": ["attachment.txt"],
                            "data_path": "../../data"}
        self.write_declaration()

    def write_declaration(self):
        (self.task / "task.json").write_text(json.dumps(self.declaration))

    def freeze(self):
        return snapshot_task_sources(self.task, self.root)

    def test_all_declared_bytes_and_hidden_directory_members_are_bound(self):
        frozen = self.freeze()
        self.assertEqual(verify_task_sources(self.task, self.root, frozen), frozen)
        self.assertIn("data/.metadata", [row[0] for row in frozen.entries])
        self.assertEqual(TaskSourceSnapshot.from_dict(frozen.to_dict()), frozen)

    def test_mutating_dataset_attachment_or_brief_invalidates_freeze(self):
        for path in (self.data / "rows.txt", self.task / "attachment.txt", self.task / "task.md"):
            with self.subTest(path=path.name):
                frozen = self.freeze()
                path.write_text("changed contents")
                with self.assertRaises(SourceIdentityError):
                    verify_task_sources(self.task, self.root, frozen)

    def test_membership_changes_and_empty_directories_invalidate_freeze(self):
        for name, directory in (("added.txt", False), ("empty", True)):
            frozen = self.freeze()
            path = self.data / name
            path.mkdir() if directory else path.write_text("added")
            with self.assertRaises(SourceIdentityError):
                verify_task_sources(self.task, self.root, frozen)

    def test_task_metadata_does_not_hide_changed_inputs(self):
        frozen = self.freeze()
        before = (self.task / "task.json").read_bytes()
        (self.data / "rows.txt").write_text("different rows with unchanged task identity")
        self.assertEqual(before, (self.task / "task.json").read_bytes())
        self.assertNotEqual(self.freeze().content_digest, frozen.content_digest)

    def test_nested_symbolic_links_and_special_files_refuse(self):
        link = self.data / "alias"
        link.symlink_to(self.data / "rows.txt")
        with self.assertRaises(SourceIdentityError):
            self.freeze()
        link.unlink()
        os.mkfifo(self.data / "pipe")
        with self.assertRaises(SourceIdentityError):
            self.freeze()

    def test_declared_root_can_resolve_only_within_database(self):
        alias = self.task / "data-alias"
        alias.symlink_to(self.data, target_is_directory=True)
        self.declaration["data_path"] = "data-alias"
        self.write_declaration()
        self.assertIn("data", self.freeze().roots)
        self.declaration["data_path"] = "../../../"
        self.write_declaration()
        with self.assertRaises(SourceIdentityError):
            self.freeze()

    def test_unrelated_source_is_not_implicitly_loaded(self):
        frozen = self.freeze()
        (self.root / "unrelated.txt").write_text("not an input")
        self.assertEqual(self.freeze(), frozen)

    def test_cache_is_scoped_and_changes_are_not_reused(self):
        cache = {}
        first = snapshot_task_sources(self.task, self.root, cache=cache)
        self.assertEqual(first, snapshot_task_sources(self.task, self.root, cache=cache))
        (self.data / "rows.txt").write_text("changed rows")
        self.assertNotEqual(first, snapshot_task_sources(self.task, self.root, cache=cache))

    def test_foreign_version_and_unknown_fields_refuse(self):
        record = self.freeze().to_dict()
        for change in ({"version": "9.0.0"}, {"trust_me": True}):
            with self.assertRaises(SourceIdentityError):
                TaskSourceSnapshot.from_dict({**record, **change})

    def test_missing_declared_source_is_frozen_as_a_gap_not_an_empty_task(self):
        self.declaration["attachments"].append("missing.txt")
        self.write_declaration()
        with self.assertRaises(FileNotFoundError):
            snapshot_task_sources(self.task, self.root)
        availability = snapshot_available_task_sources(self.task, self.root)
        relative = (self.task / "missing.txt").relative_to(self.root).as_posix()
        self.assertFalse(availability.complete)
        self.assertEqual(availability.missing, ((relative, "not_found"),))
        self.assertIn(
            "tasks/example/attachment.txt",
            [entry[0] for entry in availability.available.entries])
        restored = TaskSourceAvailability.from_dict(availability.to_dict())
        self.assertEqual(restored, availability)
        self.assertEqual(
            verify_available_task_sources(self.task, self.root, restored),
            availability)
        (self.task / "missing.txt").write_text("arrived later")
        with self.assertRaises(SourceIdentityError):
            verify_available_task_sources(self.task, self.root, restored)


if __name__ == "__main__":
    unittest.main()
