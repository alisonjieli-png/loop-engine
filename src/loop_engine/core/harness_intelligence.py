"""What a harness instance can be given, kept in one place.

The four persistent layers answer what the engine knows. This boundary answers
a narrower question that a provisioning decision actually asks: of everything
the engine knows, what can be handed to a separately initialized harness
instance, in a form that harness reads, and what does handing it over cost and
permit?

WHY THIS IS NOT A FIFTH STORE
An item here is a reference and the facts a provisioning decision needs. It is
never a second copy of the record it points at. One capability keeps one
identity: the code lives in Code Intelligence, the instruction text lives in
Context Intelligence, and an item in this catalogue says which of them a
harness instance may be given, in which form, at what size, under which
license, and with which declared effects. Copying would create two records
that drift, and the semantic rules of this repository give one concept one
authority.

Whether this becomes a fifth queryable layer beside the four is an owner
decision, not one this module takes. Adding a layer name changes the closed
layer vocabulary that conformance, record identities, routing records, and
query contracts all read, so it is a wide change that needs its own review.
This module is a component with its own boundary; promoting it later means
declaring one more layer name, not rewriting this.

WHERE IT SITS AND WHAT IT DOES
Four kinds of item can reach a harness instance: reusable code, a skill, a
tool, and an instruction file. Every item declares a digest, because the
formats these travel in carry none of their own: an instruction file and a
file system skill have no digest, no signature, and no version field in any
published specification read on 2026-09-18. Every item declares its effects,
because no vendor neutral format states what an instance is allowed to do.

TWO PROPERTIES THAT ARE NOT THE SAME
Where a body physically is, and how much of it a model sees, are separate.
A package can be installed on disk while only its one line purpose is visible
in a prompt. The default exposure is metadata only, and a fuller exposure is
asked for rather than assumed, so a step that needs only the purpose never
pays for the body.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .facets import EFFECTS
from .intelligence_tagging import EMPTY_TAGS, TagSet

RECORD_TYPE = "harness_intelligence_item/v1"
CATALOGUE_RECORD_TYPE = "harness_intelligence_offer/v1"
#: What can reach a harness instance.
KINDS = ("reusable_code", "skill", "tool", "instruction_file")
#: Where the body an item points at actually lives.
SOURCE_LAYERS = ("context_intelligence", "code_intelligence",
                 "runtime_history_solution_intelligence", "user_feedback_intelligence",
                 "harness_local")
#: How much of the body a model sees. Physical availability is separate.
EXPOSURES = ("metadata_only", "excerpt", "full_instructions")
#: Where the body physically is, which never implies that a model read it.
AVAILABILITY = ("remote", "cached", "mounted", "installed", "connected")
#: Reusable code keeps its identity in Code Intelligence and is pointed at.
CODE_SOURCE_LAYER = "code_intelligence"
#: A digest is 64 hexadecimal characters.
DIGEST_LENGTH = 64
#: Why an item is not offered. Declared once, because both the list and the
#: single item path must give the same answer to the same question.
WITHHELD_ANOTHER_KIND = "another kind"
WITHHELD_OTHER_TAGS = "filed under other tags"
WITHHELD_ANOTHER_HARNESS = "another harness"
WITHHOLDING_REASONS = (WITHHELD_ANOTHER_KIND, WITHHELD_OTHER_TAGS, WITHHELD_ANOTHER_HARNESS)


class HarnessIntelligenceError(ValueError):
    """An item names an unknown kind, carries no digest, or declares an effect."""


@dataclass(frozen=True)
class HarnessIntelligenceItem:
    """One thing a harness instance can be given, as a reference and its facts."""

    identity: str
    kind: str
    purpose: str
    digest: str
    source_layer: str
    source_ref: str
    size_bytes: int = 0
    license_name: str = ""
    declared_effects: tuple[str, ...] = ()
    styles: tuple[str, ...] = ()
    default_exposure: str = EXPOSURES[0]
    availability: str = AVAILABILITY[0]
    #: The dimensions this item is filed under: role, domain, geography,
    #: language, sensitivity, authentication, lifecycle. An item that declares
    #: nothing is general and is offered to every request.
    tags: TagSet = EMPTY_TAGS

    def __post_init__(self) -> None:
        if not isinstance(self.tags, TagSet):
            raise HarnessIntelligenceError(
                "tags must be a typed tag set; use the empty one to declare that an "
                "item is general rather than untagged")
        if not self.identity.strip() or not self.purpose.strip():
            raise HarnessIntelligenceError("an item needs an identity and a purpose")
        if self.kind not in KINDS:
            raise HarnessIntelligenceError(f"{self.kind!r} is not one of {KINDS}")
        if self.source_layer not in SOURCE_LAYERS:
            raise HarnessIntelligenceError(
                f"{self.source_layer!r} is not one of {SOURCE_LAYERS}")
        if len(self.digest) != DIGEST_LENGTH or not all(
                character in "0123456789abcdef" for character in self.digest):
            raise HarnessIntelligenceError(
                f"item {self.identity!r} carries no digest; the formats these travel in "
                "carry none of their own, so this catalogue computes and keeps one")
        if not self.source_ref.strip():
            raise HarnessIntelligenceError(
                f"item {self.identity!r} must point at the record that holds its body")
        unknown = [effect for effect in self.declared_effects if effect not in EFFECTS]
        if unknown:
            raise HarnessIntelligenceError(
                f"{unknown} is not drawn from the declared effects {EFFECTS}")
        if self.default_exposure not in EXPOSURES:
            raise HarnessIntelligenceError(f"exposure must be one of {EXPOSURES}")
        if self.availability not in AVAILABILITY:
            raise HarnessIntelligenceError(f"availability must be one of {AVAILABILITY}")
        if not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise HarnessIntelligenceError("size is a byte count")
        if self.kind == KINDS[0] and self.source_layer != CODE_SOURCE_LAYER:
            raise HarnessIntelligenceError(
                f"reusable code keeps its identity in {CODE_SOURCE_LAYER} and is pointed "
                f"at from here; item {self.identity!r} names {self.source_layer!r}")

    def reference(self, exposure: str = "") -> dict:
        """The typed reference a step sees. It never carries the body."""
        chosen = exposure or self.default_exposure
        if chosen not in EXPOSURES:
            raise HarnessIntelligenceError(f"exposure must be one of {EXPOSURES}")
        return {"record_type": RECORD_TYPE, "identity": self.identity, "kind": self.kind,
                "purpose": self.purpose, "digest": self.digest,
                "source_layer": self.source_layer, "source_ref": self.source_ref,
                "size_bytes": self.size_bytes, "license": self.license_name,
                "declared_effects": list(self.declared_effects),
                "styles": list(self.styles), "tags": self.tags.to_dict(),
                "exposure": chosen,
                "availability": self.availability, "body_included": False}

    def suits(self, style: str) -> bool:
        """An item with no style named suits every harness."""
        return not self.styles or style in self.styles


@dataclass
class HarnessIntelligenceCatalogue:
    """The items this deployment can offer, registered once and served as references."""

    items: dict = field(default_factory=dict)

    def register(self, item: HarnessIntelligenceItem) -> None:
        if not isinstance(item, HarnessIntelligenceItem):
            raise HarnessIntelligenceError("only a typed item can be registered")
        held = self.items.get(item.identity)
        if held is not None and held.digest != item.digest:
            raise HarnessIntelligenceError(
                f"{item.identity!r} is already registered with a different digest; "
                "one identity carries one body, so register a new identity instead")
        self.items[item.identity] = item

    def kinds_held(self) -> tuple[str, ...]:
        return tuple(kind for kind in KINDS
                     if any(item.kind == kind for item in self.items.values()))


def visibility(item: HarnessIntelligenceItem, *, style: str = "", authority_effects=(),
               kinds=(), tags=None) -> str:
    """Empty when this item may be offered, otherwise the reason it is withheld.

    One authority for the rule, so asking about one item costs the same as
    asking about one item. Building the whole offer to answer a question about
    a single identity is how a catalogue of fifty thousand becomes slow at the
    moment it becomes useful.
    """
    if kinds and item.kind not in kinds:
        return WITHHELD_ANOTHER_KIND
    request = tags if tags is not None else EMPTY_TAGS
    if not isinstance(request, TagSet):
        raise HarnessIntelligenceError("a tag request must be a typed tag set")
    if not item.tags.matches(request):
        return WITHHELD_OTHER_TAGS
    if style and not item.suits(style):
        return WITHHELD_ANOTHER_HARNESS
    beyond = [effect for effect in item.declared_effects
              if effect not in tuple(authority_effects)]
    if beyond:
        return f"declares {beyond}, which this step does not hold"
    return ""


def offer(catalogue: HarnessIntelligenceCatalogue, *, style: str = "",
          authority_effects=(), kinds=(), exposure: str = "", tags=None) -> dict:
    """What this instance may be given, as references with the withheld named.

    An item that declares an effect the step does not hold is not offered at
    all, and the reason is recorded rather than left silent, because an offer
    an instance cannot accept is an invitation to try. Naming a style filters
    out the items bound to another harness; naming none asks across all of
    them, which is what a planning step wants before a harness is chosen.
    """
    held = tuple(authority_effects)
    unknown = [effect for effect in held if effect not in EFFECTS]
    if unknown:
        raise HarnessIntelligenceError(
            f"the authority names {unknown}, outside the declared effects {EFFECTS}")
    wanted = tuple(kinds)
    bad = [kind for kind in wanted if kind not in KINDS]
    if bad:
        raise HarnessIntelligenceError(f"{bad} is not drawn from {KINDS}")
    request = tags if tags is not None else EMPTY_TAGS
    if not isinstance(request, TagSet):
        raise HarnessIntelligenceError("a tag request must be a typed tag set")
    offered, withheld = [], []
    for item in sorted(catalogue.items.values(), key=lambda entry: entry.identity):
        reason = visibility(item, style=style, authority_effects=held, kinds=wanted,
                            tags=request)
        if reason == WITHHELD_ANOTHER_KIND:
            continue
        if reason:
            withheld.append({"identity": item.identity, "reason": reason})
            continue
        offered.append(item.reference(exposure))
    return {"record_type": CATALOGUE_RECORD_TYPE, "style": style,
            "authority_effects": list(held), "requested_kinds": list(wanted),
            "requested_tags": request.to_dict(),
            "offered": offered, "withheld": withheld,
            "offered_bytes": sum(row["size_bytes"] for row in offered),
            "exposed_bytes": sum(row["size_bytes"] for row in offered
                                 if row["exposure"] == EXPOSURES[-1])}


@dataclass(frozen=True)
class HarnessIntelligenceDraft:
    """An item before its digest and size are measured from the body."""

    identity: str
    kind: str
    purpose: str
    source_layer: str
    source_ref: str
    license_name: str = ""
    declared_effects: tuple[str, ...] = ()
    styles: tuple[str, ...] = ()
    default_exposure: str = EXPOSURES[0]
    availability: str = AVAILABILITY[0]
    tags: TagSet = EMPTY_TAGS


def item_from_body(draft: HarnessIntelligenceDraft, body: str) -> HarnessIntelligenceItem:
    """Measure the body and return the item, so no caller invents a digest."""
    if not isinstance(draft, HarnessIntelligenceDraft):
        raise HarnessIntelligenceError("a typed draft is required before a body is measured")
    encoded = body.encode("utf-8")
    return HarnessIntelligenceItem(
        draft.identity, draft.kind, draft.purpose, hashlib.sha256(encoded).hexdigest(),
        draft.source_layer, draft.source_ref, len(encoded), draft.license_name,
        tuple(draft.declared_effects), tuple(draft.styles), draft.default_exposure,
        draft.availability, draft.tags)


def self_test() -> dict:
    """Items point rather than copy, an unaffordable effect is never offered, and bodies stay out."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except HarnessIntelligenceError:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    catalogue = HarnessIntelligenceCatalogue()
    parser = item_from_body(HarnessIntelligenceDraft(
        "capability.email_syntax", "reusable_code",
        "Check an electronic mail address against the declared syntax",
        "code_intelligence", "code.capability.email_syntax", "MIT"),
        "def check(value): return '@' in value\n")
    skill = item_from_body(HarnessIntelligenceDraft(
        "skill.clean_supplier_names", "skill",
        "When a supplier column has mixed case and suffixes, clean it",
        "context_intelligence", "ctx.skill.clean_supplier_names", "MIT",
        styles=("claude_code", "codex")),
        "# Clean supplier names\n\nUse the text conformance family.\n")
    writer = item_from_body(HarnessIntelligenceDraft(
        "tool.database_copy", "tool", "Copy a database to a new target with corrections",
        "code_intelligence", "code.capability.database_copy",
        declared_effects=("reads_fs", "writes_fs")),
        "{}")
    for item in (parser, skill, writer):
        catalogue.register(item)
    check("an_item_points_at_the_record_that_holds_its_body_and_carries_a_digest",
          parser.source_ref == "code.capability.email_syntax"
          and len(parser.digest) == DIGEST_LENGTH and parser.size_bytes > 0
          and catalogue.kinds_held() == ("reusable_code", "skill", "tool")
          and refuses(lambda: HarnessIntelligenceItem(
              "x", "reusable_code", "p", "0" * 64, "context_intelligence", "ref"))
          and refuses(lambda: HarnessIntelligenceItem(
              "x", "skill", "p", "short", "context_intelligence", "ref"))
          and refuses(lambda: HarnessIntelligenceItem(
              "x", "skill", "p", "0" * 64, "context_intelligence", ""))
          and refuses(lambda: HarnessIntelligenceItem(
              "x", "not_a_kind", "p", "0" * 64, "context_intelligence", "ref")),
          parser.digest[:12])
    pure = offer(catalogue, style="claude_code", authority_effects=())
    check("an_item_that_declares_an_effect_the_step_does_not_hold_is_never_offered",
          [row["identity"] for row in pure["offered"]]
          == ["capability.email_syntax", "skill.clean_supplier_names"]
          and [row["identity"] for row in pure["withheld"]] == ["tool.database_copy"]
          and "reads_fs" in pure["withheld"][0]["reason"],
          pure["withheld"][0]["reason"])
    writing = offer(catalogue, style="claude_code",
                    authority_effects=("reads_fs", "writes_fs"))
    other = offer(catalogue, style="opencode", authority_effects=("reads_fs", "writes_fs"))
    check("the_same_catalogue_offers_more_to_a_step_that_holds_more_and_filters_by_harness",
          len(writing["offered"]) == 3 and not writing["withheld"]
          and [row["identity"] for row in other["withheld"]] == ["skill.clean_supplier_names"]
          and other["withheld"][0]["reason"] == "another harness",
          str(len(writing["offered"])))
    check("a_reference_names_the_exposure_and_never_carries_the_body",
          all(row["body_included"] is False for row in writing["offered"])
          and all("body" not in row for row in writing["offered"])
          and all(row["exposure"] == "metadata_only" for row in writing["offered"])
          and writing["exposed_bytes"] == 0 and writing["offered_bytes"] > 0
          and offer(catalogue, authority_effects=("reads_fs", "writes_fs"),
                    exposure="full_instructions")["exposed_bytes"] > 0,
          str(writing["offered_bytes"]))
    check("reusable_code_cannot_claim_a_layer_that_does_not_hold_code",
          refuses(lambda: item_from_body(HarnessIntelligenceDraft(
              "x", "reusable_code", "p", "context_intelligence", "ref"), "b"))
          and refuses(lambda: item_from_body({"identity": "x"}, "b"))
          and refuses(lambda: offer(catalogue, authority_effects=("teleport",)))
          and refuses(lambda: offer(catalogue, kinds=("not_a_kind",)))
          and refuses(lambda: catalogue.register(object()))
          and refuses(lambda: catalogue.register(item_from_body(
              HarnessIntelligenceDraft("skill.clean_supplier_names", "skill", "p",
                                       "context_intelligence", "ref"),
              "different body"))))
    from .intelligence_tagging import TagSet as _TagSet
    tagged = item_from_body(HarnessIntelligenceDraft(
        "skill.nurse_intake_de", "skill", "Intake questions for a nurse, in German",
        "context_intelligence", "ctx.skill.nurse_intake_de", "MIT",
        tags=_TagSet({"role": ("nurse",), "language": ("de",),
                      "data_sensitivity": ("regulated",)})),
        "# Intake\n\nAsk in German.\n")
    catalogue.register(tagged)
    for_nurse = offer(catalogue, authority_effects=(),
                      tags=_TagSet({"role": ("nurse",), "language": ("de",)}))
    for_analyst = offer(catalogue, authority_effects=(),
                        tags=_TagSet({"role": ("data analyst",)}))
    check("an_item_filed_under_tags_is_offered_only_to_a_request_those_tags_satisfy",
          "skill.nurse_intake_de" in [row["identity"] for row in for_nurse["offered"]]
          and "skill.nurse_intake_de" in [row["identity"] for row in for_analyst["withheld"]]
          and {row["identity"]: row["reason"] for row in for_analyst["withheld"]}[
              "skill.nurse_intake_de"] == "filed under other tags"
          and for_nurse["requested_tags"]["role"] == ["nurse"]
          and for_nurse["offered"][0]["tags"]["record_type"] == "intelligence_tags/v1"
          and "skill.clean_supplier_names" in [
              row["identity"] for row in offer(
                  catalogue, style="claude_code", authority_effects=())["offered"]]
          and refuses(lambda: offer(catalogue, authority_effects=(), tags={"role": ("x",)}))
          and refuses(lambda: HarnessIntelligenceItem(
              "x", "skill", "p", "0" * 64, "context_intelligence", "ref", tags={"role": ()})),
          str([row["identity"] for row in for_nurse["offered"]]))
    kinds_only = offer(catalogue, authority_effects=("reads_fs", "writes_fs"),
                       kinds=("skill",))
    check("a_step_can_ask_for_one_kind_and_gets_only_that_kind",
          set(row["kind"] for row in kinds_only["offered"]) == {"skill"}
          and kinds_only["requested_kinds"] == ["skill"],
          str(len(kinds_only["offered"])))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "harness_intelligence_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
