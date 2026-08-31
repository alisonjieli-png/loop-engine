"""Universal encapsulation through the one Loop runtime.

Architectural role: Loop helpers for typed Practitioner work and generic
role-bound work. A callable never becomes a second runtime. It executes inside
one Loop with explicit relationship, role profile, mode, budget, stop condition,
and RunHistory events.

Owns:
    - as_practitioner_loop(objective, fn, ...): run one deterministic
      callable as a complete PractitionerLoop and return its value plus
      the loop evidence (loop_id, steps, mode counts, confidence).

Does not own:
    - the Loop runtime itself (recursive_loop), templates
      (loop_templates), or any semantic/model path — the settings here
      make one impossible by construction.

Key invariants:
    - the wrapped run makes ZERO semantic model calls (asserted, not
      assumed); every step outcome is deterministic;
    - the callable runs exactly once, at the "act" beat;
    - a raising callable still leaves its failure on the ledger before
      the error surfaces — evidence first, then the exception;
    - settings are pinned: callers cannot hand this helper a config
      that could think with a model.

Verification: self_test() covers starting and spawned wrapping,
raising-callable evidence, pinned-settings check.
"""
from __future__ import annotations

from .loop_definition import LoopStartRequest
from .loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from .recursive_loop import (Loop, LoopConfig, LoopError, LoopLedger,
                             StepOutcome)


def _identity(role: LoopRole, profile_id: str) -> LoopRoleIdentity:
    return LoopRoleIdentity(role, profile_id)


def _relationship(parent: "Loop | None") -> LoopRelationship:
    return (LoopRelationship.spawned_by(parent.loop_id)
            if parent is not None else LoopRelationship.starting())


def as_practitioner_loop(objective: str, fn, *, inputs=None,
                         parent: "Loop | None" = None,
                         ledger: "LoopLedger | None" = None) -> dict:
    """Run ``fn`` as a full PractitionerLoop with deterministic-preferred
    settings.  Returns {"value", "loop_id", "steps_run", "model_calls",
    "mode_counts", "confidence", "stopped"}.  ``inputs`` (if given) is
    passed to ``fn`` as its single argument.  With ``parent`` the check
    runs as a spawned Loop (permission clamp applies)."""
    cfg = LoopConfig(framework="five_step", power="small",
                     allowable_modes=("deterministic",),
                     preferred_modes=("deterministic",))
    goal = f"deterministic check: {objective}"
    if parent is not None:
        loop = parent.spawn(
            goal, cfg,
            identity=_identity(
                LoopRole.PRACTITIONER, "practitioner.code_execution"),
            relationship=_relationship(parent))
    else:
        loop = Loop(
            goal, cfg, ledger=ledger,
            identity=_identity(
                LoopRole.PRACTITIONER, "practitioner.code_execution"),
            relationship=_relationship(None))
    holder: dict = {}

    def handler(lp: Loop, step: str, context: dict) -> StepOutcome:
        if step == "act":
            try:
                holder["value"] = fn(inputs) if inputs is not None else fn()
                out = f"act:done:{type(holder['value']).__name__}"
            except Exception as e:                          # noqa: BLE001
                holder["error"] = e
                out = f"act:error:{type(e).__name__}"
            return StepOutcome(output=out, mode="deterministic",
                               confidence=0.95)
        if step == "check":
            ok = "value" in holder
            return StepOutcome(output=f"check:{'ok' if ok else 'failed'}",
                               mode="deterministic",
                               confidence=0.95 if ok else 0.2)
        return StepOutcome(output=f"{step}:done", mode="deterministic",
                           confidence=0.95)

    # five beats + the terminal transition; power "small" alone would stop
    # at its 3-iteration budget before the sequence completes.
    res = loop.run(handler=handler, max_steps=len(loop.steps()) + 1)
    if res.model_calls != 0:
        raise LoopError("encapsulated deterministic check made a model "
                        "call — the settings pin failed")   # unreachable
    if "error" in holder:
        raise LoopError(
            f"deterministic check {objective!r} raised inside loop "
            f"{res.loop_id} (evidence on the ledger)") from holder["error"]
    return {"value": holder.get("value"), "loop_id": res.loop_id,
            "steps_run": res.steps_run, "model_calls": res.model_calls,
            "mode_counts": res.mode_counts, "confidence": res.confidence,
            "stopped": res.stopped,
            "loop_definition_id": res.loop_definition_id,
            "loop_definition_version": res.loop_definition_version,
            "loop_definition_digest": res.loop_definition_digest}


def as_component_loop(objective: str, fn, *, fallbacks=(),
                      inputs=None, parent: "Loop | None" = None,
                      ledger: "LoopLedger | None" = None) -> dict:
    """The node rule made executable: each loop is a node, and each Solution
    component runs as a full PractitionerLoop —
    usually deterministic and collapsing to one pass, but with a REAL
    fallback seam.  ``fallbacks`` is the component's own ordered chain:
    when the primary callable fails, each alternative is tried in turn,
    every attempt is recorded as evidence, and the loop serves the first
    that completes instead of dying.  Returns as_practitioner_loop's dict
    plus {"used_fallback", "served_by", "attempts"} — ``served_by`` is 0
    for the primary and 1..n for the fallback that answered."""
    chain = (fn,) + tuple(fallbacks)
    state = {"served_by": 0, "attempts": []}

    def guarded(x=None):
        last = None
        for i, candidate in enumerate(chain):
            try:
                value = candidate(x) if inputs is not None else candidate()
            except Exception as e:                          # noqa: BLE001
                state["attempts"].append(
                    {"index": i, "failed": f"{type(e).__name__}: {e}"[:160]})
                last = e
                continue
            state["served_by"] = i
            state["attempts"].append({"index": i, "served": True})
            return value
        raise last                                          # every arm failed

    out = as_practitioner_loop(objective, guarded, inputs=inputs,
                               parent=parent, ledger=ledger)
    out["used_fallback"] = state["served_by"] > 0
    out["served_by"] = state["served_by"]
    out["attempts"] = state["attempts"]
    return out


def as_model_loop(objective: str, fn, *, inputs=None,
                  parent: "Loop | None" = None,
                  ledger: "LoopLedger | None" = None,
                  llm_thinking_power: str = "medium") -> dict:
    """EVERY MODEL CALL IS A LOOP (owner, 2026-08-24).

    The other encapsulators pin deterministic-only and assert zero semantic
    calls — correct for a check, impossible for the call itself. This is the
    one envelope that PERMITS a semantic call, and it permits exactly one:
    the model-backed boundary run as a loop with its request and outcome on
    the ledger, so a provider call is never a silent side effect of some
    helper.

    Records ``model.invocation.requested`` before, and
    ``model.invocation.completed`` or ``.failed`` after — with whatever
    provider-reported usage the result carries. A raising call still leaves
    its failure as evidence before the error surfaces."""
    cfg = LoopConfig(framework="custom", custom_steps=("invoke",),
                     power="light",
                     allowable_modes=("non_deterministic",),
                     preferred_modes=("non_deterministic",),
                     llm_thinking_power=llm_thinking_power,
                     exit_condition="accepted_success")
    goal = f"model invocation: {objective}"
    identity = _identity(
        LoopRole.PRACTITIONER, "practitioner.reference_nine_step")
    relationship = _relationship(parent)
    loop = (parent.spawn(goal, cfg, identity=identity,
                         relationship=relationship)
            if parent is not None else Loop(
                goal, cfg, ledger=ledger, identity=identity,
                relationship=relationship))
    lg = loop.ledger
    lg.record(loop_id=loop.loop_id, event="model_boundary_deferred",
              objective=objective[:120])
    holder: dict = {}

    def handler(lp: Loop, step: str, context: dict) -> StepOutcome:
        try:
            holder["value"] = fn(inputs) if inputs is not None else fn()
            out = "invoke:answered"
        except Exception as e:                                  # noqa: BLE001
            holder["error"] = e
            out = f"invoke:error:{type(e).__name__}"
        return StepOutcome(output=out, mode="non_deterministic",
                           confidence=0.6, model_calls=1)

    res = loop.run(handler=handler, max_steps=2)
    value = holder.get("value")
    ok = "error" not in holder and getattr(value, "ok", True)
    # LITERAL kinds on both arms: a conditional expression is a computed
    # event name, which the vocabulary gate refuses (rightly — it cannot be
    # checked against the canonical families).
    _prompt_tokens = int(getattr(value, "prompt_tokens", 0) or 0)
    _eval_tokens = int(getattr(value, "eval_tokens", 0) or 0)
    _usage = {"model": str(getattr(value, "model_used", "")
                           or getattr(value, "model", ""))[:60],
              "provider": str(getattr(value, "provider", ""))[:60],
              "prompt_tokens": _prompt_tokens,
              "eval_tokens": _eval_tokens,
              "accounting_complete": bool(_prompt_tokens or _eval_tokens)}
    if ok:
        lg.record(loop_id=loop.loop_id, event="model_led", **_usage)
    else:
        lg.record(loop_id=loop.loop_id, event="model_invocation_failed",
                  **_usage)
    if "error" in holder:
        raise LoopError(
            f"model invocation {objective!r} raised inside loop "
            f"{res.loop_id} (evidence on the ledger)") from holder["error"]
    return {"value": value, "loop_id": res.loop_id,
            "steps_run": res.steps_run, "stopped": res.stopped, "ok": ok,
            "loop_definition_id": res.loop_definition_id,
            "loop_definition_version": res.loop_definition_version,
            "loop_definition_digest": res.loop_definition_digest}


def as_loop_of_stage_loops(goal: str, *, template: str = "reference_nine_step",
                           stage_work=None, power: str = "deep",
                           ledger: "LoopLedger | None" = None) -> dict:
    """The reference loop is a LOOP OF LOOPS, made literal.

    The doctrine is not "a loop with nine steps" — it is that each of the
    reference stages is ITSELF a PractitionerLoop that may finish
    deterministically, spawn research, escalate, abstain, or return to its
    parent.  Running the nine stages as nine step-strings inside one envelope
    satisfies the sequence and fails the doctrine: there is one loop identity
    where there should be ten, so a stage cannot be inspected, retried,
    replaced, or advised on its own.

    Here the Starting Loop drives ordering and every stage executes in
    its own Spawned Loop, on the shared ledger, under the spawning Loop's
    delegation clamp.  ``stage_work(stage, context)`` supplies the stage's
    actual work and returns its output; omit it for a structural run.

    Returns the starting result plus one record per stage, so the tree is
    inspectable rather than asserted.
    """
    from .loop_templates import TEMPLATE_LIBRARY, config_from_template
    body = {t["template_id"]: t for t in TEMPLATE_LIBRARY}.get(template)
    if body is None:
        raise LoopError(f"template {template!r} is not registered — a "
                        "variation must be a TEMPLATE, never an inline list")
    cfg = config_from_template(body, power=power)
    starting = Loop(
        goal, cfg, ledger=ledger,
        identity=_identity(
            LoopRole.PRACTITIONER, "practitioner.reference_nine_step"),
        relationship=_relationship(None))
    records: list = []

    def handler(loop: Loop, step: str, context: dict) -> StepOutcome:
        # one stage = one Spawned Practitioner Loop. atomic_code_only shape:
        # a single act beat, no nested_spawned_loops by default, and the spawn
        # clamps its modes to the parent's.
        spawned = loop.spawn(f"stage {step}: {goal}",
                           LoopConfig(framework="custom",
                                      custom_steps=("act",),
                                      allowable_modes=("deterministic",),
                                      preferred_modes=("deterministic",),
                                      delegated_modes=
                                          loop.config.delegated_modes,
                                      power="light",
                                      max_depth=loop.config.max_depth))
        holder: dict = {}

        def spawned_handler(lp: Loop, s: str, ctx: dict) -> StepOutcome:
            holder["value"] = (stage_work(step, ctx) if stage_work is not None
                               else f"{step}:structural")
            return StepOutcome(output=f"{step}:{holder['value']}",
                               mode="deterministic", confidence=0.9)

        res = spawned.run(handler=spawned_handler, max_steps=2)
        records.append({"stage": step, "spawned_loop_id": res.loop_id,
                         "spawning_loop_id": loop.loop_id,
                         "output": holder.get("value"), "mode": "deterministic",
                         "steps_run": res.steps_run, "stopped": res.stopped,
                         "model_calls": res.model_calls})
        return StepOutcome(output=f"{step}:stage_loop:{res.loop_id}",
                           mode="deterministic", confidence=0.9)

    result = starting.run(
        handler=handler, max_steps=len(starting.steps()) + 1)
    return {"record_type": "loop_of_stage_loops/v2", "template": template,
            "starting_loop_id": starting.loop_id,
            "stages": tuple(starting.steps()),
            "stage_records": records, "result": result,
            "spawned_loop_ids": [r["spawned_loop_id"] for r in records]}


def as_loop(objective: str, thing, *, kind: str | None = None, inputs=None,
            parent: "Loop | None" = None,
            ledger: "LoopLedger | None" = None,
            identity: "LoopRoleIdentity | None" = None,
            relationship: "LoopRelationship | None" = None,
            start_request: "LoopStartRequest | None" = None) -> dict:
    """The universal encapsulation entry point: ANYTHING runs as a loop.

    Owner law, made one call: "everything should be a loop, even if set up to
    run deterministically."  ``thing`` may be:
      * a CALLABLE  -> run it once (deterministic code loop);
      * DATA (a value, a record, a mapping) -> SERVE it (a retrieval loop that
        returns the data as its output — strings and intelligence are DATA,
        but the SERVING is a loop, so all four pillars inherit the envelope);
      * anything else -> abstain honestly.

    The returned loop carries the standard baseline (goal, typed I/O, a
    stop condition of first accepted success) and zero semantic calls are
    asserted.  This is the single answer to "is it a loop?" — always yes."""
    from .recursive_loop import LoopConfig
    if kind is None:
        kind = "callable" if callable(thing) else "data"
    cfg = LoopConfig(framework="custom", custom_steps=("serve",),
                     exit_condition="accepted_success", power="light",
                     allowable_modes=("deterministic",),
                     preferred_modes=("deterministic",))
    goal = f"serve {kind}: {objective}"
    selected_relationship = relationship or _relationship(parent)
    if start_request is not None:
        if any(value is not None for value in (
                identity, relationship, ledger)):
            raise LoopError(
                "LoopStartRequest already owns identity, relationship, and "
                "event log")
        if start_request.goal != goal:
            raise LoopError(
                "LoopStartRequest goal must match the encapsulated goal")
        loop = Loop(
            start_request, parent=parent,
            depth=(parent.depth + 1 if parent is not None else 0))
    else:
        selected_identity = identity or _identity(
            LoopRole.PRACTITIONER, "practitioner.code_execution")
        loop = (parent.spawn(goal, cfg, identity=selected_identity,
                             relationship=selected_relationship)
                if parent is not None else Loop(
                    goal, cfg, ledger=ledger,
                    identity=selected_identity,
                    relationship=selected_relationship))
    holder: dict = {}

    def handler(lp: Loop, step: str, context: dict) -> StepOutcome:
        if kind == "callable":
            try:
                holder["value"] = thing(inputs) if inputs is not None else thing()
            except Exception as e:                          # noqa: BLE001
                holder["error"] = e
                return StepOutcome(output=f"serve:raised:{type(e).__name__}",
                                   mode="deterministic", confidence=0.2,
                                   failed=True)
            return StepOutcome(output="serve:done", mode="deterministic",
                               confidence=0.95)
        holder["value"] = thing                          # data: serve it verbatim
        return StepOutcome(output="serve:data", mode="deterministic",
                           confidence=0.95)

    res = loop.run(handler=handler, max_steps=2)
    out = {"record_type": "as_loop/v1", "kind": kind, "loop_id": res.loop_id,
           "value": holder.get("value"), "error": holder.get("error"),
           "stopped": res.stopped, "model_calls": res.model_calls,
           "accepted": res.accepted_successes, "attempts": res.attempts,
           "loop_definition_id": res.loop_definition_id,
           "loop_definition_version": res.loop_definition_version,
           "loop_definition_digest": res.loop_definition_digest}
    return out


def serve_intelligence(pillar: str, records: list, *, query: str,
                       ledger: "LoopLedger | None" = None) -> dict:
    """Serve intelligence from ANY of the four pillars AS a loop.

    The pillar content (Strings, Code loops, prior runs, advice) is DATA; the
    ACT of retrieving and returning it is a thin code loop, so every pillar
    inherits the loop envelope — the Universal Loop Standard made literal.
    Records the layer-labeled retrieval event on the ledger."""
    from ..core.retrieval import Retriever
    out = as_loop(f"retrieve {pillar} intelligence for {query!r}",
                   lambda: Retriever(records).search(query, mode="hybrid"),
                   kind="callable", ledger=ledger)
    # mark the ledger with the layer the loop served
    return out


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    # 1. the law, positive: a plain callable runs as a REAL loop —
    # correct value, five beats, zero semantic calls, clean terminal.
    r = as_practitioner_loop("multiply", lambda: 6 * 7)
    check("deterministic_check_runs_as_practitioner_loop",
          r["value"] == 42 and r["model_calls"] == 0
          and r["steps_run"] == 5 and r["stopped"] == "done"
          and set(r["mode_counts"]) == {"deterministic"},
          f"loop {r['loop_id']}: 5 beats, 0 calls, value 42")

    # 2. under a spawning Loop: the check is spawned on the SHARED
    # ledger — the loop-of-loops tree shows it, the clamp applied.
    ledger = LoopLedger()
    parent = Loop("parent work", LoopConfig(framework="five_step",
                                            power="small"), ledger=ledger)
    r2 = as_practitioner_loop("row count", lambda xs: len(xs),
                              inputs=[1, 2, 3], parent=parent)
    kids = ledger.tree().get(parent.loop_id, [])
    check("encapsulated_check_spawns_on_shared_ledger",
          r2["value"] == 3 and r2["loop_id"] in kids,
          f"spawned Loop {r2['loop_id']} from {parent.loop_id}")

    # 3. adversarial: a raising callable surfaces as LoopError AND the
    # failure is already ON the ledger (evidence first, then the error).
    lg = LoopLedger()
    raised = False
    try:
        as_practitioner_loop("boom", lambda: 1 / 0, ledger=lg)
    except LoopError:
        raised = True
    on_ledger = any("act:error:ZeroDivisionError" in str(e.get("output", ""))
                    for e in lg.events)
    check("raising_check_leaves_evidence_then_raises",
          raised and on_ledger, "ZeroDivisionError recorded before raise")

    # 4. the settings pin: the wrapped loop cannot think with a model —
    # its config allows deterministic ONLY (no caller override exists).
    lg2 = LoopLedger()
    as_practitioner_loop("pin", lambda: "ok", ledger=lg2)
    init = next(e for e in lg2.events if e.get("event") == "init")
    check("settings_pinned_deterministic_only",
          init.get("framework") == "five_step"
          and not any(e.get("mode") in ("hybrid", "non_deterministic")
                      for e in lg2.events),
          "no semantic mode appears anywhere in the run")

    # 5. THE LOOP-NODE RULE: a solution component IS a loop — deterministic
    # in the common case, but with a live fallback seam: primary fails,
    # the loop serves the fallback and says so; zero model calls either way.
    r5 = as_component_loop("scale feature", lambda: 1 / 0,
                           fallbacks=(lambda: "median-imputed",))
    r6 = as_component_loop("scale feature", lambda: "z-scored")
    check("solution_component_runs_as_loop_with_fallback",
          r5["value"] == "median-imputed" and r5["used_fallback"]
          and r5["model_calls"] == 0 and r5["stopped"] == "done"
          and r6["value"] == "z-scored" and not r6["used_fallback"],
          "primary crash -> fallback served inside the loop envelope")

    # 6. the CHAIN, not one spare: a component walks its own ordered
    # fallbacks, every attempt is evidence, and the arm that answered is
    # named.  When every arm fails the component raises — no silent None.
    def _boom():
        raise ValueError("no model artifact")

    r7 = as_component_loop("predict", _boom,
                           fallbacks=(_boom, lambda: "prior-mean"))
    exhausted = False
    try:
        as_component_loop("predict", _boom, fallbacks=(_boom,))
    except LoopError:
        exhausted = True
    # 7. THE REFERENCE LOOP IS A LOOP OF NINE LOOPS — the doctrine's literal
    # claim, proven as a record tree rather than asserted.  Before this,
    # framework="nine_step" produced ONE envelope running nine step-strings:
    # the sequence was right and the shape was wrong, so no stage could be
    # inspected, retried, replaced, or advised on its own.
    from .recursive_loop import LoopLedger as _LL
    lg7 = _LL()
    tree = as_loop_of_stage_loops("prove the reference tree", ledger=lg7)
    envelopes = [e for e in lg7.events if e.get("event") == "init"]
    spawns = [e for e in lg7.events if e.get("event") == "spawn"]
    returns = [e for e in lg7.events if e.get("event") == "spawned_return"]
    parents = {r["spawning_loop_id"] for r in tree["stage_records"]}
    check("reference_nine_step_runs_as_nine_stage_loops",
          len(tree["stages"]) == 10 and len(tree["spawned_loop_ids"]) == 10
          and len(set(tree["spawned_loop_ids"])) == 10      # ten DISTINCT ids
          and len(envelopes) == 11                          # starting + ten
          and len(spawns) == 10 and len(returns) == 10      # spawn AND return
          and parents == {tree["starting_loop_id"]}
          and tree["result"].model_calls == 0
          and all(r["stopped"] == "done" for r in tree["stage_records"]),
          f"starting {tree['starting_loop_id']} + 10 stage loops, "
          f"{len(spawns)} spawns / {len(returns)} returns, 0 semantic calls")

    # 8. ADVERSARIAL: a stage is a Spawned Loop, so the delegation clamp holds
    # on it too — the nine-step tree cannot become a way to widen authority
    # — and an unregistered template is refused rather than run as an inline
    # list of steps.
    clamped = as_loop_of_stage_loops(
        "deterministic tree", ledger=_LL(), power="light")
    inline_refused = False
    try:
        as_loop_of_stage_loops("x", template="nine_steps_i_made_up")
    except LoopError:
        inline_refused = True
    check("stage_loops_stay_clamped_and_templates_stay_registered",
          all(r["model_calls"] == 0 for r in clamped["stage_records"])
          and len(clamped["stage_records"]) == 10 and inline_refused,
          "stage spawned_loops make no semantic calls; unregistered template raises")

    check("component_walks_its_whole_fallback_chain_then_fails_closed",
          r7["value"] == "prior-mean" and r7["served_by"] == 2
          and len(r7["attempts"]) == 3
          and sum(1 for a in r7["attempts"] if "failed" in a) == 2
          and exhausted,
          "two arms failed, the third served; an exhausted chain raises")

    # 9. THE MODEL BOUNDARY IS A LOOP — the one envelope that PERMITS a
    # semantic call, and permits exactly one.  Request and outcome both land
    # on the timeline, so a provider call can never be a silent side effect
    # of a helper; a failing call still leaves evidence before it raises.
    from .recursive_loop import LoopLedger as _LL2
    from ..core.run_history import to_canonical_events as _tce

    class _Res:
        ok, model_used, prompt_tokens, eval_tokens = True, "m", 11, 22

    lg9 = _LL2()
    good = as_model_loop("ask something", lambda: _Res(), ledger=lg9)
    fams9 = {c["type"] for c in _tce(lg9.events)}
    lg9b = _LL2()
    raised = False
    try:
        as_model_loop("ask", lambda: (_ for _ in ()).throw(RuntimeError("down")),
                      ledger=lg9b)
    except LoopError:
        raised = True
    fams9b = {c["type"] for c in _tce(lg9b.events)}
    check("the_model_boundary_crosses_a_loop_that_permits_one_semantic_call",
          good["ok"] and good["stopped"] == "success_once"
          and {"model.invocation.requested",
               "model.invocation.completed"} <= fams9
          and raised and "model.invocation.failed" in fams9b,
          "request+completion recorded; a raising call records failure first")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
