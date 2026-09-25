"""The Community review campaign of September 24, 2026: prechecks, calibration and batched review.

One reviewing family can be reached (anthropic, Claude on the owner's
subscription), so an approval here is a Community approval under the "Library
tiers" row of the AGENTS.md decision table: every automated check passes and
one independent family that did not produce the item approves it against the
written native criteria. Verified approval still needs two families; the
verdicts stay in the ledger, so a second family later asks only for itself.

Every call goes through the review panel with the declared run limits and is
written to the campaign ledger with its model, usage and outcome. Library
bodies stay outside the public repository.

    PYTHONPATH=src:tools python artifacts/review-throughput-2026-09-24/community_campaign.py prechecks ...
    PYTHONPATH=src:tools python artifacts/review-throughput-2026-09-24/community_campaign.py calibrate ...
    PYTHONPATH=src:tools python artifacts/review-throughput-2026-09-24/community_campaign.py review ...
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src"), str(ROOT)]

from candidate_review import calibration as calibration_module  # noqa: E402
from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines, imported, imported_profile, native, native_profile, screen_profile  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.imported_calibration import IMPORTED_DEFAULT_SET, ImportedCalibrationSet  # noqa: E402
from candidate_review.native_calibration import DEFAULT_SET, NativeCalibrationSet  # noqa: E402
from candidate_review.panel import PanelRunRequest, ReviewPanel  # noqa: E402
from candidate_review.prechecks import PrecheckContext, run_prechecks  # noqa: E402
from candidate_review.reviewers import ReviewerContext  # noqa: E402

REVIEWER = "claude_code.subscription"
BATCH = 12


CONTENT_PROFILES = ("full", "screen")


def _profile(catalogue_folder: Path, content_profile: str = "full"):
    """The imported reader and profile for a licensed import review export, the original ones otherwise.

    ``screen`` selects the four-question Community screen (roadmap S-6.199) for an imported catalogue;
    it is refused for an original catalogue, whose screen is not written yet."""
    if content_profile not in CONTENT_PROFILES:
        raise SystemExit(f"content profile is one of {CONTENT_PROFILES}")
    if imported.is_imported_catalogue(catalogue_folder):
        return imported.ImportedCatalogue, (screen_profile if content_profile == "screen" else imported_profile)
    if content_profile == "screen":
        raise SystemExit("the Community screen is written for imported catalogues only")
    return native.NativeCatalogue, native_profile


def _build(catalogue_folder: Path, ledger: Path, authorized: bool, population_size: int, content_profile: str = "full"):
    base = config.PanelConfiguration.from_dict(json.loads(
        (ROOT / "tools/candidate_review/resources/panel.json").read_text(encoding="utf-8")))
    profile = _profile(catalogue_folder, content_profile)[1]
    configuration = profile.configuration(base, population_size=population_size)
    criteria, instructions = profile.resources()
    resolver = None
    if authorized:
        from tools import operator_credentials
        resolver = operator_credentials.resolve
    context = ReviewerContext(repository=ROOT, credential_resolver=resolver)
    reviewers = {item.installation_id: engines.build_reviewer(item, configuration.policy, context)
                 for item in configuration.installations}
    panel = ReviewPanel(configuration, criteria, instructions, reviewers,
                        engines.build_precheck_engines(configuration), ReviewLedger(ledger))
    return configuration, criteria, instructions, panel


def _exclusions(values) -> dict:
    return dict(value.split("=", 1) for value in values)


def _quota_group(configuration, reviewer: str) -> str:
    return configuration.installation(reviewer).quota_group


def _identities(options, catalogue) -> list:
    """The identities to review: named ones, or the ones listed in a file, or every identity."""
    names = list(options.identity)
    if options.identities_file:
        names += [line.strip() for line in options.identities_file.read_text().splitlines() if line.strip()]
    return names or list(catalogue.identities())


def prechecks(options) -> dict:
    catalogue = _profile(options.catalogue)[0].load(options.catalogue, ROOT)
    configuration, criteria, instructions, _panel_unused = _build(options.catalogue, options.scratch_ledger, False,
                                                                  len(catalogue.identities()))
    engine_map = engines.build_precheck_engines(configuration)
    context = PrecheckContext(configuration.policy, catalogue.population_bodies())
    rows = []
    for identity in catalogue.identities():
        request = catalogue.request(identity, catalogue.producer_for(identity), criteria, instructions.sha256)
        outcome = run_prechecks(request, engine_map, context)
        rows.append({"identity": identity, "producer_family": request.producer.family,
                     "package_digest": request.body_sha256, "refused": outcome.refused,
                     "reasons": list(outcome.reasons),
                     "findings": [{"kind": result.kind, "engine": result.engine_id, "status": result.status,
                                   "codes": sorted({finding.code for finding in result.findings})}
                                  for result in outcome.results if result.findings or result.status != "passed"]})
    record = {"record_type": "community_campaign_prechecks/v1", "catalogue": str(options.catalogue),
              "items": len(rows), "refused": sum(1 for row in rows if row["refused"]), "rows": rows}
    options.output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    return {key: record[key] for key in ("items", "refused")}


def calibrate(options) -> dict:
    """Controls asked one at a time, then in one batch of 12 with seven real candidates between them.

    An imported catalogue is calibrated on the imported controls, under the imported criteria; an original one on
    the original controls. The rule is the same: a reviewer that approves a known-wrong control is excluded."""
    reader, _content_profile = _profile(options.catalogue)
    catalogue = reader.load(options.catalogue, ROOT)
    configuration, criteria, instructions, panel = _build(options.catalogue, options.ledger,
                                                          options.authorize_model_calls, len(catalogue.identities()))
    if imported.is_imported_catalogue(options.catalogue):
        controls = ImportedCalibrationSet.load(IMPORTED_DEFAULT_SET, ROOT, criteria)
    else:
        controls = NativeCalibrationSet.load(DEFAULT_SET, ROOT, criteria)
    pairs = controls.requests(catalogue, None, criteria, instructions.sha256)
    control_requests = [request for _item, request in pairs]
    real = [catalogue.request(identity, catalogue.producer_for(identity), criteria, instructions.sha256)
            for identity in options.real]
    if options.batch_size > 1 and len(real) != BATCH - len(control_requests):
        raise SystemExit(f"a mixed calibration batch holds {BATCH - len(control_requests)} real candidates")
    population = controls.population(catalogue.population_bodies())
    quota_group = _quota_group(configuration, options.reviewer)
    limits = {"excluded_installations": _exclusions(options.exclude_installation),
              "quota_group_call_ceilings": {quota_group: options.calls_left}, "repeated_failure_limit": 2}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    single = panel.run(PanelRunRequest(
        run_id=f"calibration-single-{stamp}", requests=tuple(control_requests), population=population,
        call_ceiling=len(control_requests), token_ceiling=2_000_000,
        model_calls_authorized=options.authorize_model_calls, ask_every_eligible_reviewer=True, **limits))
    used = sum(1 for call in single.calls if call["installation_id"] == options.reviewer)
    limits["quota_group_call_ceilings"] = {quota_group: max(0, options.calls_left - used)}
    reports = {"single": calibration_module.evaluate(controls, single)}
    record = {"record_type": "community_campaign_calibration/v1", "reviewer": options.reviewer,
              "controls": [item.to_dict() for item in controls.items], "reports": reports,
              "single_calls": single.calls}
    if options.batch_size == 1:
        options.output.write_text(json.dumps(record, indent=1, sort_keys=True, default=str) + "\n")
        return {mode: {installation: {"status": row["status"], "false_approvals": row["false_approvals"],
                                      "label_refusals": row["false_refusals"], "decisions": row["decisions"]}
                       for installation, row in report["installations"].items() if installation == options.reviewer}
                for mode, report in reports.items()}
    # Controls spread evenly through the batch, the first and the last slot among them (for five controls:
    # positions 1, 4, 7, 9 and 12), real candidates in the slots between.
    slots = [round(index * (BATCH - 1) / (len(control_requests) - 1)) for index in range(len(control_requests))]
    controls_left, reals_left = iter(control_requests), iter(real)
    order = [next(controls_left) if position in slots else next(reals_left) for position in range(BATCH)]
    mixed = panel.run(PanelRunRequest(
        run_id=f"calibration-mixed-{stamp}", requests=tuple(order), population=population, call_ceiling=1,
        token_ceiling=2_000_000, model_calls_authorized=options.authorize_model_calls,
        ask_every_eligible_reviewer=True, batch_sizes={options.reviewer: BATCH}, **limits))
    mixed_controls = [item for item in mixed.items if item.identity in {request.identity for request in control_requests}]
    mixed_view = type(mixed)(**{**mixed.__dict__, "items": mixed_controls})
    reports["mixed_batch_of_12"] = calibration_module.evaluate(controls, mixed_view)
    record.update({"real_in_mixed_batch": options.real, "mixed_calls": mixed.calls,
                   "real_verdicts": [{"identity": item.identity, "verdicts": item.verdicts} for item in mixed.items
                                     if item.identity in set(options.real)]})
    options.output.write_text(json.dumps(record, indent=1, sort_keys=True, default=str) + "\n")
    return {mode: {installation: {"status": row["status"], "false_approvals": row["false_approvals"],
                                  "label_refusals": row["false_refusals"], "decisions": row["decisions"]}
                   for installation, row in report["installations"].items() if installation == options.reviewer}
            for mode, report in reports.items()}


def review(options) -> dict:
    """Every eligible candidate that passed the prechecks, asked of the reachable family in batches of 12."""
    catalogue = _profile(options.catalogue, options.content_profile)[0].load(options.catalogue, ROOT)
    configuration, criteria, instructions, panel = _build(options.catalogue, options.ledger,
                                                          options.authorize_model_calls, len(catalogue.identities()),
                                                          options.content_profile)
    identities = _identities(options, catalogue)
    requests = tuple(catalogue.request(identity, catalogue.producer_for(identity), criteria, instructions.sha256)
                     for identity in identities)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = panel.run(PanelRunRequest(
        run_id=f"community-review-{stamp}", requests=requests, population=catalogue.population_bodies(),
        call_ceiling=options.call_ceiling, token_ceiling=options.token_ceiling,
        model_calls_authorized=options.authorize_model_calls,
        batch_sizes={options.reviewer: options.batch_size} if options.batch_size > 1 else {},
        excluded_installations=_exclusions(options.exclude_installation),
        quota_group_call_ceilings={_quota_group(configuration, options.reviewer): options.calls_left},
        repeated_failure_limit=3,
        collect_below_quorum_reason="Community tier (AGENTS.md decision table, Library tiers): one independent "
                                    "family is reachable; its verdicts are stored for a later second family."))
    summary = {"run_id": result.run_id, "stop_reason": result.stop_reason, "totals": result.totals(),
               "ineligible": result.ineligible, "capped_quota_groups": sorted(result.capped_quota_groups),
               "spent_quota_groups": sorted(result.spent_quota_groups)}
    options.output.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    return {key: summary[key] for key in ("stop_reason", "capped_quota_groups")} | {
        "items": summary["totals"]["items"], "calls": summary["totals"]["calls"],
        "rejected": summary["totals"]["rejected"], "refused_before_review": summary["totals"]["refused_before_review"],
        "panel_incomplete": summary["totals"]["panel_incomplete"], "not_started": summary["totals"]["not_started"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prechecks", "calibrate", "review"):
        command = commands.add_parser(name)
        command.add_argument("--catalogue", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--exclude-installation", action="append", default=[])
        if name == "prechecks":
            command.add_argument("--scratch-ledger", type=Path, required=True)
        else:
            command.add_argument("--ledger", type=Path, required=True)
            command.add_argument("--reviewer", default=REVIEWER, help="The one installation asked in this run.")
            command.add_argument("--calls-left", type=int, required=True,
                                 help="What remains of the reviewer's quota group ceiling.")
            command.add_argument("--batch-size", type=int, default=BATCH,
                                 help="Items per call; 1 asks one item at a time.")
            command.add_argument("--authorize-model-calls", action="store_true")
        if name == "calibrate":
            command.add_argument("--real", action="append", default=[])
        if name == "review":
            command.add_argument("--identity", action="append", default=[])
            command.add_argument("--identities-file", type=Path)
            command.add_argument("--call-ceiling", type=int, required=True)
            command.add_argument("--token-ceiling", type=int, default=20_000_000)
            command.add_argument("--content-profile", choices=CONTENT_PROFILES, default="full",
                                 help="full asks the written imported criteria; screen asks the four Community screen questions.")
    options = parser.parse_args(argv)
    print(json.dumps({"prechecks": prechecks, "calibrate": calibrate, "review": review}[options.command](options),
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
