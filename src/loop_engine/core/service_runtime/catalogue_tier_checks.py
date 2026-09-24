"""Checks for the library tier of catalogue items: publishing, serving, labels and the older-reader guards.

Each known-wrong case is refused with its own code, and a removed-guard
control reruns the case with the guard patched away and requires the check's
own predicate to fail. Every check runs against a real temporary service store
and body folder. No network, model or provider is used.
"""
from __future__ import annotations

from unittest.mock import patch

from ..provisioning_server import (COMMUNITY_EXCLUDED, COMMUNITY_INCLUDED, COMMUNITY_WITHOUT_RUNNABLE,
                                   LIST_RECORD_TYPE, TIER_LABELS, tierless_answer)
from . import catalogue_bundle, catalogue_releases, catalogue_tiers
from .catalogue_release_checks import bundle_line, fixture, refused
from .catalogue_tiers import LibrarySettings, narrowed

SKILL = b"---\nname: tidy-columns\ndescription: Tidy the columns of a table.\nlicense: MIT\n---\n# Tidy columns\n"
LICENCE = b"MIT License\n\nCopyright (c) 2026 Example Author\n\nPermission is hereby granted, free of charge...\n"
SCRIPT = b"#!/bin/sh\necho tidy\n"


def community_files(runnable=False):
    files = [("LICENSE", LICENCE, "text/plain", "other"), ("SKILL.md", SKILL, "text/markdown", "skill_definition")]
    if runnable:
        files.append(("scripts/tidy.sh", SCRIPT, "text/x-shellscript", "skill_script"))
    return files


def community_line(identity, files=None, *, effects=()):
    files = files or community_files()
    line = bundle_line(identity, files, effects=effects)
    return {**line, "approval": {**line["approval"], "tier": "community"}}


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
    with fixture() as case:
        valid = community_line("tidy_columns", files)
        check("a_community_approval_that_names_its_tier_is_accepted", _accepted(case, valid, files) == "accepted")
        untiered = {**valid, "approval": {key: value for key, value in valid["approval"].items() if key != "tier"}}
        check("an_approval_that_names_no_tier_is_refused", _accepted(case, untiered, files) == "library_tier_required")
        unknown = {**valid, "approval": {**valid["approval"], "tier": "reviewed_by_a_friend"}}
        check("an_approval_that_names_an_unknown_tier_is_refused",
              _accepted(case, unknown, files) == "library_tier_invalid")
        with patch.object(catalogue_bundle, "tier_refusal", lambda approval: ""):
            check("removed_tier_rule_is_detected", _accepted(case, unknown, files) != "library_tier_invalid")
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
            return [(row["identity"], row["library_tier"], row["library_tier_label"]) for row in answer["items"]]
        check("a_community_release_is_published_and_raises_the_catalogue_state_version",
              published["state"] == "published" and case_state_version(case) == 2)
        check("verified_items_come_first_and_every_row_names_its_tier_and_exact_label",
              listed(COMMUNITY_INCLUDED) == [("verified_skill", "verified", "Verified"),
                                             ("community_runs", "community", "Community"),
                                             ("community_skill", "community", "Community")])
        check("the_runnable_choice_leaves_out_community_files_that_run",
              listed(COMMUNITY_WITHOUT_RUNNABLE) == [("verified_skill", "verified", "Verified"),
                                                     ("community_skill", "community", "Community")])
        check("a_request_that_says_nothing_receives_verified_items_only",
              [row["identity"] for row in binding.invoke(case.key.key, "list")["items"]] == ["verified_skill"])
        manifest = binding.invoke(case.key.key, "manifest", identity="community_skill",
                                  community_items=COMMUNITY_INCLUDED)
        body = binding.invoke(case.key.key, "read", identity="community_skill", request_id="tier-check-read",
                              community_items=COMMUNITY_INCLUDED)
        check("a_community_manifest_and_body_name_their_tier_and_label",
              (manifest["library_tier"], manifest["library_tier_label"]) == ("community", "Community")
              and (body["library_tier"], body["library_tier_label"]) == ("community", "Community"))
        refused_old = refused(lambda: tierless_answer(binding.invoke(
            case.key.key, "list", community_items=COMMUNITY_INCLUDED)), "tier_required_by_answer")
        legacy = tierless_answer(binding.invoke(case.key.key, "list"))
        check("a_reader_of_version_2_answers_never_receives_a_community_item",
              refused_old and legacy["record_type"] == LIST_RECORD_TYPE
              and [row["identity"] for row in legacy["items"]] == ["verified_skill"]
              and all("library_tier" not in row for row in legacy["items"]))
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


def _setting_checks(check):
    settings = LibrarySettings()
    check("the_default_library_setting_receives_every_community_item_labelled",
          settings.community_items == COMMUNITY_INCLUDED and narrowed(settings, None) == COMMUNITY_INCLUDED)
    check("the_verified_filter_excludes_community_items_and_never_widens_the_account",
          narrowed(settings, ["verified"]) == COMMUNITY_EXCLUDED
          and narrowed(settings, ["verified", "community"]) == COMMUNITY_INCLUDED
          and narrowed(LibrarySettings(COMMUNITY_EXCLUDED), ["verified", "community"]) == COMMUNITY_EXCLUDED)
    check("a_filter_that_drops_verified_items_or_repeats_or_names_an_unknown_tier_is_refused",
          refused(lambda: narrowed(settings, ["community"]), "library_tiers_invalid")
          and refused(lambda: narrowed(settings, ["verified", "verified"]), "library_tiers_invalid")
          and refused(lambda: narrowed(settings, ["verified", "reviewed"]), "library_tiers_invalid")
          and refused(lambda: narrowed(settings, "verified"), "library_tiers_invalid")
          and refused(lambda: LibrarySettings("everything"), "library_settings_invalid"))
    check("the_published_legend_names_each_tier_with_its_exact_label",
          [row["label"] for row in catalogue_tiers.tier_legend()["tiers"]] == ["Verified", "Community"]
          and TIER_LABELS == {"verified": "Verified", "community": "Community"})


__all__ = ["run_checks"]
