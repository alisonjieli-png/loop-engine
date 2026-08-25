"""Output templates — a graded ladder of response FORMS, each shaped so the answer
becomes a reusable asset rather than disposable prose.

Owner ask (2026-08-23): we need more variations and templates for output schemas to
enforce reusability of code and LLM responses — from simple, to string outputs, to
JSON lists, to if/then statements, to measurements, to evaluations, to full
code/statistical tests.

Where [[decision_schemas.py]] fixes the FIELDS of a decision type (next_action,
review…), this module fixes the FORM of a single answer, on a ladder of increasing
structure and reusability:

    rank 1  simple_value      one token/label/number      -> keyword / fact
    rank 2  string_statement  one reusable sentence        -> heuristic / practice
    rank 3  json_list         a list of typed items        -> many candidates
    rank 4  if_then_rule      condition(s) -> output(s)     -> logic node (AST)
    rank 5  measurement_spec  metric, direction, threshold -> metric definition
    rank 6  evaluation        verdict + evidence           -> evaluation criterion
    rank 7  code_or_test      runnable code / stat test    -> deterministic node

The higher the form the task allows, the more directly the response becomes a
deterministic, reusable capability — so the practitioner should REQUEST the most
structured form the content supports (``recommend_form``), not settle for prose.
Each template renders the exact instruction (``as_instruction``), maps to the
candidate type it becomes (``reusable_as``), and parses the response
deterministically (``parse``) so capture is not guesswork.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable

from ..code_nodes.learning_bundle import CANDIDATE_TYPES

OUTPUT_FORMS = ("simple_value", "string_statement", "json_list", "if_then_rule",
                "measurement_spec", "evaluation", "code_or_test")


@dataclass(frozen=True)
class OutputTemplate:
    form: str
    purpose: str
    instruction: str
    reusable_as: str            # the CANDIDATE_TYPE a well-formed answer becomes
    reusability_rank: int
    example: str
    _parse: Callable

    def __post_init__(self):
        if self.form not in OUTPUT_FORMS:
            raise ValueError(f"form must be one of {OUTPUT_FORMS}")
        if self.reusable_as not in CANDIDATE_TYPES:
            raise ValueError(f"reusable_as must be a CANDIDATE_TYPE")

    def as_instruction(self) -> str:
        return (f"Answer in the '{self.form}' form ({self.purpose}). "
                f"{self.instruction}\nExample: {self.example}")

    def parse(self, text: str) -> dict:
        """Deterministic best-effort extraction into the reusable shape.  Honest:
        ``ok`` is False when the response does not fit the requested form."""
        return self._parse(text or "")


# --- deterministic parsers --------------------------------------------------

_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_FENCE = re.compile(r"```(\w+)?\s*(.*?)```", re.DOTALL)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$")
_STAT_TESTS = ("t-test", "t test", "ttest", "chi-square", "chi square", "chi2",
               "anova", "f_oneway", "mann-whitney", "mannwhitney", "wilcoxon",
               "kolmogorov", "ks test", "kstest", "shapiro", "pearson",
               "spearman", "f-test", "z-test")


def _p_simple(t: str) -> dict:
    t = t.strip().splitlines()[0].strip() if t.strip() else ""
    return {"ok": bool(t) and len(t) <= 60, "value": t, "form": "simple_value"}


def _p_string(t: str) -> dict:
    s = " ".join(t.split())
    return {"ok": bool(s), "statement": s[:400], "form": "string_statement"}


def _p_json_list(t: str) -> dict:
    t = t.strip()
    # try real JSON first
    try:
        m = re.search(r"\[.*\]", t, re.DOTALL)
        if m:
            arr = json.loads(m.group(0))
            if isinstance(arr, list):
                return {"ok": True, "items": arr, "form": "json_list",
                        "source": "json"}
    except Exception:                                       # noqa: BLE001
        pass
    # fall back to bullet lines
    items = [m.group(1).strip() for m in
             (_BULLET.match(ln) for ln in t.splitlines()) if m]
    return {"ok": len(items) >= 1, "items": items, "form": "json_list",
            "source": "bullets"}


def _p_if_then(t: str) -> dict:
    conds, outs = [], []
    for m in re.finditer(r"if\s+(.+?)\s+then\s+(.+?)(?:[.\n]|$)", t, re.I):
        conds.append(m.group(1).strip())
        outs.append(m.group(2).strip())
    return {"ok": bool(conds), "conditions": conds, "outputs": outs,
            "form": "if_then_rule",
            "note": "nominate as a logic_candidate for the safe logic AST"}


def _p_measurement(t: str) -> dict:
    low = t.lower()
    direction = ("minimize" if any(w in low for w in
                 ("minimize", "lower is better", "lower the better", "less is"))
                 else "maximize")
    nums = _NUM.findall(t)
    threshold = float(nums[0]) if nums else None
    m = re.search(r"(?:metric|measure)\s*[:=]\s*([A-Za-z0-9_ \-]+)", t, re.I)
    name = (m.group(1).strip() if m else
            (t.split()[0].strip(":") if t.split() else ""))
    return {"ok": bool(name), "name": name, "direction": direction,
            "threshold": threshold, "form": "measurement_spec"}


def _p_evaluation(t: str) -> dict:
    low = t.lower()
    verdict = next((v for v in ("degenerate", "pass_with_notes", "fail", "pass")
                    if v in low), "")
    ev = [m.group(1).strip() for m in
          (_BULLET.match(ln) for ln in t.splitlines()) if m]
    return {"ok": bool(verdict), "verdict": verdict, "evidence": ev,
            "form": "evaluation"}


def _p_code(t: str) -> dict:
    m = _FENCE.search(t)
    code = m.group(2).strip() if m else ""
    lang = (m.group(1) or "python") if m else ""
    test_kind = next((s for s in _STAT_TESTS if s in t.lower()), "")
    return {"ok": bool(code), "code": code, "language": lang,
            "statistical_test": test_kind, "needs_sandbox": bool(code),
            "form": "code_or_test",
            "note": "execute under subprocess isolation before trusting"}


# --- the registry -----------------------------------------------------------

OUTPUT_TEMPLATE_REGISTRY = {t.form: t for t in (
    OutputTemplate("simple_value", "one atomic value",
                   "Return only the single value (a label, number, or yes/no) "
                   "with no prose.", "keyword_resource", 1,
                   "churn_rate", _p_simple),
    OutputTemplate("string_statement", "one reusable statement",
                   "Return exactly one clear sentence that stands alone and can "
                   "be reused verbatim.", "heuristic", 2,
                   "Prefer point-in-time features to avoid temporal leakage.",
                   _p_string),
    OutputTemplate("json_list", "a list of typed items",
                   "Return a JSON array; each element is one atomic, reusable "
                   "item.", "knowledge_claim", 3,
                   '["storage is an explanatory variable", "weather affects '
                   'demand"]', _p_json_list),
    OutputTemplate("if_then_rule", "a conditional rule",
                   "Return one or more 'IF <condition> THEN <output>' lines, "
                   "each a deterministic rule.", "logic_candidate", 4,
                   "IF pairwise correlation > 0.9 AND model is coefficient-"
                   "sensitive THEN flag feature redundancy for review.",
                   _p_if_then),
    OutputTemplate("measurement_spec", "a metric specification",
                   "Return metric name, direction (maximize/minimize), and "
                   "acceptance threshold.", "metric_definition", 5,
                   "metric: PR-AUC, maximize, threshold 0.85", _p_measurement),
    OutputTemplate("evaluation", "a judgement with evidence",
                   "Return a verdict (pass / pass_with_notes / degenerate / "
                   "fail) and bulleted evidence for and against.",
                   "evaluation_criterion", 6,
                   "verdict: pass_with_notes\n- CV 0.84 beats baseline 0.62\n"
                   "- but folds vary ±0.05", _p_evaluation),
    OutputTemplate("code_or_test", "runnable code or a statistical test",
                   "Return a single fenced code block implementing the exact "
                   "contract; name any statistical test used.", "node_candidate",
                   7, "```python\ndef check(x):\n    from scipy.stats import "
                   "ttest_ind\n    ...\n```", _p_code))}


def template(form: str) -> OutputTemplate:
    if form not in OUTPUT_TEMPLATE_REGISTRY:
        raise KeyError(f"no output template {form!r}; have {OUTPUT_FORMS}")
    return OUTPUT_TEMPLATE_REGISTRY[form]


def recommend_form(*, is_code: bool = False, is_judgement: bool = False,
                   is_metric: bool = False, has_conditions: bool = False,
                   is_multi: bool = False, is_atomic: bool = False) -> str:
    """Pick the MOST reusable form the content supports — the bias toward
    structure.  Higher-rank forms win, so a rule is captured as a rule (a logic
    node), a metric as a metric, code as code — never flattened to prose."""
    if is_code:
        return "code_or_test"
    if is_judgement:
        return "evaluation"
    if is_metric:
        return "measurement_spec"
    if has_conditions:
        return "if_then_rule"
    if is_multi:
        return "json_list"
    if is_atomic:
        return "simple_value"
    return "string_statement"


def template_records() -> list:
    """Each output template as a searchable strategy record."""
    from ..static_architecture.store_serve import StoreRecord
    recs = []
    for t in OUTPUT_TEMPLATE_REGISTRY.values():
        recs.append(StoreRecord(
            record_id=f"outform.{t.form}", kind="strategy",
            title=f"Output form: {t.purpose} (reusable as {t.reusable_as})",
            body={"form": t.form, "reusability_rank": t.reusability_rank,
                  "reusable_as": t.reusable_as,
                  "instruction": t.as_instruction()},
            tags=("output_template", "reusability", t.form, "step:decide_next",
                  "step:how"), tier="core"))
    return recs


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. the ladder is ordered by reusability and maps each form to a candidate.
    ranks = [template(f).reusability_rank for f in OUTPUT_FORMS]
    check("the_form_ladder_is_ordered_by_reusability",
          ranks == sorted(ranks) and ranks[0] == 1 and ranks[-1] == 7
          and all(template(f).reusable_as in CANDIDATE_TYPES
                  for f in OUTPUT_FORMS),
          f"ranks {ranks}; each form maps to a reusable candidate type")

    # 2. an if/then response parses into conditions/outputs (-> a logic node).
    r = template("if_then_rule").parse(
        "IF pairwise correlation > 0.9 AND model is coefficient-sensitive THEN "
        "flag feature redundancy for review.")
    check("if_then_form_parses_into_a_logic_candidate",
          r["ok"] and r["conditions"] and r["outputs"]
          and "logic_candidate" in r["note"],
          f"conditions={r['conditions']}")

    # 3. a json list parses (json first, bullets fallback).
    rj = template("json_list").parse('["a", "b", "c"]')
    rb = template("json_list").parse("- storage\n- weather\n- production")
    check("json_list_form_parses_json_and_bullets",
          rj["ok"] and rj["items"] == ["a", "b", "c"] and rj["source"] == "json"
          and rb["ok"] and len(rb["items"]) == 3 and rb["source"] == "bullets",
          "both a JSON array and a bullet list become items")

    # 4. a measurement spec extracts name/direction/threshold.
    rm = template("measurement_spec").parse(
        "metric: PR-AUC, maximize, threshold 0.85")
    check("measurement_form_extracts_name_direction_threshold",
          rm["ok"] and rm["direction"] == "maximize" and rm["threshold"] == 0.85,
          f"{rm['name']} / {rm['direction']} / {rm['threshold']}")

    # 5. an evaluation extracts a verdict + evidence.
    re_ = template("evaluation").parse(
        "verdict: pass_with_notes\n- CV 0.84 beats baseline\n- folds vary")
    check("evaluation_form_extracts_verdict_and_evidence",
          re_["ok"] and re_["verdict"] == "pass_with_notes"
          and len(re_["evidence"]) == 2,
          f"verdict={re_['verdict']}")

    # 6. code form extracts the code, names the stat test, flags sandbox need.
    rc = template("code_or_test").parse(
        "```python\nfrom scipy.stats import ttest_ind\nttest_ind(a,b)\n```")
    check("code_form_extracts_code_and_flags_sandbox",
          rc["ok"] and "ttest_ind" in rc["code"]
          and rc["statistical_test"] in ("t-test", "t test", "ttest")
          and rc["needs_sandbox"],
          f"stat test detected: {rc['statistical_test']}")

    # 7. recommend_form biases toward the MOST reusable form the content allows.
    check("recommend_form_prefers_the_most_reusable_form",
          recommend_form(is_code=True) == "code_or_test"
          and recommend_form(has_conditions=True) == "if_then_rule"
          and recommend_form(is_metric=True) == "measurement_spec"
          and recommend_form() == "string_statement",
          "a rule is requested as a rule, a metric as a metric, code as code")

    # 8. output templates are searchable resources.
    from ..static_architecture.store_serve import SolverStore
    store = SolverStore(core_records=template_records())
    hit = store.search("return a runnable statistical test as code",
                       kind="strategy")
    check("output_templates_are_searchable_resources",
          hit["hits"] and any("outform.code_or_test" == h["record_id"]
                              for h in hit["hits"]),
          "the code/test form is findable through the one search DAG")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "output_templates_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
