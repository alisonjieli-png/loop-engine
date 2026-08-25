"""Context enrichment — generate personas/questions for a domain, ONCE, stored.

Owner design (2026-08-23): after "Understand the problem and assemble the
relevant context", the practitioner may need MORE context than the banks hold —
a heart-disease problem wants heart-disease expert personas, personas from
completely diametric fields, and field-specific question forms.  This is NOT a
seventh kernel node.  It is:

  1. a deterministic **coverage probe** in node 1: do the stored banks cover
     this problem's domain?  Weak coverage becomes a Situation signal;
  2. a high-bias **candidate action** (`enrich:<domain>`) in node 2, proposed
     only when coverage is weak AND the (tunable, optional) EnrichmentPolicy is
     on;
  3. one structured generation in node 4 that parses into STANDARD records —
     personas and question forms with ``llm_generated_once`` provenance at the
     experimental tier — written through the normal stores, so everything
     generated is immediately searchable, permanently reusable, and never
     regenerated for the next similar problem.

Deep needs (latest publications, real-time search) stay what they already are:
research actions that spawn child practitioners.  Enrichment only grows the
banks of personas / questions / key phrases — the secret-sauce inventory.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable, Sequence

from ..static_architecture.model_call import AskSpec, execute_ask
from ..static_architecture.store_serve import SolverStore, StoreRecord
from ..strings.question_engine import QuestionForm, register_generated_form

# Words too generic to indicate domain coverage on their own.
_STOP = {"the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "with",
         "problem", "task", "data", "using", "model", "solve", "predict",
         "classification", "regression", "competition", "kaggle"}


def domain_terms(problem: str, k: int = 6) -> tuple:
    """The problem's distinguishing domain words (deterministic)."""
    words = [w for w in re.findall(r"[a-z][a-z\-]+", problem.lower())
             if w not in _STOP and len(w) > 3]
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return tuple(out[:k])


@dataclass
class CoverageReport:
    domain: tuple
    persona_hits: int
    question_hits: int
    score: float                 # 0..1 — how covered this domain is
    weak: bool

    def to_dict(self) -> dict:
        return {"domain": list(self.domain), "persona_hits": self.persona_hits,
                "question_hits": self.question_hits,
                "score": round(self.score, 3), "weak": self.weak}


def coverage_probe(store: SolverStore, problem: str, *,
                   weak_below: float = 0.34) -> CoverageReport:
    """Do the banks cover this problem's domain?  Deterministic: search the
    store for the domain terms among personas and questions and score the
    reach.  Weak coverage is a signal, never an automatic model call."""
    terms = domain_terms(problem)
    if not terms:
        return CoverageReport((), 0, 0, 1.0, False)
    q = " ".join(terms)
    from ..loop.intelligence_loops import search_as_loop
    p_hits = len(search_as_loop(store, q, kind="persona",
                                top_n=5)["value"]["hits"])
    q_hits = len(search_as_loop(store, q, kind="question",
                                top_n=5)["value"]["hits"])
    score = min(1.0, (p_hits + q_hits) / 6.0)
    return CoverageReport(terms, p_hits, q_hits, score, score < weak_below)


@dataclass
class EnrichmentPolicy:
    """The tunable switchboard for generation — OFF by default (it costs a
    model call), every count adjustable."""
    enabled: bool = False
    n_domain_personas: int = 3
    n_diametric_personas: int = 2
    n_questions: int = 4
    n_key_phrases: int = 4
    weak_below: float = 0.34


_ENRICH_CONTRACT = (
    'JSON object: {"domain_personas": [{"name": str, "description": str}],'
    ' "diametric_personas": [{"name": str, "field": str, "description": str}],'
    ' "questions": [{"name": "snake_slug", "template": "text with {task} '
    'placeholder", "answer_shape": one of ["proposals","ranking","score",'
    '"elimination","verdict","comparison","decomposition","list"]}],'
    ' "key_phrases": [str]}')


def generate_enrichment(problem: str, policy: EnrichmentPolicy, *,
                        store: SolverStore, forms: dict,
                        ask: Callable = execute_ask,
                        models: Sequence[str] | None = None) -> dict:
    """ONE structured generation, parsed into standard records, stored forever.

    Returns the receipt: what was generated, what was stored, and that nothing
    entered above the experimental tier.  A failed or unparseable generation
    stores NOTHING and says so — junk never enters the banks."""
    if not policy.enabled:
        return {"record_type": "enrichment/v1", "enabled": False, "stored": 0}
    spec = AskSpec(
        question=(f"Problem domain: {problem}\n\n"
                  f"Generate exactly {policy.n_domain_personas} expert personas "
                  f"FROM this domain, {policy.n_diametric_personas} personas "
                  f"from COMPLETELY DIAMETRIC fields (far-transfer thinkers), "
                  f"{policy.n_questions} domain-specific question templates "
                  f"(each must contain the literal placeholder {{task}}), and "
                  f"{policy.n_key_phrases} key phrases that make responses in "
                  f"this domain more precise."),
        output_contract=_ENRICH_CONTRACT, temperature=0.8)
    if models:
        spec.models = tuple(models)
    res = ask(spec)
    if not getattr(res, "ok", False):
        return {"record_type": "enrichment/v1", "enabled": True, "stored": 0,
                "error": getattr(res, "error", "ask failed")}
    try:
        s = res.text[res.text.find("{"):res.text.rfind("}") + 1]
        data = json.loads(s)
    except Exception:                                           # noqa: BLE001
        return {"record_type": "enrichment/v1", "enabled": True, "stored": 0,
                "error": "unparseable generation — nothing stored"}

    dom = "_".join(domain_terms(problem)[:2]) or "general"
    stored = 0
    for i, p in enumerate((data.get("domain_personas") or [])
                          [:policy.n_domain_personas]):
        store.add(StoreRecord(
            record_id=f"persona.gen.{dom}.{i}", kind="persona",
            title=str(p.get("name", ""))[:80],
            body={"description": str(p.get("description", "")),
                  "provenance": "llm_generated_once", "domain": dom},
            tags=("persona", dom, "domain_expert"), tier="experimental"))
        stored += 1
    for i, p in enumerate((data.get("diametric_personas") or [])
                          [:policy.n_diametric_personas]):
        store.add(StoreRecord(
            record_id=f"persona.gen.{dom}.diametric.{i}", kind="persona",
            title=str(p.get("name", ""))[:80],
            body={"description": str(p.get("description", "")),
                  "field": str(p.get("field", "")),
                  "provenance": "llm_generated_once", "domain": dom},
            tags=("persona", dom, "diametric", "far_transfer"),
            tier="experimental"))
        stored += 1
    forms_added = 0
    for qf in (data.get("questions") or [])[:policy.n_questions]:
        name = re.sub(r"[^a-z0-9_]+", "_", str(qf.get("name", "")).lower())
        tmpl = str(qf.get("template", ""))
        shape = str(qf.get("answer_shape", "proposals"))
        if not name or "{task}" not in tmpl:
            continue                          # malformed — refuse, don't store
        try:
            register_generated_form(forms, name=f"{dom}__{name}",
                                    template=tmpl, answer_shape=shape,
                                    description=f"generated for {dom}")
            store.add(StoreRecord(
                record_id=f"qform.gen.{dom}.{name}", kind="question",
                title=tmpl[:80],
                body={"template": tmpl, "answer_shape": shape,
                      "provenance": "llm_generated_once", "domain": dom},
                tags=("question_form", dom), tier="experimental"))
            stored += 1
            forms_added += 1
        except ValueError:
            continue
    for i, phrase in enumerate((data.get("key_phrases") or [])
                               [:policy.n_key_phrases]):
        store.add(StoreRecord(
            record_id=f"phrase.gen.{dom}.{i}", kind="context",
            title=str(phrase)[:80],
            body={"phrase": str(phrase), "provenance": "llm_generated_once",
                  "domain": dom},
            tags=("key_phrase", dom), tier="experimental"))
        stored += 1
    return {"record_type": "enrichment/v1", "enabled": True, "domain": dom,
            "stored": stored, "forms_added": forms_added,
            "tokens": getattr(res, "total_tokens", 0)}


# ---------------------------------------------------------------------------
# Self-test — offline: stub ask, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    from ..static_architecture.model_call import AskResult
    from ..strings.question_engine import core_forms
    from ..static_architecture.store_serve import core_seed
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    problem = ("heart disease classification from patient echocardiogram "
               "measurements")
    store = SolverStore(core_records=core_seed())

    # 1. the coverage probe detects that the banks do NOT cover this domain.
    rep = coverage_probe(store, problem)
    check("weak_domain_coverage_is_detected_deterministically",
          rep.weak and "heart" in rep.domain,
          f"domain {rep.domain}, score {rep.score} -> weak")

    # 2. policy off = a no-op that stores nothing (enrichment is opt-in).
    forms = core_forms()
    off = generate_enrichment(problem, EnrichmentPolicy(enabled=False),
                              store=store, forms=forms)
    check("enrichment_is_optional_off_stores_nothing",
          off["stored"] == 0 and off["enabled"] is False,
          "the tunable policy defaults OFF — generation costs a model call")

    # 3. one stubbed generation stores personas (domain + DIAMETRIC),
    # question forms, and key phrases as STANDARD records.
    def stub(spec: AskSpec):
        return AskResult(ok=True, text=json.dumps({
            "domain_personas": [
                {"name": "an interventional cardiologist",
                 "description": "20 years of cath-lab outcomes"},
                {"name": "a cardiac electrophysiologist",
                 "description": "arrhythmia specialist"}],
            "diametric_personas": [
                {"name": "a bridge structural engineer", "field": "civil "
                 "engineering", "description": "fatigue and load cycles"}],
            "questions": [
                {"name": "risk_stratify", "template": "For {task}, stratify "
                 "the risk factors by modifiability.",
                 "answer_shape": "ranking"}],
            "key_phrases": ["ejection fraction", "ST elevation"]}),
            model_used="stub", total_tokens=42)
    pol = EnrichmentPolicy(enabled=True, n_domain_personas=2,
                           n_diametric_personas=1, n_questions=1,
                           n_key_phrases=2)
    out = generate_enrichment(problem, pol, store=store, forms=forms,
                              ask=stub)
    check("generation_stores_personas_questions_and_phrases_as_records",
          out["stored"] == 6 and out["forms_added"] == 1,
          f"stored {out['stored']} records incl. a diametric persona and a "
          f"registered question form")

    # 4. generated items are RETRIEVABLE via the strict search DAG (tier on)
    # and carry llm_generated_once provenance at experimental tier.
    store.enable_tier("experimental")
    hit = store.search("cardiologist heart", kind="persona")
    got = store.serve(hit["hits"][0]["record_id"]) if hit["hits"] else None
    check("generated_context_is_searchable_and_provenance_tagged",
          got is not None and got.tier == "experimental"
          and got.body.get("provenance") == "llm_generated_once",
          "generated once, stored through the standard stores, reusable "
          "forever, never above experimental by assertion")

    # 5. the new question form multiplies like any shipped form.
    from ..strings.question_engine import multiply
    dom_forms = {k: f for k, f in forms.items() if k.startswith("heart")}
    variants = multiply(dom_forms, personas=("an interventional "
                        "cardiologist",), slot_values={"task": problem},
                        limit=3)
    check("a_generated_form_multiplies_like_any_shipped_form",
          variants and "stratify" in variants[0].question,
          "the domain question joins the deterministic multiplication engine")

    # 6. coverage improves after enrichment — the probe sees the new records.
    rep2 = coverage_probe(store, problem)
    check("coverage_improves_after_enrichment",
          rep2.score > rep.score,
          f"score {rep.score} -> {rep2.score}")

    # 7. a malformed generation stores NOTHING (junk never enters the banks).
    bad = generate_enrichment(problem, pol, store=store, forms=forms,
                              ask=lambda s: AskResult(ok=True,
                                                      text="not json at all"))
    check("a_malformed_generation_stores_nothing", bad["stored"] == 0
          and "error" in bad,
          "refusal beats acceptance for bank contents")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "enrichment_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
