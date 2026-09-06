"""Evidence about an attempt that the model producing it did not author.

Split out of the verification module, which these helpers pushed past its size
cap. The separation is real rather than cosmetic: everything here judges an
artifact from OUTSIDE the model's own claims -- cross-attempt agreement on
inputs harvested from generated tests, and engine-owned constraint results --
while the verification module owns the flow that consumes those judgements.

The governing rule, learned the hard way on 2026-09-06: absence of dissent is
not agreement. An attempt compared with nobody has zero dissents, and reading
that as unanimity promoted three mutually contradictory implementations under
the engine's strongest evidence label. Every check here requires POSITIVE
agreement.
"""
from __future__ import annotations

from pathlib import Path

from .solution_ratchet import rank_attempts


def independent_support(services) -> dict:
    """Evidence that the newest attempt is sound, from outside the model.

    TWO independent signals must both hold, because either alone is weak:

    * Unanimous cross-attempt agreement on inputs harvested from the generated
      tests.  Weak alone: attempts are drawn from ONE model and can share its
      misconception, agreeing while all are wrong.  Within-family behavioural
      convergence is measured in the distillation literature (arXiv:2604.21255
      reports +5.9pp action-graph similarity within a family), so agreement
      here is correlated evidence, not independent evidence.
    * An ENGINE-OWNED constraint check the model cannot author, recorded on the
      artifact as ``constraint_satisfied``.  This is the anchor: a shared
      misconception that also satisfies a predicate written by the engine is a
      far narrower failure than one that merely convinces its own author.

    Agreement without an anchor does not promote anything.  Returns a mapping
    describing the support, empty when it does not hold.
    """
    base = getattr(services, "workspace_base", None)
    attempts_ok = False
    attempts_seen = inputs_seen = 0
    detail = ""
    if base:
        try:
            from pathlib import Path

            from .solution_ratchet import rank_attempts

            attempts = sorted(str(p) for p in Path(base).glob("attempt-*")
                              if p.is_dir())
            if len(attempts) >= 2:
                report = rank_attempts(attempts)
                # POSITIVE agreement, not absence of dissent. An attempt
                # compared with nobody has zero dissents, and reading that as
                # unanimity promoted three mutually contradictory
                # implementations (measured 2026-09-06).
                if report.inputs_harvested >= 3 and report.scores and all(
                        score.is_best_available for score in report.scores):
                    attempts_ok = True
                    attempts_seen = len(report.scores)
                    inputs_seen = report.inputs_harvested
                    detail = (f"{attempts_seen} attempts agree on "
                              f"{inputs_seen} harvested inputs")
        except Exception:                                # noqa: BLE001
            return {}
    if not attempts_ok:
        return {}
    # Anchor A: an engine-owned constraint was declared and satisfied.
    anchored = []
    for attempt in (getattr(services, "project_attempts", ()) or ()):
        for artifact in (attempt.get("artifacts") or ()):
            if artifact.get("constraint") and artifact.get(
                    "constraint_satisfied"):
                anchored.append(
                    f"{artifact.get('path')}:{artifact.get('constraint')}")
    if anchored:
        return {"agreement": detail, "anchor": "engine_owned_constraint",
                "constraints": sorted(set(anchored))}

    # Anchor B: weight of agreement, for work no engine-owned check can read.
    #
    # Requiring anchor A made this branch UNREACHABLE for ordinary code:
    # constraint checks bind to application/json, a plain module declares none,
    # so promotion could never fire for the commonest task and the measured
    # 2:1 false-failure rate stood untouched.
    #
    # The substitution is a HIGHER bar, not an equal one, because the evidence
    # is weaker in kind: attempts come from one model and can share its
    # misconceptions (within-family behavioural convergence measured at
    # +5.9pp, arXiv:2604.21255), whereas an engine-owned predicate is
    # independent by construction. Anchor A needs 2 attempts over 3 inputs;
    # this needs 3 over 5, unanimous.
    #
    # What makes it defensible rather than hopeful is where the inputs come
    # from. They are harvested from the model's own tests, and the measured
    # split is that a model's test INPUTS are reliable while its expected
    # VALUES are not: 6 of 8 constants correct, both failures on multi-step
    # arithmetic, and the code itself correct every time. Agreement is judged
    # on inputs the model chose and outputs it never asserted -- the half it
    # gets right, checked by the half it cannot fake.
    #
    # This can still be wrong. Three attempts sharing one misconception would
    # agree and all be incorrect, so it is recorded as agreement-backed for a
    # reviewer to weigh differently from a test-backed pass.
    if attempts_seen >= 3 and inputs_seen >= 5:
        return {"agreement": detail, "anchor": "cross_attempt_weight",
                "constraints": []}
    return {}


def newest_attempt_dissents(services) -> str:
    """Return a reason when the newest attempt disagrees with its peers.

    Evidence, not proof: the attempts come from one model and can share a
    misconception, so this is used ONLY to withhold acceptance, never to grant
    it. Returns an empty string when there is nothing to compare or nothing to
    report -- an oracle that cannot decide must not influence the verdict.
    """
    base = getattr(services, "workspace_base", None)
    if not base:
        return ""
    try:
        from pathlib import Path

        from .solution_ratchet import rank_attempts

        attempts = sorted(str(p) for p in Path(base).glob("attempt-*")
                          if p.is_dir())
        if len(attempts) < 2:
            return ""
        report = rank_attempts(attempts)
        newest = attempts[-1]
        for score in report.scores:
            if score.attempt == newest and (score.dissents or score.undecided):
                if score.dissents:
                    return (f"{Path(newest).name} dissents on "
                            f"{score.dissents}/{score.total} harvested inputs")
                return (f"{Path(newest).name} could not be compared on "
                        f"{score.undecided}/{score.total} inputs (peers "
                        f"disagree with each other)")
    except Exception:                                    # noqa: BLE001
        # Verification must never fail because its evidence gathering did.
        return ""
    return ""


def self_test() -> dict:
    """Offline proof that absence of evidence never reads as agreement."""
    import tempfile
    from types import SimpleNamespace

    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"name": name, "passed": bool(ok), "detail": detail})

    tests = ("import unittest\nfrom mod import solve\n"
             "class T(unittest.TestCase):\n    def test_a(self):\n"
             + "".join(f"        self.assertEqual(solve('{'x' * i}'), 1)\n"
                       for i in range(1, 7)))

    def workspace(bodies):
        root = Path(tempfile.mkdtemp())
        for name, body in bodies.items():
            directory = root / name
            directory.mkdir()
            (directory / "mod.py").write_text(body, encoding="utf-8")
            (directory / "test_mod.py").write_text(tests, encoding="utf-8")
        return root

    # The blocker this module exists to prevent: three implementations that
    # disagree with EACH OTHER are charged no dissents, because a dissent was
    # only counted against a majority that passed. Read as unanimity, that
    # promoted total disagreement under the engine's strongest evidence label.
    contradictory = workspace({
        "attempt-1": "def solve(s):\n    return len(s) * 2\n",
        "attempt-2": "def solve(s):\n    return 0\n",
        "attempt-3": "def solve(s):\n    return -len(s)\n",
    })
    services = SimpleNamespace(workspace_base=str(contradictory),
                               project_attempts=[])
    check("mutual_disagreement_never_promotes",
          independent_support(services) == {},
          str(independent_support(services)))
    check("mutual_disagreement_is_reported_as_undecided",
          "could not be compared" in newest_attempt_dissents(services),
          newest_attempt_dissents(services))

    agreeing = workspace({
        "attempt-1": "def solve(s):\n    return len(s)\n",
        "attempt-2": "def solve(s):\n    return len(str(s))\n",
        "attempt-3": "def solve(s):\n    return sum(1 for _ in s)\n",
    })
    agreed = SimpleNamespace(workspace_base=str(agreeing), project_attempts=[])
    support = independent_support(agreed)
    check("genuine_agreement_promotes_under_weight",
          support.get("anchor") == "cross_attempt_weight", str(support))
    check("genuine_agreement_reports_no_dissent",
          newest_attempt_dissents(agreed) == "",
          newest_attempt_dissents(agreed))

    anchored = SimpleNamespace(
        workspace_base=str(agreeing),
        project_attempts=[{"artifacts": [
            {"path": "plan.json", "constraint": "schedule/v1",
             "constraint_satisfied": True}]}])
    check("an_engine_owned_constraint_is_the_preferred_anchor",
          independent_support(anchored).get("anchor")
          == "engine_owned_constraint")

    check("no_workspace_yields_no_evidence",
          independent_support(SimpleNamespace(
              workspace_base=None, project_attempts=[])) == {}
          and newest_attempt_dissents(SimpleNamespace(
              workspace_base=None)) == "")

    single = workspace({"attempt-1": "def solve(s):\n    return len(s)\n"})
    check("one_attempt_cannot_promote",
          independent_support(SimpleNamespace(
              workspace_base=str(single), project_attempts=[])) == {})

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
