"""Untrusted page parsing and mechanical qualification evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path

from source_qualification_records import (
    DOWNLOAD_PLAN_TYPE,
    EVALUATOR_CANDIDATE_TYPE,
    SAFE_PAGE_KINDS,
    SUCCESSFUL_PREFLIGHT_STATUSES,
    HumanLegalReview,
    IndependentEvaluatorReview,
    PageCommandResult,
    SourceQualificationRequest,
    bytes_digest,
    digest,
    utc_datetime,
)


def normalized_page_kind(name: object) -> tuple[str, str]:
    raw = str(name or "").strip().lower()
    normalized = re.sub(r"[_\s]+", "-", raw)
    kind = normalized if normalized in SAFE_PAGE_KINDS else "other"
    return kind, bytes_digest(str(name or "").encode("utf-8"))


def parse_pages(
    result: PageCommandResult,
    request: SourceQualificationRequest,
) -> tuple[list[tuple[str, str, bytes]], str]:
    if len(result.stdout) > request.bytes.maximum_response_bytes:
        return [], "CONTENT_SIZE_EXCEEDED"
    try:
        payload = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [], "PAGE_RESPONSE_INVALID"
    if not isinstance(payload, list):
        return [], "PAGE_RESPONSE_INVALID"
    if len(payload) > request.bytes.maximum_pages_per_competition:
        return [], "PAGE_COUNT_EXCEEDED"
    pages: list[tuple[str, str, bytes]] = []
    total = 0
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get("content"), str):
            return [], "PAGE_RESPONSE_INVALID"
        kind, name_digest = normalized_page_kind(item.get("name"))
        body = item["content"].encode("utf-8")
        if len(body) > request.bytes.maximum_page_body_bytes:
            return [], "PAGE_BODY_SIZE_EXCEEDED"
        total += len(body)
        if total > request.bytes.maximum_total_private_bytes:
            return [], "PRIVATE_BYTE_BUDGET_EXCEEDED"
        pages.append((kind, name_digest, body))
    return pages, "PARSED"


def artifact_path(root: Path, body_digest: str) -> Path:
    return root / "sha256" / body_digest[:2] / f"{body_digest}.page"


_METRIC_PATTERNS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "root_mean_squared_logarithmic_error",
        ("rmsle", "root mean squared logarithmic error"),
        "MINIMIZE",
    ),
    (
        "root_mean_squared_error",
        ("rmse", "root mean squared error"),
        "MINIMIZE",
    ),
    ("mean_squared_error", ("mean squared error",), "MINIMIZE"),
    ("mean_absolute_error", ("mae", "mean absolute error"), "MINIMIZE"),
    ("log_loss", ("log loss", "logarithmic loss"), "MINIMIZE"),
    ("roc_auc", ("roc auc", "area under the roc curve", "auc"), "MAXIMIZE"),
    ("f1", ("f1 score", "f1-score"), "MAXIMIZE"),
    ("accuracy", ("accuracy",), "MAXIMIZE"),
    (
        "mean_average_precision",
        ("mean average precision", "map@"),
        "MAXIMIZE",
    ),
    (
        "ndcg",
        ("ndcg", "normalized discounted cumulative gain"),
        "MAXIMIZE",
    ),
    ("quadratic_weighted_kappa", ("quadratic weighted kappa",), "MAXIMIZE"),
    ("pearson_correlation", ("pearson correlation",), "MAXIMIZE"),
    ("spearman_correlation", ("spearman correlation",), "MAXIMIZE"),
)


def mechanical_facts(page_bodies: dict[str, list[bytes]]) -> dict:
    rules_text = (
        b"\n".join(page_bodies.get("rules", ()))
        .decode("utf-8", errors="replace")
        .lower()
    )
    evaluation_text = (
        b"\n".join(page_bodies.get("evaluation", ()))
        .decode("utf-8", errors="replace")
        .lower()
    )
    all_text = f"{rules_text}\n{evaluation_text}"
    metric_matches = []
    for metric, markers, default_direction in _METRIC_PATTERNS:
        if any(marker in evaluation_text for marker in markers):
            metric_matches.append((metric, default_direction))
    unique_metrics = sorted({item[0] for item in metric_matches})
    metric = unique_metrics[0] if len(unique_metrics) == 1 else "UNKNOWN"
    direction_candidates = {item[1] for item in metric_matches}
    if any(
        marker in evaluation_text
        for marker in ("lower is better", "minimized", "minimise", "minimize")
    ):
        direction_candidates.add("MINIMIZE")
    if any(
        marker in evaluation_text
        for marker in ("higher is better", "maximized", "maximise", "maximize")
    ):
        direction_candidates.add("MAXIMIZE")
    direction = (
        next(iter(direction_candidates))
        if len(direction_candidates) == 1 and metric != "UNKNOWN"
        else "UNKNOWN"
    )
    license_candidates = []
    for code, markers in (
        ("CC_BY", ("cc by", "creative commons attribution")),
        (
            "CC_BY_SA",
            ("cc by-sa", "creative commons attribution-sharealike"),
        ),
        (
            "COMPETITION_USE_ONLY",
            ("competition use only", "only for the purpose of participating"),
        ),
        ("NON_COMMERCIAL", ("non-commercial", "noncommercial")),
        ("NO_REDISTRIBUTION", ("do not redistribute", "may not redistribute")),
    ):
        if any(marker in rules_text for marker in markers):
            license_candidates.append(code)
    external_model_candidate = "UNKNOWN"
    denial_markers = (
        "pre-trained models are not allowed",
        "pretrained models are not allowed",
        "external models are not allowed",
        "large language models are not allowed",
    )
    allow_markers = (
        "pre-trained models are allowed",
        "pretrained models are allowed",
        "external models are allowed",
        "large language models are allowed",
    )
    if any(marker in rules_text for marker in denial_markers):
        external_model_candidate = "DENY_CANDIDATE"
    elif any(marker in rules_text for marker in allow_markers):
        external_model_candidate = "ALLOW_CANDIDATE"
    instruction_markers = any(
        marker in all_text
        for marker in (
            "ignore previous instructions",
            "ignore all prior instructions",
            "system prompt",
            "kaggle competitions download",
            "kaggle competitions submit",
        )
    )
    return {
        "metric_candidate": metric,
        "metric_candidates": unique_metrics,
        "direction_candidate": direction,
        "license_or_data_use_candidates": sorted(set(license_candidates)),
        "external_model_permission_candidate": external_model_candidate,
        "untrusted_instruction_markers_detected": instruction_markers,
        "extraction_method": "bounded_mechanical_pattern_proposal/v1",
        "grants_legal_authority": False,
        "admits_evaluator": False,
    }


def deadline_assessment(deadline_value: object, as_of: str) -> dict:
    value = str(deadline_value or "").strip()
    if not value:
        return {
            "state": "UNKNOWN",
            "deadline": "",
            "as_of": as_of,
            "source": "verified_preflight_population",
        }
    try:
        deadline = utc_datetime(value, "competition deadline")
    except ValueError:
        return {
            "state": "UNREADABLE",
            "deadline": "",
            "as_of": as_of,
            "source": "verified_preflight_population",
        }
    now = utc_datetime(as_of, "as_of")
    return {
        "state": "ACTIVE" if deadline > now else "EXPIRED",
        "deadline": deadline.isoformat(),
        "as_of": now.isoformat(),
        "source": "verified_preflight_population",
    }


def evaluator_candidate(slug: str, source_bundle_digest: str, facts: dict) -> dict:
    metric = facts["metric_candidate"]
    direction = facts["direction_candidate"]
    candidate = {
        "record_type": EVALUATOR_CANDIDATE_TYPE,
        "competition_slug": slug,
        "source_bundle_digest": source_bundle_digest,
        "metric": metric,
        "direction": direction,
        "prediction_contract": {
            "state": "REQUIRES_AUTHORIZED_SOURCE_ACQUISITION",
            "sample_submission_required": True,
            "ground_truth_required": True,
        },
        "independence": {
            "must_not_read_solver_conclusion": True,
            "must_be_verified_by_separate_process": True,
        },
        "implementation_ref": "",
        "admission_state": "CANDIDATE_ONLY",
        "mechanically_complete": metric != "UNKNOWN" and direction != "UNKNOWN",
    }
    candidate["candidate_digest"] = digest(candidate)
    return candidate


def source_completeness(probe: dict, artifact_records: list[dict]) -> dict:
    status = str(probe.get("status") or "")
    file_count = probe.get("file_count_returned")
    known_bytes = probe.get("known_total_bytes")
    unknown_sizes = probe.get("files_with_unknown_size", 0)
    truncated = bool(probe.get("may_be_truncated"))
    page_kinds = {item["page_kind"] for item in artifact_records}
    reasons = []
    if status not in SUCCESSFUL_PREFLIGHT_STATUSES:
        reasons.append("PREFLIGHT_FILE_LIST_UNAVAILABLE")
    if (
        status == "files_listing_empty"
        or not isinstance(file_count, int)
        or file_count < 1
    ):
        reasons.append("SOURCE_FILE_LIST_EMPTY")
    if truncated:
        reasons.append("SOURCE_FILE_LIST_TRUNCATED")
    if not isinstance(known_bytes, int) or known_bytes < 0:
        reasons.append("SOURCE_BYTE_TOTAL_UNKNOWN")
    if isinstance(unknown_sizes, int) and unknown_sizes > 0:
        reasons.append("SOURCE_FILE_SIZES_INCOMPLETE")
    if "rules" not in page_kinds:
        reasons.append("RULES_PAGE_MISSING")
    if "evaluation" not in page_kinds:
        reasons.append("EVALUATION_PAGE_MISSING")
    return {
        "state": "COMPLETE" if not reasons else "PARTIAL",
        "reasons": sorted(set(reasons)),
        "preflight_probe_status": status,
        "file_count_returned": file_count if isinstance(file_count, int) else None,
        "known_total_bytes": known_bytes if isinstance(known_bytes, int) else None,
        "files_with_unknown_size": (
            unknown_sizes if isinstance(unknown_sizes, int) else None
        ),
        "listing_may_be_truncated": truncated,
        "rules_page_present": "rules" in page_kinds,
        "evaluation_page_present": "evaluation" in page_kinds,
    }


def matching_legal_review(
    request: SourceQualificationRequest, slug: str, source_digest: str
) -> tuple[HumanLegalReview | None, str]:
    review = next(
        (item for item in request.legal_reviews if item.competition_slug == slug),
        None,
    )
    if review is None:
        return None, "UNRESOLVED"
    if review.source_bundle_digest != source_digest:
        return None, "STALE_SOURCE_BINDING"
    if review.expires_at and utc_datetime(
        review.expires_at, "review expires_at"
    ) <= utc_datetime(request.as_of, "as_of"):
        return None, "EXPIRED_REVIEW"
    return review, "REVIEWED"


def matching_evaluator_review(
    request: SourceQualificationRequest, slug: str, candidate_digest: str
) -> tuple[IndependentEvaluatorReview | None, str]:
    review = next(
        (item for item in request.evaluator_reviews if item.competition_slug == slug),
        None,
    )
    if review is None:
        return None, "UNRESOLVED"
    if review.candidate_digest != candidate_digest:
        return None, "STALE_CANDIDATE_BINDING"
    if not review.verified:
        return review, "REJECTED"
    return review, "ADMITTED"


def qualification_state(
    *,
    retrieval_status: str,
    completeness: dict,
    deadline: dict,
    evaluator: dict,
    legal_review: HumanLegalReview | None,
    legal_state: str,
    evaluator_review: IndependentEvaluatorReview | None,
    evaluator_state: str,
    require_external_model_permission: bool,
) -> tuple[str, list[str]]:
    blocked = []
    unsupported = []
    deferred = []
    if retrieval_status != "PARSED":
        blocked.append(retrieval_status)
    if deadline["state"] == "EXPIRED":
        blocked.append("COMPETITION_DEADLINE_PASSED")
    elif deadline["state"] != "ACTIVE":
        deferred.append("COMPETITION_DEADLINE_UNRESOLVED")
    if "SOURCE_FILE_LIST_EMPTY" in completeness["reasons"]:
        unsupported.append("SOURCE_FILE_LIST_EMPTY")
    incomplete_reasons = set(completeness["reasons"]) - {
        "SOURCE_FILE_LIST_EMPTY",
        "EVALUATION_PAGE_MISSING",
    }
    if incomplete_reasons:
        deferred.extend(sorted(incomplete_reasons))
    if not evaluator["mechanically_complete"]:
        unsupported.append("INDEPENDENT_EVALUATOR_CONTRACT_UNRESOLVED")
    if legal_review is None:
        deferred.append(f"HUMAN_LEGAL_REVIEW_{legal_state}")
    else:
        if legal_review.data_use_decision == "DENY":
            blocked.append("DATA_USE_DENIED_BY_REVIEW")
        if require_external_model_permission:
            if legal_review.external_model_decision == "DENY":
                blocked.append("EXTERNAL_MODEL_USE_DENIED_BY_REVIEW")
            elif legal_review.external_model_decision == "UNKNOWN":
                deferred.append("EXTERNAL_MODEL_USE_UNRESOLVED_BY_REVIEW")
    if evaluator_review is None or evaluator_state != "ADMITTED":
        deferred.append(f"INDEPENDENT_EVALUATOR_REVIEW_{evaluator_state}")
    if blocked:
        return "BLOCKED", sorted(set(blocked + unsupported + deferred))
    if unsupported:
        return "UNSUPPORTED", sorted(set(unsupported + deferred))
    if deferred:
        return "DEFERRED", sorted(set(deferred))
    return "QUALIFIED", []


def download_plan(
    slug: str,
    source_bundle_digest: str,
    completeness: dict,
    qualification: str,
) -> dict:
    return {
        "record_type": DOWNLOAD_PLAN_TYPE,
        "competition_slug": slug,
        "source_bundle_digest": source_bundle_digest,
        "source_file_count": completeness["file_count_returned"],
        "known_source_bytes": completeness["known_total_bytes"],
        "source_complete": completeness["state"] == "COMPLETE",
        "qualification_state": qualification,
        "execution_status": "NOT_EXECUTED",
        "execution_authorized": False,
        "required_authority_contract": "KaggleDownloadAuthority",
        "requires_exact_qualification_record_digest": True,
        "requires_exact_destination_and_byte_budget": True,
        "commands": [],
        "downloads_performed": 0,
    }


__all__ = [
    "artifact_path",
    "deadline_assessment",
    "download_plan",
    "evaluator_candidate",
    "matching_evaluator_review",
    "matching_legal_review",
    "mechanical_facts",
    "normalized_page_kind",
    "parse_pages",
    "qualification_state",
    "source_completeness",
]
