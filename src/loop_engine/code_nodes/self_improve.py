"""Self-improvement — always ask "could this be done cheaper?", then make it so.

The owner's rule (2026-08-22): in a practitioner loop we can ALWAYS ask — could
this step have been done deterministically, or cheaper, with less model usage?
And more than ask: build the structures that let a very similar problem be solved
faster next time WITHOUT the model calls, and self-improve on that.

Mechanism, kept honest and simple:

  * every completed cycle is examined by ``could_this_be_cheaper`` — a
    deterministic analysis: if model calls were spent but the outcome is a
    deterministic ARTIFACT (a handle, a compiled node file, a fixed choice), then
    the same problem signature can REPLAY that artifact next time with zero model
    calls, so the step is *distillable* and a Shortcut is recorded;
  * the ``ShortcutStore`` is the append-only memory of those learned routes
    (signature -> rung + handle + provenance), and ``make_learning_probe`` plugs
    it into node 2's "do we already have this?" check — so learning lands exactly
    on the reuse-first ladder's cached/muscle-memory rung, not in a side channel;
  * signatures are EXACT-match (normalised goal family + answer kind + target).
    Exact replay is the honest first rung; similarity matching (embeddings) can
    extend it later without changing the contract.

Learning only ever comes from a cycle whose verify stage reported success — a
failed or unverified step is never distilled into a shortcut (learn only from
accepted outcomes).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Any

from ..loop.methodical import CycleStep, EXECUTION_LADDER, FIRST_LLM_RUNG


def problem_signature(goal: str, kind: str, target: str) -> str:
    """A deterministic signature for 'a very similar problem'.

    Normalises the goal to its lexical family (lowercase word stems, sorted,
    numbers stripped) plus the answer kind and normalised target — so the same
    decision on the same kind of problem matches exactly, and nothing else does.
    Exact match is deliberately conservative: a wrong shortcut is worse than a
    model call."""
    words = sorted(set(re.findall(r"[a-z]+", goal.lower())))[:12]
    tgt = re.sub(r"[^a-z0-9=_]+", "_", target.lower())[:60]
    return f"{'-'.join(words)}::{kind}::{tgt}"


@dataclass
class Shortcut:
    """A learned zero-model route for a recurring problem signature."""
    signature: str
    rung: str                    # where it now resolves (cached / exact_reuse)
    handle: str                  # the artifact to replay
    model_calls_first_time: int  # what it cost to learn
    learned_from_goal: str = ""
    uses: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class ShortcutStore:
    """Append-only store of learned shortcuts (in-memory + optional JSONL).

    ``lookup`` is the muscle-memory read node 2 uses; ``record`` is how a
    completed, VERIFIED cycle teaches the system.  Records are never edited in
    place — a better route for the same signature appends and supersedes."""

    def __init__(self, path: str | None = None):
        self.path = path
        self._by_sig: dict[str, Shortcut] = {}
        if path and os.path.exists(path):
            with open(path) as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                        self._by_sig[d["signature"]] = Shortcut(**d)
                    except Exception:                           # noqa: BLE001
                        continue

    def record(self, shortcut: Shortcut) -> None:
        self._by_sig[shortcut.signature] = shortcut
        if self.path:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "a") as fh:
                fh.write(json.dumps(shortcut.to_dict()) + "\n")

    def lookup(self, signature: str) -> "Shortcut | None":
        sc = self._by_sig.get(signature)
        if sc is not None:
            sc.uses += 1
        return sc

    def __len__(self) -> int:
        return len(self._by_sig)


@dataclass
class CheaperVerdict:
    """The answer to 'could this be done cheaper?' for one completed cycle."""
    signature: str
    model_calls_spent: int
    distillable: bool
    reason: str
    shortcut: "Shortcut | None" = None


def could_this_be_cheaper(step: CycleStep) -> CheaperVerdict:
    """The always-asked question, answered deterministically.

    Distillable when: model calls were spent, the execution produced a concrete
    reusable artifact (a handle), AND the verify stage accepted the result.  Then
    the same signature replays the artifact next time at the cached rung — zero
    model calls.  A free step teaches nothing new (it was already cheap); an
    unverified step must never be distilled."""
    sig = problem_signature(step.knowledge_goal, step.answer.kind,
                            step.answer.target)
    spent = step.execution.model_calls
    rung_idx = EXECUTION_LADDER.index(step.execution.chosen)
    verified = step.verify.outcome in ("correct_and_ready",
                                       "correct_more_needed")
    if spent <= 0 and rung_idx < FIRST_LLM_RUNG:
        return CheaperVerdict(sig, 0, False,
                              "already free — nothing to distill")
    if not step.execution.handle:
        return CheaperVerdict(sig, spent, False,
                              "no reusable artifact was produced")
    if not verified:
        return CheaperVerdict(sig, spent, False,
                              "unverified outcome — never learn from it")
    sc = Shortcut(signature=sig, rung="exact_reuse",
                  handle=step.execution.handle,
                  model_calls_first_time=spent,
                  learned_from_goal=step.knowledge_goal)
    return CheaperVerdict(sig, spent, True,
                          "verified artifact — replayable with zero model calls",
                          shortcut=sc)


def learn_from_cycle(step: CycleStep, store: ShortcutStore) -> CheaperVerdict:
    """Ask the question and, when distillable, record the shortcut."""
    verdict = could_this_be_cheaper(step)
    if verdict.distillable and verdict.shortcut is not None:
        store.record(verdict.shortcut)
    return verdict


def make_learning_probe(store: ShortcutStore, *, kind_hint: str = "add_node"):
    """A registry_probe for node 2 backed by learned shortcuts.

    'Have we already built a solution like this we can just drop in?' — if the
    store knows this signature, the answer is its handle, and the step resolves
    at the reuse rung with zero model calls.  The probe needs the goal to build
    the signature, so it is created per-solve with the goal bound in."""
    def bind(goal: str):
        def probe(target: str) -> str:
            sc = store.lookup(problem_signature(goal, kind_hint, target))
            return sc.handle if sc else ""
        return probe
    return bind


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    from ..loop.methodical import NextAnswer, ExecutionDecision, VerifyResult
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # a cycle that SPENT model calls and produced a verified artifact
    step = CycleStep(
        knowledge_goal="predict customer churn on tabular data",
        answer=NextAnswer("add_node", "estimator=xgboost", "strong tabular"),
        execution=ExecutionDecision("llm_single",
                                    rungs_checked=list(EXECUTION_LADDER[:7]),
                                    handle="nodes/estimator_xgboost.py",
                                    model_calls=3),
        verify=VerifyResult("correct_and_ready", "compiles + contract ok", True))
    v = could_this_be_cheaper(step)
    check("a_verified_model_built_step_is_distillable",
          v.distillable and v.shortcut is not None
          and v.model_calls_spent == 3,
          "3 model calls produced a verified artifact — replayable free next time")

    # learning lands in the store, and lookup returns the handle
    store = ShortcutStore()
    learn_from_cycle(step, store)
    sig = problem_signature("predict customer churn on tabular data",
                            "add_node", "estimator=xgboost")
    sc = store.lookup(sig)
    check("the_shortcut_store_learns_and_replays_the_route",
          sc is not None and sc.handle == "nodes/estimator_xgboost.py"
          and sc.model_calls_first_time == 3,
          "the learned route is retrievable by exact signature")

    # a very similar problem (same words, same decision) hits the shortcut...
    sig2 = problem_signature("on tabular data predict customer churn",
                             "add_node", "estimator=xgboost")
    check("a_very_similar_problem_maps_to_the_same_signature",
          sig == sig2 and store.lookup(sig2) is not None,
          "word order does not defeat the signature; the shortcut replays")

    # ...and a DIFFERENT problem does not (conservative exact matching).
    sig3 = problem_signature("caption images of birds", "add_node",
                             "estimator=xgboost")
    check("a_different_problem_does_not_false_match", store.lookup(sig3) is None,
          "an image task never inherits the tabular shortcut — a wrong shortcut "
          "is worse than a model call")

    # an UNVERIFIED step is never distilled.
    bad = CycleStep(
        knowledge_goal="predict churn", answer=NextAnswer("add_node", "x"),
        execution=ExecutionDecision("llm_single",
                                    rungs_checked=list(EXECUTION_LADDER[:7]),
                                    handle="nodes/x.py", model_calls=2),
        verify=VerifyResult("incorrect", "failed contract", False))
    vb = could_this_be_cheaper(bad)
    check("an_unverified_step_is_never_distilled",
          not vb.distillable and "never learn" in vb.reason,
          "learning only from accepted outcomes")

    # a free step teaches nothing (it was already cheap).
    free = CycleStep(
        knowledge_goal="predict churn", answer=NextAnswer("add_node", "y"),
        execution=ExecutionDecision("exact_reuse", handle="h", model_calls=0),
        verify=VerifyResult("correct_and_ready", "", True))
    vf = could_this_be_cheaper(free)
    check("an_already_free_step_is_not_re_distilled", not vf.distillable,
          "zero-model steps have nothing to save")

    # the learning probe plugs into node 2's 'do we already have this?'.
    bind = make_learning_probe(store)
    probe = bind("predict customer churn on tabular data")
    check("the_learning_probe_answers_do_we_already_have_this",
          probe("estimator=xgboost") == "nodes/estimator_xgboost.py"
          and probe("estimator=unseen") == "",
          "node 2's reuse check now includes everything the system has LEARNED")

    # persistence round-trip (JSONL, append-only).
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "shortcuts.jsonl")
        s1 = ShortcutStore(p)
        learn_from_cycle(step, s1)
        s2 = ShortcutStore(p)                      # fresh load from disk
        check("shortcuts_persist_append_only_and_reload",
              len(s2) == 1 and s2.lookup(sig).handle
              == "nodes/estimator_xgboost.py",
              "the store survives a restart — knowledge is saved, not conversational")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "self_improve_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
