"""Exact statistical n-gram materialization for bounded retrieval.

This module is additive to :mod:`loop_engine.core.retrieval`. It does not
replace the Retrieval Engine or register a second search authority. Character
and word n-grams are external retrieval materializations. They are not model
internals, and frequency is ranking evidence rather than intelligence truth.

The index is passive state. ``build_index_as_loop`` and ``query_as_loop`` are
the governed operation wrappers for callers that need independent Loop and
Run History identity.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass


NGRAM_SCHEMA_VERSION = "1.0.0"
RESULT_PRECISIONS = ("exact", "approximate")
_UNITS = ("character", "word")
_SCOPE_PATTERN = re.compile(r"[A-Za-z0-9_.:/-]+")
_SEMVER_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _sha256(value: object) -> str:
    body = value if isinstance(value, str) else _canonical_json(value)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _percent(value: float) -> float:
    return round(float(value), 12)


class NgramRetrievalError(ValueError):
    """An n-gram definition, document, query, or score is invalid."""


@dataclass(frozen=True)
class NgramSpaceDefinition:
    """Versioned identity for one exact lexical n-gram space.

    Every setting that can change term identity is pinned. ``hash_algorithm``
    applies to definition, document, and index digests. Posting keys remain
    exact UTF-8 strings and are never mapped into hash buckets.
    """

    space_id: str = "core.ngram_space.lexical"
    version: str = NGRAM_SCHEMA_VERSION
    artifact_family: str = "external_retrieval_materialization"
    unit_types: tuple[str, ...] = _UNITS
    character_n_range: tuple[int, int] = (3, 5)
    word_n_range: tuple[int, int] = (1, 2)
    unicode_normalization: str = "NFKC"
    case_normalization: str = "casefold"
    tokenizer: str = "unicode_alnum_v1"
    language: str = "und"
    identifier_splitting: str = "camel_snake_hyphen_v1"
    punctuation: str = "replace_with_space"
    character_boundaries: str = "token_markers_v1"
    posting_key_encoding: str = "utf-8"
    posting_key_mode: str = "exact_strings"
    hash_algorithm: str = "sha256"
    hash_seed: str = "none"
    weighting: str = "sublinear_tf_idf_cosine_v1"
    approximation: str = "none_exact"

    def __post_init__(self) -> None:
        if not self.space_id.strip():
            raise NgramRetrievalError("space_id must be non-empty")
        if not _SEMVER_PATTERN.fullmatch(self.version):
            raise NgramRetrievalError("version must use MAJOR.MINOR.PATCH")
        if tuple(self.unit_types) != _UNITS:
            raise NgramRetrievalError(
                "this exact implementation requires character and word units")
        object.__setattr__(self, "unit_types", tuple(self.unit_types))
        for name in ("character_n_range", "word_n_range"):
            value = tuple(getattr(self, name))
            if (len(value) != 2 or any(not isinstance(item, int) for item in value)
                    or value[0] < 1 or value[0] > value[1]):
                raise NgramRetrievalError(
                    f"{name} must be an increasing pair of positive integers")
            object.__setattr__(self, name, value)
        required = {
            "artifact_family": "external_retrieval_materialization",
            "unicode_normalization": "NFKC",
            "case_normalization": "casefold",
            "tokenizer": "unicode_alnum_v1",
            "identifier_splitting": "camel_snake_hyphen_v1",
            "punctuation": "replace_with_space",
            "character_boundaries": "token_markers_v1",
            "posting_key_encoding": "utf-8",
            "posting_key_mode": "exact_strings",
            "hash_algorithm": "sha256",
            "hash_seed": "none",
            "weighting": "sublinear_tf_idf_cosine_v1",
            "approximation": "none_exact",
        }
        for name, expected in required.items():
            if getattr(self, name) != expected:
                raise NgramRetrievalError(
                    f"unsupported {name}: expected {expected!r}")

    def definition_payload(self) -> dict:
        return {
            "space_id": self.space_id,
            "version": self.version,
            "artifact_family": self.artifact_family,
            "unit_types": list(self.unit_types),
            "character_n_range": list(self.character_n_range),
            "word_n_range": list(self.word_n_range),
            "unicode_normalization": self.unicode_normalization,
            "case_normalization": self.case_normalization,
            "tokenizer": self.tokenizer,
            "language": self.language,
            "identifier_splitting": self.identifier_splitting,
            "punctuation": self.punctuation,
            "character_boundaries": self.character_boundaries,
            "posting_key_encoding": self.posting_key_encoding,
            "posting_key_mode": self.posting_key_mode,
            "hash_algorithm": self.hash_algorithm,
            "hash_seed": self.hash_seed,
            "weighting": self.weighting,
            "approximation": self.approximation,
        }

    @property
    def definition_digest(self) -> str:
        return _sha256(self.definition_payload())

    @property
    def space_ref(self) -> str:
        return f"{self.space_id}@{self.version}#{self.definition_digest}"

    def to_dict(self) -> dict:
        return {**self.definition_payload(),
                "definition_digest": self.definition_digest,
                "space_ref": self.space_ref}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "NgramSpaceDefinition":
        if not isinstance(value, Mapping):
            raise NgramRetrievalError("n-gram space must be an object")
        declared = str(value.get("definition_digest", ""))
        allowed = set(cls().__dict__) | {"definition_digest", "space_ref"}
        unknown = set(value) - allowed
        if unknown:
            raise NgramRetrievalError(
                "unknown n-gram space fields: " + ", ".join(sorted(unknown)))
        kwargs = {key: value[key] for key in cls().__dict__ if key in value}
        for name in ("unit_types", "character_n_range", "word_n_range"):
            if name in kwargs:
                kwargs[name] = tuple(kwargs[name])
        result = cls(**kwargs)
        if declared and declared != result.definition_digest:
            raise NgramRetrievalError(
                "n-gram space definition_digest does not match its fields")
        return result


@dataclass(frozen=True)
class NgramDocument:
    """A small searchable card used to build the external materialization."""

    document_id: str
    text: str
    scope: str
    source_ref: str = ""
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.document_id, str) or not self.document_id.strip():
            raise NgramRetrievalError("document_id must be non-empty")
        if not isinstance(self.text, str):
            raise NgramRetrievalError("document text must be a string")
        if not isinstance(self.scope, str) or not _SCOPE_PATTERN.fullmatch(
                self.scope):
            raise NgramRetrievalError(
                "scope must use letters, numbers, dot, colon, slash, or hyphen")
        tags = tuple(self.tags)
        if any(not isinstance(tag, str) or not tag for tag in tags):
            raise NgramRetrievalError("tags must be non-empty strings")
        object.__setattr__(self, "tags", tags)

    @property
    def content_digest(self) -> str:
        return _sha256(self.text)

    def manifest_entry(self) -> dict:
        return {"document_id": self.document_id, "scope": self.scope,
                "source_ref": self.source_ref, "tags": list(self.tags),
                "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "NgramDocument":
        return cls(str(value.get("document_id", "")),
                   str(value.get("text", "")),
                   str(value.get("scope", "")),
                   str(value.get("source_ref", "")),
                   tuple(value.get("tags", ())))


@dataclass(frozen=True)
class FusionPolicy:
    """Explainable weights for exact n-grams and supplied score channels."""

    policy_id: str = "core.ngram_fusion.explainable"
    version: str = NGRAM_SCHEMA_VERSION
    character_weight: float = 0.45
    word_weight: float = 0.45
    lexical_weight: float = 0.05
    semantic_weight: float = 0.05
    external_score_normalization: str = "min_max_v1"
    normalize_active_weights: bool = True

    def __post_init__(self) -> None:
        if not self.policy_id.strip() or not _SEMVER_PATTERN.fullmatch(self.version):
            raise NgramRetrievalError("fusion policy needs an ID and semver")
        weights = self.weights()
        if any(not math.isfinite(value) or value < 0
               for value in weights.values()):
            raise NgramRetrievalError("fusion weights must be finite and non-negative")
        if weights["character"] + weights["word"] <= 0:
            raise NgramRetrievalError("at least one n-gram weight must be positive")
        if self.external_score_normalization != "min_max_v1":
            raise NgramRetrievalError("only min_max_v1 normalization is implemented")

    def weights(self) -> dict[str, float]:
        return {"character": float(self.character_weight),
                "word": float(self.word_weight),
                "lexical": float(self.lexical_weight),
                "semantic": float(self.semantic_weight)}

    @property
    def content_digest(self) -> str:
        return _sha256({"policy_id": self.policy_id, "version": self.version,
                        "weights": self.weights(),
                        "external_score_normalization":
                            self.external_score_normalization,
                        "normalize_active_weights":
                            self.normalize_active_weights})


@dataclass(frozen=True)
class NgramQueryRequest:
    """Passive input contract for one exact n-gram query."""

    query: str
    allowed_scopes: tuple[str, ...] | None = None
    top_k: "int | None" = None
    lexical_scores: Mapping[str, float] | None = None
    semantic_scores: Mapping[str, float] | None = None
    fusion_policy: FusionPolicy | None = None
    approximate: bool = False


@dataclass(frozen=True)
class DocumentSimilarityRequest:
    """Passive input contract for one judged document-pair comparison."""

    left_id: str
    right_id: str
    allowed_scopes: tuple[str, ...] | None = None
    fusion_policy: FusionPolicy | None = None


@dataclass(frozen=True)
class NgramIndexBuildRequest:
    """Passive input contract for one exact index build."""

    documents: tuple[NgramDocument, ...]
    space: NgramSpaceDefinition | None = None


@dataclass(frozen=True)
class GovernedNgramQueryRequest:
    """Index plus typed query contract for one governed retrieval operation."""

    index: "NgramIndex"
    query: NgramQueryRequest


@dataclass(frozen=True)
class NgramLoopContext:
    """Optional ownership context for a governed n-gram operation."""

    parent: object | None = None
    ledger: object | None = None


@dataclass(frozen=True)
class NgramLoopOperation:
    """Passive role and relationship contract for one operation wrapper."""

    objective: str
    role: str
    profile_id: str
    relationship_kind: str


@dataclass(frozen=True)
class NgramHit:
    """One body-free ranked reference with an exact score explanation."""

    document_id: str
    scope: str
    score: float
    score_contributions: Mapping[str, Mapping[str, float]]
    top_matching_grams: tuple[Mapping[str, object], ...] = ()
    result_precision: str = "exact"

    def to_dict(self) -> dict:
        return {"document_id": self.document_id, "scope": self.scope,
                "score": self.score,
                "score_contributions": {
                    key: dict(value)
                    for key, value in self.score_contributions.items()},
                "top_matching_grams": [dict(value)
                                       for value in self.top_matching_grams],
                "result_precision": self.result_precision,
                "body_materialized": False}


@dataclass(frozen=True)
class NgramQueryResult:
    """Typed exact retrieval result. It does not claim record truth."""

    query: str
    allowed_scopes: tuple[str, ...]
    index_digest: str
    space_ref: str
    fusion_policy_digest: str
    eligible_document_count: int
    excluded_by_scope_count: int
    candidate_count: int
    hits: tuple[NgramHit, ...]
    result_precision: str = "exact"
    approximation: None = None
    record_type: str = "ngram_retrieval_result/v1"

    def to_dict(self) -> dict:
        return {"record_type": self.record_type, "query": self.query,
                "allowed_scopes": list(self.allowed_scopes),
                "index_digest": self.index_digest,
                "space_ref": self.space_ref,
                "fusion_policy_digest": self.fusion_policy_digest,
                "eligible_document_count": self.eligible_document_count,
                "excluded_by_scope_count": self.excluded_by_scope_count,
                "candidate_count": self.candidate_count,
                "hits": [hit.to_dict() for hit in self.hits],
                "result_precision": self.result_precision,
                "approximation": self.approximation,
                "evidence_boundary": (
                    "ranking evidence only; not intelligence truth"),
                "implementation_boundary": (
                    "external retrieval materialization; not model-internal "
                    "learned n-gram embeddings")}


def normalize_text(text: str, space: NgramSpaceDefinition) -> str:
    """Normalize text according to the pinned space definition."""
    if not isinstance(text, str):
        raise NgramRetrievalError("text must be a string")
    value = unicodedata.normalize(space.unicode_normalization, text)
    value = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = value.replace("_", " ").replace("-", " ")
    value = value.casefold()
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    value = value.replace("_", " ")
    return " ".join(value.split())


def tokenize(text: str, space: NgramSpaceDefinition) -> tuple[str, ...]:
    """Return tokens for the pinned ``unicode_alnum_v1`` tokenizer."""
    return tuple(re.findall(r"[^\W_]+", normalize_text(text, space),
                            flags=re.UNICODE))


def ngram_counts(text: str, space: NgramSpaceDefinition) -> dict[str, Counter]:
    """Return exact character and word n-gram term frequencies."""
    tokens = tokenize(text, space)
    character: Counter[str] = Counter()
    word: Counter[str] = Counter()
    for token in tokens:
        padded = f"^{token}$"
        for n in range(space.character_n_range[0],
                       space.character_n_range[1] + 1):
            for offset in range(max(0, len(padded) - n + 1)):
                character[f"{n}:{padded[offset:offset + n]}"] += 1
    for n in range(space.word_n_range[0], space.word_n_range[1] + 1):
        for offset in range(max(0, len(tokens) - n + 1)):
            word[f"{n}:{' '.join(tokens[offset:offset + n])}"] += 1
    return {"character": character, "word": word}


class NgramIndex:
    """Exact inverted index over character and word n-grams.

    No sketch or approximate nearest-neighbor structure is implemented. A
    request for approximate results fails explicitly.
    """

    def __init__(self, documents: Sequence[NgramDocument], *,
                 space: NgramSpaceDefinition | None = None):
        self.space = space or NgramSpaceDefinition()
        self._documents = tuple(documents)
        ids = [document.document_id for document in self._documents]
        if len(ids) != len(set(ids)):
            raise NgramRetrievalError("document_id values must be unique")
        self._by_id = {document.document_id: document
                       for document in self._documents}
        self._grams: dict[str, dict[str, Counter[str]]] = {}
        self._postings: dict[str, dict[str, dict[str, int]]] = {
            unit: defaultdict(dict) for unit in _UNITS}
        self._collection_frequency: dict[str, Counter[str]] = {
            unit: Counter() for unit in _UNITS}
        self._document_frequency: dict[str, Counter[str]] = {
            unit: Counter() for unit in _UNITS}
        for document in self._documents:
            counts = ngram_counts(document.text, self.space)
            self._grams[document.document_id] = counts
            for unit in _UNITS:
                self._collection_frequency[unit].update(counts[unit])
                self._document_frequency[unit].update(counts[unit].keys())
                for term, frequency in counts[unit].items():
                    self._postings[unit][term][document.document_id] = frequency
        self.index_digest = _sha256({
            "space_ref": self.space.space_ref,
            "documents": [document.manifest_entry()
                          for document in sorted(
                              self._documents, key=lambda item: item.document_id)],
        })

    @property
    def document_count(self) -> int:
        return len(self._documents)

    def manifest(self) -> dict:
        posting_count = sum(len(posting)
                            for unit in _UNITS
                            for posting in self._postings[unit].values())
        term_count = sum(len(self._postings[unit]) for unit in _UNITS)
        serialized = _canonical_json({
            "space_ref": self.space.space_ref,
            "documents": [document.manifest_entry()
                          for document in self._documents],
            "postings": {
                unit: {term: sorted(posting.items())
                       for term, posting in sorted(self._postings[unit].items())}
                for unit in _UNITS},
        }).encode("utf-8")
        return {"record_type": "ngram_index_manifest/v1",
                "index_digest": self.index_digest,
                "space": self.space.to_dict(),
                "result_precision": "exact", "approximation": None,
                "document_count": self.document_count,
                "term_count": term_count, "posting_count": posting_count,
                "serialized_index_size_bytes": len(serialized),
                "bodies_in_results": False}

    def _eligible_ids(self, allowed_scopes: Sequence[str] | None) -> tuple[str, ...]:
        if allowed_scopes is None:
            return tuple(sorted(self._by_id))
        scopes = tuple(allowed_scopes)
        if not scopes or any(not isinstance(scope, str)
                             or not _SCOPE_PATTERN.fullmatch(scope)
                             for scope in scopes):
            raise NgramRetrievalError(
                "allowed_scopes must contain valid exact scope names")
        return tuple(sorted(document_id for document_id, document
                            in self._by_id.items() if document.scope in scopes))

    @staticmethod
    def _idf(document_count: int, document_frequency: int) -> float:
        return math.log((document_count + 1) / (document_frequency + 1)) + 1.0

    def statistics(self, query: str, *,
                   allowed_scopes: Sequence[str] | None = None) -> dict:
        """Return exact query-term TF, DF, CF, and smoothed IDF."""
        eligible = set(self._eligible_ids(allowed_scopes))
        terms = ngram_counts(query, self.space)
        rows = []
        for unit in _UNITS:
            for term, query_tf in sorted(terms[unit].items()):
                posting = self._postings[unit].get(term, {})
                values = [frequency for document_id, frequency in posting.items()
                          if document_id in eligible]
                rows.append({"unit": unit, "term": term,
                             "query_term_frequency": query_tf,
                             "document_frequency": len(values),
                             "collection_frequency": sum(values),
                             "idf": _percent(self._idf(
                                 len(eligible), len(values))),
                             "result_precision": "exact"})
        return {"record_type": "ngram_statistics/v1",
                "index_digest": self.index_digest,
                "allowed_scopes": list(allowed_scopes or ()),
                "eligible_document_count": len(eligible),
                "result_precision": "exact", "approximation": None,
                "terms": rows}

    def _channel_scores(self, query_terms: Counter, unit: str,
                        eligible: set[str]) -> tuple[dict, dict]:
        if not query_terms or not eligible:
            return {}, {}
        document_count = len(eligible)
        idf: dict[str, float] = {}
        for term in self._postings[unit]:
            df = sum(1 for document_id in self._postings[unit][term]
                     if document_id in eligible)
            idf[term] = self._idf(document_count, df)
        query_weights = {
            term: (1.0 + math.log(frequency))
                  * idf.get(term, self._idf(document_count, 0))
            for term, frequency in query_terms.items()}
        query_norm = math.sqrt(sum(weight * weight
                                   for weight in query_weights.values())) or 1.0
        candidates = set()
        for term in query_terms:
            candidates.update(document_id
                              for document_id in self._postings[unit].get(term, {})
                              if document_id in eligible)
        scores: dict[str, float] = {}
        explanations: dict[str, list[dict]] = {}
        for document_id in candidates:
            document_terms = self._grams[document_id][unit]
            document_weights = {
                term: (1.0 + math.log(frequency)) * idf[term]
                for term, frequency in document_terms.items()}
            document_norm = math.sqrt(sum(weight * weight for weight
                                          in document_weights.values())) or 1.0
            contributions = []
            dot = 0.0
            for term, query_weight in query_weights.items():
                document_weight = document_weights.get(term, 0.0)
                if document_weight <= 0:
                    continue
                raw = query_weight * document_weight
                dot += raw
                contributions.append({
                    "unit": unit, "term": term,
                    "document_term_frequency": document_terms[term],
                    "query_term_frequency": query_terms[term],
                    "document_frequency": sum(
                        1 for item in self._postings[unit][term]
                        if item in eligible),
                    "idf": _percent(idf[term]),
                    "cosine_contribution": _percent(
                        raw / (query_norm * document_norm)),
                })
            scores[document_id] = dot / (query_norm * document_norm)
            explanations[document_id] = sorted(
                contributions,
                key=lambda item: (-item["cosine_contribution"], item["term"]))
        return scores, explanations

    def _normalize_external(self, scores: Mapping[str, float] | None,
                            eligible: set[str]) -> dict[str, float]:
        if scores is None:
            return {}
        unknown = set(scores) - set(self._by_id)
        if unknown:
            raise NgramRetrievalError(
                "external scores name unknown documents: "
                + ", ".join(sorted(unknown)))
        selected = {document_id: float(score)
                    for document_id, score in scores.items()
                    if document_id in eligible}
        if any(not math.isfinite(score) for score in selected.values()):
            raise NgramRetrievalError("external scores must be finite")
        if not selected:
            return {}
        low, high = min(selected.values()), max(selected.values())
        if high == low:
            value = 1.0 if high > 0 else 0.0
            return {document_id: value for document_id in selected}
        return {document_id: (score - low) / (high - low)
                for document_id, score in selected.items()}

    def query(self, request: NgramQueryRequest) -> NgramQueryResult:
        """Rank body-free references using exact, explainable score fusion."""
        if not isinstance(request, NgramQueryRequest):
            raise NgramRetrievalError("query needs NgramQueryRequest")
        if request.approximate:
            raise NotImplementedError(
                "approximate n-gram retrieval is not implemented or tested")
        query = request.query
        if not isinstance(query, str) or not query.strip():
            raise NgramRetrievalError("query must be a non-empty string")
        if (request.top_k is not None
                and (not isinstance(request.top_k, int)
                     or request.top_k < 1)):
            raise NgramRetrievalError(
                "top_k must be a positive integer when provided")
        policy = request.fusion_policy or FusionPolicy()
        eligible_tuple = self._eligible_ids(request.allowed_scopes)
        eligible = set(eligible_tuple)
        query_grams = ngram_counts(query, self.space)
        char_scores, char_explanations = self._channel_scores(
            query_grams["character"], "character", eligible)
        word_scores, word_explanations = self._channel_scores(
            query_grams["word"], "word", eligible)
        lexical = self._normalize_external(request.lexical_scores, eligible)
        semantic = self._normalize_external(request.semantic_scores, eligible)
        channels = {"character": char_scores, "word": word_scores,
                    "lexical": lexical, "semantic": semantic}
        candidates = set().union(*(set(values) for values in channels.values()))
        active = {"character", "word"}
        if request.lexical_scores is not None:
            active.add("lexical")
        if request.semantic_scores is not None:
            active.add("semantic")
        weights = policy.weights()
        denominator = (sum(weights[name] for name in active)
                       if policy.normalize_active_weights else 1.0) or 1.0
        hits = []
        for document_id in candidates:
            details: dict[str, dict[str, float]] = {}
            total = 0.0
            for name in ("character", "word", "lexical", "semantic"):
                raw = float(channels[name].get(document_id, 0.0))
                effective = weights[name] / denominator if name in active else 0.0
                weighted = raw * effective
                total += weighted
                details[name] = {"raw_score": _percent(raw),
                                 "effective_weight": _percent(effective),
                                 "weighted_score": _percent(weighted)}
            matching = (char_explanations.get(document_id, [])
                        + word_explanations.get(document_id, []))
            matching = sorted(
                matching,
                key=lambda item: (-item["cosine_contribution"],
                                  item["unit"], item["term"]))[:12]
            hits.append(NgramHit(
                document_id=document_id,
                scope=self._by_id[document_id].scope,
                score=_percent(total), score_contributions=details,
                top_matching_grams=tuple(matching)))
        hits.sort(key=lambda hit: (-hit.score, hit.document_id))
        scopes = tuple(request.allowed_scopes or ())
        return NgramQueryResult(
            query=query, allowed_scopes=scopes,
            index_digest=self.index_digest, space_ref=self.space.space_ref,
            fusion_policy_digest=policy.content_digest,
            eligible_document_count=len(eligible),
            excluded_by_scope_count=self.document_count - len(eligible),
            candidate_count=len(candidates), hits=tuple(
                hits if request.top_k is None else hits[:request.top_k]))

    def document_similarity(self, request: DocumentSimilarityRequest) -> float:
        """Return exact lexical similarity for a judged document pair."""
        if not isinstance(request, DocumentSimilarityRequest):
            raise NgramRetrievalError(
                "document_similarity needs DocumentSimilarityRequest")
        left_id, right_id = request.left_id, request.right_id
        if left_id == right_id:
            return 1.0
        if left_id not in self._by_id or right_id not in self._by_id:
            raise NgramRetrievalError("document similarity IDs must exist")
        eligible = set(self._eligible_ids(request.allowed_scopes))
        if left_id not in eligible or right_id not in eligible:
            raise NgramRetrievalError("document pair is outside allowed_scopes")
        policy = request.fusion_policy or FusionPolicy()
        weights = policy.weights()
        denominator = weights["character"] + weights["word"]
        score = 0.0
        for unit in ("character", "word"):
            query_terms = self._grams[left_id][unit]
            scores, _ = self._channel_scores(query_terms, unit, eligible)
            score += scores.get(right_id, 0.0) * weights[unit] / denominator
        return _percent(score)


def _operation_as_loop(request: NgramLoopOperation,
                       operation: Callable[[], object],
                       context: NgramLoopContext | None = None) -> dict:
    from ..loop.encapsulate import as_loop
    from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    from ..loop.recursive_loop import LoopLedger

    selected_context = context or NgramLoopContext()
    parent = selected_context.parent
    selected_ledger = (parent.ledger if parent is not None
                       else selected_context.ledger or LoopLedger())
    identity = LoopRoleIdentity(LoopRole(request.role), request.profile_id)
    if parent is None:
        relationship = LoopRelationship.starting()
    elif request.relationship_kind == "queried_by":
        relationship = LoopRelationship.queried_by(parent.loop_id)
    else:
        relationship = LoopRelationship.spawned_by(parent.loop_id)
    wrapped = as_loop(request.objective, operation, kind="callable", parent=parent,
                      ledger=selected_ledger, identity=identity,
                      relationship=relationship)
    if wrapped.get("error") is not None:
        raise wrapped["error"]
    return wrapped


def build_index_as_loop(request: NgramIndexBuildRequest,
                        context: NgramLoopContext | None = None) -> dict:
    """Build one exact index through a deterministic Practitioner Loop."""
    wrapped = _operation_as_loop(NgramLoopOperation(
        "build exact statistical n-gram retrieval materialization",
        "practitioner", "practitioner.code_execution", "spawned_by"),
        lambda: NgramIndex(request.documents, space=request.space), context)
    index = wrapped["value"]
    return {**wrapped, "manifest": index.manifest(), "index": index}


def query_as_loop(request: GovernedNgramQueryRequest,
                  context: NgramLoopContext | None = None) -> dict:
    """Query an exact index through a deterministic Intelligence Loop."""
    wrapped = _operation_as_loop(NgramLoopOperation(
        "query statistical n-gram materialization for "
        f"{request.query.query[:80]!r}", "intelligence",
        "intelligence.search", "queried_by"),
        lambda: request.index.query(request.query), context)
    result = wrapped["value"]
    return {**wrapped, "result": result, "result_record": result.to_dict()}


def self_test(frozen_fixture: str = "") -> dict:
    """Delegate deterministic contracts to the benchmark companion."""
    from .ngram_benchmark import run_contract_checks
    return run_contract_checks(frozen_fixture)


def _main() -> int:
    import sys
    result = self_test(sys.argv[1] if len(sys.argv) > 1 else "")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = (
    "FusionPolicy", "NGRAM_SCHEMA_VERSION", "NgramDocument", "NgramHit",
    "NgramIndex", "NgramQueryResult", "NgramRetrievalError",
    "NgramSpaceDefinition", "RESULT_PRECISIONS", "build_index_as_loop",
    "ngram_counts", "normalize_text", "query_as_loop", "self_test",
    "tokenize",
)
