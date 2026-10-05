"""Public, body-free file metadata within the existing Public Good service owner.

``collection(view, snapshot, ...)`` consumes a CURRENT ``PublicGoodSnapshot``
for that immutable ``CatalogueView``. The HTTP owner must recheck snapshot
freshness before serialization/delivery, as for the package projection. This
pure function reads no clock, store, resolver, body or source locator and caches
nothing. It is neither a serving/admission authority nor another Loop runtime.

Only explicit ``useful_paths`` make a digest a useful-file result. A result
retains ALL its eligible package/path/licence associations, including supporting
placements. All filters must match the SAME useful placement; matching one
parent's goal and another parent's MIME never satisfies a combined filter.
Counts and facets describe the whole eligible inventory before filtering.
``matches`` and pagination count distinct useful digests after filtering.

At most 50 file rows are returned. Associations are never silently truncated;
the transport must enforce its encoded-response byte limit. Metadata is not
anonymous download, installation or execution authority. ``body_digest`` is the
parent digest for an authenticated exact file request; ``file_sha256`` verifies
the returned file. Existing package API semantics are unchanged.
"""
from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Literal, TypedDict

from ..harness_intelligence import HarnessIntelligenceCatalogue
from ..provisioning_server import ProvisioningItemBinding
from .catalogue_packages import CataloguePackage, _MEDIA_TYPE
from .catalogue_serving import CatalogueView
from .public_good import PublicGoodGrant, PublicGoodLimits, PublicGoodSnapshot
from .records import ServiceRuntimeError

COLLECTION_RECORD_TYPE = "public_good_file_collection/v1"
MAXIMUM_QUERY_CHARACTERS, MAXIMUM_PACKAGE_FILTER_CHARACTERS = 200, 200
MAXIMUM_PAGE, MAXIMUM_PAGE_SIZE = 10_000, 50
PROTOCOL_TOOL = "public_good_files"
_GOALS = tuple(range(1, 18))
_GOAL_FILTERS = ("", "related", *(str(number) for number in _GOALS))
_INITIATIVE = re.compile(r"[a-z][a-z0-9-]{0,63}")


def query_schema() -> dict:
    """The protocol adapter's bounded metadata query, using the web projection."""
    return {"type": "object", "additionalProperties": False, "properties": {
        "query": {"type": "string", "maxLength": MAXIMUM_QUERY_CHARACTERS},
        "goal": {"type": "string", "enum": list(_GOAL_FILTERS)},
        "media_type": {"type": "string", "pattern": "^(?:" + _MEDIA_TYPE.pattern + ")?$"},
        "initiative": {"type": "string", "maxLength": 64},
        "package": {"type": "string", "maxLength": MAXIMUM_PACKAGE_FILTER_CHARACTERS},
        "page": {"type": "integer", "minimum": 1, "maximum": MAXIMUM_PAGE},
        "page_size": {"type": "integer", "minimum": 1, "maximum": MAXIMUM_PAGE_SIZE}}}


class FilePlacement(TypedDict):
    identity: str
    item_version: str
    body_digest: str
    path: str
    media_type: str
    placement_role: str
    package_display_name: str
    package_purpose: str
    public_benefit: str
    licence: str
    sdg_goals: list[int]
    initiatives: list[str]
    requires_package_context: Literal[True]
    is_useful: bool
    matches_filters: bool


class FileMetadata(TypedDict):
    file_sha256: str
    size_bytes: int
    media_type: str | None
    media_types: list[str]
    placements: list[FilePlacement]


class GoalFacet(TypedDict):
    id: int
    files: int


class TextFacet(TypedDict):
    id: str
    files: int


class FileCollection(TypedDict):
    record_type: Literal["public_good_file_collection/v1"]
    authentication_required: Literal[True]
    subscription_required: Literal[False]
    policy_version: str
    eligible_fingerprint: str
    catalogue_release: str
    catalogue_state_revision: int
    packages: int
    packages_without_file_manifest: int
    distinct_files: int
    distinct_useful_files: int
    distinct_supporting_files: int
    file_placements: int
    useful_file_placements: int
    supporting_file_placements: int
    useful_file_count_basis: str
    supporting_file_count_basis: str
    facets_scope: str
    matches: int
    page: int
    page_size: int
    has_next: bool
    items: list[FileMetadata]
    goals: list[GoalFacet]
    related_files: int
    media_types: list[TextFacet]
    initiatives: list[TextFacet]
    limits_description: str


def _plain(value, maximum):
    return isinstance(value, str) and len(value) <= maximum and all(character.isprintable() for character in value)


def _filters(query, goal, media_type, initiative, package, page, page_size):
    if (not _plain(query, MAXIMUM_QUERY_CHARACTERS)
            or not isinstance(goal, str) or goal not in _GOAL_FILTERS
            or not isinstance(media_type, str) or media_type and _MEDIA_TYPE.fullmatch(media_type) is None
            or not isinstance(initiative, str) or initiative and _INITIATIVE.fullmatch(initiative) is None
            or not _plain(package, MAXIMUM_PACKAGE_FILTER_CHARACTERS)
            or type(page) is not int or not 1 <= page <= MAXIMUM_PAGE
            or type(page_size) is not int or not 1 <= page_size <= MAXIMUM_PAGE_SIZE):
        raise ServiceRuntimeError("invalid_public_good_query")


def _inputs(view, snapshot):
    # A view's parts are dictionaries in memory or read-only mappings over a disk index (catalogue_disk_view);
    # either answers the passive lookups below without a resolver, body or store call.
    if (not isinstance(view, CatalogueView) or not isinstance(view.catalogue, HarnessIntelligenceCatalogue)
            or not isinstance(view.catalogue.items, Mapping) or not isinstance(view.packages, Mapping)
            or not isinstance(view.item_versions, Mapping) or not isinstance(view.withdrawn, (set, frozenset))
            or not isinstance(snapshot, PublicGoodSnapshot) or not isinstance(snapshot.grants, tuple)
            or not isinstance(snapshot.limits, PublicGoodLimits) or not isinstance(snapshot.version, str)
            or any(not isinstance(grant, PublicGoodGrant) for grant in snapshot.grants)
            or len({grant.binding.identity for grant in snapshot.grants}) != len(snapshot.grants)):
        raise ServiceRuntimeError("public_good_file_projection_invalid")


def _inventory(view, snapshot):
    """Intersect passive current facts only; never call a resolver/body/store."""
    groups, sizes, packages, missing, useful_placements = {}, {}, 0, 0, 0
    for grant in snapshot.grants:
        item = view.catalogue.items.get(grant.binding.identity)
        if (not grant.active or item is None or view.item_versions.get(item.identity) != grant.item_version
                or ProvisioningItemBinding.from_item(item) != grant.binding
                or (item.identity, item.digest) in view.withdrawn):
            continue
        package = view.packages.get(item.identity)
        if package is not None and not isinstance(package, CataloguePackage):
            raise ServiceRuntimeError("public_good_file_projection_invalid")
        if package is not None and package.served_digest != grant.binding.body_digest:
            continue
        packages += 1
        if package is None:
            missing += 1
            continue
        useful = set(grant.useful_paths)
        if not useful <= {entry.path for entry in package.files}:
            raise ServiceRuntimeError("public_good_file_projection_invalid")
        title = grant.display_name or re.sub(r"[_-]+", " ", item.identity).strip()
        parent = {"identity": item.identity, "item_version": grant.item_version, "body_digest": item.digest,
            "package_display_name": title[:120], "package_purpose": item.purpose[:400],
            "public_benefit": grant.public_benefit_reason[:600], "licence": item.license_name,
            "sdg_goals": list(grant.sdg_goals), "initiatives": list(grant.initiatives),
            "requires_package_context": True}
        for entry in package.files:
            if entry.digest in sizes and sizes[entry.digest] != entry.size_bytes:
                raise ServiceRuntimeError("package_file_size_conflict")
            sizes[entry.digest] = entry.size_bytes
            selected = entry.path in useful
            useful_placements += selected
            groups.setdefault(entry.digest, []).append({**parent, "path": entry.path, "media_type": entry.media_type,
                "placement_role": entry.role, "is_useful": selected, "matches_filters": False})
    return groups, sizes, packages, missing, useful_placements


def _matches(placement, words, goal, media_type, initiative, package):
    if not placement["is_useful"]:
        return False
    if (goal == "related" and placement["sdg_goals"]
            or goal not in ("", "related") and int(goal) not in placement["sdg_goals"]
            or media_type and media_type != placement["media_type"]
            or initiative and initiative not in placement["initiatives"]
            or package and package != placement["identity"]):
        return False
    if not words:
        return True
    haystack = " ".join((placement["path"], placement["package_display_name"], placement["package_purpose"],
                         placement["public_benefit"], *placement["initiatives"])).casefold()
    return all(word in haystack for word in words)


def _placement_order(placement):
    return (not placement["matches_filters"], not placement["is_useful"], placement["package_display_name"].casefold(),
            placement["identity"], placement["path"])


def collection(view: CatalogueView, snapshot: PublicGoodSnapshot, *, query: str = "", goal: str = "",
               media_type: str = "", initiative: str = "", package: str = "", page: int = 1,
               page_size: int = 20) -> FileCollection:
    """Return public_good_file_collection/v1; keyword filters are exact except query.

    Query is a case-folded AND of whitespace-separated words over a useful
    placement's path and parent descriptions. Media/initiative/package filters
    are literal equality. ``related`` means no explicit SDG association.
    ``distinct_supporting_files`` excludes digests useful anywhere; supporting
    PLACEMENTS include supporting occurrences of those useful digests. Goal,
    media and initiative facet counts overlap and must not be summed.
    """
    _filters(query, goal, media_type, initiative, package, page, page_size)
    _inputs(view, snapshot)
    groups, sizes, packages, missing, useful_placements = _inventory(view, snapshot)
    words = tuple(dict.fromkeys(query.casefold().split()))
    goals, media, initiatives, related, useful_digests, results = {number: set() for number in _GOALS}, {}, {}, set(), set(), []
    for digest, placements in groups.items():
        for placement in placements:
            placement["matches_filters"] = _matches(placement, words, goal, media_type, initiative, package)
            if not placement["is_useful"]:
                continue
            useful_digests.add(digest)
            for number in placement["sdg_goals"]:
                goals[number].add(digest)
            if not placement["sdg_goals"]:
                related.add(digest)
            media.setdefault(placement["media_type"], set()).add(digest)
            for name in placement["initiatives"]:
                initiatives.setdefault(name, set()).add(digest)
        if not any(placement["matches_filters"] for placement in placements):
            continue
        placements.sort(key=_placement_order)
        types = sorted({placement["media_type"] for placement in placements})
        results.append({"file_sha256": digest, "size_bytes": sizes[digest],
            "media_type": types[0] if len(types) == 1 else None, "media_types": types, "placements": placements})
    results.sort(key=lambda row: (_placement_order(row["placements"][0]), row["file_sha256"]))
    placements_count = sum(len(placements) for placements in groups.values())
    start, limits = (page - 1) * page_size, snapshot.limits
    return {"record_type": COLLECTION_RECORD_TYPE, "authentication_required": True, "subscription_required": False,
        "policy_version": snapshot.version, "eligible_fingerprint": snapshot.fingerprint,
        "catalogue_release": view.release_id, "catalogue_state_revision": view.state_revision,
        "packages": packages, "packages_without_file_manifest": missing, "distinct_files": len(groups),
        "distinct_useful_files": len(useful_digests), "distinct_supporting_files": len(groups.keys() - useful_digests),
        "file_placements": placements_count, "useful_file_placements": useful_placements,
        "supporting_file_placements": placements_count - useful_placements,
        "useful_file_count_basis": "explicit_reviewed_paths_only",
        "supporting_file_count_basis": "distinct_digests_never_useful_in_this_inventory",
        "facets_scope": "all_distinct_useful_files_before_filters", "matches": len(results),
        "page": page, "page_size": page_size, "has_next": start + page_size < len(results), "items": results[start:start + page_size],
        "goals": [{"id": number, "files": len(goals[number])} for number in _GOALS], "related_files": len(related),
        "media_types": [{"id": value, "files": len(media[value])} for value in sorted(media)],
        "initiatives": [{"id": value, "files": len(initiatives[value])} for value in sorted(initiatives)],
        "limits_description": f"Per account: up to {limits.requests_per_window} requests and {limits.bytes_per_window:,} reserved response bytes per {limits.window_seconds:,} seconds. Shared service limits also apply. Failed attempts can consume delivery allowance; paid usage is not increased."}
