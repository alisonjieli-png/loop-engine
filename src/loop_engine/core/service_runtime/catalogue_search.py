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
└── fuse        reciprocal rank fusion over authorized candidates, as before, with the
                policy's tier order: strict, or a bounded boost for lexical requests
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

from ..provisioning_server import COMMUNITY_EXCLUDED, TIER_ORDER, VERIFIED_TIER
from ..retrieval import _bucket, hash_vector, record_search_text
from ..retrieval_backends import RetrievalRankingPolicy
from ..store_serve import StoreRecord
from .catalogue_attributes import TIER_ATTRIBUTE
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
    #: The library tier of the item's approval, and whether it declares the
    #: process effect; the ranking policy's tier order reads the tier and a
    #: library setting can leave out community items that run a file.
    tier: str = VERIFIED_TIER
    runnable: bool = False


def index_for_items(items):
    """An index over items that declare no attributes, as a packaged manifest's items do."""
    return ReleaseSearchIndex(tuple(IndexEntry(item.identity, entry_text(item), {}) for item in items), EMPTY_SCHEMA)


#: How a lexical request orders the library tiers among the relevant authorized candidates. `strict` puts every
#: verified candidate above the floor before every community one. `bounded_boost` orders them by lexical score
#: and multiplies a verified candidate's score by one plus `lexical_verified_boost` first, so a verified item
#: outranks a community item only when its own score is at least 1 / (1 + boost) of that item's score.
LEXICAL_TIER_ORDERS = ("strict", "bounded_boost")
STRICT_TIER_ORDER, BOUNDED_TIER_BOOST = LEXICAL_TIER_ORDERS
#: The largest verified boost a policy may declare: a verified item at a tenth of a community item's score.
MAXIMUM_VERIFIED_BOOST = 9.0

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_VERSION_SUFFIX = re.compile(r"^v?\d+(?:[._-]\d+)*$")
_PROMPT_STOPWORDS = frozenset({
    "a", "an", "and", "any", "are", "as", "at", "be", "best", "build", "by", "can", "code", "could", "create",
    "do", "does", "example", "find", "for", "from", "function", "generate", "get", "give", "good", "have", "help",
    "helper", "how", "i", "implement", "in", "into", "is", "it", "its", "like", "looking", "make", "me", "method",
    "module", "my", "need", "of", "on", "one", "or", "our", "please", "script", "show", "simple", "small", "some",
    "that", "the", "their", "them", "then", "these", "this", "those", "to", "tool", "use", "using", "util",
    "utility", "want", "way", "we", "what", "when", "where", "which", "with", "would", "write", "you", "your",
})
#: Bidirectional developer shorthand and technical alias expansions for Stage 2 query relaxation.
TECHNICAL_ALIASES = {
    "ttl": ("time", "live", "expiry", "expiration"),
    "lru": ("least", "recently", "used", "cache"),
    "dedup": ("duplicate", "deduplicate", "deduplication"),
    "dedupe": ("duplicate", "deduplicate", "deduplication"),
    "dotenv": ("dotenv", "environment", "variables", "settings"),
    "env": ("dotenv", "environment", "variables", "settings"),
    "semver": ("semantic", "version", "versioning"),
    "gha": ("github", "actions", "workflow"),
    "k8s": ("kubernetes", "container", "cluster"),
    "auth": ("authentication", "authorization", "oauth"),
    "a11y": ("accessibility", "wcag", "aria"),
    "i18n": ("internationalization", "localization", "translation"),
    "l10n": ("localization", "internationalization", "translation"),
    "db": ("database", "sql", "query"),
    "pr": ("pull", "request", "review"),
    "regex": ("regular", "expression", "pattern"),
    "regexp": ("regular", "expression", "pattern"),
    "changelog": ("changelog", "release", "notes", "changes"),
    "tdd": ("test", "driven", "unit"),
    "csv": ("csv", "spreadsheet", "tabular"),
}


def split_subtokens(text):
    """Split camelCase, PascalCase, snake_case, kebab-case and path segments into lowercase alphanumeric sub-tokens."""
    if not text:
        return []
    separated = _CAMEL_BOUNDARY.sub(" ", str(text))
    tokens = _TOKEN.findall(separated.lower())
    return [token for token in tokens if not _VERSION_SUFFIX.match(token) or len(tokens) == 1]


def stem_token(token):
    """Light, deterministic morphological stem folding for non-exact sub-token and LSH matching."""
    token = (token or "").lower()
    if len(token) <= 3:
        return token
    for suffix, replacement in (("isation", "iz"), ("ization", "iz"), ("ating", "at"), ("ition", "it"),
                                ("ation", "at"), ("ments", "ment"), ("ment", "ment"), ("ities", "it"),
                                ("ness", ""), ("ings", ""), ("ing", ""), ("edly", ""), ("ed", ""),
                                ("ies", "y"), ("es", ""), ("s", "")):
        if token.endswith(suffix) and len(token) - len(suffix) + len(replacement) >= 3:
            return token[:len(token) - len(suffix)] + replacement
    return token


def normalize_subtokens(text):
    """Normalized sub-tokens and their light morphological stems in appearance order, deduplicated."""
    out = []
    for token in split_subtokens(text):
        if token not in out:
            out.append(token)
        stem = stem_token(token)
        if stem and stem not in out:
            out.append(stem)
    return out


def extract_core_query_terms(query, limit=LEXICAL_TERMS):
    """Fallback Stage 1: split identifier sub-tokens and drop low-IDF conversational filler terms."""
    subtokens = split_subtokens(query)
    if not subtokens:
        return []
    core = [token for token in subtokens if token not in _PROMPT_STOPWORDS and len(token) > 1]
    if not core:
        core = [token for token in subtokens if token not in _PROMPT_STOPWORDS] or subtokens
    deduped = list(dict.fromkeys(core))
    return deduped[:limit]


def expand_query_aliases(query, limit=LEXICAL_TERMS):
    """Fallback Stage 2: expand developer shorthand and technical synonyms into high-signal search tokens."""
    core = extract_core_query_terms(query, limit=limit * 2)
    expanded = []
    for token in core:
        if token not in expanded:
            expanded.append(token)
        for alias in TECHNICAL_ALIASES.get(token, ()):
            if alias not in expanded:
                expanded.append(alias)
        stem = stem_token(token)
        if stem != token and len(stem) >= 4 and stem not in expanded:
            expanded.append(stem)
    return expanded[:limit]


_HEX_DIGEST_TOKEN = re.compile(r"^[0-9a-f]{7,}$")


class LSHShingleBlocker:
    """Fallback Stage 3: dependency-free MinHash LSH banding and character n-gram shingle candidate blocker.

    Builds character 3-gram and 4-gram shingle sets plus normalized sub-token stems for each indexed entry,
    partitions shingle hashes into `bands` MinHash bands of `rows_per_band` hash functions, and retrieves
    typo-tolerant and morphology-tolerant candidates when exact FTS5 lookup is empty or sparse. Distinct tokens
    are memoized once across the library and postings are stored in compact unsigned-int arrays so 250k+ item
    indexes build in seconds with bounded memory.
    """

    def __init__(self, entries, *, bands=4, rows_per_band=2, max_postings_per_bucket=96):
        self._entries = tuple(entries)
        self.identities = tuple(entry.identity for entry in self._entries)
        self.bands = bands
        self.rows_per_band = rows_per_band
        self.max_postings_per_bucket = max_postings_per_bucket
        self._band_buckets = [{} for _ in range(bands)]
        self._shingle_postings = {}
        self._stem_postings = {}
        num_hashes = bands * rows_per_band
        primes = tuple((1315423911 + i * 2654435761, 374761393 + i * 668265263)
                       for i in range(num_hashes))
        self._primes = primes
        token_cache = {}

        def token_features(token):
            cached = token_cache.get(token)
            if cached is None:
                stem = stem_token(token)
                shingles = self._shingles_for_tokens((token,))
                if shingles:
                    mins = tuple(min(((s * a + b) & 0xFFFFFFFF) for s in shingles) for a, b in primes)
                else:
                    mins = ()
                cached = token_cache[token] = (stem, shingles, mins)
            return cached

        for position, entry in enumerate(self._entries):
            id_tokens = [t for t in split_subtokens(entry.identity)
                         if len(t) >= 2 and not _HEX_DIGEST_TOKEN.match(t)]
            head_tokens = [t for t in _TOKEN.findall((entry.text or "")[:200].lower())
                           if 2 <= len(t) <= 28 and t not in _PROMPT_STOPWORDS and not _HEX_DIGEST_TOKEN.match(t)]
            unique_tokens = tuple(dict.fromkeys((*id_tokens, *head_tokens[:8])))
            stems = set()
            id_shingles = set()
            entry_mins = None
            for idx, tok in enumerate(unique_tokens):
                stem, shingles, mins = token_features(tok)
                if len(stem) >= 2:
                    stems.add(stem)
                if idx < len(id_tokens):
                    id_shingles.update(shingles)
                if mins:
                    if entry_mins is None:
                        entry_mins = list(mins)
                    else:
                        for h_idx, val in enumerate(mins):
                            if val < entry_mins[h_idx]:
                                entry_mins[h_idx] = val
            for stem in stems:
                bucket = self._stem_postings.get(stem)
                if bucket is None:
                    self._stem_postings[stem] = array("I", (position,))
                elif len(bucket) < max_postings_per_bucket:
                    bucket.append(position)
            for shingle in id_shingles:
                bucket = self._shingle_postings.get(shingle)
                if bucket is None:
                    self._shingle_postings[shingle] = array("I", (position,))
                elif len(bucket) < max_postings_per_bucket:
                    bucket.append(position)
            if entry_mins is not None:
                for band in range(bands):
                    offset = band * rows_per_band
                    sig = 0
                    for r in range(rows_per_band):
                        sig = (sig << 8) | ((entry_mins[offset + r] >> 24) & 0xFF)
                    bucket = self._band_buckets[band].get(sig)
                    if bucket is None:
                        self._band_buckets[band][sig] = array("I", (position,))
                    elif len(bucket) < max_postings_per_bucket:
                        bucket.append(position)

    @staticmethod
    def _shingles_for_tokens(tokens):
        shingles = set()
        for token in tokens:
            if len(token) < 2 or token in _PROMPT_STOPWORDS:
                continue
            padded = f"#{token}#"
            for size in (3, 4):
                if len(padded) >= size:
                    for start in range(len(padded) - size + 1):
                        shingles.add(_bucket(f"{size}g", padded[start:start + size]))
        return frozenset(shingles)

    def _entry_feature_sets(self, position):
        entry = self._entries[position]
        id_tokens = [t for t in split_subtokens(entry.identity)
                     if len(t) >= 2 and not _HEX_DIGEST_TOKEN.match(t)]
        text_tokens = [t for t in split_subtokens((entry.text or "")[:320])[:24]
                       if len(t) >= 2 and t not in _PROMPT_STOPWORDS and not _HEX_DIGEST_TOKEN.match(t)]
        id_stems = frozenset(stem_token(t) for t in id_tokens)
        stems = id_stems | frozenset(stem_token(t) for t in text_tokens)
        id_shingles = self._shingles_for_tokens(id_tokens)
        shingles = id_shingles | self._shingles_for_tokens(text_tokens[:12])
        return shingles, id_shingles, stems, id_stems

    def candidates(self, query, *, limit=100, eligible=None):
        """Rank candidate entries by LSH band collision + character shingle containment + sub-token stem overlap."""
        if not self.identities:
            return []
        q_tokens = extract_core_query_terms(query, limit=LEXICAL_TERMS * 2) or split_subtokens(query)
        if not q_tokens:
            return []
        q_stems = frozenset(stem_token(t) for t in q_tokens if len(t) >= 2)
        q_shingles = self._shingles_for_tokens(q_tokens)
        if not q_shingles and not q_stems:
            return []
        blocked = Counter()
        if q_shingles:
            for band in range(self.bands):
                offset = band * self.rows_per_band
                sig = 0
                for r in range(self.rows_per_band):
                    h_min = min(((shingle * self._primes[offset + r][0] + self._primes[offset + r][1]) & 0xFFFFFFFF)
                                for shingle in q_shingles)
                    sig = (sig << 8) | ((h_min >> 24) & 0xFF)
                for pos in self._band_buckets[band].get(sig, ()):
                    if eligible is None or pos in eligible:
                        blocked[pos] += 3
            for shingle in q_shingles:
                for pos in self._shingle_postings.get(shingle, ()):
                    if eligible is None or pos in eligible:
                        blocked[pos] += 2
        for stem in q_stems:
            for pos in self._stem_postings.get(stem, ()):
                if eligible is None or pos in eligible:
                    blocked[pos] += 4
        if not blocked:
            return []
        scored = []
        for pos, _hits in blocked.most_common(max(limit * 2, 120)):
            e_shingles, id_shingles, e_stems, id_stems = self._entry_feature_sets(pos)
            q_containment = (len(q_shingles & e_shingles) / len(q_shingles)) if q_shingles else 0.0
            id_containment = (len(q_shingles & id_shingles) / len(q_shingles)) if q_shingles else 0.0
            stem_overlap = (len(q_stems & e_stems) / len(q_stems)) if q_stems else 0.0
            id_overlap = (len(q_stems & id_stems) / len(q_stems)) if q_stems else 0.0
            if not (id_containment >= 0.45 or q_containment >= 0.55
                    or (stem_overlap >= 0.5 and q_containment >= 0.35)):
                continue
            score = 25.0 * (0.35 * id_containment + 0.25 * q_containment + 0.20 * stem_overlap + 0.20 * id_overlap)
            if score >= 8.0:
                scored.append((self.identities[pos], round(score, 6), pos))
        scored.sort(key=lambda row: (-row[1], row[2]))
        return [(identity, score) for identity, score, _pos in scored[:limit]]


@dataclass(frozen=True)
class CatalogueRankingPolicy(RetrievalRankingPolicy):
    """Catalogue-only lexical discovery bounds; explicit generic policies keep their own behavior.

    The floor is relative to the best authorized lexical score in this query,
    not a correctness probability. The tier order applies to lexical-only
    requests; a hybrid request keeps its candidate selection and orders
    verified candidates first. Index contents, raw engine scores and the
    permission boundary stay fixed.
    """

    lexical_pool_multiplier: int = 50
    lexical_score_floor_ratio: float = 0.2
    lexical_tier_pool_multiplier: int = 10
    lexical_tier_order: str = STRICT_TIER_ORDER
    lexical_verified_boost: float = 0.0

    def __post_init__(self):
        super().__post_init__()
        if type(self.lexical_pool_multiplier) is not int or self.lexical_pool_multiplier < 1:
            raise ValueError("the lexical pool multiplier is a positive integer")
        if type(self.lexical_tier_pool_multiplier) is not int or self.lexical_tier_pool_multiplier < 1:
            raise ValueError("the lexical tier pool multiplier is a positive integer")
        ratio = self.lexical_score_floor_ratio
        if type(ratio) not in (int, float) or not math.isfinite(ratio) or not 0 <= ratio <= 1:
            raise ValueError("the lexical score floor ratio is a finite number from zero to one")
        if self.lexical_tier_order not in LEXICAL_TIER_ORDERS:
            raise ValueError(f"the lexical tier order is one of {LEXICAL_TIER_ORDERS}")
        boost = self.lexical_verified_boost
        if (type(boost) not in (int, float) or not math.isfinite(boost)
                or not 0 <= boost <= MAXIMUM_VERIFIED_BOOST):
            raise ValueError(f"the verified boost is a finite number from zero to {MAXIMUM_VERIFIED_BOOST}")
        if self.lexical_tier_order == STRICT_TIER_ORDER and boost:
            raise ValueError("a strict tier order takes no verified boost")


@dataclass(frozen=True)
class CatalogueRankingEngine(CatalogueRankingPolicy):
    """A selectable ranking engine variation over `CatalogueRankingPolicy` with optional field/phrase/LSH bonuses."""

    engine_name: str = "bounded_tier_boost"
    identity_match_boost: float = 0.0
    phrase_match_boost: float = 0.0
    verified_score_band: float = 0.0
    enable_query_fallback: bool = False
    query_context: str = ""

    def __post_init__(self):
        super().__post_init__()
        for label, value in (("identity_match_boost", self.identity_match_boost),
                             ("phrase_match_boost", self.phrase_match_boost),
                             ("verified_score_band", self.verified_score_band)):
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= MAXIMUM_VERIFIED_BOOST:
                raise ValueError(f"{label} is a finite non-negative number")
        if type(self.enable_query_fallback) is not bool:
            raise ValueError("enable_query_fallback is a boolean")

    def for_query(self, query):
        if not (self.identity_match_boost or self.phrase_match_boost):
            return self
        return CatalogueRankingEngine(
            reciprocal_rank_offset=self.reciprocal_rank_offset,
            candidate_pool_multiplier=self.candidate_pool_multiplier,
            hash_similarity_floor=self.hash_similarity_floor,
            lexical_pool_multiplier=self.lexical_pool_multiplier,
            lexical_score_floor_ratio=self.lexical_score_floor_ratio,
            lexical_tier_pool_multiplier=self.lexical_tier_pool_multiplier,
            lexical_tier_order=self.lexical_tier_order,
            lexical_verified_boost=self.lexical_verified_boost,
            engine_name=self.engine_name,
            identity_match_boost=self.identity_match_boost,
            phrase_match_boost=self.phrase_match_boost,
            verified_score_band=self.verified_score_band,
            enable_query_fallback=self.enable_query_fallback,
            query_context=str(query or ""),
        )


#: The named ranking policies a caller can choose. `strict_tier_order` is the order served until the October 16,
#: 2026 comparison: a larger lexical pool keeps relevant candidates visible as the catalogue grows, and the
#: query-local score floor removes incidental matches before review-tier ordering; it never reads an unauthorized
#: candidate's score. `bounded_tier_boost` keeps the pool, the floor and the verified candidate pool and replaces
#: the hard tier order with a bounded boost. Both stay selectable; the comparison, its population and its limits
#: are in docs/verification/SEARCH-RANKING-2026-10-16.md.
RANKING_POLICIES = {
    "strict_tier_order": CatalogueRankingPolicy(candidate_pool_multiplier=10),
    "bounded_tier_boost": CatalogueRankingPolicy(candidate_pool_multiplier=10, lexical_tier_order=BOUNDED_TIER_BOOST,
                                                 lexical_verified_boost=1.0),
}
#: Selectable ranking engines: the baseline (`strict_tier_order` / `tier_first`), the winning default
#: (`bounded_tier_boost`), and the measured engine variations (`field_weighted_lexical`,
#: `phrase_and_symbol_boost`, `gated_relevance_fusion`, `flexible_lsh_fallback`).
RANKING_ENGINES = {
    "strict_tier_order": RANKING_POLICIES["strict_tier_order"],
    "tier_first": RANKING_POLICIES["strict_tier_order"],
    "bounded_tier_boost": RANKING_POLICIES["bounded_tier_boost"],
    "field_weighted_lexical": CatalogueRankingEngine(
        candidate_pool_multiplier=10, lexical_tier_order=BOUNDED_TIER_BOOST, lexical_verified_boost=1.0,
        engine_name="field_weighted_lexical", identity_match_boost=0.35),
    "phrase_and_symbol_boost": CatalogueRankingEngine(
        candidate_pool_multiplier=10, lexical_tier_order=BOUNDED_TIER_BOOST, lexical_verified_boost=1.0,
        engine_name="phrase_and_symbol_boost", identity_match_boost=0.2, phrase_match_boost=0.35),
    "gated_relevance_fusion": CatalogueRankingEngine(
        candidate_pool_multiplier=10, lexical_score_floor_ratio=0.25, lexical_tier_order=BOUNDED_TIER_BOOST,
        lexical_verified_boost=1.5, engine_name="gated_relevance_fusion", verified_score_band=0.35),
    "flexible_lsh_fallback": CatalogueRankingEngine(
        candidate_pool_multiplier=10, lexical_tier_order=BOUNDED_TIER_BOOST, lexical_verified_boost=1.0,
        engine_name="flexible_lsh_fallback", identity_match_boost=0.2, enable_query_fallback=True),
}
DEFAULT_RANKING_POLICY = "bounded_tier_boost"
CATALOGUE_RANKING_POLICY = RANKING_POLICIES[DEFAULT_RANKING_POLICY]


def select_ranking_engine(policy_or_name=None):
    """Resolve a ranking policy or engine by name, or return an explicit policy object."""
    if policy_or_name is None:
        return CATALOGUE_RANKING_POLICY
    if isinstance(policy_or_name, str):
        if policy_or_name in RANKING_ENGINES:
            return RANKING_ENGINES[policy_or_name]
        raise ValueError(f"unknown catalogue ranking engine: {policy_or_name!r}")
    return policy_or_name


def candidate_pool_size(policy, top_n, mode):
    """The caller's explicit policy, with a separate lexical bound only when its policy declares one."""
    multiplier = (getattr(policy, "lexical_pool_multiplier", policy.candidate_pool_multiplier)
                  if mode == LEXICAL_MODE else policy.candidate_pool_multiplier)
    return max(1, top_n * multiplier)


class ReleaseSearchIndex:
    """Full text, hash vectors and filter tables for one view, built once and read by every request."""

    def __init__(self, entries, schema=EMPTY_SCHEMA, policy=None, *, build_vectors=True):
        self.policy = select_ranking_engine(policy) if policy is not None else CATALOGUE_RANKING_POLICY
        self.schema = schema
        entries = tuple(entries)
        self._entries = entries
        self.identities = tuple(entry.identity for entry in entries)
        # This is a checked projection, never an authorization grant. A missing or conflicting attribute keeps
        # tier narrowing at the provisioning boundary instead of hiding a permitted item from search.
        self.tier_filter_complete = bool(entries) and all(
            entry.values.get(TIER_ATTRIBUTE["name"]) == entry.tier for entry in entries)
        if len(set(self.identities)) != len(self.identities):
            raise ServiceRuntimeError("catalogue_index_invalid", "an index holds each identity once")
        self._lock = threading.Lock()
        self._lsh_blocker = None
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._connection.execute("CREATE VIRTUAL TABLE entries USING fts5(position UNINDEXED, body)")
        self._connection.executemany("INSERT INTO entries VALUES (?, ?)",
                                     ((position, entry.text) for position, entry in enumerate(entries)))
        self._columns = []
        if build_vectors:
            self._ensure_vectors()
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
        self.tier_filter_complete = self.tier_filter_complete and TIER_ATTRIBUTE["name"] in self._sets

    def _ensure_vectors(self):
        if self._columns:
            return
        with self._lock:
            if self._columns:
                return
            zero = bytes(4 * len(self._entries))
            columns = []
            for _dimension in range(VECTOR_DIMENSIONS):
                column = array("f")
                column.frombytes(zero)
                columns.append(column)
            buckets = _TokenBuckets()
            for position, entry in enumerate(self._entries):
                for dimension, weight in buckets.vector(entry.text):
                    if weight:
                        columns[dimension][position] = weight
            self._columns = columns

    def lsh_blocker(self):
        """Lazily built LSH shingle blocker over this index's entries."""
        if self._lsh_blocker is None:
            with self._lock:
                if self._lsh_blocker is None:
                    self._lsh_blocker = LSHShingleBlocker(self._entries)
        return self._lsh_blocker

    def close(self):
        """Close the in-memory FTS5 SQLite connection when an index is retired."""
        with self._lock:
            self._connection.close()

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
        self._ensure_vectors()
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


def rank_with_fallbacks(index, query, *, pool, eligible=None):
    """Multi-stage query relaxation and LSH shingle blocking when exact lexical lookup is empty or sparse.

    Stage 1: Split camelCase/PascalCase/snake_case/kebab-case sub-tokens and extract high-IDF core terms.
    Stage 2: Expand developer shorthand and technical synonyms (`TECHNICAL_ALIASES`) plus morphological stems.
    Stage 3: Block and score candidates with `LSHShingleBlocker` (MinHash bands + character n-gram Jaccard).
    """
    merged = {}
    stages_used = []
    raw_terms = _TOKEN.findall((query or "").lower())[:LEXICAL_TERMS]
    core_terms = extract_core_query_terms(query, limit=LEXICAL_TERMS)
    if core_terms and core_terms != raw_terms:
        stage1_pools, _ = index.rank(" ".join(core_terms), mode=LEXICAL_MODE, pool=pool, eligible=eligible)
        for identity, score in stage1_pools.get(LEXICAL_MODE, ()):
            merged[identity] = max(merged.get(identity, 0.0), score)
        if stage1_pools.get(LEXICAL_MODE):
            stages_used.append("stage1_subtoken_core")
    alias_terms = expand_query_aliases(query, limit=LEXICAL_TERMS)
    if alias_terms and alias_terms != core_terms and alias_terms != raw_terms:
        stage2_pools, _ = index.rank(" ".join(alias_terms), mode=LEXICAL_MODE, pool=pool, eligible=eligible)
        for identity, score in stage2_pools.get(LEXICAL_MODE, ()):
            merged[identity] = max(merged.get(identity, 0.0), score * 0.92)
        if stage2_pools.get(LEXICAL_MODE):
            stages_used.append("stage2_alias_expansion")
    if len(merged) < min(pool, 10) and hasattr(index, "lsh_blocker"):
        lsh_rows = index.lsh_blocker().candidates(query, limit=pool, eligible=eligible)
        for identity, score in lsh_rows:
            merged[identity] = max(merged.get(identity, 0.0), score)
        if lsh_rows:
            stages_used.append("stage3_lsh_shingle_blocker")
    ordered = sorted(merged.items(), key=lambda row: (-row[1], row[0]))[:pool]
    return {LEXICAL_MODE: ordered}, stages_used


def _require_lexical_scores(scores):
    if any(type(score) not in (int, float) or not math.isfinite(score) or score < 0 for score in scores):
        raise ServiceRuntimeError("search_index_unavailable", "the lexical index returned an invalid score")
    return scores


def lexical_relevance_floor(pools, allowed, policy):
    """A query-local floor over authorized lexical scores, or None for an unfiltered or hybrid request."""
    ratio = getattr(policy, "lexical_score_floor_ratio", 0) if set(pools) == {LEXICAL_MODE} else 0
    if not ratio:
        return None
    scores = [score for identity, score in pools[LEXICAL_MODE] if identity in allowed]
    if not scores:
        return None
    return max(_require_lexical_scores(scores)) * ratio


def _tier_rank(allowed, identity):
    row = allowed[identity]
    return TIER_ORDER[row["library_tier"]] if isinstance(row, dict) and "library_tier" in row else 0


def _identity_bonus_multiplier(identity, q_stems, q_bigrams, id_boost, phrase_boost):
    if not (id_boost or phrase_boost) or not q_stems:
        return 1.0
    id_tokens = split_subtokens(identity)
    id_stems = {stem_token(t) for t in id_tokens if t}
    bonus = 1.0
    if id_boost and id_stems:
        overlap = len(q_stems & id_stems) / len(q_stems)
        bonus += id_boost * overlap
    if phrase_boost and q_bigrams and len(id_tokens) >= 2:
        id_bigrams = {(stem_token(id_tokens[i]), stem_token(id_tokens[i + 1])) for i in range(len(id_tokens) - 1)}
        if q_bigrams & id_bigrams:
            bonus += phrase_boost
    return bonus


def bounded_tier_boost(pools, allowed, policy):
    """The authorized lexical rows reordered by boosted score, or None when the request keeps the strict order.

    Only a lexical-only request under a `bounded_boost` policy is reordered. A verified row's score is multiplied
    by one plus the policy's boost; a community row keeps its score. Equal boosted scores put the verified row
    first, and the sort is stable, so rows equal in both keep the index's own order.
    """
    if set(pools) != {LEXICAL_MODE} or getattr(policy, "lexical_tier_order", STRICT_TIER_ORDER) != BOUNDED_TIER_BOOST:
        return None
    rows = [(identity, score) for identity, score in pools[LEXICAL_MODE] if identity in allowed]
    _require_lexical_scores([score for _identity, score in rows])
    if not rows:
        return []
    multiplier, verified = 1.0 + policy.lexical_verified_boost, TIER_ORDER[VERIFIED_TIER]
    band = getattr(policy, "verified_score_band", 0.0)
    best_raw = max(score for _identity, score in rows) if band else 0.0
    id_boost = getattr(policy, "identity_match_boost", 0.0)
    phrase_boost = getattr(policy, "phrase_match_boost", 0.0)
    query_context = getattr(policy, "query_context", "")
    q_tokens = extract_core_query_terms(query_context) if (id_boost or phrase_boost) and query_context else []
    q_stems = {stem_token(t) for t in q_tokens if t}
    q_bigrams = ({(stem_token(q_tokens[i]), stem_token(q_tokens[i + 1])) for i in range(len(q_tokens) - 1)}
                 if len(q_tokens) >= 2 else set())

    def boosted(row):
        identity, score = row
        tier = _tier_rank(allowed, identity)
        effective = score * _identity_bonus_multiplier(identity, q_stems, q_bigrams, id_boost, phrase_boost)
        if tier == verified and (not band or score >= band * best_raw):
            effective *= multiplier
        return (-effective, tier)
    return sorted(rows, key=boosted)


def _strict_fuse(pools, allowed, policy, top_n):
    """Stage 4 safety fallback: baseline strict-tier-order fusion over authorized candidates."""
    baseline = RANKING_POLICIES["strict_tier_order"]
    offset = getattr(policy, "reciprocal_rank_offset", baseline.reciprocal_rank_offset)
    floor = lexical_relevance_floor(pools, allowed, baseline)
    active = ({LEXICAL_MODE: [(identity, score) for identity, score in pools[LEXICAL_MODE]
                              if identity in allowed and score >= floor]}
              if floor is not None else pools)
    fused = {}
    for name, rows in active.items():
        rank = 0
        for identity, _score in rows:
            if identity not in allowed:
                continue
            entry = fused.setdefault(identity, [0.0, set()])
            entry[0] += 1.0 / (offset + rank)
            entry[1].add(name)
            rank += 1
    ordered = sorted(fused.items(), key=lambda row: (_tier_rank(allowed, row[0]), -row[1][0], row[0]))[:top_n]
    return [(identity, round(score, 5), sorted(modes)) for identity, (score, modes) in ordered]


def fuse(pools, allowed, policy, top_n):
    """Reciprocal rank fusion over the authorized candidates only, as `Retriever.search` fuses.

    A lexical-only request may apply its policy's query-local relevance floor
    first. Under the strict tier order, verified items come before community
    items among relevant authorized candidates and the fused score orders each
    tier. Under a bounded tier boost, a lexical-only request ranks by boosted
    lexical score and the tier only breaks ties. If a candidate ranking engine
    raises an unexpected runtime error (excluding `ServiceRuntimeError`
    refusals), Stage 4 safety fallback answers with `_strict_fuse`. `allowed`
    maps identities to the provisioning authority's rows. No other identity
    contributes to the floor, the order or a returned score.
    """
    try:
        floor = lexical_relevance_floor(pools, allowed, policy)
        active = ({LEXICAL_MODE: [(identity, score) for identity, score in pools[LEXICAL_MODE]
                                  if identity in allowed and score >= floor]}
                  if floor is not None else pools)
        boosted = bounded_tier_boost(active, allowed, policy)
        if boosted is not None:
            active = {LEXICAL_MODE: boosted}
        fused = {}
        for name, rows in active.items():
            rank = 0
            for identity, _score in rows:
                if identity not in allowed:
                    continue
                entry = fused.setdefault(identity, [0.0, set()])
                entry[0] += 1.0 / (policy.reciprocal_rank_offset + rank)
                entry[1].add(name)
                rank += 1

        if boosted is None:
            def order(row):
                return (_tier_rank(allowed, row[0]), -row[1][0], row[0])
        else:
            def order(row):
                return (-row[1][0], _tier_rank(allowed, row[0]), row[0])
        ordered = sorted(fused.items(), key=order)[:top_n]
        return [(identity, round(score, 5), sorted(modes)) for identity, (score, modes) in ordered]
    except ServiceRuntimeError:
        raise
    except Exception:
        return _strict_fuse(pools, allowed, policy, top_n)


def authorized_hits(view, fields, authorize, *, community_items=None):
    """Rank in the view's index, keep what `authorize` returns, and widen the pool until it is full.

    `authorize` receives candidate identities and returns the provisioning rows
    the caller may see. Filters are checked against the view's schema before
    anything is ranked, so an undeclared or internal attribute is refused
    without touching the index.
    """
    index = view.search_index()
    conditions = list(view.schema.filter_request(fields.get("filters")))
    if community_items == COMMUNITY_EXCLUDED and getattr(index, "tier_filter_complete", False) is True:
        conditions.append((TIER_ATTRIBUTE["name"], "any_of", (VERIFIED_TIER,)))
    eligible = index.eligible(conditions) if conditions else None
    top_n, mode = fields.get("top_n", 10), fields.get("mode", LEXICAL_MODE)
    policy = select_ranking_engine(fields.get("ranking_policy", index.policy))
    if hasattr(policy, "for_query"):
        policy = policy.for_query(fields["query"])
    pool = candidate_pool_size(policy, top_n, mode)
    from .catalogue_index_engines import index_size
    total = max(1, index_size(index))
    supplement = []
    tier_multiplier = getattr(policy, "lexical_tier_pool_multiplier", 0)
    if (mode == LEXICAL_MODE and community_items != COMMUNITY_EXCLUDED and tier_multiplier
            and getattr(index, "tier_filter_complete", False) is True):
        # The existing review-tier preference is applied after relevance and authorization. Give its tier a
        # bounded candidate pool so a large Community addition cannot crowd it out before either check.
        # Intersect with every caller filter. The checked projection is not permission to return any item.
        tier_conditions = [*conditions, (TIER_ATTRIBUTE["name"], "any_of", (VERIFIED_TIER,))]
        extra, _ = index.rank(fields["query"], mode=mode, pool=max(1, top_n * tier_multiplier),
                              eligible=index.eligible(tier_conditions))
        supplement = extra.get(LEXICAL_MODE, [])
    while True:
        pools, exhausted = index.rank(fields["query"], mode=mode, pool=pool, eligible=eligible)
        primary_lexical = pools.get(LEXICAL_MODE, [])
        if supplement:
            merged = dict(primary_lexical)
            for identity, score in supplement:
                if identity in merged and merged[identity] != score:
                    raise ServiceRuntimeError("search_index_unavailable", "one lexical index returned conflicting scores")
                merged[identity] = score
            pools = {**pools, LEXICAL_MODE: sorted(merged.items(), key=lambda row: (-row[1], row[0]))}
        candidates = tuple(dict.fromkeys(identity for rows in pools.values() for identity, _score in rows))
        rows = authorize(candidates) if candidates else {}
        hits = fuse(pools, rows, policy, top_n)
        floor = lexical_relevance_floor(pools, rows, policy)
        # A best-first lexical pool that already reaches below the floor cannot gain another qualifying
        # candidate by widening. If nothing was authorized, keep widening: a hidden high score sets no floor.
        below_floor = floor is not None and primary_lexical and primary_lexical[-1][1] < floor
        if len(hits) >= top_n or exhausted or pool >= total or below_floor:
            verbose = len(_TOKEN.findall((fields["query"] or "").lower())) > LEXICAL_TERMS
            sparse = len(primary_lexical) <= 2 and not supplement
            if mode == LEXICAL_MODE and getattr(policy, "enable_query_fallback", False) and (not hits or verbose or sparse):
                fb_pools, _stages = rank_with_fallbacks(index, fields["query"], pool=max(pool, 100), eligible=eligible)
                if fb_pools.get(LEXICAL_MODE):
                    combined = {} if verbose else dict(pools.get(LEXICAL_MODE, ()))
                    for identity, score in fb_pools[LEXICAL_MODE]:
                        if identity not in combined or score > combined[identity]:
                            combined[identity] = score
                    fb_merged = {LEXICAL_MODE: sorted(combined.items(), key=lambda row: (-row[1], row[0]))}
                    fb_candidates = tuple(identity for identity, _score in fb_merged[LEXICAL_MODE])
                    fb_rows = authorize(fb_candidates) if fb_candidates else {}
                    if fb_rows:
                        rows = {**rows, **fb_rows}
                        hits = fuse(fb_merged, rows, policy, top_n)
            return hits, rows
        pool = min(total, pool * 4)
