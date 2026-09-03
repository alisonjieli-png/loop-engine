"""One shape for every task-conditioned choice the runtime asks a model to make.

A recovery policy written as a table — which errors retry, how many times, how
long to wait, how far to compact — is a set of task-conditioned decisions
frozen by whoever wrote the table, usually from a handful of runs. It works
until it meets a task the author had not seen, and it never says why it chose
what it chose, so nothing accumulates that could justify a better table later.

This module inverts that. The runtime enumerates what is *mechanically
possible* — this route has no credential, that one's window cannot hold the
request, this checkpoint exists — and a model chooses among those facts. The
choice, the options it was made from, and the reason travel in one shape.

The shape is the point. A decision recorded the same way everywhere can be
counted, compared across tasks and models, and eventually replayed: given
enough of them, a narrow region may be distilled into deterministic policy
that reproduces what reasoning actually did, rather than what someone guessed
it would do. A table written first forecloses that; a table fitted afterwards
is evidence. Nothing here decides when that is warranted.

Three things a caller may be asked for, in one contract:

    select      choose among the eligible options
    adjust      change named settings within stated bounds
    propose     name an option nobody enumerated

Owns:
    - ChoiceOption, ChoiceRequest, ChoiceResponse: the typed interface.
    - render_choice(): the standard block a packet carries.
    - admitted_choice(): the response, checked against what was offered.

Does not own: what the options are (each caller enumerates its own), whether
the choice was good (verification), or the count of who decided
(core.semantic_decision).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

CHOICE_REQUEST_RECORD_TYPE = "choice_request/v1"
CHOICE_RESPONSE_RECORD_TYPE = "choice_response/v1"


class ChoiceError(ValueError):
    """A choice request or response violated its contract."""


@dataclass(frozen=True)
class ChoiceOption:
    """One thing that could be done, and what is mechanically true about it.

    Eligibility is a fact, not an opinion: a route with no credential cannot
    be used however attractive it looks, and saying so costs a model nothing
    to read. An ineligible option is still shown, with its reason, because a
    caller that cannot see why an option is unavailable will keep proposing
    it, and because the absence itself is sometimes the finding.
    """

    option_id: str
    summary: str
    eligible: bool = True
    ineligible_reason: str = ""
    facts: dict = field(default_factory=dict)

    def __post_init__(self):
        if not str(self.option_id or "").strip():
            raise ChoiceError("a choice option needs an option_id")
        if not self.eligible and not self.ineligible_reason:
            raise ChoiceError(
                f"option {self.option_id!r} is ineligible without a reason")

    def to_dict(self) -> dict:
        value = {"option_id": self.option_id, "summary": self.summary,
                 "eligible": self.eligible}
        if self.ineligible_reason:
            value["ineligible_reason"] = self.ineligible_reason
        if self.facts:
            value["facts"] = dict(self.facts)
        return value


#: The value types a parameter may declare, named once so that the checks
#: below refer to this table rather than restating its keys inline.
NUMBER, INTEGER, BOOLEAN, STRING, ENUM = (
    "number", "integer", "boolean", "string", "enum")
VALUE_TYPES = {NUMBER: (int, float), INTEGER: (int,), BOOLEAN: (bool,),
               STRING: (str,), ENUM: (str, int, float, bool)}


@dataclass(frozen=True)
class ParameterSpec:
    """A setting a caller may change, and the bound that will be enforced.

    A bound written as prose — "between 512 and 65536" — reads like a
    constraint and is not one. The first version of this module rendered
    exactly that under a heading promising enforcement, while admission
    checked only that the setting's name had been offered. A model could
    return any value at all and it would be admitted.

    So a bound is a value here, not a sentence. ``validate`` returns the
    reason a proposal fails, or an empty string when it holds, and admission
    refuses on that reason rather than on the name alone.
    """

    parameter_id: str
    name: str
    value_type: str = "string"
    current_value: object = None
    minimum: "float | int | None" = None
    maximum: "float | int | None" = None
    enum_values: tuple = ()
    unit: str = ""
    mutable_for_this_call: bool = True
    semantic_effect: str = ""
    authority_ref: str = ""

    def __post_init__(self):
        if self.value_type not in VALUE_TYPES:
            raise ChoiceError(
                f"parameter {self.name!r} has unknown value_type "
                f"{self.value_type!r}")
        if self.value_type == ENUM and not self.enum_values:
            raise ChoiceError(
                f"enum parameter {self.name!r} offers no values")

    def validate(self, value) -> str:
        """Why this proposed value cannot be used, or "" when it can."""
        if not self.mutable_for_this_call:
            return "this setting cannot be changed for this call"
        allowed = VALUE_TYPES[self.value_type]
        # A boolean is an int in Python and almost never what a numeric
        # setting meant, so it is refused rather than silently coerced.
        if isinstance(value, bool) and self.value_type in (NUMBER, INTEGER):
            return f"expected {self.value_type}, got boolean"
        if not isinstance(value, allowed):
            return f"expected {self.value_type}, got {type(value).__name__}"
        if self.value_type == INTEGER and isinstance(value, float):
            return "expected integer, got number"
        if self.enum_values and value not in self.enum_values:
            return f"{value!r} is not one of {list(self.enum_values)}"
        if self.minimum is not None and value < self.minimum:
            return f"{value} is below the minimum of {self.minimum}"
        if self.maximum is not None and value > self.maximum:
            return f"{value} is above the maximum of {self.maximum}"
        return ""

    def rendered(self) -> str:
        """The bound as the model sees it, matching what is enforced."""
        parts = [self.value_type]
        if self.enum_values:
            parts.append("one of " + ", ".join(
                repr(item) for item in self.enum_values))
        if self.minimum is not None or self.maximum is not None:
            parts.append(f"from {self.minimum} to {self.maximum}")
        if self.unit:
            parts.append(f"in {self.unit}")
        if self.current_value is not None:
            parts.append(f"currently {self.current_value!r}")
        if not self.mutable_for_this_call:
            parts.append("NOT changeable for this call")
        return "; ".join(parts)

    def to_dict(self) -> dict:
        return {"parameter_id": self.parameter_id, "name": self.name,
                "value_type": self.value_type,
                "current_value": self.current_value,
                "minimum": self.minimum, "maximum": self.maximum,
                "enum_values": list(self.enum_values), "unit": self.unit,
                "mutable_for_this_call": self.mutable_for_this_call,
                "semantic_effect": self.semantic_effect}


@dataclass(frozen=True)
class ChoiceRequest:
    """What is being decided, from which options, under what limits."""

    decision_kind: str
    question: str
    options: tuple[ChoiceOption, ...] = ()
    evidence: dict = field(default_factory=dict)
    #: Settings whose bounds are enforced on admission.
    parameters: tuple = ()
    #: Compatibility: names described in prose. Nothing about these can be
    #: checked, so they are rendered as unenforced and say so.
    adjustable: dict = field(default_factory=dict)
    authority: tuple[str, ...] = ()
    allow_multiple: bool = True
    allow_novel: bool = True

    def __post_init__(self):
        if not str(self.decision_kind or "").strip():
            raise ChoiceError("a choice request needs a decision_kind")
        seen = [item.option_id for item in self.options]
        if len(set(seen)) != len(seen):
            raise ChoiceError("choice options repeat an option_id")
        named = [item.name for item in self.parameters]
        if len(set(named)) != len(named):
            raise ChoiceError("choice parameters repeat a name")

    @property
    def eligible_ids(self) -> tuple[str, ...]:
        return tuple(item.option_id for item in self.options if item.eligible)

    def to_dict(self) -> dict:
        return {
            "record_type": CHOICE_REQUEST_RECORD_TYPE,
            "decision_kind": self.decision_kind,
            "question": self.question,
            "options": [item.to_dict() for item in self.options],
            "evidence": dict(self.evidence),
            "parameters": [item.to_dict() for item in self.parameters],
            "adjustable": dict(self.adjustable),
            "authority": list(self.authority),
            "allow_multiple": self.allow_multiple,
            "allow_novel": self.allow_novel,
        }


#: The answer shape, identical for every decision anywhere in the runtime.
CHOICE_RESPONSE_CONTRACT = json.dumps({
    "selected": ["option_id values, in the order they should be attempted"],
    "adjustments": {"setting_name": "new value, within the stated bounds"},
    "novel": {"summary": "an option none of the above covers", "why": "string"},
    "reason": "why this, in one or two sentences",
    "expected_observation": "what should be true if this works",
    "exit_condition": "when to stop trying this line",
    "confidence": 0.0,
}, separators=(",", ":"))


def render_choice(request: ChoiceRequest) -> str:
    """The standard block a packet carries when a choice is being asked for."""
    lines = [f"DECISION: {request.question}",
             f"KIND: {request.decision_kind}", "", "OPTIONS:"]
    for item in request.options:
        mark = "" if item.eligible else "  [UNAVAILABLE: "
        tail = "" if item.eligible else f"{item.ineligible_reason}]"
        lines.append(f"  {item.option_id}: {item.summary}{mark}{tail}")
        for name, fact in (item.facts or {}).items():
            lines.append(f"      {name}: {fact}")
    if request.parameters:
        lines += ["", "SETTINGS YOU MAY ADJUST. These bounds are checked on "
                      "admission; a value outside them is refused, not "
                      "clamped:"]
        for item in request.parameters:
            lines.append(f"  {item.name}: {item.rendered()}")
            if item.semantic_effect:
                lines.append(f"      effect: {item.semantic_effect}")
    if request.adjustable:
        # Described in prose, so nothing about the value can be checked. Say
        # so rather than implying a bound that admission cannot enforce.
        lines += ["", "SETTINGS YOU MAY ADJUST (described only; the value "
                      "you give is not range-checked):"]
        for name, bound in request.adjustable.items():
            lines.append(f"  {name}: {bound}")
    if request.evidence:
        lines += ["", "EVIDENCE:",
                  json.dumps(request.evidence, indent=1, default=str)[:4000]]
    if request.authority:
        lines += ["", "AUTHORITY:"] + [f"  {item}" for item in
                                       request.authority]
    lines += [
        "",
        "An option marked UNAVAILABLE cannot be used; do not select it. "
        "Selecting nothing is a valid answer when nothing here should be "
        "tried." if request.options else
        "There are no enumerated options; propose one.",
    ]
    if request.allow_novel:
        lines.append(
            "If none of these is right, put what should happen under `novel`. "
            "An option nobody listed is the most useful thing you can return.")
    lines += ["", "Return exactly this JSON and nothing else:",
              CHOICE_RESPONSE_CONTRACT]
    return "\n".join(lines)


@dataclass(frozen=True)
class ChoiceResponse:
    """One answer, kept to what was actually offered."""

    selected: tuple[str, ...] = ()
    adjustments: dict = field(default_factory=dict)
    novel: dict = field(default_factory=dict)
    reason: str = ""
    expected_observation: str = ""
    exit_condition: str = ""
    confidence: "float | None" = None
    refused: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "record_type": CHOICE_RESPONSE_RECORD_TYPE,
            "selected": list(self.selected),
            "adjustments": dict(self.adjustments),
            "novel": dict(self.novel),
            "reason": self.reason,
            "expected_observation": self.expected_observation,
            "exit_condition": self.exit_condition,
            "confidence": self.confidence,
            # What was asked for and could not be honoured, kept rather than
            # dropped: a caller repeatedly reaching for an unavailable route
            # is saying something about the options it was given.
            "refused": list(self.refused),
        }


def admitted_choice(value, request: ChoiceRequest) -> ChoiceResponse:
    """Read one answer against the options and bounds it was offered.

    Selections outside the eligible set are refused rather than dropped in
    silence or passed through: counting them is how the option list gets
    better. Adjustments outside their stated bounds are refused the same way.
    """
    if not isinstance(value, dict):
        raise ChoiceError("a choice response must be one object")
    eligible = set(request.eligible_ids)
    wanted = value.get("selected")
    if isinstance(wanted, str):
        wanted = [wanted]
    wanted = [str(item) for item in (wanted or []) if str(item).strip()]
    selected = tuple(item for item in wanted if item in eligible)
    refused = tuple(item for item in wanted if item not in eligible)
    if selected and not request.allow_multiple:
        selected = selected[:1]

    adjustments = {}
    proposed = value.get("adjustments")
    specs = {item.name: item for item in request.parameters}
    if isinstance(proposed, dict):
        for name, item in proposed.items():
            spec = specs.get(name)
            if spec is not None:
                problem = spec.validate(item)
                if problem:
                    refused = refused + (f"adjustment:{name}: {problem}",)
                else:
                    adjustments[str(name)] = item
            elif name in request.adjustable:
                adjustments[str(name)] = item
            else:
                refused = refused + (f"adjustment:{name}",)

    novel = value.get("novel")
    if not isinstance(novel, dict) or not novel.get("summary"):
        novel = {}
    elif not request.allow_novel:
        refused = refused + ("novel",)
        novel = {}

    confidence = value.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        confidence = None

    return ChoiceResponse(
        selected=selected, adjustments=adjustments, novel=novel,
        reason=str(value.get("reason") or "")[:600],
        expected_observation=str(value.get("expected_observation") or "")[:400],
        exit_condition=str(value.get("exit_condition") or "")[:300],
        confidence=confidence, refused=refused)


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    request = ChoiceRequest(
        decision_kind="choose_recovery",
        question="The provider returned no answer. What should happen next?",
        options=(
            ChoiceOption("retry_same_route", "Ask the same route again",
                         facts={"attempts_so_far": 1}),
            ChoiceOption("other_model_same_provider",
                         "Try another model on this provider"),
            ChoiceOption("other_provider", "Try a different provider",
                         eligible=False,
                         ineligible_reason="no credential is configured"),
        ),
        adjustable={"max_output_tokens": "between 512 and 65536"},
        authority=("cross-provider failover allowed",))

    refused_bad = False
    try:
        ChoiceOption("x", "y", eligible=False)
    except ChoiceError:
        refused_bad = True
    check("an unavailable option must say why", refused_bad)

    rendered = render_choice(request)
    check("the rendered block shows why an option cannot be used",
          "UNAVAILABLE: no credential is configured" in rendered
          and "max_output_tokens" in rendered)

    good = admitted_choice({
        "selected": ["retry_same_route", "other_model_same_provider"],
        "adjustments": {"max_output_tokens": 8192},
        "reason": "The route answered before, so one more sample is cheap.",
        "confidence": 0.7}, request)
    check("an answer within the offer is admitted in order",
          good.selected == ("retry_same_route", "other_model_same_provider")
          and good.adjustments == {"max_output_tokens": 8192}
          and good.confidence == 0.7 and not good.refused)

    reaching = admitted_choice({
        "selected": ["other_provider", "retry_same_route"],
        "adjustments": {"temperature": 1.5}}, request)
    check("an unavailable pick is refused and counted, not silently dropped",
          reaching.selected == ("retry_same_route",)
          and "other_provider" in reaching.refused
          and "adjustment:temperature" in reaching.refused)

    invented = admitted_choice({
        "selected": [],
        "novel": {"summary": "split the request into two smaller calls",
                  "why": "the packet will not fit either route"}}, request)
    check("an option nobody enumerated survives",
          invented.novel["summary"].startswith("split the request")
          and invented.selected == ())

    closed = ChoiceRequest(decision_kind="k", question="q",
                           options=(ChoiceOption("a", "a"),),
                           allow_novel=False)
    check("a closed request refuses a novel answer and says so",
          admitted_choice({"novel": {"summary": "x"}}, closed).refused
          == ("novel",))

    check("selecting nothing is a valid answer",
          admitted_choice({"selected": []}, request).selected == ())

    duplicate = False
    try:
        ChoiceRequest(decision_kind="k", question="q",
                      options=(ChoiceOption("a", "1"), ChoiceOption("a", "2")))
    except ChoiceError:
        duplicate = True
    check("a repeated option_id is refused", duplicate)

    # A bound the model is shown must be a bound admission enforces. The
    # first version of this module rendered "bounds are enforced" over prose
    # ranges and checked only that a setting's name had been offered.
    bounded = ChoiceRequest(
        decision_kind="configure", question="adjust for the next attempt",
        options=(ChoiceOption("go", "proceed"),),
        parameters=(
            ParameterSpec("p.out", "max_output_tokens", "integer", 8192,
                          minimum=512, maximum=65536, unit="tokens"),
            ParameterSpec("p.t", "temperature", "number", 0.7,
                          minimum=0.0, maximum=1.5),
            ParameterSpec("p.route", "route", "enum", "a",
                          enum_values=("a", "b")),
            ParameterSpec("p.fixed", "seed", "integer", 42,
                          mutable_for_this_call=False)))
    checks = {
        "above maximum": ({"max_output_tokens": 999999}, False),
        "below minimum": ({"max_output_tokens": 8}, False),
        "wrong type": ({"max_output_tokens": "large"}, False),
        "float for integer": ({"max_output_tokens": 1.5}, False),
        "boolean for number": ({"temperature": True}, False),
        "outside enum": ({"route": "z"}, False),
        "immutable setting": ({"seed": 7}, False),
        "within bounds": ({"max_output_tokens": 4096}, True),
        "valid enum": ({"route": "b"}, True),
    }
    outcomes = {}
    for label, (patch, should_pass) in checks.items():
        answer = admitted_choice({"adjustments": patch}, bounded)
        outcomes[label] = (bool(answer.adjustments) == should_pass)
    wrong = [label for label, ok in outcomes.items() if not ok]
    check("every advertised bound is enforced on admission",
          not wrong, f"not enforced: {wrong}")
    check("a refused adjustment says why it was refused",
          any("above the maximum" in item for item in admitted_choice(
              {"adjustments": {"max_output_tokens": 999999}},
              bounded).refused))
    check("the rendered bound matches what admission checks",
          "from 512 to 65536" in render_choice(bounded)
          and "not clamped" in render_choice(bounded))
    check("a prose bound is rendered as unenforced rather than as a bound",
          "not range-checked" in render_choice(ChoiceRequest(
              decision_kind="k", question="q",
              adjustable={"x": "between 1 and 2"})))
    unknown_type = False
    try:
        ParameterSpec("p", "n", "quantity")
    except ChoiceError:
        unknown_type = True
    check("a parameter with an unknown type is refused", unknown_type)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "choice_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
