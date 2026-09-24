"""Checks for the trust tier of catalogue items: publishing, serving and the older-reader guards.

Each known-wrong case is refused with its own code, and a removed-guard
control reruns the case with the guard patched away and requires the check's
own predicate to fail. Every check runs against a real temporary service store
and body folder. No network, model or provider is used.
"""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

from ..provisioning_server import (COMMUNITY_EXCLUDED, COMMUNITY_INCLUDED, COMMUNITY_WITHOUT_RUNNABLE,
                                   LIST_RECORD_TYPE, tierless_answer)
from . import catalogue_bundle, catalogue_releases, catalogue_tiers
from .catalogue_packages import CataloguePackage, CataloguePackageFile, sha256_hex
from .catalogue_release_checks import bundle_line, fixture, refused
from .catalogue_tiers import ADMISSION_RECORD_TYPE, COMMUNITY_CRITERIA, CommunityAdmission, LibrarySettings, narrowed

SKILL = b"---\nname: tidy-columns\ndescription: Tidy the columns of a table.\nlicense: MIT\n---\n# Tidy columns\n"
LICENCE = b"MIT License\n\nCopyright (c) 2026 Example Author\n\nPermission is hereby granted, free of charge...\n"
SCRIPT = b"#!/bin/sh\necho tidy\n"
REVISION = "0123456789abcdef0123456789abcdef01234567"


def community_files(runnable=False):
    files = [("LICENSE", LICENCE, "text/plain", "other"), ("SKILL.md", SKILL, "text/markdown", "skill_definition")]
    if runnable:
        files.append(("scripts/tidy.sh", SCRIPT, "text/x-shellscript", "skill_script"))
    return files


def admission_for(package_files, **changes):
    """A `community_admission/v1` record that the written criteria accept for exactly these files."""
    files = package_files
    entries = tuple(CataloguePackageFile(path, sha256_hex(data), len(data), media, role)
                    for path, data, media, role in files)
    package = CataloguePackage(entries, "package")
    value = {"record_type": ADMISSION_RECORD_TYPE, "criteria_digest": COMMUNITY_CRITERIA.digest,
             "package_digest": package.served_digest, "producer": "library_ingestion:run-2026-09-24",
             "admitted_by": "community_admission:criteria-v1", "admitted_at": "2026-09-24",
             "files": [{"path": path, "digest": sha256_hex(data), "spdx": "MIT",
                        "licence_decision": "verbatim_permitted",
                        "source": {"origin": "github_repository", "repository": "example/skills",
                                   "immutable_revision": REVISION, "path": "skills/tidy/" + path,
                                   "source_digest": sha256_hex(data), "fetched_at": "2026-09-24T12:00:00Z"}}
                       for path, data, _media, _role in files],
             "licence_file": "LICENSE", "attribution": "Copyright (c) 2026 Example Author; example/skills at 0123456",
             "scanners": [{"engine": "builtin_static_rules", "version": "1", "result": "passed"},
                          {"engine": "skillspector_static", "version": "1", "result": "passed"}],
             "execution": "none"}
    value.update(changes)
    return value


def community_line(identity, files=None, *, admission=None, effects=(), approval_ref=None):
    files = files or community_files()
    line = bundle_line(identity, files, effects=effects)
    record = admission if admission is not None else admission_for(files)
    reference = approval_ref or f"{ADMISSION_RECORD_TYPE}:{CommunityAdmission.from_dict(record).digest}"
    served = CataloguePackage.from_dict(line["package"]).served_digest
    return {**line, "approval": {"tier": "community", "approval_ref": reference, "approved_digest": served,
                                 "admission": record}}


def _with_bytes(case, identity, files):
    case._bytes = {**case._bytes, identity: tuple(data for _path, data, _media, _role in files)}


def run_checks(check):
    """Tier checks, grouped so that one failing group is recorded by name and the others still run."""
    for name, group in (("publishing", _publishing_checks), ("serving", _serving_checks),
                        ("older_readers", _older_reader_checks), ("library_setting", _setting_checks)):
        try:
            group(check)
        except Exception:  # noqa: BLE001 - a group that stops part way is a failure with a name
            check(f"the_tier_{name}_checks_ran_to_completion", False)


def _accepted(case, line, files):
    """Whether a bundle holding this line is read without a refusal, and the refusal code if not."""
    _with_bytes(case, line["reference"]["identity"], files)
    case.payloads = [data for _path, data, _media, _role in files]
    try:
        case.bundle([line])
    except catalogue_bundle.ServiceRuntimeError as error:
        return error.code
    except Exception as error:  # noqa: BLE001 - with a guard removed, a crash is a different answer, not a refusal
        return "crashed:" + type(error).__name__
    return "accepted"


def _publishing_checks(check):
    files = community_files()
    wrong = {
        "admission_not_independent": {"admitted_by": "library_ingestion:admission"},
        "community_licence_not_allowed": {"files": [
            {**entry, "spdx": "GPL-3.0-only"} for entry in admission_for(files)["files"]]},
        "community_provenance_unpinned": {"files": [
            {**entry, "source": {**entry["source"], "immutable_revision": "main"}}
            for entry in admission_for(files)["files"]]},
        "community_scan_insufficient": {"scanners": [
            {"engine": "builtin_static_rules", "version": "1", "result": "passed"}]},
        "community_scan_blocked": {"scanners": admission_for(files)["scanners"] + [
            {"engine": "third_scanner", "version": "1", "result": "blocked"}]},
        "community_licence_text_missing": {"licence_file": ""},
        "community_criteria_mismatch": {"criteria_digest": "0" * 64},
        "admission_not_bound_to_bytes": {"package_digest": "1" * 64},
        "community_admission_path_invalid": {"execution": "sandboxed"},
    }
    with fixture() as case:
        valid = community_line("tidy_columns", files)
        check("a_community_item_whose_admission_meets_the_written_criteria_is_accepted",
              _accepted(case, valid, files) == "accepted")
        for code, change in wrong.items():
            line = community_line("tidy_columns", files, admission=admission_for(files, **change))
            check("a_community_admission_that_fails_the_criteria_is_refused_" + code,
                  _accepted(case, line, files) == code)
        other_reference = community_line("tidy_columns", files, approval_ref=f"{ADMISSION_RECORD_TYPE}:{'2' * 64}")
        check("a_community_approval_names_the_digest_of_its_own_admission",
              _accepted(case, other_reference, files) == "community_approval_reference_mismatch")
        bare = {**valid, "approval": {key: value for key, value in valid["approval"].items() if key != "admission"}}
        check("a_community_approval_without_its_admission_is_refused",
              _accepted(case, bare, files) == "community_admission_required")
        untiered = {**valid, "approval": {key: value for key, value in valid["approval"].items()
                                          if key not in ("tier", "admission")}}
        check("an_approval_that_names_no_tier_is_refused", _accepted(case, untiered, files) == "catalogue_item_tier_invalid")
        self_admitted = community_line("tidy_columns", files, admission=admission_for(
            files, admitted_by="library_ingestion:admission"))
        with patch.object(catalogue_bundle, "community_admission_refusal", lambda admission, item, package: ""):
            check("removed_community_criteria_are_detected", _accepted(case, self_admitted, files) == "accepted")
        with patch.object(catalogue_bundle, "tier_refusal", lambda approval, item, package: ""):
            check("removed_tier_rule_is_detected", _accepted(case, untiered, files) != "catalogue_item_tier_invalid")
        runnable = community_files(runnable=True)
        undeclared = community_line("tidy_columns_runs", runnable)
        check("a_community_package_with_a_script_still_declares_the_process_effect",
              _accepted(case, undeclared, runnable) == "package_executable_effect_undeclared")


def _published(case, *, runnable=False):
    """Publish one verified skill and one community skill (and a runnable community skill when asked)."""
    verified = case.line("verified_skill", "# A reviewed skill\n")
    files = community_files()
    lines = [verified, community_line("community_skill", files)]
    payloads = {"community_skill": files}
    if runnable:
        running = community_files(runnable=True)
        lines.append(community_line("community_runs", running, effects=("spawns_process",)))
        payloads["community_runs"] = running
    for identity, entries in payloads.items():
        _with_bytes(case, identity, entries)
    return case.publish(lines)


def _serving_checks(check):
    with fixture() as case:
        published = _published(case, runnable=True)
        binding = case.binding()

        def listed(choice, effects=("spawns_process",)):
            answer = binding.invoke(case.key.key, "list", community_items=choice, authority_effects=effects)
            return [(row["identity"], row["trust_tier"]) for row in answer["items"]]
        check("a_community_release_is_published_and_raises_the_catalogue_state_version",
              published["state"] == "published" and case_state_version(case) == 2)
        check("verified_items_come_first_and_every_row_names_its_tier",
              listed(COMMUNITY_INCLUDED) == [("verified_skill", "baltor_verified"),
                                             ("community_runs", "community"), ("community_skill", "community")])
        check("the_default_offers_community_text_and_leaves_out_community_files_that_run",
              listed(COMMUNITY_WITHOUT_RUNNABLE) == [("verified_skill", "baltor_verified"),
                                                     ("community_skill", "community")])
        check("a_request_that_says_nothing_receives_verified_items_only",
              [row["identity"] for row in binding.invoke(case.key.key, "list")["items"]] == ["verified_skill"])
        manifest = binding.invoke(case.key.key, "manifest", identity="community_skill",
                                  community_items=COMMUNITY_WITHOUT_RUNNABLE)
        view = case.view()
        attribution = view.attribution("community_skill")
        check("a_community_manifest_names_its_tier_and_its_licence_file_and_attribution_travel_with_it",
              manifest["trust_tier"] == "community" and attribution["licence_file"] == "LICENSE"
              and attribution["licences"] == ["MIT"] and attribution["executed_by_baltor"] is False
              and "LICENSE" in [entry["path"] for entry in view.package_summary("community_skill")["files"]]
              and view.attribution("verified_skill") is None)
        refused_old = refused(lambda: tierless_answer(binding.invoke(
            case.key.key, "list", community_items=COMMUNITY_WITHOUT_RUNNABLE)), "tier_required_by_answer")
        legacy = tierless_answer(binding.invoke(case.key.key, "list"))
        check("a_reader_of_version_2_answers_never_receives_a_community_item",
              refused_old and legacy["record_type"] == LIST_RECORD_TYPE
              and [row["identity"] for row in legacy["items"]] == ["verified_skill"]
              and all("trust_tier" not in row for row in legacy["items"]))
        with patch("loop_engine.core.provisioning_server.in_library", lambda item, decision, choice: True):
            leaked = [row["identity"] for row in binding.invoke(case.key.key, "list")["items"]]
            check("removed_verified_only_default_is_detected", "community_skill" in leaked)


def case_state_version(case):
    binding = case.context.binding
    with binding.store() as store:
        _row, state = catalogue_releases.read_state(binding, store)
    return state["state_version"]


def _older_reader_checks(check):
    with fixture() as case:
        case.publish([case.line("verified_only", "# Only reviewed material\n")])
        binding = case.context.binding
        with binding.store() as store:
            rows = binding.rows_all(store, catalogue_releases.ITEM_KIND)
        check("a_verified_only_release_keeps_state_version_one_and_version_one_item_records",
              case_state_version(case) == 1
              and {row["payload"]["record_type"] for row in rows} == {"catalogue_item_version/v1"})
        _published(case)
        with patch.object(catalogue_releases, "SUPPORTED_CATALOGUE_STATE_VERSIONS", (1,)):
            check("an_image_that_predates_community_items_refuses_to_start_on_a_store_that_holds_them",
                  refused(case.view, "catalogue_state_version_unsupported"))
        def load_active():
            with binding.store() as store:
                _row, pointer = catalogue_releases.read_pointer(binding, store)
                return catalogue_releases.load_release(binding, store, pointer["release_id"])
        with patch.object(catalogue_releases, "ITEM_VERSION_RECORD_TYPES", ("catalogue_item_version/v1",)):
            check("a_reader_of_version_one_item_records_refuses_a_community_item_version",
                  refused(load_active, "catalogue_record_unsupported"))
    with fixture() as case:
        with patch.object(catalogue_releases, "COMMUNITY_STATE_VERSION", 1):
            _published(case)
        with patch.object(catalogue_releases, "SUPPORTED_CATALOGUE_STATE_VERSIONS", (1,)):
            started = not refused(case.view, "catalogue_state_version_unsupported")
        check("removed_state_version_raise_is_detected", started)
    with fixture() as case:
        _published(case)
        stricter = replace(COMMUNITY_CRITERIA, minimum_passing_scanners=3)
        with patch.object(catalogue_tiers, "COMMUNITY_CRITERIA", stricter):
            check("an_admission_made_under_other_criteria_is_refused_when_the_view_is_built",
                  refused(case.view, "community_criteria_mismatch"))
        with patch.object(catalogue_tiers, "COMMUNITY_CRITERIA", stricter), \
                patch.object(catalogue_tiers, "community_admission_refusal", lambda admission, item, package: ""):
            check("removed_criteria_recheck_at_view_build_is_detected", not refused(case.view))


def _setting_checks(check):
    settings = LibrarySettings()
    check("the_default_library_setting_offers_community_text_without_runnable_files",
          settings.community_items == COMMUNITY_WITHOUT_RUNNABLE
          and narrowed(settings, None) == COMMUNITY_WITHOUT_RUNNABLE
          and narrowed(settings, ["baltor_verified"]) == COMMUNITY_EXCLUDED
          and narrowed(LibrarySettings(COMMUNITY_EXCLUDED), ["baltor_verified", "community"]) == COMMUNITY_EXCLUDED)
    check("a_request_can_narrow_the_library_setting_but_never_widen_it",
          narrowed(LibrarySettings(COMMUNITY_WITHOUT_RUNNABLE), ["community"]) == COMMUNITY_WITHOUT_RUNNABLE
          and refused(lambda: narrowed(settings, ["community", "community"]), "trust_tiers_invalid")
          and refused(lambda: narrowed(settings, ["reviewed"]), "trust_tiers_invalid")
          and refused(lambda: LibrarySettings("everything"), "library_settings_invalid"))
    check("the_published_legend_names_each_tier_with_its_exact_label_and_the_criteria_digest",
          [row["label"] for row in catalogue_tiers.tier_legend()["tiers"]] == ["Baltor verified", "Community"]
          and catalogue_tiers.tier_legend()["community_criteria"]["digest"] == COMMUNITY_CRITERIA.digest)
    check("criteria_that_accept_a_single_scanner_or_running_the_package_are_refused",
          refused(lambda: replace(COMMUNITY_CRITERIA, minimum_passing_scanners=1), "community_criteria_invalid")
          and refused(lambda: replace(COMMUNITY_CRITERIA, execution="sandbox"), "community_criteria_invalid"))


__all__ = ["run_checks"]
