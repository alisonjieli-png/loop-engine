"""Domain Context Intelligence seeding through the shared Loop runtime.

Architectural role: Code Node system for a Self-Improvement Loop task.

Owns: a bounded seed specification, deterministic Context candidate generation,
classification, role-specific spawned loops, research questions, and a candidate
manifest.

Does not own: web research, source approval, persistent installation, or
promotion. A separate source-aware research loop and independent review own
those decisions.

Public entry points: ``ContextSeedSpec``, ``run_context_seed``, and
``domain_research_questions``.

Verification: ``self_test()`` uses space work with no model, network, or file
write.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass


SOURCE_POLICIES = ("primary_first", "official_first", "provided_only")

CONTEXT_SEED_STEPS = (
    "scope_domain", "audit_coverage", "map_roles_and_work",
    "define_research_questions", "generate_context", "classify",
    "deduplicate", "verify", "stage", "report")

DEFAULT_ROLES = (
    "domain expert", "researcher", "safety engineer", "data engineer",
    "software engineer", "product manager", "operations specialist",
    "regulatory specialist", "customer or end user")

CONTEXT_PATTERNS = (
    {"name": "first_principles", "context_type": "question",
     "response_shape": "decomposition",
     "text": ("From the perspective of {role}, reduce {task} for {project} "
              "in {domain} to its "
              "invariants. Which assumptions can be removed?")},
    {"name": "analogy", "context_type": "question",
     "response_shape": "comparison",
     "text": ("From the perspective of {role}, which solved problem offers "
              "the strongest analogy "
              "for {task} in {project} within {domain}, and where does it fail?")},
    {"name": "outline_to_detail", "context_type": "method",
     "response_shape": "decomposition",
     "text": ("Outline {task} for {project} in {domain}. Expand the outline "
              "into detailed steps and identify the first executable action.")},
    {"name": "gap_analysis", "context_type": "question",
     "response_shape": "list",
     "text": ("From the perspective of {role}, what is missing from a normal "
              "plan for {task} in {project} within {domain}?")},
    {"name": "top_improvements", "context_type": "question",
     "response_shape": "ranking",
     "text": ("From the perspective of {role}, rank the ten changes most "
              "likely to improve {task} "
              "for {project} in {domain} by value, effort, and risk.")},
    {"name": "avoidance", "context_type": "warning",
     "response_shape": "list",
     "text": ("From the perspective of {role}, list the ten mistakes most "
              "likely to damage {task} "
              "for {project} in {domain}, and how to detect each one early.")},
    {"name": "best_practices", "context_type": "checklist",
     "response_shape": "list",
     "text": ("Build a {role} checklist of best practices before, during, and "
              "after {task} for {project} in {domain}.")},
    {"name": "failure_analysis", "context_type": "warning",
     "response_shape": "verdict",
     "text": ("Assume {task} failed badly in {project}. From the perspective "
              "of {role}, identify "
              "the likely causes, earliest signals, and safest recovery.")},
    {"name": "inversion", "context_type": "method",
     "response_shape": "comparison",
     "text": ("From the perspective of {role}, reverse the main assumptions "
              "behind {task} for "
              "{project}. Which reversal changes the plan most?")},
    {"name": "adversarial_review", "context_type": "evaluation",
     "response_shape": "verdict",
     "text": ("Attack the proposed approach to {task} for {project} in "
              "{domain} from a {role} perspective. Name the decisive test.")},
    {"name": "evidence_review", "context_type": "checklist",
     "response_shape": "list",
     "text": ("What evidence would {role} require before accepting the "
              "result of {task} for {project} in {domain}?")},
    {"name": "alternatives", "context_type": "question",
     "response_shape": "proposals",
     "text": ("From the perspective of {role}, propose materially different "
              "ways to perform "
              "{task} for {project} in {domain}. Avoid cosmetic variations.")},
)

_THINKING_STYLE = {
    "top_improvements": "improvement",
    "best_practices": "best_practices",
    "evidence_review": "verification",
    "alternatives": "exploration",
}

_QUESTION_FAMILY = {
    "first_principles": "first_principles",
    "analogy": "analogy",
    "outline_to_detail": "outline_to_detail",
    "gap_analysis": "missing_items",
    "top_improvements": "top_improvements",
    "avoidance": "top_avoid",
    "best_practices": "best_practices",
    "failure_analysis": "failure_recovery",
    "inversion": "inversion",
    "adversarial_review": "adversarial_review",
    "evidence_review": "evidence_needed",
    "alternatives": "novel_alternatives",
}

_SPEECH_ACT = {
    "top_improvements": "rank", "avoidance": "warn",
    "best_practices": "instruct", "failure_analysis": "critique",
    "adversarial_review": "critique", "evidence_review": "verify",
    "alternatives": "generate",
}


@dataclass(frozen=True)
class ContextSeedSpec:
    """The bounded input to one domain Context seeding run."""
    domain: str
    industry: str = ""
    subdomain: str = ""
    project_types: tuple = ("general project",)
    task_types: tuple = ("plan and review the work",)
    job_roles: tuple = DEFAULT_ROLES
    geography: str = ""
    jurisdiction: str = ""
    time_horizon: str = "current"
    source_policy: str = "primary_first"
    source_refs: tuple = ()
    max_candidates: "int | None" = None

    def __post_init__(self):
        if not self.domain.strip():
            raise ValueError("a Context seed needs a domain")
        if self.source_policy not in SOURCE_POLICIES:
            raise ValueError(f"source_policy must be one of {SOURCE_POLICIES}")
        if not self.project_types or not self.task_types or not self.job_roles:
            raise ValueError("projects, tasks, and job roles cannot be empty")
        for name, values in (("project types", self.project_types),
                             ("task types", self.task_types),
                             ("job roles", self.job_roles)):
            if any(not str(value).strip() for value in values):
                raise ValueError(f"{name} cannot contain blank values")
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must be unique")
        if self.max_candidates is not None and self.max_candidates < 1:
            raise ValueError("max_candidates must be positive when provided")


@dataclass
class ContextSeedRun:
    """Candidate output plus the Loop run that produced it."""
    spec: ContextSeedSpec
    candidates: tuple
    research_questions: tuple
    manifest: dict
    loop_result: object
    ledger: object
    coverage_before: int = 0
    staged_only: bool = True

    def to_dict(self) -> dict:
        return {
            "schema": "context_seed_run/v1",
            "domain": self.spec.domain,
            "candidates": len(self.candidates),
            "research_questions": list(self.research_questions),
            "manifest": dict(self.manifest),
            "loop_id": self.loop_result.loop_id,
            "logical_kind": "search_improvement",
            "model_calls": self.loop_result.model_calls,
            "coverage_before": self.coverage_before,
            "staged_only": self.staged_only,
        }


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "general"


def _role_family(role: str) -> str:
    words = set(_slug(role).split("_"))
    rules = (
        ("data_ai_statistics", {"data", "statistician", "ml", "ai", "analyst"}),
        ("software_systems", {"software", "developer", "compiler", "database"}),
        ("science_engineering", {"scientist", "engineer", "astronomer", "physicist"}),
        ("health_safety", {"health", "clinical", "physician", "safety"}),
        ("operations_reliability", {"operations", "reliability", "sre", "mission"}),
        ("risk_compliance", {"risk", "regulatory", "auditor", "compliance"}),
        ("leadership_product", {"product", "project", "manager", "executive"}),
        ("research_review", {"researcher", "reviewer", "journalist"}),
        ("customer_domain", {"customer", "user", "domain"}),
    )
    return next((family for family, hints in rules if words & hints), "other")


def domain_research_questions(spec: ContextSeedSpec) -> tuple:
    """Questions a separate source-aware research loop should answer."""
    scope = spec.subdomain or spec.domain
    return (
        f"Which job families and job titles perform important work in {scope}?",
        f"Which project types and task families recur in {scope}?",
        f"Which people and organizations are consistently identified by "
        f"primary or official sources as important in {scope}, and why?",
        f"Which official standards, datasets, regulations, and primary sources "
        f"define accepted practice in {scope}?",
        f"Which failures, safety constraints, and disputed claims matter in {scope}?",
        f"Which existing software and Code Intelligence capabilities are used "
        f"for work in {scope}?",
    )


def _coverage_balanced_coordinates(spec: ContextSeedSpec, roles: tuple):
    """Yield every pattern/role/project/task coordinate exactly once.

    The iterator is a lazy permutation of the mixed-radix Cartesian space; it
    never constructs ``product(...)``.  Axes are ordered largest-first, then a
    triangular digit transform rotates each smaller axis by the digits already
    visited.  The transform is invertible, so coordinates cannot repeat.  It
    also gives the useful prefix property: when the requested limit is at least
    an axis's cardinality, every value on that axis appears before any value on
    that axis repeats.
    """
    axes = (tuple(CONTEXT_PATTERNS), tuple(roles),
            tuple(spec.project_types), tuple(spec.task_types))
    # Stable tie-breaking by the declared semantic order keeps identical inputs
    # byte-reproducible across Python versions.
    order = tuple(sorted(range(len(axes)),
                         key=lambda index: (-len(axes[index]), index)))
    ordered = tuple(axes[index] for index in order)
    sizes = tuple(len(axis) for axis in ordered)
    total = 1
    for size in sizes:
        total *= size

    for rank in range(total):
        remainder = rank
        digits = []
        for size in sizes:
            digits.append(remainder % size)
            remainder //= size

        selected = [None] * len(axes)
        prior_digit_sum = 0
        for position, original_index in enumerate(order):
            size = sizes[position]
            balanced_index = (digits[position] + prior_digit_sum) % size
            selected[original_index] = ordered[position][balanced_index]
            prior_digit_sum += digits[position]
        yield tuple(selected)


def build_context_candidates(spec: ContextSeedSpec, *,
                             roles: "tuple | None" = None,
                             limit: "int | None" = None) -> list:
    """Build a bounded, coverage-balanced candidate population lazily."""
    from ..core.store_serve import StoreRecord
    from ..core.facets import context_facets
    roles = tuple(roles or spec.job_roles)
    if (any(not str(role).strip() for role in roles)
            or len(roles) != len(set(roles))):
        raise ValueError("roles must be nonblank and unique")
    requested = spec.max_candidates if limit is None else max(0, int(limit))
    maximum = (requested if spec.max_candidates is None or requested is None
               else min(requested, spec.max_candidates))
    out = []
    for pattern, role, project, task in _coverage_balanced_coordinates(spec,
                                                                       roles):
        if maximum is not None and len(out) >= maximum:
            break
        text = pattern["text"].format(
            role=role, task=task, project=project,
            domain=spec.subdomain or spec.domain)
        identity = "|".join((spec.domain, role, project, task,
                             pattern["name"], text))
        digest = hashlib.sha256(identity.encode()).hexdigest()[:16]
        facets = context_facets(
            category="domain_seed",
            subcategory=pattern["name"],
            context_type=pattern["context_type"],
            role_family=_role_family(role),
            job_position=_slug(role), domain=spec.domain,
            project_type=_slug(project), task_type=_slug(task),
            workflow_stage="orientation",
            thinking_style=_THINKING_STYLE.get(
                pattern["name"], pattern["name"]),
            question_family=_QUESTION_FAMILY[pattern["name"]],
            speech_act=_SPEECH_ACT.get(pattern["name"], "ask"),
            polarity="adversarial" if pattern["name"] in (
                "avoidance", "failure_analysis", "adversarial_review")
            else "neutral",
            list_structure="ranked_list"
            if pattern["response_shape"] == "ranking"
            else "flat_list" if pattern["response_shape"] in (
                "list", "proposals") else "none",
            serialization_format="plain_text",
            response_shape=pattern["response_shape"],
            scope="domain", lifecycle="candidate",
            provenance="context_seed/v1")
        out.append(StoreRecord(
            f"context.seed.{digest}", "question"
            if pattern["context_type"] == "question" else "context",
            text,
            body={"role": "context_seed_candidate", "text": text,
                  "context_type": pattern["context_type"],
                  "job_title": role, "industry": spec.industry,
                  "domain": spec.domain,
                  "subdomain": spec.subdomain,
                  "project_type": project, "task_type": task,
                  "thinking_method": pattern["name"],
                  "answer_shape": pattern["response_shape"],
                  "geography": spec.geography,
                  "jurisdiction": spec.jurisdiction,
                  "time_horizon": spec.time_horizon,
                  "source_policy": spec.source_policy,
                  "source_refs": list(spec.source_refs),
                  "claim_status": "proposal",
                  "maturity": "candidate", "digest": digest,
                  "facets": facets},
            tags=("context_seed", _slug(spec.domain),
                  _slug(role), pattern["name"], "candidate"),
            tier="experimental", source="context_seed/v1"))
    return out


def _manifest(spec: ContextSeedSpec, candidates: list) -> dict:
    ids = [record.record_id for record in candidates]
    payload = {"domain": spec.domain, "source_policy": spec.source_policy,
               "source_refs": list(spec.source_refs), "record_ids": ids}
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {"schema": "context_seed_manifest/v1", "domain": spec.domain,
            "candidates": len(ids), "content_digest_sha256": digest,
            "maturity": "candidate", "installed": False,
            "promoted": False}


def run_context_seed(spec: ContextSeedSpec, *, existing_context_records=(),
                     ledger=None) -> ContextSeedRun:
    """Run domain seeding through one Starting Loop and one Loop per job role."""
    from ..loop.recursive_loop import Loop, LoopConfig, LoopLedger, StepOutcome
    from ..loop.loop_templates import TEMPLATE_LIBRARY, config_from_template
    from ..core.intelligence_layers import classified_record
    from .housekeeping import guard_improvement_action

    template = next(item for item in TEMPLATE_LIBRARY
                    if item["template_id"] == "context_intelligence_seed")
    base = config_from_template(template, power="deep", max_depth=2)
    config = LoopConfig(
        framework=base.framework, logical_kind=base.logical_kind,
        replay_guarantee=base.replay_guarantee,
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",), power=base.power,
        custom_steps=base.custom_steps, max_depth=base.max_depth,
        exit_condition=base.exit_condition)
    log = ledger or LoopLedger()
    root = Loop(f"seed Context Intelligence for {spec.domain}", config,
                ledger=log)
    existing = list(existing_context_records or ())
    existing_in_domain = 0
    for record in existing:
        classified = classified_record("context_intelligence", record)
        hierarchy = classified.body["classification"]["context_hierarchy"]
        if hierarchy.get("domain") == spec.domain:
            existing_in_domain += 1
    state = {"candidates": [], "coverage_before": existing_in_domain,
             "research_questions": list(domain_research_questions(spec)),
             "duplicates": 0, "verified": False}

    def handler(loop, step, context):
        if step == "scope_domain":
            return StepOutcome(
                output=f"domain={spec.domain}; source_policy={spec.source_policy}",
                mode="deterministic", confidence=0.95)
        if step == "audit_coverage":
            return StepOutcome(
                output=f"existing_domain_records={state['coverage_before']}",
                mode="deterministic", confidence=0.8)
        if step == "map_roles_and_work":
            return StepOutcome(
                output=f"roles={len(spec.job_roles)}; projects="
                       f"{len(spec.project_types)}; tasks={len(spec.task_types)}",
                mode="deterministic", confidence=0.95)
        if step == "define_research_questions":
            return StepOutcome(
                output=f"research_questions={len(state['research_questions'])}",
                mode="deterministic", confidence=0.95)
        if step == "generate_context":
            # Plan once across every declared axis so the global bound does not
            # make each role-specific spawned repeat the same pattern prefix.
            planned = build_context_candidates(spec)
            records_by_role = {role: [] for role in spec.job_roles}
            for record in planned:
                records_by_role[record.body["job_title"]].append(record)
            for role in spec.job_roles:
                role_records = records_by_role[role]
                if not role_records:
                    continue
                spawned_cfg = LoopConfig(
                    framework="custom", custom_steps=("generate_context",),
                    logical_kind="search_improvement",
                    allowable_modes=("deterministic",),
                    preferred_modes=("deterministic",), power="light",
                    max_depth=2)
                spawned = loop.spawn(f"generate Context candidates for {role}",
                                   spawned_cfg)

                def spawned_handler(_spawned, _step, _context, role=role,
                                  role_records=tuple(role_records)):
                    state["candidates"].extend(role_records)
                    return StepOutcome(output=f"generated={len(role_records)}",
                                       mode="deterministic", confidence=0.95)

                spawned.run(handler=spawned_handler)
            planned_order = {record.record_id: index
                             for index, record in enumerate(planned)}
            state["candidates"].sort(
                key=lambda record: planned_order[record.record_id])
            return StepOutcome(
                output=f"generated={len(state['candidates'])}",
                mode="deterministic", confidence=0.95)
        if step == "classify":
            state["candidates"] = [classified_record(
                "context_intelligence", record) for record in state["candidates"]]
            return StepOutcome(output=f"classified={len(state['candidates'])}",
                               mode="deterministic", confidence=0.95)
        if step == "deduplicate":
            unique = {}
            for record in state["candidates"]:
                unique.setdefault(record.record_id, record)
            state["duplicates"] = len(state["candidates"]) - len(unique)
            state["candidates"] = list(unique.values())
            return StepOutcome(output=f"deduplicated={state['duplicates']}",
                               mode="deterministic", confidence=0.95)
        if step == "verify":
            valid = all(
                record.tier == "experimental"
                and record.body["classification"]["public_key"]
                    == "context_intelligence"
                and record.body["classification"]["context_hierarchy"]
                    ["thinking_style"] != ""
                for record in state["candidates"])
            if not valid or not state["candidates"]:
                raise ValueError("Context seed candidate verification failed")
            state["verified"] = True
            return StepOutcome(output="candidate shapes verified",
                               mode="deterministic", confidence=0.98)
        if step == "stage":
            guard_improvement_action(
                "stage_candidate", logical_kind=loop.config.logical_kind)
            return StepOutcome(
                output="candidates prepared for an explicit candidate store",
                mode="deterministic", confidence=0.95)
        if step == "report":
            return StepOutcome(
                output=f"candidates={len(state['candidates'])}; promoted=0",
                mode="deterministic", confidence=0.95)
        return StepOutcome(output=f"{step}:done", mode="deterministic",
                           confidence=0.9)

    loop_result = root.run(handler=handler, max_steps=len(CONTEXT_SEED_STEPS) + 1)
    candidates = list(state["candidates"])
    return ContextSeedRun(
        spec=spec, candidates=tuple(candidates),
        research_questions=tuple(state["research_questions"]),
        manifest=_manifest(spec, candidates), loop_result=loop_result,
        ledger=log, coverage_before=state["coverage_before"])


def self_test() -> dict:
    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    spec = ContextSeedSpec(
        domain="space", industry="space economy",
        project_types=("earth observation mission", "launch system"),
        task_types=("mission risk review", "data product design"),
        job_roles=("orbital mechanics engineer", "mission operations lead",
                   "space policy researcher"),
        source_policy="official_first", max_candidates=30)
    first = run_context_seed(spec)
    second = run_context_seed(spec)
    first_ids = [record.record_id for record in first.candidates]
    second_ids = [record.record_id for record in second.candidates]
    full_spec = ContextSeedSpec(
        domain=spec.domain, industry=spec.industry,
        project_types=spec.project_types, task_types=spec.task_types,
        job_roles=spec.job_roles, source_policy=spec.source_policy,
        max_candidates=(len(CONTEXT_PATTERNS) * len(spec.job_roles)
                        * len(spec.project_types) * len(spec.task_types)))
    balanced = build_context_candidates(full_spec, limit=30)
    balanced_again = build_context_candidates(full_spec, limit=30)
    complete = build_context_candidates(
        full_spec, limit=full_spec.max_candidates)
    limited = build_context_candidates(full_spec, limit=7)
    empty = build_context_candidates(full_spec, limit=0)
    capped = build_context_candidates(spec, limit=full_spec.max_candidates)
    wide_spec = ContextSeedSpec(
        domain="wide-axis-test",
        job_roles=tuple(f"role {index}" for index in range(17)),
        project_types=tuple(f"project {index}" for index in range(15)),
        task_types=tuple(f"task {index}" for index in range(13)),
        max_candidates=30)
    wide = build_context_candidates(wide_spec)
    duplicate_axes_refused = 0
    for operation in (
            lambda: ContextSeedSpec(domain="x", job_roles=("same", "same")),
            lambda: build_context_candidates(full_spec,
                                             roles=("same", "same"))):
        try:
            operation()
        except ValueError:
            duplicate_axes_refused += 1
    check("domain_seed_runs_through_search_improvement_loops",
          first.loop_result.stopped == "done"
          and first.loop_result.model_calls == 0
          and any(event.get("event") == "spawn"
                  for event in first.ledger.events)
          and all(event.get("logical_kind") == "search_improvement"
                  for event in first.ledger.events
                  if event.get("event") == "init"))
    check("domain_seed_is_deterministic_and_manifest_bound",
          first_ids == second_ids
          and first.manifest["content_digest_sha256"]
          == second.manifest["content_digest_sha256"]
          and len(first_ids) == len(set(first_ids)) == 30)
    axes = (
        ("thinking_method", tuple(item["name"] for item in CONTEXT_PATTERNS)),
        ("job_title", spec.job_roles),
        ("project_type", spec.project_types),
        ("task_type", spec.task_types),
    )
    check("coverage_balanced_prefix_covers_each_feasible_axis_before_repeating",
          all(
              len({record.body[field]
                   for record in balanced[:len(expected)]}) == len(expected)
              and {record.body[field]
                   for record in balanced[:len(expected)]} == set(expected)
              for field, expected in axes),
          "the first N records cover all N values of each feasible axis")
    wide_axes = (
        ("thinking_method", tuple(item["name"] for item in CONTEXT_PATTERNS)),
        ("job_title", wide_spec.job_roles),
        ("project_type", wide_spec.project_types),
        ("task_type", wide_spec.task_types),
    )
    check("coverage_prefix_holds_when_a_non_pattern_axis_is_largest",
          all({record.body[field] for record in wide[:len(expected)]}
              == set(expected) for field, expected in wide_axes),
          "17 roles, 15 projects, 13 tasks, and 12 patterns all cover first")
    complete_coordinates = {
        (record.body["thinking_method"], record.body["job_title"],
         record.body["project_type"], record.body["task_type"])
        for record in complete}
    check("coverage_sampler_is_unique_deterministic_and_limit_bounded",
          [record.record_id for record in balanced]
          == [record.record_id for record in balanced_again]
          and len(complete) == len(complete_coordinates)
          == full_spec.max_candidates
          and len(limited) == 7 and not empty
          and len(capped) == spec.max_candidates
          and duplicate_axes_refused == 2,
          f"{len(complete)} unique full coordinates; limits 7 and "
          f"{spec.max_candidates} honored")
    hierarchies = [record.body["classification"]["context_hierarchy"]
                   for record in first.candidates]
    check("candidate_context_has_role_work_and_thinking_axes",
          {item["job_role"] for item in hierarchies}
          == set(spec.job_roles)
          and all(item["domain"] == "space" for item in hierarchies)
          and len({item["thinking_style"] for item in hierarchies}) >= 3
          and {record.body["thinking_method"] for record in first.candidates}
          == {item["name"] for item in CONTEXT_PATTERNS})
    check("research_questions_request_sources_without_inventing_people",
          any("people and organizations" in question
              for question in first.research_questions)
          and any("official standards" in question
                  for question in first.research_questions)
          and all(record.body.get("claim_status") == "proposal"
                  for record in first.candidates))
    from ..core.intelligence_layers import (
        IntelligenceSearchRequest, query_intelligence)
    hidden = query_intelligence(IntelligenceSearchRequest(
        "space mission risk", {"context": list(first.candidates)}))
    visible = query_intelligence(IntelligenceSearchRequest(
        "space mission risk", {"context_intelligence": list(first.candidates)},
        include_candidates=True))
    check("candidate_context_is_excluded_until_explicitly_requested",
          not hidden["hits"] and visible["hits"]
          and visible["hits"][0]["public_label"] == "Context Intelligence")
    from .housekeeping import guard_improvement_action, SafeguardError
    refused = False
    try:
        guard_improvement_action("promote", logical_kind="search_improvement")
    except SafeguardError:
        refused = True
    check("domain_seed_cannot_promote_its_own_candidates", refused)

    passed = sum(1 for result in results if result["passed"])
    return {"record_type": "context_seed_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
