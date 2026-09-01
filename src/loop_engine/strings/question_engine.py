"""The question-variation engine — a STATIC DAG that multiplies ways of asking.

Owner rule (2026-08-23): there are thousands of variations of how to ask a model
something — best way / worst way / rank 1-10 / rank by analogy / eliminate /
check / propose-the-completely-new — and generating them must NOT be a live
model job.  A model may author a new question FORM once; from then on the form
is a stored, generalized template, and this engine multiplies forms
deterministically across personas, context policies, and seeds to produce a
SWARM of different asks — millions of combinations available, every one
reproducible, none needing a generation call to exist.

The pipeline is fixed:

    form (stored template)  x  persona  x  context policy  x  seed salt
        -> deterministic multiplication (full / stratified stride)
        -> AskVariant stream -> AskSpec (the strict LLM-call DAG runs it)

Forms carry their ANSWER SHAPE (ranking, elimination, verdict, proposals,
score, ...) so downstream parsing is contract-first.  New forms — including
model-authored ones — register once with provenance and start as experimental
until they earn core tier by outcome history.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from ..strings.knowledge import Knowledge
from ..core.model_call import AskSpec
from ..core.store_serve import StoreRecord, TIERS

# What a form's answer is expected to look like (drives parsing/validation).
ANSWER_SHAPES = ("proposals", "ranking", "score", "elimination", "verdict",
                 "comparison", "decomposition", "list", "free")

# Deterministic seed salts — reframing emphases appended by seed index so the
# same form asks differently without any randomness source.
SEED_SALTS = (
    "", "Answer as if explaining to a domain outsider.",
    "Be maximally concrete; no generalities.",
    "Favor unconventional answers over safe ones.",
    "Assume the obvious answer is wrong.",
    "Optimize for the lowest cost path.",
    "Optimize for the most reliable path.",
    "Answer first, then list what would change your mind.",
)

FORM_TO_QUESTION_FAMILY = {
    "best_way": "best_way", "worst_way": "worst_way",
    "rank_1_to_10": "ranking", "rank_options": "ranking",
    "rank_by_analogy": "analogy", "eliminate": "elimination",
    "verify_check": "evidence_needed", "generate_novel": "novel_alternatives",
    "pairwise": "pairwise", "devils_advocate": "adversarial_review",
    "premortem": "premortem", "decompose": "decomposition",
    "prerequisites": "prerequisites", "whats_missing": "missing_items",
    "calibrate": "calibration", "check_then_extend": "best_practices",
    "first_principles": "first_principles",
    "outline_to_detail": "outline_to_detail",
    "top_improvements": "top_improvements", "top_avoid": "top_avoid",
    "best_practices": "best_practices", "invert_assumptions": "inversion",
    # General-purpose forms for unseen task shapes.
    "state_the_unknowns": "missing_items", "cheapest_check": "evidence_needed",
    "assumption_audit": "prerequisites", "failure_mode_map": "top_avoid",
    "definition_check": "calibration", "smallest_first_step": "best_way",
    "acceptance_inversion": "inversion", "resource_horizon": "calibration",
    "reversibility": "best_practices", "stakeholder_view": "best_practices",
    "second_order": "best_practices", "analogy_probe": "analogy",
    "constraint_inversion": "inversion", "done_definition": "best_practices",
}


@dataclass
class QuestionForm:
    """One stored, generalized way of asking.  Authored by hand or by a model —
    ONCE — then multiplied deterministically forever."""
    name: str
    template: str                  # with {slot} placeholders
    answer_shape: str
    slots: tuple = ()
    tier: str = "core"
    provenance: str = "hand_authored"    # or llm_generated_once
    description: str = ""

    def __post_init__(self):
        if self.answer_shape not in ANSWER_SHAPES:
            raise ValueError(f"answer_shape must be one of {ANSWER_SHAPES}")
        if self.tier not in TIERS:
            raise ValueError(f"tier must be one of {TIERS}")
        found = tuple(sorted(set(re.findall(r"{(\w+)}", self.template))))
        if not self.slots:
            self.slots = found
        elif set(self.slots) != set(found):
            raise ValueError(f"declared slots {self.slots} != template slots "
                             f"{found}")

    def render(self, **values) -> str:
        missing = [s for s in self.slots if s not in values]
        if missing:
            raise ValueError(f"form {self.name!r} missing slot values: "
                             f"{missing}")
        return self.template.format(**{k: values[k] for k in self.slots})


def core_forms() -> dict:
    """The shipped core forms — including every one the owner named."""
    F = QuestionForm
    forms = [
        F("best_way", "What is the BEST way to {task}? Name it, then justify "
          "in two sentences.", "proposals"),
        F("worst_way", "What is the WORST way to {task}? Name it so we can "
          "avoid it, and say what makes it fail.", "proposals"),
        F("rank_1_to_10", "On a scale of 1-10, how strongly should we proceed "
          "with {option} for {task}? Give the number, then the two factors "
          "that most moved your score.", "score"),
        F("rank_options", "Rank these options for {task} from best to worst: "
          "{options}. One line of justification each.", "ranking"),
        F("rank_by_analogy", "Given these items in the context of {task}: "
          "{options}. Which one is best by analogy to a solved "
          "problem in another field?", "comparison"),
        F("eliminate", "Candidate solutions for {task}: {options}. ELIMINATE "
          "every one that cannot work, with the disqualifying reason. Keep "
          "only survivors.", "elimination"),
        F("verify_check", "Proposed solution for {task}: {candidate}. CHECK "
          "it: is it correct, complete, and safe? Verdict then defects.",
          "verdict"),
        F("generate_novel", "Context: {task}. Existing candidates: {options}. "
          "Propose approaches that are completely new and derived from none of "
          "the above.", "proposals"),
        F("pairwise", "For {task}: A = {a}; B = {b}. Which is better and why? "
          "Answer 'A' or 'B' first.", "comparison"),
        F("devils_advocate", "Argue the strongest possible case AGAINST "
          "{candidate} for {task}.", "verdict"),
        F("premortem", "Assume {candidate} was tried for {task} and FAILED "
          "badly. Write the post-mortem: what killed it?", "verdict"),
        F("decompose", "Break {task} into its smallest independently solvable "
          "sub-problems, numbered.", "decomposition"),
        F("prerequisites", "What must already be true BEFORE {candidate} can "
          "work for {task}? List the prerequisites we may be assuming.",
          "list"),
        F("whats_missing", "For {task}, here is what we have considered: "
          "{options}. What is MISSING from this set?", "list"),
        F("calibrate", "For {task}, give each option a probability of success "
          "and one sentence of reasoning: {options}.", "score"),
        F("check_then_extend", "Solutions proposed for {task}: {options}. "
          "First CHECK each briefly, then EXTEND the strongest with one "
          "improvement.", "verdict"),
        F("first_principles", "For {task}, identify the invariants, remove "
          "assumptions, and derive the smallest approach that could work.",
          "decomposition"),
        F("outline_to_detail", "For {task}, give a short outline. Expand each "
          "part into detailed steps, then name the first executable action.",
          "decomposition"),
        F("top_improvements", "For {task}, list the ten changes most likely "
          "to improve the result. Rank them by expected value and effort.",
          "ranking"),
        F("top_avoid", "For {task}, list the ten mistakes most likely to waste "
          "time, increase risk, or produce a false result.", "list"),
        F("best_practices", "For {task}, list the practices an experienced "
          "team would check before, during, and after the work.", "list"),
        F("invert_assumptions", "For {task}, reverse the main assumptions one "
          "at a time. Which reversed assumption changes the plan most?",
          "comparison"),
        # --- general-purpose forms for unseen task shapes -------------------
        F("state_the_unknowns", "For {task}, list every fact we are missing "
          "before we could act safely, and rank which unknown blocks the most.",
          "list"),
        F("cheapest_check", "For {task}, name the cheapest single check that "
          "would most reduce the risk of a wrong result.", "proposals"),
        F("assumption_audit", "For {task}, list every assumption the current "
          "plan silently makes. Which one is least examined?", "list"),
        F("failure_mode_map", "For {task}, list the distinct ways this could "
          "fail that would each need a different fix.", "list"),
        F("definition_check", "For {task}, which words in the goal are ambiguous, "
          "and what exact meaning does success require for each?", "list"),
        F("smallest_first_step", "For {task}, name the smallest action that "
          "produces real evidence about feasibility before committing to the "
          "full approach.", "proposals"),
        F("acceptance_inversion", "For {task}, what would a result have to show "
          "for us to REJECT it as wrong or incomplete? State the rejection test "
          "first.", "list"),
        F("resource_horizon", "For {task}, what time, access, data, or budget "
          "does each candidate approach actually require? Where is the "
          "estimate least certain?", "comparison"),
        F("reversibility", "For {task}, which candidate actions are hard to "
          "undo if they turn out wrong, and what smaller reversible step "
          "replaces each?", "comparison"),
        F("stakeholder_view", "For {task}, who or what consumes the result, and "
          "what would make it useless to them even if technically correct?",
          "list"),
        F("second_order", "For {task}, if this succeeds, what new problem does "
          "it create next? Name the follow-on work it forces.", "list"),
        F("analogy_probe", "For {task}, name a solved problem elsewhere with the "
          "same structure and say which part of its solution transfers.", "proposals"),
        F("constraint_inversion", "For {task}, which stated constraint is "
          "actually optional, and which unstated constraint binds hardest?",
          "comparison"),
        F("done_definition", "For {task}, state the exact observable condition "
          "that proves the work is complete — before starting.", "list"),
    ]
    return {f.name: f for f in forms}


@dataclass
class AskVariant:
    """One point in the multiplication: a fully specified ask, reproducible."""
    form: str
    persona: str
    context_policy: str
    seed: int
    question: str
    answer_shape: str

    def to_ask_spec(self, knowledge: "Knowledge | None" = None) -> AskSpec:
        salt = SEED_SALTS[self.seed % len(SEED_SALTS)]
        q = self.question + (f"\n{salt}" if salt else "")
        return AskSpec(question=q, knowledge=knowledge,
                       context_policy=self.context_policy,
                       persona=self.persona,
                       output_contract=f"answer shape: {self.answer_shape}")


def multiply(forms: dict, *, personas: Sequence[str] = ("",),
             policies: Sequence[str] = ("fully_informed",),
             seeds: Sequence[int] = (0,), slot_values: dict,
             limit: "int | None" = None, mode: str = "stride") -> list:
    """Deterministically multiply forms x personas x policies x seeds.

    ``mode='full'`` walks the whole product unless a caller sets ``limit``;
    ``mode='stride'`` interleaves so EVERY form appears before any repeats and
    the persona/policy/seed dimensions rotate at co-prime strides — broad
    coverage early, identical output for identical inputs, no randomness
    source anywhere.  Forms whose slots are not all present in ``slot_values``
    are skipped (a form never renders half-filled)."""
    if mode not in ("full", "stride"):
        raise ValueError("mode must be 'full' or 'stride'")
    usable = [f for f in forms.values()
              if all(s in slot_values for s in f.slots)]
    out: list = []
    if mode == "full":
        for f in usable:
            for p in personas:
                for pol in policies:
                    for sd in seeds:
                        if limit is not None and len(out) >= limit:
                            return out
                        out.append(AskVariant(
                            f.name, p, pol, sd,
                            f.render(**slot_values), f.answer_shape))
        return out
    nf, np_, npol, nsd = (len(usable), len(personas), len(policies),
                          len(seeds))
    total = nf * np_ * npol * nsd
    for i in range(total if limit is None else min(limit, total)):
        f = usable[i % nf]
        combo = i // nf
        # Change the cheap framing salt first, then the persona, then the
        # context policy. Every form still appears before the next coordinate,
        # while a short bounded sample sees more than one framing early.
        sd = seeds[combo % nsd]
        p = personas[(combo // nsd) % np_]
        pol = policies[(combo // (nsd * np_)) % npol]
        out.append(AskVariant(f.name, p, pol, sd,
                              f.render(**slot_values), f.answer_shape))
    return out


def combination_space(forms: dict, personas: int, policies: int,
                      seeds: int) -> int:
    """How many distinct asks the current dimensions can produce."""
    return len(forms) * personas * policies * seeds


def register_generated_form(forms: dict, *, name: str, template: str,
                            answer_shape: str,
                            description: str = "") -> QuestionForm:
    """Register a model-authored form ONCE.  It enters as experimental with
    llm_generated_once provenance — generalized immediately, but it earns core
    tier only through outcome history, never by assertion."""
    f = QuestionForm(name=name, template=template, answer_shape=answer_shape,
                     tier="experimental", provenance="llm_generated_once",
                     description=description)
    forms[name] = f
    return f


def as_store_records(forms: dict) -> list:
    """Forms as store records so the strict search/serve DAG finds them."""
    from ..core.facets import context_facets
    return [StoreRecord(
        record_id=f"qform.{f.name}", kind="question", title=f.template[:80],
        body={"template": f.template, "answer_shape": f.answer_shape,
              "slots": list(f.slots), "provenance": f.provenance,
              "question_family": FORM_TO_QUESTION_FAMILY.get(f.name, ""),
              "serialization_format": "plain_text",
              "format_example": f.template,
              "maturity": "registered" if f.tier == "core" else "candidate",
              "facets": context_facets(
                  category="question_form", subcategory=f.name,
                  context_type="question", thinking_style=f.name
                  if f.name in ("first_principles", "outline_to_detail") else "",
                  question_family=FORM_TO_QUESTION_FAMILY.get(f.name, ""),
                  list_structure="ranked_list" if f.answer_shape == "ranking"
                  else "flat_list" if f.answer_shape in ("list", "proposals")
                  else "none",
                  serialization_format="plain_text",
                  response_shape=f.answer_shape, scope="package",
                  lifecycle="registered" if f.tier == "core" else "candidate",
                  provenance=f.provenance)},
        tags=("question_form", f.answer_shape, f.name), tier=f.tier)
        for f in forms.values()]


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    forms = core_forms()

    # 1. the owner's named forms all ship.
    wanted = ("best_way", "worst_way", "rank_1_to_10", "rank_by_analogy",
              "eliminate", "verify_check", "generate_novel")
    check("the_named_question_forms_all_ship",
          all(w in forms for w in wanted) and len(forms) >= 16,
          f"{len(forms)} core forms including {', '.join(wanted)}")

    # 2. rendering validates slots — a half-filled form never leaves.
    err = False
    try:
        forms["eliminate"].render(task="pick a model")   # missing {options}
    except ValueError:
        err = True
    txt = forms["eliminate"].render(task="pick a model",
                                    options="A) xgb B) mlp C) knn")
    check("a_form_never_renders_half_filled",
          err and "ELIMINATE" in txt and "A) xgb" in txt,
          "missing slots raise; full slots render the stored template")

    # 3. multiplication is deterministic and covers every form early.
    slot_values = {"task": "win the competition",
                   "options": "A;B;C", "candidate": "use xgboost",
                   "option": "use xgboost", "a": "xgb", "b": "mlp"}
    v1 = multiply(forms, personas=("a skeptic", "an optimist"),
                  policies=("fully_informed", "goal_only"),
                  seeds=(0, 3), slot_values=slot_values, limit=40)
    v2 = multiply(forms, personas=("a skeptic", "an optimist"),
                  policies=("fully_informed", "goal_only"),
                  seeds=(0, 3), slot_values=slot_values, limit=40)
    first_forms = [v.form for v in v1[:len(forms)]]
    check("multiplication_is_deterministic_and_covers_all_forms_first",
          [ (v.form, v.persona, v.seed) for v in v1 ]
          == [ (v.form, v.persona, v.seed) for v in v2 ]
          and len(set(first_forms)) == len(forms),
          "same inputs -> identical stream; every form appears before any "
          "repeats")

    # 4. the combination space is HUGE while every point stays reproducible.
    space = combination_space(forms, personas=1000, policies=14, seeds=8)
    check("the_combination_space_reaches_millions_reproducibly",
          space >= 1_000_000,
          f"{len(forms)} forms x 1000 personas x 14 policies x 8 seeds = "
          f"{space:,} distinct asks, zero generation calls")

    # 5. seeds change the ask via fixed salts; variant -> AskSpec carries all
    # dimensions into the strict call DAG.
    va = [v for v in v1 if v.seed == 3][0]
    spec = va.to_ask_spec()
    check("seeds_reframe_deterministically_and_feed_the_strict_call_dag",
          SEED_SALTS[3] in spec.question and spec.persona == va.persona
          and spec.output_contract.startswith("answer shape:"),
          "the seed salt lands in the prompt; persona/policy/shape ride the "
          "AskSpec")

    total = combination_space(forms, personas=2, policies=2, seeds=2)
    stride_all = multiply(
        forms, personas=("a skeptic", "an optimist"),
        policies=("fully_informed", "goal_only"), seeds=(0, 3),
        slot_values=slot_values, limit=total, mode="stride")
    full_all = multiply(
        forms, personas=("a skeptic", "an optimist"),
        policies=("fully_informed", "goal_only"), seeds=(0, 3),
        slot_values=slot_values, limit=total, mode="full")
    key = lambda variant: (variant.form, variant.persona,
                           variant.context_policy, variant.seed)
    check("stride_visits_every_combination_once",
          len(stride_all) == len({key(item) for item in stride_all}) == total
          and {key(item) for item in stride_all}
          == {key(item) for item in full_all})

    # 6. a model-authored form registers ONCE as experimental with provenance.
    f = register_generated_form(
        forms, name="steelman_then_break",
        template="Steelman the case for {candidate} on {task}, then break it.",
        answer_shape="verdict")
    check("a_model_authored_form_registers_once_as_experimental",
          forms["steelman_then_break"].provenance == "llm_generated_once"
          and f.tier == "experimental",
          "generated once, generalized forever, core tier only by outcome "
          "history")

    # 7. forms are searchable through the strict search/serve DAG.
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=as_store_records(core_forms()))
    hit = store.search("eliminate candidate solutions", kind="question")
    check("forms_are_searchable_via_the_strict_search_dag",
          hit["hits"] and hit["hits"][0]["record_id"] == "qform.eliminate",
          "the search DAG finds the elimination form for an elimination query")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "question_engine_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
