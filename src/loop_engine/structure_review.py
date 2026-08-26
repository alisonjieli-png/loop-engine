"""LLM-queryable structure review: evidence packets for semantic questions.

The LLM never receives the whole repository and a vague question. It
receives a bounded evidence packet: the constitution, the structure
rules, the tree, the diff, deterministic findings, and specific
questions. The LLM may identify semantic drift and request review. It
may not waive deterministic violations.
"""
from __future__ import annotations

import hashlib
import json

from .repository_conformance import run_repository_conformance
from .repository_structure import structure_report
from .architecture_contract import run_architecture_contract_checks

#: Questions the reviewer must answer for every structure change.
REVIEW_QUESTIONS = (
    "Does this new folder represent a stable architectural boundary, or "
    "should it be metadata on records?",
    "Does this change create a second operational Node type?",
    "Does this adapter expose provider-specific types outside its "
    "boundary?",
    "Does this plugin create a parallel runtime or plugin host?",
    "Does this path imply that mutable Learned Intelligence is shipped "
    "inside the immutable package?",
    "Does this query-engine change alter canonical query semantics?",
    "Is a provider implementation being mistaken for a Port?",
    "Does the new database become implicitly authoritative?",
    "Is the fallback explicit and compatible?",
    "Does this rename leave documentation, manifests, references, "
    "migrations, or tests behind?",
    "Does this directory classify solutions semantically in folders "
    "where typed attributes would be more appropriate?",
    "Does the structure still allow replacing DuckDB without changing "
    "LoopNode or IntelligenceRecord?",
)


def build_review_packet() -> dict:
    """Deterministic evidence packet for an LLM structure review."""
    structure = structure_report()
    conformance = run_repository_conformance()
    contract = run_architecture_contract_checks()
    packet = {
        "record_type": "structure_review_packet/v1",
        "questions": REVIEW_QUESTIONS,
        "deterministic_findings": {
            "structure_violations": structure["violations"],
            "conformance_problems": conformance["problems"],
            "contract_problems": contract["problems"],
        },
        "tree": structure["tree"],
        "files_indexed": conformance["files_indexed"],
    }
    serialized = json.dumps(packet, sort_keys=True, default=str)
    packet["input_hash"] = hashlib.sha256(
        serialized.encode("utf-8")).hexdigest()
    return packet


def validate_review_response(response: dict) -> list[str]:
    """Validate a structured LLM review response against its contract."""
    problems = []
    if not isinstance(response, dict):
        return ["review response must be a mapping"]
    if response.get("verdict") not in (
            "pass", "needs_review", "blocked"):
        problems.append("verdict must be pass, needs_review, or blocked")
    findings = response.get("findings")
    if not isinstance(findings, list):
        problems.append("findings must be a list")
        return problems
    for finding in findings:
        if not isinstance(finding, dict):
            problems.append("each finding must be a mapping")
            continue
        if not finding.get("invariant_id"):
            problems.append("each finding needs an invariant_id")
        if not finding.get("paths"):
            problems.append("each finding needs evidence paths")
        if finding.get("severity") not in (
                "low", "medium", "high", "critical"):
            problems.append("finding severity must be low, medium, high, "
                            "or critical")
    return problems


def apply_review_verdict(deterministic_passed: bool,
                         review_response: dict) -> dict:
    """Combine deterministic checks with the LLM review.

    The LLM may not waive deterministic violations. A deterministic
    failure is BLOCKED regardless of the review verdict.
    """
    problems = validate_review_response(review_response)
    if problems:
        return {"verdict": "blocked",
                "reason": "invalid review response",
                "problems": problems}
    if not deterministic_passed:
        return {"verdict": "blocked",
                "reason": "deterministic violations cannot be waived by "
                          "an LLM review"}
    if review_response.get("verdict") == "blocked":
        return {"verdict": "blocked",
                "reason": "reviewer blocked the change"}
    if review_response.get("verdict") == "needs_review":
        return {"verdict": "needs_review",
                "reason": "reviewer requested human review"}
    return {"verdict": "pass", "reason": "deterministic checks and "
                                         "review both passed"}


def self_test() -> dict:
    """Prove the review contract and the no-waiver rule."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    packet = build_review_packet()
    check("review_packet_carries_questions_and_findings",
          len(packet["questions"]) == len(REVIEW_QUESTIONS)
          and "deterministic_findings" in packet
          and len(packet["input_hash"]) == 64)
    check("review_packet_is_deterministic",
          build_review_packet()["input_hash"] == packet["input_hash"])

    good = {"verdict": "pass", "findings": []}
    check("valid_review_response_is_accepted",
          not validate_review_response(good))
    bad = {"verdict": "maybe", "findings": [{"invariant_id": "LE-X"}]}
    check("invalid_review_response_is_rejected",
          bool(validate_review_response(bad)))

    verdict = apply_review_verdict(False, good)
    check("llm_cannot_waive_deterministic_violations",
          verdict["verdict"] == "blocked"
          and "cannot be waived" in verdict["reason"])
    verdict = apply_review_verdict(True, good)
    check("clean_review_passes",
          verdict["verdict"] == "pass")
    verdict = apply_review_verdict(True, {"verdict": "needs_review",
                                          "findings": []})
    check("ambiguous_review_requests_human_review",
          verdict["verdict"] == "needs_review")
    return {"tests": results}
