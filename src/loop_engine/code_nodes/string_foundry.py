"""String Foundry — the improvement practitioner's string-generation lane.

Architectural role: Code Node system (§13.7 presets string_gap_audit +
question_expansion, made executable).

Owns:
    - the SEED CAMPAIGN: category seeds the generation loop expands
      (job positions and their unique questions, first-principles actions,
      research discipline, ETL/data engineering, LLM phrasing/prompting) —
      plus a category-gap phase where the model proposes MISSING categories
      against the current taxonomy;
    - parse_generated: the deterministic parser for the pipe-format contract
      the prompt requests (malformed lines are counted UNDIGESTED, never
      silently dropped or repaired by guesswork);
    - normalize + dedupe (within batch and against the existing bank, by
      normalized-text digest);
    - stage_candidates: append-only user-data JSONL bank under
      ``~/.loop-engine/intelligence/candidates/`` by default; every row a full envelope
      (kind, category/subcategory, job_position facet, maturity=candidate,
      provenance naming the exact run + model + seed);
    - load_candidate_bank: the bank as StoreRecords for search/browsing.

Does not own:
    - the model call (the driver's loop makes it through the gateway —
      one per iteration, §12), promotion (candidates cross validated →
      registered only through the evidence gate), or category truth (a
      model-proposed category is itself a candidate).

Public entry points:
    - SEED_CAMPAIGN, generation_prompt(seed), category_gap_prompt(existing)
    - parse_generated(text) -> {"candidates", "undigested"}
    - stage_candidates(cands, provenance, path=None) -> {"staged", "deduped"}
    - load_candidate_bank(path=None) -> list[StoreRecord]

Key invariants:
    - append-only bank; staging never edits or removes prior rows;
    - every staged row is maturity=candidate with provenance — the foundry
      cannot mark anything registered;
    - a malformed generation line is an UNDIGESTED count (the digestibility
      funnel's input), never a fabricated candidate.

Verification: self_test() (offline — parser/dedupe/staging/loader; live
generation runs in drivers with provider-reported tokens).
"""
from __future__ import annotations

import hashlib
import json
import os

VALID_KINDS = ("question", "heuristic", "warning", "checklist_item",
               "prompt_pattern")

#: the seed campaign — the owner's list, structured.  Each seed yields one
#: generation call (one iteration each, §12).
SEED_CAMPAIGN = (
    {"key": "job_data_engineer", "category": "job_position",
     "subcategory": "data_engineer", "job_position": "data_engineer",
     "brief": "the questions, heuristics, and warnings a senior DATA "
              "ENGINEER uniquely brings to a modeling task: pipeline "
              "idempotency, schema drift, late/duplicate data, partition "
              "hygiene, backfill safety, dedup keys, lineage"},
    {"key": "job_statistician", "category": "job_position",
     "subcategory": "statistician", "job_position": "statistician",
     "brief": "what a STATISTICIAN uniquely asks: estimand clarity, "
              "sampling frame, multiple comparisons, uncertainty honesty, "
              "power, exchangeability, censoring, Simpson's paradox"},
    {"key": "job_security_engineer", "category": "job_position",
     "subcategory": "security_engineer", "job_position": "security_engineer",
     "brief": "what a SECURITY ENGINEER uniquely asks of a data/ML system: "
              "data provenance trust, poisoning, secrets in artifacts, "
              "injection through retrieved content, least privilege"},
    {"key": "job_product_manager", "category": "job_position",
     "subcategory": "product_manager", "job_position": "product_manager",
     "brief": "what a PRODUCT MANAGER uniquely asks: who consumes this "
              "output, cost of a wrong answer, latency tolerance, the "
              "smallest shippable slice, what we would cut under deadline"},
    {"key": "first_principles", "category": "first_principles",
     "subcategory": "decomposition", "job_position": "",
     "brief": "FIRST-PRINCIPLES action strings: reduce to invariants, "
              "reverse each assumption, find the conserved quantity, "
              "construct the simplest system that must exhibit the effect, "
              "bound the answer from both sides"},
    {"key": "research_discipline", "category": "research",
     "subcategory": "source_discipline", "job_position": "research_scientist",
     "brief": "RESEARCH discipline strings: source quality tiers, "
              "triangulation, contradiction hunting, recency checks, "
              "claim-vs-evidence separation, stopping rules for search"},
    {"key": "etl_hygiene", "category": "data_engineering",
     "subcategory": "etl", "job_position": "data_engineer",
     "brief": "ETL/pipeline strings: type coercion traps, timezone and "
              "encoding hazards, null semantics, join key cardinality "
              "checks, row-count reconciliation at every boundary"},
    {"key": "llm_phrasing", "category": "llm_prompting",
     "subcategory": "phrasing", "job_position": "ml_engineer",
     "brief": "LLM PHRASING/PROMPTING strings: phrasings that force "
              "structured output, abstention phrasing, asking for the "
              "decisive difference not a summary, output-shape contracts, "
              "anti-sycophancy phrasing, one-question-at-a-time discipline"},
)

#: WAVE 2 — more coverage per the owner's direction (more jobs, recovery,
#: evaluation, decomposition, uncertainty, cost) + the REPAIRED
#: first-principles brief (wave 1's abstract phrasing yielded zero
#: parseable lines; concrete examples anchor the format).
SEED_CAMPAIGN_WAVE2 = (
    {"key": "first_principles_repaired", "category": "first_principles",
     "subcategory": "decomposition", "job_position": "",
     "brief": "FIRST-PRINCIPLES prompts a practitioner can apply directly. "
              "Examples of the style wanted: 'Identify the invariant that "
              "must hold regardless of implementation', 'Reverse each "
              "assumption and check what breaks', 'Bound the answer from "
              "above and below before estimating it'. Produce more like "
              "these"},
    {"key": "job_ml_engineer", "category": "job_position",
     "subcategory": "ml_engineer", "job_position": "ml_engineer",
     "brief": "what an ML ENGINEER uniquely asks: training/serving skew, "
              "feature freshness, reproducible seeds, model rollback, "
              "monitoring drift, latency budgets, batch-vs-online parity"},
    {"key": "job_sre", "category": "job_position",
     "subcategory": "site_reliability_engineer",
     "job_position": "site_reliability_engineer",
     "brief": "what an SRE uniquely asks of a pipeline/ML system: blast "
              "radius, retry storms, idempotent recovery, saturation "
              "signals, runbook-ready failure modes, graceful degradation"},
    {"key": "job_domain_expert", "category": "job_position",
     "subcategory": "domain_expert", "job_position": "domain_expert",
     "brief": "what a DOMAIN EXPERT uniquely asks: does the target mean "
              "what the column name implies, which values are physically "
              "impossible, what changed operationally during the data's "
              "time span, which correlations are policy artifacts"},
    {"key": "failure_recovery", "category": "failure_recovery",
     "subcategory": "diagnosis_first", "job_position": "",
     "brief": "FAILURE-RECOVERY strings: classify before repairing, "
              "smallest reversible fix, minimal reproduction, when to "
              "change method vs retry, preserving evidence before rewrite"},
    {"key": "evaluation_measurement", "category": "evaluation",
     "subcategory": "success_measures", "job_position": "statistician",
     "brief": "EVALUATION strings: metric-direction traps, practical vs "
              "statistical significance, baseline discipline, selection "
              "breadth corrections, when a validation design lies"},
    {"key": "uncertainty_calibration", "category": "uncertainty",
     "subcategory": "calibration", "job_position": "statistician",
     "brief": "UNCERTAINTY strings: calibration checks, abstention "
              "thresholds, when confidence is decoration vs information, "
              "selective-risk framing"},
    {"key": "cost_compression", "category": "cost_compression",
     "subcategory": "token_economy", "job_position": "ml_engineer",
     "brief": "COST-COMPRESSION strings: repeated-context detection, "
              "summarize-then-reference, cache exact recurring answers, "
              "cheapest-mode-first discipline, when a model call is pure "
              "waste"},
)

#: The improvement loop's OWN meta-intelligence (hand-authored, registered —
#: the seed the owner asked for so the lane 'actually works'): what to look
#: for in ledgers, when to distill, what promotion requires.
IMPROVEMENT_SEED_PACK = (
    ("heuristic", "mining", "A step resolved by the model more than twice "
     "across runs is a distillation trigger: build the code node or serve "
     "the recorded advice."),
    ("heuristic", "mining", "Rank opportunities by frequency x cost x "
     "reuse-breadth; a one-off expensive call loses to a cheap weekly one."),
    ("warning", "mining", "A ledger with zero findings means the miner's "
     "vocabulary is stale, not that the runs are perfect — extend the "
     "trace bridge before concluding 'nothing to improve'."),
    ("heuristic", "distillation", "Distill the DECISION, not the prose: "
     "store the chosen estimator/features/thresholds, never the model's "
     "full essay."),
    ("checklist_item", "promotion", "Promotion needs independent evidence: "
     "an oracle the proposer does not control, on data the candidate did "
     "not shape."),
    ("warning", "promotion", "Never count a warm run as improvement without "
     "a cold control on the same task family — reuse must beat rebuilding, "
     "not just exist."),
    ("checklist_item", "digestibility", "Before staging a model output: is "
     "it parseable, categorized, provenance-stamped, deduplicated, and "
     "bounded in applicability? Missing pieces mean a structuring pass, "
     "not staging."),
    ("warning", "format", "A generation call returning zero parseable lines "
     "is a FINDING: repair the prompt with concrete format examples and "
     "retry ONCE in a new iteration — never hand-fix the output."),
    ("heuristic", "scheduling", "Run housekeeping post_run while ledgers "
     "are fresh; run capability_engineering on a schedule, never inside "
     "the solve path."),
    ("warning", "negative_transfer", "Track when served prior advice made "
     "a task WORSE than the code-rail default — negative transfer silently "
     "compounds if unmeasured."),
    ("heuristic", "coverage", "Generate strings for the job position the "
     "current task lacks: an ETL failure wants the data engineer's bank, "
     "not more modeling questions."),
    ("checklist_item", "evolution", "Each improvement cycle: mutate 2-3 "
     "existing high-utility strings (sharper, narrower, or inverted) and "
     "stage the variants beside the originals."),
    ("heuristic", "utility", "A string that has been retrieved but never "
     "changed a decision is shelf-ware: demote its rank, or rewrite it "
     "with a concrete trigger condition."),
    ("warning", "stuckness", "Two consecutive improvement cycles with zero "
     "staged candidates means the lane is stuck: change the seed campaign "
     "or the miner, do not just rerun."),
)


def improvement_seed_records() -> list:
    """The meta-pack as registered searchable records (hand-authored core
    intelligence, like the measurement pack — not runtime-generated)."""
    from ..static_architecture.store_serve import StoreRecord
    from ..static_architecture.facets import string_facets
    out = []
    for i, (kind, sub, text) in enumerate(IMPROVEMENT_SEED_PACK):
        out.append(StoreRecord(
            f"improve.{sub}.{i}", "context", text[:150],
            body={"kind": kind, "text": text, "maturity": "registered",
                  "facets": string_facets(category="improvement_meta",
                                          subcategory=sub,
                                          context_type=kind,
                                          thinking_style="improvement",
                                          scope="package",
                                          lifecycle="registered",
                                          provenance="improvement_seed_pack")},
            tags=(kind, "improvement_meta", sub, "registered")))
    return out


_LINE_CONTRACT = (
    "Return EXACTLY {n} lines and nothing else. Each line MUST be:\n"
    "KIND | subcategory | the string itself\n"
    "where KIND is one of question, heuristic, warning, checklist_item, "
    "prompt_pattern. No numbering, no markdown, no blank lines, no "
    "commentary.")


def format_repair_prompt(seed: dict, bad_text: str, *, n: int = 8) -> str:
    """The ONE-retry repair re-ask for a zero-candidate response (a stricter
    contract with a worked example — the retry runs in a NEW iteration)."""
    return ("Your previous answer could not be parsed. It began: "
            f"{(bad_text or '(empty)')[:120]!r}\n"
            f"Topic again: {seed['brief']}.\n"
            "FOLLOW THE FORMAT EXACTLY. A valid line looks like:\n"
            "heuristic | invariants | Identify the invariant that must hold "
            "regardless of implementation, and test it first.\n"
            + _LINE_CONTRACT.format(n=n))


def load_seed_dimensions(path: "str | None" = None) -> dict:
    """Parse the owner-curated dimension banks (strings/SEED-DIMENSIONS.md)
    into {bank_name: [entries]}.  The MD file is the store; nothing here is
    hardcoded."""
    path = path or os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "strings", "SEED-DIMENSIONS.md")
    banks: dict = {}
    current = None
    for line in open(path):
        line = line.rstrip()
        if line.startswith("## "):
            current = line[3:].strip()
            banks[current] = []
        elif current and line and not line.startswith("#"):
            banks[current].append(line.strip())
    return banks


def compose_seeds(n: int, *, rng_seed: int = 0,
                  path: "str | None" = None) -> list:
    """Materialize n DISTINCT composed seeds from the dimension banks —
    persona × lens × operator × target × situation × domain × era ×
    contrast.  Deterministic (seeded); the composition space exceeds ten
    million, so any requested n up to the tens of thousands is distinct by
    construction (verified, not assumed)."""
    import random
    banks = load_seed_dimensions(path)
    lenses = (banks.get("famous_scientists", [])
              + banks.get("famous_authors_thinkers", []))
    geos = banks.get("geographies", [])
    rng = random.Random(rng_seed)
    seen, out = set(), []
    guard = 0
    while len(out) < n and guard < n * 20:
        guard += 1
        persona = rng.choice(banks["personas_jobs"])
        op = rng.choice(banks["thinking_operators"])
        target = rng.choice(banks["targets"])
        situation = rng.choice(banks["situations"])
        domain = rng.choice(banks["domains"])
        era = rng.choice(banks["time_frames"])
        contrast = rng.choice(banks["contrasts"])
        extras = []
        if rng.random() < 0.35 and lenses:
            extras.append(f"through the lens of {rng.choice(lenses)}")
        if rng.random() < 0.25 and geos:
            extras.append(f"in the context of {rng.choice(geos)}")
        if rng.random() < 0.3:
            extras.append(f"under the data regime: "
                          f"{rng.choice(banks['data_regimes'])}")
        if rng.random() < 0.3:
            extras.append(f"wary of the failure: "
                          f"{rng.choice(banks['failure_regimes'])}")
        key = (persona, op, target, situation, domain, era, contrast,
               tuple(extras))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "key": f"composed_{len(out)}",
            "category": "composed_seed", "subcategory": op,
            "job_position": persona.replace(" ", "_"),
            "brief": (f"As a {persona} working on {domain}, {op} the "
                      f"{target} while facing: {situation}. Frame it as "
                      f"{contrast}, with the sensibility of {era}"
                      + ("; " + "; ".join(extras) if extras else "")
                      + ". Produce strings a practitioner can apply "
                        "directly.")})
    return out


def generation_prompt(seed: dict, *, n: int = 8) -> str:
    return (f"You are expanding a reusable intelligence bank for a "
            f"practitioner system. Topic: {seed['brief']}.\n"
            "Write sharp, specific, non-generic strings a practitioner can "
            "apply directly (each self-contained, <= 30 words).\n"
            + _LINE_CONTRACT.format(n=n))


def category_gap_prompt(existing_categories) -> str:
    return ("An intelligence bank currently has these string CATEGORIES: "
            + ", ".join(sorted(set(existing_categories)))
            + ".\nPropose the 5 most valuable MISSING categories for a "
              "system that solves data/ML/software tasks. "
            + _LINE_CONTRACT.format(n=5).replace(
                "KIND | subcategory | the string itself",
                "category_name | one_word_slug | why it matters (<=20 words)"))


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _digest(text: str) -> str:
    return hashlib.sha256(_norm(text).encode()).hexdigest()[:16]


def parse_generated(text: str, seed: "dict | None" = None) -> dict:
    """Deterministic pipe-format parser; malformed lines are UNDIGESTED."""
    candidates, undigested = [], []
    for line in (text or "").splitlines():
        line = line.strip().lstrip("-*0123456789. ").strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3 or parts[0].lower() not in VALID_KINDS \
                or len(parts[2]) < 8:
            undigested.append(line[:120])
            continue
        kind, sub, body = parts[0].lower(), parts[1][:40], parts[2][:240]
        candidates.append({
            "kind": kind, "text": body,
            "category": (seed or {}).get("category", "uncategorized"),
            "subcategory": sub or (seed or {}).get("subcategory", ""),
            "job_position": (seed or {}).get("job_position", ""),
            "digest": _digest(body)})
    return {"candidates": candidates, "undigested": undigested}


def default_bank_path() -> str:
    return os.environ.get(
        "LOOP_ENGINE_CONTEXT_CANDIDATES",
        os.path.join(os.path.expanduser("~"), ".loop-engine", "intelligence",
                     "candidates", "context.jsonl"))


def packaged_bank_path() -> str:
    """The shipped candidate snapshot, read-only at runtime."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "strings", "generated_candidates.jsonl")


def stage_candidates(cands, provenance: str, ledger=None,
                     path: "str | None" = None) -> dict:
    """Append-only staging with dedupe (batch + existing bank)."""
    if ledger is not None:
        # staging a candidate IS the learning event: it was invisible, which
        # is how a flywheel can look like it is turning without evidence.
        ledger.record(loop_id="", event="learning_candidate_staged",
                      count=len(list(cands)) if hasattr(cands, "__len__") else 0,
                      provenance=str(provenance)[:80])
    path = path or default_bank_path()
    seen = set()
    if os.path.exists(path):
        for line in open(path):
            try:
                seen.add(json.loads(line)["digest"])
            except (json.JSONDecodeError, KeyError):
                continue
    staged, deduped = 0, 0
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        for c in cands:
            if c["digest"] in seen:
                deduped += 1
                continue
            seen.add(c["digest"])
            f.write(json.dumps({**c, "maturity": "candidate",
                                "provenance": provenance},
                               ensure_ascii=False) + "\n")
            staged += 1
    return {"staged": staged, "deduped": deduped, "path": path}


def load_candidate_bank(path: "str | None" = None) -> list:
    """Candidate snapshots as experimental StoreRecords.

    With no explicit path, load the packaged read-only snapshot plus the
    user-data candidate bank. An explicit path loads only that path.
    """
    from ..static_architecture.store_serve import StoreRecord
    from ..static_architecture.facets import string_facets
    paths = [path] if path else [packaged_bank_path(), default_bank_path()]
    out, seen = [], set()
    for candidate_path in paths:
        if not os.path.exists(candidate_path):
            continue
        for line in open(candidate_path):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("digest") in seen:
                continue
            seen.add(row.get("digest"))
            out.append(StoreRecord(
                f"genstr.{row['digest']}", "context", row["text"][:150],
                body={"kind": row["kind"], "text": row["text"],
                      "maturity": row.get("maturity", "candidate"),
                      "provenance": row.get("provenance", ""),
                      "facets": string_facets(
                          category=row.get("category", ""),
                          subcategory=row.get("subcategory", ""),
                          job_position=row.get("job_position", ""),
                          scope="candidate_store",
                          lifecycle=row.get("maturity", "candidate"),
                          provenance=row.get("provenance", ""))},
                tags=(row["kind"], row.get("category", ""),
                      row.get("maturity", "candidate")),
                tier="experimental", source="generated_candidate_bank"))
    return out


def foundry_wave_as_loop(raw_outputs: list, provenance: str,
                         bank_path: "str | None" = None,
                         ledger=None) -> dict:
    """Loop-standardization ledger item #1 (2026-08-24): a foundry wave
    runs AS a PractitionerLoop on the registered continuous_improvement
    template — mine (collect raw model outputs) → rank (parse into
    candidates, malformed counted as UNDIGESTED) → engineer_candidate
    (normalize) → stage (append-only bank write with dedupe) → compare
    (report counts against the bank). Same staging semantics as the
    direct calls, now with loop evidence on the ledger. Staging only —
    promotion still belongs to the evidence gate, never this loop."""
    from ..loop.recursive_loop import Loop, StepOutcome
    from ..loop.loop_templates import TEMPLATE_LIBRARY, config_from_template
    tmpl = next(b for b in TEMPLATE_LIBRARY
                if b["template_id"] == "continuous_improvement")
    state: dict = {"raw": list(raw_outputs), "cands": [], "undigested": 0}

    def handler(lp, step, ctx):
        if step == "mine":
            return StepOutcome(output=f"mine:{len(state['raw'])} raw outputs",
                               mode="deterministic", confidence=0.95)
        if step == "rank":
            for text in state["raw"]:
                parsed = parse_generated(text)
                state["cands"].extend(parsed.get("candidates", ()))
                state["undigested"] += len(parsed.get("undigested", ()))
            return StepOutcome(
                output=f"rank:{len(state['cands'])} candidates, "
                       f"{state['undigested']} undigested",
                mode="deterministic", confidence=0.9)
        if step == "engineer_candidate":
            return StepOutcome(
                output=f"engineer:{len(state['cands'])} normalized",
                mode="deterministic", confidence=0.9)
        if step == "stage":
            state["staged"] = stage_candidates(
                state["cands"], provenance, path=bank_path)
            return StepOutcome(
                output=f"stage:{state['staged']['staged']} staged, "
                       f"{state['staged']['deduped']} deduped",
                mode="deterministic", confidence=0.95)
        if step == "compare":
            bank = load_candidate_bank(bank_path)
            return StepOutcome(output=f"compare:bank now {len(bank)} records",
                               mode="deterministic", confidence=0.9)
        return StepOutcome(output=f"{step}:done", mode="deterministic",
                           confidence=0.9)

    loop = Loop(f"foundry wave: {provenance}",
                config_from_template(tmpl, power="standard"), ledger=ledger)
    res = loop.run(handler=handler, max_steps=len(loop.steps()) + 1)
    return {"loop_id": res.loop_id, "model_calls": res.model_calls,
            "stopped": res.stopped, "candidates": len(state["cands"]),
            "undigested": state["undigested"],
            "staged": state.get("staged", {})}


def seed_pack_paths() -> tuple:
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "strings")
    return (os.path.join(base, "core_seed_intelligence_v2.jsonl"),
            os.path.join(base, "core_seed_intelligence_v2.manifest.json"))


def load_seed_pack(verify: bool = True) -> dict:
    """Load the 1,000-record core seed pack (owner master prompt Appendix A)
    with its manifest, integrity-verified FAIL-CLOSED: the recomputed content
    digest must match the manifest, every record must be maturity=candidate
    (automatic preference is forbidden by the pack contract), and the
    category counts must match. Returns {"records", "manifest"}."""
    import hashlib
    path, mpath = seed_pack_paths()
    manifest = json.load(open(mpath))
    raw = open(path, "rb").read()
    if verify:
        digest = hashlib.sha256(raw).hexdigest()
        if digest != manifest["content_digest_sha256"]:
            raise ValueError("seed pack digest mismatch — refusing to load "
                             "(fail closed; rebuild or restore the pack)")
    records = [json.loads(l) for l in raw.decode().splitlines()]
    bad = [r["string_id"] for r in records if r.get("maturity") != "candidate"]
    if bad:
        raise ValueError(f"seed pack records not candidate: {bad[:3]} — "
                         "promotion happens only through the evidence gate")
    return {"records": records, "manifest": manifest}


def seed_pack_store_records(records: list) -> list:
    """Seed records as searchable StoreRecords for the ONE Retriever."""
    from ..static_architecture.store_serve import StoreRecord
    from ..static_architecture.facets import string_facets
    return [StoreRecord(r["string_id"], "context", r["text"],
                        body={"category": r["category"],
                              "subcategory": r["subcategory"],
                              "role": r["role"],
                              "stage": list(r.get("stage", ())),
                              "possible_code_target":
                                  r.get("possible_code_target", ""),
                              "scope": r.get("scope", ""),
                              "maturity": r["maturity"],
                              "provenance": r.get("provenance", ""),
                              "digest": r.get("digest", ""),
                              "facets": string_facets(
                                  category=r["category"],
                                  subcategory=r["subcategory"],
                                  scope=r.get("scope", ""),
                                  lifecycle=r["maturity"],
                                  provenance=r.get("provenance", ""))},
                        tags=tuple(r.get("tags", ())), tier="experimental",
                        source="core_seed_candidate_pack")
            for r in records]


def self_test() -> dict:
    import tempfile
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    seed = SEED_CAMPAIGN[0]

    # 1. the parser accepts the contract and counts malformed lines as
    # UNDIGESTED — never repaired by guesswork.
    text = ("question | idempotency | Can every pipeline stage be re-run "
            "without duplicating rows or effects?\n"
            "warning | schema_drift | A silently widened column is a "
            "future join explosion; pin schemas at every boundary.\n"
            "banana | nope | not a valid kind\n"
            "just prose without pipes\n"
            "heuristic | keys | Count distinct join keys on BOTH sides "
            "before any merge; explosion is cheaper to prevent than debug.")
    parsed = parse_generated(text, seed)
    check("parser_honors_the_contract_and_counts_undigested",
          len(parsed["candidates"]) == 3 and len(parsed["undigested"]) == 2
          and parsed["candidates"][0]["job_position"] == "data_engineer"
          and parsed["candidates"][0]["category"] == "job_position")

    # 2. staging is append-only with dedupe across batches.
    tmp = tempfile.mktemp(suffix=".jsonl")
    r1 = stage_candidates(parsed["candidates"], "test-run-1", path=tmp)
    r2 = stage_candidates(parsed["candidates"], "test-run-2", path=tmp)
    check("staging_appends_and_dedupes",
          r1["staged"] == 3 and r2["staged"] == 0 and r2["deduped"] == 3
          and sum(1 for _ in open(tmp)) == 3)

    # 3. the loader serves the bank as faceted, candidate-labeled records.
    recs = load_candidate_bank(tmp)
    check("bank_loads_as_faceted_candidate_records",
          len(recs) == 3
          and all(r.body["maturity"] == "candidate" for r in recs)
          and recs[0].body["facets"]["job_position"] == "data_engineer"
          and all(r.body["provenance"] == "test-run-1" for r in recs),
          "candidates never blur into registered; provenance rides each row")

    # 4. the bank flows through the one search DAG.
    from ..static_architecture.store_serve import SolverStore
    store = SolverStore(core_records=recs)
    hidden = store.search("join keys merge explosion")
    store.enable_tier("experimental")
    hit = store.search("join keys merge explosion")
    check("generated_strings_are_searchable",
          not hidden["hits"] and hit["hits"]
          and "join keys" in hit["hits"][0]["title"].lower(),
          "candidate Context is searchable only after explicit tier enablement")

    # 5. the seed campaign covers the owner's requested fronts, and wave 2
    # extends coverage (more jobs, recovery, evaluation, uncertainty, cost)
    # including the REPAIRED first-principles brief with concrete examples.
    cats = {s["category"] for s in SEED_CAMPAIGN}
    cats2 = {s["category"] for s in SEED_CAMPAIGN_WAVE2}
    check("seed_campaign_covers_the_requested_fronts",
          {"job_position", "first_principles", "research",
           "data_engineering", "llm_prompting"} <= cats
          and {"failure_recovery", "evaluation", "uncertainty",
               "cost_compression"} <= cats2
          and any("Identify the invariant" in s["brief"]
                  for s in SEED_CAMPAIGN_WAVE2)
          and len(SEED_CAMPAIGN) + len(SEED_CAMPAIGN_WAVE2) >= 16)

    # 6. the improvement loop's OWN meta-pack is registered, searchable
    # intelligence (mining heuristics, promotion standards, format repair,
    # negative-transfer warnings) — the seed that makes the lane self-aware.
    meta = improvement_seed_records()
    metastore = SolverStore(core_records=meta)
    m1 = metastore.search("distillation trigger model resolved twice")
    m2 = metastore.search("negative transfer served advice worse")
    check("improvement_meta_pack_is_registered_and_searchable",
          len(meta) >= 14
          and all(r.body["maturity"] == "registered" for r in meta)
          and m1["hits"] and m2["hits"]
          and m1["hits"][0]["facets"]["category"] == "improvement_meta")

    # 7. the format-repair node produces a stricter re-ask carrying a worked
    # example and the offending prefix — the retry is a NEW iteration.
    rp = format_repair_prompt(SEED_CAMPAIGN[4], "Here are some ideas:\n1. ...")
    check("format_repair_reasks_with_a_worked_example",
          "could not be parsed" in rp and "heuristic | invariants |" in rp
          and "Here are some ideas" in rp)

    # 8. the owner's SEED DIMENSIONS: curated banks load from the MD store,
    # and the composer materializes >= 10,000 DISTINCT seeds
    # deterministically (verified by construction, not assumed).
    banks = load_seed_dimensions()
    curated = sum(len(v) for v in banks.values())
    s1 = compose_seeds(1000, rng_seed=7)
    s2 = compose_seeds(1000, rng_seed=7)
    s10k = compose_seeds(10000, rng_seed=1)
    check("seed_dimension_banks_load_from_the_md_store",
          {"personas_jobs", "famous_scientists", "famous_authors_thinkers",
           "geographies", "time_frames", "situations", "thinking_operators",
           "targets", "domains", "failure_regimes"} <= set(banks)
          and curated >= 300,
          f"{len(banks)} banks, {curated} curated entries")
    check("composer_yields_10k_distinct_deterministic_seeds",
          len(s10k) == 10000
          and len({x["brief"] for x in s10k}) == 10000
          and s1 == s2
          and all(x["category"] == "composed_seed" for x in s1)
          and "As a " in s1[0]["brief"],
          "10,000 distinct briefs; same rng_seed -> identical output")

    # 12. THE SEED PACK (owner master prompt Appendix A, charter section 24):
    # exact count, unique ids, 20 categories x 50, digest-verified load,
    # all candidate — and a tampered manifest is REFUSED, never absorbed.
    pack = load_seed_pack()
    recs, man = pack["records"], pack["manifest"]
    from collections import Counter
    cc = Counter(r["category"] for r in recs)
    check("seed_pack_1000_records_20x50_all_candidate",
          len(recs) == 1000 and man["record_count"] == 1000
          and len({r["string_id"] for r in recs}) == 1000
          and len(cc) == 20 and all(v == 50 for v in cc.values())
          and all(r["maturity"] == "candidate" for r in recs),
          f"{len(recs)} records, {len(cc)} categories, digest verified")
    import json as _json
    _p, _mp = seed_pack_paths()
    _good = _json.load(open(_mp))
    _tampered = dict(_good, content_digest_sha256="0" * 64)
    _json.dump(_tampered, open(_mp, "w"))
    refused = False
    try:
        load_seed_pack()
    except ValueError:
        refused = True
    finally:
        _json.dump(_good, open(_mp, "w"), indent=1)
    check("seed_pack_tampered_manifest_refused", refused,
          "digest mismatch fails closed")

    # 13. the pack is REACHABLE through the one Retriever: an exact-term
    # query surfaces the Popper falsifiability lens from the 1000.
    from ..static_architecture.retrieval import Retriever
    r_seed = Retriever(seed_pack_store_records(recs))
    hits = r_seed.search("falsifiability and severe tests", mode="lexical")
    check("seed_pack_searchable_through_one_retriever",
          hits["hits"] and hits["hits"][0]["record_id"] == "SI-0882",
          f"top: {hits['hits'][0]['record_id'] if hits['hits'] else 'none'}")

    # 14. LOOP-STANDARDIZATION #1: a foundry wave runs AS a
    # continuous_improvement loop — same staging semantics, loop evidence
    # on the ledger, zero model calls, and staging-only (no promotion).
    import tempfile as _tf
    from ..loop.recursive_loop import LoopLedger
    _bank = os.path.join(_tf.mkdtemp(prefix="fwave_"), "bank.jsonl")
    _raw = ["question | idempotency | Will rerunning this pipeline "
            "produce byte-identical output or only row-count parity?",
            "not parseable at all"]
    _lg = LoopLedger()
    wave = foundry_wave_as_loop(_raw, "retro-test-wave", bank_path=_bank,
                                ledger=_lg)
    steps_seen = [e.get("step") for e in _lg.events
                  if e.get("event") == "run_step"]
    check("foundry_wave_runs_as_continuous_improvement_loop",
          wave["model_calls"] == 0 and wave["stopped"] == "done"
          and wave["candidates"] >= 1 and wave["undigested"] >= 1
          and wave["staged"].get("staged", 0) >= 1
          and steps_seen[:4] == ["load_history", "audit_intelligence",
                                 "mine", "rank"]
          and "stage" in steps_seen and "compare" in steps_seen,
          f"wave loop {wave['loop_id']}: {wave['candidates']} candidates "
          f"staged through the template beats")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


def validate_staged_candidate(candidate, *, passed: bool, evidence: str = "",
                              ledger=None) -> dict:
    """Record that a staged candidate passed (or failed) its quarantined test.

    Staging and validating are different facts and were sharing one silence:
    ``learning.candidate.staged`` said something was proposed, and nothing
    said whether it survived. Validation is NOT promotion — that remains a
    separate authority; this only records that the evidence exists."""
    rec = {"record_type": "learning_candidate_validation/v1",
           "candidate": str(getattr(candidate, "record_id", candidate))[:80],
           "passed": bool(passed), "evidence": str(evidence)[:200],
           "note": "validated is not promoted — promotion is a separate gate"}
    if ledger is not None and passed:
        ledger.record(loop_id="", event="learning_candidate_validated",
                      candidate=rec["candidate"], evidence=rec["evidence"][:80])
    return rec
