"""Interrogation — the clever, novel, adversarial questions an expert asks, as
Context Intelligence, plus the continuous-improvement presets that run them.

Owner insight (2026-08-23): the gap between a naive AI-generated solution and a
human-expert-supervised one is not magic — it is the QUESTIONS the expert asks to
interrogate the work: are there patterns in the residuals? clusters or latent
structure in the raw data? hidden patterns the model misses? is this dataset
noisy — how do we reach a stable plateau, not a fragile spike? are there errors in
the train/test/CV splits, and patterns in the errors of the errors?  There is
nothing special about the questions themselves — the machine runs the analysis and
answers them — which means we can DISTILL that expertise into reusable intelligence.

So this module carries:

  * an INTERROGATION BANK — clever/adversarial/novel questions as Strings, in
    drill-down CATEGORIES → subcategories, each declaring whether a CODE node or an
    LLM answers it (``answerable_by``).  A code-answerable interrogation is a
    distillation target: a deterministic node that computes the measure, feeding
    an LLM only for the final judgement.
  * continuous-improvement PRESETS — named self-improvement Goal Strings the
    review practitioner runs: analyze a string category vs runtime history; find
    strings that could become deterministic nodes; adversarially review each
    solution; transfer strategies across domains; enumerate best/worst ways.

Everything here is a String (a question / a goal); answering and distilling are
Code Nodes and the practitioner loop.  It composes with [[intelligence_strings.py]]
(the substrate), [[solution_shaping.py]] (decomposition), and [[housekeeping.py]]
(the presets feed a continuous-improvement run).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

# Drill-down taxonomy: category → subcategories.  The review practitioner can
# focus generally, on a category, or on a subcategory (and the same for code).
INTERROGATION_CATEGORIES = {
    "residual_analysis": ("residual_patterns", "heteroscedasticity",
                          "autocorrelation"),
    "latent_structure": ("clusters", "latent_variables", "undetected_patterns"),
    "noise_and_stability": ("noise_level", "plateau_vs_spike", "sensitivity"),
    "data_quality": ("split_errors", "label_errors", "streamlining",
                    "cross_split_leakage"),
    "error_patterns": ("systematic_bias", "errors_of_errors", "error_clusters"),
    "generalization": ("train_cv_gap", "distribution_shift", "overfit"),
    "adversarial_review": ("best_vs_worst", "preventable_failures",
                          "missing_intelligence"),
    "cross_domain": ("analogies", "transfer", "unrelated_domain_lessons"),
    "decomposition": ("sub_models", "ensembles", "staging"),
    "integration": ("as_string", "as_node", "weight_and_bias"),
}
ANSWERABLE_BY = ("code", "llm", "either")


@dataclass(frozen=True)
class InterrogationQuestion:
    """One expert question — a String.  ``answerable_by`` says whether a code node
    can compute the answer (a distillation target) or an LLM must judge it."""
    question: str
    category: str
    subcategory: str = ""
    how_to_answer: str = ""             # the analysis that answers it
    answerable_by: str = "either"

    def __post_init__(self):
        if self.category not in INTERROGATION_CATEGORIES:
            raise ValueError(f"category must be one of "
                             f"{tuple(INTERROGATION_CATEGORIES)}")
        if self.answerable_by not in ANSWERABLE_BY:
            raise ValueError(f"answerable_by must be one of {ANSWERABLE_BY}")


def _q(cat, sub, question, how, by="either"):
    return InterrogationQuestion(question, cat, sub, how, by)


def interrogation_bank() -> list:
    """The seed bank of expert interrogation questions (the owner's examples plus
    adversarial + cross-domain).  A String starter — grow it by distillation."""
    return [
        # --- residuals -----------------------------------------------------
        _q("residual_analysis", "residual_patterns",
           "Are there patterns in the residuals (structure the model failed to "
           "capture)?", "plot/curve residuals vs fitted and vs each feature; test "
           "for non-randomness", "code"),
        _q("residual_analysis", "heteroscedasticity",
           "Does residual variance change across the range (heteroscedasticity)?",
           "Breusch-Pagan / White test; residual spread by bin", "code"),
        _q("residual_analysis", "autocorrelation",
           "Are residuals autocorrelated (missed temporal/spatial dependence)?",
           "Durbin-Watson / ACF of residuals", "code"),
        # --- latent structure ---------------------------------------------
        _q("latent_structure", "clusters",
           "Are there clusters in the raw data that could mean something the model "
           "isn't using?", "unsupervised clustering + silhouette; compare cluster "
           "membership to errors", "code"),
        _q("latent_structure", "latent_variables",
           "Are there hidden/latent variables or interactions the model is not "
           "detecting — and should we address them?", "factor analysis / PCA; test "
           "engineered interactions; ask the model for candidate confounders",
           "either"),
        _q("latent_structure", "undetected_patterns",
           "How would we even TEST for a hidden pattern the model misses?",
           "hold out a structured subset; train a probe on residuals; look for "
           "learnable residual structure", "either"),
        # --- noise & stability --------------------------------------------
        _q("noise_and_stability", "noise_level",
           "This dataset looks noisy — how do we address it so the solution is "
           "stable?", "estimate label/measurement noise; robust losses; "
           "denoising; repeated CV variance", "code"),
         _q("noise_and_stability", "plateau_vs_spike",
            "Is this a thick stable plateau or a fragile spike (would it survive a "
            "seed/fold/feature perturbation)?", "sensitivity sweep over seeds, "
            "folds, feature subsets; report the spread", "code"),
        _q("noise_and_stability", "sensitivity",
           "Which single input change moves the result most, and is that "
           "dependence acceptable?", "one-at-a-time input perturbation; rank "
           "inputs by result change", "code"),
         # --- data quality (errors in the splits) --------------------------
         _q("data_quality", "split_errors",
            "Are there errors in the training, test, and CV data — should we "
            "streamline it?", "schema + range + duplicate + type audit across "
            "splits; label spot-checks", "code"),
        _q("data_quality", "label_errors",
           "Are any labels themselves wrong, and would fixing them change the "
           "conclusion?", "manual spot-check a labeled sample against the source; "
           "estimate the label error rate", "code"),
        _q("data_quality", "streamlining",
           "Could the data be simplified without losing the signal we rely on?",
           "measure result change when dropping redundant columns, constants, and "
           "duplicate rows", "code"),
         _q("data_quality", "cross_split_leakage",
           "Is anything leaking across train/test/CV (identity, time, target "
           "proxy)?", "group/time-aware split audit; near-duplicate detection "
           "across splits", "code"),
        # --- error patterns (errors of errors) ----------------------------
        _q("error_patterns", "systematic_bias",
           "Are the errors systematic (a segment the model consistently gets "
           "wrong)?", "error rate by segment/feature bin; slice analysis", "code"),
         _q("error_patterns", "errors_of_errors",
            "Are there patterns within the errors — and within the errors OF the "
            "errors (meta-structure)?", "model the residual, then model the "
            "residual of that; look for repeated structure", "either"),
        _q("error_patterns", "error_clusters",
           "Do the errors cluster into a small number of repeating types that one "
           "targeted fix would remove?", "cluster failures by message, failing "
           "input shape, and step; count the share each cluster covers", "code"),
         # --- generalization (does it hold beyond the sample?) ---------------
        _q("generalization", "train_cv_gap",
           "Is the gap between training and cross-validation performance a real "
           "signal or a measurement artifact?", "repeat CV with several seeds and "
           "folds; report the spread of the gap", "code"),
        _q("generalization", "distribution_shift",
           "How would this result behave on inputs from a different time, source, "
           "or population than the ones we tested?", "profile feature drift between "
           "the development sample and any newer sample; test on the shifted "
           "slice", "code"),
        _q("generalization", "overfit",
           "Which parts of the result depend on details of THIS sample rather than "
           "on the underlying problem?", "ablate features and parameters; check "
           "which removals barely change the outcome", "either"),
         # --- adversarial review (for solving AND improvement) -------------
         _q("adversarial_review", "best_vs_worst",
            "Is this the BEST way to solve it? What would the WORST way look like, "
            "and are we accidentally near it?", "compare against strong and naive "
            "baselines; rank approaches", "either"),
         _q("adversarial_review", "preventable_failures",
            "Were there errors, and what would have PREVENTED them? What string or "
            "code intelligence would have helped?", "trace the failure to its "
            "earliest cause; name the missing reusable asset", "llm"),
        _q("adversarial_review", "missing_intelligence",
           "What did we NOT know when this result was accepted, and which missing "
           "fact could flip the conclusion?", "list the assumptions the acceptance "
           "rested on; name the single most load-bearing unknown", "llm"),
         # --- cross-domain --------------------------------------------------
        _q("cross_domain", "analogies",
           "Which solved problem in another field has the same structure as this "
           "one, and what part of its solution transfers?", "state this problem's "
           "structure abstractly; search for structural matches in other domains", "llm"),
         _q("cross_domain", "unrelated_domain_lessons",
            "What can we learn from a completely different domain that faced an "
            "analogous problem?", "research analogous problems in other fields; map "
            "the transferable structure", "llm"),
         _q("cross_domain", "transfer",
            "Is there a theory or method from an unrelated project that applies "
            "here?", "retrieve prior runs across domains; test the analogy", "llm"),
         # --- decomposition (splitting the problem well) ---------------------
        _q("decomposition", "sub_models",
           "Would the problem become easier if split into independently solvable "
           "sub-problems, each with its own verifiable output?", "draft a split "
           "where each part has a checkable contract; test the parts separately", "either"),
        _q("decomposition", "ensembles",
           "Would several diverse weaker approaches, combined, beat one strong "
           "approach here?", "run diverse simple approaches; test a vote or stack "
           "against the single best", "code"),
        _q("decomposition", "staging",
           "Is there a natural order of stages where an early cheap stage filters "
           "or narrows the work of a later expensive stage?", "measure per-stage "
           "cost; check whether a cheap first stage removes most inputs", "code"),
         # --- integration (distillation back into the library) -------------
        _q("integration", "as_string",
           "Should this finding become a stored question, note template, or "
           "guidance string instead of being answered from scratch every time?",
           "check whether the finding generalizes beyond this task; if yes, name "
           "the exact string kind", "either"),
         _q("integration", "as_node",
           "Could answering this repeatedly become a deterministic/semi-"
           "deterministic code node instead of an LLM call?", "check if the answer "
           "is a computed measure; if so, author a node", "either"),
        _q("integration", "weight_and_bias",
           "How do we integrate this finding into Context Intelligence? Which "
           "category, weight, bias, and preference?", "classify the finding; "
           "propose the string kind + tags + a demotable bias", "llm"),
    ]


def interrogate(*, category: "str | None" = None, subcategory: "str | None" = None,
                answerable_by: "str | None" = None) -> list:
    """Drill-down selection: all questions, or a category, or a subcategory, or
    only the code-answerable ones (the distillation targets)."""
    out = interrogation_bank()
    if category:
        out = [q for q in out if q.category == category]
    if subcategory:
        out = [q for q in out if q.subcategory == subcategory]
    if answerable_by:
        out = [q for q in out if q.answerable_by == answerable_by]
    return out


def question_records() -> list:
    """The interrogation questions as searchable String resources (role=question)."""
    from ..core.store_serve import StoreRecord
    recs = []
    for i, q in enumerate(interrogation_bank()):
        recs.append(StoreRecord(
            record_id=f"interro.{q.category}.{i}", kind="question",
            title=q.question[:80],
            body={"category": q.category, "subcategory": q.subcategory,
                  "how_to_answer": q.how_to_answer,
                  "answerable_by": q.answerable_by, "role": "interrogation"},
            tags=("interrogation", q.category, q.subcategory, q.answerable_by),
            tier="core"))
    return recs


# ---------------------------------------------------------------------------
# Continuous-improvement PRESETS — named self-improvement Goal Strings.
# ---------------------------------------------------------------------------

IMPROVEMENT_PRESETS = {
    "improve_string_category":
        "Analyze the Context Intelligence in category '{category}' and, from "
        "runtime history, propose what could be improved, added, reweighted, or "
        "retired.",
    "string_to_node":
        "Review the Context Intelligence in category '{category}' and identify "
        "what could become a deterministic or semi-deterministic CODE NODE, so a "
        "future run answers it with zero or low LLM tokens.",
    "adversarial_solution_review":
        "Adversarially interrogate each recent solution: is this the best way? "
        "the worst way? were there errors? what would have prevented them? what "
        "string or code intelligence would have helped?",
    "cross_domain_transfer":
        "For recent projects, research and propose cross-domain analogies and "
        "transferable strategies from unrelated fields, and how to encode them.",
    "top_n_ways":
        "Enumerate the top {n} best and top {n} worst ways to approach "
        "'{task_family}', and distill the difference into string/code intelligence.",
    "distill_deliberation":
        "Find recurring model deliberations and propose a code node that computes "
        "the decisive measures, feeding an LLM only for the final judgement.",
}


def preset_goal(preset: str, **params) -> str:
    """Fill a preset into a self-improvement Goal String (a String routed into a
    normal continuous-improvement run — same loop, different goal)."""
    if preset not in IMPROVEMENT_PRESETS:
        raise KeyError(f"no preset {preset!r}; have {sorted(IMPROVEMENT_PRESETS)}")
    p = {"category": "any", "n": 10, "task_family": "this task family"}
    p.update(params)
    return IMPROVEMENT_PRESETS[preset].format(**p)


def preset_records() -> list:
    """The presets as searchable strategy records (role=improvement_preset)."""
    from ..core.store_serve import StoreRecord
    from ..core.facets import context_facets
    return [StoreRecord(
        record_id=f"preset.{name}", kind="strategy",
        title=preset_goal(name),
        body={"preset": name, "goal_template": tmpl,
              "role": "improvement_preset", "maturity": "registered",
              "facets": context_facets(
                  category="improvement_preset", subcategory=name,
                  context_type="instruction", thinking_style="improvement",
                  workflow_stage="improve", scope="package",
                  lifecycle="registered",
                  provenance="improvement_preset_registry")},
        tags=("improvement_preset", "continuous_improvement", name),
        tier="core") for name, tmpl in IMPROVEMENT_PRESETS.items()]


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    bank = interrogation_bank()

    # 1. the bank carries the EXPERT questions the owner named.
    text = " ".join(q.question.lower() for q in bank)
    check("bank_carries_expert_interrogation_questions",
          "patterns in the residuals" in text
          and "clusters in the raw data" in text
          and "latent variables" in text and "noisy" in text
          and "errors of the errors" in text
          and "best way" in text,
          f"{len(bank)} interrogation questions across "
          f"{len(INTERROGATION_CATEGORIES)} categories")

    # 2. drill-down: general → category → subcategory.
    resid = interrogate(category="residual_analysis")
    autoc = interrogate(category="residual_analysis",
                        subcategory="autocorrelation")
    check("drill_down_by_category_and_subcategory",
          len(bank) > len(resid) >= len(autoc) >= 1
          and all(q.category == "residual_analysis" for q in resid),
          f"all={len(bank)} residual={len(resid)} autocorr={len(autoc)}")

    # 3. THE DISTILLATION HOOK: a question declares whether a CODE node can answer
    # it — code-answerable interrogations become deterministic nodes.
    code_answerable = interrogate(answerable_by="code")
    check("questions_declare_a_distillation_target",
          code_answerable
          and all(q.answerable_by == "code" for q in code_answerable)
          and all(q.how_to_answer for q in code_answerable),
          f"{len(code_answerable)} questions a code node can compute (distill)")

    # 4. adversarial + cross-domain interrogation is present (expert review).
    check("adversarial_and_cross_domain_present",
          interrogate(category="adversarial_review")
          and interrogate(category="cross_domain")
          and any("prevented" in q.question.lower()
                  for q in interrogate(category="adversarial_review")),
          "best/worst-way, preventable failures, cross-domain transfer")

    # 5. PRESETS produce self-improvement Goal Strings (the review practitioner's
    # focused jobs) — string→node, adversarial, cross-domain, category, top-N.
    g1 = preset_goal("string_to_node", category="measurement")
    g2 = preset_goal("adversarial_solution_review")
    g3 = preset_goal("top_n_ways", n=10, task_family="tabular churn")
    check("presets_produce_self_improvement_goal_strings",
          "CODE NODE" in g1 and "measurement" in g1
          and "best way" in g2.lower()
          and "top 10" in g3 and "tabular churn" in g3,
          "each preset is a Goal String routed into a normal improvement run")

    # 6. a preset focuses the review on a category/subcategory (drill-down for the
    # improvement practitioner too).
    g4 = preset_goal("improve_string_category", category="latent_structure")
    check("presets_can_focus_a_category",
          "latent_structure" in g4,
          "the improvement practitioner drills down by category, like solving")

    # 7. unknown preset / category raise (closed vocabularies).
    bad = 0
    for fn in (lambda: preset_goal("nope"),
               lambda: InterrogationQuestion("x", "vibes")):
        try:
            fn()
        except (KeyError, ValueError):
            bad += 1
    check("closed_vocabularies", bad == 2,
          "categories and presets are closed sets")

    # 8. interrogations + presets are searchable String resources.
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=question_records() + preset_records())
    hit = store.search("are there patterns in the residuals of the model",
                       kind="question")
    hitp = store.search("turn Context Intelligence into a deterministic code node",
                        kind="strategy")
    check("interrogations_and_presets_are_searchable",
          hit["hits"] and any("interro." in h["record_id"] for h in hit["hits"])
          and hitp["hits"] and any("preset." in h["record_id"]
                                   for h in hitp["hits"]),
          "the expert questions + presets flow through the one search DAG")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "interrogation_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
