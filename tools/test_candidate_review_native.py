"""Exact native-package reader and whole-package review regression cases, with no model calls."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

from candidate_review import native, native_profile, panel, prechecks, review_record
from candidate_review.ledger import ReviewLedger
from candidate_review.prompt import build_prompt
from candidate_review.records import CandidateReviewError
from candidate_review.reviewers.fixture import FixtureReviewer
from test_candidate_review_panel import (
    BASE,
    _bound_fixture_script,
    _configuration,
    _installation,
    _only,
    answer,
    attempt,
)

from loop_engine.core.harness_intelligence import HarnessIntelligenceItem
from loop_engine.core.service_runtime.catalogue_packages import (
    CataloguePackage,
    CataloguePackageFile,
)

ROOT = HERE.parent
SOURCE = "src/loop_engine/core/service_runtime/catalogue_packages.py"
REVISION = "9c57c9a4c813578bffa504108ef9d785b308bb86"
IDENTITY = "sum_checked_integers"


def fixture(folder, *, files=None, effects=None):
    files = files or {
        "AGENTS.md": ((b"# Sum checked integers\n\nTask: read supplied integers. First validate the input, then run "
                       b"[the tool](scripts/sum.py). Check [the contract](contracts/result.json).\n"),
                      "text/markdown", "instruction_file"),
        "scripts/sum.py": ((b"import json\nimport sys\nvalues = json.load(sys.stdin)\n"
                            b"print(json.dumps({'sum': sum(values)}))\n"), "text/x-python", "executable_tool"),
        "contracts/result.json": (json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema",
                                              "type": "object", "required": ["sum"],
                                              "properties": {"sum": {"type": "integer"}},
                                              "additionalProperties": False}).encode(),
                                  "application/json", "configuration"),
    }
    effects = ["spawns_process"] if effects is None else effects
    package = CataloguePackage(tuple(CataloguePackageFile(name, hashlib.sha256(body).hexdigest(), len(body), media, role)
                                    for name, (body, media, role) in files.items()))
    producer = {"producer_identity": "native test producer", "family": "anthropic",
                "method_identity": "original_fixture/v1"}
    source_digests = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (SOURCE, "LICENSE")}
    item = HarnessIntelligenceItem(identity=IDENTITY, kind="tool", purpose="Sum supplied integers with a checked result.",
                                   digest=package.package_digest, size_bytes=package.served_size,
                                   source_layer="harness_local", source_ref=SOURCE + "@" + REVISION,
                                   license_name="MIT", declared_effects=tuple(effects), styles=("codex",))
    row = {"reference": item.reference(), "body_path": f"bodies/{IDENTITY}.package.json",
           "package": package.to_dict(), "package_root": f"packages/{IDENTITY}",
           "producer": producer, "dependencies": ["python>=3.10"]}
    spec = {"id": IDENTITY, "layer": "code", "family": "harness_tool", "title": "Sum checked integers",
            "tags": ["arithmetic"], "text": "# Search metadata only\n", "sources": [SOURCE, "LICENSE"],
            "symbols": [], "kind": "tool", "purpose": item.purpose, "styles": ["codex"],
            "dependencies": row["dependencies"], "producer": producer, "declared_effects": effects,
            "package": package.to_dict(), "package_digest": package.package_digest,
            "package_root": row["package_root"], "body_path": row["body_path"],
            "provenance": {"authoring": "original_assistant_authored", "source_revision": REVISION,
                           "source_digests": {SOURCE: source_digests[SOURCE]},
                           "license": {"expression": "MIT", "path": "LICENSE", "sha256": source_digests["LICENSE"]}}}
    folder = Path(folder)
    for name, (body, _media, _role) in files.items():
        target = folder / row["package_root"] / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    (folder / "bodies").mkdir(exist_ok=True)
    (folder / row["body_path"]).write_bytes(package.document())
    (folder / "items.json").write_text(json.dumps({"record_type": native.NATIVE_ITEMS,
        "source_revision": REVISION, "source_digests": source_digests, "publication": "not_published", "items": [row]}))
    (folder / "specifications-001.json").write_text(json.dumps({"record_type": native.NATIVE_SPECIFICATIONS,
        "population": 1, "populations": 1, "specifications": [spec]}))
    return row


def load_request(folder):
    catalogue = native.NativeCatalogue.load(Path(folder), ROOT)
    criteria, instructions = native_profile.resources()
    return catalogue, catalogue.request(IDENTITY, catalogue.producer_for(IDENTITY), criteria, instructions.sha256), instructions


def codes(outcome):
    return {finding.code for result in outcome.results for finding in result.findings}


class NativeReaderTest(unittest.TestCase):
    def test_same_size_changed_payload_digest_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            row = fixture(directory)
            path = Path(directory) / row["package_root"] / "scripts/sum.py"
            before = path.read_bytes()
            path.write_bytes(before.replace(b"sum(values)", b"max(values)"))
            self.assertEqual(path.stat().st_size, len(before))
            with self.assertRaises(CandidateReviewError):
                load_request(directory)

    def test_manifest_and_every_exact_file_reach_the_prompt_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            row = fixture(directory)
            catalogue, request, instructions = load_request(directory)
            prompt = build_prompt(request, BASE.installations[0], instructions)
        self.assertEqual(request.body_sha256, row["reference"]["digest"])
        self.assertEqual(len(request.files), 3)
        for file in request.files:
            self.assertIn(file.entry.path, prompt.user)
            self.assertIn(file.payload.decode(), prompt.user)
        self.assertNotIn("Search metadata only", prompt.user)
        self.assertNotIn("150 to 600", prompt.user)
        self.assertEqual(catalogue.not_reviewed(), (IDENTITY,))

    def test_missing_changed_extra_and_linked_helper_refuse(self):
        for change in ("missing", "changed", "extra", "link"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                row = fixture(directory)
                root = Path(directory) / row["package_root"]
                helper = root / "scripts/sum.py"
                if change == "missing":
                    helper.unlink()
                elif change == "changed":
                    helper.write_bytes(helper.read_bytes() + b"\n")
                elif change == "extra":
                    (root / "unexpected.py").write_text("print(1)")
                else:
                    helper.unlink()
                    helper.symlink_to(ROOT / "LICENSE")
                with self.assertRaises(CandidateReviewError):
                    load_request(directory)

    def test_unsafe_declared_package_path_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture(directory)
            path = Path(directory) / "items.json"
            value = json.loads(path.read_text())
            value["items"][0]["package"]["files"][0]["path"] = "../AGENTS.md"
            path.write_text(json.dumps(value))
            with self.assertRaises(CandidateReviewError):
                load_request(directory)

    def test_unknown_items_version_and_duplicate_json_keys_refuse(self):
        for payload in ('{"record_type":"starter_catalogue_candidate_items/v2"}',
                        '{"record_type":"x","record_type":"y"}'):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                fixture(directory)
                (Path(directory) / "items.json").write_text(payload)
                with self.assertRaises(CandidateReviewError):
                    load_request(directory)

    def test_item_and_specification_package_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture(directory)
            path = Path(directory) / "specifications-001.json"
            value = json.loads(path.read_text())
            value["specifications"][0]["dependencies"] = []
            path.write_text(json.dumps(value))
            with self.assertRaises(CandidateReviewError):
                load_request(directory)


class NativePrecheckTest(unittest.TestCase):
    def test_native_activation_paths_cannot_be_disguised_as_passive_resources(self):
        for path, role, media, body in (
            ("opencode.json", "other", "application/json", b'{"plugin":["npm:fixture-package"]}'),
            (".pi/settings.json", "other", "application/json", b'{"packages":["npm:fixture-package"]}'),
            ("references/opencode.json", "skill_reference", "text/markdown", b"# A reference\n"),
            (".claude/settings.json", "configuration", "application/schema+json",
             b'{"$schema":"https://json-schema.org/draft/2020-12/schema","hooks":{}}'),
            (".opencode/plugins/helper.ts", "skill_reference", "text/plain", b"example text"),
            (".pi/extensions/helper.ts", "instruction_file", "text/markdown", b"# Instructions\n"),
            ("plugin.json", "skill_reference", "text/plain", b"example text"),
            ("hooks/hooks.json", "configuration", "application/schema+json",
             b'{"$schema":"https://json-schema.org/draft/2020-12/schema"}'),
        ):
            with self.subTest(path=path, role=role):
                files = {"AGENTS.md": (b"# Task\nRead the supplied material.\n", "text/markdown", "instruction_file"),
                         path: (body, media, role)}
                self.assertIn("native_activation_path_unqualified", codes(self.evaluate(files=files)))

    def test_passive_json_is_limited_to_the_declared_resource_locations(self):
        for path, accepted in (("examples/input.json", True), ("verification/cases.json", True),
                               ("references/data.json", True), ("assets/data.json", True),
                               ("contracts/sample.json", True), ("arbitrary.json", False)):
            with self.subTest(path=path):
                files = {"AGENTS.md": (b"# Task\nRead the supplied data.\n", "text/markdown", "instruction_file"),
                         path: (b'{"input":1}', "application/json", "other")}
                outcome = self.evaluate(files=files)
                self.assertEqual(not outcome.refused, accepted)

    def test_unrelated_client_entrypoint_cannot_claim_supported_loading(self):
        files = {"GEMINI.md": (b"# Task\nUse the supplied data.\n", "text/markdown", "instruction_file")}
        self.assertIn("native_required_component_unqualified", codes(self.evaluate(files=files)))

    def test_large_population_selects_existing_minhash_engine_without_exact_sampling(self):
        config = native_profile.configuration(BASE, population_size=10000)
        self.assertEqual(tuple(config.policy.prechecks["duplicates"]), ("native_minhash_rules",))

    def test_schema_json_media_and_regular_expression_data_do_not_imply_binary_or_network_execution(self):
        files = {"AGENTS.md": (b"# Task\nRun the pure parser.\n", "text/markdown", "instruction_file"),
                 "tool.py": (b"import re\npattern = re.compile('x')\nvalue = {'requests': []}\n",
                             "text/x-python", "executable_tool"),
                 "contracts/schema.json": (b'{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object"}',
                                 "application/schema+json", "configuration")}
        self.assertFalse(self.evaluate(files=files).refused)

    def test_directly_replaced_payload_does_not_bypass_the_fixed_package_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture(directory)
            catalogue, request, _instructions = load_request(directory)
            file = request.files[0]
            forged = replace(request, files=(replace(file, payload=file.payload + b"changed"),) + request.files[1:])
            config = native_profile.configuration(BASE)
            outcome = prechecks.run_prechecks(forged, native_profile.engines(config),
                                              prechecks.PrecheckContext(config.policy, catalogue.population_bodies()))
        self.assertIn("native_payload_binding_invalid", codes(outcome))

    def evaluate(self, files=None, effects=None):
        with tempfile.TemporaryDirectory() as directory:
            fixture(directory, files=files, effects=effects)
            catalogue, request, _instructions = load_request(directory)
            config = native_profile.configuration(BASE)
            return prechecks.run_prechecks(request, native_profile.engines(config),
                                           prechecks.PrecheckContext(config.policy, catalogue.population_bodies()))

    def test_valid_complete_instruction_tool_and_schema_pass_prechecks(self):
        self.assertFalse(self.evaluate().refused)

    def test_executable_requires_process_effect(self):
        self.assertIn("native_process_effect_missing", codes(self.evaluate(effects=[])))

    def test_python_cannot_hide_under_a_passive_role(self):
        files = {"AGENTS.md": (b"# Task\nRead the tool.\n", "text/markdown", "instruction_file"),
                 "tool.py": (b"print(1)\n", "text/x-python", "skill_reference")}
        self.assertIn("native_executable_role_mismatch", codes(self.evaluate(files=files)))

    def test_missing_declared_local_resource_refuses(self):
        files = {"AGENTS.md": (b"# Task\nRead [helper](scripts/absent.py).\n", "text/markdown", "instruction_file")}
        self.assertIn("native_resource_missing", codes(self.evaluate(files=files)))

    def test_malformed_native_skill_entrypoint_refuses(self):
        files = {"SKILL.md": (b"---\nname: missing-description\n---\nDo the task.\n", "text/markdown", "skill_definition")}
        self.assertIn("native_skill_frontmatter_invalid", codes(self.evaluate(files=files)))

    def test_required_unsupported_component_is_not_silently_ignored(self):
        files = {"AGENTS.md": (b"# Task\nUse the hook.\n", "text/markdown", "instruction_file"),
                 "hooks/start.py": (b"print(1)\n", "text/x-python", "hook")}
        self.assertIn("native_required_component_unqualified", codes(self.evaluate(files=files)))

    def test_binary_asset_is_declared_but_requires_separate_verification(self):
        files = {"AGENTS.md": (b"# Task\nUse the supplied image.\n", "text/markdown", "instruction_file"),
                 "assets/input.bin": (b"\x00\xff", "application/octet-stream", "skill_asset")}
        self.assertIn("native_binary_verification_missing", codes(self.evaluate(files=files)))

    def test_python_syntax_dependency_and_dynamic_execution_refuse(self):
        for source, expected in ((b"def broken(:\n", "native_python_syntax_invalid"),
                                 (b"import unprovided_package\n", "native_dependency_unresolved"),
                                 (b"eval(input())\n", "native_dynamic_execution_refused")):
            with self.subTest(expected=expected):
                files = {"AGENTS.md": (b"# Task\nRun the tool.\n", "text/markdown", "instruction_file"),
                         "tool.py": (source, "text/x-python", "executable_tool")}
                self.assertIn(expected, codes(self.evaluate(files=files)))


def native_run(folder):
    fixture(folder)
    catalogue, request, instructions = load_request(folder)
    criteria, _instructions = native_profile.resources()
    configuration = native_profile.configuration(_configuration([
        _installation(name, family) for name, family in zip(("a", "b", "c"), ("zhipu", "deepseek", "openai"))]))
    def approve_native(prompt, number):
        return attempt(answer(prompt, findings=[{"criterion_id": "whole_package", "blocking": False,
                                                 "text": "Fixture review covers each supplied file."}]))
    reviewers = {item.installation_id: FixtureReviewer(item, _bound_fixture_script(approve_native, item.model))
                 for item in configuration.installations}
    ledger = ReviewLedger(Path(folder) / "review-ledger.jsonl")
    instance = panel.ReviewPanel(configuration, criteria, instructions, reviewers, native_profile.engines(configuration), ledger)
    result = instance.run(panel.PanelRunRequest("native-fixture", (request,), catalogue.population_bodies(),
                                               3, 1000000, True, fixture_run=True))
    record = review_record.build_panel_review_record(result, ledger, catalogue=catalogue, configuration=configuration,
        criteria=criteria, instructions=instructions, producers=catalogue.producer_declaration(configuration.families),
        population=review_record.PopulationSelection(review_record.EXPLICIT_LIST, "", (IDENTITY,), (IDENTITY,)),
        recorded_at="2026-09-23", record_path="artifacts/native-fixture-review.json", fixture_run=True)
    return result, record


class NativeReviewPersistenceTest(unittest.TestCase):
    def test_changed_file_role_or_reported_identity_invalidates_persisted_review(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            _result, good = native_run(directory)
        for change in ("role", "identity", "subject", "producer_method", "dependencies", "criteria"):
            with self.subTest(change=change):
                record = copy.deepcopy(good)
                if change == "role":
                    record["rows"][0]["subject"]["package"]["files"][0]["role"] = "other"
                elif change == "identity":
                    record["calls"][0]["reported_model"] = "different-model"
                elif change == "subject":
                    record["calls"][0]["request_record_type"] = "candidate_review_request/v1"
                elif change == "producer_method":
                    record["rows"][0]["subject"]["producer_method"] = "forged/v1"
                elif change == "dependencies":
                    record["rows"][0]["subject"]["specification"]["dependencies"] = []
                else:
                    record["criteria"]["criteria_sha256"] = "0" * 64
                with self.assertRaises(CandidateReviewError):
                    review_record.read_panel_review_record(record, allow_fixture=True)

    def test_native_cli_prechecks_and_record_export_spend_no_unauthorized_calls(self):
        import review_catalogue_candidates as command
        from candidate_review.reviewers import Availability
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            fixture(directory)
            path = Path(directory)
            options = command._parser().parse_args([
                "--content-profile", "native-original", "--catalogue", directory, "--repository", str(ROOT),
                "--ledger", str(path / "ledger.jsonl"), "--identity", IDENTITY, "--call-ceiling", "0",
                "--token-ceiling", "0", "--record", str(path / "review.json"), "--recorded-at", "2026-09-23"])
            engine = mock.Mock()
            engine.availability.return_value = Availability(False, "offline test", "", {}, "engine_unavailable")
            with mock.patch.object(command, "listed_model_versions", side_effect=AssertionError("no provider query")), \
                    mock.patch.object(command.engines, "build_reviewer", return_value=engine):
                result = command.run(options)
            record = json.loads((path / "review.json").read_text())
        self.assertEqual(result["totals"]["calls"], 0)
        self.assertEqual(record["rows"][0]["outcome"], "not_started")
        self.assertEqual(record["catalogue_items_record_type"], native.NATIVE_ITEMS)
        engine.review.assert_not_called()

    def test_complete_native_package_and_reported_identity_survive_record_roundtrip(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            result, record = native_run(directory)
        self.assertEqual(_only(result, IDENTITY).outcome, "approved")
        self.assertEqual(record["record_type"], "starter_catalogue_panel_review/v3")
        self.assertEqual(record["rows"][0]["subject"]["record_type"], native.NATIVE_REQUEST)
        self.assertEqual(len(record["rows"][0]["subject"]["package"]["files"]), 3)
        for call in record["calls"]:
            self.assertEqual(call["reported_model"], call["model"])
        self.assertEqual(review_record.read_panel_review_record(record, allow_fixture=True), record)

    def test_old_review_records_cannot_be_resumed_or_admitted_by_current_reader(self):
        from test_candidate_review_record import APPROVED_RECORD
        old = copy.deepcopy(APPROVED_RECORD)
        old["record_type"] = "starter_catalogue_panel_review/v1"
        with self.assertRaises(CandidateReviewError):
            review_record.read_panel_review_record(old, allow_fixture=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            call = copy.deepcopy(APPROVED_RECORD["calls"][0])
            call["record_type"] = "candidate_review_call/v1"
            path.write_text(json.dumps(call) + "\n")
            with self.assertRaises(CandidateReviewError):
                ReviewLedger(path)


if __name__ == "__main__":
    unittest.main()
