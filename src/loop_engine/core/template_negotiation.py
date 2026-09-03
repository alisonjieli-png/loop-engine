"""A response template the caller may argue with, and the parts it may not.

A schema handed to a model is a hypothesis about what shape the answer should
take. It is usually right and sometimes wrong: a template asking for one root
cause forces a single answer from evidence that supports three, and a template
asking for one next action discards the topology of a task that needs two
experiments and a join. A model that fills such a template obediently has
produced a well-formed misrepresentation, and nothing downstream can tell.

So the template is offered rather than imposed. A caller may accept it, extend
it, modify its fields, simplify it, replace it, or ignore it outright, and
must say which and why. Departure is not noncompliance; it is sometimes the
better reasoning, and it is always evidence about the template.

What stays fixed is narrow and load-bearing. Identity, versioning and
provenance stay, because a reply nobody can attribute or replay is not an
answer. Authority stays, because the escape hatch must never become the route
by which a caller grants itself a permission, widens an effect, or rewrites
what would count as success. Those are refused whatever disposition is
claimed, and the attempt is recorded rather than quietly dropped: a reply that
reaches for authority is worth seeing.

Owns:
    - FIELD_CLASSES: how negotiable each field of a template is.
    - TEMPLATE_DISPOSITIONS: the answers a caller may give about the template.
    - ResponseTemplate, TemplateField: the offer.
    - admitted_template_response(): the reply, with authority held fixed.

Does not own: choosing among options (core.choice), who decided
(core.semantic_decision), or whether the answer was any good (verification).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

TEMPLATE_OFFER_RECORD_TYPE = "response_template/v1"
TEMPLATE_REPLY_RECORD_TYPE = "template_negotiated_response/v1"

#: Needed to identify, parse, version and replay a reply. Never negotiable,
#: because an answer nobody can attribute is not usable as one.
PROTOCOL_REQUIRED = "protocol_required"
#: Permissions, effects, acceptance and state. Never negotiable, and never
#: settable by the reply: this is the field class the escape hatch must not
#: become a way around.
AUTHORITY_REQUIRED = "authority_required"
#: The downstream consumer needs it. Challengeable — a rigid consumer is a
#: finding — but its absence has to be reconciled rather than ignored.
CONSUMER_REQUIRED = "consumer_required"
#: Believed useful for this responsibility. Fully negotiable.
SEMANTIC_EXPECTED = "semantic_expected"
ADVISORY = "advisory"
OPTIONAL = "optional"
#: Where a reply may put something the template never imagined.
EXTENSION_POINT = "extension_point"
#: Bounded raw result, for when structure would destroy the meaning.
FREEFORM_ESCAPE = "freeform_escape"

FIELD_CLASSES = (PROTOCOL_REQUIRED, AUTHORITY_REQUIRED, CONSUMER_REQUIRED,
                 SEMANTIC_EXPECTED, ADVISORY, OPTIONAL, EXTENSION_POINT,
                 FREEFORM_ESCAPE)
#: The two classes no disposition can excuse.
FIXED_CLASSES = (PROTOCOL_REQUIRED, AUTHORITY_REQUIRED)

#: What a reply may say about the shape it was offered.
ACCEPT_AS_IS = "ACCEPT_AS_IS"
ACCEPT_WITH_EXTENSIONS = "ACCEPT_WITH_EXTENSIONS"
MODIFY_FIELDS = "MODIFY_FIELDS"
SIMPLIFY = "SIMPLIFY"
COMPOSE = "COMPOSE"
REPLACE = "REPLACE"
IGNORE = "IGNORE"
REQUEST_ALTERNATIVE = "REQUEST_ALTERNATIVE"
DEFER_CONTRACT = "DEFER_CONTRACT"
ABSTAIN = "ABSTAIN"

TEMPLATE_DISPOSITIONS = (
    ACCEPT_AS_IS, ACCEPT_WITH_EXTENSIONS, MODIFY_FIELDS, SIMPLIFY, COMPOSE,
    REPLACE, IGNORE, REQUEST_ALTERNATIVE, DEFER_CONTRACT, ABSTAIN)

#: Dispositions that set the offered semantic fields aside. Each still owes a
#: reason and a self-describing result: departing from a shape is a claim that
#: another one represents the work better, and the claim should be legible.
DEPARTING_DISPOSITIONS = (MODIFY_FIELDS, SIMPLIFY, COMPOSE, REPLACE, IGNORE)


class TemplateNegotiationError(ValueError):
    """A template offer or a negotiated reply violated its contract."""


@dataclass(frozen=True)
class TemplateField:
    """One field of an offered template, and how negotiable it is."""

    name: str
    field_class: str = SEMANTIC_EXPECTED
    description: str = ""

    def __post_init__(self):
        if self.field_class not in FIELD_CLASSES:
            raise TemplateNegotiationError(
                f"field {self.name!r} has unknown class {self.field_class!r}")

    @property
    def negotiable(self) -> bool:
        return self.field_class not in FIXED_CLASSES


@dataclass(frozen=True)
class ResponseTemplate:
    """The shape a caller is offered, and told it may argue with."""

    template_id: str
    fields: tuple[TemplateField, ...] = ()
    purpose: str = ""

    def __post_init__(self):
        names = [item.name for item in self.fields]
        if len(set(names)) != len(names):
            raise TemplateNegotiationError("template repeats a field name")

    def of_class(self, *classes) -> tuple[str, ...]:
        return tuple(item.name for item in self.fields
                     if item.field_class in classes)

    def to_dict(self) -> dict:
        return {"record_type": TEMPLATE_OFFER_RECORD_TYPE,
                "template_id": self.template_id, "purpose": self.purpose,
                "fields": [{"name": item.name, "class": item.field_class,
                            "description": item.description}
                           for item in self.fields]}


def render_template(template: ResponseTemplate) -> str:
    """The offer, stated as an offer rather than as an instruction."""
    lines = [f"SUGGESTED RESPONSE SHAPE: {template.template_id}"]
    if template.purpose:
        lines.append(f"PURPOSE: {template.purpose}")
    lines.append("")
    for item in template.fields:
        fixed = " [REQUIRED — not negotiable]" if not item.negotiable else ""
        lines.append(f"  {item.name} ({item.field_class}){fixed}")
        if item.description:
            lines.append(f"      {item.description}")
    lines += [
        "",
        "This shape is what we currently believe will represent the work "
        "well. It is a suggestion about form, not a limit on thought. If it "
        "would make you state a certainty the evidence does not support, "
        "collapse several findings into one, or discard structure the task "
        "needs, then change it and say so.",
        "",
        "Set `template_disposition.disposition` to one of: "
        + ", ".join(TEMPLATE_DISPOSITIONS) + ", give a `reason`, and when you "
        "depart from the shape return `result_kind` and `result_payload` "
        "describing what you returned instead.",
        "",
        "Fields marked not negotiable identify and authorise the reply. They "
        "are kept whatever you choose. Changing the shape of an answer is "
        "yours; changing what you are permitted to do, or what would count as "
        "success, is not — those are held by the runtime and any attempt to "
        "set them is refused and recorded.",
    ]
    return "\n".join(lines)


@dataclass(frozen=True)
class NegotiatedResponse:
    """One reply, with the template's fate and the authority held fixed."""

    disposition: str = ACCEPT_AS_IS
    reason: str = ""
    fields: dict = field(default_factory=dict)
    result_kind: str = ""
    result_payload: object = None
    #: Kept together on purpose: a caller whose natural answer is a graph
    #: should not have to destroy it to satisfy a consumer that wants one
    #: scalar. The projection serves the consumer; it does not become the
    #: only surviving copy of the reasoning.
    natural_result: object = None
    consumer_projection: object = None
    projection_is_lossy: bool = False
    extensions: dict = field(default_factory=dict)
    missing_required: tuple[str, ...] = ()
    unreconciled_consumer_fields: tuple[str, ...] = ()
    #: Attempts to set what the reply does not own. Recorded, never applied.
    refused_authority_claims: tuple[str, ...] = ()

    @property
    def usable(self) -> bool:
        """Whether this reply can be admitted at all."""
        return not self.missing_required and self.disposition != ABSTAIN

    @property
    def departed(self) -> bool:
        return self.disposition in DEPARTING_DISPOSITIONS

    def to_dict(self) -> dict:
        return {
            "record_type": TEMPLATE_REPLY_RECORD_TYPE,
            "disposition": self.disposition, "reason": self.reason,
            "result_kind": self.result_kind,
            "fields": dict(self.fields),
            "extensions": dict(self.extensions),
            "projection_is_lossy": self.projection_is_lossy,
            "missing_required": list(self.missing_required),
            "unreconciled_consumer_fields": list(
                self.unreconciled_consumer_fields),
            "refused_authority_claims": list(self.refused_authority_claims),
        }


def admitted_template_response(value, template: ResponseTemplate,
                               governed: "dict | None" = None
                               ) -> NegotiatedResponse:
    """Read a reply that may have argued with the shape it was offered.

    ``governed`` holds the values the runtime owns — permissions, effects,
    acceptance, state revision. A reply that tries to set any of them is
    refused on that field regardless of the disposition it claimed, and the
    attempt is kept: departing from a template is legitimate, and reaching
    for authority through the departure is a different act entirely.
    """
    if not isinstance(value, dict):
        raise TemplateNegotiationError("a negotiated reply must be one object")
    governed = dict(governed or {})

    stated = value.get("template_disposition")
    if isinstance(stated, str):
        stated = {"disposition": stated}
    stated = stated if isinstance(stated, dict) else {}
    disposition = str(stated.get("disposition") or ACCEPT_AS_IS).upper()
    if disposition not in TEMPLATE_DISPOSITIONS:
        disposition = ACCEPT_AS_IS

    # Authority first, and independently of the disposition claimed.
    refused = []
    for name in governed:
        if name in value and value[name] != governed[name]:
            refused.append(name)
    for name in template.of_class(AUTHORITY_REQUIRED):
        if name in value and name in governed and name not in refused:
            continue
        if name in value and name not in governed:
            refused.append(name)

    kept = {name: item for name, item in value.items()
            if name not in refused and name != "template_disposition"}
    for name in governed:
        kept[name] = governed[name]

    missing = [name for name in template.of_class(PROTOCOL_REQUIRED)
               if name not in kept or kept[name] in (None, "")]

    consumer = template.of_class(CONSUMER_REQUIRED)
    semantic = template.of_class(SEMANTIC_EXPECTED)
    departing = disposition in DEPARTING_DISPOSITIONS
    if not departing:
        missing += [name for name in consumer + semantic if name not in kept]
        unreconciled = ()
    else:
        # A departure owes an account of itself: what was returned instead,
        # and why. Without those the reply is not a different representation,
        # it is an incomplete one.
        unreconciled = tuple(name for name in consumer if name not in kept)
        if not str(value.get("result_kind") or "").strip():
            missing.append("result_kind")
        if value.get("result_payload") is None and not kept:
            missing.append("result_payload")
        if not str(stated.get("reason") or "").strip():
            missing.append("template_disposition.reason")

    known = set(template.of_class(*FIELD_CLASSES))
    extensions = {name: item for name, item in kept.items()
                  if name not in known and name not in governed
                  and name not in ("result_kind", "result_payload",
                                   "natural_result", "consumer_projection",
                                   "projection_is_lossy")}

    return NegotiatedResponse(
        disposition=disposition,
        reason=str(stated.get("reason") or "")[:600],
        fields={name: item for name, item in kept.items() if name in known},
        result_kind=str(value.get("result_kind") or "")[:120],
        result_payload=value.get("result_payload"),
        natural_result=value.get("natural_result"),
        consumer_projection=value.get("consumer_projection"),
        projection_is_lossy=bool(value.get("projection_is_lossy")),
        extensions=extensions,
        missing_required=tuple(dict.fromkeys(missing)),
        unreconciled_consumer_fields=unreconciled,
        refused_authority_claims=tuple(sorted(set(refused))))


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    template = ResponseTemplate(
        template_id="schema.single_next_action@1.0.0",
        purpose="choose one next action",
        fields=(
            TemplateField("call_id", PROTOCOL_REQUIRED),
            TemplateField("permissions", AUTHORITY_REQUIRED),
            TemplateField("selected_next_action", CONSUMER_REQUIRED),
            TemplateField("root_cause", SEMANTIC_EXPECTED),
            TemplateField("notes", OPTIONAL)))
    governed = {"permissions": ["workspace_write"],
                "acceptance_criteria": "the submission verifies"}

    rendered = render_template(template)
    check("the shape is offered as a suggestion, not an instruction",
          "not a limit on thought" in rendered
          and "REQUIRED — not negotiable" in rendered)

    plain = admitted_template_response(
        {"call_id": "c1", "selected_next_action": "run_tests",
         "root_cause": "off-by-one"}, template, governed)
    check("an accepted template is admitted with authority supplied",
          plain.usable and plain.disposition == ACCEPT_AS_IS
          and plain.fields["permissions"] == ["workspace_write"])

    # The user's own example: several unresolved hypotheses, one label asked.
    replaced = admitted_template_response({
        "call_id": "c2",
        "template_disposition": {
            "disposition": IGNORE,
            "reason": "the evidence supports several unresolved hypotheses"},
        "result_kind": "hypothesis_portfolio",
        "result_payload": {"hypotheses": ["a", "b"],
                           "discriminating_experiments": ["t1"]}},
        template, governed)
    check("ignoring the shape is admitted when it says what it returned",
          replaced.usable and replaced.departed
          and replaced.result_kind == "hypothesis_portfolio"
          and "root_cause" not in replaced.fields)
    check("a consumer field dropped by a departure is reported, not hidden",
          replaced.unreconciled_consumer_fields
          == ("selected_next_action",))

    grabbing = admitted_template_response({
        "call_id": "c3",
        "template_disposition": {"disposition": IGNORE, "reason": "r"},
        "result_kind": "k", "result_payload": {},
        "permissions": ["network_read", "workspace_write"],
        "acceptance_criteria": "whatever I produced is sufficient"},
        template, governed)
    check("a departure cannot widen permissions",
          grabbing.fields["permissions"] == ["workspace_write"]
          and "permissions" in grabbing.refused_authority_claims)
    check("a departure cannot rewrite what success means",
          "acceptance_criteria" in grabbing.refused_authority_claims)
    check("the attempt to take authority is kept, not silently dropped",
          len(grabbing.refused_authority_claims) == 2 and grabbing.usable)

    silent = admitted_template_response({
        "call_id": "c4",
        "template_disposition": {"disposition": REPLACE},
        "result_kind": "other"}, template, governed)
    check("a departure without a reason is not usable",
          not silent.usable
          and "template_disposition.reason" in silent.missing_required)

    nameless = admitted_template_response({
        "template_disposition": {"disposition": IGNORE, "reason": "r"},
        "result_kind": "k", "result_payload": {}}, template, governed)
    check("identity survives every disposition",
          not nameless.usable and "call_id" in nameless.missing_required)

    both = admitted_template_response({
        "call_id": "c5",
        "template_disposition": {"disposition": COMPOSE, "reason": "graph"},
        "result_kind": "hypothesis_graph",
        "result_payload": {"nodes": 3},
        "natural_result": {"graph": {"nodes": 3}},
        "consumer_projection": {"selected_next_action": "test_leakage"},
        "projection_is_lossy": True}, template, governed)
    check("a lossy projection does not replace the natural answer",
          both.usable and both.projection_is_lossy
          and both.natural_result == {"graph": {"nodes": 3}}
          and both.consumer_projection["selected_next_action"]
          == "test_leakage")

    extended = admitted_template_response({
        "call_id": "c6", "selected_next_action": "a", "root_cause": "b",
        "template_disposition": {"disposition": ACCEPT_WITH_EXTENSIONS,
                                 "reason": "one more thing was worth saying"},
        "competing_causes": ["x", "y"]}, template, governed)
    check("something the template never imagined is kept",
          extended.extensions == {"competing_causes": ["x", "y"]})

    unknown = admitted_template_response(
        {"call_id": "c7", "selected_next_action": "a", "root_cause": "b",
         "template_disposition": {"disposition": "INVENT_MY_OWN"}},
        template, governed)
    check("an unrecognised disposition falls back to acceptance",
          unknown.disposition == ACCEPT_AS_IS and unknown.usable)

    bad_class = False
    try:
        TemplateField("x", "sort_of_required")
    except TemplateNegotiationError:
        bad_class = True
    check("a field with an unknown class is refused", bad_class)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "template_negotiation_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
