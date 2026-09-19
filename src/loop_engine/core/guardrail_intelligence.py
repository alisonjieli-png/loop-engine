"""Rules that narrow what a run may do, kept as records rather than branches.

The recorded direction on adaptable policies describes an enforcement ladder,
a rule category that fixes how far a level may be relaxed, and a challenge
path for a rule that blocks work wrongly. None of it existed as something a
run could carry, search, or serve. This is that: a guardrail is a record with
an identity, a digest, the point at which it is evaluated, what it obliges,
and what happens when it fires.

WHY RECORDS RATHER THAN CODE
A rule written as a branch cannot be versioned, tagged, served to a harness
instance, searched for by role or sensitivity, or reviewed when it fires
wrongly. A rule written as a record can be all of those, and it still refuses
at a declared point rather than being advice a model may ignore.

A GUARDRAIL NEVER GRANTS
There is no permitting level. A guardrail narrows or it does nothing. Anything
that widens authority is a permission decision and belongs to the effect
contracts, not here. That asymmetry is what makes it safe to let a guardrail
travel with an instance.

CATEGORY FIXES THE LEVEL
Secrets, permissions, spending, external effects, and the sandbox are
protected categories. A rule in one of them blocks. It cannot be softened to a
warning because a warning is more convenient, which is the failure the
recorded direction names directly.

UNAVAILABLE IS NOT PASSED
A rule that cannot be evaluated, because the judge it needs is not installed,
does not quietly succeed. It declares in advance whether that state refuses
the work or escalates it, and the decision says which happened.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .intelligence_tagging import EMPTY_TAGS, TagSet

RECORD_TYPE = "guardrail/v1"
DECISION_RECORD_TYPE = "guardrail_decision/v1"
REVIEW_RECORD_TYPE = "guardrail_review/v1"
#: What happens when a rule fires. There is no level that permits anything.
LEVELS = ("observe", "advise", "warn", "block")
#: Where a rule is evaluated. A rule naming no point can never be reached.
POINTS = ("before_provisioning", "before_dispatch", "before_effect", "on_output",
          "before_publication")
#: What decides it. The same distinction the contract matching modes draw.
JUDGES = ("deterministic", "model_judged")
#: Categories whose level is fixed at blocking, because convenience is not a reason.
PROTECTED_CATEGORIES = ("secret", "permission", "spending", "external_effect", "sandbox")
#: Everything else a rule can be about.
OPEN_CATEGORIES = ("quality", "cost", "style", "process", "data_handling")
#: Who set the rule. A narrower scope never loosens a wider one.
SCOPES = ("organization", "project", "node")
#: What happens when the judge a rule needs is not installed.
ON_UNAVAILABLE = ("refuse", "escalate")
#: What a decision can say. Nothing here means the rule was skipped.
OUTCOMES = ("passed", "fired", "unavailable")


class GuardrailError(ValueError):
    """The rule names an unknown level, point, or category, or tries to permit something."""


@dataclass(frozen=True)
class Guardrail:
    """One rule: what it obliges, where it is checked, and what firing means."""

    guardrail_id: str
    purpose: str
    category: str
    level: str
    point: str
    obligation: str
    judge: str = JUDGES[0]
    scope: str = SCOPES[0]
    applies_to: TagSet = EMPTY_TAGS
    on_unavailable: str = ON_UNAVAILABLE[0]
    evidence_required: tuple[str, ...] = ()
    version: str = "1.0.0"
    source: str = ""

    def __post_init__(self) -> None:
        for name in ("guardrail_id", "purpose", "obligation"):
            if not str(getattr(self, name)).strip():
                raise GuardrailError(f"a guardrail needs its {name}")
        if self.level not in LEVELS:
            raise GuardrailError(f"level must be one of {LEVELS}")
        if self.point not in POINTS:
            raise GuardrailError(f"point must be one of {POINTS}")
        if self.judge not in JUDGES:
            raise GuardrailError(f"judge must be one of {JUDGES}")
        if self.scope not in SCOPES:
            raise GuardrailError(f"scope must be one of {SCOPES}")
        if self.on_unavailable not in ON_UNAVAILABLE:
            raise GuardrailError(f"on_unavailable must be one of {ON_UNAVAILABLE}")
        if self.category not in PROTECTED_CATEGORIES + OPEN_CATEGORIES:
            raise GuardrailError(
                f"{self.category!r} is not one of {PROTECTED_CATEGORIES + OPEN_CATEGORIES}")
        if self.category in PROTECTED_CATEGORIES and self.level != LEVELS[-1]:
            raise GuardrailError(
                f"{self.guardrail_id!r} is a {self.category!r} rule, which blocks. A protected "
                "category is not softened to a warning because a warning is more convenient")
        if not isinstance(self.applies_to, TagSet):
            raise GuardrailError("applies_to must be a typed tag set")

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "guardrail_id": self.guardrail_id,
                "purpose": self.purpose, "category": self.category, "level": self.level,
                "point": self.point, "obligation": self.obligation, "judge": self.judge,
                "scope": self.scope, "applies_to": self.applies_to.to_dict(),
                "on_unavailable": self.on_unavailable,
                "evidence_required": list(self.evidence_required),
                "version": self.version, "source": self.source,
                "grants_nothing": True}

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode("utf-8")).hexdigest()

    def applies(self, tags: TagSet, point: str) -> bool:
        """True when this rule is evaluated here, for work described like this."""
        if point not in POINTS:
            raise GuardrailError(f"point must be one of {POINTS}")
        return self.point == point and self.applies_to.matches(tags)


@dataclass
class GuardrailSet:
    """The rules a deployment holds, with the wider scope keeping its strictness."""

    rules: dict = field(default_factory=dict)

    def register(self, rule: Guardrail) -> None:
        if not isinstance(rule, Guardrail):
            raise GuardrailError("only a typed guardrail can be registered")
        held = self.rules.get(rule.guardrail_id)
        if held is not None and held.digest != rule.digest:
            raise GuardrailError(
                f"{rule.guardrail_id!r} is already registered with different terms; give a "
                "revised rule a new version and identity rather than replacing it in place")
        for other in self.rules.values():
            if (other.obligation == rule.obligation
                    and SCOPES.index(rule.scope) > SCOPES.index(other.scope)
                    and LEVELS.index(rule.level) < LEVELS.index(other.level)):
                raise GuardrailError(
                    f"{rule.guardrail_id!r} is {rule.scope!r} scoped and would lower the level "
                    f"of {other.guardrail_id!r}, which is {other.scope!r} scoped, on the same "
                    "obligation; a narrower scope never loosens a wider one")
        self.rules[rule.guardrail_id] = rule

    def applicable(self, tags: TagSet, point: str) -> tuple:
        """Every rule evaluated here, strictest first, then by identity."""
        matched = [rule for rule in self.rules.values() if rule.applies(tags, point)]
        return tuple(sorted(matched, key=lambda rule: (-LEVELS.index(rule.level),
                                                       rule.guardrail_id)))


def evaluate(rules, subject: dict, *, judge=None, tags: TagSet = EMPTY_TAGS,
             point: str = POINTS[0]) -> dict:
    """Check every applicable rule against one subject and report what happened.

    ``subject`` is the typed description of the work being checked. A
    deterministic rule is satisfied when the subject carries every piece of
    evidence the rule requires. A model judged rule needs the judge the caller
    installed, and without one the rule does what it declared in advance.

    Nothing here is skipped silently: every applicable rule appears in the
    result with one of the declared outcomes.
    """
    if not isinstance(subject, dict):
        raise GuardrailError("a subject is a typed description, as a mapping")
    decisions, blocked, escalated = [], [], []
    for rule in rules:
        if not isinstance(rule, Guardrail):
            raise GuardrailError("only typed guardrails can be evaluated")
        if not rule.applies(tags, point):
            continue
        missing = [name for name in rule.evidence_required if not subject.get(name)]
        if rule.judge == JUDGES[1] and judge is None:
            outcome, detail = OUTCOMES[2], "no judge is installed for a model judged rule"
        elif rule.judge == JUDGES[1]:
            verdict = judge(rule, subject)
            if not isinstance(verdict, bool):
                raise GuardrailError("a judge answers whether the obligation is met")
            outcome = OUTCOMES[0] if verdict else OUTCOMES[1]
            detail = "the judge found the obligation met" if verdict else rule.obligation
        elif missing:
            outcome, detail = OUTCOMES[1], f"the subject carries no {', '.join(missing)}"
        else:
            outcome, detail = OUTCOMES[0], "every required piece of evidence is present"
        decision = {"record_type": DECISION_RECORD_TYPE, "guardrail_id": rule.guardrail_id,
                    "digest": rule.digest, "category": rule.category, "level": rule.level,
                    "point": point, "outcome": outcome, "detail": detail,
                    "obligation": rule.obligation, "scope": rule.scope}
        if outcome == OUTCOMES[2]:
            decision["consequence"] = rule.on_unavailable
            if rule.on_unavailable == ON_UNAVAILABLE[0]:
                blocked.append(rule.guardrail_id)
            else:
                escalated.append(rule.guardrail_id)
        elif outcome == OUTCOMES[1] and rule.level == LEVELS[-1]:
            decision["consequence"] = "blocked"
            blocked.append(rule.guardrail_id)
        elif outcome == OUTCOMES[1]:
            decision["consequence"] = rule.level
        else:
            decision["consequence"] = "none"
        decisions.append(decision)
    return {"record_type": "guardrail_evaluation/v1", "point": point,
            "evaluated": len(decisions), "decisions": decisions,
            "blocked": bool(blocked), "blocked_by": blocked, "escalated_by": escalated,
            "fired": [row["guardrail_id"] for row in decisions
                      if row["outcome"] == OUTCOMES[1]]}


def refusal_lines(rules) -> tuple[str, ...]:
    """What an instance is told to refuse, in the words of the rules that apply.

    An instruction file's refusals become the obligations that actually hold
    here rather than a fixed paragraph, so a rule added to the set reaches the
    instances it applies to without anyone editing prose.
    """
    lines = []
    for rule in rules:
        if not isinstance(rule, Guardrail):
            raise GuardrailError("only typed guardrails can be rendered")
        if rule.level == LEVELS[0]:
            continue
        prefix = {"block": "You must not", "warn": "Avoid", "advise": "Prefer not to"}[rule.level]
        lines.append(f"{prefix}: {rule.obligation}")
    return tuple(lines)


def review(decision: dict, *, reviewer: str, verdict: str, evidence: tuple) -> dict:
    """Record that a firing was examined, because a rule that fires wrongly rots.

    The verdict says whether the rule applied, whether the work was wrong, or
    whether the rule itself needs revising. Nothing here changes the rule: a
    revision is a new version through the same registration path.
    """
    allowed = ("rule_applied_correctly", "work_was_wrong", "rule_needs_revision",
               "rule_did_not_apply")
    if decision.get("record_type") != DECISION_RECORD_TYPE:
        raise GuardrailError("a guardrail decision is required")
    if verdict not in allowed:
        raise GuardrailError(f"verdict must be one of {allowed}")
    if not reviewer.strip() or not tuple(evidence):
        raise GuardrailError("a review names its reviewer and quotes its evidence")
    return {"record_type": REVIEW_RECORD_TYPE, "guardrail_id": decision["guardrail_id"],
            "digest": decision["digest"], "reviewer": reviewer, "verdict": verdict,
            "evidence": list(evidence), "changes_the_rule": False}


def self_test() -> dict:
    """A protected rule blocks, a narrow scope cannot loosen a wide one, nothing is skipped."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except GuardrailError:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    secret_rule = Guardrail(
        "guard.no_secret_in_output", "Keep credentials out of anything written",
        "secret", "block", "on_output",
        "write a credential value into an output or a record",
        evidence_required=("secret_scan_passed",))
    cost_rule = Guardrail(
        "guard.prefer_deterministic", "Try the registered resolver before a model",
        "cost", "warn", "before_dispatch",
        "call a model before the registered deterministic attempt has run",
        evidence_required=("deterministic_attempted",))
    judged_rule = Guardrail(
        "guard.tone_for_regulated", "Regulated material is answered plainly",
        "data_handling", "warn", "on_output",
        "answer regulated material without plain language",
        judge="model_judged", scope="project",
        applies_to=TagSet({"data_sensitivity": ("regulated",)}),
        on_unavailable="escalate")
    # Sorts before the blocking rule alphabetically and is weaker, so the order
    # below shows strictness rather than the alphabet.
    advice_rule = Guardrail(
        "guard.a_plain_heading", "Give the answer a plain heading",
        "style", "advise", "on_output", "leave the answer without a heading")
    # Declares that it refuses rather than escalates when its judge is absent.
    strict_judged = Guardrail(
        "guard.z_needs_a_judge", "A judged obligation with no judge refuses",
        "quality", "block", "on_output", "answer without the judged obligation met",
        judge="model_judged", on_unavailable="refuse")
    rules = GuardrailSet()
    for rule in (secret_rule, cost_rule, judged_rule, advice_rule, strict_judged):
        rules.register(rule)
    check("a_protected_category_blocks_and_cannot_be_softened",
          secret_rule.level == "block"
          and refuses(lambda: Guardrail("g", "p", "secret", "warn", "on_output", "o"))
          and refuses(lambda: Guardrail("g", "p", "permission", "advise", "before_effect", "o"))
          and refuses(lambda: Guardrail("g", "p", "spending", "observe", "before_effect", "o"))
          and Guardrail("g", "p", "cost", "advise", "on_output", "o").level == "advise"
          and refuses(lambda: Guardrail("g", "p", "invented", "block", "on_output", "o"))
          and refuses(lambda: Guardrail("g", "p", "cost", "permit", "on_output", "o"))
          and refuses(lambda: Guardrail("g", "p", "cost", "warn", "whenever", "o")),
          secret_rule.digest[:12])
    check("a_narrower_scope_cannot_lower_the_level_of_a_wider_one_on_the_same_obligation",
          refuses(lambda: rules.register(Guardrail(
              "guard.local_exception", "p", "cost", "advise", "before_dispatch",
              "call a model before the registered deterministic attempt has run",
              scope="node")))
          and rules.register(Guardrail(
              "guard.stricter_here", "p", "cost", "block", "before_dispatch",
              "call a model before the registered deterministic attempt has run",
              scope="node")) is None
          and refuses(lambda: rules.register(Guardrail(
              "guard.prefer_deterministic", "different terms", "cost", "warn",
              "before_dispatch", "something else")))
          and refuses(lambda: rules.register("not a rule")))
    at_output = rules.applicable(TagSet({"data_sensitivity": ("regulated",)}), "on_output")
    elsewhere = rules.applicable(TagSet({"data_sensitivity": ("public",)}), "on_output")
    check("only_the_rules_for_this_point_and_this_work_are_applicable_strictest_first",
          # Blocking rules first, then the warning, then the advice, even though
          # the advisory rule sorts first alphabetically.
          [rule.guardrail_id for rule in at_output]
          == ["guard.no_secret_in_output", "guard.z_needs_a_judge",
              "guard.tone_for_regulated", "guard.a_plain_heading"]
          and [rule.guardrail_id for rule in elsewhere]
          == ["guard.no_secret_in_output", "guard.z_needs_a_judge",
              "guard.a_plain_heading"]
          and refuses(lambda: secret_rule.applies(EMPTY_TAGS, "whenever")),
          str([rule.guardrail_id for rule in at_output]))
    clean = evaluate(at_output, {"secret_scan_passed": True}, point="on_output",
                     tags=TagSet({"data_sensitivity": ("regulated",)}))
    outcomes = {row["guardrail_id"]: row for row in clean["decisions"]}
    check("a_rule_that_cannot_be_evaluated_does_what_it_declared_rather_than_passing",
          clean["evaluated"] == 4
          and outcomes["guard.no_secret_in_output"]["outcome"] == "passed"
          and outcomes["guard.tone_for_regulated"]["outcome"] == "unavailable"
          and outcomes["guard.tone_for_regulated"]["consequence"] == "escalate"
          and clean["escalated_by"] == ["guard.tone_for_regulated"]
          # The rule that declared it refuses blocks instead, on the same
          # missing judge, which is the whole point of declaring it in advance.
          and outcomes["guard.z_needs_a_judge"]["outcome"] == "unavailable"
          and outcomes["guard.z_needs_a_judge"]["consequence"] == "refuse"
          and clean["blocked_by"] == ["guard.z_needs_a_judge"]
          and clean["blocked"] is True,
          str(clean["blocked_by"]))
    leaking = evaluate(at_output, {}, point="on_output",
                       tags=TagSet({"data_sensitivity": ("regulated",)}),
                       judge=lambda rule, subject: False)
    fired = {row["guardrail_id"]: row for row in leaking["decisions"]}
    check("a_blocking_rule_that_fires_blocks_and_a_warning_that_fires_does_not",
          leaking["blocked"] is True
          and "guard.no_secret_in_output" in leaking["blocked_by"]
          and fired["guard.no_secret_in_output"]["consequence"] == "blocked"
          and fired["guard.tone_for_regulated"]["consequence"] == "warn"
          and "guard.no_secret_in_output" in leaking["fired"]
          and "guard.tone_for_regulated" in leaking["fired"]
          and fired["guard.a_plain_heading"]["consequence"] == "none"
          and refuses(lambda: evaluate(at_output, "not a mapping"))
          and refuses(lambda: evaluate(("not a rule",), {}))
          and refuses(lambda: evaluate(at_output, {}, point="on_output",
                                       tags=TagSet({"data_sensitivity": ("regulated",)}),
                                       judge=lambda rule, subject: "maybe")),
          str(leaking["blocked_by"]))
    lines = refusal_lines(at_output)
    check("an_instance_is_told_to_refuse_in_the_words_of_the_rules_that_apply",
          lines == ("You must not: write a credential value into an output or a record",
                    "You must not: answer without the judged obligation met",
                    "Avoid: answer regulated material without plain language",
                    "Prefer not to: leave the answer without a heading")
          and refusal_lines((Guardrail("g", "p", "style", "observe", "on_output", "o"),)) == ()
          and refuses(lambda: refusal_lines(("not a rule",))),
          str(lines[0]))
    examined = review(fired["guard.no_secret_in_output"], reviewer="an independent reviewer",
                      verdict="work_was_wrong",
                      evidence=("the output carried a value matching a secret pattern",))
    check("a_firing_can_be_examined_and_the_review_never_changes_the_rule",
          examined["verdict"] == "work_was_wrong"
          and examined["changes_the_rule"] is False
          and examined["digest"] == secret_rule.digest
          and refuses(lambda: review(fired["guard.no_secret_in_output"], reviewer="r",
                                     verdict="rule_is_silly", evidence=("x",)))
          and refuses(lambda: review(fired["guard.no_secret_in_output"], reviewer="r",
                                     verdict="work_was_wrong", evidence=()))
          and refuses(lambda: review({"record_type": "other"}, reviewer="r",
                                     verdict="work_was_wrong", evidence=("x",))),
          examined["verdict"])
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "guardrail_intelligence_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
