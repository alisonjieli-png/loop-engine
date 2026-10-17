"""Swappable multi-engine pre-turn retrieval and adoption trigger for coding harnesses.

Kind: client-side and harness-hook pre-turn component (`engine_slot`:
`preturn_adoption_trigger`). It inspects a user prompt before a harness turn,
applies a seven-layer safety and frustration-avoidance envelope, reformulates
verbose or noisy prompts into concise 2 to 5 word technical domain queries, and
injects compact Baltor contract cards (at most 200 tokens) only when a
qualified capability clears the confidence threshold and declares no ungranted
step effects.

It performs no file writes, no shell execution, and no automatic body downloads
(`provisioning_read` is never called here).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
import math
import re
import sys
import time
from typing import Any, Callable

REQUEST_VERSION = "adoption_trigger_request/v1"
RESULT_VERSION = "adoption_trigger_result/v1"
REFUSAL_VERSION = "adoption_trigger_refusal/v1"

PROTOCOL_V1 = "1.0"
SUPPORTED_PROTOCOL_VERSIONS = (PROTOCOL_V1,)
SUPPORTED_CLIENT_PROFILES = ("claude-code", "codex", "opencode", "pi", "generic")

REFUSAL_INVALID_RECORD = "invalid_record_type"
REFUSAL_UNKNOWN_FIELD = "unknown_field_refused"
REFUSAL_INVALID_PROMPT = "invalid_prompt"
REFUSAL_SECRET_DETECTED = "secret_in_prompt_refused"
REFUSAL_UNSUPPORTED_PROTOCOL = "unsupported_protocol_version"
REFUSAL_UNSUPPORTED_PROFILE = "unsupported_client_profile"
REFUSAL_INVALID_BUDGET = "invalid_budget_parameter"
REFUSAL_UNKNOWN_ENGINE = "unknown_engine_id"

ABSTAIN_NONE = "none"
ABSTAIN_FRUSTRATION_COOLDOWN = "frustration_cooldown"
ABSTAIN_TRIVIAL_OR_OFFTOPIC = "trivial_or_offtopic_prompt"
ABSTAIN_BUDGET_EXHAUSTED = "call_budget_exhausted"
ABSTAIN_PASSIVE_BASELINE = "passive_baseline_no_preturn_action"
ABSTAIN_BELOW_THRESHOLD = "below_confidence_threshold"
ABSTAIN_ALL_SEEN = "all_matching_cards_already_seen"
ABSTAIN_UNDECLARED_EFFECTS = "undeclared_step_effects"

ENGINE_T0 = "T0_passive_baseline"
ENGINE_T1 = "T1_imperative_mcp_schema"
ENGINE_T2 = "T2_workspace_rules_layer"
ENGINE_T3 = "T3_keyword_ast_router"
ENGINE_T4 = "T4_tfidf_char_ngram_router"
ENGINE_T5 = "T5_minhash_lsh_fingerprint"
ENGINE_T6 = "T6_gated_preturn_card_injector"
ENGINE_T7 = "T7_hybrid_cascade_with_fallback"
ENGINE_T8 = "T8_ollama_micro_classifier"

ENGINE_IDS = (
    ENGINE_T0,
    ENGINE_T1,
    ENGINE_T2,
    ENGINE_T3,
    ENGINE_T4,
    ENGINE_T5,
    ENGINE_T6,
    ENGINE_T7,
    ENGINE_T8,
)

DEFAULT_FALLBACK_CHAIN = (
    ENGINE_T7,
    ENGINE_T6,
    ENGINE_T5,
    ENGINE_T4,
    ENGINE_T3,
)

PROBE_1_NAME = "probe_1_technical_phrases"
PROBE_2_NAME = "probe_2_synonym_expansion"
PROBE_3_NAME = "probe_3_lsh_band_expansion"
PROBE_4_NAME = "probe_4_safe_abstention"

ALLOWED_REQUEST_FIELDS = frozenset({
    "record_type",
    "protocol_version",
    "client_profile",
    "prompt",
    "engine_id",
    "fallback_chain",
    "confidence_threshold",
    "max_injected_tokens",
    "max_cards",
    "call_budget_remaining",
    "seen_identities",
    "turn_index",
    "consecutive_ignored_injections",
    "granted_step_effects",
    "lsh_bands",
    "lsh_rows",
    "simulated_faults",
    "allow_live_model",
    "model_classifier_fn",
    "catalogue_items",
})

DEFAULT_STEP_EFFECT_GRANTS = ("reads_fs",)

_SECRET_SCAN_PATTERNS = (
    re.compile(r"\bbsk_[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+[A-Za-z0-9._-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)

_FRUSTRATION_PATTERNS = (
    re.compile(r"(?i)\b(?:stop|do\s+not|don't|never)\s+(?:suggesting|using|calling|searching|injecting)\s+baltor\b"),
    re.compile(r"(?i)\bignore\s+(?:the\s+)?(?:baltor|library|catalogue|catalog|contract\s+cards?)\b"),
    re.compile(r"(?i)\bno\s+(?:more\s+)?(?:baltor|library\s+search|contract\s+cards?)\b"),
    re.compile(r"(?i)\bstop\s+injecting\b"),
)

_TRACEBACK_LINE_RE = re.compile(
    r"(?m)^(?:\s*Traceback \(most recent call last\):.*|"
    r"\s*File \"[^\"]+\", line \d+.*|"
    r"\s+at [A-Za-z0-9_.$<>]+\([^)]*\).*|"
    r"\s*(?:ValueError|TypeError|KeyError|RuntimeError|AttributeError|IndexError|ZeroDivisionError):.*)$"
)
_FENCED_BLOCK_RE = re.compile(r"```[\s\S]*?```")
_PATH_TOKEN_RE = re.compile(r"(?:^|\s)(?:/[A-Za-z0-9._/-]+|\.{1,2}/[A-Za-z0-9._/-]+|[A-Za-z0-9_-]+/[A-Za-z0-9._/-]+\.[A-Za-z0-9]+)")
_PROJECT_NOISE_RE = re.compile(
    r"(?i)\b(?:spaceship\s+titanic|titanic\s+competition|house\s+prices\s+competition|"
    r"project\s+apollo|acme\s+corp|kaggle\s+competition|my\s+homework|assignment\s+\d+)\b"
)
_GENERIC_META_VERBS_RE = re.compile(
    r"(?i)\b(?:recreate\s+a\s+class|write\s+a\s+class|implement\s+a\s+function|"
    r"create\s+a\s+module|can\s+you\s+help\s+me|please\s+write|from\s+scratch|"
    r"in\s+python\s+without\s+external\s+dependencies)\b"
)

_TRIVIAL_OR_OFFTOPIC_PATTERNS = (
    re.compile(r"(?i)^\s*(?:rename|change\s+the\s+name\s+of)\s+(?:variable|function|method|parameter)\s+[A-Za-z0-9_]+\s+to\s+[A-Za-z0-9_]+\s*[.?!]?\s*$"),
    re.compile(r"(?i)^\s*fix\s+(?:the\s+)?(?:spelling|typo)\b"),
    re.compile(r"(?i)^\s*(?:bump|update)\s+(?:the\s+)?version\s+(?:number|string)\b"),
    re.compile(r"(?i)^\s*add\s+a\s+(?:docstring|comment|blank\s+line)\b"),
    re.compile(r"(?i)^\s*what\s+is\s+\d+\s*[+*/-]\s*\d+"),
    re.compile(r"(?i)\b(?:sourdough\s+bread|chocolate\s+cake\s+recipe|write\s+a\s+haiku|write\s+a\s+sonnet|weather\s+in\s+boston|capital\s+of\s+france)\b"),
)

_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "can", "code",
    "Could", "could", "create", "do", "does", "for", "from", "function", "get",
    "have", "help", "how", "i", "if", "in", "into", "is", "it", "its", "just",
    "like", "make", "me", "method", "module", "my", "need", "new", "of", "on",
    "or", "our", "out", "please", "project", "python", "should", "so", "some",
    "that", "the", "their", "them", "then", "there", "these", "this", "to",
    "use", "using", "want", "we", "what", "when", "where", "which", "with",
    "without", "work", "write", "you", "your",
})


@dataclass(frozen=True)
class CapabilityEntry:
    """One capability card in the pre-turn index."""

    identity: str
    kind: str
    library_tier: str
    purpose: str
    body_digest: str
    declared_effects: tuple[str, ...]
    canonical_query: str
    domain_tags: tuple[str, ...]
    ast_symbols: tuple[str, ...]
    synonyms: tuple[str, ...]


DEFAULT_CAPABILITY_CATALOGUE: tuple[CapabilityEntry, ...] = (
    CapabilityEntry(
        identity="audit_data_splits_for_errors_and_leakage",
        kind="skill",
        library_tier="verified",
        purpose=(
            "Audit train, validation and test splits for target leakage, group overlap, "
            "temporal lookahead, duplicate rows and preprocessing fit before splitting."
        ),
        body_digest="e373a8b5fb740744fc541f57770d2332a0db773a5ebba495d1ef48c383281d7a",
        declared_effects=("reads_fs",),
        canonical_query="data split leakage audit",
        domain_tags=(
            "data split", "target leakage", "group overlap", "cross validation",
            "stratified split", "temporal leakage", "train test contamination",
            "duplicate entity", "preprocessing leakage", "fold validation",
        ),
        ast_symbols=(
            "StratifiedKFold", "GroupKFold", "TimeSeriesSplit", "train_test_split",
            "fit_transform", "passenger_group", "group_id",
        ),
        synonyms=(
            "same group in train and val", "shared household across folds",
            "scaler fit on full dataset", "future rows in training fold",
            "contaminating validation split", "verify split integrity",
        ),
    ),
    CapabilityEntry(
        identity="read_the_train_validation_gap",
        kind="skill",
        library_tier="verified",
        purpose=(
            "Diagnose overfitting, underfitting, regularization strength and learning-curve "
            "divergence from the gap between training and validation loss or accuracy."
        ),
        body_digest="97fb6aa31400c35a68ff5a7fb8788687f0007200926149b1eb65258d7a6458cb",
        declared_effects=("reads_fs",),
        canonical_query="train validation gap",
        domain_tags=(
            "train validation gap", "overfitting diagnosis", "underfitting",
            "learning curve", "generalization gap", "validation loss rising",
            "regularization tuning", "early stopping", "bias variance tradeoff",
        ),
        ast_symbols=(
            "val_loss", "train_loss", "learning_curve", "EarlyStopping",
            "weight_decay", "dropout",
        ),
        synonyms=(
            "training loss drops while validation loss increases",
            "memorizing training examples", "high variance across epochs",
            "diagnose why validation score plateaus early",
        ),
    ),
    CapabilityEntry(
        identity="choose_metrics_by_task_type_and_industry",
        kind="skill",
        library_tier="verified",
        purpose=(
            "Select evaluation metrics, calibration checks and decision thresholds for "
            "imbalanced classification, ranking, regression and cost-sensitive tasks."
        ),
        body_digest="01a4ab3cd62f1ebdc9d4fc242efbc23295d6e8f1bf9d1187d76819c7e4e2a101",
        declared_effects=("reads_fs",),
        canonical_query="choose evaluation metrics imbalanced",
        domain_tags=(
            "evaluation metrics", "imbalanced classification", "precision recall auc",
            "roc auc", "f1 score", "brier score", "calibration curve",
            "cost sensitive threshold", "ranking ndcg", "false positive cost",
        ),
        ast_symbols=(
            "roc_auc_score", "average_precision_score", "f1_score",
            "precision_recall_curve", "brier_score_loss", "confusion_matrix",
        ),
        synonyms=(
            "pick metric for rare event fraud detection",
            "accuracy is 99 percent on 1 percent positive class",
            "trade off false alarms against missed detections",
            "probability calibration and threshold selection",
        ),
    ),
    CapabilityEntry(
        identity="ttl_lru_cache_with_monotonic_clock",
        kind="code_asset",
        library_tier="verified",
        purpose=(
            "Deterministic time-aware LRU cache with per-entry TTL expiration, injectable "
            "monotonic clock, O(1) eviction of expired keys before capacity eviction, and hit/miss stats."
        ),
        body_digest="4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
        declared_effects=("reads_fs",),
        canonical_query="ttl lru cache expiration",
        domain_tags=(
            "ttl cache", "lru cache", "time aware cache", "cache expiration",
            "monotonic clock", "evict expired entries", "least recently used",
            "bounded memory cache", "hit miss statistics",
        ),
        ast_symbols=(
            "OrderedDict", "move_to_end", "popitem", "monotonic",
            "TTLCache", "LRUCache", "cache_stats",
        ),
        synonyms=(
            "expire cached items after n seconds",
            "in-memory key value store with time to live and max capacity",
            "evict stale entries before evicting oldest accessed key",
            "injectable timer for deterministic cache tests",
        ),
    ),
    CapabilityEntry(
        identity="sql_where_clause_recursive_descent_parser",
        kind="code_asset",
        library_tier="verified",
        purpose=(
            "Safe recursive-descent tokenizer and AST evaluator for SQL WHERE filter "
            "predicates supporting AND, OR, NOT, parentheses, IN lists, LIKE and NULL checks."
        ),
        body_digest="7c83910b6a55e8a2f79d4b0f3e19c56072f8b04d1a3d8d6f9e20c45018b3a912",
        declared_effects=("reads_fs",),
        canonical_query="sql where clause parser",
        domain_tags=(
            "sql where parser", "recursive descent parser", "boolean predicate ast",
            "filter expression tokenizer", "operator precedence", "in list predicate",
            "is null check", "like pattern matching",
        ),
        ast_symbols=(
            "tokenize_where", "parse_expression", " parse_and", "parse_or",
            "PredicateNode", "evaluate_row",
        ),
        synonyms=(
            "parse boolean filter strings against dictionary rows",
            "safe query expression evaluator without eval",
            "nested parentheses with and or not precedence",
        ),
    ),
    CapabilityEntry(
        identity="procedural_pbr_greeble_shader_3d",
        kind="skill",
        library_tier="verified",
        purpose=(
            "Generate procedural 3D PBR hull panels, normal-mapped greeble detail, "
            "signed-distance bevels and glTF/Three.js shader materials for sci-fi or CAD scenes."
        ),
        body_digest="82a20d2666e51c6be46050ef5ff8a20b56d236704e42df056ffea9c6fb862994",
        declared_effects=("reads_fs",),
        canonical_query="procedural 3d shader greeble",
        domain_tags=(
            "procedural 3d shader", "pbr material", "greeble panel", "threejs glsl",
            "signed distance field", "normal map generation", "gltf mesh material",
            "metallic roughness", "vertex displacement",
        ),
        ast_symbols=(
            "ShaderMaterial", "MeshStandardMaterial", "GLTFExporter",
            "fragmentShader", "vertexShader", "roughnessMap",
        ),
        synonyms=(
            "sci fi hull paneling shader in three.js",
            "parametric surface detail and bevel normal map",
            "glsl fragment shader for procedural metal plates",
        ),
    ),
    CapabilityEntry(
        identity="token_bucket_rate_limiter_sliding_window",
        kind="code_asset",
        library_tier="verified",
        purpose=(
            "Deterministic token-bucket and sliding-window rate limiter with burst allowance, "
            "per-tenant quotas, retry-after calculation and injectable clock."
        ),
        body_digest="5f9c4e18b2d40a71c36e9812b04d73a91c82f1047b6e35d28a901c4f6b2e8301",
        declared_effects=("reads_fs",),
        canonical_query="token bucket rate limiter",
        domain_tags=(
            "rate limiter", "token bucket", "sliding window", "burst capacity",
            "retry after seconds", "request throttling", "per tenant quota",
        ),
        ast_symbols=(
            "TokenBucket", "SlidingWindowLimiter", "retry_after",
            "allow_request", "refill_rate",
        ),
        synonyms=(
            "throttle incoming api requests with burst limit",
            "compute wait time when request quota is exhausted",
            "per key rate limiting with deterministic clock",
        ),
    ),
    CapabilityEntry(
        identity="dag_topological_sort_cycle_detector",
        kind="code_asset",
        library_tier="verified",
        purpose=(
            "Deterministic topological sort, cycle path reporting and parallel wave "
            "scheduling for directed acyclic dependency graphs."
        ),
        body_digest="3d18a90f4c27e61b8509a2d3f4c17e82b6059d14a3e72c81f5046b93e2d18c74",
        declared_effects=("reads_fs",),
        canonical_query="dag topological sort cycle",
        domain_tags=(
            "topological sort", "directed acyclic graph", "cycle detection",
            "dependency resolution", "kahn algorithm", "parallel execution waves",
        ),
        ast_symbols=(
            "topological_sort", "find_cycle_path", "in_degree",
            "DependencyGraph", "CircularDependencyError",
        ),
        synonyms=(
            "order build steps by dependencies and detect circular references",
            "schedule tasks in dependency waves",
            "report exact cycle chain when graph is not a dag",
        ),
    ),
    CapabilityEntry(
        identity="live_network_webhook_dispatcher",
        kind="code_asset",
        library_tier="community",
        purpose="Dispatch outbound HTTP webhooks with HMAC signatures and exponential backoff.",
        body_digest="9a02b84c61d3e57f8201a4b6c9d2e3f405162738495a6b7c8d9e0f1a2b3c4d5e",
        declared_effects=("reads_fs", "network"),
        canonical_query="outbound webhook hmac dispatcher",
        domain_tags=("webhook dispatcher", "outbound http", "hmac signature"),
        ast_symbols=("dispatch_webhook", "hmac_sha256"),
        synonyms=("send signed http post callbacks to remote endpoints",),
    ),
)


def _stem_token(word: str) -> str:
    """Lightweight deterministic stemmer for English technical terms."""
    token = word.lower().strip("_-")
    if len(token) <= 3:
        return token
    for suffix, replacement in (
        ("ization", "ize"),
        ("ational", "ate"),
        ("fulness", "ful"),
        ("ousness", "ous"),
        ("iveness", "ive"),
        ("ing", ""),
        ("edly", ""),
        ("ed", ""),
        ("ies", "y"),
        ("es", ""),
        ("s", ""),
    ):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            token = token[: -len(suffix)] + replacement
            break
    return token


def _blake64(text: str, seed: int = 0) -> int:
    digest = hashlib.blake2b(
        text.encode("utf-8", errors="ignore"),
        digest_size=8,
        person=seed.to_bytes(8, "little", signed=False),
    ).digest()
    return int.from_bytes(digest, "little", signed=False)


def extract_multi_granular_shingles(text: str) -> set[str]:
    """Extract word stems, technical bigrams, char 3/4-grams, and AST/CamelCase tokens."""
    shingles: set[str] = set()
    camel_parts = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b", text)
    for ident in camel_parts:
        if "_" in ident or any(ch.isupper() for ch in ident[1:]):
            shingles.add(f"sym:{ident.lower()}")
    raw_words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", text)]
    content_words = [_stem_token(w) for w in raw_words if w not in _STOPWORDS and len(w) >= 2]
    for word in content_words:
        shingles.add(f"w:{word}")
        if len(word) >= 4:
            for n in (3, 4):
                for idx in range(len(word) - n + 1):
                    shingles.add(f"c{n}:{word[idx:idx + n]}")
    for idx in range(len(content_words) - 1):
        shingles.add(f"bg:{content_words[idx]}_{content_words[idx + 1]}")
    return shingles


_MERSENNE_61 = (1 << 61) - 1
_NUM_PERM = 128
_PERM_COEFFS: tuple[tuple[int, int], ...] = tuple(
    (
        (_blake64(f"perm_a_{i}", 1) % (_MERSENNE_61 - 1)) + 1,
        _blake64(f"perm_b_{i}", 2) % _MERSENNE_61,
    )
    for i in range(_NUM_PERM)
)


def compute_minhash_signature(shingles: set[str]) -> tuple[int, ...]:
    """Compute a 128-permutation MinHash signature over a shingle set."""
    if not shingles:
        return tuple(_MERSENNE_61 for _ in range(_NUM_PERM))
    base_hashes = [_blake64(shingle, 0) % _MERSENNE_61 for shingle in shingles]
    signature: list[int] = []
    for coeff_a, coeff_b in _PERM_COEFFS:
        min_val = _MERSENNE_61
        for h_val in base_hashes:
            candidate = (coeff_a * h_val + coeff_b) % _MERSENNE_61
            if candidate < min_val:
                min_val = candidate
        signature.append(min_val)
    return tuple(signature)


def compute_simhash64(shingles: set[str]) -> int:
    """Compute a 64-bit Charikar SimHash fingerprint over a shingle set."""
    if not shingles:
        return 0
    weights = [0] * 64
    for shingle in shingles:
        weight = 3 if shingle.startswith(("sym:", "bg:")) else 2 if shingle.startswith("w:") else 1
        h_val = _blake64(shingle, 7)
        for bit in range(64):
            if (h_val >> bit) & 1:
                weights[bit] += weight
            else:
                weights[bit] -= weight
    fingerprint = 0
    for bit in range(64):
        if weights[bit] > 0:
            fingerprint |= 1 << bit
    return fingerprint


def simhash_similarity(fp_a: int, fp_b: int) -> float:
    """Normalized Hamming similarity in [0.0, 1.0] between two 64-bit SimHash integers."""
    xor_val = (fp_a ^ fp_b) & ((1 << 64) - 1)
    distance = xor_val.bit_count()
    return 1.0 - (distance / 64.0)


def minhash_jaccard_estimate(sig_a: tuple[int, ...], sig_b: tuple[int, ...]) -> float:
    """Estimated Jaccard similarity from two MinHash signatures."""
    if not sig_a or not sig_b or len(sig_a) != len(sig_b):
        return 0.0
    matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
    return matches / len(sig_a)


class MinHashLSHIndex:
    """Multi-band MinHash + 64-bit SimHash Locality-Sensitive Hashing index."""

    def __init__(
        self,
        entries: tuple[CapabilityEntry, ...] = DEFAULT_CAPABILITY_CATALOGUE,
        bands: int = 16,
        rows: int = 8,
    ) -> None:
        if bands * rows != _NUM_PERM:
            raise ValueError(f"bands * rows must equal {_NUM_PERM}")
        self.entries = entries
        self.bands = bands
        self.rows = rows
        self.entry_by_id: dict[str, CapabilityEntry] = {e.identity: e for e in entries}
        self.entry_shingles: dict[str, set[str]] = {}
        self.entry_minhash: dict[str, tuple[int, ...]] = {}
        self.entry_simhash: dict[str, int] = {}
        self.buckets: dict[tuple[int, int], list[str]] = {}
        for entry in entries:
            corpus = " ".join((
                entry.identity.replace("_", " "),
                entry.purpose,
                entry.canonical_query,
                " ".join(entry.domain_tags),
                " ".join(entry.ast_symbols),
                " ".join(entry.synonyms),
            ))
            shingles = extract_multi_granular_shingles(corpus)
            sig = compute_minhash_signature(shingles)
            sim = compute_simhash64(shingles)
            self.entry_shingles[entry.identity] = shingles
            self.entry_minhash[entry.identity] = sig
            self.entry_simhash[entry.identity] = sim
            for band_idx in range(self.bands):
                start = band_idx * self.rows
                band_tuple = sig[start : start + self.rows]
                bucket_hash = _blake64(",".join(str(x) for x in band_tuple), band_idx + 100)
                key = (band_idx, bucket_hash)
                self.buckets.setdefault(key, []).append(entry.identity)

    def query(self, text: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Retrieve candidate capabilities via LSH band collisions + SimHash + Sub-shingle containment."""
        q_shingles = extract_multi_granular_shingles(text)
        if not q_shingles:
            return []
        q_sig = compute_minhash_signature(q_shingles)
        q_sim = compute_simhash64(q_shingles)
        band_hits: dict[str, int] = {}
        for band_idx in range(self.bands):
            start = band_idx * self.rows
            band_tuple = q_sig[start : start + self.rows]
            bucket_hash = _blake64(",".join(str(x) for x in band_tuple), band_idx + 100)
            for identity in self.buckets.get((band_idx, bucket_hash), ()):
                band_hits[identity] = band_hits.get(identity, 0) + 1

        q_word_shingles = {s for s in q_shingles if s.startswith(("w:", "bg:", "sym:"))}
        q_char_shingles = {s for s in q_shingles if s.startswith(("c3:", "c4:"))}

        scored: list[dict[str, Any]] = []
        for entry in self.entries:
            identity = entry.identity
            e_shingles = self.entry_shingles[identity]
            collisions = band_hits.get(identity, 0)
            est_jaccard = minhash_jaccard_estimate(q_sig, self.entry_minhash[identity])
            sim_score = simhash_similarity(q_sim, self.entry_simhash[identity])
            word_overlap = (
                len(q_word_shingles & e_shingles) / max(1, min(len(q_word_shingles), 10))
                if q_word_shingles
                else 0.0
            )
            char_overlap = (
                len(q_char_shingles & e_shingles) / max(1, min(len(q_char_shingles), 32))
                if q_char_shingles
                else 0.0
            )
            band_ratio = collisions / self.bands
            combined = (
                0.30 * min(1.0, band_ratio * 3.0)
                + 0.20 * min(1.0, est_jaccard * 4.0)
                + 0.15 * max(0.0, (sim_score - 0.50) * 2.0)
                + 0.22 * min(1.0, word_overlap * 1.6)
                + 0.13 * min(1.0, char_overlap * 1.5)
            )
            scored.append({
                "identity": identity,
                "canonical_query": entry.canonical_query,
                "lsh_score": round(min(1.0, combined), 4),
                "band_collisions": collisions,
                "minhash_jaccard": round(est_jaccard, 4),
                "simhash_similarity": round(sim_score, 4),
            })
        scored.sort(key=lambda item: (item["lsh_score"], item["band_collisions"]), reverse=True)
        return scored[:top_k]


_LSH_INDEX_CACHE: dict[tuple[int, int, int], MinHashLSHIndex] = {}
_TFIDF_CACHE: dict[int, tuple[dict[str, float], dict[str, dict[str, float]]]] = {}


def get_lsh_index(
    entries: tuple[CapabilityEntry, ...] = DEFAULT_CAPABILITY_CATALOGUE,
    bands: int = 16,
    rows: int = 8,
) -> MinHashLSHIndex:
    """Return a cached MinHashLSHIndex for `(entries, bands, rows)`."""
    key = (id(entries), bands, rows)
    cached = _LSH_INDEX_CACHE.get(key)
    if cached is None:
        cached = MinHashLSHIndex(entries=entries, bands=bands, rows=rows)
        _LSH_INDEX_CACHE[key] = cached
    return cached


def _build_tfidf_vectors(
    entries: tuple[CapabilityEntry, ...],
) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    """Precompute and cache IDF weights and normalized TF-IDF vectors over word stems + char 4-grams."""
    cache_key = id(entries)
    cached = _TFIDF_CACHE.get(cache_key)
    if cached is not None:
        return cached
    doc_tokens: dict[str, list[str]] = {}
    df_counts: dict[str, int] = {}
    for entry in entries:
        text = " ".join((
            entry.identity.replace("_", " "),
            entry.purpose,
            entry.canonical_query,
            " ".join(entry.domain_tags),
            " ".join(entry.ast_symbols),
            " ".join(entry.synonyms),
        ))
        shingles = list(extract_multi_granular_shingles(text))
        doc_tokens[entry.identity] = shingles
        for token in set(shingles):
            df_counts[token] = df_counts.get(token, 0) + 1
    num_docs = len(entries)
    idf: dict[str, float] = {
        token: math.log((1.0 + num_docs) / (1.0 + df)) + 1.0
        for token, df in df_counts.items()
    }
    doc_vectors: dict[str, dict[str, float]] = {}
    for identity, tokens in doc_tokens.items():
        tf: dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        vec = {
            token: (count / len(tokens)) * idf.get(token, 1.0)
            for token, count in tf.items()
        }
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        doc_vectors[identity] = {token: val / norm for token, val in vec.items()}
    _TFIDF_CACHE[cache_key] = (idf, doc_vectors)
    return idf, doc_vectors


def tfidf_rank_entries(
    query_text: str,
    entries: tuple[CapabilityEntry, ...] = DEFAULT_CAPABILITY_CATALOGUE,
) -> list[dict[str, Any]]:
    """Rank capability entries by character n-gram + word-stem TF-IDF cosine similarity."""
    idf, doc_vectors = _build_tfidf_vectors(entries)
    q_tokens = list(extract_multi_granular_shingles(query_text))
    if not q_tokens:
        return []
    tf: dict[str, int] = {}
    for token in q_tokens:
        tf[token] = tf.get(token, 0) + 1
    q_vec = {
        token: (count / len(q_tokens)) * idf.get(token, 1.0)
        for token, count in tf.items()
        if token in idf
    }
    q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
    q_vec = {token: val / q_norm for token, val in q_vec.items()}

    results: list[dict[str, Any]] = []
    for entry in entries:
        d_vec = doc_vectors[entry.identity]
        dot = sum(val * d_vec.get(token, 0.0) for token, val in q_vec.items())
        scaled = min(1.0, dot * 2.0)
        results.append({
            "identity": entry.identity,
            "canonical_query": entry.canonical_query,
            "tfidf_score": round(scaled, 4),
        })
    results.sort(key=lambda item: item["tfidf_score"], reverse=True)
    return results


def keyword_ast_route(
    text: str,
    entries: tuple[CapabilityEntry, ...] = DEFAULT_CAPABILITY_CATALOGUE,
) -> list[dict[str, Any]]:
    """Deterministic AST symbol, import, and technical-phrase trie/regex router."""
    lowered = text.lower()
    q_shingles = extract_multi_granular_shingles(text)
    scored: list[dict[str, Any]] = []
    for entry in entries:
        ast_hits = sum(1 for sym in entry.ast_symbols if sym.lower() in lowered)
        tag_hits = sum(1 for tag in entry.domain_tags if tag.lower() in lowered)
        canon_words = [_stem_token(w) for w in entry.canonical_query.split()]
        stem_hits = sum(1 for w in canon_words if f"w:{w}" in q_shingles)
        raw_score = (0.35 * min(1.0, ast_hits / 2.0)) + (0.40 * min(1.0, tag_hits / 2.0)) + (
            0.25 * (stem_hits / max(1, len(canon_words)))
        )
        scored.append({
            "identity": entry.identity,
            "canonical_query": entry.canonical_query,
            "ast_score": round(min(1.0, raw_score * 1.35), 4),
            "ast_hits": ast_hits,
            "tag_hits": tag_hits,
        })
    scored.sort(key=lambda item: item["ast_score"], reverse=True)
    return scored


_CONCEPT_SYNONYM_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?i)\b(?:leak(?:age|ed|ing)?|contaminat\w+|group\s+overlap|shared\s+(?:group|household|patient|entity)|fit_transform\s+before\s+split|temporal\s+lookahead|split\s+integrity|train[/-]test\s+split)\b"),
        "data split leakage audit",
    ),
    (
        re.compile(r"(?i)\b(?:train(?:ing)?\s+(?:and|vs\.?|versus)\s+val(?:idation)?\s+gap|overfit(?:ting)?|underfit(?:ting)?|val(?:idation)?\s+loss\s+(?:ris\w+|diverg\w+|increas\w+)|generalization\s+gap|learning\s+curve\s+gap)\b"),
        "train validation gap",
    ),
    (
        re.compile(r"(?i)\b(?:imbalanced\s+(?:class\w+|data\w*|fraud)|rare\s+event|precision\s+recall|roc\s*[-_]?auc|brier\s+score|false\s+positive\s+cost|choose\s+(?:evaluation\s+)?metrics?|metric\s+selection)\b"),
        "choose evaluation metrics imbalanced",
    ),
    (
        re.compile(r"(?i)\b(?:ttl|time\s*[-_]?to\s*[-_]?live|lru\s+cache|expir(?:e|ed|ing|ation)\s+(?:cache\w*|items?|keys?|entries)|evict\w+\s+(?:stale|expired|oldest)|monotonic\s+clock\s+cache)\b"),
        "ttl lru cache expiration",
    ),
    (
        re.compile(r"(?i)\b(?:sql\s+where|where\s+clause|recursive\s+descent\s+parser|boolean\s+(?:filter|predicate)\s+(?:parser|ast|evaluator)|parse\s+filter\s+expression)\b"),
        "sql where clause parser",
    ),
    (
        re.compile(r"(?i)\b(?:greeble|pbr\s+(?:shader|material|hull)|three\.?js\s+shader|glsl\s+(?:fragment|vertex|shader)|procedural\s+3d|signed\s+distance\s+bevel)\b"),
        "procedural 3d shader greeble",
    ),
    (
        re.compile(r"(?i)\b(?:token\s+bucket|sliding\s+window\s+rate|rate\s+limit(?:er|ing)|request\s+throttl\w+|burst\s+(?:allowance|capacity)|retry[-_\s]after)\b"),
        "token bucket rate limiter",
    ),
    (
        re.compile(r"(?i)\b(?:topological\s+sort|cycle\s+detect\w+|directed\s+acyclic\s+graph|circular\s+dependenc\w+|kahn\w*\s+algorithm|dependency\s+wave)\b"),
        "dag topological sort cycle",
    ),
)


def validate_request_edge(request: Any) -> dict[str, Any] | None:
    """Layer 1: Validate request contract version, closed schema fields, and secret absence."""
    if not isinstance(request, dict):
        return _refusal(REFUSAL_INVALID_RECORD, "Request must be a JSON object.")
    if request.get("record_type") != REQUEST_VERSION:
        return _refusal(
            REFUSAL_INVALID_RECORD,
            f"Unsupported record_type {request.get('record_type')!r}; expected {REQUEST_VERSION}.",
        )
    unknown = sorted(set(request.keys()) - ALLOWED_REQUEST_FIELDS)
    if unknown:
        return _refusal(
            REFUSAL_UNKNOWN_FIELD,
            f"Unknown request fields refused at edge: {', '.join(unknown)}.",
        )
    prompt = request.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 16384:
        return _refusal(REFUSAL_INVALID_PROMPT, "Field 'prompt' must be a non-empty string up to 16384 characters.")
    for pattern in _SECRET_SCAN_PATTERNS:
        if pattern.search(prompt):
            return _refusal(
                REFUSAL_SECRET_DETECTED,
                "Prompt contains a credential-shaped string; refused before engine dispatch.",
            )
    return None


def check_client_handshake(request: dict[str, Any]) -> dict[str, Any] | None:
    """Layer 2: Verify protocol version and client profile handshake compatibility."""
    protocol_version = request.get("protocol_version", PROTOCOL_V1)
    if protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
        return _refusal(
            REFUSAL_UNSUPPORTED_PROTOCOL,
            f"Protocol version {protocol_version!r} is not supported; supported: {SUPPORTED_PROTOCOL_VERSIONS}.",
        )
    client_profile = request.get("client_profile", "generic")
    if client_profile not in SUPPORTED_CLIENT_PROFILES:
        return _refusal(
            REFUSAL_UNSUPPORTED_PROFILE,
            f"Client profile {client_profile!r} is not supported; supported: {SUPPORTED_CLIENT_PROFILES}.",
        )
    return None


def resync_session_state(request: dict[str, Any]) -> dict[str, Any]:
    """Layer 3: Normalize session state, seen capability identities, and ignored-injection counters."""
    raw_seen = request.get("seen_identities") or ()
    seen = tuple(sorted({str(item).strip() for item in raw_seen if str(item).strip()}))
    turn_index = int(request.get("turn_index", 0))
    ignored = int(request.get("consecutive_ignored_injections", 0))
    return {
        "seen_identities": seen,
        "turn_index": max(0, turn_index),
        "consecutive_ignored_injections": max(0, ignored),
    }


def check_budget_and_account(request: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Layer 4: Enforce token budget, card count ceiling, confidence threshold, and call allowance."""
    max_tokens = request.get("max_injected_tokens", 200)
    max_cards = request.get("max_cards", 2)
    threshold = request.get("confidence_threshold", 0.38)
    budget_remaining = request.get("call_budget_remaining", 10)
    if (
        not isinstance(max_tokens, int)
        or isinstance(max_tokens, bool)
        or not 20 <= max_tokens <= 400
        or not isinstance(max_cards, int)
        or isinstance(max_cards, bool)
        or not 1 <= max_cards <= 5
        or not isinstance(threshold, (int, float))
        or isinstance(threshold, bool)
        or not 0.05 <= float(threshold) <= 0.99
        or not isinstance(budget_remaining, int)
        or isinstance(budget_remaining, bool)
        or budget_remaining < 0
    ):
        return (
            _refusal(
                REFUSAL_INVALID_BUDGET,
                "Invalid budget or threshold parameters in adoption_trigger_request/v1.",
            ),
            {},
        )
    effects = tuple(request.get("granted_step_effects") or DEFAULT_STEP_EFFECT_GRANTS)
    return None, {
        "max_injected_tokens": max_tokens,
        "max_cards": max_cards,
        "confidence_threshold": float(threshold),
        "call_budget_remaining": budget_remaining,
        "granted_step_effects": effects,
    }


def check_frustration_cooldown(prompt: str, session_state: dict[str, Any]) -> tuple[bool, str]:
    """Layer 5: Abstain when user expresses rejection or ignored 2+ consecutive injections."""
    if session_state["consecutive_ignored_injections"] >= 2:
        return True, "consecutive_ignored_injections_limit_reached"
    for pattern in _FRUSTRATION_PATTERNS:
        if pattern.search(prompt):
            return True, "user_explicit_opt_out_phrase"
    return False, ""


def preprocess_and_troubleshoot_prompt(prompt: str) -> dict[str, Any]:
    """Layer 6: Strip stack traces, file paths, project titles, and meta-verbs; detect trivial prompts."""
    for pattern in _TRIVIAL_OR_OFFTOPIC_PATTERNS:
        if pattern.search(prompt):
            return {
                "cleaned_text": "",
                "extracted_query": "",
                "is_trivial_or_offtopic": True,
                "troubleshooting_steps": ["trivial_or_offtopic_short_circuit"],
            }
    steps: list[str] = []
    working = prompt
    if _FENCED_BLOCK_RE.search(working):
        working = _FENCED_BLOCK_RE.sub(" ", working)
        steps.append("stripped_fenced_code_blocks")
    if _TRACEBACK_LINE_RE.search(working):
        working = _TRACEBACK_LINE_RE.sub(" ", working)
        steps.append("stripped_traceback_lines")
    if _PATH_TOKEN_RE.search(working):
        working = _PATH_TOKEN_RE.sub(" ", working)
        steps.append("stripped_filesystem_paths")
    if _PROJECT_NOISE_RE.search(working):
        working = _PROJECT_NOISE_RE.sub(" ", working)
        steps.append("stripped_competition_or_project_titles")
    if _GENERIC_META_VERBS_RE.search(working):
        working = _GENERIC_META_VERBS_RE.sub(" ", working)
        steps.append("stripped_generic_meta_verbs")

    words = [
        w.lower()
        for w in re.findall(r"[A-Za-z][A-Za-z0-9_]{1,}", working)
        if w.lower() not in _STOPWORDS and len(w) >= 2
    ]
    deduped: list[str] = []
    for word in words:
        if word not in deduped:
            deduped.append(word)
    if len(deduped) < 2 and len(prompt.strip().split()) <= 5:
        return {
            "cleaned_text": " ".join(deduped),
            "extracted_query": "",
            "is_trivial_or_offtopic": True,
            "troubleshooting_steps": steps + ["short_non_technical_prompt"],
        }
    concise_query = " ".join(deduped[:5])
    return {
        "cleaned_text": " ".join(deduped),
        "extracted_query": concise_query,
        "is_trivial_or_offtopic": False,
        "troubleshooting_steps": steps,
    }


def _estimate_tokens(text: str) -> int:
    if not text.strip():
        return 0
    return max(1, int(math.ceil(len(text.split()) * 1.3)))


def format_contract_cards(
    selected_entries: list[tuple[CapabilityEntry, float]],
    max_tokens: int = 200,
) -> tuple[str, int, list[dict[str, Any]]]:
    """Render compact contract cards bounded by `max_tokens`."""
    if not selected_entries:
        return "", 0, []
    header = (
        "[Baltor Contract Cards — inspect purpose/effects first; call provisioning_read "
        "only if a card fits; abstain (0 reads) if none fit]"
    )
    lines = [header]
    cards_out: list[dict[str, Any]] = []
    for entry, score in selected_entries:
        effects_str = ",".join(entry.declared_effects) if entry.declared_effects else "pure"
        card_line = (
            f"- {entry.identity} ({entry.kind}, {entry.library_tier}, score={score:.2f}, "
            f"effects={effects_str}, digest={entry.body_digest[:16]}...): {entry.purpose}"
        )
        candidate_text = "\n".join(lines + [card_line])
        if _estimate_tokens(candidate_text) > max_tokens:
            break
        lines.append(card_line)
        cards_out.append({
            "identity": entry.identity,
            "kind": entry.kind,
            "library_tier": entry.library_tier,
            "purpose": entry.purpose,
            "body_digest": entry.body_digest,
            "declared_effects": list(entry.declared_effects),
            "effects_to_declare": [],
            "score": round(score, 4),
            "canonical_query": entry.canonical_query,
        })
    if not cards_out:
        return "", 0, []
    rendered = "\n".join(lines)
    return rendered, _estimate_tokens(rendered), cards_out


def _score_catalogue_query(
    query: str,
    raw_prompt: str,
    entries: tuple[CapabilityEntry, ...],
    lsh_index: MinHashLSHIndex,
) -> list[tuple[CapabilityEntry, float]]:
    """Score catalogue entries against a 2-5 word query combined with prompt features."""
    ast_scores = {row["identity"]: row["ast_score"] for row in keyword_ast_route(query + " " + raw_prompt, entries)}
    tfidf_scores = {row["identity"]: row["tfidf_score"] for row in tfidf_rank_entries(query + " " + raw_prompt, entries)}
    lsh_scores = {row["identity"]: row["lsh_score"] for row in lsh_index.query(query + " " + raw_prompt, top_k=len(entries))}
    q_words = set(_stem_token(w) for w in re.findall(r"[A-Za-z0-9]+", query.lower()) if len(w) >= 2)

    ranked: list[tuple[CapabilityEntry, float]] = []
    for entry in entries:
        canon_words = set(_stem_token(w) for w in entry.canonical_query.split())
        exact_canon_overlap = len(q_words & canon_words) / max(1, len(canon_words))
        score = (
            0.35 * exact_canon_overlap
            + 0.25 * ast_scores.get(entry.identity, 0.0)
            + 0.20 * tfidf_scores.get(entry.identity, 0.0)
            + 0.20 * lsh_scores.get(entry.identity, 0.0)
        )
        ranked.append((entry, round(min(1.0, score), 4)))
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked


def run_four_probe_chain(
    raw_prompt: str,
    cleaned_info: dict[str, Any],
    entries: tuple[CapabilityEntry, ...],
    lsh_index: MinHashLSHIndex,
    threshold: float,
) -> dict[str, Any]:
    """Execute the 4-probe query reformulation and relaxation chain."""
    probe_trace: list[dict[str, Any]] = []

    # Probe 1: Concise 2-5 word extracted technical domain phrases
    p1_query = cleaned_info["extracted_query"]
    p1_ranked = _score_catalogue_query(p1_query, cleaned_info["cleaned_text"], entries, lsh_index) if p1_query else []
    p1_top_score = p1_ranked[0][1] if p1_ranked else 0.0
    probe_trace.append({
        "probe": PROBE_1_NAME,
        "query": p1_query,
        "top_identity": p1_ranked[0][0].identity if p1_ranked else None,
        "top_score": round(p1_top_score, 4),
        "cleared_threshold": p1_top_score >= threshold,
    })
    if p1_top_score >= threshold:
        return {
            "winning_probe": PROBE_1_NAME,
            "reformulated_query": p1_query,
            "ranked": p1_ranked,
            "probe_trace": probe_trace,
        }

    # Probe 2: Synonym & concept alias expansion
    expanded_queries: list[str] = []
    for pattern, canonical in _CONCEPT_SYNONYM_RULES:
        if pattern.search(raw_prompt) or pattern.search(cleaned_info["cleaned_text"]):
            if canonical not in expanded_queries:
                expanded_queries.append(canonical)
    p2_query = expanded_queries[0] if expanded_queries else ""
    p2_ranked = _score_catalogue_query(p2_query, raw_prompt, entries, lsh_index) if p2_query else p1_ranked
    p2_top_score = p2_ranked[0][1] if (p2_query and p2_ranked) else 0.0
    probe_trace.append({
        "probe": PROBE_2_NAME,
        "query": p2_query,
        "top_identity": p2_ranked[0][0].identity if (p2_query and p2_ranked) else None,
        "top_score": round(p2_top_score, 4),
        "cleared_threshold": p2_top_score >= threshold,
    })
    if p2_top_score >= threshold:
        return {
            "winning_probe": PROBE_2_NAME,
            "reformulated_query": p2_query,
            "ranked": p2_ranked,
            "probe_trace": probe_trace,
        }

    # Probe 3: Multi-band MinHash + SimHash LSH cluster neighbour expansion
    lsh_hits = lsh_index.query(raw_prompt + " " + cleaned_info["cleaned_text"], top_k=len(entries))
    p3_ranked = [(lsh_index.entry_by_id[hit["identity"]], hit["lsh_score"]) for hit in lsh_hits]
    p3_top_score = p3_ranked[0][1] if p3_ranked else 0.0
    p3_query = lsh_hits[0]["canonical_query"] if (lsh_hits and p3_top_score >= threshold) else ""
    probe_trace.append({
        "probe": PROBE_3_NAME,
        "query": p3_query,
        "top_identity": p3_ranked[0][0].identity if p3_ranked else None,
        "top_score": round(p3_top_score, 4),
        "cleared_threshold": p3_top_score >= threshold,
    })
    if p3_top_score >= threshold:
        return {
            "winning_probe": PROBE_3_NAME,
            "reformulated_query": p3_query,
            "ranked": p3_ranked,
            "probe_trace": probe_trace,
        }

    # Probe 4: Safe abstention fallback
    probe_trace.append({
        "probe": PROBE_4_NAME,
        "query": "",
        "top_identity": None,
        "top_score": round(max(p1_top_score, p2_top_score, p3_top_score), 4),
        "cleared_threshold": False,
    })
    return {
        "winning_probe": PROBE_4_NAME,
        "reformulated_query": "",
        "ranked": p3_ranked or p2_ranked or p1_ranked,
        "probe_trace": probe_trace,
    }


def _filter_and_gate_candidates(
    ranked: list[tuple[CapabilityEntry, float]],
    threshold: float,
    seen_identities: tuple[str, ...],
    granted_effects: tuple[str, ...],
    max_cards: int,
    max_tokens: int,
) -> dict[str, Any]:
    """Filter candidates by confidence threshold, deduplication, and granted step effects."""
    above = [(entry, score) for entry, score in ranked if score >= threshold]
    if not above:
        return {
            "abstained": True,
            "abstention_code": ABSTAIN_BELOW_THRESHOLD,
            "injected_context": "",
            "injected_tokens": 0,
            "cards": [],
        }
    unseen = [(entry, score) for entry, score in above if entry.identity not in seen_identities]
    if not unseen:
        return {
            "abstained": True,
            "abstention_code": ABSTAIN_ALL_SEEN,
            "injected_context": "",
            "injected_tokens": 0,
            "cards": [],
        }
    effect_allowed = [
        (entry, score)
        for entry, score in unseen
        if all(eff == "pure" or eff in granted_effects for eff in entry.declared_effects)
    ]
    if not effect_allowed:
        return {
            "abstained": True,
            "abstention_code": ABSTAIN_UNDECLARED_EFFECTS,
            "injected_context": "",
            "injected_tokens": 0,
            "cards": [],
        }
    rendered, tokens, cards = format_contract_cards(effect_allowed[:max_cards], max_tokens=max_tokens)
    return {
        "abstained": False,
        "abstention_code": ABSTAIN_NONE,
        "injected_context": rendered,
        "injected_tokens": tokens,
        "cards": cards,
    }


def _engine_t0_passive_baseline(context: dict[str, Any]) -> dict[str, Any]:
    """T0: Passive MCP connection baseline with no pre-turn query reformulation or card injection."""
    return {
        "abstained": True,
        "abstention_code": ABSTAIN_PASSIVE_BASELINE,
        "reformulated_query": "",
        "winning_probe": PROBE_4_NAME,
        "probe_trace": [],
        "injected_context": "",
        "injected_tokens": 0,
        "cards": [],
    }


def _engine_t1_imperative_mcp_schema(context: dict[str, Any]) -> dict[str, Any]:
    """T1: Imperative MCP initialize/schema guidance + basic 2-5 word query extraction."""
    cleaned = context["cleaned_info"]
    query = cleaned["extracted_query"]
    entries = context["entries"]
    ast_rows = keyword_ast_route(query, entries)
    entry_map = {e.identity: e for e in entries}
    ranked = [(entry_map[row["identity"]], row["ast_score"]) for row in ast_rows]
    gated = _filter_and_gate_candidates(
        ranked,
        context["budget"]["confidence_threshold"],
        context["session"]["seen_identities"],
        context["budget"]["granted_step_effects"],
        context["budget"]["max_cards"],
        context["budget"]["max_injected_tokens"],
    )
    return {
        **gated,
        "reformulated_query": ranked[0][0].canonical_query if not gated["abstained"] else query,
        "winning_probe": PROBE_1_NAME if not gated["abstained"] else PROBE_4_NAME,
        "probe_trace": [{"probe": PROBE_1_NAME, "query": query, "top_score": ranked[0][1] if ranked else 0.0}],
    }


def _engine_t2_workspace_rules_layer(context: dict[str, Any]) -> dict[str, Any]:
    """T2: Workspace rules (CLAUDE.md / AGENTS.md) directive + synonym-aware query extraction."""
    raw_prompt = context["prompt"]
    cleaned = context["cleaned_info"]
    entries = context["entries"]
    query = cleaned["extracted_query"]
    for pattern, canonical in _CONCEPT_SYNONYM_RULES:
        if pattern.search(raw_prompt):
            query = canonical
            break
    ast_rows = keyword_ast_route(query + " " + cleaned["cleaned_text"], entries)
    entry_map = {e.identity: e for e in entries}
    ranked = [(entry_map[row["identity"]], row["ast_score"]) for row in ast_rows]
    gated = _filter_and_gate_candidates(
        ranked,
        context["budget"]["confidence_threshold"],
        context["session"]["seen_identities"],
        context["budget"]["granted_step_effects"],
        context["budget"]["max_cards"],
        context["budget"]["max_injected_tokens"],
    )
    return {
        **gated,
        "reformulated_query": ranked[0][0].canonical_query if not gated["abstained"] else query,
        "winning_probe": PROBE_2_NAME if not gated["abstained"] else PROBE_4_NAME,
        "probe_trace": [{"probe": PROBE_2_NAME, "query": query, "top_score": ranked[0][1] if ranked else 0.0}],
    }


def _engine_t3_keyword_ast_router(context: dict[str, Any]) -> dict[str, Any]:
    """T3: Deterministic AST symbol, import, and technical-identifier trie/regex router."""
    entries = context["entries"]
    rows = keyword_ast_route(context["prompt"] + " " + context["cleaned_info"]["cleaned_text"], entries)
    entry_map = {e.identity: e for e in entries}
    ranked = [(entry_map[row["identity"]], row["ast_score"]) for row in rows]
    gated = _filter_and_gate_candidates(
        ranked,
        context["budget"]["confidence_threshold"],
        context["session"]["seen_identities"],
        context["budget"]["granted_step_effects"],
        context["budget"]["max_cards"],
        context["budget"]["max_injected_tokens"],
    )
    top_query = ranked[0][0].canonical_query if ranked and not gated["abstained"] else ""
    return {
        **gated,
        "reformulated_query": top_query,
        "winning_probe": PROBE_1_NAME if not gated["abstained"] else PROBE_4_NAME,
        "probe_trace": [{"probe": PROBE_1_NAME, "query": top_query, "top_score": ranked[0][1] if ranked else 0.0}],
    }


def _engine_t4_tfidf_char_ngram_router(context: dict[str, Any]) -> dict[str, Any]:
    """T4: Character 3/4-gram + token-stem TF-IDF cosine similarity router."""
    entries = context["entries"]
    rows = tfidf_rank_entries(context["cleaned_info"]["cleaned_text"] or context["prompt"], entries)
    entry_map = {e.identity: e for e in entries}
    ranked = [(entry_map[row["identity"]], row["tfidf_score"]) for row in rows]
    gated = _filter_and_gate_candidates(
        ranked,
        context["budget"]["confidence_threshold"],
        context["session"]["seen_identities"],
        context["budget"]["granted_step_effects"],
        context["budget"]["max_cards"],
        context["budget"]["max_injected_tokens"],
    )
    top_query = ranked[0][0].canonical_query if ranked and not gated["abstained"] else ""
    return {
        **gated,
        "reformulated_query": top_query,
        "winning_probe": PROBE_1_NAME if not gated["abstained"] else PROBE_4_NAME,
        "probe_trace": [{"probe": PROBE_1_NAME, "query": top_query, "top_score": ranked[0][1] if ranked else 0.0}],
    }


def _engine_t5_minhash_lsh_fingerprint(context: dict[str, Any]) -> dict[str, Any]:
    """T5: Multi-band MinHash + 64-bit SimHash LSH blocker over stems, bigrams, char-ngrams, and AST symbols."""
    lsh_index: MinHashLSHIndex = context["lsh_index"]
    hits = lsh_index.query(context["prompt"] + " " + context["cleaned_info"]["cleaned_text"], top_k=len(context["entries"]))
    ranked = [(lsh_index.entry_by_id[row["identity"]], row["lsh_score"]) for row in hits]
    gated = _filter_and_gate_candidates(
        ranked,
        context["budget"]["confidence_threshold"],
        context["session"]["seen_identities"],
        context["budget"]["granted_step_effects"],
        context["budget"]["max_cards"],
        context["budget"]["max_injected_tokens"],
    )
    top_query = ranked[0][0].canonical_query if ranked and not gated["abstained"] else ""
    return {
        **gated,
        "reformulated_query": top_query,
        "winning_probe": PROBE_3_NAME if not gated["abstained"] else PROBE_4_NAME,
        "probe_trace": [{
            "probe": PROBE_3_NAME,
            "query": top_query,
            "top_score": ranked[0][1] if ranked else 0.0,
            "band_collisions": hits[0]["band_collisions"] if hits else 0,
            "simhash_similarity": hits[0]["simhash_similarity"] if hits else 0.0,
        }],
    }


def _engine_t6_gated_preturn_card_injector(context: dict[str, Any]) -> dict[str, Any]:
    """T6: Pre-turn contract-card injector with 4-probe query reformulation and relaxation chain."""
    chain = run_four_probe_chain(
        context["prompt"],
        context["cleaned_info"],
        context["entries"],
        context["lsh_index"],
        context["budget"]["confidence_threshold"],
    )
    gated = _filter_and_gate_candidates(
        chain["ranked"],
        context["budget"]["confidence_threshold"],
        context["session"]["seen_identities"],
        context["budget"]["granted_step_effects"],
        context["budget"]["max_cards"],
        context["budget"]["max_injected_tokens"],
    )
    return {
        **gated,
        "reformulated_query": chain["ranked"][0][0].canonical_query if chain["ranked"] and not gated["abstained"] else "",
        "winning_probe": chain["winning_probe"] if not gated["abstained"] else PROBE_4_NAME,
        "probe_trace": chain["probe_trace"],
    }


def _engine_t7_hybrid_cascade_with_fallback(context: dict[str, Any]) -> dict[str, Any]:
    """T7: Multi-stage cascade (T3 AST -> T4 TF-IDF -> T5 MinHash/SimHash LSH -> T6 4-Probe Card Injector)."""
    entries = context["entries"]
    lsh_index: MinHashLSHIndex = context["lsh_index"]
    raw_prompt = context["prompt"]
    cleaned = context["cleaned_info"]

    ast_map = {row["identity"]: row["ast_score"] for row in keyword_ast_route(raw_prompt, entries)}
    tfidf_map = {row["identity"]: row["tfidf_score"] for row in tfidf_rank_entries(cleaned["cleaned_text"] or raw_prompt, entries)}
    lsh_map = {row["identity"]: row["lsh_score"] for row in lsh_index.query(raw_prompt + " " + cleaned["cleaned_text"], top_k=len(entries))}
    chain = run_four_probe_chain(
        raw_prompt,
        cleaned,
        entries,
        lsh_index,
        context["budget"]["confidence_threshold"],
    )
    probe_map = {entry.identity: score for entry, score in chain["ranked"]}

    fused_ranked: list[tuple[CapabilityEntry, float]] = []
    for entry in entries:
        s_ast = ast_map.get(entry.identity, 0.0)
        s_tfidf = tfidf_map.get(entry.identity, 0.0)
        s_lsh = lsh_map.get(entry.identity, 0.0)
        s_probe = probe_map.get(entry.identity, 0.0)
        # Consensus boost when multiple independent families agree on the same capability
        agree_count = sum(1 for val in (s_ast, s_tfidf, s_lsh, s_probe) if val >= 0.30)
        consensus_bonus = 0.08 if agree_count >= 3 else 0.04 if agree_count == 2 else 0.0
        fused = max(
            s_probe,
            0.25 * s_ast + 0.22 * s_tfidf + 0.28 * s_lsh + 0.25 * s_probe + consensus_bonus,
        )
        fused_ranked.append((entry, round(min(1.0, fused), 4)))
    fused_ranked.sort(key=lambda pair: pair[1], reverse=True)

    gated = _filter_and_gate_candidates(
        fused_ranked,
        context["budget"]["confidence_threshold"],
        context["session"]["seen_identities"],
        context["budget"]["granted_step_effects"],
        context["budget"]["max_cards"],
        context["budget"]["max_injected_tokens"],
    )
    winning_probe = chain["winning_probe"]
    if not gated["abstained"] and winning_probe == PROBE_4_NAME:
        winning_probe = PROBE_3_NAME
    return {
        **gated,
        "reformulated_query": fused_ranked[0][0].canonical_query if fused_ranked and not gated["abstained"] else "",
        "winning_probe": winning_probe if not gated["abstained"] else PROBE_4_NAME,
        "probe_trace": chain["probe_trace"],
    }


def _engine_t8_ollama_micro_classifier(context: dict[str, Any]) -> dict[str, Any]:
    """T8: Bounded micro-classifier probe with automatic deterministic fallback to T7."""
    classifier_fn: Callable[[str], str] | None = context.get("model_classifier_fn")
    allow_live = bool(context.get("allow_live_model", False))
    if classifier_fn is None and not allow_live:
        raise RuntimeError("micro_classifier_offline_fallback_to_t7")
    if classifier_fn is not None:
        model_query = classifier_fn(context["prompt"])
        entries = context["entries"]
        ranked = _score_catalogue_query(model_query, context["prompt"], entries, context["lsh_index"])
        gated = _filter_and_gate_candidates(
            ranked,
            context["budget"]["confidence_threshold"],
            context["session"]["seen_identities"],
            context["budget"]["granted_step_effects"],
            context["budget"]["max_cards"],
            context["budget"]["max_injected_tokens"],
        )
        return {
            **gated,
            "reformulated_query": ranked[0][0].canonical_query if ranked and not gated["abstained"] else model_query,
            "winning_probe": PROBE_1_NAME if not gated["abstained"] else PROBE_4_NAME,
            "probe_trace": [{"probe": "micro_classifier_probe", "query": model_query, "top_score": ranked[0][1] if ranked else 0.0}],
        }
    raise RuntimeError("micro_classifier_unconfigured_fallback_to_t7")


ENGINE_REGISTRY: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    ENGINE_T0: _engine_t0_passive_baseline,
    ENGINE_T1: _engine_t1_imperative_mcp_schema,
    ENGINE_T2: _engine_t2_workspace_rules_layer,
    ENGINE_T3: _engine_t3_keyword_ast_router,
    ENGINE_T4: _engine_t4_tfidf_char_ngram_router,
    ENGINE_T5: _engine_t5_minhash_lsh_fingerprint,
    ENGINE_T6: _engine_t6_gated_preturn_card_injector,
    ENGINE_T7: _engine_t7_hybrid_cascade_with_fallback,
    ENGINE_T8: _engine_t8_ollama_micro_classifier,
}


def _refusal(code: str, message: str) -> dict[str, Any]:
    return {
        "record_type": REFUSAL_VERSION,
        "error": {
            "code": code,
            "message": message,
        },
    }


def run_preturn_envelope(request: dict[str, Any]) -> dict[str, Any]:
    """Execute the 7-layer pre-turn component envelope and return a versioned result or refusal."""
    t_start = time.perf_counter()
    envelope_trace: list[str] = []

    # Layer 1: Edge & contract validation
    edge_error = validate_request_edge(request)
    if edge_error is not None:
        return edge_error
    envelope_trace.append("layer_1_edge_validated")

    # Layer 2: Handshake & client profile check
    handshake_error = check_client_handshake(request)
    if handshake_error is not None:
        return handshake_error
    envelope_trace.append("layer_2_handshake_verified")

    # Layer 3: Session tracking & resync
    session_state = resync_session_state(request)
    envelope_trace.append("layer_3_session_resynced")

    # Layer 4: Budget & account checks
    budget_error, budget_state = check_budget_and_account(request)
    if budget_error is not None:
        return budget_error
    envelope_trace.append("layer_4_budget_checked")

    requested_engine = request.get("engine_id", ENGINE_T7)
    if requested_engine not in ENGINE_REGISTRY:
        return _refusal(REFUSAL_UNKNOWN_ENGINE, f"Unknown engine_id {requested_engine!r}.")

    # Layer 5: Frustration avoidance
    frustrated, frustration_detail = check_frustration_cooldown(request["prompt"], session_state)
    if frustrated:
        envelope_trace.append(f"layer_5_frustration_abstained:{frustration_detail}")
        return {
            "record_type": RESULT_VERSION,
            "requested_engine": requested_engine,
            "selected_engine": requested_engine,
            "abstained": True,
            "abstention_code": ABSTAIN_FRUSTRATION_COOLDOWN,
            "reformulated_query": "",
            "winning_probe": PROBE_4_NAME,
            "probe_trace": [],
            "injected_context": "",
            "injected_tokens": 0,
            "cards": [],
            "fallback_events": [],
            "envelope_trace": envelope_trace,
            "latency_ms": round((time.perf_counter() - t_start) * 1000.0, 3),
        }
    envelope_trace.append("layer_5_frustration_clear")

    if budget_state["call_budget_remaining"] == 0:
        envelope_trace.append("layer_4_budget_zero_abstained")
        return {
            "record_type": RESULT_VERSION,
            "requested_engine": requested_engine,
            "selected_engine": requested_engine,
            "abstained": True,
            "abstention_code": ABSTAIN_BUDGET_EXHAUSTED,
            "reformulated_query": "",
            "winning_probe": PROBE_4_NAME,
            "probe_trace": [],
            "injected_context": "",
            "injected_tokens": 0,
            "cards": [],
            "fallback_events": [],
            "envelope_trace": envelope_trace,
            "latency_ms": round((time.perf_counter() - t_start) * 1000.0, 3),
        }

    # Layer 6: Pre-dispatch self-troubleshooting
    cleaned_info = preprocess_and_troubleshoot_prompt(request["prompt"])
    envelope_trace.append("layer_6_preprocessed")
    if cleaned_info["is_trivial_or_offtopic"]:
        envelope_trace.append("layer_6_trivial_or_offtopic_short_circuit")
        return {
            "record_type": RESULT_VERSION,
            "requested_engine": requested_engine,
            "selected_engine": requested_engine,
            "abstained": True,
            "abstention_code": ABSTAIN_TRIVIAL_OR_OFFTOPIC,
            "reformulated_query": "",
            "winning_probe": PROBE_4_NAME,
            "probe_trace": [],
            "injected_context": "",
            "injected_tokens": 0,
            "cards": [],
            "fallback_events": [],
            "envelope_trace": envelope_trace,
            "latency_ms": round((time.perf_counter() - t_start) * 1000.0, 3),
        }

    # Layer 7: Ordered engine selection & automatic fallback chain
    bands = int(request.get("lsh_bands", 16))
    rows = int(request.get("lsh_rows", 8))
    entries = request.get("catalogue_items") or DEFAULT_CAPABILITY_CATALOGUE
    if not isinstance(entries, tuple):
        entries = tuple(entries)
    lsh_index = get_lsh_index(entries=entries, bands=bands, rows=rows)

    custom_chain = tuple(request.get("fallback_chain") or DEFAULT_FALLBACK_CHAIN)
    execution_order: list[str] = [requested_engine]
    for fallback_id in custom_chain:
        if fallback_id in ENGINE_REGISTRY and fallback_id not in execution_order:
            execution_order.append(fallback_id)

    simulated_faults = set(request.get("simulated_faults") or ())
    fallback_events: list[dict[str, str]] = []
    context = {
        "prompt": request["prompt"],
        "cleaned_info": cleaned_info,
        "session": session_state,
        "budget": budget_state,
        "entries": entries,
        "lsh_index": lsh_index,
        "allow_live_model": request.get("allow_live_model", False),
        "model_classifier_fn": request.get("model_classifier_fn"),
    }

    for candidate_engine in execution_order:
        try:
            if candidate_engine in simulated_faults:
                raise RuntimeError(f"simulated_fault_in_{candidate_engine}")
            output = ENGINE_REGISTRY[candidate_engine](context)
            envelope_trace.append(f"layer_7_dispatched:{candidate_engine}")
            return {
                "record_type": RESULT_VERSION,
                "requested_engine": requested_engine,
                "selected_engine": candidate_engine,
                "abstained": output["abstained"],
                "abstention_code": output["abstention_code"],
                "reformulated_query": output["reformulated_query"],
                "winning_probe": output["winning_probe"],
                "probe_trace": output["probe_trace"],
                "injected_context": output["injected_context"],
                "injected_tokens": output["injected_tokens"],
                "cards": output["cards"],
                "fallback_events": fallback_events,
                "envelope_trace": envelope_trace,
                "latency_ms": round((time.perf_counter() - t_start) * 1000.0, 3),
            }
        except Exception as exc:
            fallback_events.append({
                "failed_engine": candidate_engine,
                "detail": str(exc),
            })
            envelope_trace.append(f"layer_7_fallback_from:{candidate_engine}")

    return {
        "record_type": RESULT_VERSION,
        "requested_engine": requested_engine,
        "selected_engine": ENGINE_T0,
        "abstained": True,
        "abstention_code": ABSTAIN_BELOW_THRESHOLD,
        "reformulated_query": "",
        "winning_probe": PROBE_4_NAME,
        "probe_trace": [],
        "injected_context": "",
        "injected_tokens": 0,
        "cards": [],
        "fallback_events": fallback_events,
        "envelope_trace": envelope_trace,
        "latency_ms": round((time.perf_counter() - t_start) * 1000.0, 3),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prompt", default="", help="User prompt text to evaluate before a harness turn")
    parser.add_argument("--engine", default=ENGINE_T7, choices=ENGINE_IDS, help="Selected pre-turn engine")
    parser.add_argument("--client-profile", default="generic", choices=SUPPORTED_CLIENT_PROFILES)
    parser.add_argument("--threshold", type=float, default=0.38, help="Confidence threshold in [0.05, 0.99]")
    parser.add_argument("--max-tokens", type=int, default=200, help="Maximum injected contract card tokens")
    parser.add_argument("--json", action="store_true", help="Print full typed adoption_trigger_result/v1 JSON")
    args = parser.parse_args(argv)

    prompt_text = args.prompt
    if not prompt_text and not sys.stdin.isatty():
        raw_stdin = sys.stdin.read().strip()
        if raw_stdin.startswith("{"):
            try:
                parsed = json.loads(raw_stdin)
                prompt_text = str(parsed.get("prompt") or parsed.get("user_prompt") or "")
            except ValueError:
                prompt_text = raw_stdin
        else:
            prompt_text = raw_stdin

    result = run_preturn_envelope({
        "record_type": REQUEST_VERSION,
        "protocol_version": PROTOCOL_V1,
        "client_profile": args.client_profile,
        "prompt": prompt_text,
        "engine_id": args.engine,
        "confidence_threshold": args.threshold,
        "max_injected_tokens": args.max_tokens,
    })
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        if result.get("record_type") == REFUSAL_VERSION:
            print(json.dumps(result, sort_keys=True), file=sys.stderr)
            return 1
        if not result.get("abstained") and result.get("injected_context"):
            print(result["injected_context"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
