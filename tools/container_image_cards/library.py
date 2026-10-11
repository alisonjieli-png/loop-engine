"""Read a Docker Official Images library definition file: the repository's tag families and their build facts.

```text
library/<name> of docker-library/official-images (bashbrew's RFC 2822 style manifest)
├── a first paragraph without Tags: the file's defaults (Maintainers, GitRepo, GitFetch, GitCommit, Architectures,
│   Directory, File, Builder, Constraints)
├── every paragraph with Tags: one entry, which is one tag family built from one build context per architecture
│   ├── Tags: the entry's own tags, all pushed as one image index; SharedTags: tags several entries share, whose
│   │   index joins those entries (hello-world's latest joins its Linux and Windows entries)
│   ├── Architectures: bashbrew names (amd64, arm64v8, arm32v7, i386, windows-amd64, ...)
│   ├── GitRepo, GitFetch, GitCommit, Directory, File, Builder, Constraints
│   └── <architecture>-GitRepo, -GitFetch, -GitCommit, -Directory, -File: one architecture's override
└── a line starting with # is a comment; an indented line continues the field above it
```

The family identity is what stays the same while the family's images are rebuilt and its versions move on: the
entry's own build context (its fetch reference, directory, Dockerfile name, constraints and per-architecture
directories, never a commit), or, when two entries of one file share a build context, the shortest of the entry's
own tags other than latest. Nothing here reads the network.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

#: The fields of a library file, as bashbrew names them.
(MAINTAINERS, TAGS, SHARED_TAGS, ARCHITECTURES, GIT_REPOSITORY, GIT_FETCH, GIT_COMMIT, DIRECTORY, FILE, BUILDER,
 CONSTRAINTS) = FIELDS = ("Maintainers", "Tags", "SharedTags", "Architectures", "GitRepo", "GitFetch", "GitCommit",
                          "Directory", "File", "Builder", "Constraints")
#: The fields one architecture may override with an "<architecture>-<field>" key.
ARCHITECTURE_FIELDS = (GIT_REPOSITORY, GIT_FETCH, GIT_COMMIT, DIRECTORY, FILE)
#: The fields that hold comma-separated lists.
LIST_FIELDS = (MAINTAINERS, TAGS, SHARED_TAGS, ARCHITECTURES, CONSTRAINTS)
#: bashbrew's defaults for a field neither the entry nor the file's first paragraph sets.
DEFAULTS = {GIT_FETCH: "refs/heads/master", DIRECTORY: ".", FILE: "Dockerfile", ARCHITECTURES: ("amd64",)}
COMMENT, CONTINUATION, LIST_SEPARATOR, KEY_SEPARATOR = "#", (" ", "\t"), ",", ":"
#: The tag every repository moves to its newest family; it never names a family of its own.
LATEST_TAG = "latest"
#: How a family identity says where it came from.
CONTEXT_PREFIX, TAG_PREFIX = "context:", "tag:"
#: A tag of the distribution specification (the reference grammar's tag component).
TAG_PATTERN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}")
#: A repository name of the library namespace.
REPOSITORY_PATTERN = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*")
#: A full git commit identity.
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")


class LibraryError(ValueError):
    """A library file or entry that cannot be read, with a stable reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


@dataclass(frozen=True)
class LibraryEntry:
    """One tag family of one repository: its tags, architectures and build context, with the file's defaults."""

    repository: str
    position: int  # 1-based, among the file's entries
    tags: tuple
    shared_tags: tuple
    architectures: tuple
    git_repository: str
    git_fetch: str
    git_commit: str
    directory: str
    file: str
    builder: str
    constraints: tuple
    #: {architecture: {field: value}} of the "<architecture>-<field>" keys.
    overrides: dict = field(default_factory=dict)
    #: The fields the entry's own paragraph sets (not the file's defaults), for the family identity.
    declared: dict = field(default_factory=dict)
    family: str = ""

    @property
    def resolved_tag(self) -> str:
        """The tag the card resolves: the entry's first own tag, the most specific one in docker-library's order."""
        return self.tags[0]

    def source(self) -> dict:
        """The entry's build context as the card records it."""
        return {"git_repository": self.git_repository, "git_fetch": self.git_fetch, "git_commit": self.git_commit,
                "directory": self.directory, "file": self.file, "builder": self.builder,
                "constraints": list(self.constraints),
                "architecture_overrides": {architecture: dict(sorted(values.items()))
                                           for architecture, values in sorted(self.overrides.items())}}


def paragraphs(text: str) -> list:
    """[{field: value}] of every paragraph, comments dropped and continuation lines joined to their field."""
    found, current, last = [], {}, None
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith(COMMENT):
            continue
        if not line.strip():
            if current:
                found.append(current)
            current, last = {}, None
            continue
        if line.startswith(CONTINUATION):
            if last is None:
                raise LibraryError("library_entry_invalid", f"a continuation line with no field: {line.strip()[:80]}")
            current[last] = f"{current[last]} {line.strip()}".strip()
            continue
        key, separator, value = line.partition(KEY_SEPARATOR)
        if not separator or not key.strip() or key != key.strip():
            raise LibraryError("library_entry_invalid", f"not a field line: {line[:80]}")
        if key in current:
            raise LibraryError("library_entry_invalid", f"the field {key} is set twice in one paragraph")
        current[key] = value.strip()
        last = key
    if current:
        found.append(current)
    return found


def _list(value: str) -> tuple:
    return tuple(part.strip() for part in value.split(LIST_SEPARATOR) if part.strip())


def _split_key(key: str) -> tuple:
    """(architecture or None, field) of a key: GitCommit is (None, GitCommit), amd64-GitCommit is (amd64, GitCommit),
    windows-amd64-Directory is (windows-amd64, Directory)."""
    for name in ARCHITECTURE_FIELDS:
        suffix = "-" + name
        if key.endswith(suffix) and len(key) > len(suffix):
            return key[:-len(suffix)], name
    return None, key


def read_library(repository: str, text: str) -> list:
    """Every entry of one library file, in file order, each with its family identity; raises LibraryError."""
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise LibraryError("library_entry_invalid", f"not a library repository name: {repository[:80]}")
    rows = paragraphs(text)
    defaults = rows[0] if rows and TAGS not in rows[0] else {}
    entries = []
    for row in rows:
        if TAGS not in row:
            continue
        merged, overrides, declared = {}, {}, {}
        for source in (defaults, row):
            for key, value in source.items():
                architecture, name = _split_key(key)
                if architecture is not None:
                    overrides.setdefault(architecture, {})[name] = value
                    if source is row:
                        declared.setdefault("architecture_" + name, {})[architecture] = value
                else:
                    merged[key] = value
                    if source is row:
                        declared[key] = value
        tags, shared = _list(merged.get(TAGS, "")), _list(merged.get(SHARED_TAGS, ""))
        architectures = _list(merged[ARCHITECTURES]) if merged.get(ARCHITECTURES) else DEFAULTS[ARCHITECTURES]
        if not tags or any(not TAG_PATTERN.fullmatch(tag) for tag in tags + shared):
            raise LibraryError("library_entry_invalid", f"{repository}: an entry's tags are not tags: "
                                                        f"{merged.get(TAGS, '')[:120]}")
        if not merged.get(GIT_REPOSITORY):
            raise LibraryError("library_entry_invalid", f"{repository} {tags[0]}: no GitRepo")
        commit = merged.get(GIT_COMMIT, "")
        if not COMMIT_PATTERN.fullmatch(commit) and not all(
                COMMIT_PATTERN.fullmatch(overrides.get(architecture, {}).get(GIT_COMMIT, ""))
                for architecture in architectures):
            raise LibraryError("library_entry_invalid", f"{repository} {tags[0]}: no full GitCommit")
        entries.append(LibraryEntry(
            repository=repository, position=len(entries) + 1, tags=tags, shared_tags=shared,
            architectures=architectures, git_repository=merged[GIT_REPOSITORY],
            git_fetch=merged.get(GIT_FETCH, DEFAULTS[GIT_FETCH]), git_commit=commit,
            directory=merged.get(DIRECTORY, DEFAULTS[DIRECTORY]), file=merged.get(FILE, DEFAULTS[FILE]),
            builder=merged.get(BUILDER, ""), constraints=_list(merged.get(CONSTRAINTS, "")),
            overrides={architecture: values for architecture, values in overrides.items()
                       if architecture in architectures},
            declared=declared))
    seen = {}
    for entry in entries:
        for tag in entry.tags:
            if tag in seen:
                raise LibraryError("library_entry_invalid", f"{repository}: the tag {tag} names two entries")
            seen[tag] = entry.position
    return _with_families(entries)


def context_identity(entry: LibraryEntry) -> str:
    """The entry's own build context without its commits: what a rebuild or a new version keeps."""
    declared = entry.declared
    parts = [("fetch", declared.get(GIT_FETCH, "")), ("directory", declared.get(DIRECTORY, "")),
             ("file", declared.get(FILE, "")), ("constraints", ",".join(_list(declared.get(CONSTRAINTS, ""))))]
    directories = declared.get("architecture_" + DIRECTORY, {})
    if directories:
        parts.append(("directories", ",".join(f"{architecture}={value}"
                                              for architecture, value in sorted(directories.items()))))
    present = [f"{name}={value}" for name, value in parts if value]
    return CONTEXT_PREFIX + ";".join(present) if present else ""


def tag_identity(entry: LibraryEntry) -> str:
    """The shortest of the entry's own tags other than latest, the first such in the file's order."""
    candidates = [tag for tag in entry.tags if tag != LATEST_TAG] or list(entry.tags)
    return TAG_PREFIX + min(candidates, key=len)


def _with_families(entries: list) -> list:
    contexts = [context_identity(entry) for entry in entries]
    counts = {}
    for context in contexts:
        counts[context] = counts.get(context, 0) + 1
    result = []
    for entry, context in zip(entries, contexts):
        family = context if context and counts[context] == 1 else tag_identity(entry)
        result.append(LibraryEntry(**{**entry.__dict__, "family": family}))
    families = [entry.family for entry in result]
    if len(set(families)) != len(families):
        raise LibraryError("library_entry_invalid", f"{entries[0].repository}: two entries share a family identity")
    return result


__all__ = ["LibraryEntry", "LibraryError", "read_library", "paragraphs", "context_identity", "tag_identity",
           "LATEST_TAG", "ARCHITECTURES", "TAGS", "SHARED_TAGS"]
