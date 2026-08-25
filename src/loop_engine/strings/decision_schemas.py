"""Decision schemas — prompt-side reasoning shapes that BIAS what the model
considers.  This is INTELLIGENCE, not truth.

CLEAR BOUNDARY (owner rule, 2026-08-23 — no blurred lines):

  * A ``DecisionSchema`` here is a BIAS.  Its required fields make the model
    CONSIDER things (why now, what's missing, a cheaper alternative) — a
    prompt-side nudge that shapes reasoning.  It never admits or rejects a result.
  * A ``runtime_contracts.ContractDefinition`` is TRUTH.  It ADMITS or REJECTS a
    produced result deterministically — types, enums, ranges, cardinality.  That
    is the ONLY validator with admission authority.

They may name the same fields, but their authority is different, and this module
must never encroach on admission.  So:

  * ``as_instruction`` renders the reasoning shape into the prompt (the bias).
  * ``check_engagement`` is a SOFT signal — did the model ENGAGE the required
    reasoning fields (so you know whether to re-prompt)?  It is NOT admission; a
    field answered "none, because ..." counts as engaged.
  * ``to_contract`` is the explicit BRIDGE: when a schema's shape must be
    ENFORCED rather than merely encouraged, it emits a runtime ContractDefinition
    — intelligence proposing a boundary that truth then owns.

Schemas are searchable store records; the typed learning records a call surfaces
are formalized in [[learning_bundle.py]]; admission lives in
[[runtime_contracts.py]].
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

# Where a schema's instruction sits in the 13-block prompt order.
PLACEMENTS = ("output_contract", "reasoning_considerations", "final_directive")


@dataclass(frozen=True)
class DecisionField:
    """One field in an output contract.  A REQUIRED field is the bias: the model
    must produce it, so it must think about it."""
    name: str
    required: bool = True
    kind: str = "text"                 # text | list | number | enum | bool
    bias_note: str = ""                # what considering this field forces
    enum: tuple = ()

    def describe(self) -> str:
        req = "required" if self.required else "optional"
        base = f'"{self.name}": <{self.kind}> ({req})'
        if self.enum:
            base += f" one of {list(self.enum)}"
        if self.bias_note:
            base += f"  # {self.bias_note}"
        return base


@dataclass(frozen=True)
class DecisionSchema:
    """A standardized output contract for one decision type."""
    name: str
    purpose: str
    fields: tuple
    placement: str = "output_contract"

    def __post_init__(self):
        if self.placement not in PLACEMENTS:
            raise ValueError(f"placement must be one of {PLACEMENTS}")

    def required_fields(self) -> tuple:
        return tuple(f.name for f in self.fields if f.required)

    def as_instruction(self) -> str:
        """The prompt-carried schema — the bias.  A compact JSON shape the model
        must return; required fields force the considerations."""
        lines = [f"Return a JSON object for '{self.name}' ({self.purpose}) with "
                 "these fields:"]
        for f in self.fields:
            lines.append("  " + f.describe())
        req = self.required_fields()
        if req:
            lines.append(f"All of {list(req)} are REQUIRED — you must fill each "
                         "one, even if the value is 'none' with a reason.")
        return "\n".join(lines)

    def check_engagement(self, obj: dict) -> dict:
        """SOFT prompt-effectiveness signal — did the model ENGAGE the required
        reasoning fields?  This is INTELLIGENCE, not truth: a field answered
        "none, because ..." counts as engaged (non-empty).  It tells you whether
        to re-prompt, NEVER whether the result is admissible — admission is the
        authority of ``runtime_contracts.ContractDefinition.validate``.  It does
        not check enum/type/range validity: those are TRUTH concerns owned by the
        contract, not the bias."""
        unaddressed = []
        for f in self.fields:
            if not f.required:
                continue
            if f.name not in obj or obj[f.name] in (None, "", [], {}):
                unaddressed.append(f.name)
        return {"record_type": "engagement_signal/v1",
                "engaged": not unaddressed, "unaddressed": unaddressed,
                "schema": self.name, "authority": "soft signal, not admission"}

    def to_contract(self, *, version: str = "1.0.0"):
        """The explicit BRIDGE intelligence → truth.  When this schema's shape
        must be ENFORCED (not merely encouraged), emit a runtime
        ContractDefinition — the decision schema biases the model; the contract
        admits the result.  Extra fields are allowed (a reasoning schema says
        what must be CONSIDERED, not that nothing else may appear)."""
        from ..code_nodes.runtime_contracts import ContractDefinition, FieldSpec
        _dt = {"number": "float", "bool": "bool", "enum": "string",
               "list": "any", "text": "string"}
        specs = tuple(
            FieldSpec(f.name, _dt.get(f.kind, "string"),
                      nullable=not f.required, allowed_values=tuple(f.enum))
            for f in self.fields)
        return ContractDefinition(f"from-schema.{self.name}", "object",
                                  version=version, fields=specs,
                                  additional_fields_allowed=True)


# ---------------------------------------------------------------------------
# The core schema library — bias-carrying decision contracts.
# ---------------------------------------------------------------------------

_NEXT_ACTION = DecisionSchema(
    "next_action",
    "choose the single most valuable next action",
    (DecisionField("action", bias_note="the one bounded next action"),
     DecisionField("why_now", bias_note="forces justification, not reflex"),
     DecisionField("missing_prerequisites", kind="list",
                   bias_note="forces checking what must exist first"),
     DecisionField("cheaper_alternative_considered",
                   bias_note="forces a reuse/deterministic check before spend"),
     DecisionField("expected_value", kind="number", required=False),
     DecisionField("confidence", kind="number",
                   bias_note="forces calibrated self-assessment"),
     DecisionField("abstain_reason", required=False,
                   bias_note="a first-class option, not a failure")))

_CONTEXT_COVERAGE = DecisionSchema(
    "context_coverage_decision",
    "decide whether we understand the problem well enough to proceed "
    "(research-first as a coverage decision, not a web-search reflex)",
    (DecisionField("coverage_verdict", kind="enum",
                   enum=("sufficient", "incomplete", "missing", "needs_research"),
                   bias_note="forces an explicit sufficiency judgement"),
     DecisionField("gaps", kind="list",
                   bias_note="names exactly what is missing"),
     DecisionField("chosen_action", kind="enum",
                   enum=("proceed_with_existing", "retrieve_and_combine",
                         "generate_provisional", "spawn_research",
                         "author_research_graph"),
                   bias_note="ties the verdict to one bounded next move"),
     DecisionField("justification")))

# Every open-ended call should also return this appendix — the reusable-learning
# surface.  The appendix itself is required; its inner lists may be empty.
_LEARNING_APPENDIX = DecisionSchema(
    "reusable_learning_appendix",
    "surface reusable intelligence produced as a side effect of this call",
    tuple(DecisionField(n, required=False, kind="list") for n in (
        "context_candidates", "knowledge_claims", "questions_worth_reusing",
        "keywords", "entities", "dates_and_events", "blueprint_items",
        "risks", "failure_patterns", "common_mistakes", "uncommon_mistakes",
        "best_practices", "alternative_strategies", "success_metrics",
        "evaluation_criteria", "heuristics", "logic_candidates",
        "node_opportunities", "subgraph_opportunities",
        "task_graph_opportunities", "specialist_model_opportunities",
        "tool_or_package_needs", "unresolved_items")),
    placement="output_contract")

_REVIEW = DecisionSchema(
    "result_review",
    "judge a produced result before it may update accepted state",
    (DecisionField("meets_contract", kind="bool",
                   bias_note="forces checking the actual acceptance contract"),
     DecisionField("degeneracy_check",
                   bias_note="constant/chance-level/empty/too-perfect?"),
     DecisionField("evidence_for", kind="list", required=False),
     DecisionField("evidence_against", kind="list",
                   bias_note="forces looking for disconfirming evidence"),
     DecisionField("reusable_learning", kind="list", required=False),
     DecisionField("verdict", kind="enum",
                   enum=("pass", "pass_with_notes", "degenerate", "fail"))))

SCHEMA_REGISTRY = {s.name: s for s in
                   (_NEXT_ACTION, _CONTEXT_COVERAGE, _LEARNING_APPENDIX, _REVIEW)}


def bias_schema(name: str) -> DecisionSchema:
    if name not in SCHEMA_REGISTRY:
        raise KeyError(f"no decision schema {name!r}; have "
                       f"{sorted(SCHEMA_REGISTRY)}")
    return SCHEMA_REGISTRY[name]


def schema_records() -> list:
    """Each decision schema as a searchable store record — a swappable resource."""
    from ..static_architecture.store_serve import StoreRecord
    recs = []
    for s in SCHEMA_REGISTRY.values():
        recs.append(StoreRecord(
            record_id=f"schema.{s.name}", kind="strategy",
            title=f"Decision schema: {s.purpose}",
            body={"required_fields": list(s.required_fields()),
                  "placement": s.placement,
                  "instruction": s.as_instruction()},
            tags=("decision_schema", "schema_as_bias", s.name,
                  "step:decide_next"), tier="core"))
    return recs


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    na = bias_schema("next_action")

    # 1. the schema's required fields ARE the bias (they force consideration).
    req = na.required_fields()
    check("required_fields_force_consideration",
          "why_now" in req and "missing_prerequisites" in req
          and "cheaper_alternative_considered" in req,
          f"required: {req}")

    # 2. as_instruction renders the prompt-carried schema (the bias mechanism).
    instr = na.as_instruction()
    check("as_instruction_renders_the_prompt_carried_schema",
          "missing_prerequisites" in instr and "REQUIRED" in instr,
          "the required JSON shape rides the prompt")

    # 3. check_engagement is a SOFT bias signal (not admission): a stubbed
    # required field is flagged as unaddressed so you re-prompt.
    good = na.check_engagement({"action": "profile the data", "why_now": "no "
        "profile yet", "missing_prerequisites": ["none: data is loaded"],
        "cheaper_alternative_considered": "reuse search found nothing",
        "confidence": 0.6})
    bad = na.check_engagement({"action": "train a model", "why_now": "",
        "missing_prerequisites": [], "cheaper_alternative_considered": "x",
        "confidence": 0.9})
    check("engagement_is_a_soft_signal_not_admission",
          good["engaged"] and not bad["engaged"]
          and "why_now" in bad["unaddressed"]
          and bad["authority"].startswith("soft"),
          f"unaddressed: {bad['unaddressed']}")

    # 4. THE BOUNDARY: enum VALIDITY is truth, not a bias. Engagement passes a
    # filled-but-invalid enum; the BRIDGED runtime contract rejects it.
    cc = bias_schema("context_coverage_decision")
    filled = {"coverage_verdict": "vibes", "gaps": ["sources"],
              "chosen_action": "spawn_research", "justification": "x"}
    eng = cc.check_engagement(filled)          # intelligence: all fields filled
    adm = cc.to_contract().validate(filled)    # truth: 'vibes' not in the enum
    check("enum_validity_is_truth_owned_by_the_contract_not_the_bias",
          eng["engaged"] and not adm.valid
          and any(v.kind == "invalid_enum_value" for v in adm.violations),
          "engagement passes the filled field; the runtime contract rejects the "
          "invalid enum — clean separation of bias vs admission")

    # 5. the reusable-learning appendix schema carries the full taxonomy.
    la = bias_schema("reusable_learning_appendix")
    names = {f.name for f in la.fields}
    check("learning_appendix_carries_the_full_taxonomy",
          {"failure_patterns", "best_practices", "logic_candidates",
           "subgraph_opportunities", "specialist_model_opportunities"} <= names,
          f"{len(names)} appendix fields")

    # 6. schemas are searchable resources.
    from ..static_architecture.store_serve import SolverStore
    store = SolverStore(core_records=schema_records())
    hit = store.search("what should the next action be why now prerequisites",
                       kind="strategy")
    check("decision_schemas_are_searchable_resources",
          hit["hits"] and any("schema.next_action" == h["record_id"]
                              for h in hit["hits"]),
          "a decision schema is findable through the one search DAG")

    # 7. unknown schema raises.
    bad2 = False
    try:
        bias_schema("nope")
    except KeyError:
        bad2 = True
    check("unknown_schema_raises", bad2, "the registry is closed")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "decision_schemas_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
