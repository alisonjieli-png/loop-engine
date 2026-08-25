"""Facets — the search keys, blocking filters, and exclusion mechanisms.

The two primitives (Strings, Code Nodes) carry FACETS: typed classification
fields used by the capability directory to require, prefer, or exclude
candidates when searching by need.  An offline loop blocks ``api_calling``
nodes by facet, not by folder; a search may focus one job position's string
intelligence or blend several.

Closed vocabularies are validated fail-closed: an unknown value in a closed
field is refused at annotation time, never silently stored.  Matching is also
fail-closed: a record MISSING a required facet is ineligible — an unfaceted
record cannot satisfy a requirement by omission.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Code Node facet vocabularies (closed — validated).
# ---------------------------------------------------------------------------

#: what running the node entails (the loop's mode names, reused exactly)
EXECUTION_MODES = ("code_only", "hybrid", "model_led")

#: repeatability of its output
DETERMINISM = ("deterministic", "seeded", "stochastic")

#: WHERE the work happens — a first-class split of code intelligence:
#: runs on the home system | its body calls an external API | needs
#: provisioned external resources (a GPU box, a database, a queue).
LOCALITY = ("local_machine", "api_calling", "external_resources")

#: side effects (multi-valued; "pure" excludes the others)
EFFECTS = ("pure", "reads_fs", "writes_fs", "network", "spawns_process")

#: coarse cost band
COST_CLASSES = ("free", "cheap", "metered", "expensive")

CODE_FACET_FIELDS = ("execution_mode", "determinism", "locality", "effects",
                     "cost_class", "role", "lifecycle")

# ---------------------------------------------------------------------------
# Context facet vocabularies (category drill-down is open; positions are a
# known list PLUS any explicit custom position — a lens, not a gate).
# ---------------------------------------------------------------------------

KNOWN_JOB_POSITIONS = (
    "senior_data_scientist", "ml_engineer", "data_engineer", "statistician",
    "risk_officer", "domain_expert", "product_manager", "software_architect",
    "site_reliability_engineer", "security_engineer", "research_scientist",
)

ROLE_FAMILIES = (
    "leadership_product", "software_systems", "data_ai_statistics",
    "science_engineering", "health_safety", "operations_reliability",
    "risk_compliance", "research_review", "customer_domain", "other")

CONTEXT_FACET_FIELDS = (
    "category", "subcategory", "context_type", "role_family",
    "job_position", "seniority", "industry", "domain", "subdomain",
    "topic", "project_type", "task_type", "deliverable", "workflow_stage",
    "thinking_style", "response_shape", "geography", "jurisdiction",
    "time_horizon", "source_policy", "claim_status",
    "possible_code_target", "scope", "lifecycle", "provenance", "digest")

# Compatibility name for callers that still use the internal String asset
# vocabulary. The public layer name is Context Intelligence.
STRING_FACET_FIELDS = CONTEXT_FACET_FIELDS

_CLOSED = {"execution_mode": EXECUTION_MODES, "determinism": DETERMINISM,
           "locality": LOCALITY, "cost_class": COST_CLASSES}


def code_facets(*, execution_mode: str, determinism: str, locality: str,
                effects: tuple = ("pure",), cost_class: str = "free",
                role: str = "", lifecycle: str = "") -> dict:
    """Validated facet dict for a Code Node record (closed fields refused
    fail-closed)."""
    out = {"execution_mode": execution_mode, "determinism": determinism,
           "locality": locality, "effects": tuple(effects),
           "cost_class": cost_class, "role": role, "lifecycle": lifecycle}
    for f, vocab in _CLOSED.items():
        if out[f] and out[f] not in vocab:
            raise ValueError(f"{f}={out[f]!r} not in {vocab}")
    bad = [e for e in out["effects"] if e not in EFFECTS]
    if bad:
        raise ValueError(f"effects {bad} not in {EFFECTS}")
    if "pure" in out["effects"] and len(out["effects"]) > 1:
        raise ValueError("'pure' excludes every other effect")
    return out


def string_facets(*, category: str, subcategory: str = "",
                  job_position: str = "", scope: str = "",
                  lifecycle: str = "", provenance: str = "",
                  context_type: str = "", role_family: str = "",
                  seniority: str = "", industry: str = "", domain: str = "",
                  subdomain: str = "", topic: str = "",
                  project_type: str = "", task_type: str = "",
                  deliverable: str = "", workflow_stage: str = "",
                  thinking_style: str = "", response_shape: str = "",
                  geography: str = "", jurisdiction: str = "",
                  time_horizon: str = "", source_policy: str = "",
                  claim_status: str = "", possible_code_target: str = "",
                  digest: str = "") -> dict:
    """Facet dict for a Context record.

    The function keeps its compatibility name because existing persisted
    records use the String asset vocabulary. Public interfaces call the layer
    Context Intelligence. Open fields remain explicit instead of forcing every
    industry and job into a closed list.
    """
    return {"category": category, "subcategory": subcategory,
            "context_type": context_type,
            "role_family": role_family,
            "role_family_known": (role_family in ROLE_FAMILIES
                                  if role_family else True),
            "job_position": job_position,
            "job_position_known": (job_position in KNOWN_JOB_POSITIONS
                                   if job_position else True),
            "seniority": seniority, "industry": industry,
            "domain": domain, "subdomain": subdomain, "topic": topic,
            "project_type": project_type, "task_type": task_type,
            "deliverable": deliverable, "workflow_stage": workflow_stage,
            "thinking_style": thinking_style,
            "response_shape": response_shape,
            "geography": geography, "jurisdiction": jurisdiction,
            "time_horizon": time_horizon, "source_policy": source_policy,
            "claim_status": claim_status,
            "possible_code_target": possible_code_target,
            "scope": scope, "lifecycle": lifecycle,
            "provenance": provenance, "digest": digest}


def context_facets(**kwargs) -> dict:
    """Public-language alias for ``string_facets``."""
    return string_facets(**kwargs)


# ---------------------------------------------------------------------------
# Filtering: require (hard, fail-closed) / prefer (soft rank) / exclude (hard).
# ---------------------------------------------------------------------------

@dataclass
class FacetFilter:
    """One search-time facet constraint set.

    ``require``: every key must be PRESENT and match — a record missing the
    facet is ineligible.  ``exclude``: a present-and-matching facet makes the
    record ineligible (a missing facet does NOT exclude — exclusion needs
    evidence of the property).  ``prefer``: +1 rank per match, never a gate.
    Multi-valued facets (effects) match by membership.
    """
    require: dict = field(default_factory=dict)
    prefer: dict = field(default_factory=dict)
    exclude: dict = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not (self.require or self.prefer or self.exclude)


def _matches(facets: dict, key: str, wanted) -> "bool | None":
    """None = facet absent; True/False = present and (mis)matching."""
    if key not in facets or facets[key] in ("", (), None):
        return None
    have = facets[key]
    wanted_set = wanted if isinstance(wanted, (tuple, list, set)) else (wanted,)
    if isinstance(have, (tuple, list, set)):
        return any(w in have for w in wanted_set)
    return have in wanted_set


def facet_match(facets: dict, flt: FacetFilter) -> tuple:
    """(eligible, preference_score, reasons) for one record's facets."""
    reasons = []
    for k, v in flt.require.items():
        m = _matches(facets, k, v)
        if m is None:
            return False, 0, [f"required facet {k} absent (fail-closed)"]
        if not m:
            return False, 0, [f"required {k}={v} but record has {facets[k]!r}"]
        reasons.append(f"required {k} ok")
    for k, v in flt.exclude.items():
        if _matches(facets, k, v) is True:
            return False, 0, [f"excluded: {k} matches {v!r}"]
    score = 0
    for k, v in flt.prefer.items():
        if _matches(facets, k, v) is True:
            score += 1
            reasons.append(f"preferred {k} matched")
    return True, score, reasons


#: the canonical offline preset — blocks API-calling code and network effects
#: BY FACET, never by folder.
OFFLINE = FacetFilter(exclude={"locality": ("api_calling",
                                            "external_resources"),
                               "effects": "network"})


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    local = code_facets(execution_mode="code_only", determinism="deterministic",
                        locality="local_machine", effects=("pure",),
                        role="detect")
    api = code_facets(execution_mode="hybrid", determinism="stochastic",
                      locality="api_calling", effects=("network",),
                      cost_class="metered", role="execute")

    # 1. closed vocabularies refuse unknown values (fail-closed annotation).
    refused = False
    try:
        code_facets(execution_mode="code_only", determinism="deterministic",
                    locality="my_laptop")
    except ValueError:
        refused = True
    check("closed_vocabulary_refuses_unknown_locality", refused)

    # 2. 'pure' excludes other effects.
    refused = False
    try:
        code_facets(execution_mode="code_only", determinism="deterministic",
                    locality="local_machine", effects=("pure", "network"))
    except ValueError:
        refused = True
    check("pure_excludes_other_effects", refused)

    # 3. require locality=local_machine keeps local, drops api_calling.
    flt = FacetFilter(require={"locality": "local_machine"})
    check("require_locality_keeps_local", facet_match(local, flt)[0])
    check("require_locality_drops_api_calling", not facet_match(api, flt)[0])

    # 4. a record MISSING the required facet is ineligible (fail-closed).
    ok, _, why = facet_match({}, flt)
    check("missing_required_facet_is_ineligible", not ok and "fail-closed" in why[0])

    # 5. OFFLINE preset blocks api_calling and network BY FACET.
    check("offline_preset_blocks_api_calling_by_facet",
          not facet_match(api, OFFLINE)[0])
    check("offline_preset_keeps_local_pure_node", facet_match(local, OFFLINE)[0])

    # 6. exclusion needs evidence: a record with NO locality facet is not
    #    excluded by the exclude rule (but would fail a require).
    check("exclude_does_not_fire_on_absent_facet", facet_match({}, OFFLINE)[0])

    # 7. prefer is soft: mismatch never gates, match adds rank.
    pf = FacetFilter(prefer={"job_position": "senior_data_scientist"})
    s1 = string_facets(category="measurement", subcategory="generalization",
                       job_position="senior_data_scientist")
    s2 = string_facets(category="measurement")
    ok1, sc1, _ = facet_match(s1, pf)
    ok2, sc2, _ = facet_match(s2, pf)
    check("prefer_is_soft_and_ranks", ok1 and ok2 and sc1 == 1 and sc2 == 0)

    # 8. effects membership matching (multi-valued).
    wf = code_facets(execution_mode="code_only", determinism="deterministic",
                     locality="local_machine", effects=("reads_fs", "writes_fs"))
    check("effects_membership_matching",
          not facet_match(wf, FacetFilter(exclude={"effects": "writes_fs"}))[0]
          and facet_match(wf, FacetFilter(require={"effects": "reads_fs"}))[0])

    # 9. unknown job position allowed but flagged custom (lens, not gate).
    s3 = string_facets(category="ops", job_position="chief_vibes_officer")
    check("custom_job_position_allowed_but_flagged",
          s3["job_position_known"] is False)

    # 10. the Context hierarchy is searchable through the same filter grammar.
    cx = context_facets(
        category="domain_seed", context_type="question",
        role_family="science_engineering", job_position="mission_planner",
        domain="space", project_type="earth_observation",
        task_type="risk_review", workflow_stage="planning",
        thinking_style="first_principles", response_shape="decomposition",
        scope="domain", lifecycle="candidate", provenance="seed/v1")
    cflt = FacetFilter(require={"domain": "space",
                               "thinking_style": "first_principles"})
    check("context_hierarchy_fields_use_the_shared_filter_grammar",
          facet_match(cx, cflt)[0]
          and all(field in cx for field in CONTEXT_FACET_FIELDS))

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
