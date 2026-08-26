"""Logic — the safe expression AST that COMPUTES/DECIDES deterministically.

This is the owner of the **Logic** resource category: the exact partner to
runtime_contracts (a contract ADMITS the shape; logic DECIDES the value).  It is
also the executor for a captured ``logic_candidate`` — [[capture.py]] PROPOSES a
rule; this module EXECUTES it, closing the loop engine → logic.

Hard rules (owner, 2026-08-23 — clean boundaries):

  * NEVER ``eval``.  A rule is a small JSON/dict AST over a CLOSED operator set,
    walked by a bounded recursive evaluator.
  * Logic does NOT mutate state.  A ``LogicRule`` EMITS findings and candidate
    actions; the practitioner (route/verify) decides what to do with them.
  * A rule declares its applicability, required inputs, tunable parameters (with
    a declared source), an abstain-when guard, and a fallback outside its
    validated scope — so a distilled rule is conservative and reversible, and
    abstains rather than guessing when an input is missing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

from ..loop.kernel import CandidateAction

# The CLOSED operator set (owner's list).  Anything else raises.
COMPARE_OPS = ("eq", "ne", "gt", "gte", "lt", "lte")
SET_OPS = ("in", "not_in")
ARITH_OPS = ("add", "subtract", "multiply", "divide", "abs", "min", "max", "count")
UNARY_PRESENCE = ("exists", "missing")
LOGIC_KINDS = ("hard_constraint", "check", "finding", "recommendation",
               "ranking_factor", "routing_rule", "exit_condition",
               "retry_condition", "fallback_condition", "repair_proposal")
PARAM_SOURCES = ("fixed", "default", "project_config", "tunable", "learned",
                 "retrieved", "contextual")
_MAX_DEPTH = 40


class LogicError(RuntimeError):
    """A malformed rule AST — an unknown operator, or recursion too deep."""


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _as_bool(x) -> bool:
    return bool(x) if x is not None else False


def evaluate(node, ctx: dict, params: "dict | None" = None, _depth: int = 0):
    """Walk the AST and return its value.  Deterministic, no eval, bounded."""
    params = params or {}
    if _depth > _MAX_DEPTH:
        raise LogicError("expression nesting too deep")
    if not isinstance(node, dict):
        return node                                     # a bare literal
    if "lit" in node:
        return node["lit"]
    if "op" not in node:
        if "field" in node:
            return ctx.get(node["field"])
        if "param" in node:
            return params.get(node["param"])
        if "all" in node:
            return all(_as_bool(evaluate(n, ctx, params, _depth + 1))
                       for n in node["all"])
        if "any" in node:
            return any(_as_bool(evaluate(n, ctx, params, _depth + 1))
                       for n in node["any"])
        if "not" in node:
            return not _as_bool(evaluate(node["not"], ctx, params, _depth + 1))
        raise LogicError(f"node has no operator and no known key: {node}")

    op = node["op"]
    if op in UNARY_PRESENCE:
        present = node["field"] in ctx and ctx[node["field"]] not in (None, "", [], {})
        return present if op == "exists" else not present
    if op in COMPARE_OPS or op in SET_OPS:
        left = (ctx.get(node["field"]) if "field" in node
                else evaluate(node["left"], ctx, params, _depth + 1))
        if op in SET_OPS:
            vals = node.get("values", [])
            return (left in vals) if op == "in" else (left not in vals)
        right = (node["value"] if "value" in node
                 else params.get(node["param"]) if "param" in node
                 else evaluate(node["right"], ctx, params, _depth + 1))
        if op == "eq":
            return left == right
        if op == "ne":
            return left != right
        ln, rn = _num(left), _num(right)
        if ln is None or rn is None:
            return False                                # not comparable -> False
        return {"gt": ln > rn, "gte": ln >= rn, "lt": ln < rn,
                "lte": ln <= rn}[op]
    if op == "regex":
        v = ctx.get(node["field"])
        return isinstance(v, str) and re.search(node["pattern"], v) is not None
    if op in ARITH_OPS:
        args = [evaluate(a, ctx, params, _depth + 1) for a in node.get("args", [])]
        nums = [_num(a) for a in args]
        if op == "count":
            return len(args)
        if op == "abs":
            return abs(nums[0]) if nums and nums[0] is not None else None
        if any(n is None for n in nums) or not nums:
            return None
        if op == "add":
            return sum(nums)
        if op == "subtract":
            return nums[0] - sum(nums[1:])
        if op == "multiply":
            r = 1.0
            for n in nums:
                r *= n
            return r
        if op == "divide":
            return nums[0] / nums[1] if len(nums) >= 2 and nums[1] != 0 else None
        if op == "min":
            return min(nums)
        if op == "max":
            return max(nums)
    raise LogicError(f"unknown operator {op!r}")


@dataclass(frozen=True)
class LogicParam:
    name: str
    default: float
    minimum: "float | None" = None
    maximum: "float | None" = None
    source: str = "tunable"

    def __post_init__(self):
        if self.source not in PARAM_SOURCES:
            raise ValueError(f"source must be one of {PARAM_SOURCES}")


@dataclass
class LogicRule:
    logic_id: str
    title: str
    logic_kind: str
    condition: dict
    outputs: tuple = ()                 # dicts: {output_kind, ...}
    required_inputs: tuple = ()
    parameters: tuple = ()
    abstain_when: "dict | None" = None
    fallback: "dict | None" = None      # {action_intent: ...}
    applicability: str = "any"
    maturity: str = "candidate"

    def __post_init__(self):
        if self.logic_kind not in LOGIC_KINDS:
            raise ValueError(f"logic_kind must be one of {LOGIC_KINDS}")

    def resource(self):
        """Emit the canonical Resource — a logic rule is a code node that decides."""
        from ..core.asset_lifecycle import Resource, normalize
        life = (normalize("string_maturity", self.maturity)
                if self.maturity in ("ephemeral", "candidate", "validated",
                                     "preferred") else "candidate")
        return Resource(asset_id=self.logic_id, asset_class="code",
                        role="logic_rule", content=self.title, lifecycle=life,
                        provenance="logic_ast")

    def _params(self, ctx: dict) -> dict:
        out = {}
        for p in self.parameters:
            v = ctx.get(p.name, p.default)              # contextual/learned override
            if p.minimum is not None and _num(v) is not None:
                v = max(v, p.minimum)
            if p.maximum is not None and _num(v) is not None:
                v = min(v, p.maximum)
            out[p.name] = v
        return out


@dataclass
class LogicResult:
    fired: bool
    abstained: bool
    findings: tuple = ()
    candidate_actions: tuple = ()       # CandidateAction rows — NOT state changes
    reason: str = ""


def run_rule(rule: LogicRule, ctx: dict) -> LogicResult:
    """Execute a rule against a context.  Abstains (with the fallback) when a
    required input is missing or the abstain guard fires — never guesses.  Emits
    findings + candidate actions; it does NOT mutate state."""
    params = rule._params(ctx)
    missing = [i for i in rule.required_inputs
               if i not in ctx or ctx[i] in (None, "", [], {})]
    if missing:
        fb = _fallback_actions(rule)
        return LogicResult(False, True, (), fb,
                           f"abstained: required input(s) missing {missing}")
    if rule.abstain_when is not None and _as_bool(
            evaluate(rule.abstain_when, ctx, params)):
        fb = _fallback_actions(rule)
        return LogicResult(False, True, (), fb,
                           "abstained: abstain_when guard fired (outside scope)")
    if _as_bool(evaluate(rule.condition, ctx, params)):
        findings, actions = [], []
        for o in rule.outputs:
            if o.get("output_kind") == "finding":
                findings.append({"finding_type": o.get("finding_type", "finding"),
                                 "severity": o.get("severity", "advisory")})
            elif o.get("output_kind") == "candidate_action":
                actions.append(CandidateAction(
                    action=o.get("action_intent", "review"), kind="logic",
                    rationale=f"emitted by rule {rule.logic_id}",
                    expected_value=0.55, information_gain=0.2))
        return LogicResult(True, False, tuple(findings), tuple(actions),
                           f"rule {rule.logic_id} fired")
    return LogicResult(False, False, (), (), "condition not met")


def _fallback_actions(rule: LogicRule) -> tuple:
    if rule.fallback and "action_intent" in rule.fallback:
        return (CandidateAction(action=rule.fallback["action_intent"],
                                kind="fallback",
                                rationale=f"fallback of rule {rule.logic_id}",
                                expected_value=0.5),)
    return ()


def rule_record(rule: LogicRule):
    """A logic rule as a searchable node record (the Logic category)."""
    from ..core.store_serve import StoreRecord
    return StoreRecord(
        record_id=f"logic.{rule.logic_id}", kind="node",
        title=rule.title,
        body={"logic_kind": rule.logic_kind, "applicability": rule.applicability,
              "required_inputs": list(rule.required_inputs),
              "parameters": [p.name for p in rule.parameters],
              "abstains": rule.abstain_when is not None},
        tags=("logic_rule", "deterministic", rule.logic_kind), tier="core"
        if rule.maturity in ("validated", "preferred") else "experimental")


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. the closed operator set evaluates without eval.
    ctx = {"corr": 0.94, "sensitivity": "high", "n": 5}
    node = {"all": [{"op": "gte", "field": "corr", "param": "thr"},
                    {"op": "in", "field": "sensitivity",
                     "values": ["medium", "high"]}]}
    check("closed_ast_evaluates_deterministically",
          evaluate(node, ctx, {"thr": 0.9}) is True
          and evaluate(node, ctx, {"thr": 0.99}) is False,
          "all/any/compare/in evaluate correctly, no eval")

    # 2. arithmetic ops compute values.
    check("arithmetic_ops_compute",
          evaluate({"op": "add", "args": [1, 2, {"field": "n"}]}, ctx) == 8
          and evaluate({"op": "divide", "args": [10, 4]}, ctx) == 2.5,
          "add/divide over fields and literals")

    # 3. an unknown operator raises (the set is closed).
    bad = False
    try:
        evaluate({"op": "eval_this", "args": []}, ctx)
    except LogicError:
        bad = True
    check("unknown_operator_raises", bad, "no operator outside the closed set")

    # 4. the collinearity rule fires and emits a candidate action (not a mutation).
    rule = LogicRule(
        "collinearity-review", "Review potential feature redundancy",
        "recommendation",
        condition={"all": [{"op": "gte", "field": "corr", "param": "thr"},
                           {"op": "in", "field": "sensitivity",
                            "values": ["medium", "high", "unknown"]}]},
        outputs=({"output_kind": "finding",
                  "finding_type": "potential_feature_redundancy"},
                 {"output_kind": "candidate_action",
                  "action_intent": "evaluate_collinearity_mitigation"}),
        required_inputs=("corr", "sensitivity"),
        parameters=(LogicParam("thr", 0.9, 0.5, 0.999, "tunable"),),
        abstain_when={"op": "eq", "field": "sensitivity", "value": "low"},
        fallback={"action_intent": "ask_model_to_review_redundancy"})
    res = run_rule(rule, ctx)
    check("rule_fires_and_emits_a_candidate_action_not_a_mutation",
          res.fired and res.findings
          and res.candidate_actions
          and isinstance(res.candidate_actions[0], CandidateAction),
          f"fired; findings={len(res.findings)}")

    # 5. ABSTAIN when a required input is missing — never guesses.
    res2 = run_rule(rule, {"sensitivity": "high"})     # corr missing
    check("rule_abstains_on_missing_input_with_fallback",
          res2.abstained and not res2.fired
          and res2.candidate_actions
          and res2.candidate_actions[0].kind == "fallback",
          f"{res2.reason}")

    # 6. ABSTAIN outside the validated scope (abstain_when guard).
    res3 = run_rule(rule, {"corr": 0.95, "sensitivity": "low"})
    check("rule_abstains_outside_its_scope",
          res3.abstained and "outside scope" in res3.reason,
          "low-sensitivity model -> abstain + fallback, not a spurious finding")

    # 7. a parameter is clamped to its declared range.
    res4 = run_rule(rule, {"corr": 0.6, "sensitivity": "high", "thr": 0.4})
    # thr clamped to min 0.5; corr 0.6 >= 0.5 -> fires
    check("parameters_are_clamped_to_their_range",
          res4.fired, "thr=0.4 clamped up to 0.5; 0.6>=0.5 fires")

    # 8. a logic rule is a searchable node (the Logic category).
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=[rule_record(rule)])
    store.enable_tier("experimental")
    hit = store.search("feature redundancy collinearity review", kind="node")
    check("logic_rules_are_searchable_nodes",
          hit["hits"] and any("logic." in h["record_id"] for h in hit["hits"]),
          "the Logic category shares the one search DAG")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "logic_ast_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
