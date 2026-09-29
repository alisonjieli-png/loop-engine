"""Checks for the qualification of generated components, its controls, the review adapter and admission."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tempfile as _tempfile
import unittest
from unittest import mock

from tools.component_qualification import admission, checks, controls, qualify, sampled_review, sampling
from tools.component_qualification.sandbox import SandboxSettings, parse_unittest

ROOT = Path(__file__).resolve().parents[1]
REVISION = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=False).stdout.strip()
SANDBOX = SandboxSettings()
HAS_SANDBOX = bool(REVISION) and SANDBOX.works()


def _context(work=None):
    return checks.QualificationContext.load(ROOT, sandbox_settings=SANDBOX if work else None, work_root=work)


class LicenceExpressionTests(unittest.TestCase):
    def test_expressions(self):
        self.assertEqual(checks.licence_identifiers("MIT"), ["MIT"])
        self.assertEqual(checks.licence_identifiers("MIT AND BSD-2-Clause"), ["MIT", "BSD-2-Clause"])
        self.assertEqual(checks.licence_identifiers("(MIT OR Apache-2.0) AND ISC"), ["MIT", "Apache-2.0", "ISC"])
        for wrong in ("", "MIT AND", "AND MIT", "(MIT", "MIT)", "MIT BSD-2-Clause", "GPL-2.0 WITH Classpath-exception-2.0",
                      "MIT; rm"):
            self.assertIsNone(checks.licence_identifiers(wrong), wrong)


class CodeEffectTests(unittest.TestCase):
    def test_effects_from_the_syntax_tree(self):
        found = checks.code_effects(
            "import subprocess\nimport urllib.request\nimport os\nfrom pathlib import Path\n"
            "def f():\n    subprocess.run(['true'])\n    Path('x').write_text('y')\n"
            "    open('z').read()\n    return os.environ['API_TOKEN']\n", {"API_TOKEN"})
        self.assertEqual(set(found), {"spawns_process", "network", "writes_fs", "reads_fs", "reads_secret"})

    def test_plain_code_has_no_effect(self):
        self.assertEqual(checks.code_effects("import json\n\ndef f(x):\n    return json.dumps(x).replace('a', 'b')\n",
                                             set()), {})

    def test_open_for_writing_and_aliases(self):
        found = checks.code_effects("import os as system\nfrom subprocess import run as go\n"
                                    "with open('a', mode='a') as s:\n    s.write('x')\nsystem.remove('a')\n", set())
        self.assertIn("writes_fs", found)
        self.assertIn("spawns_process", found)

    def test_environment_read_of_an_undeclared_name_is_not_a_secret(self):
        self.assertEqual(checks.code_effects("import os\nHOME = os.environ.get('HOME')\n", {"API_TOKEN"}), {})


class UnittestOutputTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_unittest("test_a ... ok\n\n----\nRan 4 tests in 0.1s\n\nOK (skipped=1)\n")["skipped"], 1)
        failed = parse_unittest("Ran 2 tests in 0.1s\n\nFAILED (failures=1, errors=1)\n")
        self.assertEqual((failed["ok"], failed["failures"], failed["errors"]), (False, 1, 1))
        self.assertEqual(parse_unittest("NO TESTS RAN\n")["ran"], 0)
        self.assertFalse(parse_unittest("Ran 3 tests in 0.1s\n\nOK\nforged line\n")["ok"])


class FixtureCheckTests(unittest.TestCase):
    def setUp(self):
        self.context = _context()
        self.code = controls.code_fixture(REVISION)
        self.configuration = controls.configuration_fixture(REVISION)
        self.api = controls.api_fixture(REVISION)
        self.context.duplicates = checks.duplicate_findings([self.code, self.configuration, self.api],
                                                            self.context.policy)

    def test_known_good_fixtures_pass_every_static_check(self):
        for fixture in (self.code, self.configuration, self.api):
            for check in checks.CHECKS:
                if check.check_id in ("sandbox", "mutation"):
                    continue
                self.assertEqual(check.run(fixture, self.context).status, checks.PASSED, (fixture.line, check.check_id))

    def test_every_static_control_is_refused_with_its_code(self):
        fixtures = {"code": self.code, "configuration": self.configuration, "api": self.api}
        by_id = {check.check_id: check for check in checks.CHECKS}
        for control in controls.CONTROLS:
            if control.check_id in ("sandbox", "mutation"):
                continue
            component = control.build(fixtures[control.base])
            self.context.duplicates.setdefault(component.identity, [])
            result = by_id[control.check_id].run(component, self.context)
            if not control.expected_code:
                self.assertEqual(result.status, checks.PASSED, control.control_id)
                continue
            self.assertIn(control.expected_code, [code for code, _detail in result.findings], control.control_id)

    def test_every_check_has_a_control(self):
        covered = {control.check_id for control in controls.CONTROLS} | {"duplicates"}
        self.assertEqual(covered, set(checks.CHECK_IDS))

    def test_job_key_distinguishes_operations_on_one_path(self):
        policy = self.context.policy
        module = "OPERATION = {'method': 'PUT', 'path': '/folders/{id}', 'operation_id': '%s'}\n"
        first = self.code.replaced(payloads=dict(self.code.payloads) | {"greeting_table.py": (module % "a").encode()})
        second = self.code.replaced(payloads=dict(self.code.payloads) | {"greeting_table.py": (module % "b").encode()})
        record = dict(first.candidate) | {"line": "openapi_operations"}
        first = first.replaced(candidate=record)
        second = second.replaced(candidate=dict(second.candidate) | {"line": "openapi_operations"})
        self.assertNotEqual(checks.job_key(first, policy), checks.job_key(second, policy))
        same = second.replaced(payloads=dict(second.payloads) | {"greeting_table.py": (module % "a").encode() + b"# x\n"},
                               candidate=dict(second.candidate))
        self.assertEqual(checks.job_key(first, policy), checks.job_key(same, policy))

    def test_vetting_keeps_dimensions_apart(self):
        rows = [{"check_id": name, "status": checks.PASSED, "notes": []} for name in checks.CHECK_IDS]
        rows[-1]["notes"] = [json.dumps({"interpreter": "3.14.4", "tests": {"ran": 3, "skipped": 0}})]
        vetting = qualify.vetting(rows, self.context.policy, "data_tables")
        self.assertTrue(vetting["source_identity_checked"])
        self.assertEqual(vetting["implementation_tested"], "tests_passed_in_sandbox")
        self.assertEqual(vetting["publication_approved"]["state"], "not_yet")
        rows[0]["status"] = checks.REFUSED
        self.assertFalse(qualify.vetting(rows, self.context.policy, "data_tables")["source_identity_checked"])


@unittest.skipUnless(HAS_SANDBOX, "bubblewrap and the system interpreter are needed for the sandbox checks")
class SelfTestTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="qualification-"))

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def test_self_test_passes(self):
        record = controls.self_test(_context(self.work), REVISION)
        self.assertTrue(record["passed"])
        self.assertGreaterEqual(len(record["known_wrong"]), 30)

    def test_a_check_that_never_refuses_fails_the_self_test(self):
        check = next(check for check in checks.CHECKS if check.check_id == "effects")
        with mock.patch.object(type(check), "run", lambda self, component, context: checks.CheckResult(
                "effects", "1", "effects", checks.IMPLEMENTATION, checks.PASSED)):
            with self.assertRaises(controls.SelfTestFailed):
                controls.self_test(_context(self.work), REVISION)

    def test_a_check_that_refuses_the_fixture_fails_the_self_test(self):
        check = next(check for check in checks.CHECKS if check.check_id == "parse")
        with mock.patch.object(type(check), "run", lambda self, component, context: checks.CheckResult(
                "parse", "1", "format", checks.IMPLEMENTATION, checks.REFUSED, (("always", "refuses"),))):
            with self.assertRaises(controls.SelfTestFailed):
                controls.self_test(_context(self.work), REVISION)


class NewRuleTests(unittest.TestCase):
    def setUp(self):
        self.policy = _context().policy

    def test_literal_statement_lines(self):
        text = "def f(a, b):\n    arguments = {'a': a, 'b': b}\n    return call(arguments)\nx = 1; y = 2\n"
        lines = checks.literal_statement_lines(text)
        self.assertIn(2, lines)
        self.assertNotIn(3, lines)
        self.assertNotIn(4, lines)

    def test_licence_fingerprints(self):
        self.assertEqual(checks.recognized_licences(controls.MIT_TEXT, self.policy), {"MIT"})
        self.assertEqual(checks.recognized_licences("All rights reserved.", self.policy), set())
        bsd3 = ("Redistribution and use in source and binary forms, with or without modification, are permitted. "
                "Neither the name of the copyright holder nor the names of its contributors may be used.")
        self.assertEqual(checks.recognized_licences(bsd3, self.policy), {"BSD-3-Clause"})

    def test_mutant_replaces_public_implementations_only(self):
        mutated, replaced = checks.mutant(controls.api_fixture(REVISION), self.policy)
        text = mutated.text("get_greeting.py")
        self.assertEqual(replaced, 1)
        self.assertIn("qualification mutant", text)
        self.assertIn("class ApiError", text)
        self.assertIsNone(checks.mutant(controls.configuration_fixture(REVISION), self.policy))


class ReuseTests(unittest.TestCase):
    def _record(self, **changes):
        record = {"identity": "a", "record_version": "v1", "package_digest": "d" * 64, "qualified_at": "2026-09-28T01:00:00Z",
                  "qualifier": {"code_revision": "r" * 40, "uncommitted_changes": False}, "checks": []}
        record.update(changes)
        return record

    def test_reuse_needs_the_same_bytes_and_committed_revision(self):
        row = {"record_id": "a", "record_version": "v1", "payload": {"package_digest": "d" * 64}}
        self.assertTrue(qualify.reusable(self._record(), row, "r" * 40))
        self.assertFalse(qualify.reusable(self._record(record_version="v2"), row, "r" * 40))
        self.assertFalse(qualify.reusable(self._record(package_digest="e" * 64), row, "r" * 40))
        self.assertFalse(qualify.reusable(self._record(), row, "s" * 40))
        self.assertFalse(qualify.reusable(self._record(qualifier={"code_revision": "r" * 40,
                                                                  "uncommitted_changes": True}), row, "r" * 40))
        self.assertFalse(qualify.reusable(None, row, "r" * 40))

    def test_load_reuse_keeps_the_newest_committed_record(self):
        folder = Path(tempfile.mkdtemp(prefix="reuse-"))
        self.addCleanup(shutil.rmtree, folder, True)
        path = folder / "qualification.jsonl"
        rows = [self._record(qualified_at="2026-09-28T01:00:00Z"), self._record(qualified_at="2026-09-28T02:00:00Z"),
                self._record(identity="b", qualifier={"code_revision": "r" * 40, "uncommitted_changes": True})]
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        loaded = qualify.load_reuse([path], "r" * 40)
        self.assertEqual(list(loaded), ["a"])
        self.assertEqual(loaded["a"]["qualified_at"], "2026-09-28T02:00:00Z")


class ReviewAdapterTests(unittest.TestCase):
    def setUp(self):
        from tools.candidate_review import native_profile
        self.criteria, self.instructions = native_profile.resources()
        self.code = controls.code_fixture(REVISION)

    def test_request_binds_the_exact_package(self):
        from tools.candidate_review.prechecks import body_binding_findings
        request = sampled_review.review_request(self.code, self.criteria, self.instructions.sha256, "anthropic")
        self.assertEqual(request.body_sha256, self.code.package.package_digest)
        self.assertEqual(body_binding_findings(request), [])
        self.assertEqual(request.producer.family, "anthropic")

    def test_planted_controls_change_the_package(self):
        import random
        for kind in sampled_review.CONTROL_KINDS:
            planted = sampled_review.plant(self.code, kind, "library.supply.data_tables." + "a" * 24 + ".b" * 1)
            if planted is None:
                continue
            self.assertNotEqual(planted.package.package_digest, self.code.package.package_digest, kind)
        identity = sampled_review._neutral_identity(self.code, random.Random(1), "c" * 64)
        self.assertRegex(identity, r"^library\.supply\.data_tables\.[0-9a-f]{24}\.c{16}$")

    def test_qualification_precheck(self):
        request = sampled_review.review_request(self.code, self.criteria, self.instructions.sha256, "anthropic")
        record = {"package_digest": self.code.package.package_digest, "outcome": "qualified",
                  "checks": [{"kind": "licence", "status": "passed", "findings": []}]}
        engine = sampled_review.QualificationPrecheck("licence", {self.code.identity: record}, set())
        self.assertEqual(engine.check(request, None).status, "passed")
        self.assertEqual(sampled_review.QualificationPrecheck("licence", {}, set()).check(request, None).status,
                         "refused")
        moved = dict(record, package_digest="0" * 64)
        self.assertEqual(sampled_review.QualificationPrecheck("licence", {self.code.identity: moved}, set())
                         .check(request, None).status, "refused")
        planted = sampled_review.QualificationPrecheck("licence", {}, {self.code.identity}).check(request, None)
        self.assertEqual((planted.status, planted.engine_id), ("passed", sampled_review.CONTROL_ENGINE))

    def test_an_authorized_panel_offers_the_provider_model_listing_to_its_reviewers(self):
        """A gateway reviewer is only eligible when the provider listing names its model.

        Known-wrong case: the panel is built with no listing, so every Ollama Cloud reviewer
        answers "the provider's model listing does not name this model" and no review call is
        ever made. The sampled review then reports a calibration it never ran, and the batch is
        withheld for a reason that has nothing to do with the components.
        """
        import tempfile as _tempfile
        from tools.candidate_review.reviewers import Availability
        listing = {"ok": True, "models": {"glm-5.3": {"id": "glm-5.3"}, "kimi-k2.6": {"id": "kimi-k2.6"}}}
        engine = mock.Mock()
        engine.availability.return_value = Availability(True, "", "test", {}, "")
        context_seen = {}
        with _tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"

            def capture(installation, policy, context):
                context_seen["listing"] = context.model_listing
                context_seen["resolver"] = context.credential_resolver
                return engine

            with mock.patch.object(sampled_review, "_listed_model_versions", return_value=listing, create=True), \
                    mock.patch("tools.candidate_review.engines.build_reviewer", capture):
                _configuration, _criteria, _instructions, panel = sampled_review._panel(ROOT, ledger, True, None)
            self.assertEqual(context_seen["listing"], listing["models"])
            self.assertIsNotNone(context_seen["resolver"])
            self.assertIsNotNone(panel)

    def test_an_unauthorized_panel_reads_no_provider_listing(self):
        with mock.patch.object(sampled_review, "_listed_model_versions",
                               side_effect=AssertionError("no provider listing"), create=True):
            seen = {}

            def capture(installation, policy, context):
                seen["listing"] = context.model_listing
                seen["resolver"] = context.credential_resolver
                return mock.Mock()

            with mock.patch("tools.candidate_review.engines.build_reviewer", capture):
                with _tempfile.TemporaryDirectory() as directory:
                    sampled_review._panel(ROOT, Path(directory) / "ledger.jsonl", False, None)
            self.assertIsNone(seen["listing"])
            self.assertIsNone(seen["resolver"])


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="admission-"))
        self.code = controls.code_fixture(REVISION)
        self.configuration = controls.configuration_fixture(REVISION)
        qualification = self.folder / "qualification"
        qualification.mkdir()
        with open(qualification / "qualification.jsonl", "w") as stream:
            for component in (self.code, self.configuration):
                stream.write(json.dumps({"identity": component.identity, "outcome": "qualified",
                                         "batch": component.batch, "package_digest": component.package.package_digest,
                                         "vetting": {"implementation_tested": "fixture"},
                                         "qualifier": {"code_revision": REVISION, "uncommitted_changes": False},
                                         "self_test_sha256": "0" * 64,
                                         "checks": []}) + "\n")
        self.qualification = qualification

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def _review(self, admissible=True, code_decision="approve"):
        decision = {"outcome": "accepted", "reasons": [], "sampled": 1, "acceptance_number": 0, "defective": 0,
                    "controls_planted": 1, "controls_rejected": 1}
        review = {"reviewer": "tactical.gemma-4-coding-abliterated", "producer_family": "anthropic",
                  "policy": sampling.SamplingPolicy().to_dict(), "admissible": admissible,
                  "admissibility_reasons": [] if admissible else ["reviewer_not_calibrated_today"], "ledger": "l",
                  "batches": {
                      self.code.batch: {"plan": {"batch_size": 1}, "decision": decision,
                                        "verdicts": [{"identity": self.code.identity, "decision": code_decision,
                                                      "criteria": [], "reason": "a reason" if code_decision != "approve"
                                                      else "", "call_ref": "run#1",
                                                      "body_sha256": self.code.package.package_digest}]},
                      self.configuration.batch: {"plan": {"batch_size": 1}, "verdicts": [],
                                                 "decision": {"outcome": "withheld", "reasons": ["x"]}}}}
        path = self.folder / f"review-{admissible}-{code_decision}.json"
        path.write_text(json.dumps(review))
        return path

    def _admit(self, review, name="out"):
        components = {self.code.identity: self.code, self.configuration.identity: self.configuration}
        return admission.admit(self.qualification, review, None, self.folder / name, "2026-09-28", ROOT,
                               components=components)

    def test_accepted_batch_is_written_and_read_by_the_manifest_builder(self):
        from tools.build_host_catalogue_manifest import _review_index
        result = self._admit(self._review())
        self.assertEqual((result["approved"], result["rejected"]), (1, 0))
        self.assertEqual(result["batches"][self.configuration.batch], "withheld")
        _record, index = _review_index(self.folder / "out")
        self.assertEqual(list(index), [self.code.identity])
        row = index[self.code.identity]
        self.assertEqual({decision["reviewer_id"] for decision in row["decisions"]},
                         {admission.ADMISSION_REVIEWER, "tactical.gemma-4-coding-abliterated"})

    def test_a_rejected_sample_is_never_approved(self):
        from tools.build_host_catalogue_manifest import _review_index
        result = self._admit(self._review(code_decision="reject"), "rejected")
        self.assertEqual((result["approved"], result["rejected"]), (0, 1))
        _record, index = _review_index(self.folder / "rejected")
        self.assertEqual(index[self.code.identity]["outcome"], "rejected")

    def test_an_uncommitted_qualifier_admits_nothing(self):
        path = self.qualification / "qualification.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for row in rows:
            row["qualifier"]["uncommitted_changes"] = True
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        with self.assertRaises(ValueError):
            self._admit(self._review(), "uncommitted")

    def test_a_review_that_is_not_admissible_admits_nothing(self):
        with self.assertRaises(ValueError):
            self._admit(self._review(admissible=False), "refused")
        self.assertFalse((self.folder / "refused").exists())


if __name__ == "__main__":
    unittest.main()
