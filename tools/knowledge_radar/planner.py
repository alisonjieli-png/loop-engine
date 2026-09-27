"""Choose which questions one run answers, within a budget, and give each a stable work identity.

A question is selected when it has never been answered (first run), when its
refresh cadence has passed (overdue), when a source it reads changed after it
was last answered (changed source), when customers asked for it (demand), or,
for a small declared share of the budget, to explore a question that is not
due yet. Everything else is deferred with the day it becomes due.

The work identity of a question is the digest of its declared record (its
constraints), the run day and the evidence version (the change times of the
local sources it reads). Two requests with the same identity are the same
work: the second attaches to the first instead of starting another. Text
similarity alone never merges two questions.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date

from .records import PLAN_RECORD_TYPE, REFRESH_DAYS, STORED

LOCAL_SIGNAL_ENGINES = ("collector_state", "model_directory", "mcp_directory", "endpoint_directory")


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def work_identity(question, as_of: str, evidence: dict) -> str:
    engines = sorted({binding.engine for binding in question.sources})
    return digest({"question": question.to_dict(), "as_of": as_of,
                   "evidence": {engine: evidence.get(engine) for engine in engines}})


def _days_between(earlier: str, later: str) -> int:
    return (date.fromisoformat(later[:10]) - date.fromisoformat(earlier[:10])).days


def plan(registry, state: dict, as_of: str, *, evidence: "dict | None" = None, demand: "dict | None" = None,
         only: "tuple | None" = None, maximum: "int | None" = None, asset_digests: "dict | None" = None) -> dict:
    """The knowledge_radar_plan/v1 of one run. ``state`` maps question ids to their last build record.

    ``asset_digests`` maps a question to the digest of the helper and tool assets it delivers, so a changed
    asset re-packages only the questions that deliver it.
    """
    evidence = evidence or {}
    demand = demand or {}
    asset_digests = asset_digests or {}
    budget = maximum if maximum is not None else registry.planner.maximum_questions
    selected, deferred, candidates = [], [], []
    for question in registry.questions:
        if only and question.id not in only:
            continue
        if question.status != "active":
            deferred.append({"question_id": question.id, "reason": "declared_gap", "detail": question.gap_reason})
            continue
        last = (state.get(question.id) or {}).get("last_built_as_of")
        stored = any(kind in STORED for kind in question.delivery)
        if last is None:
            candidates.append((0, question, "first_run", "never answered"))
            continue
        age = _days_between(last, as_of)
        due_in = REFRESH_DAYS[question.refresh] - age
        changed = [binding.engine for binding in question.sources if binding.engine in LOCAL_SIGNAL_ENGINES
                   and (evidence.get(binding.engine) or "") > (state.get(question.id) or {}).get("last_built_at", "")]
        asset_changed = asset_digests.get(question.id) not in (None, (state.get(question.id) or {}).get("asset_digest"))
        if asset_changed:
            changed.append("assets")
        if stored and due_in <= 0:
            candidates.append((1, question, "overdue", f"last answered {last}, refresh {question.refresh}"))
        elif changed and (stored or asset_changed):
            candidates.append((2, question, "changed_source", "changed since the last answer: " + ", ".join(sorted(set(changed)))))
        elif demand.get(question.id, 0) > 0:
            candidates.append((3, question, "demand", f"demand weight {demand[question.id]}"))
        else:
            candidates.append((9, question, "not_due", f"due in {max(due_in, 0)} days"))
    ordered = sorted(candidates, key=lambda item: (item[0], -demand.get(item[1].id, 0), item[1].id))
    due = [item for item in ordered if item[0] < 9]
    rest = [item for item in ordered if item[0] == 9]
    exploration = int(budget * registry.planner.exploration_share) if rest else 0
    main = due[:max(0, budget - exploration)] if len(due) > budget - exploration else due
    room = budget - len(main)
    explored = sorted(rest, key=lambda item: digest([as_of, item[1].id]))[:min(exploration, room)] if room > 0 else []
    for rank, question, reason, detail in main:
        selected.append({"question_id": question.id, "reason": reason, "detail": detail,
                         "work_identity": work_identity(question, as_of, evidence)})
    for rank, question, reason, detail in explored:
        selected.append({"question_id": question.id, "reason": "exploration", "detail": detail,
                         "work_identity": work_identity(question, as_of, evidence)})
    chosen = {row["question_id"] for row in selected}
    for rank, question, reason, detail in ordered:
        if question.id not in chosen:
            deferred.append({"question_id": question.id, "reason": "over_budget" if rank < 9 else reason, "detail": detail})
    record = {"record_type": PLAN_RECORD_TYPE, "as_of": as_of, "registry_version": registry.registry_version,
              "budget": budget, "exploration_share": registry.planner.exploration_share,
              "evidence_version": {engine: evidence.get(engine) for engine in sorted(evidence)},
              "selected": selected, "deferred": sorted(deferred, key=lambda row: row["question_id"])}
    record["plan_identity"] = digest({key: value for key, value in record.items() if key != "deferred"})
    return record
