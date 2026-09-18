"""Review a failed independent check before the producer repairs its work.

An executable check can be wrong as well as the work it checks: it can expect
a value the task never states, or misread a correct deliverable in a format the
task does not require. A retained check is reused on every later attempt, so a
wrong check makes correct work fail again and again. When an independent report
fails, this module asks, in isolated verifier calls, whether the work or the
check is wrong, and acts on the answer without taking one model's word for it:

1. Classify. One call classifies the failure from the task, the registered
   criteria, the failed cases, the probe source, and bounded excerpts of the
   subject's authored and produced text files. Supplied inputs are never sent.
   Each finding must quote its evidence, and a quote counts only when it
   appears in that material.
2. Confirm. A classification that blames the check needs a second isolated
   call that confirms it with its own quoted evidence.
3. Discriminate. A revised check, designed with the disputed check and both
   reviews as untrusted feedback and approved by the normal oracle review,
   must fail on a known-wrong subject: the same subject with its authored and
   produced files emptied. Otherwise the revision is refused and the original
   failure stands.
4. Act. An admitted revision runs on the real subject as a new check version.
   The disputed check, the failed report, and both reviews stay recorded. A
   correct failure names the part of the work to repair.

The contract is hybrid: grounding, discrimination, and revision validation are
deterministic, and classification and confirmation are model-reasoned. Every
call spends the shared model authority. A review changes no permission, secret,
network, spending, sandbox, or external effect contract.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import LoopConfig, StepOutcome
from ..strings.verification_prompts import (
    INDEPENDENT_FAILURE_CONFIRMATION_PROMPT, INDEPENDENT_FAILURE_REVIEW_PROMPT)
from . import independent_verification as verification
from .context_artifacts import ContextArtifactRef
from .generated_project import (
    GeneratedProjectAuthority, GeneratedProjectExecutionContext,
    GeneratedProjectExecutionRequest, GeneratedProjectInputArtifact, _relative_path)
from .independent_judgment import JUDGMENT_COMPARISON, MINIMUM_QUOTE_CHARACTERS, grounded_quotes

FAILURE_CLASSES = ("correct_failure", "wrong_expectation", "check_stricter_than_task",
                   "environment_defect", "ambiguous_requirement", "unknown")
#: The classes that blame the check rather than the work.
CHECK_DEFECT_CLASSES = ("wrong_expectation", "check_stricter_than_task")
REPAIR_TARGETS = ("implementation", "interface", "inputs", "output_format",
                  "dependencies", "configuration", "plan", "none")
REVIEW_RECORD_TYPE = "independent_failure_review/v1"
REVISION_RECORD_TYPE = "independent_check_revision/v1"
KNOWN_WRONG_SUBJECT = "authored_and_produced_files_emptied"
#: Bounds on subject and probe text sent to one review call.
EXCERPT_CHARACTERS = 12000
EXCERPT_BUDGET = 48000
_EVIDENCE_CONTRACT = ["exact passage copied from the failed cases, probe source, or subject excerpts"]


def _bounded(value, limit=EXCERPT_CHARACTERS):
    if isinstance(value, str):
        return value[:limit]
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return value if len(text) <= limit else text[:limit]


def _supplied_paths(request):
    return {_relative_path(item["path"]) for item in request.project.get("writes", ())
            if isinstance(item, dict) and item.get("input_artifact") is True}


def _failed_cases(bundle, report):
    """Each failed case with its declaration, expectation, and observation."""
    declared = {case["case_id"]: case for case in bundle["proposal"]["cases"]}
    failed = []
    for check in report.get("checks", ()):
        if check.get("passed") is True:
            continue
        case = declared.get(check.get("case_id"), {})
        failed.append({"case_id": check.get("case_id"), "criterion_refs": check.get("criterion_refs"),
                       "purpose": case.get("purpose"), "comparison": case.get("comparison"),
                       "tolerance": case.get("tolerance"), "expected": check.get("expected"),
                       "completed": check.get("completed"), "observed": _bounded(check.get("observed")),
                       "stderr": str(check.get("stderr") or "")[:4000],
                       "error_code": check.get("error_code", ""), "judgment": check.get("judgment")})
    return failed


def _subject_excerpts(services, request, report):
    """Bounded text of authored and produced subject files, with every exclusion named."""
    supplied, excerpts, excluded, budget = _supplied_paths(request), [], [], EXCERPT_BUDGET
    for item in report["subject"]["inventory"]:
        if item["path"] in supplied:
            excluded.append({"path": item["path"], "reason": "supplied_input"})
            continue
        try:
            text = services.artifacts.store.get(
                ContextArtifactRef.from_dict(item["artifact_ref"])).decode("utf-8")
        except UnicodeDecodeError:
            excluded.append({"path": item["path"], "reason": "not_text"})
            continue
        if budget <= 0:
            excluded.append({"path": item["path"], "reason": "excerpt_budget"})
            continue
        limit = min(EXCERPT_CHARACTERS, budget)
        excerpts.append({"path": item["path"], "authored": item["authored"],
                         "content": text[:limit], "truncated": len(text) > limit,
                         "trust": "untrusted_subject_content"})
        budget -= min(len(text), limit)
    return excerpts, excluded


def _evidence(request, services, bundle, report):
    """The shared review material, and the texts a quoted passage may come from."""
    failed = _failed_cases(bundle, report)
    excerpts, excluded = _subject_excerpts(services, request, report)
    files = [{"path": item["path"], "content": str(item.get("content", ""))[:EXCERPT_CHARACTERS]}
             for item in bundle["proposal"]["files"]]
    packet = {"task": request.task, "registered_acceptance_criteria": dict(request.criteria),
              "failed_cases": failed,
              "passed_case_ids": [item["case_id"] for item in report["checks"] if item.get("passed") is True],
              "probe_files": files, "subject_excerpts": excerpts, "excluded_subject_files": excluded}
    texts = ([json.dumps(item, ensure_ascii=False, sort_keys=True, default=str) for item in failed]
             + [item["observed"] for item in failed if isinstance(item["observed"], str)]
             + [item["stderr"] for item in failed]
             + [item["content"] for item in files] + [item["content"] for item in excerpts])
    return packet, texts


def ground_classification(value, failed, texts) -> dict:
    """Admit a classification only with one grounded finding for every failed case."""
    ids = [item["case_id"] for item in failed]
    record = {"record_type": "independent_failure_classification/v1", "classification": "unknown",
              "repair_target": "none", "findings": [], "grounded": False, "failure": ""}
    if (not isinstance(value, dict) or value.get("classification") not in FAILURE_CLASSES
            or value.get("repair_target") not in REPAIR_TARGETS
            or not isinstance(value.get("findings"), list)):
        record["failure"] = "invalid_response"
        return record
    findings = {}
    for item in value["findings"]:
        if (not isinstance(item, dict) or item.get("case_id") not in ids
                or item["case_id"] in findings
                or item.get("classification") not in FAILURE_CLASSES
                or not isinstance(item.get("evidence"), list)
                or any(not isinstance(quote, str) for quote in item["evidence"])
                or not isinstance(item.get("reason"), str)):
            record["failure"] = "invalid_finding"
            return record
        quotes, missing = grounded_quotes(texts, item["evidence"])
        findings[item["case_id"]] = {"case_id": item["case_id"], "classification": item["classification"],
                                     "evidence": quotes, "missing_quotes": missing,
                                     "reason": item["reason"][:1000], "grounded": bool(quotes) and not missing}
    record.update(classification=value["classification"], repair_target=value["repair_target"],
                  findings=[findings[case_id] for case_id in ids if case_id in findings])
    if len(findings) != len(ids):
        record["failure"] = "finding_missing"
    elif not all(item["grounded"] for item in findings.values()):
        record["failure"] = "ungrounded_finding"
    else:
        record["grounded"] = True
    return record


def ground_confirmation(value, texts) -> dict:
    """Admit a confirmation only when it agrees and quotes material other than the claim."""
    record = {"record_type": "independent_failure_confirmation/v1", "confirmed": False,
              "evidence": [], "missing_quotes": [], "reason": "", "grounded": False, "failure": ""}
    if (not isinstance(value, dict) or type(value.get("confirmed")) is not bool
            or not isinstance(value.get("evidence"), list)
            or any(not isinstance(item, str) for item in value["evidence"])
            or not isinstance(value.get("reason"), str)):
        record["failure"] = "invalid_response"
        return record
    quotes, missing = grounded_quotes(texts, value["evidence"])
    record.update(confirmed=value["confirmed"], evidence=quotes, missing_quotes=missing,
                  reason=value["reason"][:1000])
    if not value["confirmed"]:
        record["failure"] = "not_confirmed"
    elif not quotes or missing:
        record["failure"] = "ungrounded_confirmation"
    else:
        record["grounded"] = True
    return record


def claims_check_defect(classification) -> bool:
    """A grounded classification whose every finding blames the check, not the work."""
    return bool(classification.get("grounded") is True
                and classification.get("classification") in CHECK_DEFECT_CLASSES
                and all(item["classification"] in CHECK_DEFECT_CLASSES
                        for item in classification.get("findings", ())))


def review_decision(classification, confirmation) -> str:
    if classification.get("grounded") is not True:
        return "keep_failure"
    if classification.get("classification") == "correct_failure":
        return "repair_work"
    if claims_check_defect(classification) and (confirmation or {}).get("grounded") is True:
        return "revise_check"
    return "keep_failure"


def rejects_known_wrong(cases, checks) -> bool:
    """Whether a check program failed at least one case on the known-wrong subject.

    A judged case is not judged here. It counts as rejecting only when its probe
    did not complete or printed too little text to quote, because an emptied
    deliverable cannot ground any judgment.
    """
    for case, check in zip(cases, checks):
        observed = check.get("observed")
        if case.get("comparison") == JUDGMENT_COMPARISON:
            if (check.get("completed") is not True or not isinstance(observed, str)
                    or len(" ".join(observed.split())) < MINIMUM_QUOTE_CHARACTERS):
                return True
        elif check.get("passed") is not True:
            return True
    return False


def _known_wrong_inputs(inputs, request):
    """The frozen subject with every authored and produced file emptied."""
    supplied = _supplied_paths(request)
    return tuple(item if item.path.removeprefix("subject/") in supplied
                 else GeneratedProjectInputArtifact(item.path, b"", media_type=item.media_type)
                 for item in inputs)


def _refs(call):
    return {"prompt_ref": (call or {}).get("prompt_ref"), "response_ref": (call or {}).get("response_ref")}


def _review_records(services):
    records = getattr(services, "independent_failure_reviews", None)
    if not isinstance(records, list):
        records = []
        services.independent_failure_reviews = records
    return records


def _summary(record):
    classification = record.get("classification") or {}
    return {"record_type": "independent_failure_review_summary/v1", "status": record["status"],
            "decision": record["decision"], "review_ref": record.get("review_ref"),
            "classification": classification.get("classification"),
            "repair_target": classification.get("repair_target"),
            "grounded": classification.get("grounded"), "failure": classification.get("failure"),
            "findings": [{key: item[key] for key in ("case_id", "classification", "reason")}
                         for item in classification.get("findings", ())],
            "confirmed": (record.get("confirmation") or {}).get("grounded"),
            "notes": record.get("notes", "")}


def _classify(request, services, active, report, record):
    bundle = verification._load(services, report["probe_ref"])
    packet, texts = _evidence(request, services, bundle, report)
    failed = packet["failed_cases"]
    classes = "|".join(FAILURE_CLASSES)
    value, call = verification._call(services, active, "failure_review", {
        "record_type": "independent_failure_review_request/v1", **packet,
        "responsibility": INDEPENDENT_FAILURE_REVIEW_PROMPT,
        "response_contract": {"classification": classes, "repair_target": "|".join(REPAIR_TARGETS),
                              "findings": [{"case_id": item["case_id"], "classification": classes,
                                            "evidence": _EVIDENCE_CONTRACT, "reason": "string"}
                                           for item in failed],
                              "notes": "string"}})
    record["classification"] = {**ground_classification(value, failed, texts), "call": _refs(call)}
    if claims_check_defect(record["classification"]):
        claim = {"classification": record["classification"]["classification"],
                 "findings": [{key: item[key] for key in ("case_id", "classification", "reason")}
                              for item in record["classification"]["findings"]],
                 "trust": "untrusted_model_claim"}
        answer, confirm_call = verification._call(services, active, "failure_confirmation", {
            "record_type": "independent_failure_confirmation_request/v1", **packet, "claim": claim,
            "responsibility": INDEPENDENT_FAILURE_CONFIRMATION_PROMPT,
            "response_contract": {"confirmed": "boolean", "evidence": _EVIDENCE_CONTRACT,
                                  "reason": "string"}})
        record["confirmation"] = {**ground_confirmation(answer, texts), "call": _refs(confirm_call)}
    record["decision"] = review_decision(record["classification"], record["confirmation"])
    record["status"] = "reviewed"
    if record["decision"] == "revise_check":
        record["disputed_proposal"] = bundle["proposal"]


def _revise(request, services, active, report, record):
    """Design a revised check and admit it only when it rejects the known-wrong subject."""
    key = report["task_digest"]
    previous = services.independent_probe_cache.pop(key, None)
    reference, admitted = None, False
    revision = {"record_type": REVISION_RECORD_TYPE, "review_ref": record["review_ref"],
                "disputed_probe_ref": report["probe_ref"], "revised_probe_ref": None,
                "subject_digest": report["subject_digest"], "known_wrong_subject": KNOWN_WRONG_SUBJECT,
                "admitted": False, "plan_attempts": [], "oracle_reviews": []}
    try:
        if (services.request.allow_workspace_writes is not True
                or services.request.allow_sandbox_commands is not True):
            raise PermissionError("a check revision needs existing workspace and sandbox authority")
        subject, inputs, visible = verification._freeze(request, services)
        if verification._digest(subject) != report["subject_digest"]:
            raise ValueError("independent subject changed before the check revision")
        bundle, reference = verification._probe(
            request, services, active, subject, visible,
            plan_attempts=revision["plan_attempts"], oracle_reviews=revision["oracle_reviews"])
        # The probe step caches its bundle; a revision holds it back until it discriminates.
        services.independent_probe_cache.pop(key, None)
        manifest = verification._validate_probe(bundle["proposal"], request.criteria)
        execution = verification.execute_generated_project(GeneratedProjectExecutionRequest(
            manifest, str(Path(services.workspace_base) / "independent" / (active.loop_id + "-known-wrong")),
            GeneratedProjectAuthority(services.run_id, True, True, False, allow_local_execution=False),
            subject["image"], input_artifacts=_known_wrong_inputs(inputs, request),
            read_only_execution=True), GeneratedProjectExecutionContext(active))
        checks = verification._compare(bundle["proposal"]["cases"], execution)
        admitted = bool(verification._valid_execution(execution, checks, subject["image"])
                        and rejects_known_wrong(bundle["proposal"]["cases"], checks))
        revision.update(revised_probe_ref=reference, image=subject["image"], checks=checks,
                        execution_ref=verification._store(services, execution, "independent_known_wrong_execution"),
                        admitted=admitted)
        if not admitted:
            revision["notes"] = "The revised check passed the known-wrong subject, so it was refused."
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:
        revision["notes"] = "Check revision unavailable: " + str(exc)[:300]
        revision["error_type"] = type(exc).__name__
    finally:
        if admitted:
            services.independent_probe_cache[key] = reference
        elif previous is not None:
            services.independent_probe_cache[key] = previous
    revision_ref = verification._store(services, revision, "independent_check_revision")
    active.ledger.record(loop_id=active.loop_id, event="custom", custom_kind="independent_check_revision",
                         revision_ref=revision_ref, admitted=admitted,
                         revised_probe_digest=(reference or {}).get("digest"),
                         disputed_probe_digest=report["probe_ref"].get("digest"))
    return {"record_type": "independent_check_revision_summary/v1", "admitted": admitted,
            "revision_ref": revision_ref, "revised_probe_ref": reference,
            "notes": revision.get("notes", "")}


def review_failed_independent_check(request, services, owner_loop, report) -> dict:
    """Review one failed report; return fields for the parent's check entry.

    The result always has ``failure_review`` for a failed report. A confirmed
    check defect adds ``revision``, and when the admitted revision produced a
    passed or failed report, that ``report`` replaces the failed one. A review
    that cannot finish keeps the original failure and records why. One failed
    report of a check on one subject is reviewed once.
    """
    if not isinstance(report, dict) or report.get("status") != "failed":
        return {}
    reviews = _review_records(services)
    probe_digest = (report.get("probe_ref") or {}).get("digest")
    for existing in reversed(reviews):
        if (existing.get("probe_digest") == probe_digest
                and existing.get("subject_digest") == report.get("subject_digest")):
            return {"failure_review": _summary(existing)}
    config = LoopConfig(
        framework="custom", custom_steps=("verify",), power="light",
        allowable_modes=("deterministic", "hybrid", "non_deterministic"),
        preferred_modes=("non_deterministic", "hybrid", "deterministic"),
        delegated_modes=("deterministic", "hybrid", "non_deterministic"),
        exit_condition="steps_complete")
    loop = owner_loop.spawn(
        "review a failed independent check", config,
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.verifier"),
        relationship=LoopRelationship.spawned_by(owner_loop.loop_id))
    holder = {}

    def handler(active, _step, _context):
        record = {"record_type": REVIEW_RECORD_TYPE, "status": "unavailable", "decision": "keep_failure",
                  "reviewer_loop_id": active.loop_id, "producer_loop_id": owner_loop.loop_id,
                  "report_digest": report.get("report_digest"), "probe_digest": probe_digest,
                  "subject_digest": report.get("subject_digest"), "task_digest": report.get("task_digest"),
                  "classification": None, "confirmation": None,
                  "grants_task_acceptance": False, "grants_promotion": False}
        try:
            _classify(request, services, active, report, record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            record.update(status="unavailable", decision="keep_failure", error_type=type(exc).__name__,
                          notes="Failure review unavailable: " + str(exc)[:300])
        stored = {key: value for key, value in record.items() if key != "disputed_proposal"}
        record["review_ref"] = verification._store(services, stored, "independent_failure_review")
        reviews.append(record)
        active.ledger.record(loop_id=active.loop_id, event="custom", custom_kind="independent_failure_review",
                             review_ref=record["review_ref"], status=record["status"],
                             decision=record["decision"], probe_digest=probe_digest,
                             subject_digest=record["subject_digest"])
        holder["result"] = {"failure_review": _summary(record)}
        if record["decision"] == "revise_check":
            holder["result"]["revision"] = _revise(request, services, active, report, record)
        return StepOutcome("independent_failure_review:" + record["decision"], "deterministic", 1.0)

    loop.run(handler=handler, max_steps=len(loop.steps()) + 1)
    result = holder.get("result", {})
    if (result.get("revision") or {}).get("admitted") is True:
        try:
            revised = verification.run_independent_verification(request, services, owner_loop)
        except Exception as exc:  # noqa: BLE001
            result["revision"]["notes"] = "Revised check unavailable: " + str(exc)[:300]
        else:
            result["revision"].update(revised_status=revised.get("status"),
                                      revised_report_digest=revised.get("report_digest"))
            if revised.get("status") in ("passed", "failed"):
                result["report"] = revised
    return result


def validate_check_revision(report, services, owner_loop) -> None:
    """Refuse a report whose check came from a revision that did not reject its known-wrong subject."""
    probe_ref = report.get("probe_ref") if isinstance(report, dict) else None
    digest = probe_ref.get("digest") if isinstance(probe_ref, dict) else None
    for event in owner_loop.ledger.events:
        if (event.get("custom_kind") != "independent_check_revision"
                or digest is None or event.get("revised_probe_digest") != digest):
            continue
        revision = verification._load(services, event["revision_ref"])
        bundle = verification._load(services, probe_ref)
        execution = verification._load(services, revision.get("execution_ref"))
        checks = verification._compare(bundle["proposal"]["cases"], execution)
        if (revision.get("record_type") != REVISION_RECORD_TYPE
                or revision.get("revised_probe_ref") != probe_ref or revision.get("admitted") is not True
                or event.get("admitted") is not True or checks != revision.get("checks")
                or not verification._valid_execution(execution, checks, revision.get("image"))
                or not rejects_known_wrong(bundle["proposal"]["cases"], checks)):
            raise ValueError("revised independent check did not reject its known-wrong subject")


def self_test() -> dict:
    from .independent_failure_review_checks import run_checks
    return run_checks()
