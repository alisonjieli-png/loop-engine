"""The four intelligence layers — one queryable knowledge surface.

Architectural role: Static Architecture service (the formalized knowledge
plane: the owner's three persistent pillars of 2026-08-24 — string, code,
previous run & solution — extended the same day with the FOURTH layer,
User Intelligence: human advice on loops/tasks/runs/solution components).

Owns:
    - the canonical layer vocabulary (LAYERS) and its plain meanings:
      string_intelligence (questions, prompts, personas, timeframes,
      templates — everything appended to a model's context; template
      STRINGS live here), code_intelligence (runnable Code Nodes,
      deterministic and non-deterministic alike — prompt-engineering
      operations and template EXECUTORS live here), and
      past_run_intelligence (previous Loop Engine solutions and runs served
      as searchable starting points, prior-not-proof);
    - query_intelligence(): ONE query fanned across the layers through
      the one Retriever, every hit labeled with the layer that served it;
    - the layer handshake, including the state of runtime memory (the
      loop-to-loop note board): BUILT and run-scoped, in
      runtime_memory.RunNoteBoard — an ambient write with no board still
      refuses, because there is deliberately no global board.

Does not own:
    - the stores themselves (string bank/seed pack via string_foundry,
      code cards via capability_directory, solutions via
      solution_library) or the retrieval engines (retrieval.py) — this
      module composes them and never forks a second search path.

Public entry points:
    - query_intelligence(need, layer_records, ...) -> labeled hits
    - layer_handshake() -> the four layers + runtime-memory state
    - runtime_memory_write(...) -> ALWAYS refuses (fail closed until the
      note board exists; absence is explicit, never a silent no-op)

Key invariants:
    - exactly FOUR layers, spelled from LAYERS (the fourth, user
      intelligence, was the owner's 2026-08-24 decision) — a fifth
      bucket is a new owner decision, not a code change;
    - every hit names its layer (search provenance);
    - runtime memory refuses writes until implemented.

Verification: self_test() — labeled fan-out, per-layer routing, the
runtime-memory refusal, and the three-layer invariant.
"""
from __future__ import annotations

LAYERS = ("string_intelligence", "code_intelligence", "past_run_intelligence",
          "user_intelligence")

#: product-facing names (correction directive 2026-08-24 §9): internal
#: tokens stay stable; every human surface uses these labels. The third
#: pillar's canonical product name is "Previous Run & Solution
#: Intelligence" (short UI label: "Run & Solution Intelligence").
LAYER_PUBLIC_LABEL = {
    "string_intelligence": "String Intelligence",
    "code_intelligence": "Code Intelligence",
    "past_run_intelligence": "Previous Run & Solution Intelligence",
    "user_intelligence": "User Intelligence",
}
LAYER_SHORT_LABEL = {
    "string_intelligence": "String Intelligence",
    "code_intelligence": "Code Intelligence",
    "past_run_intelligence": "Run & Solution Intelligence",
    "user_intelligence": "User Intelligence",
}

#: plain-English meaning of each layer, served with every handshake so a
#: reader never needs this file to understand a result.
LAYER_MEANING = {
    "string_intelligence": ("passive context the loop can pull in: questions, "
                            "prompts, personas, timeframes, evaluations, "
                            "template strings"),
    "code_intelligence": ("runnable Code Nodes, deterministic and "
                          "non-deterministic — fast, repeatable work "
                          "including prompt-engineering operations"),
    "past_run_intelligence": ("previous runs AND solutions: loop trees, "
                              "decisions and alternatives, failures and "
                              "repairs, costs, model-call history, prior and "
                              "candidate Solutions, component performance, "
                              "warm-start evidence — a prior, never proof"),
    "user_intelligence": ("advice humans leave on loops, tasks, runs, and "
                          "solution components — like advising a coworker; "
                          "loops may consult it before deciding; guidance, "
                          "never truth, and never a gate bypass"),
}


def layer_handshake() -> dict:
    """What the knowledge plane offers, honestly."""
    return {"layers": [{"layer": l, "public_label": LAYER_PUBLIC_LABEL[l],
                        "short_label": LAYER_SHORT_LABEL[l],
                        "meaning": LAYER_MEANING[l],
                        "queryable": True} for l in LAYERS],
            "runtime_memory": {
                "meaning": "the loop-to-loop note board (any loop writes a "
                           "note, any loop reads)",
                "state": "built_run_scoped",
                "where": "static_architecture/runtime_memory.RunNoteBoard",
                "writes": "through a run's board only — ambient writes "
                          "without a board still refuse (no global state)"}}


def runtime_memory_write(note: str, board=None, *, loop_id: str = "",
                         topic: str = "general") -> dict:
    """Write to Runtime Memory through a run's board. Without a board the
    write still refuses loudly — there is deliberately NO ambient global
    board, so a note can never land outside its run's scope."""
    if board is None:
        raise NotImplementedError(
            "runtime memory is run-scoped — pass the run's RunNoteBoard "
            "(static_architecture/runtime_memory); ambient writes refuse "
            "so nothing lands outside its run")
    return board.write(note, loop_id=loop_id, topic=topic)


def query_intelligence(need: str, layer_records: dict, *,
                       mode: str = "lexical", top_n: int = 3) -> dict:
    """Fan ONE semantic need across the four layers through the one
    Retriever. ``layer_records`` maps layer name -> list of StoreRecords
    (missing layers are reported as unqueried, never silently skipped).
    Returns {"need", "hits": [... each with "layer" ...], "unqueried"}."""
    from .retrieval import Retriever
    unknown = set(layer_records) - set(LAYERS)
    if unknown:
        raise ValueError(f"unknown intelligence layers {sorted(unknown)} — "
                         f"the four layers are {LAYERS}")
    hits, unqueried = [], []
    for layer in LAYERS:
        recs = layer_records.get(layer)
        if not recs:
            unqueried.append(layer)
            continue
        res = Retriever(recs).search(need, mode=mode, top_n=top_n)
        for h in res["hits"]:
            hits.append({**h, "layer": layer})
    hits.sort(key=lambda h: -h.get("score", 0.0))
    return {"need": need, "hits": hits, "unqueried": unqueried}


def self_test() -> dict:
    from .store_serve import StoreRecord
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    strings = [StoreRecord("s.persona", "context",
                           "adopt a statistician persona for review",
                           body={}, tags=("persona",))]
    code = [StoreRecord("n.dedupe", "node",
                        "deterministic duplicate row remover",
                        body={}, tags=("dedupe",))]
    runs = [StoreRecord("sol.titanic", "strategy",
                        "prior solution: titanic survival gradient boosting",
                        body={}, tags=("prior",))]
    advice = [StoreRecord("adv.pkg", "context",
                          "user advice: try the rapidfuzz package here",
                          body={}, tags=("user_advice",))]
    packs = {"string_intelligence": strings, "code_intelligence": code,
             "past_run_intelligence": runs, "user_intelligence": advice}

    # 1. one need fans across all four layers; every hit is layer-labeled.
    out = query_intelligence("duplicate row remover", packs)
    check("hits_are_layer_labeled",
          out["hits"] and all("layer" in h for h in out["hits"])
          and out["hits"][0]["layer"] == "code_intelligence"
          and out["hits"][0]["record_id"] == "n.dedupe",
          f"top: {out['hits'][0]['record_id'] if out['hits'] else 'none'}")

    # 2. a string-flavored need routes to the string layer; a prior-solution
    # need routes to past runs — three DISTINCT buckets, not one soup.
    a = query_intelligence("statistician persona", packs)
    b = query_intelligence("prior solution titanic survival", packs)
    c = query_intelligence("user advice rapidfuzz", packs)
    check("needs_route_to_their_layers",
          a["hits"] and a["hits"][0]["layer"] == "string_intelligence"
          and b["hits"] and b["hits"][0]["layer"] == "past_run_intelligence"
          and c["hits"] and c["hits"][0]["layer"] == "user_intelligence")

    # 3. a missing layer is REPORTED, never silently skipped; an unknown
    # bucket is refused (the FOUR layers are an owner decision).
    partial = query_intelligence("anything", {"code_intelligence": code})
    refused = False
    try:
        query_intelligence("x", {"vibes_intelligence": code})
    except ValueError:
        refused = True
    check("missing_layer_reported_unknown_layer_refused",
          set(partial["unqueried"]) == {"string_intelligence",
                                        "past_run_intelligence",
                                        "user_intelligence"} and refused)

    # 4. runtime memory: BUILT run-scoped; ambient writes (no board)
    # still refuse; with a board the write lands.
    from .runtime_memory import RunNoteBoard
    hs = layer_handshake()
    rm_refused = False
    try:
        runtime_memory_write("note")
    except NotImplementedError:
        rm_refused = True
    wrote = runtime_memory_write("note", RunNoteBoard("t"), loop_id="l1")
    rm_refused = rm_refused and wrote["note"] == "note"
    check("public_labels_ride_the_handshake",
          hs["layers"][2]["public_label"]
          == "Previous Run & Solution Intelligence"
          and all("public_label" in l and "short_label" in l
                  for l in hs["layers"]))

    check("runtime_memory_is_built_run_scoped_ambient_writes_refused",
          len(hs["layers"]) == 4
          and hs["runtime_memory"]["state"] == "built_run_scoped"
          and rm_refused)

    # 5. THE FOUR-PILLAR CANARY: ONE need, ONE query, all four persistent
    # layers populated and searched together — then a real loop consumes a
    # selected hit and records WHY the alternatives were not taken.  A
    # federated search that nobody acts on proves retrieval, not use.
    from ..loop.recursive_loop import Loop, LoopConfig, LoopLedger, StepOutcome
    need = "handle duplicate rows before scoring"
    corpus = {
        "string_intelligence": [
            StoreRecord("s.dupes", "question",
                        "have duplicate rows been removed before scoring",
                        body={}, tags=("data_quality",))],
        "code_intelligence": [
            StoreRecord("n.dedupe2", "node",
                        "deterministic duplicate row remover before scoring",
                        body={"kind": "node"}, tags=("dedupe",))],
        "past_run_intelligence": [
            StoreRecord("r.run7", "strategy",
                        "a previous run removed duplicate rows and scored "
                        "higher", body={}, tags=("prior",))],
        "user_intelligence": [
            StoreRecord("adv.1", "context",
                        "duplicate rows here are legitimate repeat orders — "
                        "do not drop them", body={}, tags=("user_advice",))]}
    fed = query_intelligence(need, corpus, top_n=3)
    layers_hit = {h["layer"] for h in fed["hits"]}

    lg5 = LoopLedger()
    consumed: dict = {}

    def h5(lp, step, ctx):
        if step == "act":
            # the loop CONSUMES the top hit and records the rejects with a
            # reason — selection without a rejection record is not a decision.
            top = fed["hits"][0]
            consumed["used"] = top["record_id"]
            consumed["rejected"] = [
                {"record_id": o["record_id"], "layer": o["layer"],
                 "reason": "lower score for this need"}
                for o in fed["hits"][1:]]
            lp.ledger.record(loop_id=lp.loop_id, event="intelligence_pull",
                             layer=top["layer"].replace("_intelligence", ""),
                             record_id=top["record_id"],
                             rejected=len(consumed["rejected"]))
            return StepOutcome(output=f"act:used:{top['record_id']}",
                               mode="deterministic", confidence=0.9)
        return StepOutcome(output=f"{step}:done", mode="deterministic",
                           confidence=0.9)

    Loop("use the federated result", LoopConfig(framework="five_step"),
         ledger=lg5).run(handler=h5, max_steps=6)
    from .chronicle import to_canonical_events
    fams = {c["type"] for c in to_canonical_events(lg5.events)}
    check("one_query_spans_four_pillars_and_a_loop_uses_the_result",
          layers_hit == set(LAYERS) and fed["unqueried"] == []
          and len(fed["hits"]) >= 4
          and consumed.get("used") and len(consumed["rejected"]) >= 3
          and all(r["reason"] for r in consumed["rejected"])
          and fams & {"intelligence.string.retrieved",
                      "intelligence.code.retrieved",
                      "intelligence.history.retrieved",
                      "intelligence.user.retrieved"},
          f"{len(fed['hits'])} hits across {len(layers_hit)} pillars; loop "
          f"used {consumed.get('used')}, recorded "
          f"{len(consumed['rejected'])} rejections with reasons")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
