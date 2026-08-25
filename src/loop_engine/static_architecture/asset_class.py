"""Asset class — the whole system has exactly TWO primitives.

Owner classification (2026-08-23): this is not about "contracts" or six
categories.  Literally every resource, asset, node, and text is one of two things:

  * STRING — for the LLM to READ.  Soft; interpreted; may be uncertain; costs
    tokens.  (intelligence, questions, personas, considerations, warnings, schema
    instructions, knowledge stated as text, blueprint fragments.)
  * CODE NODE — for the machine to RUN.  Exact; deterministic; zero model tokens.
    And a code node CAN READ STRINGS when it needs to (a string is a valid input
    to a code node).  Everything runnable is a code node: a runtime contract is a
    code node that VALIDATES, a logic rule is a code node that DECIDES, an adapter
    is a code node that TRANSFORMS, a capability is a code node that EXECUTES, a
    detector is a code node that DETECTS.  "Contract / logic / capability" are not
    categories — they are ROLES a code node plays (see ``CODE_NODE_ROLES``).

The insight that makes this the top classification: the SAME need can be met by
EITHER primitive.  "Based on this data, are these variables collinear?" can be a
STRING (ask an LLM) or a CODE NODE (a VIF node) — same question, two
implementations.  So an asset's class is about HOW it is implemented, and the
practitioner picks the primitive.

The North Star is the arrow between them: STRING → CODE NODE.  A model's string
reasoning, once it recurs and is verified, DISTILLS into a deterministic code node,
so the next run answers the same question with zero tokens.  A code node never
de-distills into a string.  This module owns the two primitives, the closed
kind→primitive map, the code-node ROLES, the two-way implementation choice (prefer
the exact zero-token code node when one exists), and the distillation direction.
It is a LENS over what already exists (intelligence_strings, logic_ast,
runtime_contracts, store nodes …), not a new store.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

# The two primitives.  The token "code" denotes a CODE NODE.
ASSET_CLASSES = ("string", "code")
ASSET_CLASS_MEANING = {
    "string": "a STRING — read by an LLM; soft, interpreted, costs tokens, "
              "may be uncertain",
    "code": "a CODE NODE — run by the machine; exact, deterministic, zero model "
            "tokens; may READ strings as input",
}

# The ROLES a code node can play.  These are what used to be miscalled
# "categories" (contract / logic / capability) — they are roles, not primitives.
CODE_NODE_ROLES = ("validate", "decide", "execute", "adapt", "transform",
                   "detect", "route", "score", "search")

# The CLOSED kind → class map covering every asset kind in the system.
KIND_CLASS = {
    # --- STRING (an LLM reads it) ------------------------------------------
    "string": "string", "persona": "string", "framing": "string",
    "prompt_prefix": "string", "prompt_suffix": "string",
    "consideration": "string", "warning": "string", "analogy": "string",
    "keyword": "string", "list_item": "string", "instruction": "string",
    "question": "string", "question_pattern": "string",
    "decision_schema": "string", "output_template": "string",
    "blueprint_fragment": "string", "best_practice": "string",
    "heuristic": "string", "knowledge_claim": "string",
    "failure_pattern": "string", "context": "string", "note": "string",
    "metric_definition": "string", "authority": "string",
    # --- CODE (the machine runs it) ----------------------------------------
    "logic_rule": "code", "logic_candidate": "code", "contract": "code",
    "validator": "code", "adapter": "code", "node": "code",
    "deterministic_node": "code", "node_candidate": "code",
    "loop": "code", "loop_candidate": "code",
    "capability": "code", "task_graph": "code", "task_graph_candidate": "code",
    "subgraph": "code", "subgraph_candidate": "code",
    "degeneracy_detector": "code", "shortcut": "code", "metric_reader": "code",
    "router_model": "code", "specialist_model": "code", "ensemble": "code",
    "executor": "code",
}


def classify(kind: str) -> str:
    """Which primitive an asset kind is — 'string' or 'code' (a code node).  The
    map is CLOSED: an unknown kind raises rather than being guessed."""
    if kind not in KIND_CLASS:
        raise ValueError(f"unknown asset kind {kind!r}; the String/Code-node map "
                         f"is closed — classify it explicitly in KIND_CLASS")
    return KIND_CLASS[kind]


# The role each CODE-NODE kind plays (what used to be miscalled "categories").
KIND_ROLE = {
    "contract": "validate", "validator": "validate",
    "logic_rule": "decide", "logic_candidate": "decide",
    "adapter": "adapt", "degeneracy_detector": "detect",
    "metric_reader": "score", "router_model": "route",
    "node": "execute", "deterministic_node": "execute", "node_candidate": "execute",
    "capability": "execute", "task_graph": "execute",
    "task_graph_candidate": "execute", "subgraph": "execute",
    "subgraph_candidate": "execute", "executor": "execute",
    "specialist_model": "execute", "ensemble": "execute", "shortcut": "execute",
}


def node_role(kind: str) -> str:
    """The role a code-node kind plays.  Raises if the kind isn't a code node —
    a string has no node role."""
    if classify(kind) != "code":
        raise ValueError(f"{kind!r} is a string, not a code node — it has no role")
    return KIND_ROLE.get(kind, "execute")


@dataclass(frozen=True)
class CodeNode:
    """A runnable code node.  It plays one ROLE and may READ strings as input —
    the classification stays binary: the node is code, the strings it reads are
    strings."""
    node_id: str
    role: str = "execute"
    reads_strings: tuple = ()           # string inputs it consumes, if any
    exact: bool = True

    def __post_init__(self):
        if self.role not in CODE_NODE_ROLES:
            raise ValueError(f"role must be one of {CODE_NODE_ROLES}")


# ---------------------------------------------------------------------------
# The two-rail implementation choice — the collinearity example, generalized.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CapabilityImpl:
    """One way to satisfy a capability need — on the string rail or the code
    rail."""
    impl_class: str                     # "string" | "code"
    handle: str                         # the prompt/string OR the code node id
    exact: bool = False                 # code is exact; a string ask may be wrong
    token_cost: str = "tokens"          # "tokens" (string) | "zero_model" (code)

    def __post_init__(self):
        if self.impl_class not in ASSET_CLASSES:
            raise ValueError(f"impl_class must be one of {ASSET_CLASSES}")


def impl_options(need: str, *, string_handle: str = "",
                 code_handle: str = "") -> list:
    """The rails available for a need.  Either or both may be present — e.g. the
    collinearity check has a string ask AND a code (VIF) node."""
    opts = []
    if code_handle:
        opts.append(CapabilityImpl("code", code_handle, exact=True,
                                   token_cost="zero_model"))
    if string_handle:
        opts.append(CapabilityImpl("string", string_handle, exact=False,
                                   token_cost="tokens"))
    return opts


def choose_impl(options: Sequence, *, prefer: str = "code") -> "CapabilityImpl | None":
    """Pick the rail.  Default prefers CODE when an exact code impl exists
    (zero-token, exact — the zero-model-first / reuse-before-rewriting doctrine),
    falling back to the STRING rail only when no code answers the need."""
    if not options:
        return None
    if prefer == "code":
        code = [o for o in options if o.impl_class == "code"]
        if code:
            return code[0]
    if prefer == "string":
        s = [o for o in options if o.impl_class == "string"]
        if s:
            return s[0]
    return options[0]


# ---------------------------------------------------------------------------
# The distillation arrow — STRING → CODE (the only direction).
# ---------------------------------------------------------------------------

# When a recurring, verified string kind can become a deterministic code kind.
_DISTILL_TO_CODE = {
    "consideration": "logic_rule", "heuristic": "logic_rule",
    "warning": "logic_rule", "question": "deterministic_node",
    "instruction": "logic_rule", "best_practice": "logic_rule",
    "knowledge_claim": "node",              # a fact -> a lookup node
    "metric_definition": "metric_reader",
}


def can_distill(kind: str) -> bool:
    """Is this a STRING asset whose recurring, verified reasoning can become
    CODE?  (Code never distills to a string — the arrow is one-way.)"""
    return classify(kind) == "string" and kind in _DISTILL_TO_CODE


def distill_target(kind: str) -> str:
    """The CODE kind a distillable string kind becomes.  Raises if it isn't a
    distillable string."""
    if not can_distill(kind):
        raise ValueError(f"{kind!r} is not a distillable string asset")
    return _DISTILL_TO_CODE[kind]


# Tag markers that settle a record's rail when its body kind is ambiguous.
_CODE_TAGS = {"runtime_contract", "executable_truth", "logic_rule",
              "deterministic_node", "follow_up_policy", "failure_response",
              "scheduler_bias"}
_STRING_TAGS = {"intelligence_string", "decision_schema", "schema_as_bias",
                "output_template", "reusability", "scaffolding", "bias_checklist",
                "knowledge", "solution_shaping", "measurement", "shaping"}


def classify_record(rec) -> str:
    """Classify ANY resource record — a StoreRecord or a dict — as string or code.
    This is what makes the binary UNIVERSAL: literally every resource, asset,
    node, and text lands on exactly one rail.  Tag- and body-driven, with the
    store kind as the last-resort fallback."""
    def g(name, default=None):
        return (rec.get(name, default) if isinstance(rec, dict)
                else getattr(rec, name, default))
    body = g("body") or {}
    tags = set(g("tags") or ())
    kind = g("kind")
    # 1. an explicit asset kind in the body wins (most precise).
    for key in ("string_kind", "candidate_type", "logic_kind", "kind"):
        v = body.get(key)
        if isinstance(v, str):
            v2 = _alias(v)
            if v2 in KIND_CLASS:
                return KIND_CLASS[v2]
    if "output_type" in body:              # a runtime contract
        return "code"
    # 2. unambiguous tag markers.
    if tags & _CODE_TAGS:
        return "code"
    if tags & _STRING_TAGS:
        return "string"
    # 3. store-kind fallback (STORE_KINDS = node/question/persona/context/strategy).
    if kind in ("question", "persona", "context"):
        return "string"
    if kind == "node":
        return "string" if "knowledge" in tags else "code"
    if kind == "strategy":
        return "code" if (tags & {"logic", "follow_up_policy"}) else "string"
    return "string"                        # default: text an LLM reads


def asset_split(kinds: Sequence[str]) -> dict:
    """Classify a mixed set of asset kinds into the two rails, and report how
    many strings could still be distilled to code (remaining token savings)."""
    strings = [k for k in kinds if classify(k) == "string"]
    code = [k for k in kinds if classify(k) == "code"]
    distillable = [k for k in strings if can_distill(k)]
    return {"record_type": "asset_split/v1",
            "string": strings, "code": code,
            "n_string": len(strings), "n_code": len(code),
            "distillable_to_code": distillable,
            "share_code": round(len(code) / max(1, len(kinds)), 3)}


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. the binary covers every asset kind in the system (nothing unclassified).
    from ..strings.intelligence_strings import STRING_KINDS
    from ..code_nodes.learning_bundle import CANDIDATE_TYPES
    covered, uncovered = 0, []
    for k in set(STRING_KINDS) | set(CANDIDATE_TYPES) | set(KIND_CLASS):
        try:
            classify(k if k in KIND_CLASS else _alias(k))
            covered += 1
        except ValueError:
            uncovered.append(k)
    check("the_binary_covers_every_asset_kind",
          not uncovered,
          f"{covered} kinds classified; unclassified: {uncovered}")

    # 2. both rails are represented and mean what they should.
    check("two_rails_string_and_code",
          classify("consideration") == "string"
          and classify("logic_rule") == "code"
          and "tokens" in ASSET_CLASS_MEANING["string"]
          and "zero" in ASSET_CLASS_MEANING["code"],
          "intelligence is string; a logic rule is code")

    # 3. THE KEY DUALITY: the same need, two rails (collinearity).
    opts = impl_options(
        "are these variables collinear?",
        string_handle="Ask: based on this data, are these variables collinear?",
        code_handle="node.stats.vif_check")
    classes = {o.impl_class for o in opts}
    check("same_need_can_be_string_or_code",
          classes == {"string", "code"} and len(opts) == 2,
          "the collinearity question has an LLM ask AND a VIF node")

    # 4. the rail choice prefers exact zero-token CODE when it exists.
    chosen = choose_impl(opts, prefer="code")
    only_string = choose_impl(impl_options(
        "explain the business context", string_handle="Ask for context"))
    check("choose_prefers_code_then_falls_to_string",
          chosen.impl_class == "code" and chosen.token_cost == "zero_model"
          and only_string.impl_class == "string",
          "code wins when present (zero-token, exact); else the string rail")

    # 5. distillation is one-way: STRING → CODE only.
    check("distillation_is_string_to_code_only",
          can_distill("consideration")
          and distill_target("consideration") == "logic_rule"
          and not can_distill("logic_rule"),
          "a recurring consideration can become a logic rule; code never reverts")

    # 6. unknown kind raises (the map is closed).
    bad = False
    try:
        classify("vibes")
    except ValueError:
        bad = True
    check("unknown_kind_raises_closed_map", bad, "no asset escapes the binary")

    # 7. asset_split reports the string/code balance + remaining distillables.
    split = asset_split(["consideration", "warning", "logic_rule", "contract",
                         "node", "question"])
    check("asset_split_reports_the_balance",
          split["n_string"] == 3 and split["n_code"] == 3
          and "consideration" in split["distillable_to_code"]
          and 0.0 <= split["share_code"] <= 1.0,
          f"{split['n_string']} string / {split['n_code']} code; "
          f"distillable: {split['distillable_to_code']}")

    # 8. UNIVERSAL: every resource RECORD lands on a rail (string or code).
    from ..strings.intelligence_strings import IntelligenceString
    from ..code_nodes.runtime_contracts import ContractDefinition, ContractRegistry
    from ..code_nodes.logic_ast import LogicRule, rule_record
    from ..strings.decision_schemas import schema_records
    from ..strings.output_templates import template_records
    from ..code_nodes.follow_up import policy_records
    reg = ContractRegistry()
    reg.register(ContractDefinition("c", "enum", allowed_values=("a", "b")))
    recs = ([IntelligenceString("consideration", "x").envelope()]
            + reg.records()
            + [rule_record(LogicRule("l", "t", "check",
                                     condition={"op": "exists", "field": "x"}))]
            + schema_records() + template_records() + policy_records())
    classes = {classify_record(r) for r in recs}
    spot = (classify_record(IntelligenceString("consideration", "x").envelope())
            == "string"
            and classify_record(reg.records()[0]) == "code"
            and classify_record(schema_records()[0]) == "string"
            and classify_record(template_records()[0]) == "string"
            and classify_record(policy_records()[0]) == "code")
    check("every_resource_record_lands_on_a_rail",
          classes <= {"string", "code"} and spot,
          "intelligence/schemas/templates -> string; contracts/logic/policies -> "
          "code; nothing unclassified")

    # 9. code nodes have ROLES (contract=validate, logic=decide, capability=
    # execute) and CAN READ STRINGS — "contract / logic / capability" are roles,
    # not separate primitives; a string has no node role.
    roles_ok = (node_role("contract") == "validate"
                and node_role("logic_rule") == "decide"
                and node_role("node") == "execute"
                and node_role("adapter") == "adapt")
    reads = CodeNode("n.collinear", role="decide",
                     reads_strings=("the question phrasing",))
    string_has_no_role = False
    try:
        node_role("consideration")
    except ValueError:
        string_has_no_role = True
    check("code_nodes_have_roles_and_can_read_strings",
          roles_ok and reads.reads_strings and string_has_no_role,
          "contract=validate, logic=decide, capability=execute; a code node may "
          "read strings; a string has no node role")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "asset_class_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


def _alias(kind: str) -> str:
    """Map a couple of learning-bundle candidate types onto their asset kind so
    the coverage check stays honest."""
    return {"common_mistake": "failure_pattern", "uncommon_mistake": "failure_pattern",
            "risk_resource": "warning", "context_resource": "context",
            "question_resource": "question", "prompt_resource": "instruction",
            "keyword_resource": "keyword", "entity_resource": "knowledge_claim",
            "date_or_event_resource": "knowledge_claim",
            "evaluation_criterion": "instruction", "research_need": "note",
            "tool_need": "note", "package_need": "note",
            "specialist_model_candidate": "specialist_model",
            "ensemble_candidate": "ensemble"}.get(kind, kind)
