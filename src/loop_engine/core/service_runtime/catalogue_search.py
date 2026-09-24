"""One reusable search index for each catalogue view, and the authorized search over it.

Served search used to build a new full-text table and a new set of hash
vectors for every request. Here one index is built with the view it belongs
to, off to the side of serving, and every request of that view reads it.

```text
Search over one view
├── filters     declared, filterable, public attributes only, refused otherwise
├── lexical     SQLite FTS5 BM25 over the same text the service indexed before,
│               plus the words of the release's searchable attributes
├── hybrid      lexical fused with the same deterministic character hash vectors,
│               held once as float32 columns instead of Python lists
├── authorize   the existing provisioning list, asked about the candidates only
└── fuse        reciprocal rank fusion over authorized candidates, as before
```

The index orders references; it never decides access. Every candidate passes
through the existing provisioning authority before it is returned, and ranks
and scores are computed among the authorized candidates only. The text,
tokens, vectors and fusion match `core.retrieval.Retriever`, so the starter
catalogue ranks as it did. One difference is stated rather than hidden: the
full-text statistics are computed over the whole view, not over one account's
items.
"""
from __future__ import annotations

from array import array
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass
import heapq
from itertools import repeat
import math
from operator import add, mul
import re
import sqlite3
import threading

from ..provisioning_server import TIER_ORDER, VERIFIED_TIER
from ..retrieval import _bucket, hash_vector, record_search_text
from ..retrieval_backends import RetrievalRankingPolicy
from ..store_serve import StoreRecord
from .catalogue_schema import DATE, EMPTY_SCHEMA, KEYWORD_LIST, NUMBER
from .records import ServiceRuntimeError

INDEX_RECORD_TYPE = "catalogue_view_index/v1"
#: The same limits and token rule as `core.retrieval.SqliteFtsBackend`.
LEXICAL_TERMS = 12
VECTOR_DIMENSIONS = 512
#: The retrieval modes the service offers, as `service_retrieval_request/v2` names them.
SEARCH_MODES = ("lexical", "hybrid")
LEXICAL_MODE, HYBRID_MODE = SEARCH_MODES
_TOKEN = re.compile(r"[a-z0-9]+")


class _TokenBuckets:
    """The same features as `core.retrieval.hash_vector`, computed once for each distinct word.

    Before normalization a hash vector holds whole-number counts, so adding one
    word's contributions in any order gives exactly the same sums, and the
    normalized vector equals `hash_vector` bit for bit. A library repeats its
    words, so each word's buckets are worked out once for the whole index.
    """

    def __init__(self):
        self._held = {}

    def contributions(self, token):
        held = self._held.get(token)
        if held is None:
            counts = {}
            bucket = _bucket("tok", token)
            counts[bucket] = counts.get(bucket, 0.0) + 2.0
            padded = f"##{token}##"
            for start in range(len(padded) - 2):
                bucket = _bucket("3g", padded[start:start + 3])
                counts[bucket] = counts.get(bucket, 0.0) + 1.0
            held = self._held[token] = tuple(counts.items())
        return held

    def vector(self, text):
        """Nonzero (dimension, weight) pairs of the normalized hash vector of one text."""
        counts = {}
        for token, times in Counter(_TOKEN.findall((text or "").lower())).items():
            for bucket, amount in self.contributions(token):
                counts[bucket] = counts.get(bucket, 0.0) + amount * times
        norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
        return [(bucket, value / norm) for bucket, value in counts.items()]


def entry_text(item, extra=""):
    """The words one item offers: exactly what the service indexed before, plus searchable attributes."""
    keywords = [item.identity, item.kind, item.source_layer] + ([extra] if extra else [])
    return record_search_text(StoreRecord(item.identity, "context", item.purpose,
                                          body={"description": item.purpose, "keywords": keywords}))


@dataclass(frozen=True)
class IndexEntry:
    identity: str
    text: str
    values: dict
    #: The trust tier of the item's approval, and whether it declares the
    #: process effect; search orders verified items first and a library
    #: setting can leave out community items that run a file.
    tier: str = VERIFIED_TIER
    runnable: bool = False


def index_for_items(items):
    """An index over items that declare no attributes, as a packaged manifest's items do."""
    return ReleaseSearchIndex(tuple(IndexEntry(item.identity, entry_text(item), {}) for item in items), EMPTY_SCHEMA)


class ReleaseSearchIndex:
    """Full text, hash vectors and filter tables for one view, built once and read by every request."""

    def __init__(self, entries, schema=EMPTY_SCHEMA, policy=None):
        self.policy = policy if policy is not None else RetrievalRankingPolicy()
        self.schema = schema
        entries = tuple(entries)
        self.identities = tuple(entry.identity for entry in entries)
        if len(set(self.identities)) != len(self.identities):
            raise ServiceRuntimeError("catalogue_index_invalid", "an index holds each identity once")
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._connection.execute("CREATE VIRTUAL TABLE entries USING fts5(position UNINDEXED, body)")
        self._connection.executemany("INSERT INTO entries VALUES (?, ?)",
                                     ((position, entry.text) for position, entry in enumerate(entries)))
        zero = bytes(4 * len(entries))
        self._columns = []
        for _dimension in range(VECTOR_DIMENSIONS):
            column = array("f")
            column.frombytes(zero)
            self._columns.append(column)
        buckets = _TokenBuckets()
        for position, entry in enumerate(entries):
            for dimension, weight in buckets.vector(entry.text):
                if weight:
                    self._columns[dimension][position] = weight
        self._sets, self._ranges = {}, {}
        for attribute in schema.attributes:
            if not attribute.filterable:
                continue
            if attribute.type in (NUMBER, DATE):
                pairs = sorted((entry.values[attribute.name], position) for position, entry in enumerate(entries)
                               if attribute.name in entry.values)
                self._ranges[attribute.name] = ([value for value, _position in pairs],
                                                [position for _value, position in pairs])
                continue
            table = {}
            for position, entry in enumerate(entries):
                if attribute.name in entry.values:
                    value = entry.values[attribute.name]
                    for element in (value if attribute.type == KEYWORD_LIST else (value,)):
                        table.setdefault(element, set()).add(position)
            self._sets[attribute.name] = table

    def stats(self):
        return {"record_type": INDEX_RECORD_TYPE, "entries": len(self.identities),
                "vector_bytes": VECTOR_DIMENSIONS * 4 * len(self.identities),
                "filterable_attributes": sorted(set(self._sets) | set(self._ranges))}

    def eligible(self, conditions):
        """The positions every typed filter condition accepts, or None when there is no filter."""
        chosen = None
        for name, operator, operand in conditions:
            if operator == "any_of":
                table = self._sets.get(name, {})
                positions = set().union(*(table.get(value, ()) for value in operand))
            else:
                values, positions_in_order = self._ranges.get(name, ([], []))
                low, high = operand
                start = 0 if low is None else bisect_left(values, low)
                end = len(values) if high is None else bisect_right(values, high)
                positions = set(positions_in_order[start:end])
            chosen = positions if chosen is None else chosen & positions
        return chosen

    def rank(self, query, *, mode, pool, eligible=None):
        """Best-first candidate pools and whether a larger pool could add anything."""
        lexical, exhausted = self._lexical(query, pool, eligible)
        pools = {"lexical": lexical}
        if mode == HYBRID_MODE:
            pools["vector"], vector_exhausted = self._vector(query, pool, eligible)
            exhausted = exhausted and vector_exhausted
        return pools, exhausted

    def _lexical(self, query, pool, eligible):
        terms = _TOKEN.findall(query.lower())
        if not terms or not self.identities:
            return [], True
        match = " OR ".join(f'"{term}"' for term in terms[:LEXICAL_TERMS])
        limit = len(self.identities) if eligible is not None else pool
        try:
            with self._lock:
                rows = self._connection.execute(
                    "SELECT position, bm25(entries) FROM entries WHERE entries MATCH ? "
                    "ORDER BY bm25(entries), position LIMIT ?", (match, limit)).fetchall()
        except sqlite3.Error:
            raise ServiceRuntimeError("search_index_unavailable", "the release search index did not answer") from None
        kept = [(self.identities[position], -score) for position, score in rows
                if eligible is None or position in eligible]
        if eligible is None:
            return kept, len(rows) < limit
        return kept[:pool], len(kept) <= pool

    def _vector(self, query, pool, eligible):
        weights = [(dimension, weight) for dimension, weight in enumerate(hash_vector(query)) if weight]
        if not weights or not self.identities:
            return [], True
        scores = None
        for dimension, weight in weights:
            products = map(mul, self._columns[dimension], repeat(weight))
            scores = list(products) if scores is None else list(map(add, scores, products))
        floor = self.policy.hash_similarity_floor
        candidates = ((score, position) for position, score in enumerate(scores)
                      if score > floor and (eligible is None or position in eligible))
        best = heapq.nsmallest(pool + 1, candidates, key=lambda row: (-row[0], row[1]))
        return [(self.identities[position], score) for score, position in best[:pool]], len(best) <= pool


def fuse(pools, allowed, policy, top_n):
    """Reciprocal rank fusion over the authorized candidates only, as `Retriever.search` fuses.

    Verified items come before community items; within a tier the fused score
    orders them. `allowed` maps each authorized identity to its provisioning
    row, whose trust tier the provisioning authority stated.
    """
    fused = {}
    for name, rows in pools.items():
        rank = 0
        for identity, _score in rows:
            if identity not in allowed:
                continue
            entry = fused.setdefault(identity, [0.0, set()])
            entry[0] += 1.0 / (policy.reciprocal_rank_offset + rank)
            entry[1].add(name)
            rank += 1

    def tier_rank(identity):
        row = allowed[identity]
        return TIER_ORDER[row["trust_tier"]] if isinstance(row, dict) and "trust_tier" in row else 0
    ordered = sorted(fused.items(), key=lambda row: (tier_rank(row[0]), -row[1][0], row[0]))[:top_n]
    return [(identity, round(score, 5), sorted(modes)) for identity, (score, modes) in ordered]


def authorized_hits(view, fields, authorize):
    """Rank in the view's index, keep what `authorize` returns, and widen the pool until it is full.

    `authorize` receives candidate identities and returns the provisioning rows
    the caller may see. Filters are checked against the view's schema before
    anything is ranked, so an undeclared or internal attribute is refused
    without touching the index.
    """
    index = view.search_index()
    conditions = view.schema.filter_request(fields.get("filters"))
    eligible = index.eligible(conditions) if conditions else None
    top_n, mode = fields.get("top_n", 10), fields.get("mode", LEXICAL_MODE)
    pool = max(1, top_n * index.policy.candidate_pool_multiplier)
    total = max(1, len(index.identities))
    while True:
        pools, exhausted = index.rank(fields["query"], mode=mode, pool=pool, eligible=eligible)
        candidates = tuple(dict.fromkeys(identity for rows in pools.values() for identity, _score in rows))
        rows = authorize(candidates) if candidates else {}
        hits = fuse(pools, rows, index.policy, top_n)
        if len(hits) >= top_n or exhausted or pool >= total:
            return hits, rows
        pool = min(total, pool * 4)
