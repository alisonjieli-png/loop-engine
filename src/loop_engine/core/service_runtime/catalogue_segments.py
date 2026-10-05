"""Segmented catalogue releases: content-addressed segments, release version 2 and bundle version 2.

A version 1 release names every item identity and item version in one record,
and a version 1 bundle carries every item's line, so every publish uploads,
validates and verifies the whole library. A version 2 release is an ordered
list of content-addressed segments. A segment is a bounded, sorted run of
`(identity, item version)` pairs with its own digest, and the release digest
binds the ordered segment digests, so a publish uploads only the segments,
item versions and bodies the store does not hold, and a withdrawal or a change
is a new segment that replaces one old one.

```text
Catalogue release, version 2
├── catalogue_segment/v1          {"record_type", "items": [[identity, item version], ...]}
│   ├── identities sorted and unique, 1 to MAXIMUM_SEGMENT_ITEMS pairs
│   └── digest: SHA-256 of the canonical document, stored once under that digest
├── catalogue_segmentation/v1     where one segment ends, decided by the content alone
│   ├── cut after an identity whose boundary hash is 0 modulo target_items
│   └── cut after maximum_items = 4 x target_items pairs when no boundary came
├── catalogue_release/v2          schema digest, segmentation, segments [[digest, first identity, count]],
│                                 item count, content digest, based_on, bounded changes and notes
└── catalogue_release_bundle/v2   bundle.json, release-segments.jsonl, and any subset of
                                  segments/, items/ and blobs/ by digest; the store supplies the rest
```

The segmentation is a function of the sorted membership only, the leaf level
of a probabilistic B-tree (Noms and Dolt) or a Merkle search tree: the same
content always gives the same segments and the same release digest, a changed
item version changes one segment, and an added or removed identity changes at
most the segments around it. The content digest of a version 2 release is the
version 1 content digest of the same membership, computed as a stream, so a
version 1 and a version 2 release of one library serve one content digest.

Version negotiation. A publisher asks the service which formats it reads
(`catalogue_formats`, the `catalogue-formats` operator command) and sends the
first one both sides support; a service that predates this module has no such
command, and the publisher sends version 1. Every reader refuses a record
version it does not list before any write. The first version 2 publish raises
the catalogue state marker to SEGMENTED_STATE_VERSION, so an image that cannot
read a version 2 release refuses to start against the store rather than serve
a store it cannot read.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import stat

from .catalogue_bundle import (ITEM_VERSION_RECORD_TYPES, MAXIMUM_BUNDLE_ITEMS, MAXIMUM_HEADER_BYTES,
                               MAXIMUM_ITEM_LINE_BYTES, MAXIMUM_RELEASE_NOTES_CHARACTERS, canonical_bytes, item_line,
                               note, strict_json, validate_item)
from .catalogue_body_flush import ExactFlushVolumeBodyStore
from .catalogue_packages import VolumeBodyStore, exact_digest, sha256_hex
from .catalogue_schema import CatalogueAttributeSchema
from .records import ServiceRuntimeError

SEGMENT_RECORD_TYPE = "catalogue_segment/v1"
SEGMENTATION_RULE = "catalogue_segmentation/v1"
RELEASE_V2_RECORD_TYPE = "catalogue_release/v2"
SEGMENTED_BUNDLE_RECORD_TYPE = "catalogue_release_bundle/v2"
FORMATS_RECORD_TYPE = "catalogue_release_formats/v1"
SEGMENT_KIND = "service_catalogue_segment"
#: Written by the first publish of a version 2 release and never lowered afterwards.
SEGMENTED_STATE_VERSION = 3
#: The targets a segmentation may name: powers of two, so a boundary is a run of zero bits.
SEGMENT_TARGETS = tuple(2 ** power for power in range(4, 13))
DEFAULT_SEGMENT_TARGET = 256
MAXIMUM_SEGMENT_ITEMS = 4 * SEGMENT_TARGETS[-1]
#: One release record names at most this many segments; 16.7 million items at the default target. A larger
#: library raises the target, or uses the two-level segment index the scale design describes.
MAXIMUM_RELEASE_SEGMENTS = 65_536
MAXIMUM_IDENTITY_CHARACTERS = 1_000
#: A segment document is read whole; this bounds one file of a bundle and one record of the store.
MAXIMUM_SEGMENT_BYTES = MAXIMUM_SEGMENT_ITEMS * (MAXIMUM_IDENTITY_CHARACTERS + 80)
#: A version 2 release keeps at most this many change rows of each kind with their notes, and always the counts.
MAXIMUM_CHANGE_ROWS = 2_000
BOUNDARY_PREFIX = b"catalogue-segment-boundary/v1\x00"
HEADER_FILE, SEGMENT_LIST_FILE = "bundle.json", "release-segments.jsonl"
SEGMENTS_FOLDER, ITEMS_FOLDER, BLOBS_FOLDER = "segments", "items", "blobs"
MAXIMUM_SEGMENT_LIST_LINE_BYTES = MAXIMUM_IDENTITY_CHARACTERS + 128


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


@dataclass(frozen=True)
class Segmentation:
    """Where one segment ends: decided by each identity alone, so the same content always gives the same segments."""

    target_items: int = DEFAULT_SEGMENT_TARGET
    rule: str = SEGMENTATION_RULE

    def __post_init__(self):
        if self.rule != SEGMENTATION_RULE:
            _refuse("catalogue_segmentation_unsupported", f"this release reads {SEGMENTATION_RULE} only")
        if type(self.target_items) is not int or self.target_items not in SEGMENT_TARGETS:
            _refuse("catalogue_segmentation_unsupported", f"a segment target is one of {SEGMENT_TARGETS}")

    @property
    def maximum_items(self):
        return 4 * self.target_items

    def boundary(self, identity):
        """True when a segment ends after this identity, unless the maximum ended it earlier."""
        value = int.from_bytes(hashlib.sha256(BOUNDARY_PREFIX + identity.encode("utf-8")).digest()[:8], "big")
        return value % self.target_items == 0

    def split(self, entries):
        """Yield the canonical segments of sorted, unique `(identity, version)` pairs, each a tuple of pairs."""
        current, maximum = [], self.maximum_items
        for entry in entries:
            current.append(entry)
            if len(current) >= maximum or self.boundary(entry[0]):
                yield tuple(current)
                current = []
        if current:
            yield tuple(current)

    def require_canonical(self, entries, *, last):
        """Refuse a segment whose cuts differ from the ones `split` makes; the last segment may end anywhere."""
        maximum = self.maximum_items
        if not 1 <= len(entries) <= maximum:
            _refuse("catalogue_segment_not_canonical", "a segment holds one to maximum_items pairs")
        for position, (identity, _version) in enumerate(entries[:-1], 1):
            if position >= maximum or self.boundary(identity):
                _refuse("catalogue_segment_not_canonical", "a segment continues past one of its own cut points")
        if not last and len(entries) < maximum and not self.boundary(entries[-1][0]):
            _refuse("catalogue_segment_not_canonical", "a segment ends where the segmentation does not cut")

    def to_dict(self):
        return {"rule": self.rule, "target_items": self.target_items, "maximum_items": self.maximum_items}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != {"rule", "target_items", "maximum_items"}:
            _refuse("catalogue_segmentation_unsupported", "a segmentation names its rule, target and maximum only")
        segmentation = cls(value["target_items"], value["rule"])
        if value["maximum_items"] != segmentation.maximum_items:
            _refuse("catalogue_segmentation_unsupported", "the maximum is four times the target")
        return segmentation


def segment_document(entries):
    return {"record_type": SEGMENT_RECORD_TYPE, "items": [[identity, version] for identity, version in entries]}


def segment_digest(document):
    return sha256_hex(canonical_bytes(document))


def segment_entries(document, expected_digest=None):
    """Read one segment document strictly and return its pairs; refuse any other shape or digest."""
    if (not isinstance(document, dict) or set(document) != {"record_type", "items"}
            or document["record_type"] != SEGMENT_RECORD_TYPE):
        _refuse("catalogue_segment_invalid", f"a segment is one {SEGMENT_RECORD_TYPE} record and nothing else")
    items = document["items"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAXIMUM_SEGMENT_ITEMS:
        _refuse("catalogue_segment_invalid", "a segment holds a bounded nonempty list of pairs")
    previous = None
    for pair in items:
        if (not isinstance(pair, list) or len(pair) != 2 or not isinstance(pair[0], str) or not pair[0]
                or len(pair[0]) > MAXIMUM_IDENTITY_CHARACTERS):
            _refuse("catalogue_segment_invalid", "a segment pair is an identity and an item version")
        exact_digest(pair[1], "catalogue_segment_invalid")
        if previous is not None and pair[0] <= previous:
            _refuse("catalogue_segment_invalid", "segment identities are sorted and unique")
        previous = pair[0]
    if expected_digest is not None:
        exact_digest(expected_digest, "catalogue_segment_invalid")
        if segment_digest(document) != expected_digest:
            _refuse("catalogue_segment_digest_mismatch", "a segment differs from its digest")
    return tuple((pair[0], pair[1]) for pair in items)


@dataclass(frozen=True)
class SegmentRef:
    """One segment as a release names it: its digest, its first identity and its number of pairs."""

    digest: str
    first: str
    count: int

    def to_list(self):
        return [self.digest, self.first, self.count]

    @classmethod
    def from_list(cls, value, code="catalogue_release_digest_mismatch"):
        if (not isinstance(value, list) or len(value) != 3 or not isinstance(value[1], str) or not value[1]
                or len(value[1]) > MAXIMUM_IDENTITY_CHARACTERS or type(value[2]) is not int
                or not 1 <= value[2] <= MAXIMUM_SEGMENT_ITEMS):
            _refuse(code, "a segment reference is a digest, a first identity and a count")
        exact_digest(value[0], code)
        return cls(value[0], value[1], value[2])


def require_segment_list(refs, segmentation, code):
    """Refuse a segment list whose first identities are not strictly increasing or whose counts are out of bounds."""
    if not isinstance(refs, (list, tuple)) or not 1 <= len(refs) <= MAXIMUM_RELEASE_SEGMENTS:
        _refuse(code, f"a release names one to {MAXIMUM_RELEASE_SEGMENTS} segments")
    previous = None
    for ref in refs:
        if ref.count > segmentation.maximum_items:
            _refuse(code, "a segment reference counts more pairs than the segmentation allows")
        if previous is not None and ref.first <= previous:
            _refuse(code, "segments are listed in identity order and never overlap")
        previous = ref.first
    return tuple(refs)


class ContentDigest:
    """The version 1 content digest of a membership, fed one pair at a time.

    `content_digest(schema, items)` hashes `{"items":[[identity,version],...],"schema_digest":...}` in canonical
    JSON. Keys sort `items` before `schema_digest`, so the bytes can be produced as a stream, and the result is
    the same digest without holding the membership.
    """

    def __init__(self, schema_digest):
        self._schema = schema_digest
        self._hash = hashlib.sha256(b'{"items":[')
        self._first = True
        self.count = 0

    def add(self, identity, version):
        if not self._first:
            self._hash.update(b",")
        self._first = False
        self._hash.update(canonical_bytes([identity, version]))
        self.count += 1

    def hexdigest(self):
        final = self._hash.copy()
        final.update(b'],"schema_digest":' + canonical_bytes(self._schema) + b"}")
        return final.hexdigest()


def membership_segments(entries, segmentation):
    """The canonical segments of a sorted membership, as (reference, document) pairs."""
    for segment in segmentation.split(entries):
        document = segment_document(segment)
        yield SegmentRef(segment_digest(document), segment[0][0], len(segment)), document


@dataclass(frozen=True)
class SegmentedRelease:
    """A verified version 2 release header. Its pairs are read segment by segment, never held whole."""

    release_id: str
    document: dict
    schema: CatalogueAttributeSchema
    segmentation: Segmentation
    segments: tuple

    @property
    def item_count(self):
        return self.document["items"]

    @property
    def content_digest(self):
        return self.document["content_digest"]

    def entries(self, read_segment):
        """Yield every pair in identity order, verifying each segment, the cuts, the count and the content digest.

        `read_segment(digest)` returns the stored segment document or None. The content digest is checked when the
        last pair has been yielded, so a reader that stops early has verified only the segments it read.
        """
        stream, previous = ContentDigest(self.document["schema_digest"]), None
        for position, ref in enumerate(self.segments):
            pairs = verified_segment(ref, read_segment(ref.digest), self.segmentation,
                                     last=position == len(self.segments) - 1)
            if previous is not None and pairs[0][0] <= previous:
                _refuse("catalogue_release_digest_mismatch", "segments overlap or are out of identity order")
            previous = pairs[-1][0]
            for identity, version in pairs:
                stream.add(identity, version)
                yield identity, version
        if stream.count != self.item_count or stream.hexdigest() != self.content_digest:
            _refuse("catalogue_release_digest_mismatch", "the segments differ from the release's count or content")

    def segment_for(self, identity):
        """The reference of the one segment that would hold `identity`, or None when it sorts before them all."""
        position = bisect_right([ref.first for ref in self.segments], identity) - 1
        return self.segments[position] if position >= 0 else None

    def version_of(self, identity, read_segment):
        """The item version this release lists for `identity`, or None; reads one segment."""
        return self.find(identity, read_segment)

    def find(self, identity, read_segment):
        """The item version this release lists for `identity`, or None; reads one segment."""
        ref = self.segment_for(identity)
        if ref is None:
            return None
        position = self.segments.index(ref)
        pairs = verified_segment(ref, read_segment(ref.digest), self.segmentation,
                                 last=position == len(self.segments) - 1)
        return dict(pairs).get(identity)


def verified_segment(ref, document, segmentation, *, last):
    """The pairs of one segment, checked against the reference the release names and the segmentation rule."""
    if document is None:
        _refuse("catalogue_release_incomplete", "the release names a segment the store does not hold")
    pairs = segment_entries(document, ref.digest)
    if pairs[0][0] != ref.first or len(pairs) != ref.count:
        _refuse("catalogue_release_digest_mismatch", "a segment differs from the reference the release names")
    segmentation.require_canonical(pairs, last=last)
    return pairs


def release_v2_header(document, release_id, schema):
    """Check the shape of a version 2 release document whose digest and schema were already checked."""
    fields = {"record_type", "schema_digest", "segmentation", "segments", "items", "content_digest", "based_on",
              "changes", "notes", "release_id", "published_at"}
    if set(document) != fields or document["record_type"] != RELEASE_V2_RECORD_TYPE:
        _refuse("catalogue_release_digest_mismatch", f"a {RELEASE_V2_RECORD_TYPE} record has exactly its own fields")
    segmentation = Segmentation.from_dict(document["segmentation"])
    raw = document["segments"]
    if not isinstance(raw, list):
        _refuse("catalogue_release_digest_mismatch", "a release lists its segments")
    refs = require_segment_list([SegmentRef.from_list(value) for value in raw], segmentation,
                                "catalogue_release_digest_mismatch")
    if type(document["items"]) is not int or document["items"] != sum(ref.count for ref in refs):
        _refuse("catalogue_release_digest_mismatch", "the item count is the sum of the segment counts")
    exact_digest(document["content_digest"], "catalogue_release_digest_mismatch")
    return SegmentedRelease(release_id, document, schema, segmentation, refs)


def bounded_changes(added, changed, withdrawn):
    """The release's own change record: every count, and at most MAXIMUM_CHANGE_ROWS rows of each kind."""
    rows = {"added": added, "changed": changed, "withdrawn": withdrawn}
    return {**{key: value[:MAXIMUM_CHANGE_ROWS] for key, value in rows.items()},
            "counts": {key: len(value) for key, value in rows.items()},
            "complete": all(len(value) <= MAXIMUM_CHANGE_ROWS for value in rows.values())}


def catalogue_formats():
    """What this image reads and writes, for a publisher to negotiate before it uploads anything."""
    from .catalogue_bundle import BUNDLE_RECORD_TYPE
    from .catalogue_releases import RELEASE_RECORD_TYPE, SUPPORTED_CATALOGUE_STATE_VERSIONS
    return {"record_type": FORMATS_RECORD_TYPE,
            "bundle_record_types": [BUNDLE_RECORD_TYPE, SEGMENTED_BUNDLE_RECORD_TYPE],
            "release_record_types": [RELEASE_RECORD_TYPE, RELEASE_V2_RECORD_TYPE],
            "segment_record_types": [SEGMENT_RECORD_TYPE],
            "segmentation_rules": [{"rule": SEGMENTATION_RULE, "targets": list(SEGMENT_TARGETS)}],
            "item_version_record_types": list(ITEM_VERSION_RECORD_TYPES),
            "catalogue_state_versions": list(SUPPORTED_CATALOGUE_STATE_VERSIONS)}


def negotiate_bundle_format(offered, preference=(SEGMENTED_BUNDLE_RECORD_TYPE, "catalogue_release_bundle/v1")):
    """The first bundle version in the publisher's preference that the service offers, or a typed refusal.

    `offered` is the service's `catalogue_formats()` record, or None when the service has no such command, which
    means it predates version 2 and reads version 1 only.
    """
    if offered is None:
        readable = ("catalogue_release_bundle/v1",)
    elif not isinstance(offered, dict) or offered.get("record_type") != FORMATS_RECORD_TYPE or not isinstance(
            offered.get("bundle_record_types"), list):
        _refuse("catalogue_format_unsupported", "the service stated its formats in a record this publisher cannot read")
    else:
        readable = tuple(value for value in offered["bundle_record_types"] if isinstance(value, str))
    for choice in preference:
        if choice in readable:
            return choice
    _refuse("catalogue_format_unsupported", "the service reads no bundle version this publisher writes")


# ---------------------------------------------------------------------------
# Bundle version 2
# ---------------------------------------------------------------------------

def _regular_size(path, code, limit):
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        _refuse("bundle_path_unsafe", "every bundle file is a regular file, never a symbolic link")
    if info.st_size > limit:
        _refuse(code, "a bundle file is larger than its bound")
    return info.st_size


def _object_path(root, folder, digest):
    return Path(root) / folder / "sha256" / digest[:2] / digest


@dataclass(frozen=True)
class SegmentedBundle:
    """A validated version 2 bundle header and segment list. Carried objects are read and checked on demand."""

    folder: Path
    digest: str
    schema: CatalogueAttributeSchema
    notes: str
    change_notes: dict
    withdrawals: tuple
    segmentation: Segmentation
    segments: tuple
    release_items: int
    content_digest: str
    license_policy: object = field(repr=False, compare=False)
    family_policy: object = field(repr=False, compare=False)

    record_type = SEGMENTED_BUNDLE_RECORD_TYPE

    def carried_segment(self, digest):
        """The segment document this bundle carries under `digest`, checked against it, or None."""
        exact_digest(digest, "catalogue_segment_invalid")
        path = _object_path(self.folder, SEGMENTS_FOLDER, digest)
        if _regular_size(path, "catalogue_segment_invalid", MAXIMUM_SEGMENT_BYTES) is None:
            return None
        document = strict_json(path.read_bytes(), "catalogue_segment_invalid")
        segment_entries(document, digest)
        return document

    def carried_item(self, version):
        """The validated bundle item this bundle carries for one item version, or None.

        The line passes every rule a version 1 line passes, and the version its document hashes to must be the
        name it is carried under.
        """
        exact_digest(version, "bundle_item_invalid")
        path = _object_path(self.folder, ITEMS_FOLDER, version)
        if _regular_size(path, "bundle_item_line_invalid", MAXIMUM_ITEM_LINE_BYTES + 1) is None:
            return None
        raw = path.read_bytes()
        if not raw.endswith(b"\n"):
            _refuse("bundle_item_line_invalid", "each item line is bounded and ends with one newline")
        entry = validate_item(strict_json(raw[:-1], "bundle_item_invalid"), self.schema,
                              license_policy=self.license_policy, family_policy=self.family_policy)
        if entry.version != version:
            _refuse("bundle_item_digest_mismatch", "a carried item line hashes to another item version")
        return entry

    def blobs(self):
        """The bundle's own blob folder, read-only, or an empty store when it carries no bodies."""
        folder = self.folder / BLOBS_FOLDER
        return VolumeBodyStore(str(folder)) if folder.is_dir() else None


def read_segmented_bundle(folder, *, license_policy, family_policy):
    """Read and validate one version 2 bundle header and segment list without writing anything."""
    root = Path(folder) if isinstance(folder, (str, Path)) else None
    if root is None or not root.is_absolute() or root.resolve() != root or not root.is_dir():
        _refuse("bundle_folder_invalid", "a bundle is an existing absolute folder without symbolic links")
    if _regular_size(root / HEADER_FILE, "bundle_header_too_large", MAXIMUM_HEADER_BYTES) is None:
        _refuse("bundle_header_missing", "a bundle file is missing")
    raw_header = (root / HEADER_FILE).read_bytes()
    header = strict_json(raw_header, "bundle_header_invalid")
    fields = {"record_type", "schema", "notes", "change_notes", "withdrawals", "segmentation", "release_items",
              "content_digest", "segment_list"}
    if set(header) != fields or header["record_type"] != SEGMENTED_BUNDLE_RECORD_TYPE:
        _refuse("bundle_header_invalid", f"this reader reads {SEGMENTED_BUNDLE_RECORD_TYPE} with its exact fields")
    schema = CatalogueAttributeSchema.from_dict(header["schema"])
    notes = note(header["notes"], MAXIMUM_RELEASE_NOTES_CHARACTERS)
    segmentation = Segmentation.from_dict(header["segmentation"])
    count = header["release_items"]
    if type(count) is not int or count < 1:
        _refuse("bundle_header_invalid", "a release holds at least one item")
    exact_digest(header["content_digest"], "bundle_header_invalid")
    change_notes = header["change_notes"]
    if not isinstance(change_notes, dict) or len(change_notes) > MAXIMUM_BUNDLE_ITEMS:
        _refuse("bundle_header_invalid", "change notes map an item identity to a short note")
    change_notes = {str(key): note(value) for key, value in change_notes.items()}
    withdrawals = header["withdrawals"]
    if not isinstance(withdrawals, list) or len(withdrawals) > MAXIMUM_BUNDLE_ITEMS or any(
            not isinstance(row, dict) or set(row) != {"identity", "note"} or not isinstance(row["identity"], str)
            or not row["identity"] for row in withdrawals):
        _refuse("bundle_header_invalid", "a withdrawal names an item identity and a note")
    withdrawals = tuple(sorted(({"identity": row["identity"], "note": note(row["note"])} for row in withdrawals),
                               key=lambda row: row["identity"]))
    if len({row["identity"] for row in withdrawals}) != len(withdrawals):
        _refuse("bundle_header_invalid", "an identity is withdrawn once in one bundle")
    listing = header["segment_list"]
    if not isinstance(listing, dict) or set(listing) != {"count", "bytes", "digest"}:
        _refuse("bundle_header_invalid", "the header states the segment list's count, bytes and digest")
    lines, size = listing["count"], listing["bytes"]
    if (type(lines) is not int or not 1 <= lines <= MAXIMUM_RELEASE_SEGMENTS or type(size) is not int
            or not lines <= size <= lines * (MAXIMUM_SEGMENT_LIST_LINE_BYTES + 1)):
        _refuse("bundle_header_invalid", "the segment list is bounded")
    exact_digest(listing["digest"], "bundle_header_invalid")
    held = _regular_size(root / SEGMENT_LIST_FILE, "bundle_segments_changed", size)
    if held != size:
        _refuse("bundle_segments_changed", "the segment list holds another number of bytes than the header states")
    checksum, refs = hashlib.sha256(), []
    with open(root / SEGMENT_LIST_FILE, "rb") as stream:
        while True:
            line = stream.readline(MAXIMUM_SEGMENT_LIST_LINE_BYTES + 2)
            if not line:
                break
            checksum.update(line)
            if len(line) > MAXIMUM_SEGMENT_LIST_LINE_BYTES + 1 or not line.endswith(b"\n") or len(refs) >= lines:
                _refuse("bundle_segments_changed", "each segment list line is bounded and ends with one newline")
            try:
                value = json.loads(line[:-1])
            except ValueError:
                _refuse("bundle_segments_changed", "a segment list line is one JSON array")
            ref = SegmentRef.from_list(value, "bundle_segments_changed")
            if canonical_bytes(ref.to_list()) + b"\n" != line:
                _refuse("bundle_segments_changed", "a segment list line is written in canonical form")
            refs.append(ref)
    if len(refs) != lines or checksum.hexdigest() != listing["digest"]:
        _refuse("bundle_segments_changed", "the segment list differs from the count and digest the header states")
    refs = require_segment_list(refs, segmentation, "bundle_segments_changed")
    if sum(ref.count for ref in refs) != count:
        _refuse("bundle_segments_changed", "the segment counts differ from the release's item count")
    return SegmentedBundle(root, sha256_hex(raw_header), schema, notes, change_notes, withdrawals, segmentation,
                           refs, count, header["content_digest"], license_policy, family_policy)


def bundle_record_type(folder):
    """The record version a bundle header names, read with the header's bound, without validating the rest."""
    root = Path(folder)
    if _regular_size(root / HEADER_FILE, "bundle_header_too_large", MAXIMUM_HEADER_BYTES) is None:
        _refuse("bundle_header_missing", "a bundle file is missing")
    header = strict_json((root / HEADER_FILE).read_bytes(), "bundle_header_invalid")
    value = header.get("record_type")
    if not isinstance(value, str):
        _refuse("bundle_header_invalid", "a bundle header names its record version")
    return value


def read_any_bundle(folder, *, license_policy, family_policy, verify_blobs=False):
    """Read a version 1 or version 2 bundle by the version its header names; refuse any other before any write."""
    from .catalogue_bundle import BUNDLE_RECORD_TYPE, read_bundle
    record_type = bundle_record_type(folder)
    if record_type == BUNDLE_RECORD_TYPE:
        return read_bundle(Path(folder), license_policy=license_policy, family_policy=family_policy,
                           verify_blobs=verify_blobs)
    if record_type == SEGMENTED_BUNDLE_RECORD_TYPE:
        return read_segmented_bundle(folder, license_policy=license_policy, family_policy=family_policy)
    _refuse("bundle_header_invalid", "this release reads catalogue_release_bundle/v1 and /v2 only")


@dataclass(frozen=True)
class Carried:
    """Which segments and item lines a version 2 bundle carries; None carries every one."""

    segments: "frozenset | None" = None
    items: "frozenset | None" = None

    def carries_segment(self, digest):
        return self.segments is None or digest in self.segments

    def carries_item(self, version):
        return self.items is None or version in self.items


def write_segmented_bundle(folder, *, schema, items, payloads=(), segmentation=None, notes="", change_notes=None,
                           withdrawals=(), carry=Carried()):
    """Write one version 2 bundle and return its header digest.

    `items` is every `(bundle line, item version)` pair of the release, the full membership; the header and the
    segment list describe all of it. `carry` names the segment digests and item versions the bundle carries, so a
    publisher carries only what the service lacks. `payloads` are the body bytes carried. The folder must not exist
    yet.
    """
    root = Path(folder)
    if not root.is_absolute() or root.exists():
        _refuse("bundle_folder_invalid", "a new bundle is written into a new absolute folder")
    segmentation = segmentation or Segmentation()
    rows = sorted(items, key=lambda pair: pair[0]["reference"]["identity"])
    identities = [line["reference"]["identity"] for line, _version in rows]
    if len(set(identities)) != len(identities) or not rows:
        _refuse("duplicate_item_identity", "a release names each identity once and at least one")
    rendered = {version: item_line(line) for line, version in rows}
    stream = ContentDigest(schema.digest)
    for identity, (_line, version) in zip(identities, rows):
        stream.add(identity, version)
    segments = list(membership_segments(((identity, version) for identity, (_line, version) in zip(identities, rows)),
                                        segmentation))
    root.mkdir(parents=True)
    for ref, document in segments:
        if carry.carries_segment(ref.digest):
            path = _object_path(root, SEGMENTS_FOLDER, ref.digest)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(canonical_bytes(document))
    for version, line in rendered.items():
        if carry.carries_item(version):
            path = _object_path(root, ITEMS_FOLDER, version)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(line)
    payloads = tuple(payloads)
    if payloads:
        (root / BLOBS_FOLDER).mkdir()
        blobs = ExactFlushVolumeBodyStore(str((root / BLOBS_FOLDER).resolve()), writes_authorized=True)
        for payload in payloads:
            blobs.put(payload, durable=False)
        blobs.sync()
    listing = b"".join(canonical_bytes(ref.to_list()) + b"\n" for ref, _document in segments)
    (root / SEGMENT_LIST_FILE).write_bytes(listing)
    header = {"record_type": SEGMENTED_BUNDLE_RECORD_TYPE, "schema": schema.to_dict(), "notes": notes,
              "change_notes": dict(change_notes or {}), "withdrawals": list(withdrawals),
              "segmentation": segmentation.to_dict(), "release_items": len(rows),
              "content_digest": stream.hexdigest(),
              "segment_list": {"count": len(segments), "bytes": len(listing), "digest": sha256_hex(listing)}}
    encoded = json.dumps(header, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    (root / HEADER_FILE).write_bytes(encoded)
    return sha256_hex(encoded)




def segment_reader(binding, store):
    """`read_segment(digest)` over the stored segment records of one open store."""
    def read(digest):
        row = binding.read(store, SEGMENT_KIND, digest)
        return row["payload"] if row is not None else None
    return read
