"""The kaggle_public_good supply line: the local profiler, the SDG rules, the licence decisions, and one synthetic
download end to end through every qualification check on the exact built bytes (the sandbox and mutation checks
when bubblewrap is available).

Known-wrong controls: a dataset under ODbL, one under CC BY-SA, one that asks for permission, one with no licence
signal, one whose signals disagree, one with mixed terms and no declaration, and a stale declaration are each held by
name; a licensable dataset with no table is held as no_table; a rule naming a target of another goal is refused; a
package whose test cannot fail is refused by the mutation check.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tools", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from supply_lines import kaggle_profile as profile  # noqa: E402
from supply_lines import kaggle_public_good as line  # noqa: E402
from supply_lines import kaggle_sdg as sdg  # noqa: E402
from supply_lines.records import KAGGLE_PUBLIC_GOOD, read_supply_candidate  # noqa: E402
from tools.component_qualification import checks, components  # noqa: E402
from tools.component_qualification.sandbox import SandboxSettings  # noqa: E402

REVISION = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
SANDBOX = SandboxSettings()
HAS_SANDBOX = bool(REVISION) and SANDBOX.works()
CC_BY_STATEMENT = "Creative Commons Attribution 4.0 International (CC BY 4.0)\n\nRows authored by the example project.\n"
MIT_TEXT = (ROOT / "LICENSE").read_text(encoding="utf-8")


def write(folder: Path, name: str, text: str) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def csv_text(header, rows, delimiter=",") -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=delimiter, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


class ProfilerTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.folder)

    def test_cell_kinds_keep_leading_zeros_and_check_dates(self):
        expected = {"7": profile.INTEGER, "-12": profile.INTEGER, "007": profile.TEXT, "7.5": profile.NUMBER,
                    "1e3": profile.NUMBER, "0.25": profile.NUMBER, "01.5": profile.TEXT, "true": profile.BOOLEAN,
                    "FALSE": profile.BOOLEAN, "2026-01-05": profile.DATE, "2026-02-30": profile.TEXT,
                    "2026-01-05T10:00:00Z": profile.DATE_TIME, "2026-01-05 10:00": profile.DATE_TIME,
                    "nan": profile.TEXT, "inf": profile.TEXT, "02134": profile.TEXT}
        for text, kind in expected.items():
            self.assertEqual(profile.cell_kind(text), kind, text)

    def test_column_type_is_the_narrowest_covering_type(self):
        self.assertEqual(profile.column_type({profile.INTEGER: 3, profile.NUMBER: 1}), profile.NUMBER)
        self.assertEqual(profile.column_type({profile.DATE: 3, profile.DATE_TIME: 1}), profile.DATE_TIME)
        self.assertEqual(profile.column_type({profile.BOOLEAN: 1, profile.INTEGER: 1}), profile.TEXT)
        self.assertEqual(profile.column_type({}), profile.EMPTY_COLUMN)

    def test_delimited_file_counts_quoted_newlines_as_one_record_and_digests_every_byte(self):
        text = "﻿id;note;amount\n1;\"two\nlines\";3.5\n2;;4\n3;plain;x\n"
        path = write(self.folder, "a.csv", text)
        table, digest, size = profile.profile_delimited(path)
        self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(size, len(path.read_bytes()))
        self.assertEqual((table["delimiter"], table["records"], table["encoding"]), (";", 3, "utf-8 with byte-order mark"))
        columns = {column["name"]: column for column in table["columns"]}
        self.assertEqual(columns["id"]["type"], profile.INTEGER)
        self.assertEqual(columns["note"]["empty"], 1)
        self.assertEqual(columns["amount"]["type"], profile.TEXT)  # "x" is not a number
        self.assertEqual(columns["id"]["minimum"], 1)

    def test_the_profile_bound_limits_statistics_but_not_the_record_count(self):
        rows = [[number, "v"] for number in range(5000)]
        path = write(self.folder, "big.csv", csv_text(["n", "v"], rows))
        table, _digest, _size = profile.profile_delimited(path, profile_bytes=1)
        self.assertEqual(table["records"], 5000)
        self.assertLess(table["profiled_records"], 5000)
        self.assertIn("first", table["profile_basis"])

    def test_known_wrong_a_saved_web_page_and_a_ragged_table(self):
        page = write(self.folder, "page.csv", "<html><body>Not found</body></html>\n")
        self.assertEqual(profile.profile_delimited(page)[0]["format"], profile.WEB_PAGE)
        ragged = write(self.folder, "ragged.csv", "a,b,c\n1,2,3\n1,2\n4,5,6\n")
        table = profile.profile_delimited(ragged)[0]
        self.assertEqual(table["ragged_records"], 1)
        self.assertIsNotNone(line.rectangular_problem(table))

    def test_json_lines_count_absent_keys_apart_from_nulls(self):
        path = write(self.folder, "rows.jsonl", '{"a": 1, "b": null}\n{"a": 2}\n\n{"a": 3, "b": "x"}\n')
        table = profile.profile_json_lines(path)[0]
        columns = {column["name"]: column for column in table["columns"]}
        self.assertEqual(table["records"], 3)
        self.assertEqual((columns["b"]["present"], columns["b"]["empty"], columns["b"]["absent"]), (1, 1, 1))
        self.assertEqual(columns["a"]["type"], profile.INTEGER)

    def test_dataset_profile_lists_files_with_formats_and_digests(self):
        write(self.folder, "LICENSE", "x\n")
        write(self.folder, "t.csv", "a\n1\n")
        record = profile.profile_dataset(self.folder)
        formats = {row["path"]: row["format"] for row in record["files"]}
        self.assertEqual(formats, {"LICENSE": profile.DOCUMENT, "t.csv": profile.DELIMITED})
        self.assertEqual(len(record["tables"]), 1)


class SdgRuleTests(unittest.TestCase):
    def setUp(self):
        self.rules = sdg.read_rules(line.SDG_RULES_FILE)

    def test_every_rule_names_targets_of_its_goals_and_a_reason(self):
        vocabulary = sdg.vocabulary_targets()
        for rule in self.rules["rules"]:
            for target in rule["targets"]:
                self.assertIn(vocabulary[target][0], rule["goals"], rule["id"])
            self.assertTrue(rule["reason"])

    def test_known_wrong_a_target_of_another_goal_or_a_stray_indicator_is_refused(self):
        record = json.loads(line.SDG_RULES_FILE.read_text(encoding="utf-8"))
        folder = Path(tempfile.mkdtemp())
        try:
            for change in ({"targets": ["16.1"]}, {"indicators": ["9.c.1"]}, {"fields": ["title"]},
                           {"goals": [18]}):
                broken = copy.deepcopy(record)
                broken["rules"][0].update(change)
                path = write(folder, "rules.json", json.dumps(broken))
                with self.assertRaises(sdg.RulesError, msg=change):
                    sdg.read_rules(path)
        finally:
            shutil.rmtree(folder)

    def test_phrases_match_whole_words_and_unless_phrases_veto(self):
        evidence = sdg.evidence_text(name="model train dataset", files=["trainer.csv"])
        self.assertNotIn("climate_and_weather_records", sdg.propose(evidence, self.rules)["rules"])
        evidence = sdg.evidence_text(name="australia rain dataset", columns=["RainToday"])
        proposal = sdg.propose(evidence, self.rules)
        self.assertIn("climate_and_weather_records", proposal["rules"])
        self.assertEqual(proposal["status"], sdg.PROPOSAL_STATUS)
        vetoed = sdg.propose(sdg.evidence_text(name="us cities and ashrae climate zone"), self.rules)
        self.assertNotIn("climate_and_weather_records", vetoed["rules"])
        self.assertIn("energy_use_of_buildings", vetoed["rules"])

    def test_no_rule_means_no_goal_and_matches_name_their_field(self):
        self.assertEqual(sdg.propose(sdg.evidence_text(name="stock prices of five years"), self.rules)["goals"], [])
        proposal = sdg.propose(sdg.evidence_text(name="road collisions", columns=["meansDebtBondageEarnings"]),
                               self.rules)
        self.assertEqual(proposal["goals"], [3, 5, 8, 11, 16])
        fields = {(match["rule"], match["field"]) for match in proposal["matches"]}
        self.assertIn(("human_trafficking_and_forced_labour", "columns"), fields)

    def test_agreement_counts_proposals_equal_to_the_review(self):
        proposals = {"a": {"goals": [3], "targets": ["3.6"]}, "b": {"goals": [], "targets": []}}
        review = {"datasets": {"a": {"goals": [3], "targets": ["3.6"]}, "b": {"goals": [16], "targets": ["16.1"]}}}
        result = sdg.agreement(proposals, review)
        self.assertEqual((result["reviewed"], result["agreed"]), (2, 1))


class LicenceDecisionTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.sources = line.read_sources()
        self.accepted = line.accepted_licences()

    def tearDown(self):
        shutil.rmtree(self.folder)

    def decide(self, files: dict, slug: str = "example", sources=None):
        target = self.folder / slug
        if target.exists():
            shutil.rmtree(target)
        for name, text in files.items():
            write(target, name, text)
        record = profile.profile_dataset(target)
        sources = sources or self.sources
        signals = line.licence_signals(target, record, sources)
        return line.licence_decision(slug, record, signals, sources, self.accepted)

    def test_agreeing_licence_file_and_metadata_field_decide_cc_by(self):
        decision = self.decide({"LICENSE": CC_BY_STATEMENT, "croissant.json": json.dumps(
            {"license": "https://creativecommons.org/licenses/by/4.0/"}), "CITATION.cff": "license: CC-BY-4.0\n"})
        self.assertEqual((decision["decision"], decision["spdx"], decision["basis"]),
                         (line.LICENSABLE, "CC-BY-4.0", line.BASIS_STATEMENT))

    def test_a_full_licence_text_is_matched_by_its_template(self):
        decision = self.decide({"LICENSE": MIT_TEXT})
        self.assertEqual((decision["spdx"], decision["basis"]), ("MIT", line.BASIS_TEMPLATE))

    def test_known_wrong_licences_off_the_list_or_unclear_are_held_by_name(self):
        cases = {
            line.LICENCE_NOT_ON_ALLOWLIST: {"README.txt": "LICENSE\nAvailable under the Open Database License (ODbL).\n"},
            line.LICENCE_PERMISSION_REQUIRED: {"README.md": "## License\nFor usage and publication please contact us.\n"},
            line.LICENCE_UNKNOWN: {"data.csv": "a\n1\n"},
            line.LICENCE_SIGNALS_DISAGREE: {"LICENSE": CC_BY_STATEMENT,
                                            "croissant.json": json.dumps({"license": "CC BY-SA 4.0"})},
            line.LICENCE_MIXED_TERMS: {"LICENSE": "Mixed terms apply. Adapters: Apache License, Version 2.0. "
                                                  "Everything else: CC BY 4.0.\n"}}
        for expected, files in cases.items():
            self.assertEqual(self.decide(files)["decision"], expected, files)
        self.assertEqual(self.decide({"LICENSE": "Dataset license: CC-BY-SA-4.0\n"})["spdx"], "CC-BY-SA-4.0")
        header = self.decide({"t.csv": "By using this data you agree to the Terms of Use,year\nx,2020\n"})
        self.assertEqual(header["decision"], line.LICENCE_PERMISSION_REQUIRED)

    def test_a_declared_decision_holds_only_while_its_conditions_hold(self):
        mixed = "Mixed terms apply. runs/: Apache License, Version 2.0. Everything else: CC BY 4.0.\n"
        sources = copy.deepcopy(self.sources)
        sources["declared"]["declared-example"] = {
            "licence": "CC-BY-4.0", "decided_on": "2026-10-09", "evidence_file": "LICENSE",
            "evidence_sha256": hashlib.sha256(mixed.encode()).hexdigest(), "requires_absent": ["runs"],
            "reason": "test"}
        decision = self.decide({"LICENSE": mixed, "t.csv": "a\n1\n"}, "declared-example", sources)
        self.assertEqual((decision["decision"], decision["basis"]), (line.LICENSABLE, line.BASIS_DECLARED))
        stale = self.decide({"LICENSE": mixed, "runs/run-01/adapter.bin": "x"}, "declared-example", sources)
        self.assertEqual(stale["decision"], line.DECLARED_DECISION_STALE)
        changed = self.decide({"LICENSE": mixed + "changed\n"}, "declared-example", sources)
        self.assertEqual(changed["decision"], line.DECLARED_DECISION_STALE)


def download(root: Path) -> Path:
    """A synthetic local download: one licensable dataset with tables, and held ones."""
    source = root / "download"
    write(source, "backup-manifest.json", json.dumps({"as_of": "2026-10-06", "account": "exampleowner",
                                                      "datasets": {}}))
    good = source / "road-collisions-sample"
    write(good, "LICENSE", CC_BY_STATEMENT)
    write(good, "CITATION.cff", "title: Road Collisions Sample\nauthors:\n  - name: \"Example Project\"\n"
                                "license: CC-BY-4.0\n")
    write(good, "README.md", "# Road Collisions Sample\n\nSynthetic road traffic collisions for tests.\n")
    write(good, "collisions.csv", csv_text(["crash_date", "borough", "injured", "killed", "fatal"],
                                           [["2026-01-0%d" % day, "north" if day % 2 else "south", day, day % 2,
                                             "true" if day % 2 else "false"] for day in range(1, 8)]))
    write(good, "rights.jsonl", "".join(json.dumps({"id": index, "allow_public_redistribution": index != 2}) + "\n"
                                        for index in range(3)))
    write(good, "summary.csv", "metric,value\nrows,7\n")
    write(good, "summary.json", json.dumps([{"metric": "rows", "value": 7}]))
    for split, count in (("train", 4), ("test", 2)):
        write(good, f"labels-{split}-00000.jsonl", "".join(json.dumps(
            {"id": f"{split}-{index}", "split": split, "label": "safe" if index % 2 else None, "score": index / 2}) + "\n"
            for index in range(count)))
    write(source / "coastline-sample", "README.txt", "LICENSE\nAvailable under the Open Database License (ODbL).\n")
    write(source / "coastline-sample", "lines.csv", "id,length\n1,2.5\n")
    write(source / "unknown-sample", "data.csv", "a,b\n1,2\n")
    write(source / "code-only-sample", "LICENSE", MIT_TEXT)
    write(source / "code-only-sample", "tool.py", "VALUE = 1\n")
    return source


class LineEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp())
        cls.source = download(cls.root)
        cls.result = line.generate(cls.source, code_revision=REVISION, licence_text=(ROOT / "LICENSE").read_bytes(),
                                   generated_on="2026-10-09", staging=cls.root / "staging")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    def component(self, built, name="package"):
        payload, bodies = built
        folder = self.root / name / payload["record_id"]
        for entry in payload["package"]["files"]:
            target = folder / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bodies[entry["digest"]])
        (folder / "candidate.json").write_text(json.dumps(payload), encoding="utf-8")
        return components.from_folder(folder)

    def test_one_package_and_every_other_dataset_held_by_name(self):
        built, refused, _facts, summary, inventory = self.result
        self.assertEqual(len(built), 1)
        self.assertEqual(sorted((row["subject"], row["reason"]) for row in refused),
                         [("coastline-sample", line.LICENCE_NOT_ON_ALLOWLIST), ("code-only-sample", line.NO_TABLE),
                          ("unknown-sample", line.LICENCE_UNKNOWN)])
        self.assertEqual(summary["outcomes"]["packaged"], 1)
        self.assertEqual(len(inventory), 4)

    def test_the_candidate_carries_the_contract_licence_and_sdg_proposal(self):
        payload, bodies = self.result[0][0]
        read_supply_candidate(payload)
        self.assertEqual(payload["line"], KAGGLE_PUBLIC_GOOD)
        self.assertEqual(payload["licence"]["spdx_expression"], "CC-BY-4.0 AND MIT")
        paths = {row["path"]: row for row in payload["files"]}
        self.assertEqual(paths["SOURCE-LICENSE"]["origin"], "upstream_verbatim")
        self.assertEqual(paths["UPSTREAM-LICENSE"]["origin"], "licence_text")
        self.assertIn("data/collisions.csv", paths)
        self.assertEqual(paths["fixtures/labels.jsonl"]["media_type"], "text/plain")
        card = json.loads(bodies[paths["component.json"]["digest"]])
        self.assertEqual(card["job"], {"source": line.JOB_SOURCE, "identity": "exampleowner/road-collisions-sample"})
        # The train and test shards are one table; two tables of one family name are told apart by their format.
        self.assertEqual(sorted(card["fixtures"]), ["collisions", "labels", "rights", "summary_csv", "summary_json"])
        # A table whose rows carry a redistribution flag that is not true for every row is described, not copied.
        self.assertNotIn("data/rights.jsonl", paths)
        self.assertIn("`rights`", card["data_note"])
        self.assertIn("data/summary.json", paths)
        self.assertEqual(card["sdg"]["goals"], [3, 11])
        self.assertEqual(card["sdg"]["status"], sdg.PROPOSAL_STATUS)
        self.assertEqual(payload["tests"]["result"], "passed")
        schema = json.loads(bodies[paths["schema.json"]["digest"]])
        self.assertEqual(schema["$defs"]["collisions"]["properties"]["injured"]["type"], "integer")
        self.assertEqual(schema["$defs"]["labels"]["properties"]["label"]["type"], ["null", "string"])

    def test_every_static_check_passes_on_the_stored_bytes(self):
        component = self.component(self.result[0][0])
        context = checks.QualificationContext.load(ROOT)
        context.duplicates = checks.duplicate_findings([component], context.policy)
        for check in checks.CHECKS:
            if check.check_id in ("sandbox", "mutation"):
                continue
            result = check.run(component, context)
            self.assertEqual(result.status, checks.PASSED, (check.check_id, result.findings))
        self.assertEqual(checks.job_key(component, context.policy),
                         "kaggle_public_good|kaggle_dataset|exampleowner/road-collisions-sample")

    @unittest.skipUnless(HAS_SANDBOX, "bubblewrap and the system interpreter are needed for the sandbox checks")
    def test_sandbox_and_mutation_pass_and_a_test_that_cannot_fail_is_caught(self):
        component = self.component(self.result[0][0])
        context = checks.QualificationContext.load(ROOT, sandbox_settings=SANDBOX, work_root=self.root / "work")
        by_id = {check.check_id: check for check in checks.CHECKS}
        self.assertEqual(by_id["sandbox"].run(component, context).status, checks.PASSED)
        self.assertEqual(by_id["mutation"].run(component, context).status, checks.PASSED)
        payloads = dict(component.payloads)
        payloads[line.CONTRACT_TESTS_NAME] = (b"import unittest\n\n\nclass T(unittest.TestCase):\n"
                                              b"    def test_nothing(self):\n        self.assertTrue(True)\n")
        weak = component.replaced(payloads=payloads)
        self.assertEqual(by_id["mutation"].run(weak, context).status, checks.REFUSED)


if __name__ == "__main__":
    unittest.main()
