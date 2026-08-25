"""Lenses — role and method perspectives, kept as separate dimensions.

A persona database should not be decorative biographies (v3 §12.5, §16).  A
**LensSpec** is a typed perspective: what it focuses on, what evidence it
prefers, the questions it always asks, its risk posture, and its known blind
spots.  Two kinds are kept independent, because they combine:

- a **role** lens (data scientist, security reviewer, cost controller, novice…)
  is *who* is looking;
- a **method** lens (first-principles, failure-first, counterfactual,
  information-gain, minimum-complexity, adversarial…) is *how* they look.

A data scientist can use a counterfactual method lens; a security reviewer can
use an information-gain lens — the two axes multiply.  A lens folds into an
``AskFrame`` deterministically (its focus and questions become salts and its
identity a persona), so it steers a model prompt AND is readable by a rule.  A
named historical thinker may only ever be a documented method lens over public
work, never a claim to reproduce a private mind.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

from ..strings.frame import AskFrame

LENS_KINDS = ("role", "method")


@dataclass(frozen=True)
class LensSpec:
    id: str
    kind: str                                 # role | method
    focus: tuple[str, ...] = ()
    preferred_evidence: tuple[str, ...] = ()
    default_questions: tuple[str, ...] = ()
    risk_posture: dict = field(default_factory=dict)
    known_blind_spots: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in LENS_KINDS:
            raise ValueError(f"unknown lens kind {self.kind!r}; expected "
                             f"{LENS_KINDS}")

    def to_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v)
                for k, v in asdict(self).items()}


# --- Role lenses ---------------------------------------------------------
ROLE_LENSES = {
    "data_scientist": LensSpec(
        "lens.role.data_scientist", "role",
        focus=("validation integrity", "leakage", "metric alignment",
               "uncertainty"),
        preferred_evidence=("out-of-fold results", "ablations", "holdout tests"),
        default_questions=("Could this be leakage?",
                           "Does the validation unit match the test distribution?",
                           "What is the simplest competitive baseline?"),
        risk_posture={"leaderboard_overfitting": "high_concern"},
        known_blind_spots=("product usability", "presentation")),
    "ml_engineer": LensSpec(
        "lens.role.ml_engineer", "role",
        focus=("dataflow", "scale", "reproducibility", "cost"),
        preferred_evidence=("matched-budget comparisons", "runtime profiles"),
        default_questions=("Will this run within the compute limit?",
                           "Is the pipeline reproducible?")),
    "statistician": LensSpec(
        "lens.role.statistician", "role",
        focus=("identifiability", "uncertainty", "experimental design",
               "calibration"),
        default_questions=("Are these observations independent?",
                           "What is the effective sample size?")),
    "security_reviewer": LensSpec(
        "lens.role.security_reviewer", "role",
        focus=("authority", "attack surface", "isolation", "supply chain"),
        default_questions=("What is the smallest path to an unauthorized effect?",
                           "Is generated code isolated?")),
    "red_team": LensSpec(
        "lens.role.red_team", "role",
        focus=("counterexamples", "failure injection", "evaluator gaming"),
        default_questions=("How would this fail silently?",
                           "What assumption, if wrong, breaks it?")),
    "cost_controller": LensSpec(
        "lens.role.cost_controller", "role",
        focus=("token spend", "compute", "opportunity cost"),
        default_questions=("Is a cheaper path good enough?",
                           "What is the value of information per unit cost?")),
    "novice_outsider": LensSpec(
        "lens.role.novice_outsider", "role",
        focus=("unstated assumptions", "terminology", "usability"),
        default_questions=("What is assumed that a newcomer would not know?",)),
    "domain_scientist": LensSpec(
        "lens.role.domain_scientist", "role",
        focus=("mechanism", "domain constraints", "measurement validity")),
}

# --- Method lenses -------------------------------------------------------
METHOD_LENSES = {
    "first_principles": LensSpec(
        "lens.method.first_principles", "method",
        focus=("mechanism", "assumptions"),
        default_questions=("What must be true for this to work?",)),
    "failure_first": LensSpec(
        "lens.method.failure_first", "method",
        focus=("failure modes", "counterexamples"),
        default_questions=("What would make this fail?",
                           "What is the earliest reusable cause of failure?")),
    "counterfactual": LensSpec(
        "lens.method.counterfactual", "method",
        focus=("alternative worlds", "removed assumptions"),
        default_questions=("What if the incumbent design is wrong?",)),
    "information_gain": LensSpec(
        "lens.method.information_gain", "method",
        focus=("value of information", "discriminating tests"),
        default_questions=("Which evidence would most change the ranking?",)),
    "minimum_complexity": LensSpec(
        "lens.method.minimum_complexity", "method",
        focus=("simplicity", "removal"),
        default_questions=("What is the smallest graph that meets the contract?",)),
    "adversarial": LensSpec(
        "lens.method.adversarial", "method",
        focus=("exploits", "robustness"),
        default_questions=("How would an attacker break this?",)),
    "maximum_diversity": LensSpec(
        "lens.method.maximum_diversity", "method",
        focus=("novelty", "underused mechanisms"),
        default_questions=("Which valid mechanism is underexplored here?",)),
}


def get_lens(lens_id_or_name: str) -> LensSpec | None:
    """Resolve a lens by short name or full id from either catalog."""
    for catalog in (ROLE_LENSES, METHOD_LENSES):
        if lens_id_or_name in catalog:
            return catalog[lens_id_or_name]
        for lens in catalog.values():
            if lens.id == lens_id_or_name:
                return lens
    return None


def apply_lens(frame: AskFrame, *lenses: LensSpec) -> AskFrame:
    """Fold one role lens and/or method lens(es) into an AskFrame.

    The role lens sets the persona; every lens contributes its default questions
    as salts and its identity to ``extra['lenses']`` so a deterministic resolver
    can read them.  Applying two lenses of different kinds keeps both — the axes
    multiply."""
    persona = frame.persona
    salts = list(frame.salts)
    extra = dict(frame.extra)
    applied = list(extra.get("lenses", []))
    for lens in lenses:
        if lens.kind == "role" and not persona:
            persona = lens.id
        salts.extend(q for q in lens.default_questions if q not in salts)
        applied.append(lens.id)
    extra["lenses"] = applied
    return AskFrame(
        system_prompt=frame.system_prompt, original_task=frame.original_task,
        simplified_task=frame.simplified_task, features=frame.features,
        persona=persona, time_period=frame.time_period, purpose=frame.purpose,
        salts=tuple(salts), extra=extra)


# ---------------------------------------------------------------------------
# Self-test — deterministic.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    ds = get_lens("data_scientist")
    ff = get_lens("failure_first")
    check("role_and_method_lenses_resolve_from_their_catalogs",
          ds is not None and ds.kind == "role"
          and ff is not None and ff.kind == "method"
          and "leakage" in ds.focus,
          "a role lens (data_scientist) and a method lens (failure_first) "
          "resolve by name from separate catalogs")

    bad = False
    try:
        LensSpec("x", "biography")
    except ValueError:
        bad = True
    check("an_unknown_lens_kind_is_refused",
          bad, "a lens kind outside role/method is refused")

    # A data scientist USING a counterfactual method lens — two axes multiply.
    framed = apply_lens(AskFrame(original_task="predict churn"),
                        get_lens("data_scientist"),
                        get_lens("counterfactual"))
    check("a_role_and_a_method_lens_combine_on_one_frame",
          framed.persona == "lens.role.data_scientist"
          and "lens.method.counterfactual" in framed.extra["lenses"]
          and "lens.role.data_scientist" in framed.extra["lenses"]
          and any("Could this be leakage?" == s for s in framed.salts)
          and any("incumbent design is wrong" in s for s in framed.salts),
          "a data-scientist role lens plus a counterfactual method lens both "
          "fold into one frame: the role becomes the persona, and both lenses' "
          "questions become salts — the two dimensions multiply, not conflict")

    # The frame's lens data is readable deterministically (not just in a prompt).
    check("lens_data_is_available_deterministically",
          len(framed.extra["lenses"]) == 2
          and "lens.role.data_scientist" in framed.render_prompt_preamble(),
          "the applied lenses are on the frame's extra dims for a rule to read, "
          "and the persona also renders into a model prompt")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "lens_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
