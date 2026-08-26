"""Capture — before the loop composes the next step, harvest what an open-ended
model call taught us into a standardized, reusable form.

Owner invariant (2026-08-23): the opening steps (research first, then a detailed
solution outline, things to watch out for, common and uncommon mistakes, best
practices, and ways of measuring success) produce open-ended reasoning.  That
reasoning must be encapsulated into our databases for next time — as text, a
logic node, or a subdag graph/logic node — BEFORE moving on to the next
DAG-composing step.  And if a model response is so open-ended that it cannot be
encapsulated and reused, that is the signal to spend additional model calls
breaking it down further — not to advance.

So this module is two things:

  * The OPENING SCAFFOLDING (required first steps + their strings):
    ``scaffolding_pack`` / ``SCAFFOLDING_STEPS`` — outline, watch-outs, common &
    uncommon mistakes, best practices, success measures.  Data (strings), so an
    open-source consumer swaps or grows them.

  * The CAPTURE GATE (the invariant, harness code): ``encapsulate`` scans an
    open-ended result and proposes typed ``CaptureCandidate``s along the
    compression ladder (intelligence_string → question → logic_rule →
    deterministic_node → subdag_fragment → task_graph → knowledge_fact →
    failure_pattern → blueprint_fragment), or flags that it is too diffuse to
    encapsulate.  ``capture_gate`` then decides: advance to compose, capture
    first, or break it down with more calls — fail-closed, so nothing learned is
    silently dropped.  Captured candidates become searchable store records and
    materialize as IntelligenceStrings, so the learning enters the library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

from ..strings.intelligence_strings import IntelligenceString, StringBank, distill_string

# The required opening steps the owner named.  ``research`` is the first bias
# step (critically important); the rest scaffold the solution before building.
SCAFFOLDING_STEPS = ("research", "outline", "watch_outs", "common_mistakes",
                     "uncommon_mistakes", "best_practices", "success_measures")

# The standardized reusable forms an open-ended answer can be captured as — the
# capability-compression ladder, cheapest/loosest to richest.
CAPTURE_TARGETS = ("intelligence_string", "question", "logic_rule",
                   "deterministic_loop", "subdag_fragment", "task_graph",
                   "knowledge_fact", "failure_pattern", "blueprint_fragment")
GATE_ACTIONS = ("advance_to_compose", "capture_then_advance",
                "break_down_with_more_calls")


# ---------------------------------------------------------------------------
# Opening scaffolding: required first steps as Context Intelligence.
# ---------------------------------------------------------------------------


def scaffolding_pack() -> StringBank:
    """One instruction string per required opening step.  Tagged for the
    preparation nodes (assess/reconcile) — these run BEFORE composing a
    solution, and every output is meant to be captured."""
    bank = StringBank()
    steps = [
        ("research",
         "First, research the problem: what has already been solved, which "
         "standards/sources/packages apply, and what the state of the art is. "
         "Do not invent what can be reused."),
        ("outline",
         "Produce a detailed outline of the solution — the components, their "
         "contracts, and the order of work — before building anything."),
        ("watch_outs",
         "List the things to watch out for on this task: hidden assumptions, "
         "data/leakage traps, edge cases, and where solutions usually go wrong."),
        ("common_mistakes",
         "List the common mistakes for this kind of problem and how to avoid "
         "each one."),
        ("uncommon_mistakes",
         "List the uncommon, subtle mistakes an expert still makes here — the "
         "ones that pass casual review."),
        ("best_practices",
         "State the best practices and established conventions for this task "
         "family, with why each matters."),
        ("success_measures",
         "Define how success will be measured: the acceptance metric, its "
         "direction and threshold, the population, and the health checks "
         "(train-CV gap, leakage, baselines)."),
    ]
    for step, text in steps:
        bank.add(IntelligenceString(
            "instruction", text,
            tags=("scaffolding", f"scaffold:{step}", "step:assess_prepare"),
            applicability="any", provenance="hand_seed"))
    return bank


def opening_agenda() -> list:
    """The required opening steps as an ordered agenda template.  The loop plans
    this window but executes ONE step per pass and re-evaluates (per the
    one-bounded-obligation rule)."""
    return [{"step": s, "captures_to": "standardized reusable records",
             "required": s in ("research", "outline", "success_measures")}
            for s in SCAFFOLDING_STEPS]


# ---------------------------------------------------------------------------
# The capture gate — encapsulate an open-ended result, or break it down.
# ---------------------------------------------------------------------------


@dataclass
class CaptureCandidate:
    """One standardized reusable unit harvested from an open-ended result."""
    target_kind: str
    canonical_text: str
    intended_function: str = ""
    applicability: str = "any"
    confidence: float = 0.5
    source_ref: str = ""

    def __post_init__(self):
        if self.target_kind not in CAPTURE_TARGETS:
            raise ValueError(f"target_kind must be one of {CAPTURE_TARGETS}")


@dataclass
class CaptureReport:
    encapsulable: bool
    needs_more_calls: bool
    candidates: tuple = ()
    reason: str = ""
    coverage: dict = field(default_factory=dict)


_COND_CUES = ("if ", "when ", "unless ", "whenever ", ">=", "<=", "threshold",
              "greater than", "less than", "at least", "exceeds")
_QUESTION = re.compile(r"[?]\s*$")
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$")


def _lines(text: str) -> list:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def _bullets(lines: Sequence[str]) -> list:
    out = []
    for ln in lines:
        m = _BULLET.match(ln)
        if m:
            out.append(m.group(1).strip())
    return out


def encapsulate(text: str, *, agenda_step: str = "",
                min_units: int = 1) -> CaptureReport:
    """Scan an open-ended result and propose standardized capture candidates.

    Deterministic and honest — a heuristic scanner, not a model.  It looks for
    the structure that makes a result reusable (a crisp claim, a list of
    considerations, an if/then rule, a diagnostic question) and proposes the
    matching target on the compression ladder.  If the text is long and shows NO
    extractable structure, it declines to fake a capture and flags
    ``needs_more_calls`` — the signal to break it down with additional calls."""
    lines = _lines(text)
    bullets = _bullets(lines)
    joined = " ".join(lines).lower()
    cands: list = []

    # 1. explicit conditional/threshold language -> a logic-rule candidate
    #    (materialized later against the safe logic AST; here it is nominated).
    if any(c in joined for c in _COND_CUES):
        cands.append(CaptureCandidate(
            "logic_rule", text.strip()[:400],
            intended_function=f"deterministic check from {agenda_step or 'result'}",
            confidence=0.5, source_ref=agenda_step))

    # 2. a list of considerations/steps -> reusable strings (+ a blueprint
    #    fragment when the step is an outline/plan).
    if len(bullets) >= 2:
        for b in bullets[:12]:
            kind = "question" if _QUESTION.search(b) else "intelligence_string"
            cands.append(CaptureCandidate(
                kind, b, intended_function=agenda_step or "consideration",
                confidence=0.55, source_ref=agenda_step))
        if agenda_step in ("outline",):
            cands.append(CaptureCandidate(
                "blueprint_fragment", " | ".join(bullets[:12]),
                intended_function="solution outline", confidence=0.6,
                source_ref=agenda_step))

    # 3. a single crisp claim/question (short, structured) -> one unit.
    if not cands and lines:
        one = " ".join(lines)
        if len(one) <= 300:
            kind = "question" if _QUESTION.search(one) else "intelligence_string"
            cands.append(CaptureCandidate(
                kind, one, intended_function=agenda_step or "note",
                confidence=0.5, source_ref=agenda_step))

    # 4. failure/mistake framing -> also capture a failure_pattern.
    if agenda_step in ("common_mistakes", "uncommon_mistakes", "watch_outs") \
            and bullets:
        cands.append(CaptureCandidate(
            "failure_pattern", " | ".join(bullets[:12]),
            intended_function=f"nogoods from {agenda_step}", confidence=0.55,
            source_ref=agenda_step))

    coverage = {"lines": len(lines), "bullets": len(bullets),
                "has_conditional": any(c in joined for c in _COND_CUES)}

    # Too diffuse to encapsulate: long prose, no list, no rule, no crisp unit.
    if len(cands) < min_units and len(joined) > 600 and len(bullets) == 0:
        return CaptureReport(
            encapsulable=False, needs_more_calls=True, candidates=(),
            reason="the result is long and unstructured — it cannot be "
            "encapsulated into a reusable unit; spend additional model calls to "
            "break it into components (outline / checks / questions) before "
            "advancing", coverage=coverage)

    return CaptureReport(
        encapsulable=bool(cands), needs_more_calls=False,
        candidates=tuple(cands),
        reason=(f"captured {len(cands)} standardized reusable unit(s)"
                if cands else "nothing reusable found in this result"),
        coverage=coverage)


@dataclass
class CaptureGateDecision:
    advance: bool
    next_action: str
    reason: str

    def __post_init__(self):
        if self.next_action not in GATE_ACTIONS:
            raise ValueError(f"next_action must be one of {GATE_ACTIONS}")


def capture_gate(report: CaptureReport) -> CaptureGateDecision:
    """The fail-closed gate between an open-ended pass and the next DAG-composing
    step.  Nothing learned is silently dropped: either it was captured, or we
    break it down with more calls — we never advance past un-harvested learning."""
    if report.needs_more_calls:
        return CaptureGateDecision(
            False, "break_down_with_more_calls",
            "result too open-ended to encapsulate; schedule additional model "
            "calls to decompose it — do not advance to compose the next step")
    if not report.candidates:
        return CaptureGateDecision(
            False, "capture_then_advance",
            "no standardized reusable candidate was harvested; capture at least "
            "one before advancing")
    return CaptureGateDecision(
        True, "advance_to_compose",
        f"{len(report.candidates)} reusable unit(s) stored; safe to compose the "
        "next step")


class CaptureGateError(RuntimeError):
    """Raised by the strict assertion when the loop would advance past
    un-harvested learning."""


def require_capture_before_advance(report: CaptureReport) -> None:
    """Strict form of the invariant for callers that must not proceed."""
    decision = capture_gate(report)
    if not decision.advance:
        raise CaptureGateError(decision.reason)


# ---------------------------------------------------------------------------
# Materialize captures into the library.
# ---------------------------------------------------------------------------


def to_intelligence_strings(report: CaptureReport) -> list:
    """Materialize string/question candidates as IntelligenceStrings (candidate
    maturity) so the harvest enters the searchable string library."""
    out = []
    for c in report.candidates:
        if c.target_kind in ("intelligence_string", "question"):
            kind = "consideration" if c.target_kind == "intelligence_string" \
                else "question" if "question" in \
                _string_kinds() else "consideration"
            out.append(distill_string(
                c.canonical_text, kind, tags=("captured", c.intended_function),
                applicability=c.applicability))
    return out


def _string_kinds() -> tuple:
    from ..strings.intelligence_strings import STRING_KINDS
    return STRING_KINDS


def candidate_records(report: CaptureReport, *, run_ref: str = "") -> list:
    """Every capture candidate as a searchable store record (the harvested
    learning, findable next time)."""
    from ..core.store_serve import StoreRecord
    recs = []
    for i, c in enumerate(report.candidates):
        kind = "question" if c.target_kind == "question" else \
            "node" if c.target_kind in ("logic_rule", "deterministic_loop",
                                        "subdag_fragment", "task_graph") \
            else "context"
        recs.append(StoreRecord(
            record_id=f"capture.{run_ref or 'run'}.{i}", kind=kind,
            title=c.canonical_text[:80],
            body={"target_kind": c.target_kind, "text": c.canonical_text,
                  "intended_function": c.intended_function,
                  "confidence": c.confidence},
            tags=("captured", c.target_kind, c.intended_function),
            tier="experimental"))
    return recs


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. the required opening steps are present as scaffolding strings.
    pack = scaffolding_pack()
    txt = " ".join(s.text.lower() for s in pack.all())
    check("required_opening_steps_exist_as_scaffolding_strings",
          len(pack) == len(SCAFFOLDING_STEPS)
          and "detailed outline" in txt and "watch out for" in txt
          and "common mistakes" in txt and "uncommon" in txt
          and "best practices" in txt and "how success will be measured" in txt,
          f"{len(pack)} scaffolding strings: {list(SCAFFOLDING_STEPS)}")

    # 2. a bulleted result is captured into reusable units.
    outline = ("Solution outline:\n- Load and validate the data\n"
               "- Engineer point-in-time features\n- Fit a baseline model\n"
               "- Backtest with rolling origin")
    rep = encapsulate(outline, agenda_step="outline")
    kinds = {c.target_kind for c in rep.candidates}
    check("a_structured_result_is_captured_into_reusable_units",
          rep.encapsulable and "intelligence_string" in kinds
          and "blueprint_fragment" in kinds,
          f"captured {len(rep.candidates)} units: {sorted(kinds)}")

    # 3. conditional language yields a logic-rule candidate.
    rule = encapsulate("If pairwise correlation exceeds 0.9 and the model is "
                       "coefficient-sensitive, flag feature redundancy for "
                       "review.")
    check("conditional_language_yields_a_logic_rule_candidate",
          any(c.target_kind == "logic_rule" for c in rule.candidates),
          "an if/then result is nominated as deterministic logic")

    # 4. mistake framing also captures a failure_pattern.
    mistakes = ("- Splitting time series randomly leaks the future\n"
                "- Tuning on the test set\n- Ignoring class imbalance")
    repm = encapsulate(mistakes, agenda_step="common_mistakes")
    check("mistake_framing_captures_a_failure_pattern",
          any(c.target_kind == "failure_pattern" for c in repm.candidates),
          "common-mistakes output becomes a searchable nogood")

    # 5. THE INVARIANT: a diffuse, unstructured result is NOT faked into a
    # capture — it flags needs_more_calls (break it down).
    diffuse = ("Well, there are many considerations here and it really depends "
               "on a lot of factors and context that we would need to think "
               "about carefully before deciding anything concrete. " * 6)
    repd = encapsulate(diffuse)
    gate = capture_gate(repd)
    check("too_open_ended_flags_break_down_not_a_fake_capture",
          repd.needs_more_calls and not gate.advance
          and gate.next_action == "break_down_with_more_calls",
          "an unencapsulable result routes to more calls, never a silent skip")

    # 6. the gate is fail-closed: no advance past un-harvested learning.
    raised = False
    try:
        require_capture_before_advance(repd)
    except CaptureGateError:
        raised = True
    ok_advance = capture_gate(rep).advance          # the outline captured fine
    check("capture_gate_is_fail_closed_before_advancing",
          raised and ok_advance,
          "advancing past a diffuse result raises; a captured result advances")

    # 7. captured units materialize as searchable Context Intelligence.
    strings = to_intelligence_strings(rep)
    check("captured_units_enter_the_string_library",
          strings and all(isinstance(s, IntelligenceString) for s in strings)
          and all(s.provenance == "llm_distilled" for s in strings),
          f"{len(strings)} captured strings materialized (candidate maturity)")

    # 8. captured candidates are searchable store records.
    from ..core.store_serve import SolverStore
    recs = candidate_records(rep, run_ref="t1")
    store = SolverStore(core_records=[])
    store.enable_tier("experimental")
    store = SolverStore(core_records=recs)
    store.enable_tier("experimental")
    hit = store.search("engineer point in time features outline")
    check("captured_learning_is_findable_next_time",
          hit["hits"] and any("capture." in h["record_id"]
                              for h in hit["hits"]),
          "the harvest is stored where the next run's search will find it")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "capture_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
