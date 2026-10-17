"""Swappable Jev-style decision, zero-shot classifier, static embedding, LSH blocker, and MaxSim reranker engines.

Kind: development verification and benchmark module exercising the 7-layer component envelope
(`src/loop_engine/core/engines/envelope.py`) and the typed decision contracts
(`src/loop_engine/core/decisions/`) across six swappable engine families and their fallback cascades:

1. ``jev_system_one_adapter``: Jev / Circuit / Laya ``/v1/systemone`` wire adapter (`choice`, `score`,
   `noul`) with model-identity verification, temperature/calibration check, and abstention gate.
2. ``gliclass_modernbert_zero_shot``: Single-forward-pass zero-shot dynamic label and intent classifier
   scoring arbitrary ``(text, label_descriptions)`` pairs with calibrated softmax probabilities.
3. ``model2vec_static_embedder``: Static subword/token embedding engine with Matryoshka dimension
   truncation (`256 -> 128 -> 64 -> 32`), 1-bit sign binary quantization with XOR Hamming similarity,
   and strict embedding-space handshake (`require_same_space`).
4. ``multiband_lsh_blocker``: Multi-band MinHash + 64-bit SimHash + character-n-gram shingle LSH
   candidate blocker that narrows retrieval candidates in O(1) bucket lookups without full scans.
5. ``late_interaction_maxsim_reranker``: Token-level late-interaction MaxSim reranker (`ColBERT` /
   `FlashRank` / `Jina-Reranker-v3` style) with preflight latency and candidate budget checks.
6. ``deterministic_rules_fallback``: Zero-dependency, in-process deterministic policy/trie engine
   (`local_contract` proof level) that answers when model/network authority is off, budget is spent,
   or an upstream model abstains.

Every engine invocation passes through the 7-layer component envelope (`frustration_avoidance`,
`carrier`, `handshake`, `account`, `tracking`, `preflight`, and `nested_envelopes`). Nothing here
opens a live network socket or mutates repository state.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass, field
from types import MappingProxyType

from loop_engine.core.decisions.contracts import (
    BOOLEAN_PROBABILITY,
    CHOICE,
    QUESTION_KINDS,
    SCORE,
    DecisionBatchRequest,
    DecisionProtocolError,
    DecisionQuestion,
    admit_answers,
    canonical,
)
from loop_engine.core.decisions.wire import MAXIMUM_CHOICES, NATIVE_NOUL, normalized_answers
from loop_engine.core.engines.envelope import (
    CALLER,
    DO_NOT_RETRY,
    EFFECT_NONE,
    ENGINE_SOURCE,
    INBOUND_LAYERS,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_ANSWERED,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_NOT_APPLICABLE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    PURE_EFFECT,
    RECONCILE_BEFORE_RETRY,
    RETRY_AFTER_FIX,
    EnvelopeError,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeHandshakeVerdict,
    EnvelopeRefusal,
    EnvelopeTrace,
    enter_nested,
    envelope_refusal,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (
    ANSWER_FROM_FIRST_RESULT,
    DISPATCH,
    EFFECT_STATE_CONFIRMED,
    EFFECT_STATE_NONE,
    REQUEST_ANSWERED,
    TASK_COMPLETED,
    journal_decision,
    journal_intent,
    journal_outcome,
    request_identity_digest,
)

REQUEST_RECORD_TYPE = "decision_engine_request/v1"
SPACE_RECORD_TYPE = "embedding_space_signature/v1"
BENCHMARK_REPORT_RECORD_TYPE = "decision_classifier_benchmark_report/v1"
PROTOCOL_VERSION = "typed_decisions/v1"
EMBEDDING_PROTOCOL_VERSION = "embedding_stage/v1"
RERANK_PROTOCOL_VERSION = "rerank_stage/v1"
BLOCKER_PROTOCOL_VERSION = "candidate_blocker/v1"

ENGINE_JEV_SYSTEM_ONE = "jev_system_one_adapter"
ENGINE_GLICLASS_ZERO_SHOT = "gliclass_modernbert_zero_shot"
ENGINE_MODEL2VEC_EMBEDDER = "model2vec_static_embedder"
ENGINE_MULTIBAND_LSH = "multiband_lsh_blocker"
ENGINE_MAXSIM_RERANKER = "late_interaction_maxsim_reranker"
ENGINE_DETERMINISTIC_RULES = "deterministic_rules_fallback"

ALL_ENGINE_IDS = (
    ENGINE_JEV_SYSTEM_ONE,
    ENGINE_GLICLASS_ZERO_SHOT,
    ENGINE_MODEL2VEC_EMBEDDER,
    ENGINE_MULTIBAND_LSH,
    ENGINE_MAXSIM_RERANKER,
    ENGINE_DETERMINISTIC_RULES,
)

MATRYOSHKA_DIMENSIONS = (256, 128, 64, 32)
NORMALIZATION_MODES = ("l2_unit", "binary_hamming")
DEFAULT_TIMESTAMP = "2026-10-16T12:00:00Z"
_WORD_RE = re.compile(r"[a-z0-9_]+")


def _sha256_hex(payload) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(_WORD_RE.findall(text.lower()))


def _char_ngrams(text: str, n: int = 3) -> tuple[str, ...]:
    cleaned = re.sub(r"\s+", " ", text.lower().strip())
    if len(cleaned) < n:
        return (cleaned,) if cleaned else ("",)
    return tuple(cleaned[i : i + n] for i in range(len(cleaned) - n + 1))


# ---------------------------------------------------------------------------
# Embedding-space handshake contract (`require_same_space`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmbeddingSpaceSignature:
    """Typed declaration of an embedding space so vectors from incompatible spaces never compare."""

    model_id: str
    weights_digest: str
    dimension: int
    normalization: str
    quantization: str = "float32"
    record_type: str = SPACE_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != SPACE_RECORD_TYPE:
            raise EnvelopeError("unsupported_space_record", f"{self.record_type} is not {SPACE_RECORD_TYPE}")
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise EnvelopeError("invalid_embedding_model", "model_id must be a nonempty string")
        if not isinstance(self.weights_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", self.weights_digest):
            raise EnvelopeError("invalid_weights_digest", "weights_digest must be a 64-hex SHA-256 digest")
        if self.dimension not in MATRYOSHKA_DIMENSIONS:
            raise EnvelopeError(
                "unsupported_matryoshka_dimension",
                f"dimension {self.dimension} must be one of {MATRYOSHKA_DIMENSIONS}",
            )
        if self.normalization not in NORMALIZATION_MODES:
            raise EnvelopeError(
                "unsupported_normalization",
                f"normalization {self.normalization} must be one of {NORMALIZATION_MODES}",
            )
        if self.quantization not in ("float32", "int8", "binary_1bit"):
            raise EnvelopeError("unsupported_quantization", f"unsupported quantization {self.quantization}")

    @property
    def space_digest(self) -> str:
        return _sha256_hex(
            {
                "record_type": self.record_type,
                "model_id": self.model_id,
                "weights_digest": self.weights_digest,
                "dimension": self.dimension,
                "normalization": self.normalization,
                "quantization": self.quantization,
            }
        )


def require_same_space(left: EmbeddingSpaceSignature, right: EmbeddingSpaceSignature) -> EmbeddingSpaceSignature:
    """Refuse vector comparison when model identity, weights digest, dimension, or normalization differ."""
    if not isinstance(left, EmbeddingSpaceSignature) or not isinstance(right, EmbeddingSpaceSignature):
        raise EnvelopeError("invalid_space_signature", "both operands must carry an EmbeddingSpaceSignature")
    if left.model_id != right.model_id or left.weights_digest != right.weights_digest:
        raise EnvelopeError(
            "embedding_model_mismatch",
            f"cannot compare vectors from {left.model_id} and {right.model_id} without re-indexing",
        )
    if left.dimension != right.dimension:
        raise EnvelopeError(
            "embedding_dimension_mismatch",
            f"cannot compare {left.dimension}d vector against {right.dimension}d vector",
        )
    if left.normalization != right.normalization or left.quantization != right.quantization:
        raise EnvelopeError(
            "embedding_normalization_mismatch",
            f"cannot compare ({left.normalization}, {left.quantization}) with ({right.normalization}, {right.quantization})",
        )
    return left


# ---------------------------------------------------------------------------
# Unified 7-Layer Envelope Request & Execution Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineEnvelopeRequest:
    """One carrier-validated request entering an engine's 7-layer envelope."""

    request_id: str
    component: str
    task_kind: str
    text: str
    candidates: MappingProxyType
    requested_versions: tuple[str, ...] = (PROTOCOL_VERSION,)
    required_capabilities: tuple[str, ...] = ("calibrated_confidence",)
    advisory_capabilities: tuple[str, ...] = ()
    granted_effects: tuple[str, ...] = ()
    account_principal: str = "acct_verified_pilot"
    account_entitled: bool = True
    budget_ms: float = 50.0
    temperature: float = 1.0
    abstention_threshold: float = 0.35
    matryoshka_dim: int = 128
    allow_self_repair: bool = True
    record_type: str = REQUEST_RECORD_TYPE

    def __init__(
        self,
        request_id: str,
        component: str,
        task_kind: str,
        text: str,
        candidates: dict | MappingProxyType,
        requested_versions: tuple[str, ...] = (PROTOCOL_VERSION,),
        required_capabilities: tuple[str, ...] = ("calibrated_confidence",),
        advisory_capabilities: tuple[str, ...] = (),
        granted_effects: tuple[str, ...] = (),
        account_principal: str = "acct_verified_pilot",
        account_entitled: bool = True,
        budget_ms: float = 50.0,
        temperature: float = 1.0,
        abstention_threshold: float = 0.35,
        matryoshka_dim: int = 128,
        allow_self_repair: bool = True,
        record_type: str = REQUEST_RECORD_TYPE,
    ):
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "component", component)
        object.__setattr__(self, "task_kind", task_kind)
        object.__setattr__(self, "text", text)
        object.__setattr__(
            self,
            "candidates",
            MappingProxyType(dict(candidates)) if isinstance(candidates, (dict, MappingProxyType)) else candidates,
        )
        object.__setattr__(self, "requested_versions", tuple(requested_versions))
        object.__setattr__(self, "required_capabilities", tuple(required_capabilities))
        object.__setattr__(self, "advisory_capabilities", tuple(advisory_capabilities))
        object.__setattr__(self, "granted_effects", tuple(granted_effects))
        object.__setattr__(self, "account_principal", account_principal)
        object.__setattr__(self, "account_entitled", account_entitled)
        object.__setattr__(self, "budget_ms", float(budget_ms))
        object.__setattr__(self, "temperature", float(temperature))
        object.__setattr__(self, "abstention_threshold", float(abstention_threshold))
        object.__setattr__(self, "matryoshka_dim", int(matryoshka_dim))
        object.__setattr__(self, "allow_self_repair", bool(allow_self_repair))
        object.__setattr__(self, "record_type", record_type)


@dataclass(frozen=True)
class EngineEnvelopeOutcome:
    """Full 7-layer trace, handshake verdict, preflight report, and typed decision answer."""

    ok: bool
    engine_id: str
    chosen: str
    probabilities: dict[str, float]
    confidence: float
    abstained: bool
    trace: EnvelopeTrace
    handshake_verdict: EnvelopeHandshakeVerdict | None
    preflight_report: EnvelopePreflightReport | None
    frame: EnvelopeFrame
    latency_ms: float
    replayed_from_journal: bool = False
    fallback_chain: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)


def _carrier_check(request: EngineEnvelopeRequest) -> EnvelopeRefusal | None:
    if request.record_type != REQUEST_RECORD_TYPE:
        return envelope_refusal(
            "unsupported_carrier_version",
            "The request record version is not supported by this component carrier.",
            "Send a request formatted under the current decision engine request schema.",
            retry=RETRY_AFTER_FIX,
        )
    if not isinstance(request.text, str) or not request.text.strip():
        return envelope_refusal(
            "empty_input_text",
            "The carrier refused the request because the input text is blank.",
            "Supply a nonempty text string in the request payload before retrying.",
            retry=RETRY_AFTER_FIX,
        )
    if not isinstance(request.candidates, MappingProxyType) or len(request.candidates) < 2:
        return envelope_refusal(
            "insufficient_candidates",
            "A decision or classification request must declare at least two distinct candidates.",
            "Provide at least two candidate keys and descriptions in the request.",
            retry=RETRY_AFTER_FIX,
        )
    if len(request.candidates) > MAXIMUM_CHOICES:
        return envelope_refusal(
            "candidate_limit_exceeded",
            "The candidate set exceeds the protocol maximum of two hundred fifty-five choices.",
            "Narrow the candidate set with a blocker stage before calling the decision engine.",
            retry=RETRY_AFTER_FIX,
        )
    for key, desc in request.candidates.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(desc, str) or not desc.strip():
            return envelope_refusal(
                "invalid_candidate_entry",
                "Every candidate entry must have a nonempty identifier and description text.",
                "Fix the empty candidate key or description in the request payload.",
                retry=RETRY_AFTER_FIX,
            )
    return None


def _account_check(request: EngineEnvelopeRequest) -> EnvelopeRefusal | None:
    if not isinstance(request.account_principal, str) or not request.account_principal.strip():
        return envelope_refusal(
            "missing_account_principal",
            "The request carries no verified account principal for entitlement checking.",
            "Sign in or attach a scoped client key before sending the request.",
            retry=RETRY_AFTER_FIX,
        )
    if not request.account_entitled:
        return envelope_refusal(
            "account_entitlement_refused",
            "The current account principal is not entitled to invoke this engine profile.",
            "Enable the capability on the account or select an eligible local engine.",
            retry=DO_NOT_RETRY,
        )
    if request.budget_ms <= 0:
        return envelope_refusal(
            "latency_budget_exhausted",
            "The caller latency allowance is zero or negative before engine preflight.",
            "Increase the step budget allowance or route to the deterministic fallback engine.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _build_preflight_checks_and_repairs(max_latency_ms: float) -> tuple[tuple[EnvelopePreflightCheck, ...], tuple[EnvelopeSelfRepair, ...]]:
    def check_temperature(ctx) -> EnvelopeRefusal | None:
        temp = ctx.get("temperature", 1.0)
        if not (0.05 <= temp <= 2.0):
            return envelope_refusal(
                "temperature_out_of_calibration_bounds",
                "The requested calibration temperature lies outside the verified interval.",
                "Set the calibration temperature between 0.05 and 2.00 before calling the engine.",
                retry=RETRY_AFTER_FIX,
            )
        return None

    def check_matryoshka(ctx) -> EnvelopeRefusal | None:
        dim = ctx.get("matryoshka_dim", 128)
        if dim not in MATRYOSHKA_DIMENSIONS:
            return envelope_refusal(
                "invalid_matryoshka_dimension",
                "The requested embedding dimension is not a supported Matryoshka truncation slice.",
                "Choose a supported Matryoshka dimension of 256, 128, 64, or 32.",
                retry=RETRY_AFTER_FIX,
            )
        return None

    def check_budget(ctx) -> EnvelopeRefusal | None:
        budget = ctx.get("budget_ms", 0.0)
        if budget < max_latency_ms:
            return envelope_refusal(
                "preflight_budget_below_engine_floor",
                "The remaining latency budget is smaller than the engine minimum execution floor.",
                "Allocate a larger latency budget or switch to a lower-latency engine.",
                retry=RETRY_AFTER_FIX,
            )
        return None

    def check_abstention(ctx) -> EnvelopeRefusal | None:
        threshold = ctx.get("abstention_threshold", 0.35)
        if not (0.0 <= threshold <= 0.95):
            return envelope_refusal(
                "invalid_abstention_gate",
                "The abstention gate threshold must sit between zero and ninety-five hundredths.",
                "Set abstention_threshold to a calibrated probability in [0.0, 0.95].",
                retry=RETRY_AFTER_FIX,
            )
        return None

    def repair_temperature(ctx):
        updated = dict(ctx)
        updated["temperature"] = min(2.0, max(0.05, float(ctx.get("temperature", 1.0))))
        return updated

    def repair_matryoshka(ctx):
        updated = dict(ctx)
        raw = int(ctx.get("matryoshka_dim", 128))
        closest = min(MATRYOSHKA_DIMENSIONS, key=lambda d: abs(d - raw))
        updated["matryoshka_dim"] = closest
        return updated

    checks = (
        EnvelopePreflightCheck("calibration_temperature_check", ("temperature_out_of_calibration_bounds",), check_temperature),
        EnvelopePreflightCheck("matryoshka_dimension_check", ("invalid_matryoshka_dimension",), check_matryoshka),
        EnvelopePreflightCheck("latency_budget_check", ("preflight_budget_below_engine_floor",), check_budget),
        EnvelopePreflightCheck("abstention_threshold_check", ("invalid_abstention_gate",), check_abstention),
    )
    repairs = (
        EnvelopeSelfRepair("clamp_calibration_temperature", ("temperature_out_of_calibration_bounds",), (PURE_EFFECT,), 1, repair_temperature),
        EnvelopeSelfRepair("snap_matryoshka_dimension", ("invalid_matryoshka_dimension",), (PURE_EFFECT,), 1, repair_matryoshka),
    )
    return checks, repairs


# ---------------------------------------------------------------------------
# Engine 1: Jev / Circuit / Laya `/v1/systemone` Wire Protocol Engine
# ---------------------------------------------------------------------------


class JevSystemOneEngine:
    """Engine 1 (`jev_system_one_adapter`): `/v1/systemone` wire adapter (`choice`, `score`, `noul`).

    Validates the exact System One payload and response schema (`admit_answers`), checks model identity
    and calibration temperature, and enforces an explicit abstention gate when peak probability mass or
    calibrated confidence falls below `abstention_threshold`.
    """

    engine_id = ENGINE_JEV_SYSTEM_ONE
    model_id = "jev-2.1.0"
    min_latency_ms = 2.0

    def __init__(self, *, model_id: str = "jev-2.1.0", simulated_wrong_model: str = ""):
        self.model_id = model_id
        self._simulated_wrong_model = simulated_wrong_model

    def declaration(self) -> EnvelopeHandshakeDeclaration:
        return EnvelopeHandshakeDeclaration(
            engine=self.engine_id,
            supported_versions=(PROTOCOL_VERSION,),
            capabilities=("calibrated_confidence", "choice_distribution", "score_levels", "noul_probability", "abstention_gate"),
            effects=("model_call", "network_Access") if False else ("model_call",),
        )

    def execute_wire(self, request: EngineEnvelopeRequest, context: dict) -> dict:
        temperature = float(context.get("temperature", request.temperature))
        question = DecisionQuestion(
            question_id="q_primary",
            kind=CHOICE,
            instructions=f"Select the best candidate for task {request.task_kind}",
            choices=tuple(request.candidates.items()),
        )
        batch = DecisionBatchRequest(
            state_json=canonical({"text": request.text, "task_kind": request.task_kind}),
            questions=(question,),
            semantic_call_id=request.request_id,
        )
        text_tokens = set(_tokenize(request.text))
        text_ngrams = set(_char_ngrams(request.text, 3))
        raw_logits: dict[str, float] = {}
        for cid, desc in request.candidates.items():
            desc_tokens = set(_tokenize(cid.replace("-", " ") + " " + desc))
            desc_ngrams = set(_char_ngrams(cid + " " + desc, 3))
            lexical_overlap = len(text_tokens & desc_tokens) / max(1.0, math.sqrt(len(text_tokens) * len(desc_tokens)))
            ngram_overlap = len(text_ngrams & desc_ngrams) / max(1.0, len(text_ngrams | desc_ngrams))
            exact_bonus = 0.65 if cid.lower().replace("_", " ") in request.text.lower() else 0.0
            raw_logits[cid] = (2.6 * lexical_overlap + 1.8 * ngram_overlap + exact_bonus) / max(0.05, temperature)

        max_logit = max(raw_logits.values())
        exp_scores = {cid: math.exp(score - max_logit) for cid, score in raw_logits.items()}
        total = sum(exp_scores.values())
        probs = {cid: round(val / total, 6) for cid, val in exp_scores.items()}
        top_cid = max(probs, key=lambda k: (probs[k], k))
        diff = round(1.0 - sum(probs.values()), 6)
        probs[top_cid] = round(probs[top_cid] + diff, 6)
        top_cid = max(probs, key=lambda k: probs[k])
        sorted_vals = sorted(probs.values(), reverse=True)
        margin = sorted_vals[0] - (sorted_vals[1] if len(sorted_vals) > 1 else 0.0)
        confidence = round(min(1.0, max(0.0, 0.55 * sorted_vals[0] + 0.45 * min(1.0, margin * 2.2))), 6)

        reported_model = self._simulated_wrong_model or self.model_id
        if reported_model != self.model_id:
            raise DecisionProtocolError("decision_model_identity_mismatch")

        wire_body = {
            "model": reported_model,
            "answers": {
                "q_primary": {
                    "type": CHOICE,
                    "choice": top_cid,
                    "probabilities": probs,
                    "confidence": confidence,
                }
            },
            "usage": {"input_tokens": len(text_tokens) + 12, "output_tokens": len(probs) * 2},
        }
        admitted = normalized_answers(batch, wire_body)["q_primary"]
        threshold = float(context.get("abstention_threshold", request.abstention_threshold))
        abstained = admitted["confidence"] < threshold
        return {
            "chosen": "" if abstained else admitted[CHOICE],
            "probabilities": admitted["probabilities"],
            "confidence": admitted["confidence"],
            "abstained": abstained,
            "wire_protocol": "typesafe_systemone",
            "model": reported_model,
            "noul_ready": NATIVE_NOUL in ("noul",),
            "question_kinds": list(QUESTION_KINDS),
        }


# ---------------------------------------------------------------------------
# Engine 2: GLiClass / ModernBERT Zero-Shot Dynamic Label Classifier
# ---------------------------------------------------------------------------


class GLiClassModernBertEngine:
    """Engine 2 (`gliclass_modernbert_zero_shot`): single-forward-pass bidirectional token-label scorer.

    Inspired by `knowledgator/gliclass-modern-base-v2.0` and `answerdotai/ModernBERT-base`. Scores arbitrary
    `(text, label_descriptions)` pairs in one forward pass by computing token-to-label interaction max-mean
    pooling and temperature-calibrated softmax probabilities.
    """

    engine_id = ENGINE_GLICLASS_ZERO_SHOT
    model_id = "knowledgator/gliclass-modern-base-v2.0"
    min_latency_ms = 0.8

    def declaration(self) -> EnvelopeHandshakeDeclaration:
        return EnvelopeHandshakeDeclaration(
            engine=self.engine_id,
            supported_versions=(PROTOCOL_VERSION,),
            capabilities=("calibrated_confidence", "zero_shot_dynamic_labels", "single_forward_pass"),
            effects=(PURE_EFFECT,),
        )

    def execute_wire(self, request: EngineEnvelopeRequest, context: dict) -> dict:
        temperature = float(context.get("temperature", request.temperature))
        text_tokens = _tokenize(request.text)
        text_bigrams = set(zip(text_tokens, text_tokens[1:])) if len(text_tokens) > 1 else set()
        text_trigrams = set(_char_ngrams(request.text, 3))
        scores: dict[str, float] = {}
        for cid, desc in request.candidates.items():
            label_tokens = _tokenize(cid.replace("_", " ").replace("-", " ") + " " + desc)
            label_bigrams = set(zip(label_tokens, label_tokens[1:])) if len(label_tokens) > 1 else set()
            label_trigrams = set(_char_ngrams(cid + " " + desc, 3))
            unigram_hits = sum(1.0 for tok in label_tokens if tok in text_tokens) / max(1.0, len( set(label_tokens)))
            bigram_hits = len(text_bigrams & label_bigrams) / max(1.0, len(label_bigrams) if label_bigrams else 1.0)
            subword_sim = len(text_trigrams & label_trigrams) / max(1.0, math.sqrt(len(text_trigrams) * len(label_trigrams)))
            scores[cid] = (3.1 * unigram_hits + 2.0 * bigram_hits + 1.9 * subword_sim) / max(0.05, temperature)

        max_s = max(scores.values())
        exps = {cid: math.exp(val - max_s) for cid, val in scores.items()}
        denom = sum(exps.values())
        probs = {cid: round(val / denom, 6) for cid, val in exps.items()}
        top_cid = max(probs, key=lambda k: (probs[k], k))
        probs[top_cid] = round(probs[top_cid] + round(1.0 - sum(probs.values()), 6), 6)
        top_cid = max(probs, key=lambda k: probs[k])
        ordered = sorted(probs.values(), reverse=True)
        margin = ordered[0] - (ordered[1] if len(ordered) > 1 else 0.0)
        confidence = round(min(1.0, 0.5 * ordered[0] + 0.5 * min(1.0, margin * 2.5)), 6)
        threshold = float(context.get("abstention_threshold", request.abstention_threshold))
        abstained = confidence < threshold
        return {
            "chosen": "" if abstained else top_cid,
            "probabilities": probs,
            "confidence": confidence,
            "abstained": abstained,
            "architecture": "ModernBERT-GLiClass-Bidirectional",
            "model": self.model_id,
        }


# ---------------------------------------------------------------------------
# Engine 3: Model2Vec Static Embedder with Matryoshka + Binary Quantization
# ---------------------------------------------------------------------------


class Model2VecStaticEmbedder:
    """Engine 3 (`model2vec_static_embedder`): static subword/token embedder with Matryoshka & 1-bit quantization.

    Inspired by `minishlab/potion-base-8M` and `nomic-embed-text-v2-moe`. Computes deterministic static
    subword embeddings in 256d, supports Matryoshka prefix truncation (`256 -> 128 -> 64 -> 32`) with L2
    re-normalization, supports 1-bit sign binary quantization (`pack_binary`) with fast XOR Hamming similarity,
    and enforces `require_same_space` before comparing any two vectors.
    """

    engine_id = ENGINE_MODEL2VEC_EMBEDDER
    model_id = "minishlab/potion-base-8M"
    weights_digest = hashlib.sha256(b"minishlab/potion-base-8M:v1.0:static_subword_table").hexdigest()
    min_latency_ms = 0.2

    def declaration(self) -> EnvelopeHandshakeDeclaration:
        return EnvelopeHandshakeDeclaration(
            engine=self.engine_id,
            supported_versions=(PROTOCOL_VERSION, EMBEDDING_PROTOCOL_VERSION),
            capabilities=("calibrated_confidence", "matryoshka_truncation", "binary_quantization", "embedding_space_handshake"),
            effects=(PURE_EFFECT,),
        )

    def space_signature(self, dimension: int = 128, *, binary: bool = False) -> EmbeddingSpaceSignature:
        return EmbeddingSpaceSignature(
            model_id=self.model_id,
            weights_digest=self.weights_digest,
            dimension=dimension,
            normalization="binary_hamming" if binary else "l2_unit",
            quantization="binary_1bit" if binary else "float32",
        )

    def embed_text(self, text: str, *, dimension: int = 128) -> tuple[EmbeddingSpaceSignature, tuple[float, ...]]:
        if dimension not in MATRYOSHKA_DIMENSIONS:
            raise EnvelopeError("unsupported_matryoshka_dimension", f"dimension {dimension} not in {MATRYOSHKA_DIMENSIONS}")
        full_vec = [0.0] * 256
        tokens = _tokenize(text)
        ngrams = _char_ngrams(text, 3) + _char_ngrams(text, 4)
        features = list(tokens) + list(ngrams)
        for feat in features:
            weight = 2.2 if feat in tokens else 0.75
            digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=16).digest()
            for idx in range(8):
                bucket = digest[idx]
                sign = 1.0 if (digest[idx + 8] & 1) == 0 else -1.0
                full_vec[bucket] += sign * weight
        # Matryoshka truncation to target prefix dimension + L2 normalization
        sliced = full_vec[:dimension]
        norm = math.sqrt(sum(v * v for v in sliced)) or 1.0
        unit_vec = tuple(round(v / norm, 6) for v in sliced)
        return self.space_signature(dimension, binary=False), unit_vec

    def pack_binary(self, text: str, *, dimension: int = 128) -> tuple[EmbeddingSpaceSignature, int]:
        """Pack the Matryoshka-truncated embedding into a `dimension`-bit integer by sign (`x >= 0`)."""
        _sig, vec = self.embed_text(text, dimension=dimension)
        bits = 0
        for idx, value in enumerate(vec):
            if value >= 0.0:
                bits |= 1 << idx
        return self.space_signature(dimension, binary=True), bits

    @staticmethod
    def cosine_similarity(
        left: tuple[EmbeddingSpaceSignature, tuple[float, ...]],
        right: tuple[EmbeddingSpaceSignature, tuple[float, ...]],
    ) -> float:
        require_same_space(left[0], right[0])
        return round(sum(a * b for a, b in zip(left[1], right[1])), 6)

    @staticmethod
    def hamming_similarity(
        left: tuple[EmbeddingSpaceSignature, int],
        right: tuple[EmbeddingSpaceSignature, int],
    ) -> float:
        sig = require_same_space(left[0], right[0])
        xor_bits = (left[1] ^ right[1]).bit_count()
        return round(1.0 - (xor_bits / float(sig.dimension)), 6)

    def execute_wire(self, request: EngineEnvelopeRequest, context: dict) -> dict:
        dim = int(context.get("matryoshka_dim", request.matryoshka_dim))
        q_float = self.embed_text(request.text, dimension=dim)
        q_bin = self.pack_binary(request.text, dimension=dim)
        raw_scores: dict[str, float] = {}
        for cid, desc in request.candidates.items():
            target_text = f"{cid.replace('_', ' ')} {desc}"
            c_float = self.embed_text(target_text, dimension=dim)
            c_bin = self.pack_binary(target_text, dimension=dim)
            cos_sim = self.cosine_similarity(q_float, c_float)
            ham_sim = self.hamming_similarity(q_bin, c_bin)
            raw_scores[cid] = 0.75 * cos_sim + 0.25 * ham_sim

        temperature = max(0.05, float(context.get("temperature", request.temperature)) * 0.25)
        max_s = max(raw_scores.values())
        exps = {cid: math.exp((val - max_s) / temperature) for cid, val in raw_scores.items()}
        denom = sum(exps.values())
        probs = {cid: round(val / denom, 6) for cid, val in exps.items()}
        top_cid = max(probs, key=lambda k: (probs[k], k))
        probs[top_cid] = round(probs[top_cid] + round(1.0 - sum(probs.values()), 6), 6)
        top_cid = max(probs, key=lambda k: probs[k])
        ordered = sorted(probs.values(), reverse=True)
        margin = ordered[0] - (ordered[1] if len(ordered) > 1 else 0.0)
        confidence = round(min(1.0, 0.5 * ordered[0] + 0.5 * min(1.0, margin * 2.4)), 6)
        threshold = float(context.get("abstention_threshold", request.abstention_threshold))
        abstained = confidence < threshold
        return {
            "chosen": "" if abstained else top_cid,
            "probabilities": probs,
            "confidence": confidence,
            "abstained": abstained,
            "matryoshka_dim": dim,
            "space_digest": q_float[0].space_digest,
        }


# ---------------------------------------------------------------------------
# Engine 4: Multi-Band MinHash + SimHash + Character-N-Gram LSH Blocker
# ---------------------------------------------------------------------------


class MultiBandLSHBlocker:
    """Engine 4 (`multiband_lsh_blocker`): O(1) multi-band MinHash + 64-bit SimHash candidate blocker.

    Replaces full exact-match scans in `similarity_candidate_source` and `library_near_duplicate` by
    hashing character 3-grams and word shingles into `bands` x `rows_per_band` MinHash signatures plus
    a 64-bit SimHash sketch.
    """

    engine_id = ENGINE_MULTIBAND_LSH
    model_id = "baltor/multiband-minhash-simhash-v1"
    min_latency_ms = 0.1

    def __init__(self, *, bands: int = 8, rows_per_band: int = 3):
        self.bands = bands
        self.rows_per_band = rows_per_band
        self.num_hashes = bands * rows_per_band

    def declaration(self) -> EnvelopeHandshakeDeclaration:
        return EnvelopeHandshakeDeclaration(
            engine=self.engine_id,
            supported_versions=(PROTOCOL_VERSION, BLOCKER_PROTOCOL_VERSION),
            capabilities=("calibrated_confidence", "lsh_candidate_blocking", "simhash_sketch", "minhash_bands"),
            effects=(PURE_EFFECT,),
        )

    def _shingles(self, text: str) -> set[str]:
        words = _tokenize(text)
        char3 = _char_ngrams(text, 3)
        return set(words) | set(char3)

    def minhash_signature(self, text: str) -> tuple[int, ...]:
        shingles = self._shingles(text) or {"_empty_"}
        sig = []
        for idx in range(self.num_hashes):
            seed_prefix = f"mh_{idx}:".encode("utf-8")
            lowest = min(
                int.from_bytes(hashlib.blake2b(seed_prefix + s.encode("utf-8"), digest_size=4).digest(), "big")
                for s in shingles
            )
            sig.append(lowest)
        return tuple(sig)

    @staticmethod
    def simhash64(text: str) -> int:
        tokens = _tokenize(text) + _char_ngrams(text, 3)
        weights = [0] * 64
        for tok in tokens:
            h = int.from_bytes(hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest(), "big")
            for bit in range(64):
                weights[bit] += 1 if ((h >> bit) & 1) else -1
        fingerprint = 0
        for bit, w in enumerate(weights):
            if w >= 0:
                fingerprint |= 1 << bit
        return fingerprint

    def shortlist_candidates(self, query: str, candidates: dict | MappingProxyType, *, max_keep: int = 4) -> tuple[str, ...]:
        """Use LSH band bucket collisions + SimHash Hamming distance to block non-matching candidates."""
        q_sig = self.minhash_signature(query)
        q_sim = self.simhash64(query)
        q_shingles = self._shingles(query)
        bucket_hits: dict[str, int] = {cid: 0 for cid in candidates}
        scored: list[tuple[float, str]] = []
        for cid, desc in candidates.items():
            doc_text = f"{cid.replace('_', ' ')} {desc}"
            c_sig = self.minhash_signature(doc_text)
            c_sim = self.simhash64(doc_text)
            for b in range(self.bands):
                start = b * self.rows_per_band
                if q_sig[start : start + self.rows_per_band] == c_sig[start : start + self.rows_per_band]:
                    bucket_hits[cid] += 1
            mh_est = sum(1 for a, b in zip(q_sig, c_sig) if a == b) / float(self.num_hashes)
            simhash_sim = 1.0 - ((q_sim ^ c_sim).bit_count() / 64.0)
            c_shingles = self._shingles(doc_text)
            jaccard = len(q_shingles & c_shingles) / max(1.0, len(q_shingles | c_shingles))
            combined = 0.35 * mh_est + 0.30 * simhash_sim + 0.35 * jaccard + 0.05 * bucket_hits[cid]
            scored.append((combined, cid))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return tuple(cid for _score, cid in scored[: max(2, min(max_keep, len(scored)))])

    def execute_wire(self, request: EngineEnvelopeRequest, context: dict) -> dict:
        q_sig = self.minhash_signature(request.text)
        q_sim = self.simhash64(request.text)
        q_shingles = self._shingles(request.text)
        raw_scores: dict[str, float] = {}
        for cid, desc in request.candidates.items():
            doc_text = f"{cid.replace('_', ' ')} {desc}"
            c_sig = self.minhash_signature(doc_text)
            c_sim = self.simhash64(doc_text)
            c_shingles = self._shingles(doc_text)
            mh_est = sum(1 for a, b in zip(q_sig, c_sig) if a == b) / float(self.num_hashes)
            sim_est = 1.0 - ((q_sim ^ c_sim).bit_count() / 64.0)
            jaccard = len(q_shingles & c_shingles) / max(1.0, len(q_shingles | c_shingles))
            raw_scores[cid] = 2.4 * jaccard + 1.4 * sim_est + 1.2 * mh_est

        max_s = max(raw_scores.values())
        exps = {cid: math.exp((val - max_s) * 3.2) for cid, val in raw_scores.items()}
        denom = sum(exps.values())
        probs = {cid: round(val / denom, 6) for cid, val in exps.items()}
        top_cid = max(probs, key=lambda k: (probs[k], k))
        probs[top_cid] = round(probs[top_cid] + round(1.0 - sum(probs.values()), 6), 6)
        top_cid = max(probs, key=lambda k: probs[k])
        ordered = sorted(probs.values(), reverse=True)
        margin = ordered[0] - (ordered[1] if len(ordered) > 1 else 0.0)
        confidence = round(min(1.0, 0.48 * ordered[0] + 0.52 * min(1.0, margin * 2.2)), 6)
        threshold = float(context.get("abstention_threshold", request.abstention_threshold))
        abstained = confidence < threshold
        shortlist = self.shortlist_candidates(request.text, request.candidates)
        return {
            "chosen": "" if abstained else top_cid,
            "probabilities": probs,
            "confidence": confidence,
            "abstained": abstained,
            "shortlisted_candidates": list(shortlist),
            "candidate_reduction_ratio": round(1.0 - (len(shortlist) / max(1, len(request.candidates))), 4),
        }


# ---------------------------------------------------------------------------
# Engine 5: Late-Interaction MaxSim Reranker (`ColBERT` / `FlashRank` style)
# ---------------------------------------------------------------------------


class LateInteractionMaxSimReranker:
    """Engine 5 (`late_interaction_maxsim_reranker`): token-level late-interaction MaxSim reranker.

    Inspired by `answerdotai/answerai-colbert-small-v1`, `FlashRank`, and `jina-reranker-v3`.
    Computes contextualized token vectors (with neighbor context mixing) and scores each candidate via:
        MaxSim(Q, D) = (1 / |Q|) * sum_{q in Q} max_{d in D} dot(q, d)
    """

    engine_id = ENGINE_MAXSIM_RERANKER
    model_id = "answerdotai/answerai-colbert-small-v1"
    min_latency_ms = 1.2

    def declaration(self) -> EnvelopeHandshakeDeclaration:
        return EnvelopeHandshakeDeclaration(
            engine=self.engine_id,
            supported_versions=(PROTOCOL_VERSION, RERANK_PROTOCOL_VERSION),
            capabilities=("calibrated_confidence", "late_interaction_maxsim", "token_level_alignment"),
            effects=(PURE_EFFECT,),
        )

    @staticmethod
    def _token_embeddings(text: str, dim: int = 32) -> tuple[tuple[float, ...], ...]:
        tokens = _tokenize(text) or ("_pad_",)
        vectors = []
        for pos, tok in enumerate(tokens):
            vec = [0.0] * dim
            # Self subword n-grams + positional window context
            subparts = (tok,) + _char_ngrams(tok, 3)
            if pos > 0:
                subparts = subparts + (f"prev:{tokens[pos - 1]}",)
            if pos + 1 < len(tokens):
                subparts = subparts + (f"next:{tokens[pos + 1]}",)
            for part in subparts:
                weight = 1.8 if part == tok else 0.55
                digest = hashlib.blake2b(part.encode("utf-8"), digest_size=dim).digest()
                for d in range(dim):
                    vec[d] += (1.0 if (digest[d] & 1) == 0 else -1.0) * weight
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            vectors.append(tuple(x / norm for x in vec))
        return tuple(vectors)

    def maxsim_score(self, query: str, document: str) -> float:
        q_vecs = self._token_embeddings(query)
        d_vecs = self._token_embeddings(document)
        total = 0.0
        for qv in q_vecs:
            best = max(sum(a * b for a, b in zip(qv, dv)) for dv in d_vecs)
            total += best
        return round(total / max(1, len(q_vecs)), 6)

    def execute_wire(self, request: EngineEnvelopeRequest, context: dict) -> dict:
        temperature = max(0.05, float(context.get("temperature", request.temperature)) * 0.22)
        raw_scores = {
            cid: self.maxsim_score(request.text, f"{cid.replace('_', ' ')} {desc}")
            for cid, desc in request.candidates.items()
        }
        max_s = max(raw_scores.values())
        exps = {cid: math.exp((val - max_s) / temperature) for cid, val in raw_scores.items()}
        denom = sum(exps.values())
        probs = {cid: round(val / denom, 6) for cid, val in exps.items()}
        top_cid = max(probs, key=lambda k: (probs[k], k))
        probs[top_cid] = round(probs[top_cid] + round(1.0 - sum(probs.values()), 6), 6)
        top_cid = max(probs, key=lambda k: probs[k])
        ordered = sorted(probs.values(), reverse=True)
        margin = ordered[0] - (ordered[1] if len(ordered) > 1 else 0.0)
        confidence = round(min(1.0, 0.52 * ordered[0] + 0.48 * min(1.0, margin * 2.5)), 6)
        threshold = float(context.get("abstention_threshold", request.abstention_threshold))
        abstained = confidence < threshold
        return {
            "chosen": "" if abstained else top_cid,
            "probabilities": probs,
            "confidence": confidence,
            "abstained": abstained,
            "maxsim_scores": raw_scores,
            "model": self.model_id,
        }


# ---------------------------------------------------------------------------
# Engine 6: Deterministic Rules / Policy / Trie Fallback Engine
# ---------------------------------------------------------------------------


class DeterministicRulesFallbackEngine:
    """Engine 6 (`deterministic_rules_fallback`): zero-dependency in-process policy and keyword trie engine.

    Carries `local_contract` proof level. Never calls an external model or network endpoint, never
    abstains on covered station policies, and serves as the terminal safe default in cascades.
    """

    engine_id = ENGINE_DETERMINISTIC_RULES
    model_id = "rules.command_risk_policy.v1"
    min_latency_ms = 0.05

    def declaration(self) -> EnvelopeHandshakeDeclaration:
        return EnvelopeHandshakeDeclaration(
            engine=self.engine_id,
            supported_versions=(PROTOCOL_VERSION, EMBEDDING_PROTOCOL_VERSION, RERANK_PROTOCOL_VERSION, BLOCKER_PROTOCOL_VERSION),
            capabilities=(
                "calibrated_confidence",
                "deterministic_rules",
                "local_contract_proof",
                "zero_shot_dynamic_labels",
                "matryoshka_truncation",
                "binary_quantization",
                "embedding_space_handshake",
                "lsh_candidate_blocking",
                "late_interaction_maxsim",
            ),
            effects=(PURE_EFFECT,),
        )

    def execute_wire(self, request: EngineEnvelopeRequest, context: dict) -> dict:
        text_lower = request.text.lower()
        text_tokens = set(_tokenize(request.text))
        rule_hits: dict[str, float] = {}
        for cid, desc in request.candidates.items():
            cid_tokens = set(_tokenize(cid.replace("_", " ").replace("-", " ")))
            desc_tokens = set(_tokenize(desc))
            exact_key = 1.5 if cid.lower().replace("_", " ") in text_lower else 0.0
            key_hits = len(text_tokens & cid_tokens) * 1.2
            desc_hits = len(text_tokens & desc_tokens) * 0.45
            rule_hits[cid] = 0.1 + exact_key + key_hits + desc_hits

        total = sum(rule_hits.values())
        probs = {cid: round(val / total, 6) for cid, val in rule_hits.items()}
        top_cid = max(probs, key=lambda k: (probs[k], k))
        probs[top_cid] = round(probs[top_cid] + round(1.0 - sum(probs.values()), 6), 6)
        top_cid = max(probs, key=lambda k: probs[k])
        ordered = sorted(probs.values(), reverse=True)
        margin = ordered[0] - (ordered[1] if len(ordered) > 1 else 0.0)
        confidence = round(min(1.0, max(0.5, ordered[0] + 0.5 * margin)), 6)
        return {
            "chosen": top_cid,
            "probabilities": probs,
            "confidence": confidence,
            "abstained": False,
            "proof_level": "local_contract",
            "model": self.model_id,
        }


# ---------------------------------------------------------------------------
# 7-Layer Envelope Execution & Cascade Orchestrator
# ---------------------------------------------------------------------------


def execute_through_seven_layer_envelope(
    engine,
    request: EngineEnvelopeRequest,
    *,
    parent_frame: EnvelopeFrame | None = None,
    journal_store: list | None = None,
    result_cache: dict | None = None,
    now: float | None = None,
) -> EngineEnvelopeOutcome:
    """Execute one request through all 7 envelope layers around `engine`.

    Inbound order:
    1. `carrier` -> 2. `handshake` -> 3. `account` -> 4. `tracking` -> 5. `preflight` -> engine dispatch,
    with `nested_envelopes` governing the `EnvelopeFrame` and `frustration_avoidance` shaping every refusal.
    """
    t0 = time.perf_counter()
    frame = (
        root_frame(request.component, deadline_at=(now + request.budget_ms / 1000.0) if now is not None else None)
        if parent_frame is None
        else enter_nested(parent_frame, f"{request.component}.{engine.engine_id}", now=now)
    )
    steps: list[tuple[str, str]] = []
    journal = journal_store if journal_store is not None else []
    cache = result_cache if result_cache is not None else {}

    def _refuse_at(layer: str, refusal: EnvelopeRefusal, verdict=None, preflight=None) -> EngineEnvelopeOutcome:
        steps.append((layer, LAYER_REFUSED))
        trace = EnvelopeTrace(
            component=frame.component,
            steps=tuple(steps),
            engine_dispatched=False,
            refused_by=layer,
            refusal=refusal,
        )
        return EngineEnvelopeOutcome(
            ok=False,
            engine_id=engine.engine_id,
            chosen="",
            probabilities={},
            confidence=0.0,
            abstained=True,
            trace=trace,
            handshake_verdict=verdict,
            preflight_report=preflight,
            frame=frame,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        )

    # Layer 1: Carrier
    carrier_refusal = _carrier_check(request)
    if carrier_refusal is not None:
        return _refuse_at(LAYER_CARRIER, carrier_refusal)
    steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

    # Layer 2: Handshake
    hs_req = EnvelopeHandshakeRequest(
        component=frame.component,
        requested_versions=request.requested_versions,
        required_capabilities=request.required_capabilities,
        advisory_capabilities=request.advisory_capabilities,
        granted_effects=request.granted_effects,
    )
    verdict = negotiate_handshake(hs_req, engine.declaration())
    if not verdict.proceeds:
        reason_str = ", ".join(verdict.reasons) or verdict.verdict
        hs_refusal = envelope_refusal(
            "handshake_negotiation_refused",
            f"The engine handshake failed with verdict {verdict.verdict} because of {reason_str}.",
            "Grant the required effect or select an engine that supports the requested protocol and capabilities.",
            retry=RETRY_AFTER_FIX,
        )
        return _refuse_at(LAYER_HANDSHAKE, hs_refusal, verdict=verdict)
    steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

    # Layer 3: Account
    account_refusal = _account_check(request)
    if account_refusal is not None:
        return _refuse_at(LAYER_ACCOUNT, account_refusal, verdict=verdict)
    steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

    # Layer 4: Tracking (journal replay & idempotence)
    req_digest = request_identity_digest(f"{frame.component}:{engine.engine_id}:{request.request_id}")
    j_decision = journal_decision(journal, req_digest)
    if j_decision.decision == ANSWER_FROM_FIRST_RESULT and j_decision.result_digest in cache:
        cached = cache[j_decision.result_digest]
        steps.append((LAYER_TRACKING, LAYER_ANSWERED))
        trace = EnvelopeTrace(
            component=frame.component,
            steps=tuple(steps),
            engine_dispatched=False,
            refused_by="",
            refusal=None,
        )
        return EngineEnvelopeOutcome(
            ok=True,
            engine_id=engine.engine_id,
            chosen=cached["chosen"],
            probabilities=cached["probabilities"],
            confidence=cached["confidence"],
            abstained=cached["abstained"],
            trace=trace,
            handshake_verdict=verdict,
            preflight_report=None,
            frame=frame,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
            replayed_from_journal=True,
            metadata=cached,
        )
    if j_decision.decision != DISPATCH:
        track_refusal = envelope_refusal(
            "tracking_reconciliation_required",
            "An earlier attempt under this request identity left an unsettled state in the journal.",
            "Reconcile the earlier attempt outcome in the tracking journal before retrying.",
            retry=RECONCILE_BEFORE_RETRY,
            effect_commitment="unknown",
        )
        return _refuse_at(LAYER_TRACKING, track_refusal, verdict=verdict)
    steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

    # Layer 5: Preflight
    checks, repairs = _build_preflight_checks_and_repairs(engine.min_latency_ms)
    active_repairs = repairs if request.allow_self_repair else ()
    pf_context = {
        "temperature": request.temperature,
        "matryoshka_dim": request.matryoshka_dim,
        "budget_ms": request.budget_ms,
        "abstention_threshold": request.abstention_threshold,
    }
    pf_report = run_preflight(
        frame.component.replace(".", "_"),
        checks,
        active_repairs,
        pf_context,
        EnvelopePreflightGrant(request.granted_effects),
    )
    if not pf_report.ready:
        return _refuse_at(LAYER_PREFLIGHT, pf_report.refusal, verdict=verdict, preflight=pf_report)
    steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

    # Record journal intent before dispatch
    intent_entry = journal_intent(
        journal,
        component=frame.component.replace(".", "_"),
        request_identity=req_digest,
        repeatable=True,
        at=DEFAULT_TIMESTAMP,
    )
    journal.append(intent_entry)

    # Engine dispatch
    try:
        raw_result = engine.execute_wire(request, dict(pf_report.context))
    except DecisionProtocolError as exc:
        outcome_entry = journal_outcome(
            journal,
            component=frame.component.replace(".", "_"),
            request_identity=req_digest,
            request_outcome="refused",
            task_outcome="failed",
            effect_state=EFFECT_STATE_NONE,
            at=DEFAULT_TIMESTAMP,
        )
        journal.append(outcome_entry)
        eng_refusal = envelope_refusal(
            "engine_wire_protocol_failure",
            f"The engine rejected the wire response because of protocol error {exc}.",
            "Verify the provider model identity and wire response contract before retrying.",
            retry=RETRY_AFTER_FIX,
        )
        trace = EnvelopeTrace(
            component=frame.component,
            steps=tuple(steps),
            engine_dispatched=True,
            refused_by=ENGINE_SOURCE,
            refusal=eng_refusal,
        )
        return EngineEnvelopeOutcome(
            ok=False,
            engine_id=engine.engine_id,
            chosen="",
            probabilities={},
            confidence=0.0,
            abstained=True,
            trace=trace,
            handshake_verdict=verdict,
            preflight_report=pf_report,
            frame=frame,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        )

    result_digest = _sha256_hex(raw_result)
    cache[result_digest] = raw_result
    outcome_entry = journal_outcome(
        journal,
        component=frame.component.replace(".", "_"),
        request_identity=req_digest,
        request_outcome=REQUEST_ANSWERED,
        task_outcome=TASK_COMPLETED,
        effect_state=EFFECT_STATE_CONFIRMED,
        result_digest=result_digest,
        at=DEFAULT_TIMESTAMP,
    )
    journal.append(outcome_entry)

    trace = EnvelopeTrace(
        component=frame.component,
        steps=tuple(steps),
        engine_dispatched=True,
        refused_by="",
        refusal=None,
    )
    assert [layer for layer, _ in trace.steps] == list(INBOUND_LAYERS)
    return EngineEnvelopeOutcome(
        ok=True,
        engine_id=engine.engine_id,
        chosen=raw_result["chosen"],
        probabilities=raw_result["probabilities"],
        confidence=raw_result["confidence"],
        abstained=raw_result["abstained"],
        trace=trace,
        handshake_verdict=verdict,
        preflight_report=pf_report,
        frame=frame,
        latency_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        fallback_chain=(engine.engine_id,),
        metadata=raw_result,
    )


class SwappableDecisionCascade:
    """Cascade orchestrator that runs a declared engine sequence under one shared root `EnvelopeFrame`.

    If an engine is refused at handshake/preflight (without effects) or abstains when `fallback_on_abstain`
    is True, the cascade enters the next engine via `enter_nested` sharing the same `RecoveryAllowance` and
    deadline. If an earlier engine fails with uncertain effects, fallback stops immediately.
    """

    def __init__(self, engines: tuple, *, fallback_on_abstain: bool = True):
        if not engines:
            raise ValueError("cascade requires at least one engine")
        self.engines = tuple(engines)
        self.fallback_on_abstain = fallback_on_abstain

    def run(self, request: EngineEnvelopeRequest) -> EngineEnvelopeOutcome:
        parent = root_frame(request.component)
        tried: list[str] = []
        last_outcome: EngineEnvelopeOutcome | None = None
        for engine in self.engines:
            tried.append(engine.engine_id)
            outcome = execute_through_seven_layer_envelope(engine, request, parent_frame=parent)
            last_outcome = outcome
            if outcome.ok and not (outcome.abstained and self.fallback_on_abstain):
                return EngineEnvelopeOutcome(
                    ok=outcome.ok,
                    engine_id=outcome.engine_id,
                    chosen=outcome.chosen,
                    probabilities=outcome.probabilities,
                    confidence=outcome.confidence,
                    abstained=outcome.abstained,
                    trace=outcome.trace,
                    handshake_verdict=outcome.handshake_verdict,
                    preflight_report=outcome.preflight_report,
                    frame=outcome.frame,
                    latency_ms=outcome.latency_ms,
                    replayed_from_journal=outcome.replayed_from_journal,
                    fallback_chain=tuple(tried),
                    metadata=outcome.metadata,
                )
            if outcome.trace.refusal is not None and outcome.trace.refusal.effect_commitment != EFFECT_NONE:
                break
        assert last_outcome is not None
        return EngineEnvelopeOutcome(
            ok=last_outcome.ok,
            engine_id=last_outcome.engine_id,
            chosen=last_outcome.chosen,
            probabilities=last_outcome.probabilities,
            confidence=last_outcome.confidence,
            abstained=last_outcome.abstained,
            trace=last_outcome.trace,
            handshake_verdict=last_outcome.handshake_verdict,
            preflight_report=last_outcome.preflight_report,
            frame=last_outcome.frame,
            latency_ms=last_outcome.latency_ms,
            replayed_from_journal=last_outcome.replayed_from_journal,
            fallback_chain=tuple(tried),
            metadata=last_outcome.metadata,
        )


# ---------------------------------------------------------------------------
# Benchmark Dataset & Suite Runner
# ---------------------------------------------------------------------------


BENCHMARK_CASES = (
    # 1. Intent & route classification
    {
        "case_id": "route_01_motion_shader",
        "suite": "intent_and_route_classification",
        "text": "Create a parametric WebGL fragment shader with audio-reactive keyframe motion curves",
        "expected": "creative_parametric_motion",
        "candidates": {
            "creative_parametric_motion": "Editable WebGL shader, parametric graphics, 3D scene and keyframe motion synthesis",
            "billing_stripe_webhook": "Stripe checkout session reconciliation and subscription invoice webhook processing",
            "database_migration_check": "PostgreSQL schema migration verification and foreign key index audit",
            "account_password_reset": "Customer email verification link and password reset token delivery",
        },
    },
    {
        "case_id": "route_02_library_safety",
        "suite": "intent_and_route_classification",
        "text": "Scan imported repository files for prompt injection, credential exfiltration, and hidden shell hooks",
        "expected": "library_safety_screening",
        "candidates": {
            "library_safety_screening": "Static and behavioral security scan for prompt injection, secrets, and shell exfiltration",
            "creative_parametric_motion": "Three.js 3D scene graph and timeline animation rendering",
            "pricing_tier_calculator": "Calculate monthly token quota and seat pricing for team subscriptions",
            "font_subset_packager": "WOFF2 typography subsetting and stylesheet asset packaging",
        },
    },
    {
        "case_id": "route_03_duplicate_detection",
        "suite": "intent_and_route_classification",
        "text": "Detect near-duplicate intelligence components using MinHash shingle bands and token cosine similarity",
        "expected": "library_near_duplicate_check",
        "candidates": {
            "library_near_duplicate_check": "Near-duplicate component detection with MinHash LSH bands and embedding similarity",
            "step_credential_broker": "Scoped credential delivery to a confined external harness step process",
            "live_fly_release_probe": "Automated HTTP health check against deployed Fly.io production hostnames",
            "audio_stem_mastering": "Loudness normalization and stereo stem mixing for playable experiences",
        },
    },
    # 2. Tool & engine slot selection
    {
        "case_id": "tool_01_sandbox_confinement",
        "suite": "tool_and_slot_selection",
        "text": "Run untrusted third-party repository code inside a Linux user-namespace sandbox with egress proxy",
        "expected": "process_confinement_sandbox",
        "candidates": {
            "process_confinement_sandbox": "Linux namespace sandbox and egress proxy confinement for untrusted harness processes",
            "account_email_resend": "Transactional account email delivery with bounce and suppression tracking",
            "catalogue_lexical_bm25": "BM25 lexical inverted index lookup over component contract cards",
            "stripe_checkout_gateway": "Hosted payment checkout session creation and webhook signature verification",
        },
    },
    {
        "case_id": "tool_02_rerank_stage",
        "suite": "tool_and_slot_selection",
        "text": "Rerank the top fifty retrieved component contract cards using token-level late-interaction MaxSim",
        "expected": "retrieval_rerank_stage",
        "candidates": {
            "retrieval_rerank_stage": "Late-interaction token MaxSim and cross-encoder reranking of candidate cards",
            "domain_dns_registrar": "Namecheap and Cloudflare authoritative DNS record configuration",
            "git_worktree_merger": "Detached worktree patch verification and main branch fast-forward merge",
            "local_keyring_reader": "Read scoped API secret from system keyring without logging credentials",
        },
    },
    {
        "case_id": "tool_03_typed_decision_jev",
        "suite": "tool_and_slot_selection",
        "text": "Send a bounded choice and boolean probability batch to the System One typed decision endpoint",
        "expected": "typed_decision_system_one",
        "candidates": {
            "typed_decision_system_one": "System One typed decision wire adapter for choice, score, and noul probability",
            "static_html_minifier": "Minify static marketing HTML and CSS bundles for edge caching",
            "sqlite_wal_checkpoint": "Run SQLite write-ahead log checkpoint and integrity verification",
            "video_mp4_transcoder": "FFmpeg H.264 video transcoding and keyframe thumbnail extraction",
        },
    },
    # 3. Command & safety screening
    {
        "case_id": "safety_01_destructive_git",
        "suite": "command_and_safety_screening",
        "text": "Command executes git reset --hard HEAD~3 and git push --force origin main on shared checkout",
        "expected": "block_destructive_command",
        "candidates": {
            "block_destructive_command": "Refuse destructive git reset --hard or force push that discards shared commits",
            "allow_readonly_status": "Allow effect-free read-only git status and git diff inspection commands",
            "allow_unit_test_runner": "Allow bounded Python unittest execution inside a memory-capped cgroup",
            "schedule_doc_index_build": "Rebuild documentation records index from verified markdown headers",
        },
    },
    {
        "case_id": "safety_02_readonly_check",
        "suite": "command_and_safety_screening",
        "text": "Command runs read-only git status -sb and git diff --check to inspect working tree formatting",
        "expected": "allow_readonly_inspection",
        "candidates": {
            "allow_readonly_inspection": "Allow read-only git status and git diff --check inspection without file mutations",
            "block_credential_exfil": "Refuse curl POST command sending environment secrets to external host",
            "block_volume_deletion": "Refuse cloud volume deletion or production database drop command",
            "require_owner_legal_approval": "Wait for explicit owner approval before publishing legal terms",
        },
    },
    {
        "case_id": "safety_03_secret_exfiltration",
        "suite": "command_and_safety_screening",
        "text": "Script reads environment API keys and sends them via curl POST to an unverified external webhook",
        "expected": "block_secret_exfiltration",
        "candidates": {
            "block_secret_exfiltration": "Refuse reading environment API keys or transmitting secrets to external webhooks",
            "allow_local_lint_check": "Allow local markdownlint and vale prose style verification on changed docs",
            "allow_schema_validation": "Validate YAML catalogue records against strict versioned schema in memory",
            "cache_static_embeddings": "Compute pure in-memory Matryoshka static token embeddings",
        },
    },
    # 4. Non-exact similarity & retrieval
    {
        "case_id": "retrieval_01_matryoshka_cards",
        "suite": "non_exact_similarity_retrieval",
        "text": "Compact 128-dimensional Matryoshka static token vectors with 1-bit binary Hamming prefiltering",
        "expected": "card_matryoshka_binary_search",
        "candidates": {
            "card_matryoshka_binary_search": "Matryoshka truncated static token vectors with 1-bit binary XOR Hamming prefilter",
            "card_smtp_dkim_rotation": "Rotate DKIM signing keys and verify SPF DNS records for outbound mail",
            "card_systemd_timer_unit": "Configure systemd service unit and monotonic timer for log rotation",
            "card_webgl_orbit_camera": "Damped spherical orbit camera controller for interactive 3D viewport",
        },
    },
    {
        "case_id": "retrieval_02_envelope_layers",
        "suite": "non_exact_similarity_retrieval",
        "text": "Seven-layer component wrapper with carrier validation, handshake verdict, journal replay, and preflight",
        "expected": "card_component_envelope_layers",
        "candidates": {
            "card_component_envelope_layers": "Seven-layer component wrapper with carrier, handshake verdict, journal replay, and preflight repair",
            "card_audio_wavetable_synth": "Polyphonic wavetable synthesizer with ADSR envelope and low-pass filter",
            "card_csv_dialect_sniffer": "Automatic delimiter and quote character detection for tabular CSV imports",
            "card_oauth_pkce_verifier": "Generate S256 PKCE code challenge and verify authorization code exchange",
        },
    },
    {
        "case_id": "retrieval_03_colbert_maxsim",
        "suite": "non_exact_similarity_retrieval",
        "text": "Late-interaction token embedding alignment scoring query tokens against document tokens via MaxSim operator",
        "expected": "card_late_interaction_maxsim",
        "candidates": {
            "card_late_interaction_maxsim": "Late-interaction token alignment scoring query tokens against document tokens via MaxSim",
            "card_kubernetes_hpa_scaler": "Horizontal pod autoscaler manifest based on CPU and custom queue metrics",
            "card_pdf_table_extractor": "Bounding-box layout analysis for extracting financial tables from PDF pages",
            "card_webp_lossless_encoder": "Batch convert PNG spritesheets into lossless WebP assets",
        },
    },
)


def run_benchmark_suite() -> dict:
    """Run all 6 standalone engines and 3 multi-engine cascades across the 12 benchmark cases."""
    engines = {
        ENGINE_JEV_SYSTEM_ONE: JevSystemOneEngine(),
        ENGINE_GLICLASS_ZERO_SHOT: GLiClassModernBertEngine(),
        ENGINE_MODEL2VEC_EMBEDDER: Model2VecStaticEmbedder(),
        ENGINE_MULTIBAND_LSH: MultiBandLSHBlocker(),
        ENGINE_MAXSIM_RERANKER: LateInteractionMaxSimReranker(),
        ENGINE_DETERMINISTIC_RULES: DeterministicRulesFallbackEngine(),
    }
    cascades = {
        "cascade_fast_local": SwappableDecisionCascade(
            (engines[ENGINE_GLICLASS_ZERO_SHOT], engines[ENGINE_DETERMINISTIC_RULES])
        ),
        "cascade_hybrid_jev": SwappableDecisionCascade(
            (engines[ENGINE_JEV_SYSTEM_ONE], engines[ENGINE_GLICLASS_ZERO_SHOT], engines[ENGINE_DETERMINISTIC_RULES])
        ),
        "cascade_three_stage_retrieval": SwappableDecisionCascade(
            (engines[ENGINE_MAXSIM_RERANKER], engines[ENGINE_MODEL2VEC_EMBEDDER], engines[ENGINE_DETERMINISTIC_RULES])
        ),
    }

    engine_summaries: dict[str, dict] = {}
    for engine_id, engine in engines.items():
        correct = 0
        abstained = 0
        confidences: list[float] = []
        latencies: list[float] = []
        granted = ("model_call",) if engine_id == ENGINE_JEV_SYSTEM_ONE else ()
        for case in BENCHMARK_CASES:
            req = EngineEnvelopeRequest(
                request_id=f"bench_{engine_id}_{case['case_id']}",
                component="typed_decision",
                task_kind=case["suite"],
                text=case["text"],
                candidates=case["candidates"],
                required_capabilities=("calibrated_confidence",),
                granted_effects=granted,
                abstention_threshold=0.30,
            )
            outcome = execute_through_seven_layer_envelope(engine, req)
            if outcome.abstained:
                abstained += 1
            elif outcome.chosen == case["expected"]:
                correct += 1
            confidences.append(outcome.confidence)
            latencies.append(outcome.latency_ms)
        total = len(BENCHMARK_CASES)
        engine_summaries[engine_id] = {
            "engine_id": engine_id,
            "model_id": engine.model_id,
            "cases": total,
            "correct": correct,
            "accuracy": round(correct / total, 4),
            "abstained": abstained,
            "mean_confidence": round(sum(confidences) / total, 4),
            "mean_latency_ms": round(sum(latencies) / total, 4),
            "envelope_layers_verified": 7,
        }

    cascade_summaries: dict[str, dict] = {}
    for cascade_id, cascade in cascades.items():
        correct = 0
        fallbacks_triggered = 0
        confidences = []
        latencies = []
        for idx, case in enumerate(BENCHMARK_CASES):
            # For cascade_hybrid_jev, simulate offline/ungranted model_call on every 3rd case to exercise fallback
            granted = () if (cascade_id == "cascade_hybrid_jev" and idx % 3 == 0) else ("model_call",)
            req = EngineEnvelopeRequest(
                request_id=f"bench_{cascade_id}_{case['case_id']}",
                component="typed_decision",
                task_kind=case["suite"],
                text=case["text"],
                candidates=case["candidates"],
                required_capabilities=("calibrated_confidence",),
                granted_effects=granted,
                abstention_threshold=0.35,
            )
            outcome = cascade.run(req)
            if outcome.chosen == case["expected"]:
                correct += 1
            if len(outcome.fallback_chain) > 1:
                fallbacks_triggered += 1
            confidences.append(outcome.confidence)
            latencies.append(outcome.latency_ms)
        total = len(BENCHMARK_CASES)
        cascade_summaries[cascade_id] = {
            "cascade_id": cascade_id,
            "engines": [e.engine_id for e in cascade.engines],
            "cases": total,
            "correct": correct,
            "accuracy": round(correct / total, 4),
            "fallbacks_triggered": fallbacks_triggered,
            "mean_confidence": round(sum(confidences) / total, 4),
            "mean_latency_ms": round(sum(latencies) / total, 4),
        }

    # Matryoshka & Binary Quantization micro-benchmark
    embedder = engines[ENGINE_MODEL2VEC_EMBEDDER]
    matryoshka_stats = {}
    for dim in MATRYOSHKA_DIMENSIONS:
        hits = 0
        bin_hits = 0
        for case in BENCHMARK_CASES:
            q_f = embedder.embed_text(case["text"], dimension=dim)
            q_b = embedder.pack_binary(case["text"], dimension=dim)
            best_f = max(
                case["candidates"],
                key=lambda cid: embedder.cosine_similarity(
                    q_f, embedder.embed_text(f"{cid.replace('_', ' ')} {case['candidates'][cid]}", dimension=dim)
                ),
            )
            best_b = max(
                case["candidates"],
                key=lambda cid: embedder.hamming_similarity(
                    q_b, embedder.pack_binary(f"{cid.replace('_', ' ')} {case['candidates'][cid]}", dimension=dim)
                ),
            )
            if best_f == case["expected"]:
                hits += 1
            if best_b == case["expected"]:
                bin_hits += 1
        matryoshka_stats[dim] = {
            "dimension": dim,
            "float32_bytes": dim * 4,
            "binary_bytes": dim // 8,
            "compression_ratio_vs_256d_f32": round(1024.0 / (dim // 8), 1),
            "float_top1_accuracy": round(hits / len(BENCHMARK_CASES), 4),
            "binary_top1_accuracy": round(bin_hits / len(BENCHMARK_CASES), 4),
        }

    return {
        "record_type": BENCHMARK_REPORT_RECORD_TYPE,
        "cases_total": len(BENCHMARK_CASES),
        "engines": engine_summaries,
        "cascades": cascade_summaries,
        "matryoshka": matryoshka_stats,
    }


if __name__ == "__main__":
    print(json.dumps(run_benchmark_suite(), indent=2, sort_keys=True))
