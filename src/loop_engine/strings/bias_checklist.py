"""Bias checklist — a semi-persistent, per-run list of preferred first steps that
rides in every model prompt and subtly biases what happens next.

Owner design (2026-08-23): research first is critically important, then the other
preferred steps in order — understand why, outline, watch-outs, common & uncommon
mistakes, best practices, success measures, and finally create reusable assets and
distill deterministic rules / reusable subgraphs.  Rather than hard-code that as a
gate, carry a CHECKLIST into each LLM call so the model knows what we prefer and
what has already been done.  Once every preferred step is completed, considered,
or ruled out, the model earns more freedom to choose what is next — we are subtly
increasing bias through the prompt, not forcing a rigid order.

Two more rules the owner set:

  * BEFORE **and** AFTER.  A step is not "done" when we merely plan it — we don't
    yet know if the result is good.  ``open_step`` records the before; ``close_step``
    records the after with whether the result was good.  A step only counts as done
    when it has both, and a poor result sends it back to pending (retry), never
    forward.  (Pre- and post-implementation capture; see [[capture.py]].)

  * SKIPS are allowed but TRACKED — why, when, where, how — so a step the model
    keeps skipping for a task family can later be dropped deterministically and
    cheaply.  Skip records are append-only and searchable.

The checklist is per-run mutable state; ``snapshot`` yields a dict for the
immutable pass record, so each pass carries a frozen view.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Sequence

# The preferred first steps, in order.  Research first; the last two ensure we
# actually leave reusable capability behind (assets + deterministic rules).
BIAS_STEP_SEQUENCE = ("research", "understand_why", "outline", "watch_outs",
                      "common_mistakes", "uncommon_mistakes", "best_practices",
                      "success_measures", "create_reusable_assets",
                      "distill_deterministic_rules")

STEP_STATUSES = ("pending", "in_progress", "done", "considered", "ruled_out",
                 "skipped")
# A step no longer demands attention once it is in one of these.
_RESOLVED = ("done", "considered", "ruled_out", "skipped")
_MARKERS = {"pending": "[ ]", "in_progress": "[~]", "done": "[x]",
            "considered": "[c]", "ruled_out": "[r]", "skipped": "[-]"}


@dataclass
class SkipRecord:
    """Why a preferred step was skipped — the four facts that make it learnable."""
    step: str
    why: str
    when_pass: str = ""          # when: the pass id
    where: str = ""              # where: node / checkpoint / context
    how: str = "model"           # how it was decided: model | deterministic | policy


@dataclass
class BiasStep:
    key: str
    order: int
    status: str = "pending"
    done_count: int = 0
    result_good: "bool | None" = None
    before_captured: bool = False
    after_captured: bool = False


class BiasStepError(RuntimeError):
    """A checklist misuse — e.g. closing a step that was never opened (which
    would skip the 'before' half of before-and-after)."""


class BiasChecklist:
    """The semi-persistent per-run checklist."""

    def __init__(self, steps: "Sequence[str] | None" = None, *,
                 run_ref: str = ""):
        seq = tuple(steps) if steps else BIAS_STEP_SEQUENCE
        self.run_ref = run_ref
        self.steps: dict = {k: BiasStep(k, i) for i, k in enumerate(seq)}
        self.skips: list = []            # append-only

    def _get(self, key: str) -> BiasStep:
        if key not in self.steps:
            raise BiasStepError(f"unknown bias step {key!r}; have "
                                f"{list(self.steps)}")
        return self.steps[key]

    # --- before / after -----------------------------------------------------

    def open_step(self, key: str, *, before_captured: bool = True) -> BiasStep:
        """BEFORE: mark a step in progress and record that we captured the plan."""
        st = self._get(key)
        st.status = "in_progress"
        st.before_captured = before_captured
        return st

    def close_step(self, key: str, *, result_good: bool,
                   after_captured: bool = True) -> BiasStep:
        """AFTER: record the result.  A step counts as done only with BOTH the
        before and a good after — a poor result returns it to pending (retry),
        never forward, so we never advance on results we haven't judged good."""
        st = self._get(key)
        if not st.before_captured:
            raise BiasStepError(
                f"cannot close {key!r} before it was opened — the 'before' "
                "capture is missing; a step needs before AND after")
        st.after_captured = after_captured
        st.result_good = bool(result_good)
        if result_good:
            st.status = "done"
            st.done_count += 1
        else:
            st.status = "pending"       # retry: we don't advance on a bad result
        return st

    # --- other resolutions --------------------------------------------------

    def consider(self, key: str) -> BiasStep:
        st = self._get(key)
        st.status = "considered"
        return st

    def rule_out(self, key: str, *, why: str) -> BiasStep:
        st = self._get(key)
        st.status = "ruled_out"
        self.skips.append(SkipRecord(key, why, how="model"))
        return st

    def skip(self, key: str, *, why: str, when_pass: str = "",
             where: str = "", how: str = "model") -> SkipRecord:
        """Skip a step — allowed, but the four facts are recorded for learning."""
        st = self._get(key)
        st.status = "skipped"
        rec = SkipRecord(key, why, when_pass=when_pass, where=where, how=how)
        self.skips.append(rec)
        return rec

    # --- what's next / freedom ---------------------------------------------

    def next_preferred(self) -> "str | None":
        """The next preferred step still demanding attention, or None when the
        model has earned freedom to choose."""
        for st in sorted(self.steps.values(), key=lambda s: s.order):
            if st.status in ("pending", "in_progress"):
                return st.key
        return None

    def freedom_granted(self) -> bool:
        """True once every preferred step is resolved (done/considered/ruled out/
        skipped) — the model may then choose the next action freely."""
        return all(st.status in _RESOLVED for st in self.steps.values())

    # --- the prompt-carried bias -------------------------------------------

    def render_for_prompt(self) -> str:
        """The compact checklist injected into each model prompt — the subtle
        bias mechanism.  The next preferred step is marked so the model leans
        toward it without being forced."""
        nxt = self.next_preferred()
        lines = ["SOLVING PREFERENCES (do these first, in order; skip only with "
                 "a recorded reason):"]
        for st in sorted(self.steps.values(), key=lambda s: s.order):
            mark = _MARKERS[st.status]
            tag = st.key.replace("_", " ")
            suffix = ""
            if st.status == "done" and st.done_count > 1:
                suffix = f" (x{st.done_count})"
            elif st.key == nxt:
                suffix = "   <- do this next"
            lines.append(f"  {mark} {tag}{suffix}")
        if self.freedom_granted():
            lines.append("All preferred steps resolved — you may choose the next "
                         "action freely, justifying your choice.")
        else:
            lines.append("You may skip a step that is genuinely irrelevant, but "
                         "state why (it will be recorded).")
        return "\n".join(lines)

    # --- persistence / search ----------------------------------------------

    def snapshot(self) -> dict:
        """A frozen dict for the immutable pass record."""
        return {"record_type": "bias_checklist_snapshot/v1",
                "run_ref": self.run_ref,
                "next_preferred": self.next_preferred(),
                "freedom_granted": self.freedom_granted(),
                "steps": {k: asdict(v) for k, v in self.steps.items()},
                "skips": [asdict(s) for s in self.skips]}

    def skip_records(self) -> list:
        """Every skip/rule-out as a searchable store record — 'when do we skip
        watch-outs?' becomes answerable, so skips get cheaper and deterministic."""
        from ..static_architecture.store_serve import StoreRecord
        recs = []
        for i, s in enumerate(self.skips):
            recs.append(StoreRecord(
                record_id=f"biasskip.{self.run_ref or 'run'}.{i}", kind="context",
                title=f"skipped '{s.step}': {s.why[:60]}",
                body={"step": s.step, "why": s.why, "when_pass": s.when_pass,
                      "where": s.where, "how": s.how},
                tags=("bias_skip", "learning", f"step:{s.step}"),
                tier="experimental"))
        return recs


def checklist_node():
    """The checklist mechanism as a searchable node record."""
    from ..static_architecture.store_serve import StoreRecord
    return StoreRecord(
        record_id="node.bias_checklist", kind="node",
        title="Semi-persistent bias-step checklist carried in every prompt",
        body={"sequence": list(BIAS_STEP_SEQUENCE),
              "statuses": list(STEP_STATUSES),
              "rule": "before AND after; skips tracked (why/when/where/how); "
              "freedom granted once all steps resolved"},
        tags=("bias_checklist", "step:decide_next", "step:assess_prepare"),
        tier="core")


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    cl = BiasChecklist(run_ref="t1")

    # 1. research is the first preferred step; the sequence is ordered.
    check("research_is_the_first_preferred_step",
          cl.next_preferred() == "research"
          and cl.steps["research"].order == 0
          and cl.steps["distill_deterministic_rules"].order
          == len(BIAS_STEP_SEQUENCE) - 1,
          f"next preferred = {cl.next_preferred()}")

    # 2. BEFORE and AFTER: closing without opening raises (before is required).
    raised = False
    try:
        cl.close_step("research", result_good=True)
    except BiasStepError:
        raised = True
    check("a_step_needs_before_and_after_close_without_open_raises", raised,
          "we cannot mark a step done from planning alone")

    # 3. open (before) then close good (after) -> done.
    cl.open_step("research")
    cl.close_step("research", result_good=True)
    check("open_then_good_close_marks_done",
          cl.steps["research"].status == "done"
          and cl.steps["research"].done_count == 1,
          "before + good after = done")

    # 4. a POOR after-result does NOT advance — it returns to pending (retry).
    cl.open_step("understand_why")
    cl.close_step("understand_why", result_good=False)
    check("a_poor_result_does_not_advance_it_retries",
          cl.steps["understand_why"].status == "pending"
          and cl.steps["understand_why"].result_good is False
          and cl.next_preferred() == "understand_why",
          "we don't move on when the result isn't good")

    # 5. the prompt checklist marks the next preferred step (subtle bias).
    cl.open_step("understand_why")
    cl.close_step("understand_why", result_good=True)
    rendered = cl.render_for_prompt()
    check("the_prompt_checklist_marks_the_next_preferred_step",
          "SOLVING PREFERENCES" in rendered
          and "[x] research" in rendered
          and "<- do this next" in rendered
          and rendered.count("<- do this next") == 1,
          "the checklist rides the prompt and points at the next step")

    # 6. skips are allowed but record why/when/where/how.
    rec = cl.skip("uncommon_mistakes", why="one-line task; no subtle failure "
                  "modes", when_pass="pass.7", where="assess_prepare",
                  how="model")
    check("skips_are_tracked_with_why_when_where_how",
          cl.steps["uncommon_mistakes"].status == "skipped"
          and rec.why and rec.when_pass == "pass.7"
          and rec.where == "assess_prepare" and rec.how == "model",
          "a skip is permitted but fully attributed")

    # 7. freedom is granted only once ALL steps are resolved.
    check("freedom_is_withheld_until_all_steps_resolved",
          not cl.freedom_granted() and cl.next_preferred() is not None,
          "still steps pending -> no free choice yet")
    for k in BIAS_STEP_SEQUENCE:
        st = cl.steps[k]
        if st.status not in _RESOLVED:
            if st.status != "in_progress":
                cl.open_step(k)
            cl.close_step(k, result_good=True)
    freed = cl.freedom_granted()
    rendered2 = cl.render_for_prompt()
    check("freedom_is_granted_once_all_steps_resolved",
          freed and cl.next_preferred() is None
          and "choose the next action freely" in rendered2,
          "all resolved -> the model may choose freely")

    # 8. snapshot round-trips and skip records are searchable.
    snap = cl.snapshot()
    from ..static_architecture.store_serve import SolverStore
    store = SolverStore(core_records=[checklist_node()] + cl.skip_records())
    store.enable_tier("experimental")
    hit = store.search("why did we skip uncommon mistakes one-line task")
    check("snapshot_and_searchable_skip_records",
          snap["freedom_granted"] is True
          and snap["steps"]["research"]["status"] == "done"
          and hit["hits"] and any("biasskip." in h["record_id"]
                                  for h in hit["hits"]),
          "the frozen view embeds in the pass record; skips are learnable")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "bias_checklist_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
