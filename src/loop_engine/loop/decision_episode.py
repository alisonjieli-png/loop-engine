"""Decision episodes — learn from decisions, not only from winning graphs.

The system should learn more than "CatBoost worked on this dataset" (v3 §27).  It
should learn: when the state looked like this, and these unknowns remained, and
these proposals competed, the decision to run a group-overlap test invalidated
the validation design and prevented wasted search.  That requires recording the
whole decision — the state fingerprint, every proposal (selected, rejected, and
merely exposed), the selection propensities, and, crucially, EXPOSURE: a move
cannot be judged by wins alone if it was only ever shown on easy states.

Final task outcomes usually arrive much later, so an episode is append-only: the
outcome is linked in when it is known, never by rewriting the episode.  From the
accumulated episodes the system can estimate which resolvers work for which state
fingerprints — with the propensities needed to avoid mistaking popularity for
effectiveness.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ProposalRecord:
    move_key: str
    resolver: str
    exposed: bool = True           # was it shown / considered?
    selected: bool = False         # was it chosen?
    selection_propensity: float = 1.0   # P(it would be chosen), for off-policy
    reason: str = ""

    def to_dict(self) -> dict:
        return dict(asdict(self))


@dataclass
class DecisionEpisode:
    state_fingerprint: str
    decision_need_mode: str
    proposals: tuple[ProposalRecord, ...] = ()
    context_policy: str = ""
    model_calls_made: int = 0
    # Outcome — linked in LATER, append-only.  None until known.
    outcome: dict = field(default_factory=dict)   # {accepted, goal_progress, cost}
    outcome_linked: bool = False

    def selected(self) -> list[ProposalRecord]:
        return [p for p in self.proposals if p.selected]

    def to_dict(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if k != "proposals"}
        d["proposals"] = [p.to_dict() for p in self.proposals]
        d["record_type"] = "decision_episode/v1"
        return d


@dataclass
class EpisodeStore:
    _episodes: list = field(default_factory=list)   # DecisionEpisode

    def add(self, episode: DecisionEpisode) -> int:
        self._episodes.append(episode)
        return len(self._episodes) - 1

    def link_outcome(self, index: int, *, accepted: bool,
                     goal_progress: float = 0.0, cost: float = 0.0) -> None:
        """Attach a task outcome to an episode when it becomes known — the
        episode is NOT rewritten, its outcome fields are filled once."""
        ep = self._episodes[index]
        if ep.outcome_linked:
            return   # append-only: an outcome is linked once
        ep.outcome = {"accepted": accepted, "goal_progress": goal_progress,
                      "cost": cost}
        ep.outcome_linked = True

    def resolver_calibration(self, *, min_selected: int = 1) -> dict:
        """For each resolver, over episodes with a linked outcome: how often its
        SELECTED proposals led to an accepted outcome, alongside its EXPOSURE, so
        a resolver that is merely often-selected on easy states is not mistaken
        for an effective one."""
        stats: dict[str, dict] = {}
        for ep in self._episodes:
            if not ep.outcome_linked:
                continue
            accepted = bool(ep.outcome.get("accepted"))
            for p in ep.proposals:
                s = stats.setdefault(p.resolver, {
                    "exposed": 0, "selected": 0, "selected_accepted": 0,
                    "mean_propensity": 0.0, "_prop_sum": 0.0})
                if p.exposed:
                    s["exposed"] += 1
                if p.selected:
                    s["selected"] += 1
                    s["_prop_sum"] += p.selection_propensity
                    if accepted:
                        s["selected_accepted"] += 1
        rows = {}
        for resolver, s in stats.items():
            if s["selected"] < min_selected:
                continue
            rows[resolver] = {
                "exposed": s["exposed"], "selected": s["selected"],
                "acceptance_rate": round(s["selected_accepted"] / s["selected"],
                                         4),
                "mean_selection_propensity": round(
                    s["_prop_sum"] / s["selected"], 4),
                "selection_rate": round(s["selected"] / max(1, s["exposed"]), 4)}
        return {"record_type": "resolver_calibration/v1",
                "episodes_with_outcome": sum(1 for e in self._episodes
                                             if e.outcome_linked),
                "resolvers": rows,
                "the_rule": ("acceptance is judged on SELECTED proposals with a "
                             "linked outcome; exposure and propensity are kept so "
                             "popularity on easy states is not read as skill")}


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    store = EpisodeStore()
    # Episode 1: the diagnostic resolver's test was selected and led to an
    # accepted outcome; a premature-tuning proposal was exposed but rejected.
    i1 = store.add(DecisionEpisode(
        state_fingerprint="fp.leaky_tabular", decision_need_mode="investigate",
        proposals=(
            ProposalRecord("run_tests:group_overlap", "diagnostic",
                           selected=True, selection_propensity=0.6),
            ProposalRecord("tune:catboost", "optimizer", exposed=True,
                           selected=False, reason="premature")),
        context_policy="memory_informed"))
    i2 = store.add(DecisionEpisode(
        state_fingerprint="fp.leaky_tabular", decision_need_mode="route",
        proposals=(ProposalRecord("add_node:lightgbm", "planner", selected=True,
                                  selection_propensity=0.8),)))

    # Outcomes arrive later.
    store.link_outcome(i1, accepted=True, goal_progress=0.1)
    store.link_outcome(i2, accepted=True, goal_progress=0.2)

    check("episodes_record_exposed_and_rejected_proposals_not_only_winners",
          len(store._episodes[i1].proposals) == 2
          and any(not p.selected for p in store._episodes[i1].proposals),
          "the episode retains the rejected premature-tuning proposal alongside "
          "the selected diagnostic — an unselected proposal is decision "
          "evidence, not deleted")

    # Outcomes are append-only: a second link is ignored.
    store.link_outcome(i1, accepted=False)
    check("outcomes_are_linked_once_and_never_rewritten",
          store._episodes[i1].outcome["accepted"] is True,
          "the first linked outcome (accepted) stands; a later conflicting link "
          "does not rewrite it — history is append-only")

    cal = store.resolver_calibration()
    diag = cal["resolvers"].get("diagnostic", {})
    check("calibration_keeps_exposure_and_propensity_not_just_wins",
          diag.get("acceptance_rate") == 1.0
          and diag.get("mean_selection_propensity") == 0.6
          and "optimizer" not in cal["resolvers"],   # never selected
          "the diagnostic resolver's selected proposal led to acceptance (rate "
          "1.0) with its selection propensity (0.6) retained; the optimizer, "
          "never selected, is not scored as effective — exposure is kept so "
          "popularity is not read as skill")

    # An episode without a linked outcome does not contribute to calibration.
    store.add(DecisionEpisode(
        state_fingerprint="fp.new", decision_need_mode="route",
        proposals=(ProposalRecord("add_node:x", "planner", selected=True),)))
    cal2 = store.resolver_calibration()
    check("unlinked_episodes_do_not_pollute_calibration",
          cal2["episodes_with_outcome"] == 2,
          "an episode whose outcome is not yet known is excluded from "
          "calibration until its outcome is linked")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "decision_episode_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
