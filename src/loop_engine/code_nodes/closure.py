"""Run-closure audit — fail-closed, no-orphan. Success is impossible with orphans.

Owner spec (2026-08-23): a run may not report success while required work remains
orphaned.  Every trackable thing a run produces MUST reach a TERMINAL DISPOSITION
with complete lineage before the run can close successfully:

  * an artifact -> consumed | stored | quarantined | rejected | superseded |
                   explicitly_discarded
  * a spawned Practitioner Loop -> completed | failed | cancelled | paused_durably
  * a branch -> completed | abandoned_with_reason | retained_as_named_alternative
  * a checkpoint -> closed_with_exit_evidence | abandoned_with_reason
  * a goal / blueprint item / action / task-graph execution / evaluation /
    external effect -> a recorded disposition

The audit is **fail-closed**: an item with no disposition, or with a disposition
outside its allowed set, blocks a successful close.  ``audit_run`` returns the
verdict + the exact orphan list, so closure is never a vibe — it is proven.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Item kinds a run tracks, and the terminal dispositions each may reach.
TERMINAL_DISPOSITIONS = {
    "goal": ("met", "abandoned_with_reason"),
    "blueprint_item": ("done", "abandoned_with_reason",
                       "retained_as_named_alternative"),
    "checkpoint": ("closed_with_exit_evidence", "abandoned_with_reason"),
    "action": ("completed", "failed", "superseded"),
    "task_graph": ("completed", "failed", "cancelled"),
    "spawned_practitioner": ("completed", "failed", "cancelled",
                           "paused_durably"),
    "branch": ("completed", "abandoned_with_reason",
               "retained_as_named_alternative"),
    "artifact": ("consumed", "stored", "quarantined", "rejected",
                 "superseded", "explicitly_discarded"),
    "staged_memory": ("committed", "rejected", "superseded"),
    "evaluation": ("recorded",),
    "external_effect": ("completed", "rolled_back", "recorded"),
}
ITEM_KINDS = tuple(TERMINAL_DISPOSITIONS)


@dataclass
class TrackedItem:
    kind: str
    item_id: str
    disposition: str = ""            # empty = not yet disposed (an orphan)
    lineage: tuple = ()              # the Run->Pass->...->item chain
    reason: str = ""

    def __post_init__(self):
        if self.kind not in ITEM_KINDS:
            raise ValueError(f"item kind must be one of {ITEM_KINDS}")

    def is_disposed(self) -> bool:
        return self.disposition in TERMINAL_DISPOSITIONS[self.kind]

    def is_orphan(self) -> bool:
        return not self.disposition or not self.lineage


class RunLedger:
    """Append-only ledger of tracked items; dispose() records a terminal state."""

    def __init__(self):
        self.items: dict = {}

    def track(self, kind: str, item_id: str, *, lineage: tuple = ()) -> None:
        key = (kind, item_id)
        if key not in self.items:
            self.items[key] = TrackedItem(kind, item_id, lineage=lineage)
        elif lineage and not self.items[key].lineage:
            self.items[key].lineage = lineage

    def dispose(self, kind: str, item_id: str, disposition: str, *,
                reason: str = "") -> None:
        item = self.items.get((kind, item_id))
        if item is None:
            raise KeyError(f"cannot dispose untracked item {(kind, item_id)}")
        if disposition not in TERMINAL_DISPOSITIONS[kind]:
            raise ValueError(
                f"{disposition!r} is not a terminal disposition for {kind}; "
                f"allowed: {TERMINAL_DISPOSITIONS[kind]}")
        item.disposition = disposition
        item.reason = reason


@dataclass
class ClosureVerdict:
    can_close_success: bool
    orphans: list = field(default_factory=list)      # [(kind, id, why)]
    n_items: int = 0
    n_disposed: int = 0

    def record(self) -> dict:
        return {"record_type": "run_closure_audit/v1",
                "can_close_success": self.can_close_success,
                "n_items": self.n_items, "n_disposed": self.n_disposed,
                "n_orphans": len(self.orphans),
                "orphans": [{"kind": k, "id": i, "why": w}
                            for k, i, w in self.orphans]}


def audit_run(ledger: RunLedger) -> ClosureVerdict:
    """Fail-closed no-orphan audit.  A run may close successfully ONLY when every
    tracked item has a valid terminal disposition AND complete lineage."""
    orphans: list = []
    disposed = 0
    for item in ledger.items.values():
        if not item.disposition:
            orphans.append((item.kind, item.item_id, "no disposition"))
        elif not item.is_disposed():
            orphans.append((item.kind, item.item_id,
                            f"disposition {item.disposition!r} not terminal"))
        elif not item.lineage:
            orphans.append((item.kind, item.item_id, "no lineage"))
        else:
            disposed += 1
    return ClosureVerdict(can_close_success=not orphans, orphans=orphans,
                          n_items=len(ledger.items), n_disposed=disposed)


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    LIN = ("run1", "pass3", "step_act", "action_x")

    # 1. a fully-disposed ledger can close successfully.
    led = RunLedger()
    led.track("artifact", "submission.csv", lineage=LIN)
    led.track("checkpoint", "extract_labels", lineage=LIN)
    led.dispose("artifact", "submission.csv", "stored")
    led.dispose("checkpoint", "extract_labels", "closed_with_exit_evidence")
    v = audit_run(led)
    check("a_fully_disposed_ledger_closes_successfully",
          v.can_close_success and not v.orphans and v.n_disposed == 2,
          "every item disposed with lineage -> success permitted")

    # 2. an UNDISPOSED artifact BLOCKS a successful close (fail-closed).
    led2 = RunLedger()
    led2.track("artifact", "scratch.tmp", lineage=LIN)     # never disposed
    led2.track("checkpoint", "c", lineage=LIN)
    led2.dispose("checkpoint", "c", "closed_with_exit_evidence")
    v2 = audit_run(led2)
    check("an_undisposed_artifact_blocks_a_successful_close",
          not v2.can_close_success
          and any(o[1] == "scratch.tmp" for o in v2.orphans),
          "success is impossible while an artifact is orphaned")

    # 3. a disposition OUTSIDE the allowed set is rejected at dispose time.
    led3 = RunLedger()
    led3.track("spawned_practitioner", "spawned1", lineage=LIN)
    bad = False
    try:
        led3.dispose("spawned_practitioner", "spawned1", "vanished")
    except ValueError:
        bad = True
    check("a_non_terminal_disposition_is_refused",
          bad, "a spawned Loop must be completed/failed/cancelled/paused_durably")

    # 4. an item with a disposition but NO lineage is still an orphan.
    led4 = RunLedger()
    led4.track("branch", "alt_plan")                       # no lineage
    led4.dispose("branch", "alt_plan", "retained_as_named_alternative")
    v4 = audit_run(led4)
    check("a_disposed_item_without_lineage_is_an_orphan",
          not v4.can_close_success
          and any("no lineage" in o[2] for o in v4.orphans),
          "complete lineage is required, not just a disposition")

    # 5. every item kind declares terminal dispositions; unknown kind refused.
    bad2 = False
    try:
        TrackedItem("gremlin", "x")
    except ValueError:
        bad2 = True
    check("item_kinds_and_dispositions_are_closed",
          bad2 and len(ITEM_KINDS) == 11
          and "explicitly_discarded" in TERMINAL_DISPOSITIONS["artifact"],
          "11 tracked kinds, each with a closed disposition set")

    # 6. the verdict record names every orphan for repair.
    r = v2.record()
    check("the_verdict_record_names_every_orphan",
          r["record_type"] == "run_closure_audit/v1"
          and r["n_orphans"] == 1 and r["orphans"][0]["id"] == "scratch.tmp",
          "closure is proven, never a vibe — the orphan is named")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "closure_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
