"""Ollama-backed resolvers — the model answers 'what is next' when nothing cheaper can.

These wrap the Ollama Cloud client as ``llm_single`` / ``llm_council`` what-is-next
resolvers.  They sit at the expensive end of the waterfall: the deterministic
reflexes, checklists, and memory answer first and for free; the model is reached
only when a decision is genuinely open (DELIBERATE) and worth the tokens.  The
resolver renders the decision into a prompt (task + known facts + the decision
need + any domain-pack questions), calls the model, and parses the reply into
typed moves — the model proposes; the fold oracle still decides.
"""

from __future__ import annotations

import json
import re
from typing import Any, Sequence

from ..strings.knowledge import Knowledge
from ..loop.moves import move, answer, MOVE_TYPES, is_valid_move_kind
from ..loop.resolvers import WhatIsNextResolver
from ..static_architecture.ollama_client import chat, chat_maxout, DEFAULT_MODEL

_MOVE_SCHEMA_HINT = (
    'Respond ONLY with a JSON array of the 3 best next moves, each: '
    '{"move_kind": one of ["add_node","run_tests","do_research","mutate",'
    '"optimize","gather_context"], "key": short slug like "estimator=lightgbm" '
    'or "test=leakage_audit", "reason": one sentence, "confidence": 0..1}. '
    'Prefer advanced, specific methods over generic defaults. No prose outside '
    'the JSON.')


def render_next_move_prompt(knowledge: Knowledge, *,
                            questions: Sequence[str] = ()) -> str:
    facts = ", ".join(f"{k}={v}" for k, v in knowledge.facts.items()) or "none"
    parts = [knowledge.frame.render_prompt_preamble(),
             f"Task / goal: {knowledge.goal}",
             f"Current graph: {knowledge.graph_summary or 'empty'}",
             f"Known facts: {facts}",
             f"Open obligations: {', '.join(knowledge.open_obligations) or 'none'}"]
    if questions:
        parts.append("Consider these expert questions:\n"
                     + "\n".join(f"- {q}" for q in questions[:8]))
    parts.append("What is the single best next move (and two alternatives)?")
    parts.append(_MOVE_SCHEMA_HINT)
    return "\n".join(p for p in parts if p)


def parse_moves(text: str) -> list[dict]:
    """Extract typed moves from a model reply — a JSON array, or numbered/
    bulleted 'kind: key' lines.  Invented move kinds are coerced to add_node."""
    out: list[dict] = []
    # JSON array first.
    start, end = text.find("["), text.rfind("]")
    if 0 <= start < end:
        try:
            arr = json.loads(text[start:end + 1])
            for item in arr:
                if not isinstance(item, dict):
                    continue
                kind = str(item.get("move_kind") or item.get("kind")
                           or "add_node")
                if not is_valid_move_kind(kind):
                    kind = "add_node"
                key = str(item.get("key") or item.get("move") or "").strip()
                if key:
                    out.append({"kind": kind, "key": key,
                                "reason": str(item.get("reason", "")),
                                "confidence": float(item.get("confidence", 0.6)
                                                    or 0.6)})
        except Exception:                                       # noqa: BLE001
            pass
    if out:
        return out
    # Fallback: bulleted "kind: key" or "key" lines.
    for line in text.splitlines():
        m = re.match(r"\s*(?:\d+[.)]|[-*])\s*(?:([a-z_]+)\s*:\s*)?(.+)", line)
        if m and m.group(2).strip():
            kind = m.group(1) if m.group(1) and is_valid_move_kind(m.group(1)) \
                else "add_node"
            out.append({"kind": kind, "key": m.group(2).strip()[:80],
                        "reason": "", "confidence": 0.55})
    return out[:3]


def make_ollama_proposer(model: str = DEFAULT_MODEL, *, num_predict: int = 8000,
                         questions: Sequence[str] = ()):
    """A proposer (knowledge, preamble) -> [move dicts] backed by a live model."""
    def proposer(knowledge: Knowledge, preamble: str) -> list[dict]:
        prompt = render_next_move_prompt(knowledge, questions=questions)
        res = chat_maxout(prompt, model=model, temperature=0.6)
        if not res.ok:
            return []
        moves = parse_moves(res.text)
        for mv in moves:
            mv["_tokens"] = res.total_tokens
            mv["_model"] = res.model
        return moves
    return proposer


def make_ollama_regime(name: str = "ollama_next_move",
                       model: str = DEFAULT_MODEL, *, category: str = "llm_single",
                       cost: float = 8.0, num_predict: int = 8000,
                       questions: Sequence[str] = ()) -> WhatIsNextResolver:
    """A live-model what-is-next resolver, registered at the expensive tier."""
    proposer = make_ollama_proposer(model, num_predict=num_predict,
                                    questions=questions)

    def resolve(knowledge: Knowledge):
        proposed = proposer(knowledge, "")
        if not proposed:
            return None
        moves = [move(p["kind"], p["key"], mechanism=p.get("reason", ""),
                      confidence=float(p.get("confidence", 0.6)))
                 for p in proposed[:5]]
        conf = max((m.confidence for m in moves), default=0.6)
        return answer(name, category, moves, conf,
                      detail=f"{proposed[0].get('_model', model)} · "
                      f"{proposed[0].get('_tokens', 0)} tokens")
    return WhatIsNextResolver(name=name, category=category, fn=resolve,
                              cost=cost, model_calls=1)


# ---------------------------------------------------------------------------
# Self-test — offline (parsing + prompt), no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    prompt = render_next_move_prompt(
        Knowledge(goal="knee MRI abnormality detection",
                  graph_summary="empty", facts={"modality": "image"}),
        questions=["Is there class imbalance across abnormality types?"])
    check("the_prompt_carries_task_facts_questions_and_a_json_schema",
          "knee MRI" in prompt and "modality=image" in prompt
          and "class imbalance" in prompt and "JSON array" in prompt,
          "the rendered prompt includes the task, known facts, an expert "
          "question, and the strict move-JSON schema")

    moves = parse_moves(
        '```json\n[{"move_kind":"add_node","key":"backbone=efficientnet",'
        '"reason":"strong image baseline","confidence":0.7},'
        '{"move_kind":"run_tests","key":"test=class_balance","confidence":0.6}]'
        '\n```')
    check("json_replies_parse_into_typed_moves",
          len(moves) == 2 and moves[0]["key"] == "backbone=efficientnet"
          and moves[1]["kind"] == "run_tests",
          "a fenced JSON array of moves parses into typed moves with kinds "
          "validated")

    coerced = parse_moves('[{"move_kind":"teleport","key":"x"}]')
    check("an_invented_move_kind_is_coerced_not_crashed",
          coerced and coerced[0]["kind"] == "add_node",
          "a move kind outside the vocabulary is coerced to add_node rather than "
          "crashing the parse")

    bullets = parse_moves("1. add_node: estimator=lightgbm\n2. run_tests: leakage")
    check("bulleted_replies_parse_as_a_fallback",
          len(bullets) == 2 and bullets[1]["kind"] == "run_tests",
          "when the model does not return JSON, numbered 'kind: key' lines still "
          "parse")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "ollama_resolvers_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


# ---------------------------------------------------------------------------
# Multi-model council — at least THREE different models, each an independent
# voter, each with a different context-shuffle archetype for real diversity.
# ---------------------------------------------------------------------------

from ..loop.context_shuffle import shuffle_lanes  # noqa: E402

# Default trio of DIFFERENT model families (dependence-aware: one model = one
# independent voter; five personas of one model are not five voters).
COUNCIL_MODELS = ("deepseek-v4-pro", "glm-5.2", "kimi-k2.7-code")


def deep_deliberate(knowledge: Knowledge, *, models: Sequence[str] = COUNCIL_MODELS,
                    num_predict: int = 16000, questions: Sequence[str] = (),
                    shuffle: bool = True) -> dict:
    """Run a real council: at least three different models, each displaced into a
    different distant-domain archetype, then aggregate their proposals treating
    each MODEL as one independent voter (agreement across models leads).  Returns
    the ranked moves, the per-model proposals, and the TOTAL provider tokens."""
    models = list(models)
    if len(models) < 3:
        raise ValueError("a council needs at least 3 different models; got "
                         f"{len(models)}")
    frames = shuffle_lanes(knowledge.goal, n=len(models)) if shuffle else []
    members: list[dict] = []
    total_tokens = 0
    for i, model in enumerate(models):
        k = knowledge
        if shuffle and i < len(frames):
            k = Knowledge(
                goal=knowledge.goal, graph_summary=knowledge.graph_summary,
                results=knowledge.results, facts=knowledge.facts,
                open_obligations=knowledge.open_obligations,
                context_level=knowledge.context_level,
                frame=frames[i].to_ask_frame(knowledge.goal, knowledge.frame))
        prompt = render_next_move_prompt(k, questions=questions)
        res = chat_maxout(prompt, model=model, temperature=0.7)
        total_tokens += res.total_tokens
        moves = parse_moves(res.text) if res.ok else []
        members.append({"model": model,
                        "archetype": (frames[i].distant_domain + "/"
                                      + frames[i].cognition_mode)
                        if shuffle and i < len(frames) else "",
                        "ok": res.ok, "tokens": res.total_tokens,
                        "moves": moves})

    # Dependence-aware aggregation: each MODEL endorses a move at most once.
    agg: dict[tuple[str, str], dict] = {}
    for m in members:
        seen: set[tuple[str, str]] = set()
        for mv in m["moves"]:
            key = (mv["kind"], mv["key"].strip().lower())
            if key in seen:
                continue
            seen.add(key)
            row = agg.setdefault(key, {"display": mv["key"], "kind": mv["kind"],
                                       "models": 0, "conf": 0.0, "reasons": []})
            row["models"] += 1
            row["conf"] = max(row["conf"], float(mv.get("confidence", 0.6)))
            if mv.get("reason"):
                row["reasons"].append(f"[{m['model'].split(':')[0]}] "
                                      + mv["reason"])
    ranked = sorted(agg.values(),
                    key=lambda r: (-r["models"], -r["conf"], r["display"]))
    n = max(1, len(models))
    moves = [move(r["kind"], r["display"],
                  mechanism="; ".join(r["reasons"][:2]),
                  support=r["models"], confidence=min(1.0, r["models"] / n))
             for r in ranked]
    answered = sum(1 for m in members if m["moves"])
    return {"record_type": "ollama_council/v1", "models": models,
            "members_answered": answered, "total_tokens": total_tokens,
            "consensus": [{"move": r["display"], "kind": r["kind"],
                           "models_endorsing": r["models"]} for r in ranked[:6]],
            "answer": (answer("ollama_council", "llm_council", moves,
                              min(1.0, (ranked[0]["models"] / n) if ranked else 0),
                              detail=f"{answered}/{len(models)} models · "
                              f"{total_tokens} tokens") if moves else None),
            "members": members}


def make_ollama_council(name: str = "ollama_council", *,
                        models: Sequence[str] = COUNCIL_MODELS,
                        category: str = "llm_council", cost: float = 40.0,
                        num_predict: int = 16000, questions: Sequence[str] = (),
                        shuffle: bool = True) -> WhatIsNextResolver:
    """A ≥3-model council as a what-is-next resolver (the expensive tier)."""
    def resolve(knowledge: Knowledge):
        out = deep_deliberate(knowledge, models=list(models),
                              num_predict=num_predict, questions=questions,
                              shuffle=shuffle)
        return out["answer"]
    return WhatIsNextResolver(name=name, category=category, fn=resolve,
                              cost=cost, model_calls=len(list(models)))


# ---------------------------------------------------------------------------
# Multi-round debate — the deep deliberation.  Round 1 each model proposes;
# every later round each model SEES the others' proposals and critiques /
# defends / revises.  Disagreement is the point: a move that survives other
# models trying to knock it down is stronger than a move proposed once.  No
# arbitrary token cap — reasoning models are given real room to think.
# ---------------------------------------------------------------------------


def _render_critique_prompt(knowledge: Knowledge, own: list[dict],
                            others: list[dict], *,
                            questions: Sequence[str]) -> str:
    """Round-N prompt: here is the field's current thinking — attack the weak
    moves, defend or revise your own, and return your best final moves."""
    def fmt(rows):
        return "\n".join(f"- [{r['kind']}] {r['key']}"
                         + (f" — {r['reason']}" if r.get('reason') else "")
                         for r in rows) or "(none)"
    base = render_next_move_prompt(knowledge, questions=questions)
    return (base + "\n\n--- DEBATE ---\n"
            "Your previous proposals:\n" + fmt(own)
            + "\n\nOther experts proposed:\n" + fmt(others)
            + "\n\nNow critique the field: which of the other proposals are wrong "
            "or risky for THIS task and why, which are stronger than yours, and "
            "what is your revised best set of moves? A move that other experts "
            "would struggle to refute is what we want. Return the JSON moves "
            "array as before — your FINAL, post-debate moves.")


def debate(knowledge: Knowledge, *, models: Sequence[str] = COUNCIL_MODELS,
           rounds: int = 2, num_predict: int = 32000,
           questions: Sequence[str] = (), shuffle: bool = True) -> dict:
    """Run a multi-round council debate and return the post-debate consensus.

    ``rounds`` >= 2 means real deliberation: propose, then critique+revise each
    round.  ``num_predict`` is deliberately large (default 8000) so reasoning
    models finish their thinking AND their answer — the earlier 4000 cap was the
    arbitrary limit that made deliberation look shallow.  Returns the same shape
    as ``deep_deliberate`` plus per-round token totals."""
    models = list(models)
    if len(models) < 3:
        raise ValueError("a debate needs at least 3 different models; got "
                         f"{len(models)}")
    frames = shuffle_lanes(knowledge.goal, n=len(models)) if shuffle else []
    # Per-model knowledge (each displaced into its own archetype for round 1).
    kviews = []
    for i in range(len(models)):
        if shuffle and i < len(frames):
            kviews.append(Knowledge(
                goal=knowledge.goal, graph_summary=knowledge.graph_summary,
                results=knowledge.results, facts=knowledge.facts,
                open_obligations=knowledge.open_obligations,
                context_level=knowledge.context_level,
                frame=frames[i].to_ask_frame(knowledge.goal, knowledge.frame)))
        else:
            kviews.append(knowledge)

    current: list[list[dict]] = [[] for _ in models]     # each model's moves
    total_tokens = 0
    round_tokens: list[int] = []
    for rnd in range(rounds):
        rt = 0
        new_current: list[list[dict]] = []
        for i, model in enumerate(models):
            if rnd == 0:
                prompt = render_next_move_prompt(kviews[i], questions=questions)
            else:
                others = [mv for j, mvs in enumerate(current) if j != i
                          for mv in mvs]
                prompt = _render_critique_prompt(kviews[i], current[i], others,
                                                 questions=questions)
            res = chat_maxout(prompt, model=model, temperature=0.7)
            rt += res.total_tokens
            new_current.append(parse_moves(res.text) if res.ok else current[i])
        current = new_current
        total_tokens += rt
        round_tokens.append(rt)

    # Final dependence-aware aggregation over the post-debate moves.
    members = [{"model": models[i],
                "archetype": (frames[i].distant_domain + "/"
                              + frames[i].cognition_mode)
                if shuffle and i < len(frames) else "",
                "moves": current[i]} for i in range(len(models))]
    agg: dict[tuple[str, str], dict] = {}
    for m in members:
        seen: set[tuple[str, str]] = set()
        for mv in m["moves"]:
            key = (mv["kind"], mv["key"].strip().lower())
            if key in seen:
                continue
            seen.add(key)
            row = agg.setdefault(key, {"display": mv["key"], "kind": mv["kind"],
                                       "models": 0, "conf": 0.0, "reasons": []})
            row["models"] += 1
            row["conf"] = max(row["conf"], float(mv.get("confidence", 0.6)))
            if mv.get("reason"):
                row["reasons"].append(f"[{m['model'].split(':')[0]}] "
                                      + mv["reason"])
    ranked = sorted(agg.values(),
                    key=lambda r: (-r["models"], -r["conf"], r["display"]))
    n = max(1, len(models))
    moves = [move(r["kind"], r["display"], mechanism="; ".join(r["reasons"][:2]),
                  support=r["models"], confidence=min(1.0, r["models"] / n))
             for r in ranked]
    answered = sum(1 for m in members if m["moves"])
    return {"record_type": "ollama_debate/v1", "models": models,
            "rounds": rounds, "members_answered": answered,
            "total_tokens": total_tokens, "round_tokens": round_tokens,
            "consensus": [{"move": r["display"], "kind": r["kind"],
                           "models_endorsing": r["models"]} for r in ranked[:8]],
            "answer": (answer("ollama_debate", "llm_council", moves,
                              min(1.0, (ranked[0]["models"] / n) if ranked else 0),
                              detail=f"{rounds}-round debate · {answered}/"
                              f"{len(models)} models · {total_tokens} tokens")
                       if moves else None),
            "members": members}
