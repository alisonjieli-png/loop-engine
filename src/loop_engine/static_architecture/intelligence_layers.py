"""The four intelligence layers — one queryable knowledge surface.

Architectural role: Static Architecture service for the four persistent
intelligence layers: String, Code, Previous Run & Solution, and User.

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

Verification: self_test() — labeled fan-out, per-layer routing, shared
classification, real population building, and the four-layer invariant.
"""
from __future__ import annotations

import os
import re
from collections import Counter

from .context_classification import (CONTEXT_HIERARCHY_FIELDS,
                                     CONTEXT_THINKING_STYLES,
                                     context_hierarchy)

LAYERS = ("string_intelligence", "code_intelligence", "past_run_intelligence",
          "user_intelligence")

# Public names changed without rewriting persisted layer IDs. The internal
# ``string_intelligence`` token remains stable for Chronicle history, seed
# identities, content addresses, and existing API clients.
PUBLIC_LAYER_KEYS = ("context_intelligence", "code_intelligence",
                     "past_run_intelligence", "user_intelligence")
LAYER_PUBLIC_KEY = dict(zip(LAYERS, PUBLIC_LAYER_KEYS))
LAYER_PUBLIC_SLUG = {
    "string_intelligence": "context",
    "code_intelligence": "code",
    "past_run_intelligence": "history",
    "user_intelligence": "user",
}
LAYER_ALIASES = {
    "context": "string_intelligence",
    "context_intelligence": "string_intelligence",
    "string": "string_intelligence",
    **{layer: layer for layer in LAYERS},
}

#: product-facing names (correction directive 2026-08-24 §9): internal
#: tokens stay stable; every human surface uses these labels. The third
#: pillar's canonical product name is "Previous Run & Solution
#: Intelligence" (short UI label: "Run & Solution Intelligence").
LAYER_PUBLIC_LABEL = {
    "string_intelligence": "Context Intelligence",
    "code_intelligence": "Code Intelligence",
    "past_run_intelligence": "Previous Run & Solution Intelligence",
    "user_intelligence": "User Intelligence",
}
LAYER_SHORT_LABEL = {
    "string_intelligence": "Context Intelligence",
    "code_intelligence": "Code Intelligence",
    "past_run_intelligence": "Run & Solution Intelligence",
    "user_intelligence": "User Intelligence",
}

#: plain-English meaning of each layer, served with every handshake so a
#: reader never needs this file to understand a result.
LAYER_MEANING = {
    "string_intelligence": ("reusable context the loop can pull in: questions, "
                            "methods, personas, timeframes, evaluations, "
                            "instructions, and templates"),
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

# A shared, broad category group for each layer. The record's more specific
# category and subcategory stay intact. Unknown items remain visible as
# ``other`` with a missing-field report rather than receiving an invented type.
LAYER_CATEGORY_GROUPS = {
    "string_intelligence": (
        "question", "method", "checklist", "template", "persona",
        "evaluation", "context", "instruction", "warning", "constraint",
        "consideration", "other"),
    "code_intelligence": (
        "transform", "analyze", "decide", "retrieve", "execute",
        "validate", "report", "integrate", "other"),
    "past_run_intelligence": (
        "run", "solution", "decision", "failure", "repair",
        "measurement", "comparison", "other"),
    "user_intelligence": (
        "advice", "correction", "context", "source_suggestion",
        "package_suggestion", "priority_change", "constraint",
        "instruction", "approval", "veto", "other"),
}

CLASSIFICATION_FIELDS = (
    "layer", "item_type", "category_group", "category", "subcategory",
    "domain", "scope", "lifecycle", "source", "tags")

_GROUP_HINTS = {
    "string_intelligence": (
        ("question", ("question", "interrogation")),
        ("persona", ("persona", "perspective", "role")),
        ("warning", ("warning", "risk", "failure", "leakage")),
        ("constraint", ("constraint", "limit", "requirement")),
        ("consideration", ("consideration", "tradeoff", "trade_off")),
        ("checklist", ("checklist", "list_item")),
        ("template", ("template", "prompt_prefix", "prompt_suffix")),
        ("evaluation", ("evaluation", "measurement", "metric", "rubric")),
        ("instruction", ("instruction", "guidance", "policy")),
        ("method", ("method", "strategy", "practice", "approach")),
        ("context", ("context", "framing", "analogy", "keyword"))),
    "code_intelligence": (
        ("validate", ("validate", "validator", "check", "guard", "audit")),
        ("retrieve", ("search", "retrieve", "lookup", "catalog")),
        ("report", ("report", "render", "playback", "analytics")),
        ("decide", ("decide", "route", "rank", "select", "policy")),
        ("analyze", ("analyze", "analysis", "measure", "score", "profile")),
        ("transform", ("transform", "clean", "normalize", "dedupe", "parse")),
        ("integrate", ("integrate", "compile", "compose", "persist")),
        ("execute", ("execute", "run", "client", "provider"))),
    "past_run_intelligence": (
        ("solution", ("solution", "asset", "canvas")),
        ("failure", ("failure", "failed", "error", "stuck")),
        ("repair", ("repair", "recovery", "fallback", "retry")),
        ("comparison", ("comparison", "paired", "versus")),
        ("measurement", ("measurement", "score", "metric", "cost")),
        ("decision", ("decision", "selected", "rejected")),
        ("run", ("run", "chronicle", "history", "previous"))),
    "user_intelligence": (),
}


def _words(*values) -> set:
    return set(re.findall(r"[a-z0-9_]+", " ".join(
        str(value or "").lower() for value in values)))


def normalize_layer_name(layer: str) -> str:
    """Map a public or compatibility name to the stable wire identifier."""
    try:
        return LAYER_ALIASES[str(layer).strip().lower()]
    except KeyError as exc:
        raise ValueError(
            f"unknown intelligence layer {layer!r}; public layers are "
            f"{PUBLIC_LAYER_KEYS}") from exc


def normalize_layer_records(layer_records: dict) -> dict:
    """Normalize public keys once and refuse duplicate aliases."""
    normalized, supplied_as = {}, {}
    for supplied, records in layer_records.items():
        layer = normalize_layer_name(supplied)
        if layer in normalized:
            raise ValueError(
                f"duplicate intelligence layer {layer!r} supplied as "
                f"{supplied_as[layer]!r} and {supplied!r}")
        normalized[layer] = records
        supplied_as[layer] = supplied
    return normalized


def classify_record(layer: str, record) -> dict:
    """Return the common ``classification/v1`` view for one StoreRecord."""
    if layer not in LAYERS:
        raise ValueError(f"unknown intelligence layer {layer!r}")
    body = dict(record.body or {})
    facets = dict(body.get("facets") or {})
    tags = tuple(record.tags or ())
    item_type = str(body.get("role") or body.get("string_kind")
                    or body.get("history_type") or record.kind or "")
    specific = str(facets.get("category") or body.get("category")
                   or item_type or "")
    subcategory = str(facets.get("subcategory")
                      or body.get("subcategory") or "")
    explicit_group = str(facets.get("category_group") or "")
    group = explicit_group if explicit_group in LAYER_CATEGORY_GROUPS[layer] \
        else ""
    if not group and layer == "user_intelligence":
        guidance_type = str(body.get("guidance_type") or subcategory)
        group = guidance_type if guidance_type in LAYER_CATEGORY_GROUPS[layer] \
            else "other"
    if not group:
        words = _words(item_type, specific, subcategory, record.title, *tags)
        for candidate, hints in _GROUP_HINTS[layer]:
            if words & set(hints):
                group = candidate
                break
    group = group or "other"
    scope = str(facets.get("scope") or body.get("scope") or "")
    lifecycle = str(facets.get("lifecycle") or body.get("lifecycle")
                    or body.get("maturity") or "")
    source = str(body.get("provenance") or record.source or "")
    out = {"schema": "classification/v1", "layer": layer,
           "item_type": item_type, "category_group": group,
           "category": specific, "subcategory": subcategory,
           "domain": str(facets.get("domain") or body.get("domain") or ""),
           "scope": scope, "lifecycle": lifecycle, "source": source,
           "tags": list(tags)}
    required = ("layer", "item_type", "category", "scope", "lifecycle")
    out["missing"] = [field for field in required if not out.get(field)]
    out["complete"] = not out["missing"]
    out["public_key"] = LAYER_PUBLIC_KEY[layer]
    out["public_slug"] = LAYER_PUBLIC_SLUG[layer]
    out["public_label"] = LAYER_PUBLIC_LABEL[layer]
    if layer == "string_intelligence":
        out["context_hierarchy"] = context_hierarchy(record, out)
    return out


def classified_record(layer: str, record, *, record_id: str = ""):
    """Copy a StoreRecord and add common classification facets."""
    from .store_serve import StoreRecord
    classification = classify_record(layer, record)
    body = dict(record.body or {})
    facets = dict(body.get("facets") or {})
    facets.update({key: classification[key] for key in (
        "layer", "item_type", "category_group", "category", "subcategory",
        "domain", "scope", "lifecycle")})
    hierarchy = classification.get("context_hierarchy") or {}
    facets.update({key: value for key, value in hierarchy.items()
                   if key not in ("schema", "tags") and value not in ("", [])})
    body.update({"facets": facets, "classification": classification,
                 "original_record_id": record.record_id})
    return StoreRecord(record_id or record.record_id, record.kind, record.title,
                       body=body, tags=tuple(record.tags), tier=record.tier,
                       source=record.source)


def build_intelligence_catalog(*, runs_dir: str = "",
                               advice_path: str = "",
                               include_candidates: bool = False) -> dict:
    """Build the four real layer populations through existing adapters.

    Candidate Context records are excluded by default. Set
    ``include_candidates=True`` for review and comparison, never as a silent
    substitute for promotion.
    """
    from .store_serve import StoreRecord
    from .context_catalog import build_context_records
    strings = build_context_records(include_candidates=include_candidates)

    # Code Intelligence is conservative: these are implemented module
    # references, not claims that every module is an independently invokable
    # registered node.
    import ast
    from ..architecture_map import MODULE_MAP
    package_root = os.path.dirname(os.path.dirname(__file__))
    code = []
    for module in MODULE_MAP["code_nodes"]:
        path = os.path.join(package_root, "code_nodes", module + ".py")
        if not os.path.exists(path):
            continue
        doc = ""
        try:
            doc = (ast.get_docstring(ast.parse(open(path).read())) or "") \
                .splitlines()[0]
        except (OSError, SyntaxError):
            pass
        code.append(StoreRecord(
            f"code.module.{module}", "node", doc or module,
            body={"role": "module_reference", "module": module,
                  "maturity": "implemented",
                  "facets": {"category": "implemented_module",
                             "subcategory": module, "scope": "package",
                             "lifecycle": "implemented"}},
            tags=("code_module", module), source="package"))

    from .chronicle import Chronicle, default_runs_dir, as_ledger_events
    from ..loop.intelligence_loops import serve_historical_intelligence
    history = []
    root = default_runs_dir(runs_dir)
    if os.path.isdir(root):
        for run_id in sorted(os.listdir(root)):
            if not os.path.exists(os.path.join(root, run_id, "manifest.json")):
                continue
            try:
                chronicle = serve_historical_intelligence(
                    f"catalog-run:{run_id}",
                    lambda run_id=run_id: Chronicle.load(root, run_id))["value"]
            except (OSError, KeyError, ValueError):
                continue
            projected = as_ledger_events(chronicle.events)
            goal = next((str(e.get("goal", "")) for e in projected
                         if e.get("event") == "init" and e.get("goal")), "")
            calls = sum(1 for e in projected
                        if e.get("event") == "model_invocation")
            tokens = sum(int(e.get("prompt_tokens", 0) or 0)
                         + int(e.get("eval_tokens", 0) or 0)
                         for e in projected
                         if e.get("event") == "model_invocation")
            history.append(StoreRecord(
                f"run.{run_id}", "strategy",
                f"Previous run: {goal or run_id}",
                body={"history_type": "run", "run_id": run_id,
                      "events": len(chronicle.events), "model_calls": calls,
                      "tokens": tokens, "chain_intact":
                          chronicle.verify_chain()["intact"],
                      "maturity": "committed",
                      "facets": {"category": "previous_run",
                                 "subcategory": "chronicle",
                                 "scope": "cross_run",
                                 "lifecycle": "committed"}},
                tags=("previous_run", "chronicle"), source="chronicle"))

    from .user_intelligence import AdviceStore, advice_records_for_search
    if not advice_path:
        advice_path = os.path.join(os.path.dirname(root), "studio",
                                   "user-advice.jsonl")
    user = advice_records_for_search(AdviceStore(advice_path))
    return {"string_intelligence": strings, "code_intelligence": code,
            "past_run_intelligence": history, "user_intelligence": user}


def catalog_summary(layer_records: dict) -> dict:
    """Counts and category coverage for a four-layer catalog."""
    layer_records = normalize_layer_records(layer_records)
    layers = []
    for layer in LAYERS:
        records = list(layer_records.get(layer) or ())
        classifications = [classify_record(layer, record)
                           for record in records]
        counts = Counter(c["category_group"] for c in classifications)
        layers.append({"layer": layer,
                       "public_key": LAYER_PUBLIC_KEY[layer],
                       "public_slug": LAYER_PUBLIC_SLUG[layer],
                       "public_label": LAYER_PUBLIC_LABEL[layer],
                       "meaning": LAYER_MEANING[layer],
                       "items": len(records),
                       "category_groups": dict(sorted(counts.items())),
                       "incomplete": sum(not c["complete"]
                                         for c in classifications)})
    return {"schema": "intelligence_catalog_summary/v1", "layers": layers,
            "total_items": sum(row["items"] for row in layers)}


def layer_handshake() -> dict:
    """What the knowledge plane offers, honestly."""
    return {"layers": [{"layer": l,
                        "public_key": LAYER_PUBLIC_KEY[l],
                        "public_slug": LAYER_PUBLIC_SLUG[l],
                        "public_label": LAYER_PUBLIC_LABEL[l],
                        "short_label": LAYER_SHORT_LABEL[l],
                        "meaning": LAYER_MEANING[l],
                        "category_groups": list(LAYER_CATEGORY_GROUPS[l]),
                        "queryable": True} for l in LAYERS],
            "classification": {"schema": "classification/v1",
                               "fields": list(CLASSIFICATION_FIELDS)},
            "context_hierarchy": {
                "schema": "context_hierarchy/v1",
                "fields": list(CONTEXT_HIERARCHY_FIELDS),
                "thinking_styles": list(CONTEXT_THINKING_STYLES)},
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
                       mode: str = "lexical", top_n: int = 3,
                       flt=None, include_candidates: bool = False) -> dict:
    """Fan ONE semantic need across the four layers through the one
    Retriever. ``layer_records`` maps layer name -> list of StoreRecords
    (missing layers are reported as unqueried, never silently skipped).
    Returns {"need", "hits": [... each with "layer" ...], "unqueried"}."""
    from .retrieval import Retriever
    normalized = normalize_layer_records(layer_records)
    combined, identities, unqueried = [], {}, []
    for layer in LAYERS:
        recs = list(normalized.get(layer) or ())
        if not include_candidates:
            recs = [record for record in recs if record.tier == "core"
                    and str((record.body or {}).get("maturity", ""))
                    != "candidate"]
        if not recs:
            unqueried.append(layer)
            continue
        for record in recs:
            wrapped_id = f"{layer}:{record.record_id}"
            wrapped = classified_record(layer, record, record_id=wrapped_id)
            combined.append(wrapped)
            identities[wrapped_id] = (record.record_id,
                                      wrapped.body["classification"])
    requested = max(top_n, top_n * max(1, len(LAYERS) - len(unqueried)))
    res = Retriever(combined).search(need, mode=mode, flt=flt,
                                     top_n=requested) if combined else {"hits": []}
    hits = []
    for hit in res["hits"]:
        original_id, classification = identities[hit["record_id"]]
        hits.append({**hit, "record_id": original_id,
                     "layer": classification["layer"],
                     "public_key": classification["public_key"],
                     "public_slug": classification["public_slug"],
                     "public_label": classification["public_label"],
                     "classification": classification,
                     "score": hit.get("rrf", 0.0)})
    return {"need": need, "hits": hits, "unqueried": unqueried,
            "unqueried_public": [LAYER_PUBLIC_KEY[layer]
                                 for layer in unqueried],
            "candidates_included": bool(include_candidates)}


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
          out["hits"] and all("layer" in h and "public_label" in h
                              for h in out["hits"])
          and out["hits"][0]["layer"] == "code_intelligence"
          and out["hits"][0]["record_id"] == "n.dedupe",
          f"top: {out['hits'][0]['record_id'] if out['hits'] else 'none'}")

    # 2. a Context need routes to the stable internal string layer; a prior-solution
    # need routes to past runs — three DISTINCT buckets, not one soup.
    a = query_intelligence("statistician persona", packs)
    b = query_intelligence("prior solution titanic survival", packs)
    c = query_intelligence("user advice rapidfuzz", packs)
    check("needs_route_to_their_layers",
          a["hits"] and a["hits"][0]["layer"] == "string_intelligence"
          and a["hits"][0]["public_label"] == "Context Intelligence"
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

    alias_hit = query_intelligence(
        "statistician persona", {"context": strings})
    duplicate_refused = False
    try:
        query_intelligence("x", {"context": strings,
                                  "string_intelligence": strings})
    except ValueError:
        duplicate_refused = True
    check("context_aliases_preserve_one_internal_layer",
          alias_hit["hits"]
          and alias_hit["hits"][0]["layer"] == "string_intelligence"
          and alias_hit["hits"][0]["public_key"] == "context_intelligence"
          and duplicate_refused and len(LAYERS) == len(PUBLIC_LAYER_KEYS) == 4)

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
          hs["layers"][0]["public_label"] == "Context Intelligence"
          and hs["layers"][0]["public_key"] == "context_intelligence"
          and hs["layers"][2]["public_label"]
          == "Previous Run & Solution Intelligence"
          and all("public_label" in l and "short_label" in l
                  for l in hs["layers"]))

    check("runtime_memory_is_built_run_scoped_ambient_writes_refused",
          len(hs["layers"]) == 4
          and hs["runtime_memory"]["state"] == "built_run_scoped"
          and rm_refused)

    # 5. FOUR-LAYER CANARY: one need, one query, all four persistent
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
    check("one_query_spans_four_layers_and_a_loop_uses_the_result",
          layers_hit == set(LAYERS) and fed["unqueried"] == []
          and len(fed["hits"]) >= 4
          and consumed.get("used") and len(consumed["rejected"]) >= 3
          and all(r["reason"] for r in consumed["rejected"])
          and fams & {"intelligence.string.retrieved",
                      "intelligence.code.retrieved",
                      "intelligence.history.retrieved",
                      "intelligence.user.retrieved"},
          f"{len(fed['hits'])} hits across {len(layers_hit)} layers; loop "
          f"used {consumed.get('used')}, recorded "
          f"{len(consumed['rejected'])} rejections with reasons")

    # 6. One common classification rides every hit and supports the same hard
    # filters across all four layers.
    from .facets import FacetFilter
    code_only = query_intelligence(
        "duplicate row remover", packs,
        flt=FacetFilter(require={"layer": "code_intelligence"}))
    check("classification_and_filters_span_all_layers",
          code_only["hits"]
          and all(hit["classification"]["schema"] == "classification/v1"
                  and hit["layer"] == "code_intelligence"
                  for hit in code_only["hits"])
          and "category_groups" in layer_handshake()["layers"][0],
          "shared layer/category/scope/lifecycle facets")

    weak_vs_exact = query_intelligence(
        "alpha beta gamma delta",
        {"string_intelligence": [StoreRecord(
             "weak", "context", "alpha", body={}, tags=())],
         "code_intelligence": [StoreRecord(
             "exact", "node", "alpha beta gamma delta", body={}, tags=())]},
        mode="lexical", top_n=2)
    check("global_ranking_compares_layers_in_one_corpus",
          weak_vs_exact["hits"][0]["record_id"] == "exact"
          and weak_vs_exact["hits"][0]["layer"] == "code_intelligence",
          "exact Code match outranks weak String match")

    # 8. The default real population excludes candidates. A review catalog can
    # include the 1,000-record seed pack and generated candidate bank.
    import os
    import tempfile
    from .chronicle import Chronicle
    from .user_intelligence import AdviceStore
    root = tempfile.mkdtemp(prefix="intelligence_catalog_")
    ch = Chronicle("catalog-run")
    ch.append("loop_init", loop_id="loop1", detail={"goal": "catalog test"})
    ch.append("terminal", loop_id="loop1", detail={"reason": "done"})
    ch.commit(); ch.save(root)
    advice_path = os.path.join(root, "advice.jsonl")
    AdviceStore(advice_path).leave_advice(
        "Prefer the documented parser.", scope="task", target="catalog")
    real = build_intelligence_catalog(runs_dir=root, advice_path=advice_path)
    review = build_intelligence_catalog(
        runs_dir=root, advice_path=advice_path, include_candidates=True)
    summary = catalog_summary(real)
    review_summary = catalog_summary(review)
    seed_class = classify_record("string_intelligence",
                                 next(record for record
                                      in review["string_intelligence"]
                                      if record.record_id == "SI-0001"))
    check("real_catalog_populates_and_categorizes_four_layers",
          100 <= len(real["string_intelligence"]) < 1000
          and len(review["string_intelligence"]) >= 1000
          and len(real["code_intelligence"]) >= 30
          and len(real["past_run_intelligence"]) == 1
          and len(real["user_intelligence"]) == 1
          and review_summary["total_items"] > summary["total_items"]
          and seed_class["complete"]
          and seed_class["scope"] == "core_seed",
          f"{summary['total_items']} active items; "
          f"{review_summary['total_items']} with candidates")

    candidate = next(record for record in review["string_intelligence"]
                     if record.record_id == "SI-0001")
    hidden = query_intelligence(
        candidate.title, {"context_intelligence": [candidate]})
    visible = query_intelligence(
        candidate.title, {"context_intelligence": [candidate]},
        include_candidates=True)
    check("candidate_context_is_off_by_default",
          not hidden["hits"] and visible["hits"]
          and visible["hits"][0]["public_label"] == "Context Intelligence")
    import shutil
    shutil.rmtree(root, ignore_errors=True)

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
