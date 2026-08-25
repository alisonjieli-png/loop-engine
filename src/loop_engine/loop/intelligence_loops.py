"""Intelligence loops — every one of the four pillars stored and served AS a loop.

Architectural role: loop (the four intelligence pillars get their loop
envelopes: context loop / code loop / guidance loop / historical run loop).

Owner law (2026-08-24): "make all 4 layers of intelligence be stored and
consumed as loops — context loops, code loops, guidance loops, and historical
run loops."  This module makes that literal: an intelligence item is NOT just
a record; it is a named loop envelope — identity, goal, typed I/O, a stop
condition of one accepted success, and a layer-labeled retrieval event on the
ledger.  The CONTENT stays passive data; the SERVING is always a loop.  This
is the Universal Loop Standard applied to the intelligence plane: nothing is
consumed raw, everything crosses a loop.

The four kinds (pillar → loop kind):
    string_intelligence    -> CONTEXT loop     (a String served as a loop)
    code_intelligence      -> CODE loop        (a bound executable unit)
    user_intelligence      -> GUIDANCE loop    (human advice, scoped + timed)
    past_run_intelligence  -> HISTORICAL loop  (a prior run / solution)

A loop kind is closed (`INTELLIGENCE_LOOP_KINDS`); an unknown kind is refused
fail-closed.  Every serve is accepted-success-once, deterministic, zero
semantic calls, with ``intelligence.<layer>.retrieved`` recorded.

Owns:
    - IntelligenceLoop (the named envelope kind + the serve);
    - serve_context_intelligence / serve_code / serve_guidance /
      serve_historical (one call per pillar);
    - serve_pillar(pillar, ...) -> the right kind for any of the four.

Does not own:
    - the runtime (recursive_loop), the encapsulators (encapsulate), or the
      retriever (static_architecture/retrieval).  This module COMPOSES them.

Key invariants:
    - every serve returns through a loop, never raw;
    - ``stop_condition`` is always a first accepted success;
    - the layer is always recorded (the ledger never sees an unlabeled read);
    - unknown pillar -> fail-closed.

Verification: self_test() — each pillar serves through the right kind, the
loop events are recorded, and a bad pillar raises.
"""
from __future__ import annotations

from dataclasses import dataclass

from .encapsulate import as_loop
from .recursive_loop import Loop, LoopLedger

#: the four pillars ride named loop kinds — never a raw serve.
INTELLIGENCE_LOOP_KINDS = {
    "string_intelligence": "context_loop",
    "code_intelligence": "code_loop",
    "user_intelligence": "guidance_loop",
    "past_run_intelligence": "historical_run_loop",
}

#: the canonical ledger family for each pillar's retrieve event.
_PILLAR_EVENT = {
    "string_intelligence": "intelligence.string.retrieved",
    "code_intelligence": "intelligence.code.retrieved",
    "user_intelligence": "intelligence.user.retrieved",
    "past_run_intelligence": "intelligence.history.retrieved",
}


class IntelligenceLoopKindError(ValueError):
    """An unknown pillar/kind was requested — refused, never guessed."""


@dataclass
class IntelligenceLoop:
    """The named loop envelope for one intelligence item.

    The item's content is the DATA it carries; the envelope is the loop.  A
    ``serve()`` runs the envelope as a thin accepted-success loop and returns
    the content as its output."""
    pillar: str               # one of LAYERS
    name: str                 # short identifier
    content: "object"         # the passive data (a String, a record, a callable)
    kind: str = ""            # one of INTELLIGENCE_LOOP_KINDS values
    query_hint: str = ""      # the "need" this loop serves against

    def __post_init__(self):
        if self.pillar not in INTELLIGENCE_LOOP_KINDS:
            raise IntelligenceLoopKindError(
                f"pillar {self.pillar!r} not in {tuple(INTELLIGENCE_LOOP_KINDS)}")
        if not self.kind:
            self.kind = INTELLIGENCE_LOOP_KINDS[self.pillar]
        elif self.kind != INTELLIGENCE_LOOP_KINDS[self.pillar]:
            raise IntelligenceLoopKindError(
                f"pillar {self.pillar} must be kind "
                f"{INTELLIGENCE_LOOP_KINDS[self.pillar]}, not {self.kind!r}")

    @property
    def loop_kind(self) -> str:
        return self.kind

    def serve(self, *, ledger: "LoopLedger | None" = None,
              parent: "Loop | None" = None) -> dict:
        """Serve this intelligence item AS a loop.  One accepted success; the
        retrieval is layer-labeled on the ledger; zero semantic calls."""
        out = as_loop(f"{self.kind}:{self.name}", self.content if callable(self.content) else (self.content if not callable(self.content) else self.content),
                      ledger=ledger, parent=parent)
        lg = ledger or LoopLedger()
        # the layer-labeled retrieval event rides the ledger
        lg.record(loop_id=out["loop_id"],
                  event=_PILLAR_EVENT[self.pillar], kind=self.kind,
                  name=self.name, pulled=out["value"] is not None)
        out["pillar"] = self.pillar
        out["kind"] = self.kind
        return out

    def to_dict(self) -> dict:
        return {"record_type": "intelligence_loop/v1", "pillar": self.pillar,
                "kind": self.kind, "name": self.name,
                "query_hint": self.query_hint}


def make_intelligence_loop(pillar: str, name: str, content, *,
                           query_hint: str = "") -> IntelligenceLoop:
    """The single constructor — build the right loop kind for a pillar."""
    return IntelligenceLoop(pillar=pillar, name=name, content=content,
                            query_hint=query_hint)


# Convenience: one call per pillar.  All four are the same loop envelope.
def serve_context_intelligence(name: str, content, *, ledger=None, parent=None,
                               **kw) -> dict:
    """Serve this pillar as a loop.  ``ledger``/``parent`` reach serve(); the
    rest configure the capsule — an earlier version forwarded everything to
    the constructor, so no caller could put the retrieval on a run's
    timeline."""
    return IntelligenceLoop(pillar="string_intelligence", name=name,
                            content=content, **kw).serve(ledger=ledger,
                                                         parent=parent)


def serve_code_intelligence(name: str, content, *, ledger=None, parent=None,
                            **kw) -> dict:
    """Serve this pillar as a loop.  ``ledger``/``parent`` reach serve(); the
    rest configure the capsule."""
    return IntelligenceLoop(pillar="code_intelligence", name=name,
                            content=content, **kw).serve(ledger=ledger,
                                                         parent=parent)


def serve_guidance_intelligence(name: str, content, *, ledger=None, parent=None,
                                **kw) -> dict:
    """Serve this pillar as a loop.  ``ledger``/``parent`` reach serve(); the
    rest configure the capsule."""
    return IntelligenceLoop(pillar="user_intelligence", name=name,
                            content=content, **kw).serve(ledger=ledger,
                                                         parent=parent)


def serve_historical_intelligence(name: str, content, *, ledger=None, parent=None,
                                  **kw) -> dict:
    """Serve this pillar as a loop.  ``ledger``/``parent`` reach serve(); the
    rest configure the capsule."""
    return IntelligenceLoop(pillar="past_run_intelligence", name=name,
                            content=content, **kw).serve(ledger=ledger,
                                                         parent=parent)


def serve_pillar(pillar: str, name: str, content, *, ledger=None,
                 parent=None, **kw) -> dict:
    """Serve any pillar through its named loop kind (one entry point).

    ``ledger`` and ``parent`` belong to serve(); everything else configures
    the capsule."""
    return make_intelligence_loop(pillar, name, content, **kw).serve(
        ledger=ledger, parent=parent)


def search_as_loop(store, query: str, *, pillar: str = "string_intelligence",
                   kind: "str | None" = None, top_n: int = 5, ledger=None,
                   parent=None) -> dict:
    """EVERY SEARCH IS A LOOP (owner, 2026-08-24).

    A product-level caller may not reach a store's ``search`` directly. It
    invokes this envelope, which runs the search as a deterministic
    accepted-success loop and records the layer-labelled retrieval on the
    caller's ledger — so "we searched the strings" is evidence, not an
    assumption. Returns the serve dict; ``value`` holds the hits."""
    return serve_pillar(pillar, f"search:{query[:40]}",
                        lambda: store.search(query, kind=kind, top_n=top_n)
                        if kind is not None
                        else store.search(query, top_n=top_n),
                        ledger=ledger, parent=parent)


def search_as_loop_refs(store, query: str, *,
                        pillar: str = "string_intelligence",
                        kind: "str | None" = None, top_n: int = 5,
                        ledger=None, parent=None) -> list:
    """SEARCH RETURNS LOOPS (charter §20).

    ``search_as_loop`` returns hits through an envelope — correct, but the
    caller still receives content.  This returns ranked ``LoopRef``s: address
    plus handshake, no payload.  The caller filters by compatibility, chooses,
    and only then invokes, so selection costs nothing to materialise."""
    from .loop_capsule import refs_for_hits
    hits = search_as_loop(store, query, pillar=pillar, kind=kind,
                          top_n=top_n, ledger=ledger,
                          parent=parent)["value"]["hits"]
    return refs_for_hits(hits, role=pillar)


def serve_record_as_loop(store, record_id: str, *,
                         pillar: str = "string_intelligence", ledger=None,
                         parent=None) -> dict:
    """One stored record, fetched through its loop rather than read directly."""
    return serve_pillar(pillar, f"record:{record_id}",
                        lambda: store.serve(record_id),
                        ledger=ledger, parent=parent)


def records_as_loop(store, *, pillar: str = "string_intelligence",
                    ledger=None, parent=None) -> dict:
    """The store's whole record set, fetched through a loop."""
    return serve_pillar(pillar, "records:all", lambda: store.records(),
                        ledger=ledger, parent=parent)


def consult_guidance_as_loop(store, scope: str, target: str, *,
                             loop_id: str = "", ledger=None,
                             parent=None) -> dict:
    """EVERY GUIDANCE ACCESS IS A LOOP. Consulting human advice crosses a
    boundary, so it runs as a Guidance Loop; the consult still records its own
    audit row on the advice store."""
    return serve_pillar("user_intelligence", f"consult:{scope}:{target}",
                        lambda: store.consult(scope, target, loop_id=loop_id,
                                              ledger=ledger),
                        ledger=ledger, parent=parent)


def guidance_for_as_loop(store, scope: str, target: str, *, ledger=None,
                         parent=None) -> dict:
    """Active advice for a target, read through a Guidance Loop."""
    return serve_pillar("user_intelligence", f"advice_for:{scope}:{target}",
                        lambda: store.advice_for(scope, target),
                        ledger=ledger, parent=parent)


def leave_guidance_as_loop(store, text: str, *, ledger=None, parent=None,
                           **kw) -> dict:
    """A person leaving advice is a WRITE that crosses the boundary, so it
    crosses through a Guidance Loop too. The store's own append-only rules
    and refusals are unchanged — this adds the envelope, not new authority."""
    return serve_pillar("user_intelligence", f"leave:{str(text)[:30]}",
                        lambda: store.leave_advice(text, **kw),
                        ledger=ledger, parent=parent)


#: map a store record kind onto the pillar its loop belongs to (closed).
#: "node" is the code-store's internal spelling of a code loop; both map to
#: Code Intelligence.  Unknown kinds fail closed — never guessed.
_STORE_KIND_TO_PILLAR = {
    "context": "string_intelligence",
    "question": "string_intelligence",
    "persona": "string_intelligence",
    "strategy": "past_run_intelligence",
    "loop": "code_intelligence",
    "node": "code_intelligence",     # the store's internal code spelling
}


def loops_for_records(records: list, *, query_hint: str = "") -> list:
    """Wrap a sequence of store records into their named intelligence loops.

    The catalog's read path calls this so any intelligence it returns crosses
    the loop envelope instead of being handed over raw.  A record's ``kind``
    (context/question/persona/strategy/…) maps to its pillar; an unknown kind
    fails closed (never guessed)."""
    out = []
    for r in records:
        kind = getattr(r, "kind", "")
        pillar = _STORE_KIND_TO_PILLAR.get(kind)
        if pillar is None:
            raise IntelligenceLoopKindError(
                f"record kind {kind!r} has no intelligence pillar — a record "
                "must map to a pillar before it can be served as a loop")
        out.append(make_intelligence_loop(
            pillar, getattr(r, "record_id", "unknown"), r,
            query_hint=query_hint))
    return out


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    # 1. POSITIVE — each pillar serves through its NAMED loop kind.
    ctx = serve_context_intelligence("persona.statistician",
                                     {"text": "be a statistician"})
    code = serve_code_intelligence("dedupe", lambda: "rows->deduped")
    guide = serve_guidance_intelligence("advice.rapidfuzz",
                                        {"text": "try rapidfuzz"})
    hist = serve_historical_intelligence("prior.titanic", {"solution": "hgb"})
    check("four_pillars_serve_through_named_loop_kinds",
          ctx["kind"] == "context_loop" and code["kind"] == "code_loop"
          and guide["kind"] == "guidance_loop" and hist["kind"] == "historical_run_loop"
          and all(x["accepted"] >= 1 for x in (ctx, code, guide, hist))
          and all(x["model_calls"] == 0 for x in (ctx, code, guide, hist))
          and all(x["stopped"] in ("success_once", "done") for x in (ctx, code, guide, hist)),
          "each pillar ran as its named loop, stopped at one success, no model")

    # 2. content comes back through the loop (never bypassed).
    check("serve_returns_content_through_the_loop",
          ctx["value"] == {"text": "be a statistician"}
          and code["value"] == "rows->deduped"
          and guide["value"]["text"] == "try rapidfuzz"
          and hist["value"]["solution"] == "hgb",
          "content is the loop's output")

    # 3. ADVERSARIAL — an unknown pillar is refused, fail-closed.
    refused = False
    try:
        serve_pillar("mystery_intelligence", "x", {"a": 1})
    except IntelligenceLoopKindError:
        refused = True
    check("unknown_pillar_refused_fail_closed", refused)

    # 4. the layer-labeled retrieval event lands on the ledger.
    lg = LoopLedger()
    IntelligenceLoop(pillar="user_intelligence", name="a",
                     content={"text": "hi"}).serve(ledger=lg)
    check("retrieval_is_layer_labeled_on_the_ledger",
          any(e.get("event") == "intelligence.user.retrieved"
              for e in lg.events),
          "guidance read recorded under its canonical family")

    # 5. one entry point serves any pillar to the right kind.
    o = serve_pillar("past_run_intelligence", "prior", {"r": 1})
    check("serve_pillar_resolves_to_the_right_kind",
          o["kind"] == "historical_run_loop" and o["value"] == {"r": 1},
          "one entry point, right kind")

    # 6. the catalog's read side returns NAMED LOOPS, not bare records —
    # the whole store maps to pillars and a "node" code record becomes a
    # code loop.
    from ..static_architecture.store_serve import SolverStore, core_seed
    s = SolverStore(core_records=core_seed())
    loops = s.records_as_loops()
    check("catalog_reads_return_named_loops_everywhere",
          loops and all(l.loop_kind in set(INTELLIGENCE_LOOP_KINDS.values())
                        for l in loops)
          and any(l.pillar == "code_intelligence" and l.loop_kind == "code_loop"
                  for l in loops),
          f"{len(loops)} records -> named loops")
    hits = s.search_as_loops("what is the best next move")
    check("catalog_search_returns_named_loops",
          hits and all(h.loop_kind in set(INTELLIGENCE_LOOP_KINDS.values())
                       for h in hits),
          f"{len(hits)} search hits -> loops")

    class BodyFreeSearchSpy:
        served = 0

        def search(self, query, **kwargs):
            return {"hits": [{"record_id": "q.card", "kind": "question",
                              "title": "body-free question card",
                              "tier": "core", "source": "test",
                              "score": 1.0, "facets": {}}]}

        def serve(self, record_id):
            self.served += 1
            raise AssertionError("search must not materialize the body")

    spy = BodyFreeSearchSpy()
    refs = search_as_loop_refs(spy, "question card")
    check("search_refs_never_serve_unselected_bodies",
          len(refs) == 1 and spy.served == 0
          and refs[0].loop_ref.endswith("q.card"))

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
