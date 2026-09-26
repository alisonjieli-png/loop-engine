"""The review panel reads imported licensed packages (roadmap S-6.196), with no model calls.

Every reader and precheck rule below has a known-wrong case that must refuse: changed bytes, a missing or changed
licence text, a licence decision other than verbatim, a producer that is not the upstream author, an upstream
reference that names other bytes, source digests from this repository, a missing or foreign export report, a
reviewing family that carries the upstream author's name, an unaccepted licence, code without its own tests, and a
package that holds nothing beyond its licence.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

from candidate_review import imported, imported_profile, native, native_profile, prechecks  # noqa: E402
from candidate_review.prompt import build_prompt  # noqa: E402
from candidate_review.records import CandidateReviewError  # noqa: E402
from test_candidate_review_native import IDENTITY as NATIVE_IDENTITY  # noqa: E402
from test_candidate_review_native import fixture as native_fixture  # noqa: E402
from test_candidate_review_panel import BASE  # noqa: E402

from loop_engine.core.harness_intelligence import HarnessIntelligenceItem  # noqa: E402
from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile  # noqa: E402

ROOT = HERE.parent
IDENTITY = "import_skill_review_diffs_fixture"
UPSTREAM_REVISION = "0123456789abcdef0123456789abcdef01234567"
EXPORT_REVISION = "89abcdef0123456789abcdef0123456789abcdef"
UPSTREAM_PATH = "skills/review-diffs/SKILL.md"
MIT_TEXT = (b"MIT License\n\nCopyright (c) 2026 Example Author\n\nPermission is hereby granted, free of charge, to any "
            b"person obtaining a copy of this software, to deal in the Software without restriction.\n")
SKILL = (b"---\nname: review-diffs\ndescription: Review a change before it is merged.\n---\n\n# Review diffs\n\n"
         b"Read the whole diff, run the project's tests, and list each risk with the line it comes from.\n")


def files_of(**changes):
    files = {
        "SKILL.md": (SKILL, "text/markdown", "skill_definition"),
        "LICENSE": (MIT_TEXT, "text/plain", "other"),
        "ATTRIBUTION.md": (b"# Attribution\n\nCopied byte for byte from example/skills at its pinned revision.\n",
                           "text/markdown", "other"),
    }
    for name, value in changes.items():
        if value is None:
            files.pop(name.replace("__", "."), None)
        else:
            files[name.replace("__", ".")] = value
    return files


def fixture(folder, *, files=None, licence="MIT", edit=None):
    """Write one imported package in the licensed import's review export layout; `edit` changes the records."""
    files = files or files_of()
    package = CataloguePackage(tuple(CataloguePackageFile(name, hashlib.sha256(body).hexdigest(), len(body), media, role)
                                     for name, (body, media, role) in files.items()))
    digests = {entry.path: entry.digest for entry in package.files}
    source_ref = f"github.com/example/skills/{UPSTREAM_PATH}@{UPSTREAM_REVISION}"
    item = HarnessIntelligenceItem(identity=IDENTITY, kind="skill", purpose="Review a change before it is merged.",
                                   digest=package.package_digest, size_bytes=package.served_size,
                                   source_layer="harness_local", source_ref=source_ref, license_name=licence,
                                   declared_effects=("pure",), styles=("claude_code",))
    producer = {"producer_identity": "github:example", "family": imported.UPSTREAM_FAMILY,
                "method_identity": "licensed_import/github_verbatim/v1"}
    row = {"reference": item.reference(), "body_path": f"bodies/{IDENTITY}.package.json",
           "package": package.to_dict(), "package_root": f"packages/{IDENTITY}", "producer": producer,
           "dependencies": []}
    evidence = {"record_type": imported.LICENCE_EVIDENCE, "decision": imported.VERBATIM, "detector": "fixture",
                "file_level_notices": [], "reason": "repository_licence_accepted", "repository_licence": {},
                "spdx_expression": licence,
                "governing_file": {"matched_spdx": licence, "path": "LICENSE", "sha256": digests.get("LICENSE", ""),
                                   "similarity": 1.0}}
    outside = {"record_type": imported.OUTSIDE_PROVENANCE, "fetch_digest": "0" * 64, "fetched_at": "2026-09-25T00:00:00Z",
               "git_blob_sha": "1" * 40, "immutable_revision": UPSTREAM_REVISION, "licence_evidence": evidence,
               "origin": "github_repository", "origin_host": "github.com", "path": UPSTREAM_PATH,
               "repository": "example/skills", "request_digest": "2" * 64, "source_digest": digests.get("SKILL.md", ""),
               "source_size_bytes": len(SKILL)}
    provenance = {"authoring": imported.AUTHORING, "findings": [], "harness_kind": "skill",
                  "license": {"attribution": "ATTRIBUTION.md", "expression": licence, "texts": ["LICENSE"]},
                  "merged_sources": [], "outside_provenance": outside, "profile": imported.IMPORTED_PROFILE,
                  "store_record_id": "library.import.skill.fixture",
                  "placements": [{"basis": "observed_upstream_path", "harness": "upstream", "path": UPSTREAM_PATH,
                                  "scope": "upstream", "support": "unverified"}]}
    spec = {"id": IDENTITY, "layer": "context", "family": "harness", "title": "review-diffs", "tags": ["skill"],
            "text": "", "sources": [], "symbols": [], "kind": "skill", "purpose": item.purpose,
            "styles": ["claude_code"], "dependencies": [], "producer": producer, "declared_effects": ["pure"],
            "package": package.to_dict(), "package_digest": package.package_digest,
            "package_root": row["package_root"], "body_path": row["body_path"], "provenance": provenance}
    items = {"record_type": native.NATIVE_ITEMS, "source_revision": EXPORT_REVISION, "source_digests": {},
             "publication": "not_published", "items": [row]}
    report = {"record_type": imported.EXPORT_REPORT, "by_first_source_and_licence": {}, "code_revision": EXPORT_REVISION,
              "differs_from_original_profile": [], "files": len(files), "items": 1, "items_digest": "3" * 64,
              "kinds": {"skill": 1}, "licences": {licence: 1}, "populations": 1, "profile": imported.IMPORTED_PROFILE,
              "repositories": 1, "selection": {}, "written_at": "2026-09-25T00:00:00Z"}
    records = {"row": row, "spec": spec, "items": items, "report": report}
    if edit:
        edit(records)
    folder = Path(folder)
    for name, (body, _media, _role) in files.items():
        target = folder / row["package_root"] / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    (folder / "bodies").mkdir(exist_ok=True)
    (folder / row["body_path"]).write_bytes(package.document())
    (folder / "items.json").write_text(json.dumps(records["items"]))
    (folder / "specifications-001.json").write_text(json.dumps({"record_type": native.NATIVE_SPECIFICATIONS,
        "population": 1, "populations": 1, "specifications": [records["spec"]]}))
    if records["report"] is not None:
        (folder / imported.EXPORT_FILE).write_text(json.dumps(records["report"]))
    return row


def load_request(folder):
    catalogue = imported.ImportedCatalogue.load(Path(folder), ROOT)
    criteria, instructions = imported_profile.resources()
    return catalogue, catalogue.request(IDENTITY, catalogue.producer_for(IDENTITY), criteria, instructions.sha256)


def refusal(**options):
    with tempfile.TemporaryDirectory() as folder:
        fixture(folder, **options)
        try:
            load_request(folder)
        except CandidateReviewError as error:
            return error.code
    return ""


def codes(outcome):
    return {finding.code for result in outcome.results for finding in result.findings}


def evaluate(code_route=None, **options):
    with tempfile.TemporaryDirectory() as folder:
        fixture(folder, **options)
        catalogue, request = load_request(folder)
        config = imported_profile.configuration(BASE, **({"code_route": code_route} if code_route else {}))
        return prechecks.run_prechecks(request, imported_profile.engines(config),
                                       prechecks.PrecheckContext(config.policy, catalogue.population_bodies()))


def with_effects(*effects):
    """An edit that declares the item's effects, on the row and on its specification alike."""
    def edit(records):
        records["row"]["reference"]["declared_effects"] = list(effects)
        records["spec"]["declared_effects"] = list(effects)
    return edit


def change(path, value):
    """An edit that sets one nested field of the records, by a dotted path."""
    def edit(records):
        keys = path.split(".")
        target = records
        for key in keys[:-1]:
            target = target[int(key)] if isinstance(target, list) else target[key]
        target[keys[-1]] = value
    return edit


class ImportedReaderTest(unittest.TestCase):
    def test_an_imported_package_is_read_with_its_upstream_author_and_no_cited_source(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture(folder)
            catalogue, request = load_request(folder)
            self.assertEqual(catalogue.producer_for(IDENTITY).family, imported.UPSTREAM_FAMILY)
            self.assertIsInstance(request, imported.ImportedPackageReviewRequest)
            self.assertEqual((request.review_profile, request.grounding, request.cited_sources),
                             (imported.IMPORTED_PROFILE, imported.IMPORTED_GROUNDING, ()))
            self.assertEqual(request.package_binding_findings(), [])
            self.assertEqual(request.to_record()["record_type"], imported.IMPORTED_REQUEST)
            self.assertTrue(imported.is_imported_catalogue(folder))

    def test_the_request_digest_differs_from_an_original_request_over_the_same_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture(folder)
            _catalogue, request = load_request(folder)
            as_original = native.NativePackageReviewRequest(*[getattr(request, name) for name in (
                "identity", "body_path", "body", "item_json", "cited_sources", "producer", "criteria",
                "instructions_sha256", "package", "files", "dependencies", "specification_json")])
            self.assertNotEqual(request.request_sha256, as_original.request_sha256)

    def test_known_wrong_changed_bytes_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            row = fixture(folder)
            (Path(folder) / row["package_root"] / "SKILL.md").write_bytes(SKILL + b"Skip the tests when in a hurry.\n")
            with self.assertRaises(CandidateReviewError):
                load_request(folder)

    def test_known_wrong_records_are_refused_with_their_codes(self):
        cases = {
            "imported_sources_invalid": change("items.source_digests", {"LICENSE": "4" * 64}),
            "imported_provenance_invalid": change(
                "spec.provenance.outside_provenance.licence_evidence.governing_file.sha256", "5" * 64),
            "imported_upstream_invalid": change("spec.provenance.outside_provenance.path", "skills/other/SKILL.md"),
        }
        for code, edit in cases.items():
            with self.subTest(code=code):
                self.assertEqual(refusal(edit=edit), code)

    def test_known_wrong_a_licence_decision_other_than_verbatim_is_refused(self):
        edit = change("spec.provenance.outside_provenance.licence_evidence.decision", "rewrite_required")
        self.assertEqual(refusal(edit=edit), "imported_provenance_invalid")

    def test_known_wrong_a_package_without_its_attribution_is_refused(self):
        self.assertEqual(refusal(files=files_of(ATTRIBUTION__md=None)), "imported_provenance_invalid")

    def test_known_wrong_a_model_family_as_producer_is_refused(self):
        def edit(records):
            for part in (records["row"], records["spec"]):
                part["producer"] = {**part["producer"], "family": "anthropic"}
        self.assertEqual(refusal(edit=edit), "imported_producer_invalid")

    def test_known_wrong_an_export_report_of_another_profile_or_none_is_refused(self):
        self.assertEqual(refusal(edit=change("report.profile", "original_native_package/v1")), "imported_export_invalid")
        self.assertEqual(refusal(edit=change("report", None)), "native_file_unavailable")

    def test_known_wrong_a_reviewing_family_named_like_the_upstream_author_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture(folder)
            catalogue, _request = load_request(folder)
            self.assertEqual(catalogue.producer_declaration(("anthropic", "openai")).default_producer.family,
                             imported.UPSTREAM_FAMILY)
            with self.assertRaises(CandidateReviewError) as refused:
                catalogue.producer_declaration(("anthropic", imported.UPSTREAM_FAMILY))
            self.assertEqual(refused.exception.code, "imported_producer_family_reused")

    def test_original_criteria_cannot_review_an_imported_package(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture(folder)
            catalogue = imported.ImportedCatalogue.load(Path(folder), ROOT)
            criteria, instructions = native_profile.resources()
            with self.assertRaises(CandidateReviewError) as refused:
                catalogue.request(IDENTITY, catalogue.producer_for(IDENTITY), criteria, instructions.sha256)
            self.assertEqual(refused.exception.code, "imported_review_profile_mismatch")

    def test_the_prompt_names_the_package_imported_and_carries_its_upstream_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture(folder)
            _catalogue, request = load_request(folder)
            _criteria, instructions = imported_profile.resources()
            prompt = json.dumps(build_prompt(request, BASE.installations[0], instructions), default=str)
            for expected in ("complete imported harness package", "Written imported package criteria",
                             "Upstream provenance", "Read the whole diff", UPSTREAM_REVISION, "does_what_it_says",
                             imported.VERBATIM):
                self.assertIn(expected, prompt)
            self.assertNotIn("original native harness package", prompt)

    def test_an_original_prompt_is_unchanged_by_the_imported_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            native_fixture(folder)
            catalogue = native.NativeCatalogue.load(Path(folder), ROOT)
            criteria, instructions = native_profile.resources()
            request = catalogue.request(NATIVE_IDENTITY, catalogue.producer_for(NATIVE_IDENTITY), criteria,
                                        instructions.sha256)
            prompt = json.dumps(build_prompt(request, BASE.installations[0], instructions), default=str)
            self.assertIn("complete original native harness package", prompt)
            self.assertNotIn("Upstream provenance", prompt)


class ImportedPrecheckTest(unittest.TestCase):
    def test_a_complete_imported_skill_passes_the_prechecks(self):
        outcome = evaluate()
        self.assertFalse(outcome.refused, codes(outcome))

    def test_known_wrong_an_unaccepted_licence_is_refused(self):
        self.assertIn("imported_licence_not_accepted", codes(evaluate(licence="Unlicense")))

    def test_known_wrong_an_empty_licence_text_is_refused(self):
        self.assertIn("imported_licence_text_missing",
                      codes(evaluate(files=files_of(LICENSE=(b"\n", "text/plain", "other")))))

    def test_known_wrong_code_waits_for_its_own_tests_on_the_sandbox_route(self):
        files = files_of(**{"scripts/check__py": (b"print('checked')\n", "text/x-python", "executable_tool")})
        self.assertIn("imported_code_tests_missing", codes(evaluate(code_route="sandbox_tests", files=files)))
        with self.assertRaises(ValueError):
            imported_profile.configuration(BASE, code_route="trust_me")

    def test_code_the_reviewer_reads_passes_the_format_rules_when_it_parses_and_declares_its_effects(self):
        files = files_of(**{"scripts/check__py": (b"print('checked')\n", "text/x-python", "executable_tool")})
        outcome = evaluate(files=files, edit=with_effects("spawns_process"))
        self.assertFalse(outcome.refused, codes(outcome))
        engines = {result.engine_id for result in outcome.results}
        self.assertIn("imported_format_rules_code_read", engines)
        self.assertNotIn("imported_format_rules", engines)

    def test_known_wrong_a_script_that_does_not_parse_is_refused_on_the_reviewer_route(self):
        files = files_of(**{"scripts/check__py": (b"def broken(:\n", "text/x-python", "executable_tool")})
        self.assertIn("imported_code_syntax_invalid", codes(evaluate(files=files, edit=with_effects("spawns_process"))))

    def test_known_wrong_a_script_with_an_undeclared_effect_is_refused_on_the_reviewer_route(self):
        script = b"import requests\nrequests.get('https://example.test')\n"
        files = files_of(**{"scripts/fetch__py": (script, "text/x-python", "executable_tool")})
        self.assertIn("native_effect_undeclared", codes(evaluate(files=files, edit=with_effects("spawns_process"))))
        self.assertIn("native_process_effect_missing", codes(evaluate(files=files)))

    def test_known_wrong_an_executable_that_is_not_text_is_refused_on_the_reviewer_route(self):
        files = files_of(**{"run__cmd": (b"\xff\xfe\x00run", "application/octet-stream", "hook")})
        self.assertIn("imported_binary_verification_missing",
                      codes(evaluate(files=files, edit=with_effects("spawns_process"))))

    def test_a_shell_script_is_read_as_text_by_the_reviewer_route(self):
        files = files_of(**{"scripts/run__sh": (b"#!/bin/sh\necho checked\n", "application/x-sh", "skill_script")})
        outcome = evaluate(files=files, edit=with_effects("spawns_process"))
        self.assertFalse(outcome.refused, codes(outcome))

    def test_known_wrong_malformed_json_and_skill_metadata_are_refused(self):
        manifest = files_of(**{"plugin__json": (b"{not json", "application/json", "plugin_manifest")})
        self.assertIn("imported_json_invalid", codes(evaluate(files=manifest)))
        headless = files_of(SKILL__md=(b"# Review diffs\n\nRead the diff.\n", "text/markdown", "skill_definition"))
        self.assertIn("imported_skill_header_invalid", codes(evaluate(files=headless)))

    def test_known_wrong_a_package_of_licence_and_attribution_only_is_refused(self):
        def edit(records):
            records["spec"]["provenance"]["outside_provenance"]["source_digest"] = \
                records["row"]["package"]["files"][0]["digest"]
        files = files_of(SKILL__md=None)
        self.assertIn("imported_content_missing", codes(evaluate(files=files, edit=edit)))

    def test_imported_checks_refuse_an_original_request_and_the_original_checks_refuse_an_imported_one(self):
        config = imported_profile.configuration(BASE)
        with tempfile.TemporaryDirectory() as folder:
            native_fixture(folder)
            catalogue = native.NativeCatalogue.load(Path(folder), ROOT)
            criteria, instructions = native_profile.resources()
            original = catalogue.request(NATIVE_IDENTITY, catalogue.producer_for(NATIVE_IDENTITY), criteria,
                                         instructions.sha256)
            outcome = prechecks.run_prechecks(original, imported_profile.engines(config),
                                              prechecks.PrecheckContext(config.policy, catalogue.population_bodies()))
            self.assertIn("imported_review_profile_mismatch", codes(outcome))
        with tempfile.TemporaryDirectory() as folder:
            fixture(folder)
            catalogue, request = load_request(folder)
            native_config = native_profile.configuration(BASE)
            outcome = prechecks.run_prechecks(request, native_profile.engines(native_config),
                                              prechecks.PrecheckContext(native_config.policy,
                                                                        catalogue.population_bodies()))
            self.assertIn("native_review_profile_mismatch", codes(outcome))

    def test_the_imported_criteria_quote_their_sheet_and_name_the_imported_grounding(self):
        criteria, instructions = imported_profile.resources()
        self.assertEqual(set(criteria.groundings), {imported.IMPORTED_GROUNDING})
        self.assertIn("no_self_defeating_steps", {criterion.criterion_id for criterion in criteria.criteria})
        self.assertIn("imported", instructions.every_reviewer())

    def test_a_large_population_selects_the_minhash_engine(self):
        config = imported_profile.configuration(BASE, population_size=10000)
        self.assertEqual(tuple(config.policy.prechecks["duplicates"]), ("imported_minhash_rules",))


if __name__ == "__main__":
    unittest.main()
