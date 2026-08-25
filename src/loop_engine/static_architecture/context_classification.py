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

from .context_ontology import (QUESTION_FAMILIES, THINKING_METHODS,
                               extract_key_phrases)


CONTEXT_HIERARCHY_FIELDS = (
    "context_type", "industry", "domain", "subdomain", "topic",
    "role_family", "job_role", "seniority", "project_type", "task_type",
    "deliverable", "workflow_stage", "thinking_style", "question_family",
    "speech_act", "polarity", "comparison_mode", "detail_direction",
    "list_structure", "ordering_rule", "response_shape",
    "serialization_format", "format_example",
    "geography", "jurisdiction", "time_horizon", "source_policy",
    "source_refs", "claim_status", "evidence_status", "access_level",
    "source_type", "freshness_status", "risk_level",
    "applicability_status",
    "possible_code_target", "scope", "lifecycle", "source", "digest",
    "key_phrases", "labels", "relationships", "utility_status",
    "utility_history", "failure_history", "tags")

CONTEXT_THINKING_STYLES = THINKING_METHODS

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
    tokens = re.findall(r"[a-z0-9_]+", " ".join(
        str(value or "").lower() for value in values))
    phrases = {"_".join(tokens[index:index + size])
               for size in (2, 3)
               for index in range(max(0, len(tokens) - size + 1))}
    return set(tokens) | phrases


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
            facet_value = facets.get(key)
            if facet_value not in (None, "", (), []):
                return (list(facet_value) if isinstance(facet_value, tuple)
                        else facet_value)
            body_value = body.get(key)
            if body_value not in (None, "", (), []):
                return (list(body_value) if isinstance(body_value, tuple)
                        else body_value)
        return ""

    question_family = value("question_family")
    if not question_family:
        subcategory = str(body.get("subcategory")
                          or facets.get("subcategory") or "")
        question_family = subcategory if subcategory in QUESTION_FAMILIES else ""
    key_phrases = value("key_phrases") or extract_key_phrases(
        str(body.get("text") or body.get("template") or record.title))
    if isinstance(key_phrases, str):
        key_phrases = [key_phrases]
    raw_labels = value("labels")
    labels = (list(raw_labels) if isinstance(raw_labels, (list, tuple))
              else [raw_labels] if raw_labels else [])
    labels.extend(str(tag) for tag in tags if str(tag) not in labels)
    for key, label_value in (
            ("thinking", thinking), ("question", question_family),
            ("format", value("serialization_format")),
            ("shape", value("response_shape", "answer_shape"))):
        label = f"{key}:{label_value}" if label_value else ""
        if label and label not in labels:
            labels.append(label)
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
        "question_family": question_family,
        "speech_act": value("speech_act"),
        "polarity": value("polarity"),
        "comparison_mode": value("comparison_mode"),
        "detail_direction": value("detail_direction"),
        "list_structure": value("list_structure"),
        "ordering_rule": value("ordering_rule"),
        "response_shape": value("response_shape", "answer_shape",
                                "output_shape"),
        "serialization_format": value("serialization_format", "format"),
        "format_example": value("format_example"),
        "geography": value("geography"),
        "jurisdiction": value("jurisdiction"),
        "time_horizon": value("time_horizon", "timeframe"),
        "source_policy": value("source_policy"),
        "source_refs": value("source_refs"),
        "claim_status": value("claim_status"),
        "evidence_status": value("evidence_status"),
        "access_level": value("access_level"),
        "source_type": value("source_type"),
        "freshness_status": value("freshness_status"),
        "risk_level": value("risk_level"),
        "applicability_status": value("applicability_status"),
        "possible_code_target": value("possible_code_target"),
        "scope": value("scope") or base.get("scope", ""),
        "lifecycle": value("lifecycle", "maturity")
        or base.get("lifecycle", ""),
        "source": value("source", "provenance") or base.get("source", ""),
        "digest": value("digest"),
        "key_phrases": list(key_phrases),
        "labels": labels,
        "relationships": value("relationships"),
        "utility_status": value("utility_status"),
        "utility_history": value("utility_history"),
        "failure_history": value("failure_history"),
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
    from .facets import context_facets
    body_fallback = context_hierarchy(StoreRecord(
        "ctx.body", "context", "source-backed method",
        body={"digest": "abc123", "evidence_status": "source_backed",
              "utility_status": "helpful",
              "possible_code_target": "code.validator",
              "facets": context_facets(category="method")}),
        {"category_group": "method"})
    tests = [
        {"test": "explicit_context_axes_are_preserved",
         "passed": got["job_role"] == "mission operations lead"
         and got["domain"] == "space"
         and got["thinking_style"] == "first_principles"},
        {"test": "thinking_style_is_inferred_without_inventing_a_role",
         "passed": inferred["thinking_style"] == "gap_analysis"
         and inferred["job_role"] == ""},
        {"test": "empty_facets_do_not_mask_populated_body_metadata",
         "passed": body_fallback["digest"] == "abc123"
         and body_fallback["evidence_status"] == "source_backed"
         and body_fallback["utility_status"] == "helpful"
         and body_fallback["possible_code_target"] == "code.validator"},
    ]
    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
