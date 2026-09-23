"""Reconstruct persisted calibration eligibility from trusted controls and bound verdicts."""
from __future__ import annotations

import json
from pathlib import Path

from .calibration import (
    CALIBRATION_INCOMPLETE,
    CALIBRATION_RESULT_RECORD,
    FAILED_CALIBRATION,
    LIMITS,
    CalibrationInputs,
    CalibrationSet,
    installation_result,
)
from .configuration import FIXTURE_ENGINE_KIND
from .ledger import read_row
from .prompt import build_prompt
from .records import (
    CALL_RECORD,
    DISPATCH_RECORD,
    SHA256,
    VERDICT_RECORD,
    digest,
    read_part,
    read_record,
    refuse,
)
from .reviewers import ANSWERED, ATTEMPT_OUTCOMES, Usage
from .verdicts import DECISIONS, parse_verdict

FIELDS = ("set_sha256", "purpose", "items", "run_id", "installations", "excluded", "limits", "calls",
          "verdicts", "interrupted_dispatches")
INELIGIBLE_FIELDS = ("installation_id", "reason", "family", "model", "disabled_reason")
EXCLUSIONS = (FAILED_CALIBRATION, CALIBRATION_INCOMPLETE)
OUTCOMES = (set(ATTEMPT_OUTCOMES) - {ANSWERED}) | {"verdict", "invalid_response"}


def default_inputs(set_digest: str) -> CalibrationInputs:
    """Select only deployment-owned resource bytes, never labels from an export."""
    from . import configuration, native_calibration, native_profile
    from .catalogue import StarterCatalogue

    resources = Path(__file__).resolve().parent / "resources"
    repository = resources.parents[2]
    native_record = json.loads(native_calibration.DEFAULT_SET.read_text())
    if set_digest == digest(native_record):
        criteria, instructions = native_profile.resources()
        chosen = native_calibration.NativeCalibrationSet.load(native_calibration.DEFAULT_SET, repository, criteria)
        pairs = chosen.requests(None, None, criteria, instructions.sha256)
        return CalibrationInputs(chosen, tuple(request for _item, request in pairs), instructions)
    value = json.loads((resources / "calibration-set.json").read_text())
    if set_digest != digest(value):
        refuse("calibration_set_untrusted", "the set digest names no deployment-owned control set")
    criteria_record = json.loads((resources / "criteria.json").read_text())
    criteria = configuration.compile_criteria(criteria_record, (repository / criteria_record["source_path"]).read_text())
    chosen = CalibrationSet.from_dict(value, criteria.ids)
    declaration = json.loads((resources / "producer-starter-catalogue.json").read_text())
    panel = configuration.PanelConfiguration.from_dict(json.loads((resources / "panel.json").read_text()))
    producers = configuration.ProducerDeclaration.from_dict(declaration,
        (repository / declaration["evidence"]["path"]).read_text(), panel.families)
    catalogue = StarterCatalogue.load(repository / declaration["catalogue_folder"], repository)
    instructions = configuration.load_instructions(resources / "REVIEWER-INSTRUCTIONS.md")
    return CalibrationInputs(chosen, tuple(request for _item, request in chosen.requests(
        catalogue, producers, criteria, instructions.sha256)), instructions)


def _sha(value) -> bool:
    return type(value) is str and SHA256.fullmatch(value) is not None


def _identity(row) -> tuple:
    return tuple(row[key] for key in ("installation_sha256", "engine_kind", "family", "model"))


def _binding(row, requests, installations):
    if type(row["identity"]) is not str or type(row["installation_id"]) is not str:
        refuse("calibration_call_invalid", "control and installation identities must be strings")
    request = requests.get(row["identity"])
    if (request is None or row["body_sha256"] != request.body_sha256
            or row["request_sha256"] != request.request_sha256
            or row["request_record_type"] != request.to_record()["record_type"]):
        refuse("calibration_call_mismatch", "a control call must bind its exact trusted package, criteria and instructions")
    if installations is not None and row["installation_id"] not in installations:
        refuse("calibration_installation_unknown", "a control call names an undeclared installation")
    if (type(row["run_id"]) is not str or not row["run_id"] or type(row["sequence"]) is not int
            or row["sequence"] < 1 or not _sha(row["review_key"])):
        refuse("calibration_call_invalid", "a control call needs a valid run, sequence and review identity")
    return request


def read_calibration(value, ineligible, *, configuration=None, reviewers=None,
                     calibration_inputs=None, criteria=None, instructions=None,
                     allow_fixture=True) -> dict:
    """Unknown controls, incomplete reviews and edited summary lists cannot qualify a reviewer."""
    saved = read_record(value, CALIBRATION_RESULT_RECORD, FIELDS)
    inputs = calibration_inputs or default_inputs(saved["set_sha256"])
    if not isinstance(inputs, CalibrationInputs):
        refuse("calibration_inputs_invalid", "trusted calibration inputs are host-supplied typed values")
    chosen = inputs.control_set
    requests = {request.identity: request for request in inputs.requests}
    expected = {item.identity: item.expected_decision for item in chosen.items}
    if (len(requests) != len(inputs.requests) or set(requests) != set(expected)
            or len(expected) != len(chosen.items) or not expected):
        refuse("calibration_inputs_invalid", "trusted requests exactly cover the distinct controls")
    if (saved["set_sha256"] != chosen.sha256 or saved["items"] != [item.to_dict() for item in chosen.items]
            or saved["purpose"] != chosen.purpose or saved["limits"] != LIMITS):
        refuse("calibration_controls_changed", "exported labels and control metadata differ from the trusted set")
    for item in chosen.items:
        request = requests[item.identity]
        if request.instructions_sha256 != inputs.instructions.sha256:
            refuse("calibration_inputs_invalid", "trusted instructions differ from the control request")
        if item.criterion_id not in request.applicable_criteria_ids:
            refuse("calibration_criterion_invalid", "a control's known criterion does not apply to its exact request")
        if criteria is not None and (request.criteria.sha256 != criteria["criteria_sha256"]
                or request.instructions_sha256 != instructions["sha256"]):
            refuse("calibration_profile_mismatch", "controls and candidates must use identical review criteria and instructions")
    if any(type(saved[name]) is not list for name in ("calls", "verdicts", "interrupted_dispatches")):
        refuse("calibration_records_invalid", "calibration evidence uses explicit record lists")
    if type(saved["installations"]) is not dict or type(saved["excluded"]) is not dict or type(ineligible) is not list:
        refuse("calibration_records_invalid", "calibration summaries and exclusions have closed container shapes")
    installations = ({item.installation_id: item for item in configuration.installations}
                     if configuration is not None else None)
    ineligible_by_id = {}
    for raw in ineligible:
        row = read_part(raw, "ineligible reviewer", INELIGIBLE_FIELDS)
        identity = row["installation_id"]
        if type(identity) is not str or identity in ineligible_by_id or any(type(v) is not str for v in row.values()):
            refuse("calibration_ineligible_invalid", "ineligible reviewers are distinct named records")
        if installations is not None:
            installation = installations.get(identity)
            if installation is None or (row["family"], row["model"]) != (installation.family, installation.model):
                refuse("calibration_installation_unknown", "an excluded installation differs from the panel configuration")
        ineligible_by_id[identity] = row
    calls, versions, bindings = {}, {}, {}
    for raw in saved["calls"]:
        call = read_row(raw)
        if call["record_type"] != CALL_RECORD:
            refuse("record_call_unsupported", "calibration calls contain only call records")
        request = _binding(call, requests, installations)
        if call["family"] == request.producer.family:
            refuse("calibration_producer_family", "a control's producer family cannot review that control")
        key = (call["run_id"], call["sequence"])
        if key in calls:
            refuse("calibration_call_repeated", "a calibration call is represented exactly once")
        if (type(call["outcome"]) is not str or call["outcome"] not in OUTCOMES
                or (call["outcome"] == "verdict") != (call["decision"] in DECISIONS)):
            refuse("calibration_call_invalid", "only a valid verdict call may carry a decision")
        if call["outcome"] != "verdict" and call["decision"] != "":
            refuse("calibration_call_invalid", "invalid or unavailable answers cannot carry decisions")
        if call["outcome"] == "verdict" and (call["error_code"] or call["invalid_answer_excerpt"] or not call["reported_model"]):
            refuse("calibration_call_invalid", "a valid verdict has an exact answering identity and no parse failure")
        if not _sha(call["installation_sha256"]) or not _sha(call["prompt_sha256"]):
            refuse("calibration_call_invalid", "control calls bind exact installation and prompt digests")
        review_key = digest({"installation_sha256": call["installation_sha256"],
            "request_sha256": call["request_sha256"], "prompt_sha256": call["prompt_sha256"],
            "record_type": VERDICT_RECORD, "request_record_type": call["request_record_type"]})
        if call["review_key"] != review_key:
            refuse("calibration_call_invalid", "the calibration review key does not bind the recorded request")
        try:
            Usage(**call["usage"])
        except (TypeError, ValueError):
            refuse("calibration_usage_invalid", "reported and unknown usage must retain their typed representation")
        identity = call["installation_id"]
        if call["engine_kind"] == FIXTURE_ENGINE_KIND and not allow_fixture:
            refuse("fixture_reviewer_in_record", "a fixture calibration cannot qualify a live reviewer")
        version = (call["model_version"], call["engine_version"])
        if identity in bindings and (bindings[identity] != _identity(call) or versions[identity] != version):
            refuse("calibration_installation_changed", "one installation cannot change identity or version during calibration")
        if installations is not None:
            installation = installations[identity]
            if not installation.enabled:
                refuse("calibration_installation_disabled", "a disabled installation cannot provide control evidence")
            if _identity(call) != (installation.sha256, installation.engine_kind, installation.family, installation.model):
                refuse("calibration_installation_changed", "a calibration call differs from its configured installation")
            prompt = build_prompt(request, installation, inputs.instructions)
            if call["prompt_sha256"] != prompt.sha256:
                refuse("calibration_prompt_mismatch", "the exact control prompt differs from the trusted request, installation or instructions")
        bindings[identity], versions[identity] = _identity(call), version
        calls[key] = call
    interrupted = set()
    observed = {row["installation_id"] for row in calls.values()}
    for raw in saved["interrupted_dispatches"]:
        row = read_row(raw)
        if row["record_type"] != DISPATCH_RECORD:
            refuse("record_dispatch_unsupported", "an interrupted calibration holds dispatch records")
        _binding(row, requests, installations)
        key = (row["run_id"], row["sequence"])
        if key in calls or key in interrupted:
            refuse("calibration_dispatch_inconsistent", "a dispatch is neither duplicated nor completed and interrupted")
        interrupted.add(key)
        observed.add(row["installation_id"])
    answers, covered = {}, set()
    for raw in saved["verdicts"]:
        verdict = read_row(raw)
        if verdict["record_type"] != VERDICT_RECORD:
            refuse("calibration_verdict_invalid", "calibration verdicts use the existing typed verdict record")
        _binding(verdict, requests, installations)
        key = (verdict["run_id"], verdict["sequence"])
        call = calls.get(key)
        if key in covered or call is None or call["outcome"] != "verdict":
            refuse("calibration_verdict_invalid", "a verdict needs one distinct completed verdict call")
        fields = ("review_key", "installation_id", "family", "identity", "body_sha256", "request_sha256", "decision",
                  "reported_model", "request_record_type")
        if any(verdict[name] != call[name] for name in fields):
            refuse("calibration_verdict_invalid", "a verdict differs from the call and subject that produced it")
        request = requests[verdict["identity"]]
        content, error = parse_verdict(json.dumps({name: verdict[name] for name in
            ("body_sha256", "decision", "findings", "reasons")}), body_sha256=request.body_sha256,
            criteria_ids=request.applicable_criteria_ids)
        if error or content is None:
            refuse("calibration_verdict_invalid", "the bound verdict fails the exact control's review criteria")
        selected = answers.setdefault(verdict["installation_id"], {})
        if verdict["identity"] in selected:
            refuse("calibration_verdict_repeated", "an installation decides each frozen control once")
        selected[verdict["identity"]] = content.decision
        covered.add(key)
    if covered != {key for key, call in calls.items() if call["outcome"] == "verdict"}:
        refuse("calibration_verdict_missing", "every claimed verdict call needs its complete typed verdict evidence")
    observed.update(identity for identity, row in ineligible_by_id.items() if row["reason"] in EXCLUSIONS)
    expected_installations = set(installations) if installations is not None else observed
    recomputed = {identity: installation_result(expected, answers.get(identity, {}))
                  for identity in sorted(expected_installations)}
    if digest(saved["installations"]) != digest(recomputed):
        refuse("calibration_summary_inconsistent", "installation results must be recomputed from complete bound control verdicts")
    excluded = {identity: row["status"] for identity, row in recomputed.items() if row["status"] != "qualified"}
    if saved["excluded"] != excluded or {identity: row["reason"] for identity, row in ineligible_by_id.items()
                                        if row["reason"] in EXCLUSIONS} != excluded:
        refuse("calibration_inconsistent", "both exclusion projections must match the independently recomputed eligibility")
    for identity, reviewer in (reviewers or {}).items():
        if identity not in recomputed or recomputed[identity]["status"] != "qualified":
            refuse("excluded_calibration_reviewer_decided", "a candidate reviewer lacks complete qualified calibration")
        if (bindings.get(identity) != _identity(reviewer)
                or versions.get(identity) != (reviewer["model_version"], reviewer["engine_version"])):
            refuse("calibration_installation_changed", "candidate and control calls must use the same exact installation version")
    return recomputed
