"""Exact and near-duplicate grouping for outside candidates, and the merge of provenance.

Exact duplicates share the digest of their normalized comparison text (the
body of a skill without its frontmatter, the whole text of an instruction
file, or the package or endpoint identity of a connection). Near duplicates
are pairs whose word shingles an engine of the library_near_duplicate slot
estimates to be at least the declared threshold alike. Pairs join groups,
and each group keeps one item by the declared order (source order, then
path); every other member is merged into it, its provenance added to the
kept item's list, with a library_duplicate_link/v1 record naming the kept
item, the merged item, the item it matched and the similarity. Nothing is
dropped without a record.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .record_rules import LibraryRecordError, bytes_digest

DUPLICATE_LINK_RECORD_TYPE = "library_duplicate_link/v1"
SHINGLE_WORDS = 5
#: Below this, unrelated texts on a common topic start to merge.
MINIMUM_THRESHOLD = 0.5


@dataclass(frozen=True)
class DuplicateSubject:
    key: str
    order: tuple
    comparison_text: str
    exact_only: bool = False


def normalized(text: str) -> str:
    return " ".join(re.findall(r"[\w'-]+", text.lower()))


def shingles(text: str, size: int = SHINGLE_WORDS) -> frozenset:
    words = normalized(text).split()
    if len(words) < size:
        return frozenset({" ".join(words)}) if words else frozenset()
    return frozenset(" ".join(words[index:index + size]) for index in range(len(words) - size + 1))


def _link(kept: str, merged: str, kind: str, similarity: float) -> dict:
    return {"record_type": DUPLICATE_LINK_RECORD_TYPE, "kept": kept, "merged": merged, "matched": kept,
            "kind": kind, "similarity": similarity}


def group_duplicates(subjects, engine, threshold: float):
    """Return the kept keys in order and one link record for every merged key."""
    if not MINIMUM_THRESHOLD <= threshold <= 1:
        raise LibraryRecordError("invalid_threshold",
                                 f"a near-duplicate threshold is between {MINIMUM_THRESHOLD} and 1")
    subjects = sorted(subjects, key=lambda subject: subject.order)
    kept, links, by_digest = [], [], {}
    for subject in subjects:
        digest = bytes_digest(normalized(subject.comparison_text).encode("utf-8"))
        if digest in by_digest:
            links.append(_link(by_digest[digest].key, subject.key, "exact", 1.0))
            continue
        by_digest[digest] = subject
        kept.append(subject)
    near = {subject.key: shingles(subject.comparison_text) for subject in kept if not subject.exact_only}
    near = {key: value for key, value in near.items() if value}
    parent = {subject.key: subject.key for subject in kept}
    rank = {subject.key: index for index, subject in enumerate(kept)}
    similarity = {}

    def root(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for left, right, estimate in engine.pairs(near, threshold) if len(near) > 1 else ():
        first, second = root(left), root(right)
        if first != second:
            keep, drop = (first, second) if rank[first] < rank[second] else (second, first)
            parent[drop] = keep
            similarity[drop] = estimate
    survivors = []
    for subject in kept:
        top = root(subject.key)
        if top == subject.key:
            survivors.append(subject.key)
        else:
            links.append(_link(top, subject.key, "near", similarity.get(subject.key, threshold)))
    # An exact twin of an item that was later merged as a near duplicate belongs to the
    # item that survived; "matched" keeps the twin it was compared with.
    for link in links:
        link["kept"] = root(link["kept"])
    return survivors, links
