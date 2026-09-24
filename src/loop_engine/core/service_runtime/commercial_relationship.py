"""The commercial relationship of one row of a public directory, kept apart from its editorial facts.

Kind: passive typed record with its strict reader. Every public directory the website publishes
(the directory of Model Context Protocol servers and agent APIs, and the directory of models and
endpoints) gives each row one `commercial_relationship` object with exactly the fields below. The
object says whether a link to the listed product earns Baltor anything (an affiliate or referral
commission, or a paid placement) or whether the product is Baltor's own service. Nothing here serves
a page, joins a programme or makes a link.

The labels follow the research record docs/research/AFFILIATE-ADVERTISING-AND-LISTING-INCOME-2026-09-24.md:
an affiliate or referral link is labelled "Paid link", a paid placement "Ad" in a band headed "Ads",
and Baltor's own service "Baltor's own service". Five rules hold for every directory that uses it:

1. Ranking, ordering, filtering, search and inclusion never read a commercial field. Each directory
   build has a check that changes every commercial field and requires the same rows in the same
   order, with a known-wrong mutant that reads the field and must be caught.
2. A paid link is shown only for an active relationship, with its visible label beside it, the plain
   address of the product beside it and `rel="sponsored noopener"`. It never replaces a row's own
   links. The page links a short disclosure section.
3. One visible sentence, PAID_LINK_NOTICE, sits directly above any list that shows an active paid link,
   and only then.
4. An ad sits in its own band headed "Ads", at most MAXIMUM_ADS in a page, never inside a ranked list.
5. Joining a programme is the owner's legal and payout step, and the disclosure wording waits for the
   owner's approval, so every row ships as `NONE` until the owner approves a programme.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

#: The version of this object. A directory manifest names it, so a reader refuses another shape.
SCHEMA = "directory_commercial_relationship/v1"
#: The exact fields of the object, in the order a record writes them.
FIELDS = ("kind", "program_name", "program_terms_address", "disclosure_label", "outbound_link",
          "canonical_address", "status", "reviewed_at")
NO_RELATIONSHIP = "none"
AFFILIATE = "affiliate"
REFERRAL = "referral"
SPONSORED = "sponsored"
OWNED = "owned"
KINDS = (NO_RELATIONSHIP, AFFILIATE, REFERRAL, SPONSORED, OWNED)
NOT_STARTED = "none"
PENDING_OWNER = "pending_owner"
ACTIVE = "active"
STATUSES = (NOT_STARTED, PENDING_OWNER, ACTIVE)
#: The visible label a commercial link carries beside it, for each kind.
DISCLOSURE_LABELS = {AFFILIATE: "Paid link", REFERRAL: "Paid link", SPONSORED: "Ad", OWNED: "Baltor's own service"}
#: The rel attribute of every paid link and ad, and of a link to Baltor's own service.
LINK_REL = "sponsored noopener"
OWNED_LINK_REL = "noopener"
#: The heading of the band that holds ads, and the most ads one page shows.
AD_BAND_HEADING = "Ads"
MAXIMUM_ADS = 3
#: The sentence directly above a list that shows an active paid link. A draft that waits for the owner's approval;
#: no page shows it until a paid link is active, and none is.
PAID_LINK_NOTICE = ("Links marked Paid link are ads: Baltor earns money when you sign up or buy through them. "
                    "They do not change which services we list or their order.")
#: The id of the disclosure section a directory page links to.
DISCLOSURE_SECTION_ID = "paid-links"
_SECURE_SCHEME = "https"
_REVIEWED = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z)?\Z")
#: An https address: the scheme, a dotted host name of letters, digits and hyphens, an optional port, and then
#: nothing, or a path, query or fragment. User information (a name or password before the host) is refused.
_SECURE_ADDRESS = re.compile(re.escape(_SECURE_SCHEME) + r"://(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
                             r"[A-Za-z]{2,63}(?::[0-9]{1,5})?(?:[/?#][^\s@]*)?\Z")


class CommercialRelationshipError(ValueError):
    """A commercial relationship record this reader refuses, with the reason."""


@dataclass(frozen=True)
class CommercialRelationship:
    """Whether a row's link earns anything, and under which programme. Never an input to ranking."""

    kind: str = NO_RELATIONSHIP
    program_name: str = ""
    program_terms_address: str = ""
    disclosure_label: str = ""
    outbound_link: str = ""
    canonical_address: str = ""
    status: str = NOT_STARTED
    reviewed_at: str = ""

    def __post_init__(self) -> None:
        _check(self)

    @property
    def shows_commercial_link(self) -> bool:
        """True only for an active affiliate or referral relationship: the one case a paid link shows."""
        return self.status == ACTIVE and self.kind in (AFFILIATE, REFERRAL)

    @property
    def is_sponsored_placement(self) -> bool:
        """True only for an active sponsored relationship, which is shown as an ad in its own band."""
        return self.status == ACTIVE and self.kind == SPONSORED

    @property
    def is_owned_service(self) -> bool:
        """True only for an active relationship that marks Baltor's own service."""
        return self.status == ACTIVE and self.kind == OWNED


def _secure_address(value: str) -> bool:
    return bool(_SECURE_ADDRESS.match(value))


def _check(item: CommercialRelationship) -> None:
    values = asdict(item)
    if any(not isinstance(values[name], str) or values[name] != values[name].strip() for name in FIELDS):
        raise CommercialRelationshipError("every field of a commercial relationship is a trimmed string")
    if item.kind not in KINDS or item.status not in STATUSES:
        raise CommercialRelationshipError(f"kind must be one of {KINDS} and status one of {STATUSES}")
    if item.kind == NO_RELATIONSHIP:
        if item.status != NOT_STARTED or any(values[name] for name in FIELDS[1:-2] + FIELDS[-1:]):
            raise CommercialRelationshipError("a row without a relationship has status none and no other field")
        return
    if item.status == NOT_STARTED:
        raise CommercialRelationshipError("a relationship other than none is pending the owner or active")
    if not item.program_name:
        raise CommercialRelationshipError("a relationship names its programme")
    for name in ("program_terms_address", "outbound_link", "canonical_address"):
        if not _secure_address(values[name]):
            raise CommercialRelationshipError(f"{name} must be an https address without user information")
    if item.disclosure_label != DISCLOSURE_LABELS[item.kind]:
        raise CommercialRelationshipError(f"a relationship of kind {item.kind} is labelled {DISCLOSURE_LABELS[item.kind]!r}")
    if item.kind == OWNED and item.outbound_link != item.canonical_address:
        raise CommercialRelationshipError("a link to Baltor's own service is its plain address, with nothing added")
    if item.reviewed_at and not _REVIEWED.match(item.reviewed_at):
        raise CommercialRelationshipError("reviewed_at is a date or a UTC time")
    if item.status == ACTIVE and not item.reviewed_at:
        raise CommercialRelationshipError("an active relationship records when it was reviewed")


#: The relationship every row ships with until the owner approves a programme.
NONE = CommercialRelationship()


def from_record(value) -> CommercialRelationship:
    """Read one commercial relationship object, refusing an unknown or a missing field."""
    if not isinstance(value, dict):
        raise CommercialRelationshipError("a commercial relationship is an object")
    missing, unknown = sorted(set(FIELDS) - set(value)), sorted(set(value) - set(FIELDS))
    if missing or unknown:
        raise CommercialRelationshipError(f"missing fields {missing} and unknown fields {unknown}")
    return CommercialRelationship(**{name: value[name] for name in FIELDS})


def to_record(relationship: CommercialRelationship) -> dict:
    """The object as a directory writes it, with the fields in their declared order."""
    values = asdict(relationship)
    return {name: values[name] for name in FIELDS}


def link_attributes(relationship: CommercialRelationship) -> "dict | None":
    """The href, rel, visible label and plain address of a row's paid link or own-service link, or None.

    An ad is not a row link: it is shown only in the band of ads, through is_sponsored_placement.
    """
    if relationship.shows_commercial_link:
        return {"href": relationship.outbound_link, "rel": LINK_REL, "label": relationship.disclosure_label,
                "plain_address": relationship.canonical_address}
    if relationship.is_owned_service:
        return {"href": relationship.canonical_address, "rel": OWNED_LINK_REL, "label": relationship.disclosure_label,
                "plain_address": relationship.canonical_address}
    return None


def shows_paid_link_notice(relationships) -> bool:
    """True exactly when at least one relationship of a list shows a paid link, so PAID_LINK_NOTICE sits above it."""
    return any(item.shows_commercial_link for item in relationships)


def invariance_variants(host: str) -> tuple:
    """Valid relationships that change every field, for the check that ordering never reads them.

    The caller names the host of the example addresses, for example a reserved example domain, so no
    real programme address is written here.
    """
    variants = [NONE]
    for kind in (AFFILIATE, REFERRAL, SPONSORED, OWNED):
        for status in (PENDING_OWNER, ACTIVE):
            base = f"{_SECURE_SCHEME}://{kind}.{host}"
            variants.append(CommercialRelationship(
                kind=kind, program_name=f"{kind} programme {status}", program_terms_address=f"{base}/terms/{status}",
                disclosure_label=DISCLOSURE_LABELS[kind],
                outbound_link=f"{base}/product" if kind == OWNED else f"{base}/go/{status}",
                canonical_address=f"{base}/product", status=status, reviewed_at="2026-09-24"))
    return tuple(variants)
