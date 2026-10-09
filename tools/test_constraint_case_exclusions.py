"""Cross-run novelty controls: exclude known jobs before grouping, bind exact snapshots."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from tools.test_constraint_case_factory import parent_run, LICENSE, REVISION
from supply_lines import constraint_case_exclusions as exclusions
from supply_lines import constraint_case_run as runner
from supply_lines import constraint_case_runtime as runtime


class ExclusionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.parent, _ = parent_run(self.root)
        self.args = SimpleNamespace(parent_run=[self.parent], run_folder=self.root / "first", maximum_contracts=1,
            maximum_cases=1000, maximum_candidate_bytes=64 * 1024 * 1024, batch_size=1, maximum_seconds=60,
            authorize_output_writes=True)

    def run_cases(self, args):
        return runner.run(args, revision=REVISION, licence_text=LICENSE, generator_digest="a" * 64)

    def test_existing_jobs_are_not_repackaged_under_new_names(self):
        first = self.run_cases(self.args)
        path = self.root / "known.json"
        exclusions.write(path, exclusions.snapshot(sorted((self.args.run_folder / "packages").iterdir())))
        second_args = SimpleNamespace(**{**vars(self.args), "run_folder": self.root / "second", "exclude_case_jobs": path})
        second = self.run_cases(second_args)
        self.assertEqual(second["case_jobs"], 0)
        self.assertEqual(second["groups"], 0)
        self.assertEqual(second["accounting"]["case_jobs_previously_known"], first["case_jobs"])
        self.assertEqual(second["excluded_known_case_jobs"], first["case_jobs"])

    def test_changed_exclusion_snapshot_refuses_resume(self):
        self.run_cases(self.args)
        path = self.root / "known.json"
        record = exclusions.snapshot(sorted((self.args.run_folder / "packages").iterdir()))
        exclusions.write(path, record)
        args = SimpleNamespace(**{**vars(self.args), "run_folder": self.root / "second", "exclude_case_jobs": path})
        self.run_cases(args)
        changed = deepcopy(record)
        changed["job_ids"].pop()
        path.write_bytes(runtime.encode(changed))
        with self.assertRaisesRegex(ValueError, "resume_plan_changed"):
            self.run_cases(args)

    def test_shards_bind_complete_parent_population_and_do_not_overlap(self):
        next_root = self.root / "other"
        next_root.mkdir()
        other, _ = parent_run(next_root, schema={"type": "integer", "minimum": 1}, baselines=[2])
        base = {**vars(self.args), "parent_run": [self.parent, other], "maximum_contracts": 2, "parent_limit": 1}
        first = self.run_cases(SimpleNamespace(**{**base, "run_folder": self.root / "shard-a", "parent_offset": 0}))
        second = self.run_cases(SimpleNamespace(**{**base, "run_folder": self.root / "shard-b", "parent_offset": 1}))
        self.assertEqual(first["parent_population"], 2)
        self.assertEqual(first["source_contracts"], 1)
        one = runtime.decode((self.root / "shard-a/run.json").read_bytes(), maximum=8 * 1024 * 1024)["plan"]
        two = runtime.decode((self.root / "shard-b/run.json").read_bytes(), maximum=8 * 1024 * 1024)["plan"]
        self.assertEqual(one["parent_selection"]["population_sha256"], two["parent_selection"]["population_sha256"])
        self.assertNotEqual(one["inputs"][0]["record_id"], two["inputs"][0]["record_id"])
        self.assertTrue(first["complete"] and second["complete"])

    def test_bad_exclusion_contract_duplicate_jobs_and_alias_refuse(self):
        record = {"record_type": exclusions.RECORD_TYPE, "job_ids": [], "sources": []}
        for changed in ({**record, "extra": True}, {**record, "job_ids": ["not-a-job"]},
                        {**record, "job_ids": ["a" * 64, "a" * 64]}):
            with self.assertRaises(ValueError):
                exclusions.validate(changed)
        target = self.root / "known.json"
        exclusions.write(target, record)
        alias = self.root / "alias.json"
        alias.symlink_to(target)
        with self.assertRaises(ValueError):
            exclusions.read(alias)

    def test_source_member_alias_is_not_followed_for_a_snapshot(self):
        self.run_cases(self.args)
        folder = next((self.args.run_folder / "packages").iterdir())
        member = folder / "README.md"
        outside = self.root / "outside-readme.md"
        outside.write_bytes(member.read_bytes())
        member.unlink()
        member.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            exclusions.snapshot([folder])


if __name__ == "__main__":
    unittest.main()
