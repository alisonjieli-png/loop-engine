"""Duplicates across the batch and every existing corpus, and the restricted-copy rule.

One upstream file listed by three websites, forked into ten repositories or
vendored into a collection is one record. Items are joined into groups by
four signals, strongest first:

```text
Duplicate signals
├── git_blob: the same git object identity, so the same bytes, before anything is read
├── exact_bytes and normalized_text: the digest of the comparison text as words, lower case
└── near_text: word shingles at or above the declared similarity, through the library
    ingestion component's near-duplicate engines (datasketch MinHash LSH, or the built-in one)
```

The comparison text of a Markdown file is its body without frontmatter, so a
renamed or re-described copy still matches. Each group is then decided:

```text
One group
├── holds a restricted item (text that may not be copied, from this batch or the September 23 runs)
│   └── every copied member from another owner is refused as copy_of_restricted_source; the same
│       owner may license its own work under a second licence, so its permissive copy stands
├── holds an item of the served catalogue, the candidate folders under artifacts, the overnight
│   batch or an earlier import round
│   └── every batch member is a duplicate of it and is not added
├── holds a staged row of the September 23 ingestion runs
│   └── the batch package is kept as the complete new version of that row, which it supersedes
└── holds batch members only
    └── one is kept by source order, then stars, then name; the others are merged into it,
        their provenance travelling in the kept record
```

Nothing is dropped without a `licensed_import_duplicate/v1` link that names
the kept item, the merged item, the signal and the corpus.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from loop_engine.core.library_ingestion import engines as ingestion_engines
from loop_engine.core.library_ingestion.duplicates import normalized, shingles
from loop_engine.core.library_ingestion.provenance import OUTLINE_ONLY, REFUSED
from loop_engine.core.library_ingestion.record_rules import bytes_digest
from loop_engine.core.library_ingestion.selection import select_engines

from .packaging import comparison_text
from .records import duplicate_link

DEFAULT_THRESHOLD = 0.85
BATCH, SERVED, ARTIFACTS, OVERNIGHT, LS1, IMPORT_STORE = (
    "batch", "served_catalogue", "artifacts_candidates", "overnight_batch", "ls1_staged", "import_store")
#: Which existing corpus wins a group, strongest first; LS1 rows are superseded, not kept.
_CORPUS_PRIORITY = (IMPORT_STORE, SERVED, ARTIFACTS, OVERNIGHT)
HARNESS_NAMES = ("SKILL.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md", "plugin.json", "hooks.json", ".mcp.json")
HARNESS_SUFFIXES = (".mdc", ".instructions.md", ".prompt.md", ".agent.md", ".chatmode.md")
FOLDER_MARKERS = ("packages", "bodies", "candidates")
_TEXT_SUFFIXES = (".md", ".mdc", ".json", ".toml", ".yaml", ".yml", ".txt", ".py", ".sh", ".js", ".ts")
MAXIMUM_CORPUS_FILE_BYTES = 512 * 1024


@dataclass(frozen=True)
class Subject:
    """One item compared for duplicates: where it lives, how it ranks and what it says."""

    key: str
    corpus: str
    ref: str
    order: tuple  # (int, int, str, str) for every subject, so any two orders compare
    text: str
    blob: "str | None" = None
    restricted: bool = False
    owner: "str | None" = None


@dataclass
class Resolution:
    kept: list = field(default_factory=list)
    links: list = field(default_factory=list)
    restricted_copies: dict = field(default_factory=dict)
    supersedes: dict = field(default_factory=dict)
    merged_into: dict = field(default_factory=dict)


def near_engine(settings: "dict | None" = None):
    """The first eligible engine of the near-duplicate slot, with the slot's recorded decision."""
    slot = ingestion_engines.NEAR_DUPLICATE_SLOT
    decision, chosen = select_engines(slot, ingestion_engines.FACTORIES[slot.slot_id], dict(settings or {}))
    return decision, chosen[0].from_settings({}, {})


class LazyShingles:
    """Shingle sets made one at a time as an engine iterates, so a round's texts never all hold theirs at once.

    Both near-duplicate engines read their documents only through `items()`,
    turning each shingle set into a signature before the next is made. Texts
    with no words are left out, as they were when the sets were built eagerly.
    """

    def __init__(self, texts: dict) -> None:
        self._texts = {key: text for key, text in texts.items() if normalized(text)}

    def __len__(self) -> int:
        return len(self._texts)

    def __iter__(self):
        return iter(self._texts)

    def keys(self):
        return self._texts.keys()

    def items(self):
        for key, text in self._texts.items():
            yield key, shingles(text)

    def __getitem__(self, key):
        return shingles(self._texts[key])


class DuplicateIndex:
    """Every subject of one resolution, grouped by the four signals and decided group by group."""

    def __init__(self, engine, threshold: float = DEFAULT_THRESHOLD) -> None:
        self.engine, self.threshold = engine, threshold
        self.subjects: dict = {}

    def add(self, subject: Subject) -> None:
        if subject.key in self.subjects:
            raise ValueError(f"subject {subject.key} is added twice")
        self.subjects[subject.key] = subject

    def resolve(self) -> Resolution:
        keys = sorted(self.subjects, key=lambda key: (self.subjects[key].corpus != BATCH, self.subjects[key].order))
        parent = {key: key for key in keys}
        signal = {}

        def root(key):
            while parent[key] != key:
                parent[key] = parent[parent[key]]
                key = parent[key]
            return key

        def join(left, right, match, similarity):
            first, second = root(left), root(right)
            if first != second:
                parent[second] = first
            for key in (left, right):
                signal.setdefault(key, (match, similarity))

        by_blob, by_text = {}, {}
        for key in keys:
            subject = self.subjects[key]
            if subject.blob:
                if subject.blob in by_blob:
                    join(by_blob[subject.blob], key, "git_blob", 1.0)
                else:
                    by_blob[subject.blob] = key
            digest = bytes_digest(normalized(subject.text).encode("utf-8"))
            if normalized(subject.text):
                if digest in by_text:
                    join(by_text[digest], key, "normalized_text", 1.0)
                else:
                    by_text[digest] = key
        documents = LazyShingles({key: self.subjects[key].text for key in keys})
        if len(documents) > 1:
            for left, right, estimate in self.engine.pairs(documents, self.threshold):
                join(left, right, "near_text", estimate)
        groups: dict = {}
        for key in keys:
            groups.setdefault(root(key), []).append(key)
        result = Resolution()
        for members in groups.values():
            self._decide(members, signal, result)
        result.kept.sort(key=lambda key: self.subjects[key].order)
        return result

    def _decide(self, members, signal, result: Resolution) -> None:
        subjects = [self.subjects[key] for key in members]
        batch = sorted((subject for subject in subjects if subject.corpus == BATCH and not subject.restricted),
                       key=lambda subject: subject.order)
        if not batch:
            return
        restricted = [subject for subject in subjects if subject.restricted]
        existing = sorted((subject for subject in subjects if subject.corpus in _CORPUS_PRIORITY),
                          key=lambda subject: (_CORPUS_PRIORITY.index(subject.corpus), subject.order))
        staged = [subject for subject in subjects if subject.corpus == LS1 and not subject.restricted]

        def link(kept, merged):
            match, similarity = signal.get(merged.key, ("normalized_text", 1.0))
            return duplicate_link(kept.ref, {"ref": merged.ref, "corpus": merged.corpus}, match, similarity,
                                  kept.corpus)

        if restricted:
            refused = []
            for subject in batch:
                other = [row for row in restricted if row.owner is None or row.owner != subject.owner]
                if other:
                    result.restricted_copies[subject.key] = other[0].ref
                    result.links.append(link(other[0], subject))
                    refused.append(subject)
            batch = [subject for subject in batch if subject not in refused]
            if not batch:
                return
        if existing:
            for subject in batch:
                result.merged_into[subject.key] = existing[0].ref
                result.links.append(link(existing[0], subject))
            return
        kept, others = batch[0], batch[1:]
        result.kept.append(kept.key)
        for subject in others:
            result.merged_into[subject.key] = kept.ref
            result.links.append(link(kept, subject))
        if staged:
            result.supersedes[kept.key] = sorted(subject.ref for subject in staged)


def owner_of(repository: str) -> "str | None":
    """The lowercase owner of owner/name, or None when there is none."""
    owner = str(repository or "").partition("/")[0].lower()
    return owner or None


def _readable_text(path: Path) -> "str | None":
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAXIMUM_CORPUS_FILE_BYTES:
            return None
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _is_harness_like(path: Path) -> bool:
    name = path.name
    return (name in HARNESS_NAMES or name.lower() == "skill.md" or name.endswith(HARNESS_SUFFIXES)
            or (any(part in FOLDER_MARKERS for part in path.parts) and name.endswith(_TEXT_SUFFIXES)))


def folder_subjects(corpus: str, roots, *, every_text_file: bool = False) -> list:
    """Subjects from folders on this machine, read only; the same bytes under two roots count once."""
    found, seen = [], set()
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not (every_text_file and path.suffix in _TEXT_SUFFIXES) and not _is_harness_like(path):
                continue
            text = _readable_text(path)
            if text is None:
                continue
            digest = bytes_digest(text.encode("utf-8"))
            if digest in seen:
                continue
            seen.add(digest)
            relative = f"{root.parent.name}/{root.name}/{path.relative_to(root).as_posix()}"
            found.append(Subject(f"{corpus}:{relative}", corpus, relative, (1, 0, relative, ""),
                                 comparison_text(path.name, text.encode("utf-8"))))
    return found


def ls1_subjects(run_folder: Path) -> list:
    """The staged rows of a September 23 run, and its outline-only and refused texts as restricted."""
    run_folder = Path(run_folder)
    found = []
    database = run_folder / "candidates.db"
    if database.is_file():
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            for record_id, payload in connection.execute("SELECT record_id, payload FROM records ORDER BY record_id"):
                text = (json.loads(payload) or {}).get("text") or ""
                if text:
                    found.append(Subject(f"{LS1}:{record_id}", LS1, record_id, (2, 0, record_id, ""),
                                         comparison_text("SKILL.md", text.encode("utf-8"))))
        finally:
            connection.close()
    restricted_digests = {}
    for name in ("outlines.jsonl",):
        path = run_folder / name
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                provenance = json.loads(line).get("provenance") or {}
                if provenance.get("source_digest"):
                    restricted_digests[provenance["source_digest"]] = (provenance.get("path", ""),
                                                                       provenance.get("repository", ""))
    for batch in sorted((run_folder / "batches").glob("*.json")) if (run_folder / "batches").is_dir() else ():
        for candidate in json.loads(batch.read_text(encoding="utf-8")).get("candidates", ()):
            provenance = candidate.get("provenance") or {}
            decision = ((provenance.get("licence_evidence") or {}).get("decision"))
            if decision in (OUTLINE_ONLY, REFUSED) and provenance.get("source_digest"):
                restricted_digests[provenance["source_digest"]] = (provenance.get("path", ""),
                                                                   provenance.get("repository", ""))
    for digest, (path, repository) in sorted(restricted_digests.items()):
        stored = run_folder / "quarantine" / digest[:2] / digest
        text = _readable_text(stored)
        if text is not None:
            found.append(Subject(f"{LS1}:restricted:{digest}", LS1, f"restricted:{repository}/{path}",
                                 (0, 0, digest, ""), comparison_text(path or "SKILL.md", text.encode("utf-8")),
                                 restricted=True, owner=owner_of(repository)))
    return found
