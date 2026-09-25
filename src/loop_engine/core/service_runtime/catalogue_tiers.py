"""Library tiers of the catalogue: Verified and Community, and what an account and a request choose to receive.

The owner, September 24, 2026: "we need to have a continuously updating
database of millions of skills, tooks, code, functions, plugins, contracts,
rules, agents, agent support files, agent support code, etc that coding
harnesses can detect and freely use". The decision table of AGENTS.md records
the two tiers in its row "Library tiers":

```text
Library tier of an approved item   label       admission
├── verified                       Verified    independent reviewers of at least two model families
│                                              that did not produce it; every automated check passes
└── community                      Community   every automated check passes (licence allowlist,
                                               provenance, secret and safety scanners, its own
                                               tests where it has code) and one independent review
                                               by a family that did not produce it
```

The reviewed catalogue names the tier of each approval, and the tier travels
with the approval through the bundle, the item version record, the served view
and every answer: each served item carries the typed field `library_tier` and
the exact label `library_tier_label`. No retrieval count, score or model
confidence sets a tier, and a community item becomes verified only through the
full review.

The first catalogue does not meet the family rule, and the published meaning of
Verified says so. Its items were approved on September 21, 2026, before the
rule, by three reviewers that did not write them; the items were written with
Claude Code and the one reviewer whose model is recorded is a Claude model
(`examples/29_intelligence_service/starter-catalogue/reviews.json`). The release
30 live check on September 25, 2026 found the meaning claiming two families for
them. They keep the Verified label, with that sentence, until reviewers of two
other families approve them; no other family could review on that day.

What a request may be offered is narrowed in two places. An account setting
chooses which community items the account receives; its default is every
community item, labelled. A request can narrow further with a `library_tiers`
filter, for example to verified items only, but never widen what the account
receives. A reader of a record version that has no tier field is offered
verified items only.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..provisioning_server import (COMMUNITY_EXCLUDED, COMMUNITY_INCLUDED, COMMUNITY_ITEM_CHOICES, COMMUNITY_TIER,
                                   COMMUNITY_WITHOUT_RUNNABLE, LIBRARY_TIERS, TIER_LABELS, TIER_ORDER, VERIFIED_TIER)
from .records import ServiceRuntimeError

__all__ = ["COMMUNITY_EXCLUDED", "COMMUNITY_INCLUDED", "COMMUNITY_ITEM_CHOICES", "COMMUNITY_TIER",
           "COMMUNITY_WITHOUT_RUNNABLE", "DEFAULT_COMMUNITY_ITEMS", "LIBRARY_TIERS", "LibrarySettings", "TIER_LABELS",
           "TIER_MEANINGS", "TIER_ORDER", "VERIFIED_TIER", "narrowed", "tier_legend", "tier_of_review"]

LIBRARY_SETTINGS_RECORD_TYPE = "account_library_settings/v1"
LEGEND_RECORD_TYPE = "catalogue_library_tiers/v1"
TIER_MEANINGS = {
    VERIFIED_TIER: ("Approved by independent reviewers of at least two model families that did not produce it, "
                    "with every automated check passing. The first catalogue, approved on September 21, 2026 before "
                    "this rule, is the exception: its items were written with Claude models and approved by three "
                    "reviewers that did not write them, and those reviews do not show two other model families. They "
                    "are reviewed again by two other model families as soon as those reviewers are available."),
    COMMUNITY_TIER: ("Passed every automated check (licence allowlist, provenance, secret and safety scanners, and "
                     "its own tests where it has code) and one independent review by a model family that did not "
                     "produce it.")}
#: The owner's decision labels community items everywhere and lets a search
#: exclude them, so an account receives them by default.
DEFAULT_COMMUNITY_ITEMS = COMMUNITY_INCLUDED
COMMUNITY_ITEM_MEANINGS = {
    COMMUNITY_EXCLUDED: "Verified items only.",
    COMMUNITY_WITHOUT_RUNNABLE: "Verified items, and community items that hold no file a development tool may run.",
    COMMUNITY_INCLUDED: "Verified items and every community item, each labelled. This is the default."}


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def tier_of_review(value):
    """The library tier a reviewed catalogue row names; a row that names none is verified.

    A row without a tier is an approval of the first catalogue, September 21, 2026, which the published meaning of
    Verified names as its exception until two other model families have reviewed it."""
    if value is None:
        return VERIFIED_TIER
    if value not in LIBRARY_TIERS:
        _refuse("library_tier_invalid", f"a library tier is one of {LIBRARY_TIERS}")
    return value


@dataclass(frozen=True)
class LibrarySettings:
    """What one account chooses to receive from the library; a request can only narrow it."""

    community_items: str = DEFAULT_COMMUNITY_ITEMS
    record_type: str = LIBRARY_SETTINGS_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != LIBRARY_SETTINGS_RECORD_TYPE:
            _refuse("library_settings_unsupported", f"this release reads {LIBRARY_SETTINGS_RECORD_TYPE} only")
        if self.community_items not in COMMUNITY_ITEM_CHOICES:
            _refuse("library_settings_invalid", f"community items are one of {COMMUNITY_ITEM_CHOICES}")

    def to_dict(self):
        return {"record_type": self.record_type, "community_items": self.community_items}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != {"record_type", "community_items"}:
            _refuse("library_settings_invalid", "library settings name their record version and community items only")
        return cls(value["community_items"], value["record_type"])


DEFAULT_LIBRARY_SETTINGS = LibrarySettings()


def narrowed(settings, requested_tiers):
    """The community choice for one request: the account's setting, narrowed by the tiers the request names.

    `requested_tiers` of None means the request did not narrow. The filter is
    `["verified"]`, which excludes community items, or `["verified",
    "community"]`, which receives what the account's setting allows and never
    more. Verified items are always part of the answer.
    """
    if requested_tiers is None:
        return settings.community_items
    if isinstance(requested_tiers, str) or not isinstance(requested_tiers, (list, tuple)):
        _refuse("library_tiers_invalid", f"library tiers are a list of distinct values of {LIBRARY_TIERS}")
    tiers = tuple(requested_tiers)
    if (len(set(tiers)) != len(tiers) or any(tier not in LIBRARY_TIERS for tier in tiers)
            or VERIFIED_TIER not in tiers):
        _refuse("library_tiers_invalid", "the filter is [\"verified\"] or [\"verified\", \"community\"]")
    return settings.community_items if COMMUNITY_TIER in tiers else COMMUNITY_EXCLUDED


def tier_legend():
    """The published meaning of each tier and each community choice, for capabilities and search answers."""
    return {"record_type": LEGEND_RECORD_TYPE,
            "tiers": [{"library_tier": tier, "label": TIER_LABELS[tier], "meaning": TIER_MEANINGS[tier],
                       "rank": TIER_ORDER[tier]} for tier in LIBRARY_TIERS],
            "community_items": {"default": DEFAULT_COMMUNITY_ITEMS,
                                "choices": [{"value": choice, "meaning": COMMUNITY_ITEM_MEANINGS[choice]}
                                            for choice in COMMUNITY_ITEM_CHOICES]},
            "filter": "library_tiers: a list of verified and community; verified alone excludes community items"}
