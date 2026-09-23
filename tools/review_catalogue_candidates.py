"""Put catalogue candidates to the independent review panel and write a dated review record.

The command reads the panel's declared resources, selects a population of
candidates by a declared rule, runs the deterministic pre-checks, optionally
calibrates every eligible reviewer on known-wrong and known-good items, asks
the reviewers within one declared ceiling of calls and tokens for the whole
command, and writes a dated review record beside the catalogue's ``reviews.json``.
It never edits ``reviews.json``, the item file, the bodies or a host manifest.

No model is called without ``--authorize-model-calls``. Without it the command
runs the pre-checks and reports what it would have asked. A stopped command can
be run again with the same ledger: it reuses every verdict already given and
never repeats a call that was dispatched and not completed.

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
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from candidate_review import calibration as calibration_module  # noqa: E402
from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines, review_record  # noqa: E402
from candidate_review.catalogue import StarterCatalogue, select_population  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.panel import PanelRunRequest, ReviewPanel  # noqa: E402
from candidate_review.records import CandidateReviewError, refuse  # noqa: E402
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
    parser.add_argument("--run-id", default="", help="The run identity. Defaults to the start time.")
    parser.add_argument("--record", type=Path, help="Write the dated review record here, inside the repository.")
    parser.add_argument("--recorded-at", default="", help="The date the record states, as YYYY-MM-DD.")
    parser.add_argument("--replace-record", action="store_true", help="Replace an existing record at --record.")
    parser.add_argument("--authorize-model-calls", action="store_true",
                        help="Allow calls to the declared reviewer models within the ceilings.")
    return parser


def run(options) -> dict:
    repository = options.repository.resolve()
    configuration = config.PanelConfiguration.from_dict(_json(options.panel))
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
    else:
        eligible = catalogue.not_reviewed()
        selection = review_record.PopulationSelection(review_record.SEEDED_HASH_ORDER, options.seed, eligible,
                                                      select_population(eligible, count=options.count,
                                                                        seed=options.seed))
    requests = tuple(catalogue.request(identity, producers.producer_for(identity), criteria, instructions.sha256)
                     for identity in selection.selected)
    listing = {"record_type": "ollama_model_versions/v1", "ok": False, "models": {},
               "error": "model calls were not authorized, so the provider listing was not read"}
    if options.authorize_model_calls:
        listing = listed_model_versions()
    context = ReviewerContext(model_listing=listing["models"] if listing["ok"] else None)
    reviewers = {item.installation_id: engines.build_reviewer(item, configuration.policy, context)
                 for item in configuration.installations}
    prechecks = engines.build_precheck_engines(configuration, programs=_programs(options.program))
    ledger = ReviewLedger(options.ledger)
    panel = ReviewPanel(configuration, criteria, instructions, reviewers, prechecks, ledger)
    run_id = options.run_id or "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    calls_left, tokens_left = options.call_ceiling, options.token_ceiling
    report, calibration_requests, excluded, calibration_result = None, (), {}, None
    if options.calibrate:
        chosen = calibration_module.CalibrationSet.from_dict(_json(options.calibration_set), criteria.ids)
        pairs = chosen.requests(catalogue, producers, criteria, instructions.sha256)
        calibration_requests = tuple(request.request_sha256 for _item, request in pairs)
        calibration_result = panel.run(PanelRunRequest(
            run_id=run_id + "-calibration", requests=tuple(request for _item, request in pairs),
            population=chosen.population(catalogue.population_bodies()), call_ceiling=calls_left,
            token_ceiling=tokens_left, model_calls_authorized=options.authorize_model_calls,
            item_concurrency=options.item_concurrency, ask_every_eligible_reviewer=True))
        report = calibration_module.evaluate(chosen, calibration_result)
        excluded = dict(report["excluded"])
        calls_left -= calibration_result.budget["calls_reserved"]
        tokens_left = max(0, tokens_left - calibration_result.budget["tokens_charged"])
    result = panel.run(PanelRunRequest(
        run_id=run_id, requests=requests, population=catalogue.population_bodies(),
        call_ceiling=max(0, calls_left), token_ceiling=tokens_left,
        model_calls_authorized=options.authorize_model_calls, item_concurrency=options.item_concurrency,
        excluded_installations=excluded))
    summary = {"record_type": SUMMARY_RECORD, "run_id": run_id, "listing": {key: listing.get(key) for key in (
        "ok", "error", "withheld")}, "stop_reason": result.stop_reason, "totals": result.totals(),
        "ineligible": result.ineligible, "calibration": None if report is None else {
            "stop_reason": calibration_result.stop_reason, "totals": calibration_result.totals(),
            "installations": {key: value["status"] for key, value in report["installations"].items()}},
        "record": None}
    if options.record:
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
        review_record.read_panel_review_record(record)
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
