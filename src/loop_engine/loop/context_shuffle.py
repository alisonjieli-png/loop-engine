"""Context shuffle — inject the far-transfer diversity a human gets off-task.

A human practitioner's best ideas often arrive off-task: on a walk, relaxed in
the bath, or while immersed in something unrelated — ecology, music, geology —
and a weird cross-domain connection surfaces that on-task focus would never
reach.  An LLM, asked "select the next action" cold, rarely bridges distant niches; it
returns the near, conventional answer.  This module injects that shuffle
deliberately: it produces deliberation frames that displace the reasoner into a
distant domain, a different reasoning *mode*, or a different time, and asks the
question from there — widening the swarm's variety and inviting connections
across industries an on-task lane would miss.

**Framing discipline (read this).**  The archetypes here are *modes of reasoning
and perception*, documented as cognitive styles — "reason from first principles",
"reason without visual imagery, from structural descriptions", "reason as an
agent whose primary sense is a chemical gradient".  They are NEVER a claim to
reproduce a specific real person's mind, NEVER a medical or diagnostic label
applied to a person, and NEVER a stereotype of any group.  A mode is a way of
looking that anyone can adopt to diversify proposals; that is the whole and only
use.  Like every frame in this system, a shuffle frame ORDERS what to consider —
it produces *proposals*; the fold oracle still decides what actually works, and a
plain on-task lane always runs alongside.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict

from ..strings.frame import AskFrame

DISCLAIMER = ("a mode of reasoning/perception used to diversify proposals — not "
              "a claim about any real person, not a diagnosis, not a stereotype")

# Distant domains to draw structural analogies from (far-transfer sources).
DISTANT_DOMAINS = (
    "ecology", "evolution", "immunology", "thermodynamics", "fluid_dynamics",
    "jazz_improvisation", "linguistics", "urban_planning", "ant_colonies",
    "geology", "cooking", "epidemiology", "economics", "cartography",
    "music_theory", "materials_science", "cell_biology")

# Reasoning/perception MODES (documented cognitive styles; see DISCLAIMER).
COGNITION_MODES = {
    "first_principles": "reason from physical and mathematical first principles, "
                        "distrusting convention and popularity",
    "associative_pattern": "reason by leaping between distant analogies and "
                           "surface patterns, tolerating loose connections",
    "systematizing_detail": "reason exhaustively by exact rules and edge cases, "
                            "detail-first, privileging precision over gestalt",
    "non_visual_structural": "reason without any visual imagery, from purely "
                             "structural and relational descriptions",
    "sequential_tactile": "reason step by step from local, touch-like structure "
                          "rather than a global picture",
    "auditory_temporal": "reason as if the problem were a sound or rhythm "
                         "unfolding in time",
    "non_human_sensor": "reason as an agent whose primary sense is a non-human "
                        "modality — a chemical gradient, a frequency spectrum",
    "relaxed_defocused": "reason in a relaxed, defocused state, not forcing an "
                         "answer — the walk-or-bath mode",
}

# Temporal displacement — a different era's methods or an imagined future.
TEMPORAL_STANCES = {
    "pre_deep_learning": "using only methods available before deep learning",
    "present": "using current methods and tools",
    "imagined_future": "imagining tools a decade ahead, then working backward",
}


@dataclass(frozen=True)
class ShuffleFrame:
    """A far-transfer deliberation frame: a distant domain + a reasoning mode +
    a temporal stance, plus the injected narrative."""
    id: str
    distant_domain: str
    cognition_mode: str
    temporal_stance: str
    narrative: str

    def to_dict(self) -> dict:
        d = dict(asdict(self))
        d["disclaimer"] = DISCLAIMER
        return d

    def to_ask_frame(self, problem_summary: str = "",
                     base: AskFrame | None = None) -> AskFrame:
        base = base or AskFrame()
        mode_desc = COGNITION_MODES.get(self.cognition_mode, self.cognition_mode)
        temporal_desc = TEMPORAL_STANCES.get(self.temporal_stance, "")
        system_prompt = (
            f"{self.narrative} You are approaching this fresh, having stepped "
            f"away and been immersed in {self.distant_domain}. In this session, "
            f"{mode_desc}"
            + (f", {temporal_desc}" if temporal_desc else "") + ". "
            + f"({DISCLAIMER}.)")
        salts = list(base.salts) + [
            cross_domain_bridge(problem_summary, self.distant_domain),
            f"What structure from {self.distant_domain} maps onto this problem "
            f"that a specialist would miss?",
            "Seen from this angle, what should NOT be tried?"]
        extra = dict(base.extra)
        extra["shuffle"] = {"domain": self.distant_domain,
                            "mode": self.cognition_mode,
                            "stance": self.temporal_stance}
        return AskFrame(
            system_prompt=system_prompt, original_task=base.original_task,
            simplified_task=base.simplified_task, features=base.features,
            persona=f"shuffle:{self.cognition_mode}",
            time_period=self.temporal_stance, purpose=base.purpose,
            salts=tuple(salts), extra=extra)


def cross_domain_bridge(problem_summary: str, distant_domain: str) -> str:
    """A prompt fragment that asks for a structural analogy between the problem
    and a distant domain — forcing far transfer."""
    problem = problem_summary or "this problem"
    return (f"Find a structural analogy between {problem} and {distant_domain}: "
            f"what mechanism, constraint, or pattern in {distant_domain} has the "
            f"same shape here, and what does it suggest to try or avoid?")


def _stable_index(seed: str, n: int) -> int:
    if n <= 0:
        return 0
    return int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16) % n


def make_shuffle_frame(distant_domain: str, cognition_mode: str, *,
                       temporal_stance: str = "present",
                       narrative: str = "You are a senior practitioner who just "
                       "took a long walk.") -> ShuffleFrame:
    fid = f"shuffle.{distant_domain}.{cognition_mode}.{temporal_stance}"
    return ShuffleFrame(id=fid, distant_domain=distant_domain,
                        cognition_mode=cognition_mode,
                        temporal_stance=temporal_stance, narrative=narrative)


def shuffle_lanes(problem_summary: str, n: int = 5, *,
                  include_relaxed: bool = True, salt: str = "shuffle"
                  ) -> list[ShuffleFrame]:
    """Deterministically produce ``n`` diverse far-transfer frames — distinct
    (domain × mode × stance) combinations — plus a protected relaxed/defocused
    lane (the 'bath' lane) so the shuffle always includes a low-context view.
    Deterministic: combinations are chosen by a stable hash, not RNG."""
    domains = list(DISTANT_DOMAINS)
    modes = [m for m in COGNITION_MODES if m != "relaxed_defocused"]
    stances = list(TEMPORAL_STANCES)
    frames: list[ShuffleFrame] = []
    used: set[str] = set()
    i = 0
    guard = 0
    while len(frames) < max(1, n) and guard < 10 * max(1, n) + 50:
        guard += 1
        d = domains[_stable_index(f"{salt}:d:{i}", len(domains))]
        m = modes[_stable_index(f"{salt}:m:{i}", len(modes))]
        s = stances[_stable_index(f"{salt}:s:{i}", len(stances))]
        i += 1
        key = f"{d}|{m}|{s}"
        if key in used:
            continue
        used.add(key)
        frames.append(make_shuffle_frame(d, m, temporal_stance=s))
    if include_relaxed:
        frames.append(make_shuffle_frame(
            "nothing_in_particular", "relaxed_defocused",
            narrative="You are relaxed and not forcing an answer, thinking of "
            "nothing in particular."))
    return frames


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    frame = make_shuffle_frame("ecology", "first_principles")
    ask = frame.to_ask_frame(problem_summary="predicting churn")
    check("a_shuffle_frame_injects_a_distant_domain_and_mode",
          "ecology" in ask.system_prompt and "first principles" in ask.system_prompt
          and any("ecology" in s for s in ask.salts)
          and ask.extra["shuffle"]["domain"] == "ecology",
          "the ecology / first-principles shuffle frame renders a system prompt "
          "that displaces the reasoner into ecology and a first-principles mode, "
          "with a cross-domain-bridge salt")

    bridge = cross_domain_bridge("a segmentation task", "immunology")
    check("cross_domain_bridge_asks_for_a_structural_analogy",
          "structural analogy" in bridge and "immunology" in bridge
          and "avoid" in bridge,
          "the bridge asks for a same-shape mechanism in immunology and what it "
          "suggests to try or avoid — forcing far transfer")

    lanes = shuffle_lanes("predicting churn", n=5)
    domains = {f.distant_domain for f in lanes}
    modes = {f.cognition_mode for f in lanes}
    check("shuffle_lanes_are_diverse_and_include_a_relaxed_lane",
          len(lanes) == 6 and len(domains) >= 4 and len(modes) >= 3
          and any(f.cognition_mode == "relaxed_defocused" for f in lanes),
          "five far-transfer lanes span at least four distant domains and three "
          "reasoning modes, plus a protected relaxed/defocused 'bath' lane — the "
          "shuffle always keeps a low-context view")

    # The framing discipline: every frame carries the mode-not-identity
    # disclaimer, and no frame asserts a real named person.
    disclaimed = all(DISCLAIMER in f.to_dict()["disclaimer"] for f in lanes)
    prompt = ask.system_prompt
    check("archetypes_are_modes_not_identities_and_carry_the_disclaimer",
          disclaimed and "not a diagnosis" in DISCLAIMER
          and "not a claim about any real person" in prompt
          and "not a diagnosis" in prompt,
          "every shuffle frame is documented as a reasoning/perception MODE with "
          "the explicit disclaimer (not a real person, not a diagnosis, not a "
          "stereotype) rendered into the prompt itself")

    # Determinism.
    lanes2 = shuffle_lanes("predicting churn", n=5)
    check("shuffle_lanes_are_deterministic",
          [f.id for f in lanes2] == [f.id for f in lanes]
          and make_shuffle_frame("ecology", "first_principles").id == frame.id,
          "the same problem and count always produce the identical set of "
          "shuffle frames — diverse but replayable, no hidden randomness")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "context_shuffle_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
