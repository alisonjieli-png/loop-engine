"""Evidence about an attempt that the model producing it did not author.

Split out of the verification module, which these helpers pushed past its size
cap. The separation is real rather than cosmetic: everything here judges an
artifact from OUTSIDE the model's own claims -- cross-attempt agreement on
inputs harvested from generated tests, and engine-owned constraint results --
and records correlation separately from acceptance. Cross-attempt agreement
cannot overrule a failed check, grant execution authority, or clear an
unresolved requirement. A suspected wrong evaluator requires independent
review of that evaluator and a new verification, not a majority override.

The governing rule, learned the hard way on 2026-09-06: absence of dissent is
not agreement. An attempt compared with nobody has zero dissents, and reading
that as unanimity promoted three mutually contradictory implementations under
the engine's strongest evidence label. Every check here requires POSITIVE
agreement -- on VALUES, from DISTINCT attempts.  Three attempts that all raise
NotImplementedError agree on every input and have done nothing; three
byte-identical copies of one attempt are one attempt.  Both were measured
promoting under cross_attempt_weight on 2026-09-13, and neither may again.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .solution_ratchet import rank_attempts, sort_attempts


def module_digest(path: "str | Path") -> str:
    """sha256 of an attempt's module, so byte-identical copies can be seen."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""


def attempt_directories(base: "str | Path") -> list:
    """Attempt directories under a workspace, in natural order.

    Natural, not lexicographic: at ten or more attempts ``attempt-10`` sorted
    before ``attempt-9``, so "newest" named the wrong attempt (measured
    2026-09-13).
    """
    return sort_attempts(p for p in Path(base).glob("attempt-*") if p.is_dir())


def independent_support(services) -> dict:
    """Evidence that the newest attempt is sound, from outside the model.

    TWO independent signals must both hold, because either alone is weak:

    * Unanimous cross-attempt agreement ON VALUES across DISTINCT attempts, on
      inputs harvested from the generated tests.  Weak alone: attempts are
      drawn from ONE model and can share its misconception, agreeing while
      all are wrong.  Within-family behavioural convergence is measured in
      the distillation literature (arXiv:2604.21255 reports +5.9pp
      action-graph similarity within a family), so agreement here is
      correlated evidence, not independent evidence.  Agreement that every
      attempt raises the same exception is not agreement that any of them
      works, and copies of one module are counted once.
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
            attempts = attempt_directories(base)
            if len(attempts) >= 2:
                report = rank_attempts(attempts, host_execution_permitted=(
                    getattr(services, "allow_host_verification", False) is True))
                scores = report.scores
                # POSITIVE agreement, not absence of dissent. An attempt
                # compared with nobody has zero dissents, and reading that as
                # unanimity promoted three mutually contradictory
                # implementations (measured 2026-09-06).
                distinct = len({module_digest(s.module) for s in scores})
                copies = len(scores) - distinct
                unanimous_on_values = bool(scores) and all(
                    s.is_best_available and s.value_agreements == s.total
                    for s in scores)
                if (report.inputs_harvested >= 3 and distinct >= 2
                        and unanimous_on_values):
                    attempts_ok = True
                    attempts_seen = distinct
                    inputs_seen = report.inputs_harvested
                    detail = (f"{distinct} distinct attempts agree on values "
                              f"for {inputs_seen} harvested inputs")
                    if copies:
                        detail += (f" ({copies} byte-identical "
                                   f"{'copy' if copies == 1 else 'copies'} "
                                   "not counted)")
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
    # this needs 3 over 5, unanimous -- and the 3 are DISTINCT modules.
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
        attempts = attempt_directories(base)
        if len(attempts) < 2:
            return ""
        report = rank_attempts(attempts, host_execution_permitted=(
            getattr(services, "allow_host_verification", False) is True))
        newest = attempts[-1]
        for score in report.scores:
            if score.attempt == newest and (score.dissents or score.undecided):
                if score.dissents:
                    return (f"{Path(newest).name} dissents on "
                            f"{score.dissents}/{score.total} harvested inputs")
                return (f"{Path(newest).name} could not be compared on "
                        f"{score.undecided}/{score.total} inputs (no strict "
                        "majority among the attempts, or it produced no "
                        "outcome)")
    except Exception:                                    # noqa: BLE001
        # Verification must never fail because its evidence gathering did.
        return ""
    return ""


def apply_cross_attempt_evidence(services, verdict: str,
                                 deterministic_pass: bool) -> tuple:
    """Record agreement as advisory and let dissent tighten acceptance.

    Different source bytes, more attempts, and an unrelated constraint do
    not establish an independent evaluator for the current task. The legacy
    support mapping is retained as diagnostic data, never acceptance power.
    """
    support = ({} if deterministic_pass or verdict == "accept"
               else independent_support(services))
    if support:
        services.diagnostic("cross_attempt_agreement_advisory", {
            "note": ("attempts agree on sampled values; this does not "
                     "override failed checks or unresolved requirements"),
            "agreement": support["agreement"],
            "anchor": support.get("anchor"),
            "constraints": support.get("constraints") or [],
            "certification": "unverified_correlation",
        })
    dissent = newest_attempt_dissents(services)
    if verdict == "accept" and dissent:
        verdict = "repair"
        services.diagnostic("independent_cross_attempt_dissent", {
            "note": ("the newest attempt disagrees with its peers on "
                     "inputs harvested from the generated tests"),
            "detail": dissent,
        })
    return verdict, support, dissent


def self_test() -> dict:
    """Offline proof that absence of evidence never reads as agreement."""
    import tempfile
    from types import SimpleNamespace
    from functools import partial
    # These fixtures deliberately execute only sources authored below.
    SimpleNamespace = partial(SimpleNamespace, allow_host_verification=True)

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

    def fake_services(root, project_attempts=None):
        log: list = []
        return SimpleNamespace(
            workspace_base=str(root), project_attempts=project_attempts or [],
            diagnostic=lambda code, payload: log.append((code, payload)),
            log=log)

    good = "def solve(s):\n    return len(s)\n"
    broken = "def solve(s):\n    return 0\n"

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
        "attempt-1": good,
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

    single = workspace({"attempt-1": good})
    check("one_attempt_cannot_promote",
          independent_support(SimpleNamespace(
              workspace_base=str(single), project_attempts=[])) == {})

    # H5: copies of one module are one attempt; unanimous exceptions are
    # agreement that nothing works, not that something does.
    copies = workspace({f"attempt-{i}": good for i in (1, 2, 3)})
    check("byte_identical_copies_do_not_count_as_independent_attempts",
          independent_support(SimpleNamespace(
              workspace_base=str(copies), project_attempts=[])) == {}
          and newest_attempt_dissents(SimpleNamespace(
              workspace_base=str(copies))) == "")
    one_copy = workspace({"attempt-1": good, "attempt-2": good,
                          "attempt-3": "def solve(s):\n    return len(str(s))\n"})
    named = independent_support(SimpleNamespace(
        workspace_base=str(one_copy),
        project_attempts=[{"artifacts": [
            {"path": "plan.json", "constraint": "schedule/v1",
             "constraint_satisfied": True}]}]))
    check("a_copy_is_named_but_not_counted",
          named.get("anchor") == "engine_owned_constraint"
          and "2 distinct attempts" in named.get("agreement", "")
          and "1 byte-identical copy not counted" in named.get("agreement", "")
          and independent_support(SimpleNamespace(
              workspace_base=str(one_copy), project_attempts=[])) == {},
          str(named))
    stubs = workspace({f"attempt-{i}": (
        "def solve(s):\n    raise NotImplementedError('todo')\n")
        for i in (1, 2, 3)})
    check("unanimous_exceptions_do_not_promote",
          independent_support(SimpleNamespace(
              workspace_base=str(stubs), project_attempts=[])) == {})

    # L5: attempt-11 is newer than attempt-9, whatever the string order says.
    many = workspace({"attempt-9": good, "attempt-10": good,
                      "attempt-11": broken})
    check("attempt_eleven_is_newer_than_attempt_nine",
          newest_attempt_dissents(SimpleNamespace(
              workspace_base=str(many))).startswith("attempt-11 dissents"),
          newest_attempt_dissents(SimpleNamespace(workspace_base=str(many))))

    # H4: the outlier is charged the dissent, whichever position it holds.
    outlier_first = workspace({"attempt-1": broken, "attempt-2": good,
                               "attempt-3": good})
    check("dissent_is_charged_to_the_outlier_not_the_newest",
          newest_attempt_dissents(SimpleNamespace(
              workspace_base=str(outlier_first))) == ""
          and independent_support(SimpleNamespace(
              workspace_base=str(outlier_first), project_attempts=[])) == {})

    # The facade helpers: promotion, then demotion, then deferral.
    promoted = fake_services(agreeing)
    verdict, got_support, dissent = apply_cross_attempt_evidence(
        promoted, "repair", False)
    check("agreement_cannot_override_failed_checks",
          verdict == "repair" and got_support.get("anchor")
          == "cross_attempt_weight" and dissent == ""
          and [c for c, _ in promoted.log]
          == ["cross_attempt_agreement_advisory"],
          f"{verdict} {[c for c, _ in promoted.log]}")
    untouched = fake_services(agreeing)
    check("a_model_earned_accept_is_not_touched_by_agreement",
          apply_cross_attempt_evidence(untouched, "accept", True)
          == ("accept", {}, "") and untouched.log == [])
    regressed = workspace({"attempt-1": good, "attempt-2": good,
                           "attempt-3": broken})
    demoted = fake_services(regressed)
    verdict, got_support, dissent = apply_cross_attempt_evidence(
        demoted, "accept", True)
    check("dissent_demotes_an_accept_through_the_helper",
          verdict == "repair" and got_support == {}
          and dissent.startswith("attempt-3 dissents")
          and [c for c, _ in demoted.log]
          == ["independent_cross_attempt_dissent"],
          f"{verdict} {dissent}")
    for state in ("repair", "blocked", "stop"):
        held = fake_services(agreeing)
        check(f"agreement_preserves_{state}",
              apply_cross_attempt_evidence(held, state, False)[0] == state)

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
