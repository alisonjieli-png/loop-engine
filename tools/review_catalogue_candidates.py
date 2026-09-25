"""Put catalogue candidates to the independent review panel and write a dated review record.

The command reads the panel's declared resources, selects a population of
candidates by a declared rule, runs the deterministic pre-checks, optionally
calibrates every eligible reviewer on known-wrong and known-good items, asks
the reviewers within one declared ceiling of calls and tokens for the whole
command, and writes a dated review record beside the catalogue's ``reviews.json``.
It never edits ``reviews.json``, the item file, the bodies or a host manifest.

No model is called without ``--authorize-model-calls``. Without it the command
runs the pre-checks and reports what it would have asked, and no credential is
resolved. A stopped command can be run again with the same ledger: it reuses
every verdict already given and never repeats a call that was dispatched and
not completed.

Run limits and modes, each recorded in the summary:

- ``--batch-size INSTALLATION=N`` asks that reviewer about up to N items in one
  call (the calibration decides whether a reviewer may be asked this way);
- ``--quota-group-ceiling GROUP=N`` stops a quota group after N calls in this
  command while other groups continue;
- ``--stop-after-repeated-failures N`` stops asking an installation that failed
  the same way N calls in a row;
- ``--exclude-installation ID=REASON`` keeps an installation out of this
  command with a written reason, for example a spent allowance;
- ``--collect-below-quorum REASON`` asks each reachable family once although
  the reachable families cannot reach the quorum; the approval rule is
  unchanged and the verdicts wait in the ledger for the missing families;
- ``--calibrate-only`` runs the calibration and no real candidate.

The dated review record does not yet read batch calls, so ``--record`` is
refused together with a batch size above one; the ledger records every batch
call and verdict.

    PYTHONPATH=src:tools python tools/review_catalogue_candidates.py \\
        --catalogue examples/29_intelligence_service/starter-catalogue \\
        --ledger RUN_FOLDER/ledger.jsonl --count 30 --seed SEED \\
        --call-ceiling 220 --token-ceiling 4000000 --calibrate \\
        --record examples/29_intelligence_service/starter-catalogue/reviews-panel-DATE.json \\
        --recorded-at DATE --authorize-model-calls
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from candidate_review import calibration as calibration_module  # noqa: E402
from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines, review_record  # noqa: E402
from candidate_review.catalogue import StarterCatalogue, select_population  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.panel import PanelRunRequest, ReviewPanel  # noqa: E402
from candidate_review.records import CandidateReviewError, refuse  # noqa: E402
from candidate_review.prompt import MAXIMUM_BATCH  # noqa: E402
from candidate_review.reviewers import ReviewerContext  # noqa: E402
from candidate_review.reviewers.gateway import listed_model_versions  # noqa: E402

RESOURCES = HERE / "candidate_review" / "resources"
SUMMARY_RECORD = "candidate_review_command_summary/v1"


def _json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        refuse("resource_unreadable", f"{Path(path).name} is not readable JSON")


def _programs(values) -> dict:
    programs = {}
    for value in values:
        engine_id, separator, path = value.partition("=")
        if not separator or engine_id not in engines.PRECHECK_ENGINE_FACTORIES or not path:
            refuse("invalid_program_option", "a program is written ENGINE_ID=PATH for a known pre-check engine")
        programs[engine_id] = path
    return programs


def _pairs(values, name: str, parse) -> dict:
    """``NAME=VALUE`` options into a mapping; a repeated name or an unreadable value is refused."""
    pairs = {}
    for value in values:
        key, separator, raw = value.partition("=")
        if not separator or not key or key in pairs:
            refuse("invalid_option", f"{name} is written NAME=VALUE, each name once")
        pairs[key] = parse(raw)
    return pairs


def _whole_number(low: int, high: int):
    def parse(raw: str) -> int:
        if not raw.isdigit() or not low <= int(raw) <= high:
            refuse("invalid_option", f"a value here is a whole number from {low} to {high}")
        return int(raw)
    return parse


def _reason(raw: str) -> str:
    if not raw.strip():
        refuse("invalid_option", "an exclusion carries a written reason")
    return raw.strip()


def _operator_resolver():
    """The operator credential resolver, imported only when model calls are authorized."""
    from tools import operator_credentials
    return operator_credentials.resolve


def _write_record(path: Path, value: dict, replace: bool) -> None:
    payload = review_record.serialized(value)
    if path.exists() and not replace:
        refuse("record_exists", f"{path.name} exists; pass --replace-record to write it again")
    temporary = path.with_name(path.name + ".writing")
    with temporary.open("xb") as stream:
        stream.write(payload)
    os.replace(temporary, path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalogue", type=Path, required=True, help="The candidate catalogue folder.")
    parser.add_argument("--content-profile", choices=("starter", "native-original"), default="starter",
                        help="The exact content and review criteria profile; native-original reads complete v3 packages.")
    parser.add_argument("--repository", type=Path, default=Path.cwd(), help="The repository root.")
    parser.add_argument("--panel", type=Path, default=RESOURCES / "panel.json")
    parser.add_argument("--criteria", type=Path, default=RESOURCES / "criteria.json")
    parser.add_argument("--producers", type=Path, default=RESOURCES / "producer-starter-catalogue.json")
    parser.add_argument("--instructions", type=Path, default=RESOURCES / "REVIEWER-INSTRUCTIONS.md")
    parser.add_argument("--calibration-set", type=Path, default=RESOURCES / "calibration-set.json")
    parser.add_argument("--calibrate", action="store_true",
                        help="Ask every eligible reviewer about the calibration set first and exclude any reviewer "
                             "that approves a known-wrong item.")
    parser.add_argument("--ledger", type=Path, required=True, help="The ledger file: the resumable cursor.")
    parser.add_argument("--identity", action="append", default=[],
                        help="Review this item. Repeat for more. Without it a seeded sample of unreviewed items.")
    parser.add_argument("--count", type=int, default=0, help="How many unreviewed items the seeded sample takes.")
    parser.add_argument("--seed", default="", help="The written seed of the sample.")
    parser.add_argument("--call-ceiling", type=int, required=True, help="Calls allowed in this command, in all.")
    parser.add_argument("--token-ceiling", type=int, required=True, help="Tokens allowed in this command, in all.")
    parser.add_argument("--item-concurrency", type=int, default=1, help="Items reviewed at the same time.")
    parser.add_argument("--program", action="append", default=[],
                        help="Where a pre-check engine's program is on this machine, as ENGINE_ID=PATH.")
    parser.add_argument("--run-id", default="",
                        help="The run identity, new for every command on one ledger; the ledger refuses an "
                             "identity it already holds. Defaults to the start time.")
    parser.add_argument("--record", type=Path, help="Write the dated review record here, inside the repository.")
    parser.add_argument("--recorded-at", default="", help="The date the record states, as YYYY-MM-DD.")
    parser.add_argument("--replace-record", action="store_true", help="Replace an existing record at --record.")
    parser.add_argument("--authorize-model-calls", action="store_true",
                        help="Allow calls to the declared reviewer models within the ceilings.")
    parser.add_argument("--batch-size", action="append", default=[],
                        help=f"Ask an installation about up to N items per call, as INSTALLATION=N (1 to "
                             f"{MAXIMUM_BATCH}).")
    parser.add_argument("--quota-group-ceiling", action="append", default=[],
                        help="The most calls one quota group may take in this command, as GROUP=N.")
    parser.add_argument("--stop-after-repeated-failures", type=int, default=0,
                        help="Stop asking an installation after this many identical failures in a row; 0 is off.")
    parser.add_argument("--exclude-installation", action="append", default=[],
                        help="Keep an installation out of this command, as INSTALLATION=REASON.")
    parser.add_argument("--collect-below-quorum", default="",
                        help="The written reason to ask each reachable family once although the reachable "
                             "families cannot reach the quorum.")
    parser.add_argument("--calibrate-only", action="store_true",
                        help="Run the calibration and no real candidate; needs --calibrate.")
    return parser


def run(options) -> dict:
    repository = options.repository.resolve()
    configuration = config.PanelConfiguration.from_dict(_json(options.panel))
    batch_sizes = _pairs(options.batch_size, "--batch-size", _whole_number(1, MAXIMUM_BATCH))
    group_ceilings = _pairs(options.quota_group_ceiling, "--quota-group-ceiling", _whole_number(0, 1_000_000))
    exclusions = _pairs(options.exclude_installation, "--exclude-installation", _reason)
    known = {item.installation_id for item in configuration.installations}
    if set(batch_sizes) - known or set(exclusions) - known:
        refuse("invalid_option", "a batch size or an exclusion names an installation the panel does not declare")
    if options.record and any(size > 1 for size in batch_sizes.values()):
        refuse("record_batch_calls_unsupported",
               "the dated review record does not yet read batch calls; the ledger records them")
    if options.calibrate_only and not options.calibrate:
        refuse("invalid_option", "--calibrate-only needs --calibrate")
    if options.stop_after_repeated_failures < 0:
        refuse("invalid_option", "--stop-after-repeated-failures is a whole number of zero or more")
    limits = {"batch_sizes": batch_sizes, "quota_group_call_ceilings": group_ceilings,
              "repeated_failure_limit": options.stop_after_repeated_failures}
    if options.content_profile == "native-original":
        from candidate_review import native, native_profile
        if (options.criteria != RESOURCES / "criteria.json" or options.producers != RESOURCES / "producer-starter-catalogue.json"
                or options.instructions != RESOURCES / "REVIEWER-INSTRUCTIONS.md"):
            refuse("native_review_profile_mismatch", "native-original selects its own criteria, instructions and per-item producers")
        criteria, instructions = native_profile.resources()
        catalogue = native.NativeCatalogue.load(options.catalogue, repository)
        configuration = native_profile.configuration(configuration, population_size=len(catalogue.identities()))
        producers = catalogue.producer_declaration(configuration.families)
    else:
        criteria_record = _json(options.criteria)
        criteria = config.compile_criteria(criteria_record, (repository / criteria_record["source_path"]).read_text(
            encoding="utf-8"))
        producer_record = _json(options.producers)
        producers = config.ProducerDeclaration.from_dict(
            producer_record, (repository / producer_record["evidence"]["path"]).read_text(encoding="utf-8"),
            configuration.families)
        instructions = config.load_instructions(options.instructions)
        catalogue = StarterCatalogue.load(options.catalogue, repository)
    if options.identity:
        selection = review_record.PopulationSelection(review_record.EXPLICIT_LIST, "", tuple(options.identity),
                                                      tuple(options.identity))
    elif options.calibrate_only:
        # A calibration-only command selects no real candidate.
        selection = review_record.PopulationSelection(review_record.EXPLICIT_LIST, "", (), ())
    else:
        eligible = catalogue.not_reviewed()
        selection = review_record.PopulationSelection(review_record.SEEDED_HASH_ORDER, options.seed, eligible,
                                                      select_population(eligible, count=options.count,
                                                                        seed=options.seed))
    requests = tuple(catalogue.request(identity, producers.producer_for(identity), criteria, instructions.sha256)
                     for identity in selection.selected)
    chosen, pairs = None, ()
    if options.calibrate:
        if options.content_profile == "native-original":
            from candidate_review.native_calibration import DEFAULT_SET, NativeCalibrationSet
            calibration_path = (DEFAULT_SET if options.calibration_set == RESOURCES / "calibration-set.json"
                                else options.calibration_set)
            chosen = NativeCalibrationSet.load(calibration_path, repository, criteria)
        else:
            chosen = calibration_module.CalibrationSet.from_dict(_json(options.calibration_set), criteria.ids)
        pairs = chosen.requests(catalogue, producers, criteria, instructions.sha256)
    listing = {"record_type": "ollama_model_versions/v1", "ok": False, "models": {},
               "error": "model calls were not authorized, so the provider listing was not read"}
    if options.authorize_model_calls:
        listing = listed_model_versions()
    context = ReviewerContext(model_listing=listing["models"] if listing["ok"] else None, repository=repository,
                              credential_resolver=_operator_resolver() if options.authorize_model_calls else None)
    reviewers = {item.installation_id: engines.build_reviewer(item, configuration.policy, context)
                 for item in configuration.installations}
    prechecks = engines.build_precheck_engines(configuration, programs=_programs(options.program))
    ledger = ReviewLedger(options.ledger)
    panel = ReviewPanel(configuration, criteria, instructions, reviewers, prechecks, ledger)
    run_id = options.run_id or "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    calls_left, tokens_left = options.call_ceiling, options.token_ceiling
    report, calibration_requests, excluded, calibration_result = None, (), dict(exclusions), None
    if options.calibrate:
        calibration_requests = tuple(request.request_sha256 for _item, request in pairs)
        calibration_result = panel.run(PanelRunRequest(
            run_id=run_id + "-calibration", requests=tuple(request for _item, request in pairs),
            population=chosen.population(catalogue.population_bodies()), call_ceiling=calls_left,
            token_ceiling=tokens_left, model_calls_authorized=options.authorize_model_calls,
            item_concurrency=options.item_concurrency, ask_every_eligible_reviewer=True,
            excluded_installations=dict(exclusions), **limits))
        report = calibration_module.evaluate(chosen, calibration_result)
        excluded.update({key: value for key, value in report["excluded"].items() if key not in excluded})
        calls_left -= calibration_result.budget["calls_reserved"]
        tokens_left = max(0, tokens_left - calibration_result.budget["tokens_charged"])
        group_used = {}
        for call in calibration_result.calls:
            group = configuration.installation(call["installation_id"]).quota_group
            group_used[group] = group_used.get(group, 0) + 1
        limits["quota_group_call_ceilings"] = {group: max(0, ceiling - group_used.get(group, 0))
                                               for group, ceiling in group_ceilings.items()}
    result = None
    if not options.calibrate_only:
        result = panel.run(PanelRunRequest(
            run_id=run_id, requests=requests, population=catalogue.population_bodies(),
            call_ceiling=max(0, calls_left), token_ceiling=tokens_left,
            model_calls_authorized=options.authorize_model_calls, item_concurrency=options.item_concurrency,
            excluded_installations=excluded, collect_below_quorum_reason=options.collect_below_quorum, **limits))
    summary = {"record_type": SUMMARY_RECORD, "run_id": run_id, "listing": {key: listing.get(key) for key in (
        "ok", "error", "withheld")}, "stop_reason": result.stop_reason if result else "calibration_only",
        "totals": result.totals() if result else None, "ineligible": result.ineligible if result else None,
        "capped_quota_groups": sorted(result.capped_quota_groups) if result else [],
        "run_limits": {"batch_sizes": batch_sizes, "quota_group_call_ceilings": group_ceilings,
                       "repeated_failure_limit": options.stop_after_repeated_failures,
                       "excluded_installations": exclusions, "collect_below_quorum": options.collect_below_quorum},
        "calibration": None if report is None else {
            "stop_reason": calibration_result.stop_reason, "totals": calibration_result.totals(),
            "ineligible": calibration_result.ineligible,
            "installations": {key: value["status"] for key, value in report["installations"].items()},
            "report": report},
        "record": None}
    if options.record and result is not None:
        if not options.recorded_at:
            refuse("record_date_missing", "a record states the date it was written: pass --recorded-at")
        path = options.record.resolve()
        try:
            relative = path.relative_to(repository).as_posix()
        except ValueError:
            refuse("record_outside_repository", "the record is written inside the repository")
        record = review_record.build_panel_review_record(
            result, ledger, catalogue=catalogue, configuration=configuration, criteria=criteria,
            instructions=instructions, producers=producers, population=selection, recorded_at=options.recorded_at,
            record_path=relative, calibration_report=report, calibration_requests=calibration_requests)
        review_record.read_panel_review_record(record, calibration_inputs=(
            calibration_module.CalibrationInputs(chosen, tuple(request for _item, request in pairs), instructions)
            if chosen is not None else None))
        _write_record(path, record, options.replace_record)
        summary["record"] = relative
    return summary


def main(argv=None) -> int:
    options = _parser().parse_args(argv)
    started = time.monotonic()
    try:
        summary = run(options)
    except CandidateReviewError as error:
        print(json.dumps({"record_type": SUMMARY_RECORD, "refused": True, "code": error.code,
                          "message": str(error)}, ensure_ascii=False))
        return 2
    summary["command_seconds"] = round(time.monotonic() - started, 3)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
