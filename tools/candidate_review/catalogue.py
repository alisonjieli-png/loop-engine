"""Read the starter catalogue into review requests that carry exact bytes and pinned provenance.

A review request holds the body bytes, the item's row from ``items.json``, every
cited source file (each checked against the digest the catalogue pinned for it),
the declared producer, the compiled criteria and the digest of the reviewer
instructions. Its digest names all of them, so a reviewer's verdict can be
bound to exactly what the reviewer was shown.

This module reads files only. It never writes, never calls a model and never
reaches the network.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from carry_catalogue_approvals import ITEMS_RECORD_TYPE, REVIEW_RECORD_TYPE

from .configuration import CompiledCriteria, Producer
from .records import REQUEST_RECORD, CandidateReviewError, digest, refuse, sha256_hex

ITEMS_FILE, REVIEW_FILE, BODY_SUFFIX = "items.json", "reviews.json", ".md"
#: The catalogue's population files and their record, as the catalogue's refresh tool names them.
SPECIFICATIONS_GLOB = "specifications-[0-9][0-9][0-9].json"
SPECIFICATIONS_RECORD_TYPE = "candidate_intelligence_specifications/v1"
NOT_REVIEWED = "not_reviewed"
SOURCE_SEPARATOR = "@"


@dataclass(frozen=True)
class CitedSource:
    """One cited file at the revision the catalogue pinned, with its measured digest."""

    path: str
    revision: str
    sha256: str
    text: str

    def to_dict(self) -> dict:
        return {"path": self.path, "revision": self.revision, "sha256": self.sha256}


@dataclass(frozen=True)
class CandidateReviewRequest:
    """The edge request: everything one reviewer is shown about one candidate, and nothing else."""

    identity: str
    body_path: str
    body: bytes
    item_json: str
    cited_sources: tuple
    producer: Producer
    criteria: CompiledCriteria
    instructions_sha256: str

    @property
    def item(self) -> dict:
        """A fresh copy of the item row, so nothing a caller does can change the request."""
        return json.loads(self.item_json)

    @property
    def grounding(self) -> str:
        """The kind of body the item declares in its provenance, or empty when it declares none."""
        provenance = self.item.get("provenance")
        value = provenance.get("grounding") if isinstance(provenance, dict) else None
        return value if isinstance(value, str) else ""

    @property
    def applicable_criteria(self) -> tuple:
        """The written criteria for this kind of body: the only ones a reviewer is given and may cite."""
        return self.criteria.applicable(self.grounding)

    @property
    def applicable_criteria_ids(self) -> frozenset:
        return frozenset(criterion.criterion_id for criterion in self.applicable_criteria)

    @property
    def body_sha256(self) -> str:
        return sha256_hex(self.body)

    @property
    def body_size_bytes(self) -> int:
        return len(self.body)

    @property
    def body_text(self) -> str:
        """The body as strict UTF-8 text. Bytes that are not UTF-8 are the format pre-check's refusal."""
        try:
            return self.body.decode("utf-8")
        except UnicodeDecodeError:
            raise CandidateReviewError("body_not_utf8", f"the body of {self.identity} is not UTF-8 text") from None

    @property
    def body_text_lenient(self) -> str:
        """The body with any byte that is not UTF-8 replaced, for the kinds that do not own the encoding."""
        return self.body.decode("utf-8", "replace")

    @property
    def request_sha256(self) -> str:
        return digest({"identity": self.identity, "body_sha256": self.body_sha256, "item": self.item,
                       "cited_sources": [source.to_dict() for source in self.cited_sources],
                       "producer": self.producer.to_dict(), "criteria_sha256": self.criteria.sha256,
                       "instructions_sha256": self.instructions_sha256})

    def replaced(self, *, body: "bytes | None" = None, item: "dict | None" = None,
                 identity: str = "") -> "CandidateReviewRequest":
        """A new request with other bytes, another item row or another identity; its digests follow."""
        return replace(self, body=self.body if body is None else body,
                       item_json=self.item_json if item is None else _item_json(item),
                       identity=identity or self.identity)

    def to_record(self) -> dict:
        return {"record_type": REQUEST_RECORD, "identity": self.identity, "body_path": self.body_path,
                "body_sha256": self.body_sha256, "body_size_bytes": self.body_size_bytes,
                "cited_sources": [source.to_dict() for source in self.cited_sources],
                "producer": self.producer.to_dict(), "criteria_sha256": self.criteria.sha256,
                "instructions_sha256": self.instructions_sha256, "request_sha256": self.request_sha256}


def _item_json(item: dict) -> str:
    return json.dumps(item, sort_keys=True, ensure_ascii=False)


def _json_file(path: Path, label: str) -> dict:
    if path.is_symlink() or not path.is_file():
        refuse("catalogue_file_missing", f"{label} must be a regular file")
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        refuse("catalogue_file_unreadable", f"{label} is not UTF-8 JSON")


def _confined(root: Path, relative: str, label: str) -> Path:
    if type(relative) is not str or not relative:
        refuse("unsafe_path", f"{label} names no path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or any(part.startswith(".") for part in pure.parts):
        refuse("unsafe_path", f"{label} {relative!r} must stay inside its folder")
    path = root
    for part in pure.parts:
        path = path / part
        if path.is_symlink():
            refuse("unsafe_path", f"{label} {relative!r} passes through a link")
    if not path.is_file() or root not in path.resolve().parents:
        refuse("unsafe_path", f"{label} {relative!r} is not a regular file inside its folder")
    return path


class StarterCatalogue:
    """The candidate items, their bodies and the committed review record, read and never written."""

    def __init__(self, folder: Path, repository: Path, items: dict, reviews: dict, specifications: dict):
        self.folder, self.repository = folder, repository
        if items.get("record_type") != ITEMS_RECORD_TYPE:
            refuse("catalogue_record_unsupported", f"this panel reads {ITEMS_RECORD_TYPE} only")
        if reviews.get("record_type") != REVIEW_RECORD_TYPE:
            refuse("review_record_unsupported", f"this panel reads {REVIEW_RECORD_TYPE} only")
        rows = items.get("items")
        if type(rows) is not list:
            refuse("catalogue_record_unsupported", "the item file lists no items")
        self._rows = {}
        for row in rows:
            identity = row["reference"]["identity"]
            if identity in self._rows:
                refuse("catalogue_record_unsupported", f"{identity} appears twice")
            self._rows[identity] = _item_json(row)
        self._order = tuple(row["reference"]["identity"] for row in rows)
        self._sources = specifications
        self.source_revision = items.get("source_revision")
        self.source_digests = MappingProxyType(dict(items.get("source_digests") or {}))
        self._outcomes = {row["identity"]: row["outcome"] for row in reviews.get("rows") or ()}
        self._review_order = tuple(row["identity"] for row in reviews.get("rows") or ())
        self.review_record_sha256 = sha256_hex((folder / REVIEW_FILE).read_bytes())
        self._bodies = {}

    @classmethod
    def load(cls, folder: Path, repository: Path) -> "StarterCatalogue":
        folder, repository = Path(folder).resolve(), Path(repository).resolve()
        sources = {}
        names = sorted(path.name for path in folder.glob(SPECIFICATIONS_GLOB))
        if not names:
            refuse("catalogue_file_missing", "the catalogue holds no specification population file")
        for name in names:
            record = _json_file(folder / name, name)
            if record.get("record_type") != SPECIFICATIONS_RECORD_TYPE:
                refuse("catalogue_record_unsupported", f"{name} is not {SPECIFICATIONS_RECORD_TYPE}")
            for row in record.get("specifications") or ():
                if row.get("id") in sources or type(row.get("sources")) is not list or not row["sources"]:
                    refuse("catalogue_record_unsupported", f"{name} names an item twice or without sources")
                sources[row["id"]] = tuple(row["sources"])
        return cls(folder, repository, _json_file(folder / ITEMS_FILE, ITEMS_FILE),
                   _json_file(folder / REVIEW_FILE, REVIEW_FILE), sources)

    def identities(self) -> tuple:
        return self._order

    def item(self, identity: str) -> dict:
        if identity not in self._rows:
            refuse("unknown_item_identity", f"{identity} is not in the catalogue")
        return json.loads(self._rows[identity])

    def outcome(self, identity: str) -> str:
        return self._outcomes.get(identity, "")

    def not_reviewed(self) -> tuple:
        return tuple(identity for identity in self._review_order if self._outcomes[identity] == NOT_REVIEWED)

    def body_bytes(self, identity: str) -> bytes:
        if identity not in self._bodies:
            self._bodies[identity] = _confined(self.folder, self.item(identity)["body_path"], "body path").read_bytes()
        return self._bodies[identity]

    def population_bodies(self) -> MappingProxyType:
        """Every body in the catalogue, for the duplicate pre-check."""
        return MappingProxyType({identity: self.body_bytes(identity) for identity in self._order})

    def cited_sources(self, identity: str) -> tuple:
        """Every file the item cites, each at the pinned revision and checked against its pinned digest."""
        reference = self.item(identity)["reference"]
        first, separator, revision = str(reference.get("source_ref") or "").rpartition(SOURCE_SEPARATOR)
        if not separator or revision != self.source_revision:
            refuse("source_revision_mismatch",
                   f"{identity} cites a source at another revision than the catalogue is anchored to")
        paths = self._sources.get(identity)
        if not paths or paths[0] != first:
            refuse("source_list_inconsistent", f"the specification of {identity} does not start with its cited source")
        cited = []
        for path in paths:
            data = _confined(self.repository, path, "cited source").read_bytes()
            measured = hashlib.sha256(data).hexdigest()
            if self.source_digests.get(path) != measured:
                refuse("source_digest_mismatch", f"a cited source of {identity} is not the pinned bytes")
            try:
                cited.append(CitedSource(path, revision, measured, data.decode("utf-8")))
            except UnicodeDecodeError:
                refuse("source_not_text", f"a cited source of {identity} is not UTF-8 text")
        return tuple(cited)

    def request(self, identity: str, producer: Producer, criteria: CompiledCriteria,
                instructions_sha256: str) -> CandidateReviewRequest:
        item = self.item(identity)
        return CandidateReviewRequest(identity, item["body_path"], self.body_bytes(identity), _item_json(item),
                                      self.cited_sources(identity), producer, criteria, instructions_sha256)


def select_population(identities, *, count: int, seed: str) -> tuple:
    """A declared, reproducible sample: order by the digest of the seed and the identity, take the first."""
    if type(count) is not int or count < 1:
        refuse("invalid_population", "a population needs a positive count")
    if type(seed) is not str or not seed.strip():
        refuse("invalid_population", "a population needs a written seed")
    ordered = sorted(identities, key=lambda identity: hashlib.sha256(f"{seed}:{identity}".encode()).hexdigest())
    return tuple(ordered[:count])
