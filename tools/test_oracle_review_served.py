"""The oracle second look over served items (roadmap package oracle-review), with no model call.

The fixture is a licensed import export of three packages, a reviewed Community folder the real writer wrote from
a real panel ledger, and a release bundle the real bundle tool wrote. The second look runs the real review panel
over a scripted fixture reviewer into a real ledger. Known-wrong cases: a reviewer of the producer's family is
never chosen, an unqualified reviewer is never asked, a same-family approval is not an upgrade candidate, and a
double-checked item is not sampled again.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src"), str(HERE.parent)]

import build_catalogue_release_bundle as bundle_tool  # noqa: E402
import oracle_review_served as oracle  # noqa: E402
import write_reviewed_catalogue as writer  # noqa: E402
from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines, imported, imported_profile, native  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.panel import PanelRunRequest, ReviewPanel  # noqa: E402
from candidate_review.reviewers import PROVIDER_REPORTED, ReviewerAttempt, Usage  # noqa: E402
from candidate_review.reviewers.fixture import FixtureReviewer  # noqa: E402
from test_candidate_review_imported import fixture, files_of  # noqa: E402
from test_write_reviewed_catalogue import fixture_panel, verdict_script  # noqa: E402

ROOT = HERE.parent
FIRST, SECOND = "fixture.reviewer", "fixture.second"
ORDER_LINE = re.compile(r"^(\d+)\. identity (\S+), body_sha256 ([0-9a-f]{64})$", re.MULTILINE)


def batch_script(decision):
    """A scripted reviewer that answers a batch prompt with one verdict for each candidate it lists."""
    def script(prompt, number):
        rows = []
        for _position, identity, digest in ORDER_LINE.findall(prompt.user):
            findings = ([{"criterion_id": "whole_package", "blocking": True, "text": "The recomputation is missing."}]
                        if decision == "reject" else [])
            rows.append({"identity": identity, "body_sha256": digest, "decision": decision, "findings": findings,
                         "reasons": "It fails its own check." if decision == "reject" else "Every criterion holds."})
        return ReviewerAttempt("answered", json.dumps({"verdicts": rows}), Usage(100, 20, source=PROVIDER_REPORTED), 1,
                               0.1, None, "fixture-model", "fixture")
    return script


BODIES = {
    "import_skill_alpha_fixture": ("skill", b"---\nname: alpha\ndescription: Review a change before it is merged.\n---\n\n"
                                   b"# Review diffs\n\nRead the whole diff, run the project's tests, and list each risk "
                                   b"with the line it comes from.\n"),
    "import_command_beta_fixture": ("command", b"---\nname: beta\ndescription: Summarise a failing build log.\n---\n\n"
                                    b"# Summarise the log\n\nOpen the newest log, keep the first failing step, quote its "
                                    b"last twenty lines and name the file it points at.\n"),
    "import_skill_gamma_fixture": ("skill", b"---\nname: gamma\ndescription: Write a release note from merged changes.\n"
                                   b"---\n\n# Release note\n\nList every merged title since the last tag, group them by "
                                   b"area, and write one plain sentence for each group.\n"),
}


def export(folder: Path) -> None:
    """Three imported packages in one export, each with its own bytes, identity and declared harness kind."""
    rows, specs = [], []

    def rename(identity, kind):
        def edit(records):
            row, spec = records["row"], records["spec"]
            row["reference"]["identity"] = identity
            row["body_path"], row["package_root"] = f"bodies/{identity}.package.json", f"packages/{identity}"
            spec.update(id=identity, body_path=row["body_path"], package_root=row["package_root"])
            spec["provenance"]["harness_kind"] = kind
            spec["provenance"]["store_record_id"] = "library.import." + identity
            rows.append(row)
            specs.append(spec)
        return edit

    for identity, (kind, body) in BODIES.items():
        fixture(folder, files=files_of(SKILL__md=(body, "text/markdown", "skill_definition")),
                edit=rename(identity, kind))
    items = json.loads((folder / "items.json").read_text())
    items["items"] = rows
    (folder / "items.json").write_text(json.dumps(items))
    (folder / "specifications-001.json").write_text(json.dumps({
        "record_type": native.NATIVE_SPECIFICATIONS, "population": 1, "populations": 1, "specifications": specs}))
    report = json.loads((folder / imported.EXPORT_FILE).read_text())
    report.update(items=len(rows), kinds={"skill": 2, "command": 1})
    (folder / imported.EXPORT_FILE).write_text(json.dumps(report))


class OracleReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.export = self.root / "batches" / "batch-fixture"
        self.export.mkdir(parents=True)
        export(self.export)
        self.panel_path = self.root / "panel.json"
        self.configuration = imported_profile.configuration(fixture_panel(self.panel_path))
        self.first_review()
        self.bundle = self.root / "bundles" / "daily-2026-09-26-fixture"
        self.assertEqual(bundle_tool.main(["--catalogue", str(self.reviewed), "--output", str(self.bundle),
                                           "--accept-license", "MIT", "--batch", "daily-fixture", "--write"]), 0)
        (self.root / "release-folders").mkdir()
        (self.root / "release-folders/reviewed-folders.txt").write_text(str(self.reviewed) + "\n")

    def first_review(self):
        """The daily job's review and writer: the first family approves every package."""
        criteria, instructions = imported_profile.resources()
        catalogue = imported.ImportedCatalogue.load(self.export, ROOT)
        first = self.configuration.installation(FIRST)
        panel = ReviewPanel(self.configuration, criteria, instructions,
                            {FIRST: FixtureReviewer(first, verdict_script("approve"))},
                            engines.build_precheck_engines(self.configuration), ReviewLedger(self.root / "daily-ledger.jsonl"))
        requests = tuple(catalogue.request(identity, catalogue.producer_for(identity), criteria, instructions.sha256)
                         for identity in BODIES)
        panel.run(PanelRunRequest(run_id="daily-1", requests=requests, population=catalogue.population_bodies(),
                                  call_ceiling=6, token_ceiling=1_000_000, model_calls_authorized=True, fixture_run=True,
                                  collect_below_quorum_reason="one family in this check"))
        self.reviewed = self.root / "reviewed" / "imported"
        summary = writer.write(argparse.Namespace(
            repository=ROOT, panel=self.panel_path, catalogue=self.export, ledger=[str(self.root / "daily-ledger.jsonl")],
            reviewer=[FIRST], tier="community", output=self.reviewed, recorded_at="2026-09-26", allow_fixture=True,
            scan_record=[], identities_file=None))
        self.assertEqual((summary["approved"], summary["rejected"]), (3, 0))

    def calibrate(self, *reviewers, status="qualified"):
        folder = self.root / "daily" / "2026-09-26-10"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "calibration.json").write_text(json.dumps({
            "reports": {"mixed_batch_of_12": {"installations": {name: {"status": status} for name in reviewers}}}}))

    def options(self, *reviewers, panel=None, **extra) -> argparse.Namespace:
        library = self.root / "library"
        values = {"bundles_root": self.root / "bundles", "bundle": None, "library": library,
                  "reviewed_folders_file": self.root / "release-folders/reviewed-folders.txt", "reviewed_folder": [],
                  "candidate_root": [self.root / "batches"], "ledger": library / "oracle/review-ledger.jsonl",
                  "withdrawals": library / "oracle/withdrawals", "upgrades": library / "oracle/upgrades",
                  "runs": library / "oracle/runs", "calibration_root": self.root / "daily", "calibration_hours": 36.0,
                  "panel": panel or self.panel_path, "reviewer": list(reviewers) or [SECOND], "second_family_only": False,
                  "sample": 24, "set_aside_after": 3, "call_ceiling": 8, "token_ceiling": 4_000_000,
                  "group_timeout_seconds": 60.0, "authorize_model_calls": True, "run_id": "", "repository": ROOT,
                  "python": sys.executable, "campaign": oracle.CAMPAIGN}
        values.update(extra)
        return argparse.Namespace(**values)

    def second_look(self, decision="approve", *reviewers, panel=None, run_id="", **extra) -> dict:
        scripts = {name: batch_script(decision) for name in (FIRST, SECOND)}
        call = oracle.PanelReviewCall(panel or self.panel_path, ROOT, fixture_scripts=scripts, authorized=True)
        return oracle.run(self.options(*reviewers, panel=panel, run_id=run_id, **extra), review_call=call,
                          now=datetime.now(timezone.utc))

    def ledger_rows(self) -> list:
        path = self.root / "library/oracle/review-ledger.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []

    def test_the_sample_takes_the_oldest_first_and_every_kind_in_turn(self):
        entries = [{"sort": ("2026-09-25", 0, index), "kind": "skill", "name": f"skill-{index}"} for index in range(4)]
        entries += [{"sort": ("2026-09-26", 1, index), "kind": "command", "name": f"command-{index}"} for index in range(2)]
        entries += [{"sort": ("2026-09-24", 0, 0), "kind": "agent", "name": "agent-0"}]
        chosen = [entry["name"] for entry in oracle.sample(entries, 5)]
        self.assertEqual(chosen, ["agent-0", "skill-0", "command-0", "skill-1", "command-1"])
        self.assertEqual(len(oracle.sample(entries, 100)), 7)

    def test_a_reviewer_of_the_producer_family_is_never_chosen(self):
        installations = self.configuration.installations
        by_id = {item.installation_id: item for item in installations}
        chosen, second = oracle.choose_reviewer([by_id[SECOND], by_id[FIRST]], "google", set())
        self.assertEqual((chosen.installation_id, second), (FIRST, True))
        # Every reviewer is of the producer's family: nobody is chosen, whatever the record says.
        self.assertEqual(oracle.choose_reviewer([by_id[SECOND]], "google", set()), (None, False))
        # A family already on record comes after a new family, and is refused when only a new family may look.
        chosen, second = oracle.choose_reviewer([by_id[FIRST], by_id[SECOND]], "upstream_author", {"anthropic"})
        self.assertEqual((chosen.installation_id, second), (SECOND, True))
        chosen, second = oracle.choose_reviewer([by_id[FIRST]], "upstream_author", {"anthropic"})
        self.assertEqual((chosen.installation_id, second), (FIRST, False))
        self.assertEqual(oracle.choose_reviewer([by_id[FIRST]], "upstream_author", {"anthropic"}, False), (None, False))

    def test_a_second_family_approval_writes_an_upgrade_candidate_and_the_ledger(self):
        self.calibrate(SECOND)
        report = self.second_look("approve", SECOND)
        self.assertEqual((report["served"], len(report["sampled"]), report["stop_reason"]), (3, 3, "completed"))
        self.assertEqual([entry["kind"] for entry in report["sampled"]], ["skill", "command", "skill"])
        self.assertEqual(report["verdicts"], {"approve": 3, "reject": 0, "none": 0})
        self.assertEqual(len(report["upgrade_candidates"]), 3)
        self.assertEqual(report["withdrawal_candidates"], [])
        rows = self.ledger_rows()
        self.assertEqual(len(rows), 3)
        row = rows[0]
        self.assertEqual((row["record_type"], row["reviewer"], row["family"], row["verdict"], row["second_family"]),
                         (oracle.LEDGER_ROW, SECOND, "google", "approve", True))
        # The fixture's criteria did not change between the two reviews, so the request digests agree.
        self.assertEqual((row["same_criteria_as_first_review"], row["first_review_request_sha256"]),
                         (True, row["request_sha256"]))
        self.assertTrue(row["call_ref"].startswith("group-1-ledger.jsonl#oracle-review-"))
        served = {line["reference"]["identity"]: line["reference"]["digest"]
                  for line in map(json.loads, (self.bundle / "items.jsonl").read_text().splitlines())}
        self.assertEqual(row["digest"], served[row["identity"]])
        upgrade = json.loads(Path(report["upgrade_candidates"][0]).read_text())
        self.assertEqual(upgrade["record_type"], oracle.UPGRADE_RECORD)
        self.assertEqual(upgrade["families"], ["anthropic", "google"])
        self.assertEqual([review["decision"] for review in upgrade["reviews"]], ["approve", "approve"])
        self.assertEqual(upgrade["reviews"][0]["ledger"], str(self.root / "daily-ledger.jsonl"))
        # The next run samples nothing: every served digest is double-checked.
        again = self.second_look("approve", SECOND, run_id="oracle-again")
        self.assertEqual((len(again["sampled"]), again["skipped"]), (0, {"already_double_checked": 3}))
        self.assertEqual(len(self.ledger_rows()), 3)

    def test_a_rejection_writes_a_withdrawal_candidate_that_names_the_reviewer_and_reasons(self):
        self.calibrate(SECOND)
        report = self.second_look("reject", SECOND, sample=1)
        self.assertEqual((len(report["sampled"]), report["verdicts"]), (1, {"approve": 0, "reject": 1, "none": 0}))
        self.assertEqual(report["sampled"][0]["identity"], "import_skill_alpha_fixture")
        [path] = report["withdrawal_candidates"]
        record = json.loads(Path(path).read_text())
        self.assertTrue(path.startswith(str(self.root / "library/oracle/withdrawals/import_skill_alpha_fixture--")))
        self.assertEqual(record["record_type"], oracle.WITHDRAWAL_RECORD)
        self.assertEqual((record["decision"], record["reasons"], record["status"]),
                         ("reject", "It fails its own check.", "candidate"))
        self.assertEqual(record["reviewer"], {"installation_id": SECOND, "family": "google", "model": "fixture-model"})
        self.assertEqual(record["first_review"][0]["reviewer_id"], FIRST)
        self.assertEqual(record["findings"][0]["criterion_id"], "whole_package")
        self.assertEqual(record["tier"], "community")
        [row] = self.ledger_rows()
        self.assertEqual((row["verdict"], row["withdrawal_candidate"], row["upgrade_candidate"]), ("reject", path, ""))
        self.assertEqual(report["upgrade_candidates"], [])

    def test_a_same_family_second_look_is_recorded_without_an_upgrade_candidate(self):
        self.calibrate(FIRST)
        report = self.second_look("approve", FIRST, sample=2)
        self.assertEqual(report["verdicts"]["approve"], 2)
        self.assertEqual(report["upgrade_candidates"], [])
        self.assertEqual({row["second_family"] for row in self.ledger_rows()}, {False})
        # With only a new family allowed, the same family is not chosen at all.
        strict = self.second_look("approve", FIRST, run_id="oracle-strict", second_family_only=True)
        self.assertEqual((len(strict["sampled"]), strict["skipped"]["no_eligible_reviewer"]), (0, 1))

    def test_an_unqualified_reviewer_is_not_asked_and_nothing_is_written(self):
        report = self.second_look("reject", SECOND)
        self.assertEqual(report["skipped"], {"reviewer_not_qualified_recently": 3})
        self.assertEqual((report["calls"], self.ledger_rows(), report["withdrawal_candidates"]), (0, [], []))
        self.calibrate(SECOND, status="calibration_incomplete")
        report = self.second_look("reject", SECOND, run_id="oracle-incomplete")
        self.assertEqual(report["skipped"], {"reviewer_not_qualified_recently": 3})
        self.assertEqual(self.ledger_rows(), [])
        # A qualification older than the window does not count.
        self.calibrate(SECOND)
        old = self.second_look("reject", SECOND, run_id="oracle-old", calibration_hours=0.0)
        self.assertEqual(old["skipped"], {"reviewer_not_qualified_recently": 3})

    def test_a_precheck_refusal_writes_a_withdrawal_candidate_with_no_call(self):
        self.calibrate(SECOND)
        # The rules changed since publication: a secret pattern now matches the alpha package's own words.
        stricter = json.loads(self.panel_path.read_text())
        stricter["precheck_engines"]["builtin_secret_patterns"]["extra_patterns"].append("Read the whole diff")
        stricter_path = self.root / "panel-stricter.json"
        stricter_path.write_text(json.dumps(stricter))
        report = self.second_look("approve", SECOND, panel=stricter_path)
        self.assertEqual(report["precheck_refusals"], 1)
        self.assertEqual(report["verdicts"], {"approve": 2, "reject": 1, "none": 0})
        refused = [row for row in self.ledger_rows() if row["reviewer"] == oracle.PRECHECKS]
        self.assertEqual(len(refused), 1)
        self.assertEqual((refused[0]["identity"], refused[0]["verdict"], refused[0]["family"]),
                         ("import_skill_alpha_fixture", "reject", "deterministic"))
        record = json.loads(Path(refused[0]["withdrawal_candidate"]).read_text())
        self.assertEqual(record["decision"], "precheck_refused")
        self.assertIn("secret", record["reasons"])
        # The refused item was not in the identities the panel was asked about.
        asked = (self.root / "library/oracle/runs" / report["run_id"] / "group-1-identities.txt").read_text().split()
        self.assertEqual(sorted(asked), ["import_command_beta_fixture", "import_skill_gamma_fixture"])

    def test_without_model_call_authority_the_run_only_reports_the_sample(self):
        self.calibrate(SECOND)
        report = self.second_look("reject", SECOND, authorize_model_calls=False)
        self.assertEqual((len(report["sampled"]), report["stop_reason"]), (3, "model_calls_not_authorized"))
        self.assertEqual((self.ledger_rows(), report["withdrawal_candidates"]), ([], []))

    def test_the_campaign_command_names_the_reviewer_and_excludes_every_other_installation(self):
        call = oracle.CampaignReviewCall(ROOT, "python", oracle.CAMPAIGN, authorized=True)
        panel = self.configuration
        exclusions = oracle.exclusions_for(panel, SECOND)
        self.assertEqual(exclusions, {FIRST: oracle.NOT_THE_REVIEWER})
        command = call.command("CAT", "ids.txt", SECOND, exclusions, "ledger.jsonl", "out.json", 3, 4_000_000, 3)
        self.assertEqual(command[1:3], [str(oracle.CAMPAIGN), "review"])
        self.assertIn("--authorize-model-calls", command)
        self.assertEqual(command[command.index("--reviewer") + 1], SECOND)
        self.assertEqual(command[command.index("--batch-size") + 1], "12")
        self.assertEqual(command[command.index("--exclude-installation") + 1], f"{FIRST}={oracle.NOT_THE_REVIEWER}")
        self.assertNotIn("--authorize-model-calls",
                         oracle.CampaignReviewCall(ROOT, "python", oracle.CAMPAIGN).command(
                             "CAT", "ids.txt", SECOND, exclusions, "l", "o", 3, 4, 3))
        # The real panel: every enabled installation but the Tactical reviewer is excluded, as the daily job does.
        real = oracle.exclusions_for(config.PanelConfiguration.from_dict(json.loads(oracle.PANEL.read_text())),
                                     oracle.DEFAULT_REVIEWER)
        self.assertIn("claude_code.subscription", real)
        self.assertNotIn(oracle.DEFAULT_REVIEWER, real)

    def test_the_oracle_ledger_refuses_a_foreign_row(self):
        path = self.root / "foreign.jsonl"
        path.write_text(json.dumps({"record_type": "something_else/v1"}) + "\n")
        with self.assertRaisesRegex(oracle.OracleError, "oracle_ledger_row_unknown"):
            oracle.OracleLedger(path)
        ledger = oracle.OracleLedger(self.root / "new.jsonl")
        with self.assertRaisesRegex(oracle.OracleError, "oracle_ledger_row_unknown"):
            ledger.append({"record_type": "something_else/v1"})


if __name__ == "__main__":
    unittest.main()
