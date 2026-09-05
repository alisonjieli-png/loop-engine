"""Offline checks for the read-only Kaggle access preflight.

The fixture proves population freezing, authority refusal, exact accounting,
and failure preservation. It performs no network request or Kaggle effect.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import replace

from preflight import (
    CommandResult,
    KagglePreflightRequest,
    _digest,
    _list_command,
    _parser,
    _validate_destinations,
    freeze_population,
    probe_competition_files,
    run_preflight,
    run_preflight_as_loop,
    write_report,
)


class FixtureRunner:
    """Deterministic Kaggle CLI fixture with a visible command history."""

    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, argv: tuple[str, ...], _timeout: int) -> CommandResult:
        self.commands.append(argv)
        if argv[2] == "list":
            page = int(argv[argv.index("--page") + 1])
            rows = {
                1: [
                    {"ref": "https://www.kaggle.com/competitions/a",
                     "userHasEntered": True},
                    {"ref": "https://www.kaggle.com/competitions/b",
                     "userHasEntered": True},
                ],
                2: [
                    {"ref": "https://www.kaggle.com/competitions/b",
                     "userHasEntered": True},
                    {"ref": "https://www.kaggle.com/competitions/c",
                     "userHasEntered": True},
                    {"ref": "https://www.kaggle.com/competitions/d",
                     "userHasEntered": True},
                ],
            }.get(page, [])
            return CommandResult(argv, 0, json.dumps(rows), "")
        slug = argv[3]
        if slug == "a":
            return CommandResult(argv, 0, json.dumps([
                {"name": "train.csv", "size": 10},
                {"name": "test.csv", "size": 8},
            ]), "")
        if slug == "b":
            return CommandResult(argv, 1, "", "403 rules not accepted")
        if slug == "d":
            return CommandResult(argv, 1, "", "429 Too Many Requests")
        return CommandResult(argv, 0, "not-json", "")


def self_test() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    denied_runner = FixtureRunner()
    denied = False
    try:
        freeze_population(KagglePreflightRequest("denied"), denied_runner)
    except PermissionError:
        denied = True
    check("network_authority_is_required_before_any_cli_call",
          denied and not denied_runner.commands)
    non_boolean_refused = False
    try:
        KagglePreflightRequest("bad-bool", authorize_network_reads="false")
    except ValueError:
        non_boolean_refused = True
    check("network_authority_must_be_an_exact_boolean", non_boolean_refused)

    runner = FixtureRunner()
    request = KagglePreflightRequest(
        "fixture", target_competitions=4, maximum_pages=3,
        page_size=2, concurrency=1, probe_delay_seconds=0,
        authorize_network_reads=True)
    population = freeze_population(request, runner)
    check("population_is_frozen_before_probes_and_deduplicated",
          [item["slug"] for item in population["selected"]]
          == ["a", "b", "c", "d"] and population["target_met"])
    check("population_has_a_stable_digest",
          population["population_digest"]
          == freeze_population(request, FixtureRunner())["population_digest"])

    runner = FixtureRunner()
    report = run_preflight(request, runner)
    check("every_selected_competition_is_probed_once",
          report["summary"]["selected_denominator"] == 4
          and report["summary"]["file_probes_attempted"] == 4)
    check("success_refusal_rate_limit_and_invalid_json_are_kept_apart",
          report["summary"]["status_counts"] == {
              "access_refused": 1,
              "files_accessible": 1,
              "rate_limited": 1,
              "response_invalid": 1,
          })
    check("the_campaign_performs_no_download_submission_or_model_call",
          report["summary"]["downloads"] == 0
          and report["summary"]["submissions"] == 0
          and report["summary"]["model_calls"] == 0
          and all("download" not in command and "submit" not in command
                  for command in runner.commands))
    check("physical_cli_requests_match_the_command_history",
          report["summary"]["physical_cli_requests"] == len(runner.commands))
    check("failures_remain_in_the_denominator",
          len(report["probes"]) == 4
          and sum(item["status"] != "files_accessible"
                  for item in report["probes"]) == 3)

    cursor_result = CommandResult(
        ("kaggle", "competitions", "files", "cursor"), 0,
        'Next Page Token = opaque403cursor\n[{"name":"train.csv","size":7}]',
        "")
    cursor_probe = probe_competition_files(
        {"selection_rank": 1, "slug": "cursor"}, request,
        lambda _argv, _timeout: cursor_result)
    invalid_cursor_result = replace(cursor_result, stdout=(
        "Next Page Token = opaque403cursor\nnot-json"))
    invalid_cursor_probe = probe_competition_files(
        {"selection_rank": 1, "slug": "cursor"}, request,
        lambda _argv, _timeout: invalid_cursor_result)
    check("pagination_preamble_is_parsed_without_status_code_guessing",
          cursor_probe["status"] == "files_accessible"
          and cursor_probe["next_page_available"]
          and cursor_probe["may_be_truncated"]
          and invalid_cursor_probe["status"] == "response_invalid"
          and "opaque403cursor" not in json.dumps(invalid_cursor_probe)
          and "response_preview" not in invalid_cursor_probe)
    empty_probe = probe_competition_files(
        {"selection_rank": 1, "slug": "empty"}, request,
        lambda argv, _timeout: CommandResult(argv, 0, "[]", ""))
    check("an_empty_readable_listing_is_not_a_nonempty_metadata_success",
          empty_probe["status"] == "files_listing_empty"
          and empty_probe["access_response_readable"]
          and empty_probe["file_count_returned"] == 0)
    secret_text = "Authorization: Bearer do-not-record-this"
    secret_probe = probe_competition_files(
        {"selection_rank": 1, "slug": "secret"}, request,
        lambda argv, _timeout: CommandResult(argv, 1, "", secret_text))
    check("provider_error_text_and_tokens_are_not_persisted",
          "do-not-record-this" not in json.dumps(secret_probe)
          and "Authorization" not in json.dumps(secret_probe)
          and "response_preview" not in secret_probe)
    secret_list = freeze_population(
        request,
        lambda argv, _timeout: CommandResult(argv, 1, "", secret_text))
    check("list_failure_text_and_tokens_are_not_persisted",
          "do-not-record-this" not in json.dumps(secret_list)
          and "Authorization" not in json.dumps(secret_list))

    denied_probe_runner = FixtureRunner()
    direct_probe_refused = False
    try:
        probe_competition_files(
            {"selection_rank": 1, "slug": "a"},
            replace(request, authorize_network_reads=False),
            denied_probe_runner)
    except PermissionError:
        direct_probe_refused = True
    check("direct_probe_rechecks_authority_at_the_effect_boundary",
          direct_probe_refused and not denied_probe_runner.commands)

    with tempfile.TemporaryDirectory(prefix="kaggle-preflight-test-") as root:
        output = os.path.join(root, "report.json")
        write_report(report, output, root)
        with open(output, encoding="utf-8") as handle:
            restored = json.load(handle)
        check("atomic_report_round_trip_preserves_the_digest",
              restored["report_digest"] == report["report_digest"])
        retry_runner = FixtureRunner()
        resumed = run_preflight(
            replace(request, resume_report_path=output, workspace_root=root),
            retry_runner)
        check("resume_retries_transient_results_but_keeps_hard_refusals",
              resumed["population"]["population_digest"]
                  == report["population"]["population_digest"]
              and resumed["summary"]["list_calls"] == 0
              and resumed["summary"]["file_probe_calls"] == 2
              and resumed["summary"]["prior_probe_results_reused"] == 2
              and len(retry_runner.commands) == 2
              and resumed["retry_lineage"]["parent_report_digest"]
                  == report["report_digest"])
        legacy = json.loads(json.dumps(report))
        legacy_probe = next(
            item for item in legacy["probes"]
            if item["status"] == "files_accessible")
        legacy_probe.update(
            file_count_returned=0, known_total_bytes=0, files=[])
        legacy.pop("report_digest")
        legacy["report_digest"] = _digest(legacy)
        legacy_path = os.path.join(root, "legacy-empty.json")
        write_report(legacy, legacy_path, root)
        migrated = run_preflight(
            replace(request, resume_report_path=legacy_path,
                    workspace_root=root), FixtureRunner())
        migrated_probe = next(
            item for item in migrated["probes"]
            if item["slug"] == legacy_probe["slug"])
        check("legacy_empty_success_is_migrated_without_a_false_file_claim",
              migrated_probe["status"] == "files_listing_empty"
              and len(migrated["retry_lineage"]["reader_migrations"]) == 1)
        denied_resume_runner = FixtureRunner()
        denied_resume = False
        try:
            run_preflight(
                replace(request, resume_report_path=output,
                        workspace_root=root, authorize_network_reads=False),
                denied_resume_runner)
        except PermissionError:
            denied_resume = True
        check("resume_cannot_bypass_network_authority",
              denied_resume and not denied_resume_runner.commands)
        semantics_refused = False
        try:
            run_preflight(
                replace(request, resume_report_path=output,
                        workspace_root=root, group="general"),
                FixtureRunner())
        except ValueError:
            semantics_refused = True
        check("resume_preserves_frozen_selection_and_privacy_semantics",
              semantics_refused)
        overwrite_refused = False
        try:
            write_report(report, output, root)
        except FileExistsError:
            overwrite_refused = True
        check("report_write_refuses_overwrite", overwrite_refused)

    with tempfile.TemporaryDirectory(
            prefix="kaggle-preflight-loop-test-") as root:
        loop_report = run_preflight_as_loop(
            replace(request, workspace_root=root),
            os.path.join(root, "runs"), FixtureRunner())
        execution = loop_report["loop_execution"]
        check("campaign_and_metadata_reads_execute_through_Loops",
              execution["model_calls"] == 0
              and execution["run_history_chain"]["intact"]
              and execution["tool_attempt_events"]
                  == loop_report["summary"]["physical_cli_requests"]
              and execution["tool_success_events"]
                  + execution["tool_failure_events"]
                  == execution["tool_attempt_events"]
              and execution["retrieval_events"]
                  == execution["tool_success_events"]
              and os.path.isdir(execution["run_history_path"])
              and (os.stat(execution["run_history_path"]).st_mode & 0o777)
                  == 0o700
              and all((os.stat(os.path.join(
                      execution["run_history_path"], name)).st_mode & 0o777)
                      == 0o600 for name in ("manifest.json", "events.jsonl")))
        with open(os.path.join(
                execution["run_history_path"], "events.jsonl"),
                encoding="utf-8") as handle:
            history_events = [json.loads(line) for line in handle]
        network_loops = [event for event in history_events
                         if event["detail"].get("baseline_goal")
                         == "kaggle_metadata_read"]
        bindings = [event for event in history_events
                    if event["detail"].get("_ledger_event")
                    == "information.binding.published"]
        tool_starts = [event for event in history_events
                       if event["detail"].get("_ledger_event")
                       == "tool_invocation_started"]
        approved_ids = {
            event["detail"].get("request_id") for event in history_events
            if (event["detail"].get("_ledger_event")
                == "effect_approval_decided"
                and event["detail"].get("action") == "approve")}
        check("network_effects_and_report_core_binding_are_in_run_history",
              len(network_loops) == execution["tool_attempt_events"]
              and all(event["detail"].get("role") == "intelligence"
                      and event["detail"].get("relationship_kind")
                      == "queried_by" for event in network_loops)
              and len(bindings) == 1
              and bindings[0]["detail"].get("content_digest")
                  == execution["report_core_digest"]
              and len(tool_starts) == execution["tool_attempt_events"]
              and all(event["detail"].get("declared_effect") == "network"
                      and event["detail"].get("effect_class") == "network_read"
                      and event["detail"].get("approval_request_id")
                      in approved_ids for event in tool_starts))
        collision_runner = FixtureRunner()
        collision_refused = False
        try:
            run_preflight_as_loop(
                replace(request, workspace_root=root),
                os.path.join(root, "runs"), collision_runner)
        except FileExistsError:
            collision_refused = True
        check("run_history_collision_is_refused_before_external_calls",
              collision_refused and not collision_runner.commands)
        overlap_refused = False
        try:
            _validate_destinations(
                replace(request, workspace_root=root),
                os.path.join(root, "same"), os.path.join(root, "same"))
        except ValueError:
            overlap_refused = True
        nested_refused = False
        try:
            _validate_destinations(
                replace(request, workspace_root=root),
                os.path.join(root, "runs", "fixture", "manifest.json"),
                os.path.join(root, "runs"))
        except ValueError:
            nested_refused = True
        check("output_and_run_history_destinations_cannot_overlap",
              overlap_refused and nested_refused)

    unowned_real_runner_refused = False
    try:
        run_preflight(KagglePreflightRequest(
            "unowned", target_competitions=1, maximum_pages=1,
            page_size=1, concurrency=1, authorize_network_reads=True))
    except ValueError:
        unowned_real_runner_refused = True
    check("real_network_runner_cannot_execute_outside_a_Loop",
          unowned_real_runner_refused)

    tests.extend(_search_checks())
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "kaggle_access_preflight_test/v1",
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
        "network_requests": 0,
        "model_calls": 0,
        "submissions": 0,
    }


def _search_checks() -> list[dict]:
    """Search is explicit selection identity, never a solve-routing rule."""
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed), "detail": "offline fixture"})

    request = KagglePreflightRequest(
        "search-fixture", target_competitions=4, maximum_pages=3,
        page_size=2, concurrency=1, authorize_network_reads=True)
    search = "playground-series-s6e9"
    selected = replace(request, search=search)
    expected = (
        "kaggle", "competitions", "list", "--group", "entered",
        "--sort-by", "prize", "--page", "1", "--page-size", "2",
        "--format", "json")
    cli_required = ["--campaign-id", "fixture", "--workspace-root", "/fixture",
                    "--output", "/fixture/report.json", "--runs-dir", "/fixture/runs"]
    check("absent_search_preserves_existing_cli_command_and_default",
          request.search == "" and _list_command(request, 1) == expected
          and _parser().parse_args(cli_required).search == "")
    check("explicit_search_is_one_exact_kaggle_argument_value",
          _list_command(selected, 1) == expected + ("--search", search)
          and _parser().parse_args(cli_required + ["--search", search]).search == search
          and _list_command(replace(request, search="two words"), 1)[-2:]
          == ("--search", "two words"))
    invalid = 0
    for value in (None, True, 1, [], " ", " leading", "trailing ",
                  "line\nbreak", "tab\tinside", "nul\x00inside", "\ud800"):
        try:
            replace(request, search=value)
        except ValueError:
            invalid += 1
    check("invalid_search_types_whitespace_controls_and_encoding_are_refused",
          invalid == 11)

    runner = FixtureRunner()
    report = run_preflight(selected, runner)
    unfiltered = run_preflight(request, FixtureRunner())
    check("search_is_bound_in_request_population_and_population_digest",
          report["request"]["search"] == report["population"]["search"] == search
          and report["population"]["selected"] == unfiltered["population"]["selected"]
          and report["population"]["population_digest"]
          != unfiltered["population"]["population_digest"]
          and all(command[-2:] == ("--search", search)
                  for command in runner.commands if command[2] == "list"))

    with tempfile.TemporaryDirectory(prefix="kaggle-search-check-") as root:
        loop_runner = FixtureRunner()
        loop_report = run_preflight_as_loop(
            replace(selected, workspace_root=root), os.path.join(root, "runs"),
            loop_runner)
        check("search_survives_canonical_Loop_owned_preflight_and_report_binding",
              loop_report["request"]["search"] == loop_report["population"]["search"] == search
              and loop_report["loop_execution"]["run_history_chain"]["intact"]
              and all(command[-2:] == ("--search", search)
                      for command in loop_runner.commands if command[2] == "list"))
        filtered_path = os.path.join(root, "filtered.json")
        write_report(report, filtered_path, root)
        runner = FixtureRunner()
        resumed = run_preflight(replace(
            selected, resume_report_path=filtered_path, workspace_root=root), runner)
        check("resume_with_same_search_keeps_frozen_population_without_relisting",
              resumed["population"] == report["population"]
              and resumed["request"]["search"] == search
              and not any(command[2] == "list" for command in runner.commands))
        mismatches_refused = 0
        for changed in ("", "another-query"):
            runner = FixtureRunner()
            try:
                run_preflight(replace(
                    selected, search=changed, resume_report_path=filtered_path,
                    workspace_root=root), runner)
            except ValueError:
                mismatches_refused += not bool(runner.commands)
        check("resume_cannot_drop_or_change_a_frozen_search_filter",
              mismatches_refused == 2)

        legacy = json.loads(json.dumps(unfiltered))
        legacy["request"].pop("search")
        population = legacy["population"]
        population.pop("search")
        population["population_digest"] = _digest({
            key: population[key] for key in (
                "record_type", "group", "sort_by", "page_size",
                "target_competitions", "selected", "list_failures")})
        legacy.pop("report_digest")
        legacy["report_digest"] = _digest(legacy)
        legacy_path = os.path.join(root, "legacy.json")
        write_report(legacy, legacy_path, root)
        resumed_legacy = run_preflight(replace(
            request, resume_report_path=legacy_path, workspace_root=root), FixtureRunner())
        check("legacy_absent_search_resumes_as_unfiltered_without_rehashing_population",
              resumed_legacy["population"] == legacy["population"]
              and resumed_legacy["request"]["search"] == "")
        runner = FixtureRunner()
        refused = False
        try:
            run_preflight(replace(
                selected, resume_report_path=legacy_path, workspace_root=root), runner)
        except ValueError:
            refused = True
        check("legacy_population_cannot_acquire_a_new_search_on_resume",
              refused and not runner.commands)
    return tests


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2, sort_keys=True))
