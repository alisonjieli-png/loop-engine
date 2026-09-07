"""Choose among independent overnight attempts without trusting any of them.

WHY MORE THAN ONE PATH
A small model solves a gate-failure task some fraction of the time. Running
it once accepts that fraction as the product's reliability. Running K
independent attempts -- different models, different skill sets, each in its
own worktree -- and keeping any that pass turns a 60% model into a
1-(0.4^K) system: 84% at K=2, 94% at K=3. Worktrees make the isolation free
and the gate makes the selection honest, so the only cost is model calls,
and the night has hours of them.

Diversity matters more than count. Three runs of one model share its blind
spots; three models do not. Twenty-two are reachable here.

WHY SELECTION IS ENGINE-OWNED
Every path will report that it succeeded. Selection reads two things only:
whether the project's own gate passed in that path's worktree, and what git
says changed there. A path that says it fixed the source while git shows it
edited a test loses to one whose diff is in the source -- and asking the
path would never have surfaced the difference.

WHY ALL PATHS ARE KEPT
The chosen path is a recommendation, not a verdict. A reviewer who can see
that three paths passed and two made the same change trusts the change more
than a reviewer shown one. And a path that failed with a real error is worth
more at 7am than a path that was deleted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .overnight_outcome import OUTCOME_ORDER, Outcome

#: Among paths on the same rung, this decides. Smaller diffs first: a fix
#: that changes less is easier to review and less likely to carry a second
#: change nobody asked for. Fewer files, then fewer lines.
_RUNG_INDEX = {rung: index for index, rung in enumerate(OUTCOME_ORDER)}


class MultipathSelectError(ValueError):
    """The paths supplied could not be compared."""


@dataclass(frozen=True)
class PathResult:
    """One independent attempt, described only by what the engine observed."""

    label: str
    model: str
    outcome: Outcome
    branch: str = ""
    worktree: str = ""
    files_changed: tuple = ()
    lines_changed: int = 0
    seconds: float = 0.0
    error: str = ""

    def __post_init__(self) -> None:
        if not str(self.label).strip():
            raise MultipathSelectError("a path needs a label")
        if not isinstance(self.outcome, Outcome):
            raise MultipathSelectError(
                f"path {self.label!r} carries {type(self.outcome).__name__}, "
                "not an Outcome; selection reads graded outcomes only")

    def sort_key(self) -> tuple:
        return (_RUNG_INDEX[self.outcome.rung], len(self.files_changed),
                self.lines_changed, self.seconds)


@dataclass(frozen=True)
class Selection:
    """The recommendation and the evidence a reviewer needs to distrust it."""

    chosen: "PathResult | None"
    ranked: tuple
    agreement: dict = field(default_factory=dict)

    @property
    def rung(self) -> str:
        return self.chosen.outcome.rung if self.chosen else "no_progress"

    @property
    def mergeable(self) -> bool:
        """Whether the recommendation is a diff, not just a place to start.

        Distinct from actionable. A cause_localised path is worth an
        engineer's first look and is recommended for that reason; it is not
        something to merge. Conflating the two would put a diagnosis in the
        "review and merge" column of the morning report.
        """
        return (self.chosen is not None and self.chosen.outcome.rung
                in ("verified", "verified_by_test_change"))

    def why(self) -> str:
        if self.chosen is None:
            return "no path produced anything usable"
        passing = [p for p in self.ranked
                   if p.outcome.rung in ("verified", "verified_by_test_change")]
        same = self.agreement.get(self.chosen.label, 0)
        parts = [f"{self.chosen.label} ({self.chosen.model}) reached "
                 f"{self.chosen.outcome.rung}"]
        if len(passing) > 1:
            parts.append(f"{len(passing)} of {len(self.ranked)} paths passed "
                         "the gate")
        if same:
            parts.append(f"{same} other path(s) made an identical change, "
                         "which is stronger evidence than any one of them")
        if len(self.chosen.files_changed) == 1:
            parts.append("one file changed")
        return "; ".join(parts)

    def to_dict(self) -> dict:
        return {
            "chosen": self.chosen.label if self.chosen else None,
            "rung": self.rung,
            "why": self.why(),
            "paths": [{"label": p.label, "model": p.model,
                       "rung": p.outcome.rung, "branch": p.branch,
                       "files_changed": list(p.files_changed),
                       "lines_changed": p.lines_changed,
                       "seconds": round(p.seconds, 1),
                       "error": p.error[:200]} for p in self.ranked],
            "agreement": dict(self.agreement),
        }


def select(paths, *, diffs: "dict | None" = None) -> Selection:
    """Rank independent paths and recommend one.

    ``diffs`` maps label -> the path's diff text, used only to detect paths
    that made the same change. Agreement is reported, not used to re-rank:
    two wrong paths agreeing is not evidence of correctness, and the gate
    already decided correctness.
    """
    paths = list(paths)
    if not paths:
        return Selection(chosen=None, ranked=())
    labels = [p.label for p in paths]
    if len(set(labels)) != len(labels):
        raise MultipathSelectError(f"duplicate path labels: {labels}")
    ranked = tuple(sorted(paths, key=PathResult.sort_key))

    agreement = {}
    if diffs:
        for path in ranked:
            mine = diffs.get(path.label, "").strip()
            if not mine:
                continue
            agreement[path.label] = sum(
                1 for other in ranked
                if other.label != path.label
                and diffs.get(other.label, "").strip() == mine)

    best = ranked[0]
    usable = best.outcome.actionable
    return Selection(chosen=best if usable else None, ranked=ranked,
                     agreement=agreement)


def self_test() -> dict:
    """Prove selection prefers the gate, then the smaller diff, and never a claim."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:170]})

    def path(label, model, rung, files=(), lines=0, seconds=10.0):
        return PathResult(label=label, model=model,
                          outcome=Outcome(rung, "test", {}),
                          files_changed=tuple(files), lines_changed=lines,
                          seconds=seconds)

    a = path("a", "model-a", "verified", ("src/x.py",), 4)
    b = path("b", "model-b", "verified", ("src/x.py", "src/y.py"), 12)
    c = path("c", "model-c", "cause_localised", ("src/x.py",), 0)
    d = path("d", "model-d", "no_progress")
    sel = select([d, c, b, a])
    check("the_passing_path_wins_regardless_of_order",
          sel.chosen is a, sel.why())
    check("among_passing_paths_the_smaller_diff_wins",
          [p.label for p in sel.ranked][:2] == ["a", "b"])
    check("ranking_follows_the_outcome_ladder",
          [p.label for p in sel.ranked] == ["a", "b", "c", "d"])

    # A path that only edited tests loses to one that fixed the source,
    # even with a smaller diff -- the ladder, not the diff, decides first.
    tests_only = path("t", "m", "verified_by_test_change", ("tests/test_x.py",), 1)
    real = path("r", "m", "verified", ("src/x.py",), 30)
    check("a_source_fix_beats_a_smaller_test_only_change",
          select([tests_only, real]).chosen is real,
          "an agent that edits tests can make any gate green")

    # No passing path: recommend nothing, but keep everything ranked.
    none = select([d, c])
    check("a_diagnosis_is_recommended_for_attention_but_not_for_merge",
          none.chosen is c and none.rung == "cause_localised"
          and not none.mergeable and len(none.ranked) == 2,
          "cause_localised is a good night but not a merge recommendation")
    check("a_verified_path_is_mergeable", sel.mergeable)
    only_nothing = select([d])
    check("a_path_with_no_progress_is_not_recommended_at_all",
          only_nothing.chosen is None and not only_nothing.mergeable)

    # Agreement is reported, not used to rank.
    diffs = {"a": "+fix\n", "b": "+fix\n", "c": "+other\n"}
    agreed = select([a, b, c], diffs=diffs)
    check("identical_changes_are_reported_as_agreement",
          agreed.agreement.get("a") == 1 and agreed.agreement.get("b") == 1
          and agreed.agreement.get("c") == 0, str(agreed.agreement))
    check("agreement_appears_in_the_explanation",
          "identical change" in agreed.why(), agreed.why())

    check("empty_input_is_a_clean_no_progress",
          select([]).chosen is None and select([]).rung == "no_progress")

    try:
        select([a, path("a", "other", "verified")])
        check("duplicate_labels_are_refused", False)
    except MultipathSelectError:
        check("duplicate_labels_are_refused", True)
    try:
        PathResult(label="x", model="m", outcome="verified")  # type: ignore
        check("a_bare_string_is_not_an_outcome", False)
    except MultipathSelectError as exc:
        check("a_bare_string_is_not_an_outcome", "graded" in str(exc))

    return {"module": "core.multipath_select", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
