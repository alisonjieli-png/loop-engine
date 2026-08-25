"""User Intelligence — the fourth intelligence layer (owner, 2026-08-24).

Architectural role: Static Architecture service (the human-advice plane).

The owner's ruling: when a person watches a run and sees a loop stuck,
erroring, lagging, or simply improvable, they can click it, see what the
loop was GIVEN (input) and what it is trying to PRODUCE (expected
output), and type advice exactly as they would to a coworker on Slack —
"check out this website", "try this Python package". That advice IS an
intelligence layer: addressable at loop level, task level, run level,
and solution-component level, and loops may check for guidance before
deciding.

Owns:
    - AdviceStore: append-only JSONL of advice records (id, text, scope,
      target, author, status, timestamps) — data lives in a store, never
      in prose or code;
    - leave_advice() / advice_for() / consult(): consulting RECORDS the
      consultation (the loop's "check user guidance before deciding" is
      an auditable event, not a silent read);
    - retire_advice(): advice retires by tombstone, never by deletion.

Does not own:
    - the other three persistent layers (intelligence_layers composes all
      four), Runtime Memory (loop-to-loop notes — a different thing:
      this layer is HUMAN-to-loop), or any promotion authority — advice
      is guidance, not truth: it never bypasses gates, and acting on it
      still goes through the loop's own verification.

Public entry points:
    - AdviceStore(path).leave_advice(text, scope=..., target=...)
    - AdviceStore.consult(scope, target, loop_id=..., ledger=...)
    - advice_records_for_search(store) -> StoreRecords for the Retriever

Key invariants:
    - append-only; retirement is a status record, never a rewrite;
    - every consult is recorded (on the ledger too when one is given);
    - scopes are closed vocabulary: loop | task | run | solution_component.

Verification: self_test() — leave/consult/retire lifecycle, the ledger
event on consult, a REAL Loop checking guidance before deciding, and
scope refusal.
"""
from __future__ import annotations

import json
import os
import time

SCOPES = ("organization", "project", "task", "run", "loop", "iteration",
          "solution", "solution_loop")
#: Legacy spelling accepted on input and stored as the canonical loop-node scope.
_SCOPE_ALIASES = {"solution_component": "solution_loop"}
GUIDANCE_TYPES = ("advice", "correction", "context", "source_suggestion",
                  "package_suggestion", "priority_change", "constraint",
                  "instruction", "approval", "veto")
STRENGTHS = ("suggestion", "preference", "instruction", "constraint",
             "approval", "veto")
TIMINGS = ("immediately_if_safe", "next_safe_boundary", "before_next_retry",
           "before_verification", "future_runs_only")
RESPONSES = ("accepted", "partially_accepted", "deferred", "rejected")

#: response -> the LITERAL canonical event kind it records.  A partial
#: acceptance is recorded as an acceptance; the exact response stays on the
#: store record, so nothing is lost by the coarser event.
_RESPONSE_EVENT = {"accepted": "user_intelligence.accepted",
                   "partially_accepted": "user_intelligence.accepted",
                   "deferred": "user_intelligence.deferred",
                   "rejected": "user_intelligence.rejected"}

#: §13.2 — the authority ladder, highest first.  The first three rungs are
#: NOT user intelligence: they are the floor a person's advice can never
#: override, however strongly it is worded.  User instructions, approvals
#: and vetoes sit at rung 4; bare suggestions and preferences sit at the
#: bottom, below the loop's own template defaults.
GUIDANCE_PRECEDENCE = (
    "platform_safety_legal_security",
    "organization_policy",
    "project_hard_constraint",
    "user_instruction_approval_veto",
    "task_or_solution_requirement",
    "loop_template_default",
    "learned_routing_preference",
    "exploratory_suggestion",
)

#: which rung a piece of user advice occupies, decided by its STRENGTH —
#: never by how forcefully the text is written.
_STRENGTH_RUNG = {"veto": "user_instruction_approval_veto",
                  "approval": "user_instruction_approval_veto",
                  "instruction": "user_instruction_approval_veto",
                  "constraint": "user_instruction_approval_veto",
                  "preference": "exploratory_suggestion",
                  "suggestion": "exploratory_suggestion"}

#: narrowest scope first: a note left on THIS loop is more specific than a
#: standing organization rule, so within one rung the narrower one leads.
_SCOPE_NARROWNESS = {"iteration": 0, "loop": 1, "solution_loop": 2, "run": 3,
                     "task": 4, "solution": 5, "project": 6,
                     "organization": 7}

#: guidance types that structurally oppose each other on the same target.
#: Two vetoes agree; a veto and an approval do not.
_OPPOSED = {frozenset(("veto", "approval")),
            frozenset(("veto", "instruction")),
            frozenset(("veto", "package_suggestion")),
            frozenset(("veto", "source_suggestion"))}


def rank_guidance(advices, *, policy_floor=()) -> dict:
    """Order applicable guidance by the §13.2 ladder and SURFACE conflicts.

    ``policy_floor`` carries the rungs above user intelligence — platform
    safety, organization policy, project hard constraints — as records with
    a ``rung`` in GUIDANCE_PRECEDENCE.  They are merged into the same
    ordering, which is what makes the safety property structural rather
    than hoped-for: no user record can sort above a floor record, whatever
    its strength.

    Nothing is ever dropped.  Opposed advice on one target is returned in
    ``conflicts`` with both sides intact, because the directive forbids
    silently discarding one side of a disagreement.
    """
    rows = []
    for p in policy_floor:
        rung = p.get("rung", "platform_safety_legal_security")
        if rung not in GUIDANCE_PRECEDENCE:
            raise ValueError(f"policy rung {rung!r} not in the ladder")
        if GUIDANCE_PRECEDENCE.index(rung) >= GUIDANCE_PRECEDENCE.index(
                "user_instruction_approval_veto"):
            raise ValueError(
                f"policy floor entry {p.get('rule')!r} claims rung {rung!r}, "
                "which is at or below user intelligence — the floor is the "
                "three rungs ABOVE it")
        rows.append({"source": "policy", "record": p, "rung": rung,
                     "rung_index": GUIDANCE_PRECEDENCE.index(rung),
                     "narrowness": -1, "ts": 0.0})
    for a in advices:
        rung = _STRENGTH_RUNG.get(a.get("strength", "suggestion"),
                                  "exploratory_suggestion")
        rows.append({"source": "user", "record": a, "rung": rung,
                     "rung_index": GUIDANCE_PRECEDENCE.index(rung),
                     "narrowness": _SCOPE_NARROWNESS.get(a.get("scope"), 9),
                     "ts": float(a.get("ts", 0.0))})
    # rung first, then the narrower scope, then the more recent record
    rows.sort(key=lambda r: (r["rung_index"], r["narrowness"], -r["ts"]))

    conflicts = []
    users = [r for r in rows if r["source"] == "user"]
    for i, a in enumerate(users):
        for b in users[i + 1:]:
            if a["record"].get("target") != b["record"].get("target"):
                continue
            pair = frozenset((a["record"].get("guidance_type"),
                              b["record"].get("guidance_type")))
            if pair in _OPPOSED:
                conflicts.append({
                    "target": a["record"].get("target"),
                    "advice_ids": [a["record"].get("advice_id"),
                                   b["record"].get("advice_id")],
                    "guidance_types": sorted(pair),
                    "leads": (a if a["rung_index"] < b["rung_index"]
                              or (a["rung_index"] == b["rung_index"]
                                  and a["ts"] >= b["ts"])
                              else b)["record"].get("advice_id"),
                    "note": "both preserved — a loop must surface this, not "
                            "silently pick one"})
    return {"record_type": "guidance_ranking/v1", "ordered": rows,
            "conflicts": conflicts,
            "highest_rung": rows[0]["rung"] if rows else None,
            "user_records_above_the_floor": [
                r["record"].get("advice_id") for r in rows
                if r["source"] == "user"
                and r["rung_index"] < min(
                    [p["rung_index"] for p in rows if p["source"] == "policy"],
                    default=len(GUIDANCE_PRECEDENCE))]}


class AdviceStore:
    """Append-only user-advice store over one JSONL file."""

    def __init__(self, path: str):
        self.path = path

    def _append(self, rec: dict) -> dict:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def _rows(self) -> list:
        if not os.path.exists(self.path):
            return []
        return [json.loads(l) for l in open(self.path) if l.strip()]

    def leave_advice(self, text: str, *, scope: str, target: str,
                     author: str = "user", guidance_type: str = "advice",
                     strength: str = "suggestion",
                     timing: str = "next_safe_boundary") -> dict:
        scope = _SCOPE_ALIASES.get(scope, scope)
        if scope not in SCOPES:
            raise ValueError(f"advice scope {scope!r} not in {SCOPES}")
        if guidance_type not in GUIDANCE_TYPES:
            raise ValueError(f"guidance_type {guidance_type!r} not in "
                             f"{GUIDANCE_TYPES}")
        if strength not in STRENGTHS or timing not in TIMINGS:
            raise ValueError("unknown strength or timing")
        if not text.strip():
            raise ValueError("empty advice is refused")
        # millisecond time alone collides when a person (or a test) leaves
        # two notes in the same tick, and a collided id would let one
        # response or retirement land on BOTH records.  The per-store
        # counter makes identity unique without needing a clock guarantee.
        if not hasattr(self, "_seq"):       # seeded from what is already
            self._seq = sum(1 for r in self._rows()   # on disk, so a
                            if r.get("kind") == "user_advice")  # reopened
        self._seq += 1                                          # store
        # cannot restart its numbering into an existing id.
        rec = {"kind": "user_advice",
               "advice_id": f"adv-{int(time.time()*1000):x}-{self._seq:03d}",
               "text": text.strip(), "scope": scope, "target": target,
               "author": author, "guidance_type": guidance_type,
               "strength": strength, "timing": timing,
               "status": "submitted", "ts": time.time()}
        return self._append(rec)

    def respond(self, advice_id: str, response: str, *, reason: str = "",
                loop_id: str = "", ledger=None) -> dict:
        """The LOOP'S answer to a piece of guidance — accepted, partially
        accepted, deferred, or rejected, always with the reason on the
        record and (when a ledger is given) as a canonical
        user_intelligence.<response> event. Append-only: the response is
        a new record, never an edit of the advice."""
        if response not in RESPONSES:
            raise ValueError(f"response {response!r} not in {RESPONSES}")
        rec = self._append({"kind": "advice_response",
                            "advice_id": advice_id, "response": response,
                            "reason": reason, "loop_id": loop_id,
                            "ts": time.time()})
        if ledger is not None:
            # LITERAL kinds, resolved through a closed map: a computed event
            # name cannot be checked against the canonical vocabulary, so the
            # conformance gate refuses one (it is how an untyped family
            # reaches a consumer unnoticed).
            ledger.record(loop_id=loop_id, event=_RESPONSE_EVENT[response],
                          advice_id=advice_id, reason=reason[:120])
        return rec

    def responses_for(self, advice_id: str) -> list:
        return [r for r in self._rows()
                if r.get("kind") == "advice_response"
                and r["advice_id"] == advice_id]

    def retire_advice(self, advice_id: str, reason: str = "") -> dict:
        return self._append({"kind": "advice_retired", "advice_id": advice_id,
                             "reason": reason, "ts": time.time()})

    def advice_for(self, scope: str, target: str) -> list:
        retired = {r["advice_id"] for r in self._rows()
                   if r.get("kind") == "advice_retired"}
        return [r for r in self._rows()
                if r.get("kind") == "user_advice" and r["scope"] == scope
                and r["target"] == target and r["advice_id"] not in retired]

    def consult(self, scope: str, target: str, *, loop_id: str = "",
                ledger=None) -> list:
        """The loop's guidance check: returns active advice AND records
        the consultation — on the store, and on the loop's ledger when
        one is given, so 'did the loop check?' is always answerable."""
        hits = self.advice_for(scope, target)
        self._append({"kind": "advice_consulted", "scope": scope,
                      "target": target, "loop_id": loop_id,
                      "advice_ids": [h["advice_id"] for h in hits],
                      "ts": time.time()})
        if ledger is not None:
            ledger.record(loop_id=loop_id, event="user_guidance",
                          scope=scope, target=target,
                          advice_count=len(hits),
                          advice_ids=[h["advice_id"] for h in hits])
        return hits


def resolve_user_intelligence(store: "AdviceStore", targets: dict, *,
                              loop_id: str = "", ledger=None,
                              policy_floor=()) -> dict:
    """The UserIntelligenceSnapshot resolver — and per the live-runtime
    directive it RUNS AS a thin deterministic PractitionerLoop (one
    logical resolution loop, zero model calls; physically it is one
    encapsulated pass — sanctioned fusion with identity). ``targets``
    maps scope -> target id; every scope consulted is recorded.

    The snapshot arrives RANKED by the §13.2 ladder with conflicts
    surfaced, so a loop reads guidance in authority order instead of in
    whatever order the file happened to hold, and can never quietly act on
    one half of a disagreement."""
    from ..loop.encapsulate import as_practitioner_loop

    def _resolve():
        snapshot = []
        for scope, target in targets.items():
            snapshot.extend(store.consult(scope, target, loop_id=loop_id,
                                          ledger=ledger))
        return snapshot

    out = as_practitioner_loop("resolve user intelligence", _resolve,
                               ledger=ledger)
    ranking = rank_guidance(out["value"], policy_floor=policy_floor)
    if ledger is not None and out["value"]:
        ledger.record(loop_id=loop_id, event="user_intelligence.attached",
                      advice_count=len(out["value"]),
                      highest_rung=ranking["highest_rung"],
                      conflicts=len(ranking["conflicts"]))
    return {"snapshot": out["value"], "resolver_loop_id": out["loop_id"],
            "model_calls": out["model_calls"],
            "ordered": ranking["ordered"], "conflicts": ranking["conflicts"],
            "highest_rung": ranking["highest_rung"]}


def advice_records_for_search(store: "AdviceStore") -> list:
    """Advice as StoreRecords, so the fourth layer rides the one
    Retriever exactly like the other three."""
    from .store_serve import StoreRecord
    from .facets import string_facets
    rows = store._rows()
    retired = {r.get("advice_id") for r in rows
               if r.get("kind") == "advice_retired"}
    return [StoreRecord(
                r["advice_id"], "context", r["text"],
                body={"scope": r["scope"], "target": r["target"],
                      "author": r["author"],
                      "guidance_type": r.get("guidance_type", "advice"),
                      "strength": r.get("strength", "suggestion"),
                      "timing": r.get("timing", "next_safe_boundary"),
                      "status": r.get("status", "submitted"),
                      "ts": r.get("ts"),
                      "facets": string_facets(
                          category="user_guidance",
                          subcategory=r.get("guidance_type", "advice"),
                          scope=r["scope"],
                          lifecycle=r.get("status", "submitted"),
                          provenance="human")},
                tags=("user_guidance", r.get("guidance_type", "advice"),
                      r.get("strength", "suggestion"), r["scope"]))
            for r in rows
            if r.get("kind") == "user_advice"
            and r.get("advice_id") not in retired]


def self_test() -> dict:
    import tempfile
    from ..loop.recursive_loop import Loop, LoopConfig, LoopLedger, StepOutcome
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    store = AdviceStore(os.path.join(tempfile.mkdtemp(prefix="uadv_"),
                                     "user_advice.jsonl"))

    # 1. leave -> consult -> retire lifecycle, append-only.
    a = store.leave_advice("Try the rapidfuzz package for the alias step.",
                           scope="loop", target="loop7")
    hits = store.advice_for("loop", "loop7")
    store.retire_advice(a["advice_id"], "superseded")
    after = store.advice_for("loop", "loop7")
    check("advice_lifecycle_append_only",
          len(hits) == 1 and hits[0]["text"].startswith("Try the rapidfuzz")
          and after == [] and len(store._rows()) == 2,
          "leave + tombstone — two appended rows, zero rewrites")

    # 2. a REAL Loop checks user guidance BEFORE deciding: the handler
    # consults at the choose step; the ledger records the check and the
    # advice shapes the step's output.
    store2 = AdviceStore(os.path.join(tempfile.mkdtemp(prefix="uadv_"),
                                      "a.jsonl"))
    store2.leave_advice("Check out the winning write-up before modeling.",
                        scope="task", target="demo-task")
    ledger = LoopLedger()

    def handler(lp, step, ctx):
        if step == "choose":
            g = store2.consult("task", "demo-task", loop_id=lp.loop_id,
                               ledger=lp.ledger)
            note = g[0]["text"][:40] if g else "no guidance"
            return StepOutcome(output=f"choose:guided:{note}",
                               mode="deterministic", confidence=0.9)
        return StepOutcome(output=f"{step}:done", mode="deterministic",
                           confidence=0.9)

    Loop("guided run", LoopConfig(framework="five_step", power="small"),
         ledger=ledger).run(handler=handler, max_steps=6)
    guided = [e for e in ledger.events if e.get("event") == "user_guidance"]
    shaped = any("choose:guided:Check out the winning" in str(e.get("output"))
                 for e in ledger.events)
    check("loop_checks_user_guidance_before_deciding",
          len(guided) == 1 and guided[0]["advice_count"] == 1 and shaped,
          "user_guidance event on the ledger; advice shaped the decision")

    # 3. the fourth layer rides the one Retriever like the other three.
    from .retrieval import Retriever
    recs = advice_records_for_search(store2)
    r = Retriever(recs)
    h = r.search("winning write-up", mode="lexical")
    check("advice_searchable_through_one_retriever",
          h["hits"] and h["hits"][0]["record_id"].startswith("adv-")
          and recs[0].body["guidance_type"] == "advice"
          and recs[0].body["strength"] == "suggestion"
          and recs[0].body["facets"]["category"] == "user_guidance")
    check("retired_advice_is_not_searchable",
          advice_records_for_search(store) == [],
          "retirement tombstone removes advice from the active search view")

    # 4. closed scope vocabulary + empty advice refused.
    refused = 0
    for bad in ({"text": "x", "scope": "vibes", "target": "t"},
                {"text": "   ", "scope": "loop", "target": "t"}):
        try:
            store.leave_advice(bad["text"], scope=bad["scope"],
                               target=bad["target"])
        except ValueError:
            refused += 1
    check("bad_scope_and_empty_advice_refused", refused == 2)

    # 5. THE FULL RECORD (live-runtime directive): guidance type,
    # strength, timing stored; the LOOP'S RESPONSE is append-only
    # evidence with a canonical event; legacy scope spelling accepted.
    s5 = AdviceStore(os.path.join(tempfile.mkdtemp(prefix="uadv_"),
                                  "r.jsonl"))
    a5 = s5.leave_advice("Use the deterministic parser first.",
                         scope="solution_component", target="sl-parse",
                         guidance_type="instruction", strength="instruction",
                         timing="before_verification")
    lg5 = LoopLedger()
    s5.respond(a5["advice_id"], "accepted", reason="parser swapped",
               loop_id="loop9", ledger=lg5)
    resp = s5.responses_for(a5["advice_id"])
    check("full_record_and_loop_response_lifecycle",
          a5["scope"] == "solution_loop"
          and a5["guidance_type"] == "instruction"
          and a5["timing"] == "before_verification"
          and len(resp) == 1 and resp[0]["response"] == "accepted"
          and any(e.get("event") == "user_intelligence.accepted"
                  for e in lg5.events),
          "legacy scope aliased; response recorded on store + ledger")

    # 6. the snapshot resolver runs AS a thin deterministic loop.
    s6 = AdviceStore(os.path.join(tempfile.mkdtemp(prefix="uadv_"),
                                  "s.jsonl"))
    s6.leave_advice("check the winning write-up", scope="task", target="t1")
    lg6 = LoopLedger()
    snap = resolve_user_intelligence(s6, {"task": "t1", "run": "r1"},
                                     loop_id="loop2", ledger=lg6)
    check("snapshot_resolution_is_a_thin_deterministic_loop",
          len(snap["snapshot"]) == 1 and snap["model_calls"] == 0
          and snap["resolver_loop_id"]
          and sum(1 for e in lg6.events
                  if e.get("event") == "user_guidance") == 2,
          f"resolver loop {snap['resolver_loop_id']}: 2 scopes consulted, "
          "0 model calls")

    # 7. §13.2 THE LADDER: a person's advice is ordered by its STRENGTH,
    # not by how forcefully it is written, and within one rung the narrower
    # scope leads.  An instruction on this loop outranks an organization
    # suggestion even though the suggestion is older and broader.
    s7 = AdviceStore(os.path.join(tempfile.mkdtemp(prefix="uadv_"),
                                  "s.jsonl"))
    org = s7.leave_advice("prefer speed over accuracy", scope="organization",
                          target="acme", strength="suggestion")
    here = s7.leave_advice("do not ship without the leakage check",
                           scope="loop", target="loop9",
                           guidance_type="instruction", strength="instruction")
    ranked = rank_guidance([org, here])
    order = [r["record"]["advice_id"] for r in ranked["ordered"]]
    check("guidance_is_ordered_by_authority_then_specificity",
          order == [here["advice_id"], org["advice_id"]]
          and ranked["highest_rung"] == "user_instruction_approval_veto"
          and len(ranked["ordered"]) == 2,
          "instruction-on-this-loop leads a broad organization suggestion")

    # 8. ADVERSARIAL — THE FLOOR HOLDS: a veto is the strongest thing a
    # person can write, and it still cannot sort above platform safety,
    # organization policy, or a project hard constraint.  A "policy" that
    # tries to claim a rung at or below user intelligence is refused, so
    # the floor cannot be forged downward either.
    veto = s7.leave_advice("skip the safety validator entirely", scope="loop",
                           target="loop9", guidance_type="veto",
                           strength="veto")
    floor = [{"rule": "never disable the safety validator",
              "rung": "platform_safety_legal_security"},
             {"rule": "customer data stays in region",
              "rung": "organization_policy"}]
    with_floor = rank_guidance([veto, here, org], policy_floor=floor)
    top_two = [r["source"] for r in with_floor["ordered"][:2]]
    forged = False
    try:
        rank_guidance([veto], policy_floor=[{"rule": "fake",
                                             "rung": "loop_template_default"}])
    except ValueError:
        forged = True
    check("no_user_record_outranks_the_policy_floor",
          top_two == ["policy", "policy"]
          and with_floor["user_records_above_the_floor"] == []
          and forged,
          "a veto sorts below both floor rungs; a forged floor rung raises")

    # 9. CONFLICTS ARE SURFACED, NEVER RESOLVED AWAY: opposed guidance on
    # one target keeps both sides and says which leads.
    conf = rank_guidance([veto, s7.leave_advice(
        "go ahead and ship it", scope="loop", target="loop9",
        guidance_type="approval", strength="approval")])
    check("opposed_guidance_is_preserved_and_surfaced",
          len(conf["conflicts"]) == 1
          and sorted(conf["conflicts"][0]["guidance_types"])
          == ["approval", "veto"]
          and len(conf["ordered"]) == 2
          and conf["conflicts"][0]["leads"],
          "veto vs approval on one loop: both kept, the leader named")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


def propose_generalization(store: "AdviceStore", advice_ids, *,
                           rationale: str = "", ledger=None) -> dict:
    """Propose that repeatedly-accepted advice become reusable intelligence.

    The system may PROPOSE a generalization derived from advice that kept
    working; it may never rewrite the original user record, and it may never
    promote its own proposal. This records the proposal — a candidate, with
    the source advice named so the human who wrote it stays attributable."""
    ids = [str(a) for a in advice_ids]
    rec = {"record_type": "user_intelligence_generalization/v1",
           "from_advice": ids, "rationale": str(rationale)[:200],
           "status": "candidate",
           "note": "a proposal, not a promotion; the original advice is "
                   "unchanged and its author stays attributed"}
    if ledger is not None:
        ledger.record(loop_id="", event="user_intelligence_generalized",
                      from_advice=len(ids), rationale=rec["rationale"][:80])
    return rec
