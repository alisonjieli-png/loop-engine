"""Context Intelligence hierarchy and deterministic classification helpers.

Architectural role: Static Architecture classification service.

Owns: the Context-specific hierarchy fields, thinking-style vocabulary, and
conservative projection of one stored record. Empty values stay empty.

Does not own: the four-layer catalog, retrieval, candidate promotion, or any
source-of-truth decision.

Verification: ``self_test()`` checks explicit and inferred hierarchy values.
"""
from __future__ import annotations

import re


CONTEXT_HIERARCHY_FIELDS = (
    "context_type", "industry", "domain", "subdomain", "topic",
    "role_family", "job_role", "seniority", "project_type", "task_type",
    "deliverable", "workflow_stage", "thinking_style", "response_shape",
    "geography", "jurisdiction", "time_horizon", "source_policy",
    "source_refs", "claim_status", "possible_code_target", "scope",
    "lifecycle", "source", "digest", "tags")

CONTEXT_THINKING_STYLES = (
    "first_principles", "analogy", "outline_to_detail", "gap_analysis",
    "improvement", "avoidance", "best_practices", "failure_analysis",
    "inversion", "adversarial_review", "comparison", "prioritization",
    "verification", "exploration", "other")

_THINKING_HINTS = (
    ("first_principles", ("first_principles", "invariant", "fundamental")),
    ("analogy", ("analogy", "analogical", "far_transfer")),
    ("outline_to_detail", ("outline", "decompose", "decomposition", "steps")),
    ("gap_analysis", ("missing", "gap", "coverage")),
    ("improvement", ("improve", "improvement", "optimize", "better")),
    ("avoidance", ("avoid", "warning", "mistake", "anti_pattern")),
    ("best_practices", ("best_practice", "checklist", "recommended")),
    ("failure_analysis", ("failure", "premortem", "postmortem", "risk")),
    ("inversion", ("invert", "reverse", "opposite")),
    ("adversarial_review", ("adversarial", "devils_advocate", "attack")),
    ("comparison", ("compare", "comparison", "pairwise")),
    ("prioritization", ("prioritize", "rank", "top_ten")),
    ("verification", ("verify", "validation", "evidence", "falsify")),
    ("exploration", ("novel", "brainstorm", "alternative", "explore")),
)


def _words(*values) -> set:
    return set(re.findall(r"[a-z0-9_]+", " ".join(
        str(value or "").lower() for value in values)))


def context_hierarchy(record, classification: "dict | None" = None) -> dict:
    """Return the composable Context Intelligence axes for one record."""
    body = dict(record.body or {})
    facets = dict(body.get("facets") or {})
    tags = tuple(record.tags or ())
    base = classification or {}
    words = _words(record.title, body.get("text"), body.get("template"),
                   body.get("category"), body.get("subcategory"), *tags)
    thinking = str(facets.get("thinking_style")
                   or body.get("thinking_style")
                   or body.get("thinking_method") or "")
    if not thinking:
        for style, hints in _THINKING_HINTS:
            if words & set(hints):
                thinking = style
                break
    thinking = thinking if thinking in CONTEXT_THINKING_STYLES else (
        thinking or "other")

    def value(name: str, *aliases: str):
        for key in (name,) + aliases:
            got = facets.get(key, body.get(key, ""))
            if got not in (None, "", (), []):
                return list(got) if isinstance(got, tuple) else got
        return ""

    return {
        "schema": "context_hierarchy/v1",
        "context_type": value("context_type")
        or base.get("category_group", "other"),
        "industry": value("industry"),
        "domain": value("domain"),
        "subdomain": value("subdomain"),
        "topic": value("topic", "target"),
        "role_family": value("role_family", "job_family"),
        "job_role": value("job_role", "job_title", "job_position"),
        "seniority": value("seniority"),
        "project_type": value("project_type"),
        "task_type": value("task_type", "task_family"),
        "deliverable": value("deliverable"),
        "workflow_stage": value("workflow_stage", "task_stage", "stage"),
        "thinking_style": thinking,
        "response_shape": value("response_shape", "answer_shape",
                                "output_shape"),
        "geography": value("geography"),
        "jurisdiction": value("jurisdiction"),
        "time_horizon": value("time_horizon", "timeframe"),
        "source_policy": value("source_policy"),
        "source_refs": value("source_refs"),
        "claim_status": value("claim_status"),
        "possible_code_target": value("possible_code_target"),
        "scope": value("scope") or base.get("scope", ""),
        "lifecycle": value("lifecycle", "maturity")
        or base.get("lifecycle", ""),
        "source": value("source", "provenance") or base.get("source", ""),
        "digest": value("digest"),
        "tags": list(tags),
    }


def self_test() -> dict:
    from .store_serve import StoreRecord
    explicit = StoreRecord(
        "ctx.space", "question", "review mission assumptions",
        body={"job_title": "mission operations lead", "domain": "space",
              "facets": {"context_type": "question",
                         "thinking_style": "first_principles",
                         "project_type": "earth_observation"}},
        tags=("mission",))
    got = context_hierarchy(explicit, {"category_group": "question"})
    inferred = context_hierarchy(StoreRecord(
        "ctx.missing", "question", "What is missing from this plan?",
        tags=("coverage",)), {"category_group": "question"})
    tests = [
        {"test": "explicit_context_axes_are_preserved",
         "passed": got["job_role"] == "mission operations lead"
         and got["domain"] == "space"
         and got["thinking_style"] == "first_principles"},
        {"test": "thinking_style_is_inferred_without_inventing_a_role",
         "passed": inferred["thinking_style"] == "gap_analysis"
         and inferred["job_role"] == ""},
    ]
    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
