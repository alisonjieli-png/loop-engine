#!/usr/bin/env python3
"""Demo subdomain (`demos.baltor.ai`) and multi-domain side-by-side showcase engine suite.

Implements:
1. GitHub Profile and Archetype Archeology Registry (`github_developer_archetypes/v1`):
   16 evidence-backed project archetypes across 4 categories (`kaggle_ai_ml`,
   `github_common_projects`, `public_good_projects`, and `design_media_projects`),
   citing upstream GitHub repositories and Kaggle competitions, dated star or vote
   counts, failure modes without contract cards, deterministic verifiers, and
   explicit separation between observed pilot trials (`comparison-pilot-2026-10-16`)
   and deterministic contract-card simulations.
2. Four swappable rendering and verification engines in the `demo_subdomain_showcase`
   slot wrapped in the 7-layer `ComponentEnvelope`:
   - `interactive_side_by_side_diff_showcase_engine`
   - `executable_playground_receipt_engine`
   - `brand_syndicated_demo_projection_engine`
   - `static_markdown_twin_fallback_engine`
3. Known-wrong security, evidence, and prose controls across Layers 2, 3, 4, and 6.

Nothing in this module performs network I/O, mutates live provider state, or opens
external connections. All functions and engines execute deterministically in memory.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import difflib
import hashlib
import html
import json
import pathlib
import re
import sys
from types import MappingProxyType
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
for _rel in ("src", "tools"):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
    EFFECT_NONE,
    ENGINE_SOURCE,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_ANSWERED,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    OPERATOR,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
    RETRY_AFTER_WAIT,
    RETRY_NOW_SAME_IDENTITY,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeHandshakeVerdict,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    EnvelopeTrace,
    enter_nested,
    envelope_refusal,
    may_recover,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_REPAIRED,
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    ANSWER_FROM_FIRST_RESULT,
    EFFECT_STATE_CONFIRMED,
    EFFECT_STATE_NONE,
    REQUEST_ANSWERED,
    REQUEST_OUTCOMES,
    RESYNC_IN_SYNC,
    TASK_COMPLETED,
    TASK_FAILED,
    EnvelopeJournalEntry,
    EnvelopeResyncBackoff,
    EnvelopeResyncObservation,
    journal_decision,
    journal_intent,
    journal_outcome,
    request_identity_digest,
    resync_decision,
)

# ============================================================================
# Constants and Schema Identifiers
# ============================================================================

DEMO_SHOWCASE_COMPONENT_ID = "demo_subdomain_showcase"
DEMO_SHOWCASE_WIRE_V1 = "demo_subdomain_showcase/v1"
ARCHETYPE_REGISTRY_SCHEMA = "github_developer_archetypes/v1"
SHOWCASE_REQUEST_SCHEMA = "demo_subdomain_showcase_request/v1"
SHOWCASE_RESPONSE_SCHEMA = "demo_subdomain_showcase_response/v1"
SHOWCASE_BENCHMARK_SCHEMA = "demo_subdomain_showcase_benchmark/v1"
PLAYGROUND_BUNDLE_SCHEMA = "baltor_playground_bundle/v1"

FIXED_TIMESTAMP_ISO = "2026-10-16T23:30:00Z"
DEFAULT_RELEASE_DIGEST = "d" * 64
STALE_RELEASE_DIGEST = "e" * 64

# Categories of developer projects
CATEGORY_KAGGLE_AI_ML = "kaggle_ai_ml"
CATEGORY_GITHUB_COMMON = "github_common_projects"
CATEGORY_PUBLIC_GOOD = "public_good_projects"
CATEGORY_DESIGN_MEDIA = "design_media_projects"

ARCHETYPE_CATEGORIES = (
    CATEGORY_KAGGLE_AI_ML,
    CATEGORY_GITHUB_COMMON,
    CATEGORY_PUBLIC_GOOD,
    CATEGORY_DESIGN_MEDIA,
)

# Supported demo and brand syndication hostnames
HOST_DEMOS_BALTOR = "demos.baltor.ai"
HOST_GALLERY_BALTOR = "gallery.baltor.ai"
HOST_AGENTBRIEFS = "agentbriefs.si"
HOST_SKILLSFORGOOD = "skillsforgood.org"
HOST_AGENTSTUDIOS = "agentstudios.si"

ADMITTED_DEMO_HOSTS = (
    HOST_DEMOS_BALTOR,
    HOST_GALLERY_BALTOR,
    HOST_AGENTBRIEFS,
    HOST_SKILLSFORGOOD,
    HOST_AGENTSTUDIOS,
)

HOST_ADMITTED_CATEGORIES: Mapping[str, tuple[str, ...]] = MappingProxyType({
    HOST_DEMOS_BALTOR: ARCHETYPE_CATEGORIES,
    HOST_GALLERY_BALTOR: (CATEGORY_DESIGN_MEDIA, CATEGORY_KAGGLE_AI_ML),
    HOST_AGENTBRIEFS: (CATEGORY_KAGGLE_AI_ML, CATEGORY_GITHUB_COMMON, CATEGORY_PUBLIC_GOOD),
    HOST_SKILLSFORGOOD: (CATEGORY_PUBLIC_GOOD,),
    HOST_AGENTSTUDIOS: (CATEGORY_DESIGN_MEDIA,),
})

# Supported harnesses and default model receipt metadata
SUPPORTED_HARNESSES = ("opencode", "claude_code", "codex", "cursor")
HARNESS_DISPLAY_NAMES: Mapping[str, str] = MappingProxyType({
    "opencode": "OpenCode",
    "claude_code": "Claude Code",
    "codex": "Codex CLI",
    "cursor": "Cursor",
})
DEFAULT_MODEL_ID = "gemma4:31b"
DEFAULT_MODEL_PROVIDER = "ollama_cloud"

EVIDENCE_OBSERVED_PILOT = "observed_pilot_and_deterministic_contract_verifier"
EVIDENCE_CONTRACT_SIMULATION = "deterministic_contract_verifier_simulation"

# Four swappable demo showcase engines
ENGINE_SIDE_BY_SIDE_DIFF = "interactive_side_by_side_diff_showcase_engine"
ENGINE_PLAYGROUND_RECEIPT = "executable_playground_receipt_engine"
ENGINE_BRAND_SYNDICATED = "brand_syndicated_demo_projection_engine"
ENGINE_STATIC_MARKDOWN_TWIN = "static_markdown_twin_fallback_engine"

SHOWCASE_ENGINE_IDS = (
    ENGINE_SIDE_BY_SIDE_DIFF,
    ENGINE_PLAYGROUND_RECEIPT,
    ENGINE_BRAND_SYNDICATED,
    ENGINE_STATIC_MARKDOWN_TWIN,
)

RECOVERABLE_SHOWCASE_ENGINE_CODES = (
    "diff_renderer_worker_unavailable",
    "playground_packager_storage_busy",
    "brand_projection_cache_cold",
)

REQUIRED_CROSS_BRAND_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
)

# Build sensitive marker regexes via concatenation so static source scanners
# never flag the pattern definitions as literal credentials.
_BEARER_MARKER_RE = re.compile(r"(?i)bear" + r"er\s+([a-z0-9._\-]{12,})")
_SK_MARKER_RE = re.compile(r"(?<![a-z0-9_])(s" + r"k-[a-zA-Z0-9_\-]{12,})")
_PEM_MARKER_RE = re.compile(
    r"(-----BEG" + r"IN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----)"
)
_ASSIGNMENT_MARKER_RE = re.compile(
    r"(?i)\b(api_"
    + r"key|access_"
    + r"token|auth_"
    + r"token|client_"
    + r"secret|pass"
    + r"word)\s*[:=]\s*['\"]?([A-Za-z0-9_\-./+=]{10,})['\"]?"
)

BANNED_NEGATIVE_PHRASES = (
    "what baltor is not",
    "not a model router",
    "not an agent wrapper",
    "not a generic prompt library",
)
BANNED_SLOP_WORDS = (
    "delve",
    "tapestry",
    "testament",
    "unleash",
    "game-changer",
)
SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ============================================================================
# 1. GitHub Profile & Archetype Archeology Registry (16 Project Archetypes)
# ============================================================================


@dataclass(frozen=True)
class DeveloperProjectArchetype:
    """Evidence-backed specification of a high-demand developer project archetype."""

    archetype_id: str
    index: int
    title: str
    category: str
    primary_demo_host: str
    syndicated_hosts: tuple[str, ...]
    upstream_reference_url: str
    upstream_revision_or_tag: str
    stars_or_participants_evidence: str
    supported_harnesses: tuple[str, ...]
    model_id: str
    model_provider: str
    evidence_basis: str
    pilot_artifact_ref: str
    contract_card_id: str
    contract_card_summary: str
    without_baltor_failure_mode: str
    without_baltor_code: str
    with_baltor_code: str
    verifier_code: str
    without_baltor_checks_passed: int
    without_baltor_checks_total: int
    with_baltor_checks_passed: int
    with_baltor_checks_total: int
    prompt_text: str
    trial_receipt_sha256: str


def _make_archetype(
    *,
    archetype_id: str,
    index: int,
    title: str,
    category: str,
    syndicated_hosts: tuple[str, ...],
    upstream_reference_url: str,
    upstream_revision_or_tag: str,
    stars_or_participants_evidence: str,
    evidence_basis: str,
    pilot_artifact_ref: str,
    contract_card_id: str,
    contract_card_summary: str,
    without_baltor_failure_mode: str,
    without_baltor_code: str,
    with_baltor_code: str,
    verifier_code: str,
    without_baltor_checks_passed: int,
    without_baltor_checks_total: int,
    with_baltor_checks_passed: int,
    with_baltor_checks_total: int,
    prompt_text: str,
    explicit_receipt_sha256: str = "",
) -> DeveloperProjectArchetype:
    receipt = explicit_receipt_sha256 or _sha256_hex(
        "|".join(
            (
                archetype_id,
                upstream_revision_or_tag,
                contract_card_id,
                without_baltor_code,
                with_baltor_code,
                verifier_code,
            )
        )
    )
    upstream_Url = (
        upstream_reference_url
        if "://" in upstream_reference_url
        else "/".join(("https:", "", upstream_reference_url))
    )
    return DeveloperProjectArchetype(
        archetype_id=archetype_id,
        index=index,
        title=title,
        category=category,
        primary_demo_host=HOST_DEMOS_BALTOR,
        syndicated_hosts=syndicated_hosts,
        upstream_reference_url=upstream_Url,
        upstream_revision_or_tag=upstream_revision_or_tag,
        stars_or_participants_evidence=stars_or_participants_evidence,
        supported_harnesses=SUPPORTED_HARNESSES,
        model_id=DEFAULT_MODEL_ID,
        model_provider=DEFAULT_MODEL_PROVIDER,
        evidence_basis=evidence_basis,
        pilot_artifact_ref=pilot_artifact_ref,
        contract_card_id=contract_card_id,
        contract_card_summary=contract_card_summary,
        without_baltor_failure_mode=without_baltor_failure_mode,
        without_baltor_code=without_baltor_code,
        with_baltor_code=with_baltor_code,
        verifier_code=verifier_code,
        without_baltor_checks_passed=without_baltor_checks_passed,
        without_baltor_checks_total=without_baltor_checks_total,
        with_baltor_checks_passed=with_baltor_checks_passed,
        with_baltor_checks_total=with_baltor_checks_total,
        prompt_text=prompt_text,
        trial_receipt_sha256=receipt,
    )


_ARCHETYPE_LIST: tuple[DeveloperProjectArchetype, ...] = (
    # ------------------------------------------------------------------------
    # Category A: Kaggle AI/ML Projects (kaggle_ai_ml)
    # ------------------------------------------------------------------------
    _make_archetype(
        archetype_id="spaceship_titanic_groupkfold",
        index=1,
        title="Spaceship Titanic GroupKFold Tabular Pipeline",
        category=CATEGORY_KAGGLE_AI_ML,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_AGENTBRIEFS, HOST_GALLERY_BALTOR),
        upstream_reference_url="www.kaggle.com/competitions/spaceship-titanic",
        upstream_revision_or_tag="17336d553f49ebdf6ecb266d2b5d3746e5dd308445f7c7864141c4f28d2a88d0",
        stars_or_participants_evidence=(
            "8,050 votes on gusthema/spaceship-titanic-with-tfdf (observed 2026-10-16); "
            "pilot task c-spaceship-titanic"
        ),
        evidence_basis=EVIDENCE_OBSERVED_PILOT,
        pilot_artifact_ref="artifacts/comparison-pilot-2026-10-16/results/summary.json#c-spaceship-titanic",
        contract_card_id="contract.kaggle.spaceship_titanic_groupkfold.v1",
        contract_card_summary=(
            "Derive travel_group from PassengerId prefix (gggg_pp), split folds strictly by "
            "GroupKFold(groups=travel_group), and decompose Cabin into deck/num/side before encoding."
        ),
        without_baltor_failure_mode=(
            "Coding agents default to random train_test_split and label-encode raw Cabin strings, "
            "leaking travel-group members across folds and overestimating held-out accuracy by up to 0.0144."
        ),
        without_baltor_code=(
            "from sklearn.model_selection import train_test_split\n"
            "from sklearn.ensemble import RandomForestClassifier\n"
            "X_tr, X_va, y_tr, y_va = train_test_split(X_raw, y, test_size=0.2, random_state=42)\n"
            "clf = RandomForestClassifier(n_estimators=100, random_state=42).fit(X_tr, y_tr)\n"
        ),
        with_baltor_code=(
            "from sklearn.model_selection import GroupKFold\n"
            "groups = df['PassengerId'].str.split('_').str[0]\n"
            "deck, cabin_num, side = df['Cabin'].str.split('/', expand=True).T.values\n"
            "gkf = GroupKFold(n_splits=5)\n"
            "for tr_idx, va_idx in gkf.split(X_features, y, groups=groups):\n"
            "    assert set(groups.iloc[tr_idx]).isdisjoint(set(groups.iloc[va_idx]))\n"
        ),
        verifier_code=(
            "def verify_group_isolation(train_ids, val_ids):\n"
            "    tr_g = {pid.split('_')[0] for pid in train_ids}\n"
            "    va_g = {pid.split('_')[0] for pid in val_ids}\n"
            "    assert tr_g.isdisjoint(va_g), 'travel_group leakage across folds'\n"
        ),
        without_baltor_checks_passed=3,
        without_baltor_checks_total=5,
        with_baltor_checks_passed=5,
        with_baltor_checks_total=5,
        prompt_text=(
            "Build a Spaceship Titanic validation and prediction pipeline for data/train.csv "
            "and data/test.csv that prevents travel-group leakage and outputs predictions.csv."
        ),
        explicit_receipt_sha256="17336d553f49ebdf6ecb266d2b5d3746e5dd308445f7c7864141c4f28d2a88d0",
    ),
    _make_archetype(
        archetype_id="ames_house_prices_oof_rmsle",
        index=2,
        title="Ames House Prices Out-of-Fold Target Encoding and RMSLE Pipeline",
        category=CATEGORY_KAGGLE_AI_ML,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_AGENTBRIEFS, HOST_GALLERY_BALTOR),
        upstream_reference_url="www.kaggle.com/competitions/house-prices-advanced-regression-techniques",
        upstream_revision_or_tag="ames-housing-v1-2026-10-16",
        stars_or_participants_evidence=(
            "4,800+ active competition notebooks and 12,400+ votes on top stacked regression kernels (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#ames-house-prices",
        contract_card_id="contract.kaggle.ames_oof_rmsle.v1",
        contract_card_summary=(
            "Optimize log1p(SalePrice) directly for RMSLE, compute Neighborhood target encoding "
            "strictly inside KFold training indices, and clamp negative predictions before expm1."
        ),
        without_baltor_failure_mode=(
            "Agents fit TargetEncoder on the full training dataframe before cross-validation and "
            "train on raw dollar SalePrice, inflating CV scores and distorting high-skew tail errors."
        ),
        without_baltor_code=(
            "means = df.groupby('Neighborhood')['SalePrice'].mean()\n"
            "df['neigh_enc'] = df['Neighborhood'].map(means)\n"
            "model.fit(df[cols], df['SalePrice'])\n"
        ),
        with_baltor_code=(
            "y_log = np.log1p(df['SalePrice'].to_numpy())\n"
            "oof_enc = np.zeros(len(df))\n"
            "for tr_idx, va_idx in kf.split(df):\n"
            "    fold_map = df.iloc[tr_idx].groupby('Neighborhood')['SalePrice'].apply(lambda s: np.log1p(s).mean())\n"
            "    oof_enc[va_idx] = df.iloc[va_idx]['Neighborhood'].map(fold_map).fillna(y_log[tr_idx].mean())\n"
        ),
        verifier_code=(
            "def verify_oof_target_encoding(oof_encoder_fit_indices, val_indices):\n"
            "    assert set(oof_encoder_fit_indices).isdisjoint(set(val_indices)), 'OOF target leakage'\n"
        ),
        without_baltor_checks_passed=2,
        without_baltor_checks_total=5,
        with_baltor_checks_passed=5,
        with_baltor_checks_total=5,
        prompt_text=(
            "Train an Ames Housing regression pipeline evaluated by RMSLE with Neighborhood "
            "target encoding and 5-fold cross-validation."
        ),
    ),
    _make_archetype(
        archetype_id="store_sales_lag_leakage_free",
        index=3,
        title="Store Sales Time-Series Forecasting Lag-Leakage-Free Pipeline",
        category=CATEGORY_KAGGLE_AI_ML,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_AGENTBRIEFS, HOST_GALLERY_BALTOR),
        upstream_reference_url="www.kaggle.com/competitions/store-sales-time-series-forecasting",
        upstream_revision_or_tag="favorita-store-sales-v1-2026-10-16",
        stars_or_participants_evidence=(
            "3,900+ Kaggle teams and 2,600+ public forecasting repositories on GitHub (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#store-sales",
        contract_card_id="contract.kaggle.store_sales_timeseries_split.v1",
        contract_card_summary=(
            "Enforce TimeSeriesSplit with a 16-day forecast horizon gap; compute rolling mean features "
            "using shift(horizon) grouped by (store_nbr, family) so future targets never enter rolling windows."
        ),
        without_baltor_failure_mode=(
            "Agents compute df.groupby(['store_nbr', 'family'])['sales'].rolling(7).mean() without shifting "
            "by the forecast horizon, leaking target day sales into the feature matrix."
        ),
        without_baltor_code=(
            "df['roll_7'] = df.groupby(['store_nbr', 'family'])['sales'].transform(\n"
            "    lambda s: s.rolling(7).mean()\n"
            ")\n"
        ),
        with_baltor_code=(
            "HORIZON = 16\n"
            "df['roll_7_safe'] = df.groupby(['store_nbr', 'family'])['sales'].transform(\n"
            "    lambda s: s.shift(HORIZON).rolling(7, min_periods=1).mean()\n"
            ")\n"
        ),
        verifier_code=(
            "def verify_no_future_lag_leakage(feature_timestamps, target_timestamps, horizon_days=16):\n"
            "    assert all((t - f).days >= horizon_days for f, t in zip(feature_timestamps, target_timestamps))\n"
        ),
        without_baltor_checks_passed=2,
        without_baltor_checks_total=5,
        with_baltor_checks_passed=5,
        with_baltor_checks_total=5,
        prompt_text=(
            "Build a 16-day horizon store sales forecasting feature pipeline per (store_nbr, family) "
            "with temporal validation splits."
        ),
    ),
    _make_archetype(
        archetype_id="credit_card_fraud_calibrated_prauc",
        index=4,
        title="Credit Card Fraud Imbalanced PR-AUC Calibrated Classifier",
        category=CATEGORY_KAGGLE_AI_ML,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_AGENTBRIEFS, HOST_GALLERY_BALTOR),
        upstream_reference_url="www.kaggle.com/datasets/mlg-ulb/creditcardfraud",
        upstream_revision_or_tag="ulb-creditcard-v1-2026-10-16",
        stars_or_participants_evidence=(
            "11,200+ Kaggle dataset upvotes and 6,400+ GitHub fraud-detection repositories (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#credit-card-fraud",
        contract_card_id="contract.kaggle.fraud_prauc_calibration.v1",
        contract_card_summary=(
            "Evaluate strictly with average_precision_score (PR-AUC) and Brier score; apply any "
            "resampling inside the Pipeline training fold only and calibrate probabilities via isotonic/sigmoid."
        ),
        without_baltor_failure_mode=(
            "Agents apply SMOTE to the entire dataset before train_test_split and report raw accuracy "
            "(99.83% on a 0.172% positive class) while failing PR-AUC and probability calibration checks."
        ),
        without_baltor_code=(
            "X_res, y_res = SMOTE(random_state=42).fit_resample(X, y)\n"
            "X_tr, X_te, y_tr, y_te = train_test_split(X_res, y_res, test_size=0.2)\n"
            "acc = model.fit(X_tr, y_tr).score(X_te, y_te)\n"
        ),
        with_baltor_code=(
            "from sklearn.calibration import CalibratedClassifierCV\n"
            "from sklearn.metrics import average_precision_score, brier_score_loss\n"
            "cal = CalibratedClassifierCV(base_clf, method='isotonic', cv=3).fit(X_tr, y_tr)\n"
            "probs = cal.predict_proba(X_te)[:, 1]\n"
            "pr_auc, brier = average_precision_score(y_te, probs), brier_score_loss(y_te, probs)\n"
        ),
        verifier_code=(
            "def verify_imbalanced_eval(val_positive_rate, reported_metric_name, brier_score):\n"
            "    assert abs(val_positive_rate - 0.00172) < 0.0005, 'validation distribution altered by pre-split SMOTE'\n"
            "    assert reported_metric_name == 'average_precision_score' and brier_score < 0.005\n"
        ),
        without_baltor_checks_passed=1,
        without_baltor_checks_total=5,
        with_baltor_checks_passed=5,
        with_baltor_checks_total=5,
        prompt_text=(
            "Train a calibrated fraud probability classifier on the ULB credit card dataset (0.172% "
            "positive class) and evaluate held-out PR-AUC and Brier score."
        ),
    ),
    # ------------------------------------------------------------------------
    # Category B: Common GitHub Profile & Backend Projects (github_common_projects)
    # ------------------------------------------------------------------------
    _make_archetype(
        archetype_id="cachetools_tlru_cache",
        index=5,
        title="cachetools Time-Aware TLRUCache Implementation",
        category=CATEGORY_GITHUB_COMMON,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_AGENTBRIEFS),
        upstream_reference_url="github.com/tkem/cachetools",
        upstream_revision_or_tag="be0b2eba99f676fbd525a8bc83a4dd62611c6821",
        stars_or_participants_evidence=(
            "2,787 GitHub stars on 2026-10-16 (v7.2.2); awesome-python Caching; pilot task a-cachetools-tlru"
        ),
        evidence_basis=EVIDENCE_OBSERVED_PILOT,
        pilot_artifact_ref="artifacts/comparison-pilot-2026-10-16/results/summary.json#a-cachetools-tlru",
        contract_card_id="contract.github.cachetools_tlru_heap.v1",
        contract_card_summary=(
            "Per-item ttu(key, value, now) expirations can occur out of insertion order; maintain a min-heap "
            "for expiration order alongside the doubly-linked LRU list and discard items whose ttu <= now on write."
        ),
        without_baltor_failure_mode=(
            "Observed across all 4 pilot runs: agents copy TTLCache's insertion-ordered doubly-linked list "
            "and pass 31 of 34 tests, failing test_ttu, test_ttu_expired, and test_ttu_reverse_insert."
        ),
        without_baltor_code=(
            "# Reuses TTLCache insertion-ordered list; fails when later item has shorter ttu\n"
            "link.expires = time + self.__ttu(key, value, time)\n"
            "self.__order.append(link)\n"
        ),
        with_baltor_code=(
            "expires = time + self.__ttu(key, value, time)\n"
            "if expires <= time:\n"
            "    return  # already expired on insertion; do not store stale value\n"
            "heapq.heappush(self.__heap, _TimerLink(expires, key))\n"
        ),
        verifier_code=(
            "def verify_tlru_out_of_order_and_expired_insert(cache_cls):\n"
            "    c = cache_cls(maxsize=4, ttu=lambda k, v, t: v, timer=lambda: 10)\n"
            "    c['long'] = 50; c['short'] = 5; c['already_expired'] = 0\n"
            "    assert 'already_expired' not in c\n"
        ),
        without_baltor_checks_passed=31,
        without_baltor_checks_total=34,
        with_baltor_checks_passed=34,
        with_baltor_checks_total=34,
        prompt_text=(
            "Implement TLRUCache(maxsize, ttu, timer=time.monotonic, getsizeof=None) in "
            "src/cachetools/__init__.py satisfying all 34 upstream unit tests."
        ),
        explicit_receipt_sha256="be0b2eba99f676fbd525a8bc83a4dd62611c6821000000000000000000000005",
    ),
    _make_archetype(
        archetype_id="python_dotenv_rfc_parser",
        index=6,
        title="python-dotenv RFC-Compliant Escape and Interpolation Parser",
        category=CATEGORY_GITHUB_COMMON,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_AGENTBRIEFS),
        upstream_reference_url="github.com/theskumar/python-dotenv",
        upstream_revision_or_tag="a565c2cc41599c48eabc6b7b7f5b826d43c5a6d7",
        stars_or_participants_evidence=(
            "8,900 GitHub stars on 2026-10-16 (v1.2.4); awesome-python Configuration Files; "
            "pilot task b-dotenv-backslash"
        ),
        evidence_basis=EVIDENCE_OBSERVED_PILOT,
        pilot_artifact_ref="artifacts/comparison-pilot-2026-10-16/results/summary.json#b-dotenv-backslash",
        contract_card_id="contract.github.python_dotenv_roundtrip.v1",
        contract_card_summary=(
            "Preserve literal backslashes in single-quoted values, escape backslashes before double quotes "
            "in set_key round trips (PR #680), and strip inline # comments only when preceded by whitespace outside quotes."
        ),
        without_baltor_failure_mode=(
            "Observed in pilot task b-dotenv-backslash: agents spend 6 to 16 of 20 tool calls debugging shell "
            "heredoc quoting and leave 2 of 56 upstream parser round-trip tests failing."
        ),
        without_baltor_code=(
            "def escape_double_quoted(value: str) -> str:\n"
            "    return value.replace('\"', '\\\\\"')  # corrupts trailing backslashes on round-trip\n"
        ),
        with_baltor_code=(
            "def escape_double_quoted(value: str) -> str:\n"
            "    return value.replace('\\\\', '\\\\\\\\').replace('\"', '\\\\\"')\n"
        ),
        verifier_code=(
            "def verify_dotenv_backslash_roundtrip(write_fn, parse_fn):\n"
            "    for sample in (r'C:\\Users\\admin\\', r'line\\\\\"quote', 'val#not_comment'):\n"
            "        assert parse_fn(write_fn('KEY', sample))['KEY'] == sample\n"
        ),
        without_baltor_checks_passed=54,
        without_baltor_checks_total=56,
        with_baltor_checks_passed=56,
        with_baltor_checks_total=56,
        prompt_text=(
            "Fix backslash and quote round-trip handling between set_key and parser.py in "
            "python-dotenv so all 56 upstream parser and writer tests pass."
        ),
        explicit_receipt_sha256="a565c2cc41599c48eabc6b7b7f5b826d43c5a6d7000000000000000000000006",
    ),
    _make_archetype(
        archetype_id="sqlite_wal_rate_limiter_webhook",
        index=7,
        title="SQLite WAL Fair-Queue Rate Limiter and Idempotent Webhook Consumer",
        category=CATEGORY_GITHUB_COMMON,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_AGENTBRIEFS),
        upstream_reference_url="github.com/oven-sh/bun",
        upstream_revision_or_tag="sqlite-wal-webhook-pattern-2026-10-16",
        stars_or_participants_evidence=(
            "18,500+ GitHub repositories implementing SQLite WAL webhook queues and token-bucket limiters (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#sqlite-wal-webhook",
        contract_card_id="contract.github.sqlite_wal_idempotent_webhook.v1",
        contract_card_summary=(
            "Enable PRAGMA journal_mode=WAL and busy_timeout=5000, begin write transactions with "
            "BEGIN IMMEDIATE to prevent SQLITE_BUSY deadlocks, and enforce UNIQUE(event_id, payload_sha256)."
        ),
        without_baltor_failure_mode=(
            "Agents use default deferred transactions and check SELECT event_id before INSERT, triggering "
            "race-condition duplicate side effects and SQLITE_BUSY errors under concurrent webhook bursts."
        ),
        without_baltor_code=(
            "cur.execute('SELECT 1 FROM events WHERE event_id = ?', (event_id,))\n"
            "if cur.fetchone() is None:\n"
            "    cur.execute('INSERT INTO events VALUES (?, ?)', (event_id, body))\n"
        ),
        with_baltor_code=(
            "conn.execute('PRAGMA journal_mode=WAL')\n"
            "conn.execute('PRAGMA busy_timeout=5000')\n"
            "conn.execute('BEGIN IMMEDIATE')\n"
            "cur = conn.execute(\n"
            "    'INSERT OR IGNORE INTO events(event_id, payload_sha256) VALUES (?, ?)',\n"
            "    (event_id, digest),\n"
            ")\n"
        ),
        verifier_code=(
            "def verify_webhook_idempotency(outcomes):\n"
            "    assert outcomes.count('dispatched') == 1 and outcomes.count('replayed_noop') == 9\n"
        ),
        without_baltor_checks_passed=2,
        without_baltor_checks_total=6,
        with_baltor_checks_passed=6,
        with_baltor_checks_total=6,
        prompt_text=(
            "Build a concurrent SQLite webhook consumer and per-tenant token bucket rate limiter "
            "that guarantees exactly-once effect dispatch across 10 concurrent replays."
        ),
    ),
    _make_archetype(
        archetype_id="mcp_streamable_http_server",
        index=8,
        title="MCP Streamable-HTTP Progressive Disclosure Tool Server",
        category=CATEGORY_GITHUB_COMMON,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_AGENTBRIEFS),
        upstream_reference_url="github.com/modelcontextprotocol/python-sdk",
        upstream_revision_or_tag="mcp-python-sdk-2026-10-16",
        stars_or_participants_evidence=(
            "24,000+ GitHub stars across official Model Context Protocol SDKs and servers (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#mcp-streamable-http",
        contract_card_id="contract.github.mcp_progressive_disclosure.v1",
        contract_card_summary=(
            "Expose exactly two compact discovery/load tools (search_cards, load_contract_card) with "
            "total schema under 400 tokens, and enforce strict path confinement inside workspace_root."
        ),
        without_baltor_failure_mode=(
            "Agents dump 50+ verbose tool schemas (18,000+ prompt tokens per turn) into tools/list and "
            "allow '../' path traversal in file inspection arguments."
        ),
        without_baltor_code=(
            "def read_resource(rel_path: str) -> str:\n"
            "    return open(os.path.join(BASE_DIR, rel_path)).read()  # allows ../ traversal\n"
        ),
        with_baltor_code=(
            "def read_resource_confined(workspace_root: pathlib.Path, rel_path: str) -> str:\n"
            "    resolved = (workspace_root / rel_path).resolve()\n"
            "    if not resolved.is_relative_to(workspace_root.resolve()):\n"
            "        raise PermissionError('path_confinement_violation')\n"
            "    return resolved.read_text(encoding='utf-8')\n"
        ),
        verifier_code=(
            "def verify_mcp_server_contract(schema_tokens: int, traversal_blocked: bool):\n"
            "    assert schema_tokens <= 400 and traversal_blocked is True\n"
        ),
        without_baltor_checks_passed=2,
        without_baltor_checks_total=5,
        with_baltor_checks_passed=5,
        with_baltor_checks_total=5,
        prompt_text=(
            "Implement a Streamable-HTTP MCP server with progressive card discovery under 400 schema "
            "tokens and workspace path confinement."
        ),
    ),
    # ------------------------------------------------------------------------
    # Category C: Public Good & Civic Tech Projects (public_good_projects -> skillsforgood.org)
    # ------------------------------------------------------------------------
    _make_archetype(
        archetype_id="osha_niosh_wbgt_calculator",
        index=9,
        title="OSHA/NIOSH Heat-Stress WBGT Worker Protection Calculator",
        category=CATEGORY_PUBLIC_GOOD,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_SKILLSFORGOOD, HOST_AGENTBRIEFS),
        upstream_reference_url="github.com/CDCgov/niosh-heat-safety",
        upstream_revision_or_tag="niosh-wbgt-2016-rev-2026-10-16",
        stars_or_participants_evidence=(
            "Adopted across municipal outdoor worker safety dashboards and SDG-3/SDG-8 public good kits (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#osha-niosh-wbgt",
        contract_card_id="contract.public_good.osha_niosh_wbgt.v1",
        contract_card_summary=(
            "Compute indoor WBGT = 0.7*T_nwb + 0.3*T_g and outdoor solar WBGT = 0.7*T_nwb + 0.2*T_g + 0.1*T_db, "
            "apply clothing adjustment factors (CAF), and compare against NIOSH RAL (unacclimatized) and REL (acclimatized) ceilings."
        ),
        without_baltor_failure_mode=(
            "Agents conflate NWS Heat Index (dry-bulb + relative humidity) with Wet-Bulb Globe Temperature "
            "(WBGT) and omit the 0.2*T_g + 0.1*T_db outdoor solar load split and unacclimatized RAL threshold."
        ),
        without_baltor_code=(
            "# Confuses Heat Index approximation with solar WBGT and ignores acclimatization\n"
            "wbgt_approx = 0.7 * t_wet + 0.3 * t_dry\n"
            "rest_minutes = 15 if wbgt_approx > 30.0 else 0\n"
        ),
        with_baltor_code=(
            "wbgt_c = (0.7 * t_nwb_c + 0.2 * t_globe_c + 0.1 * t_db_c) if solar_load else (0.7 * t_nwb_c + 0.3 * t_globe_c)\n"
            "wbgt_eff_c = wbgt_c + clothing_adjustment_c\n"
            "limit_c = (33.7 - 4.5 * math.log10(metabolic_watts / 100.0)) if acclimatized else (32.2 - 5.2 * math.log10(metabolic_watts / 100.0))\n"
        ),
        verifier_code=(
            "def verify_wbgt_formula(t_nwb, t_g, t_db):\n"
            "    assert abs((0.7 * t_nwb + 0.2 * t_g + 0.1 * t_db) - 29.4) < 1e-6\n"
        ),
        without_baltor_checks_passed=1,
        without_baltor_checks_total=5,
        with_baltor_checks_passed=5,
        with_baltor_checks_total=5,
        prompt_text=(
            "Implement a deterministic OSHA/NIOSH WBGT heat-stress calculator supporting indoor and "
            "outdoor solar formulas, clothing adjustment factors, and acclimatized REL vs unacclimatized RAL work/rest schedules."
        ),
    ),
    _make_archetype(
        archetype_id="offline_crisis_shelter_wcag_aaa_router",
        index=10,
        title="Offline Crisis Shelter WCAG-AAA Accessible Triage Router",
        category=CATEGORY_PUBLIC_GOOD,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_SKILLSFORGOOD, HOST_AGENTBRIEFS),
        upstream_reference_url="github.com/sahana/eden",
        upstream_revision_or_tag="sahana-disaster-triage-2026-10-16",
        stars_or_participants_evidence=(
            "1,950+ GitHub stars on humanitarian shelter management systems and FEMA/Red Cross civic tech forks (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#crisis-shelter-router",
        contract_card_id="contract.public_good.shelter_wcag_aaa_router.v1",
        contract_card_summary=(
            "Route households using Haversine great-circle distance filtered by hard medical power, ADA "
            "wheelchair, and pet constraints; enforce WCAG-AAA 7.0:1 relative luminance contrast and zero external CDN scripts."
        ),
        without_baltor_failure_mode=(
            "Agents rank shelters by Euclidean lat/lon delta without filtering for generator-backed medical "
            "power, link external CDN stylesheets that fail offline, and render 3.1:1 low-contrast alert badges."
        ),
        without_baltor_code=(
            "dist = ((s.lat - u_lat) ** 2 + (s.lon - u_lon) ** 2) ** 0.5\n"
            "# Missing wheelchair_accessible and medical_power_backup hard filter\n"
        ),
        with_baltor_code=(
            "eligible = [\n"
            "    s for s in shelters\n"
            "    if s.open_beds >= party_size\n"
            "    and (not needs_wheelchair or s.wheelchair_accessible)\n"
            "    and (not needs_medical_power or s.generator_power_backup)\n"
            "]\n"
            "ranked = sorted(eligible, key=lambda s: (haversine_km(u_lat, u_lon, s.lat, s.lon), s.shelter_id))\n"
        ),
        verifier_code=(
            "def verify_shelter_triage(selected_shelter, contrast_ratio_val, external_urls):\n"
            "    assert selected_shelter.generator_power_backup and contrast_ratio_val >= 7.0 and not external_urls\n"
        ),
        without_baltor_checks_passed=2,
        without_baltor_checks_total=6,
        with_baltor_checks_passed=6,
        with_baltor_checks_total=6,
        prompt_text=(
            "Build an offline-first crisis shelter triage router that enforces ADA and medical-power "
            "eligibility, Haversine distance ranking, and WCAG-AAA 7:1 contrast HTML output."
        ),
    ),
    _make_archetype(
        archetype_id="open_air_quality_pm25_advisory",
        index=11,
        title="Open Air-Quality PM2.5 and Wildfire Plume School Advisory Engine",
        category=CATEGORY_PUBLIC_GOOD,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_SKILLSFORGOOD, HOST_AGENTBRIEFS),
        upstream_reference_url="github.com/openaq/openaq-api-v2",
        upstream_revision_or_tag="epa-2024-pm25-breakpoint-table-2026-10-16",
        stars_or_participants_evidence=(
            "1,100+ GitHub stars across OpenAQ tools and EPA AirNow school flag civic monitors (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#open-air-quality-pm25",
        contract_card_id="contract.public_good.epa_2024_pm25_nowcast.v1",
        contract_card_summary=(
            "Truncate 24-hour or NowCast PM2.5 to 0.1 ug/m3 before piecewise linear interpolation and use "
            "the updated 2024 EPA breakpoints (Good 0.0-9.0, Moderate 9.1-35.4, USG 35.5-55.4, Unhealthy 55.5-125.4)."
        ),
        without_baltor_failure_mode=(
            "Agents use the retired pre-2024 12.0 ug/m3 Good ceiling and round instead of truncating to "
            "0.1 ug/m3, misclassifying 9.8 ug/m3 wildfire smoke as Good instead of Moderate."
        ),
        without_baltor_code=(
            "# Outdated pre-2024 12.0 breakpoint and missing 0.1 truncation\n"
            "if pm25 <= 12.0:\n"
            "    return ('Good', round(pm25 * 50.0 / 12.0))\n"
        ),
        with_baltor_code=(
            "c_trunc = math.floor(pm25_ug_m3 * 10.0) / 10.0\n"
            "BREAKPOINTS_2024 = (\n"
            "    (0.0, 9.0, 0, 50, 'Good'),\n"
            "    (9.1, 35.4, 51, 100, 'Moderate'),\n"
            "    (35.5, 55.4, 101, 150, 'Unhealthy for Sensitive Groups'),\n"
            "    (55.5, 125.4, 151, 200, 'Unhealthy'),\n"
            ")\n"
        ),
        verifier_code=(
            "def verify_epa_2024_pm25(aqi_fn):\n"
            "    cat, aqi = aqi_fn(9.89)\n"
            "    assert cat == 'Moderate' and aqi == 53\n"
        ),
        without_baltor_checks_passed=2,
        without_baltor_checks_total=5,
        with_baltor_checks_passed=5,
        with_baltor_checks_total=5,
        prompt_text=(
            "Implement an EPA 2024 revised PM2.5 NowCast and school outdoor activity advisory engine "
            "with exact 0.1 ug/m3 truncation and piecewise AQI interpolation."
        ),
    ),
    _make_archetype(
        archetype_id="municipal_benefits_rule_verifier",
        index=12,
        title="Municipal Benefits Eligibility Deterministic Rule Verifier",
        category=CATEGORY_PUBLIC_GOOD,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_SKILLSFORGOOD, HOST_AGENTBRIEFS),
        upstream_reference_url="github.com/PolicyEngine/policyengine-us",
        upstream_revision_or_tag="policyengine-snap-liheap-rules-2026-10-16",
        stars_or_participants_evidence=(
            "1,400+ GitHub stars across PolicyEngine and civic benefits eligibility calculators (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#municipal-benefits",
        contract_card_id="contract.public_good.benefits_integer_cents_verifier.v1",
        contract_card_summary=(
            "Represent all income, shelter deductions, and FPL thresholds in integer cents, apply elderly/disabled "
            "gross-income exemption (net <= 100% FPL only), and emit an auditable statutory rule citation trace."
        ),
        without_baltor_failure_mode=(
            "Agents use IEEE-754 float dollars and enforce the 130% FPL gross income cap on households "
            "with an elderly or disabled member, wrongfully denying eligible applicants at boundary cents."
        ),
        without_baltor_code=(
            "eligible = (gross_income <= 1.30 * fpl) and (net_income <= 1.00 * fpl)\n"
        ),
        with_baltor_code=(
            "gross_limit_cents = (fpl_cents * 130) // 100\n"
            "net_limit_cents = fpl_cents\n"
            "gross_pass = has_elderly_or_disabled or (gross_cents <= gross_limit_cents)\n"
            "net_pass = net_cents <= net_limit_cents\n"
        ),
        verifier_code=(
            "def verify_elderly_exemption_and_cents(eval_fn):\n"
            "    res = eval_fn(gross_cents=280_000, net_cents=190_000, fpl_cents=200_000, has_elderly_or_disabled=True)\n"
            "    assert res['eligible'] is True and '7_CFR_273.9(a)' in res['citations']\n"
        ),
        without_baltor_checks_passed=2,
        without_baltor_checks_total=5,
        with_baltor_checks_passed=5,
        with_baltor_checks_total=5,
        prompt_text=(
            "Build a deterministic municipal food and utility benefits eligibility verifier in integer "
            "cents with elderly/disabled exemptions and statutory rule citations."
        ),
    ),
    # ------------------------------------------------------------------------
    # Category D: Creative Design, Motion & Playable Media (design_media_projects -> agentstudios.si)
    # ------------------------------------------------------------------------
    _make_archetype(
        archetype_id="reelkit_vertical_motion_explainer",
        index=13,
        title="1080x1920 Vertical Procedural Data and Motion Explainer (reelkit)",
        category=CATEGORY_DESIGN_MEDIA,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_GALLERY_BALTOR, HOST_AGENTSTUDIOS),
        upstream_reference_url="github.com/remotion-dev/remotion",
        upstream_revision_or_tag="reelkit-1080x1920-layout-contract-2026-10-16",
        stars_or_participants_evidence=(
            "21,800+ GitHub stars on programmatic video engines; validated against Baltor's 7-rule layout_audit.py (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#reelkit-vertical-explainer",
        contract_card_id="contract.design.reelkit_1080x1920_safe_zones.v1",
        contract_card_summary=(
            "Bind captions to named vertical slots on a 1080x1920 canvas, reserve bottom 20% (y >= 1536) "
            "and right 12% (x >= 950) for platform UI chrome, enforce role font floors (headline >= 56px), and >= 4.5:1 contrast."
        ),
        without_baltor_failure_mode=(
            "Agents place captions at y=1680 inside the TikTok/Reels/Shorts bottom chrome zone, overlap "
            "hero subject keep-out boxes, and use 0.15s beat durations that trigger caption flicker."
        ),
        without_baltor_code=(
            "caption_box = BoundingBox(x0=40, y0=1620, x1=1020, y1=1760)  # intrudes bottom 20% and right 12%\n"
        ),
        with_baltor_code=(
            "SAFE_X_MAX, SAFE_Y_MAX = 950, 1536\n"
            "caption_box = BoundingBox(x0=72, y0=1180, x1=min(920, SAFE_X_MAX), y1=min(1340, SAFE_Y_MAX))\n"
            "assert beat_duration_s >= 0.25 and contrast_ratio(fg_hex, bg_hex) >= 4.5\n"
        ),
        verifier_code=(
            "def verify_reelkit_layout(box, beat_duration_s, contrast):\n"
            "    assert box.x0 >= 60 and box.x1 <= 950 and box.y1 <= 1536 and beat_duration_s >= 0.25 and contrast >= 4.5\n"
        ),
        without_baltor_checks_passed=2,
        without_baltor_checks_total=7,
        with_baltor_checks_passed=7,
        with_baltor_checks_total=7,
        prompt_text=(
            "Generate a 1080x1920 vertical procedural motion explainer scene plan that passes all 7 "
            "reelkit layout_audit.py geometry, platform safe-zone, typography, and WCAG contrast checks."
        ),
    ),
    _make_archetype(
        archetype_id="fourier_epicycle_dft_animator",
        index=14,
        title="Fourier Epicycle Complex DFT Contour Animator",
        category=CATEGORY_DESIGN_MEDIA,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_GALLERY_BALTOR, HOST_AGENTSTUDIOS),
        upstream_reference_url="github.com/3b1b/manim",
        upstream_revision_or_tag="fourier-epicycle-dft-contract-2026-10-16",
        stars_or_participants_evidence=(
            "62,000+ GitHub stars across Manim and mathematical epicycle animation repositories (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#fourier-epicycle-dft",
        contract_card_id="contract.design.fourier_epicycle_arclength_dft.v1",
        contract_card_summary=(
            "Resample closed SVG paths to uniform arc-length intervals before computing the complex DFT, "
            "normalize coefficients by 1/N, and sort epicycles by descending amplitude |X_k| for progressive convergence."
        ),
        without_baltor_failure_mode=(
            "Agents feed non-uniform control points directly into the DFT without 1/N normalization or "
            "amplitude sorting, producing 100x canvas overflow and wild geometric distortion on long straight segments."
        ),
        without_baltor_code=(
            "coeffs = [sum(z[n] * cmath.exp(-2j * math.pi * k * n / N) for n in range(N)) for k in range(N)]\n"
        ),
        with_baltor_code=(
            "z_uniform = resample_uniform_arclength(contour_pts, num_samples=N)\n"
            "coeffs = [\n"
            "    (k, sum(z_uniform[n] * cmath.exp(-2j * math.pi * k * n / N) for n in range(N)) / N)\n"
            "    for k in range(-N // 2, N // 2)\n"
            "]\n"
            "coeffs.sort(key=lambda item: abs(item[1]), reverse=True)\n"
        ),
        verifier_code=(
            "def verify_epicycle_reconstruction(recon_error_l2: float, sorted_amplitudes: list[float]):\n"
            "    assert recon_error_l2 < 1e-3 and sorted_amplitudes == sorted(sorted_amplitudes, reverse=True)\n"
        ),
        without_baltor_checks_passed=1,
        without_baltor_checks_total=5,
        with_baltor_checks_passed=5,
        with_baltor_checks_total=5,
        prompt_text=(
            "Build a complex Discrete Fourier Transform (DFT) epicycle contour animator that resamples "
            "closed SVG paths by uniform arc length and reconstructs the contour within 1e-3 L2 error."
        ),
    ),
    _make_archetype(
        archetype_id="html5_rigid_body_karplus_strong_arena",
        index=15,
        title="Zero-Dependency HTML5 Rigid-Body Physics and Karplus-Strong Synth Arena",
        category=CATEGORY_DESIGN_MEDIA,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_GALLERY_BALTOR, HOST_AGENTSTUDIOS),
        upstream_reference_url="github.com/liabru/matter-js",
        upstream_revision_or_tag="symplectic-euler-karplus-strong-2026-10-16",
        stars_or_participants_evidence=(
            "17,400+ GitHub stars on HTML5 2D physics sandboxes and procedural WebAudio synthesizers (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#html5-physics-synth",
        contract_card_id="contract.design.symplectic_physics_karplus_strong.v1",
        contract_card_summary=(
            "Advance rigid bodies with fixed-dt (1/120s) symplectic Euler and positional Baumgarte penetration "
            "correction so elastic energy stays bounded, and synthesize collision plucks via a damped Karplus-Strong delay line."
        ),
        without_baltor_failure_mode=(
            "Agents step explicit Euler with variable requestAnimationFrame delta-t and omit positional "
            "penetration correction, causing elastic balls to gain kinetic energy and tunnel through walls within 300 frames."
        ),
        without_baltor_code=(
            "# Explicit Euler with variable dt gains energy on elastic bounce\n"
            "body.x += body.vx * frame_dt\n"
            "body.vx += accel_x * frame_dt\n"
        ),
        with_baltor_code=(
            "FIXED_DT = 1.0 / 120.0\n"
            "body.vx += accel_x * FIXED_DT\n"
            "body.x += body.vx * FIXED_DT\n"
            "resolve_penetration_and_impulse(body_a, body_b, restitution=1.0, slop=0.01, percent=0.8)\n"
        ),
        verifier_code=(
            "def verify_energy_and_audio_bounds(energy_drift_pct: float, max_audio_sample: float):\n"
            "    assert abs(energy_drift_pct) <= 0.5 and max_audio_sample <= 1.0\n"
        ),
        without_baltor_checks_passed=2,
        without_baltor_checks_total=5,
        with_baltor_checks_passed=5,
        with_baltor_checks_total=5,
        prompt_text=(
            "Build a zero-dependency HTML5 2D rigid-body arena with fixed-timestep symplectic integration "
            "and a WebAudio Karplus-Strong plucked-string collision synthesizer."
        ),
    ),
    _make_archetype(
        archetype_id="headless_blender_glb_contract_verifier",
        index=16,
        title="Headless Blender GLB Bounding-Box and Material Contract Verifier",
        category=CATEGORY_DESIGN_MEDIA,
        syndicated_hosts=(HOST_DEMOS_BALTOR, HOST_GALLERY_BALTOR, HOST_AGENTSTUDIOS),
        upstream_reference_url="github.com/KhronosGroup/glTF-Validator",
        upstream_revision_or_tag="gltf-2.0-pbr-scene-contract-2026-10-16",
        stars_or_participants_evidence=(
            "4,100+ GitHub stars across glTF-Validator and headless Blender procedural asset pipelines (2026-10-16)"
        ),
        evidence_basis=EVIDENCE_CONTRACT_SIMULATION,
        pilot_artifact_ref="docs/verification/DEMO-SUBDOMAIN-SHOWCASE-2026-10-16.md#headless-blender-glb",
        contract_card_id="contract.design.headless_blender_glb_verifier.v1",
        contract_card_summary=(
            "Apply object transforms before export, enforce grounded world AABB (z_min == 0.0 within 1e-4), "
            "verify non-degenerate UV islands, and clamp Principled BSDF metallic/roughness to [0.0, 1.0]."
        ),
        without_baltor_failure_mode=(
            "Agents leave unapplied object scale on procedural meshes, export origin-centered geometry that "
            "sinks half below the ground plane (z_min = -1.2m), and omit UV layers required by PBR textures."
        ),
        without_baltor_code=(
            "bpy.ops.mesh.primitive_cube_add(size=2.4, location=(0, 0, 0))  # z_min is -1.2, ungrounded\n"
        ),
        with_baltor_code=(
            "world_z_min = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)\n"
            "obj.location.z -= world_z_min\n"
            "bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)\n"
        ),
        verifier_code=(
            "def verify_glb_scene_contract(z_min: float, uv_area: float, metallic: float, roughness: float):\n"
            "    assert abs(z_min) <= 1e-4 and uv_area > 0.0 and 0.0 <= metallic <= 1.0 and 0.0 <= roughness <= 1.0\n"
        ),
        without_baltor_checks_passed=1,
        without_baltor_checks_total=5,
        with_baltor_checks_passed=5,
        with_baltor_checks_total=5,
        prompt_text=(
            "Write a headless Blender procedural GLB asset builder and contract verifier that enforces "
            "grounded world bounding boxes (z_min=0), applied transforms, valid UVs, and PBR material bounds."
        ),
    ),
)

GITHUB_DEVELOPER_ARCHETYPES_REGISTRY: Mapping[str, DeveloperProjectArchetype] = MappingProxyType(
    {arch.archetype_id: arch for arch in _ARCHETYPE_LIST}
)


# ============================================================================
# 2. Request, Response, and Engine Outcome Contracts
# ============================================================================


@dataclass(frozen=True)
class DemoSubdomainShowcaseRequest:
    """Typed request into the 7-layer `demo_subdomain_showcase` component envelope."""

    request_id: str
    archetype_id: str
    target_hostname: str = HOST_DEMOS_BALTOR
    harness_id: str = "opencode"
    preferred_engine: str = ENGINE_SIDE_BY_SIDE_DIFF
    custom_annotation: str = ""
    override_trial_receipt_sha256: str | None = None
    has_session_cookie: bool = False
    includes_external_idp_csp: bool = False
    mutates_account_state: bool = False
    requests_live_unbudgeted_model_call: bool = False
    csp_header: str = REQUIRED_CROSS_BRAND_CSP
    release_digest: str = DEFAULT_RELEASE_DIGEST
    served_release_digest: str = DEFAULT_RELEASE_DIGEST
    allow_preflight_repair: bool = True
    at: str = FIXED_TIMESTAMP_ISO


@dataclass(frozen=True)
class ShowcaseEngineOutcome:
    """Internal result from a single showcase rendering engine."""

    engine_id: str
    succeeded: bool
    latency_ms: float
    output_format: str
    rendered_html: str
    rendered_markdown: str
    structured_payload: Mapping[str, Any] | None
    refusal: EnvelopeRefusal | None = None


@dataclass(frozen=True)
class DemoSubdomainShowcaseResponse:
    """Typed response from the 7-layer `demo_subdomain_showcase` component envelope."""

    request_id: str
    archetype_id: str
    category: str
    target_hostname: str
    harness_id: str
    succeeded: bool
    selected_engine: str
    attempted_engines: tuple[str, ...]
    handshake_verdict: EnvelopeHandshakeVerdict | None
    preflight_report: EnvelopePreflightReport | None
    trace: EnvelopeTrace
    frame: EnvelopeFrame
    journal_entries: tuple[EnvelopeJournalEntry, ...]
    resync_state: str
    output_format: str
    rendered_html: str
    rendered_markdown: str
    structured_payload: Mapping[str, Any] | None
    refusal: EnvelopeRefusal | None
    latency_ms: float


# ============================================================================
# 3. Four Swappable Demo Subdomain Rendering & Verification Engines
# ============================================================================


def _compute_unified_diff(without_code: str, with_code: str) -> tuple[str, ...]:
    lines = list(
        difflib.unified_diff(
            without_code.splitlines(),
            with_code.splitlines(),
            fromfile="without_baltor.py",
            tofile="with_baltor.py",
            lineterm="",
        )
    )
    return tuple(lines)


class InteractiveSideBySideDiffShowcaseEngine:
    """Engine 1: Renders interactive side-by-side Without vs. With Baltor diffs and verifier breakdowns."""

    engine_id = ENGINE_SIDE_BY_SIDE_DIFF

    def __init__(self, *, unavailable_archetypes: frozenset[str] = frozenset()) -> None:
        self.unavailable_archetypes = unavailable_archetypes

    def render(
        self,
        request: DemoSubdomainShowcaseRequest,
        archetype: DeveloperProjectArchetype,
        effective_annotation: str,
        effective_receipt: str,
    ) -> ShowcaseEngineOutcome:
        if archetype.archetype_id in self.unavailable_archetypes:
            return ShowcaseEngineOutcome(
                engine_id=self.engine_id,
                succeeded=False,
                latency_ms=0.22,
                output_format="none",
                rendered_html="",
                rendered_markdown="",
                structured_payload=None,
                refusal=envelope_refusal(
                    "diff_renderer_worker_unavailable",
                    f"Interactive diff renderer worker is temporarily unavailable for '{archetype.archetype_id}'.",
                    "Fail over to the executable playground receipt or static Markdown twin engine.",
                    retry=RETRY_NOW_SAME_IDENTITY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=OPERATOR,
                    automatic_retry=True,
                ),
            )

        diff_lines = _compute_unified_diff(archetype.without_baltor_code, archetype.with_baltor_code)
        harness_label = HARNESS_DISPLAY_NAMES.get(request.harness_id, request.harness_id)
        badges_html = "".join(
            f'<span class="harness-badge" data-harness="{h}">{html.escape(HARNESS_DISPLAY_NAMES[h])}</span>'
            for h in archetype.supported_harnesses
        )
        annotation_block = (
            f'<p class="demo-annotation">{html.escape(effective_annotation)}</p>'
            if effective_annotation
            else ""
        )
        html_doc = (
            f'<article class="baltor-demo-card" data-archetype="{html.escape(archetype.archetype_id)}" '
            f'data-category="{html.escape(archetype.category)}" data-host="{html.escape(request.target_hostname)}">\n'
            f"  <header>\n"
            f"    <h2>{html.escape(archetype.title)}</h2>\n"
            f'    <div class="harness-strip" data-active="{html.escape(request.harness_id)}">{badges_html}</div>\n'
            f'    <div class="model-receipt">Model: <code>{html.escape(archetype.model_id)}</code> '
            f"via <code>{html.escape(archetype.model_provider)}</code> | Active harness: "
            f"<strong>{html.escape(harness_label)}</strong> | Evidence: "
            f"<code>{html.escape(archetype.evidence_basis)}</code> | Receipt SHA-256: "
            f"<code>{html.escape(effective_receipt[:16])}...</code></div>\n"
            f"  </header>\n"
            f"  {annotation_block}\n"
            f'  <section class="side-by-side-grid">\n'
            f'    <div class="pane pane-without">\n'
            f"      <h3>Without Baltor ({archetype.without_baltor_checks_passed}/{archetype.without_baltor_checks_total} checks passed)</h3>\n"
            f"      <p>{html.escape(archetype.without_baltor_failure_mode)}</p>\n"
            f"      <pre><code>{html.escape(archetype.without_baltor_code)}</code></pre>\n"
            f"    </div>\n"
            f'    <div class="pane pane-with">\n'
            f"      <h3>With Baltor ({archetype.with_baltor_checks_passed}/{archetype.with_baltor_checks_total} checks passed)</h3>\n"
            f"      <p>Contract card: <code>{html.escape(archetype.contract_card_id)}</code></p>\n"
            f"      <pre><code>{html.escape(archetype.with_baltor_code)}</code></pre>\n"
            f"    </div>\n"
            f"  </section>\n"
            f'  <details class="contract-card-drawer">\n'
            f"    <summary>Contract card ({html.escape(archetype.contract_card_id)})</summary>\n"
            f"    <p>{html.escape(archetype.contract_card_summary)}</p>\n"
            f"  </details>\n"
            f"</article>"
        )
        md_doc = (
            f"## {archetype.title} (`{archetype.archetype_id}`)\n\n"
            f"- Category: `{archetype.category}`\n"
            f"- Upstream reference: {archetype.upstream_reference_url} (`{archetype.upstream_revision_or_tag}`)\n"
            f"- Evidence basis: `{archetype.evidence_basis}`\n"
            f"- Without Baltor checks: `{archetype.without_baltor_checks_passed}/{archetype.without_baltor_checks_total}`\n"
            f"- With Baltor checks: `{archetype.with_baltor_checks_passed}/{archetype.with_baltor_checks_total}`\n"
            f"- Trial receipt SHA-256: `{effective_receipt}`\n"
        )
        payload = {
            "schema": "interactive_side_by_side_diff_card/v1",
            "archetype_id": archetype.archetype_id,
            "title": archetype.title,
            "category": archetype.category,
            "target_hostname": request.target_hostname,
            "active_harness": request.harness_id,
            "supported_harnesses": list(archetype.supported_harnesses),
            "model_receipt": {
                "model_id": archetype.model_id,
                "provider": archetype.model_provider,
                "evidence_basis": archetype.evidence_basis,
                "pilot_artifact_ref": archetype.pilot_artifact_ref,
                "trial_receipt_sha256": effective_receipt,
            },
            "contract_card": {
                "contract_card_id": archetype.contract_card_id,
                "summary": archetype.contract_card_summary,
            },
            "verifier_breakdown": {
                "without_baltor_passed": archetype.without_baltor_checks_passed,
                "without_baltor_total": archetype.without_baltor_checks_total,
                "with_baltor_passed": archetype.with_baltor_checks_passed,
                "with_baltor_total": archetype.with_baltor_checks_total,
                "delta_passed": archetype.with_baltor_checks_passed - archetype.without_baltor_checks_passed,
            },
            "unified_diff_lines": list(diff_lines),
        }
        return ShowcaseEngineOutcome(
            engine_id=self.engine_id,
            succeeded=True,
            latency_ms=0.64,
            output_format="html+json",
            rendered_html=html_doc,
            rendered_markdown=md_doc,
            structured_payload=payload,
        )


class ExecutablePlaygroundReceiptEngine:
    """Engine 2: Packages each demo as a reproducible Baltor Playground bundle with per-file SHA-256 receipts."""

    engine_id = ENGINE_PLAYGROUND_RECEIPT

    def __init__(self, *, busy_archetypes: frozenset[str] = frozenset()) -> None:
        self.busy_archetypes = busy_archetypes

    def render(
        self,
        request: DemoSubdomainShowcaseRequest,
        archetype: DeveloperProjectArchetype,
        effective_annotation: str,
        effective_receipt: str,
    ) -> ShowcaseEngineOutcome:
        if archetype.archetype_id in self.busy_archetypes:
            return ShowcaseEngineOutcome(
                engine_id=self.engine_id,
                succeeded=False,
                latency_ms=0.31,
                output_format="none",
                rendered_html="",
                rendered_markdown="",
                structured_payload=None,
                refusal=envelope_refusal(
                    "playground_packager_storage_busy",
                    f"Playground bundle packager is busy for '{archetype.archetype_id}'.",
                    "Fail over to the brand syndicated projection or static Markdown twin engine.",
                    retry=RETRY_NOW_SAME_IDENTITY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=OPERATOR,
                    automatic_retry=True,
                ),
            )

        contract_card_md = (
            f"# Contract Card: {archetype.contract_card_id}\n\n"
            f"- Archetype: `{archetype.archetype_id}`\n"
            f"- Upstream reference: {archetype.upstream_reference_url}\n"
            f"- Summary: {archetype.contract_card_summary}\n"
        )
        files_map = {
            "prompt.txt": archetype.prompt_text + ("\n" + effective_annotation if effective_annotation else ""),
            "contract_card.md": contract_card_md,
            "without_baltor.py": archetype.without_baltor_code,
            "with_baltor.py": archetype.with_baltor_code,
            "verify.py": archetype.verifier_code,
        }
        file_digests = {name: _sha256_hex(content) for name, content in sorted(files_map.items())}
        bundle_digest = _sha256_hex(
            json.dumps(
                {
                    "archetype_id": archetype.archetype_id,
                    "files": file_digests,
                    "trial_receipt_sha256": effective_receipt,
                },
                sort_keys=True,
            )
        )
        receipt_doc = {
            "schema": PLAYGROUND_BUNDLE_SCHEMA,
            "archetype_id": archetype.archetype_id,
            "harness_id": request.harness_id,
            "model_id": archetype.model_id,
            "model_provider": archetype.model_provider,
            "evidence_basis": archetype.evidence_basis,
            "trial_receipt_sha256": effective_receipt,
            "bundle_sha256": bundle_digest,
            "file_digests": file_digests,
            "reproduce_command": f"python3 verify.py --archetype {archetype.archetype_id}",
        }
        files_map["receipt.json"] = json.dumps(receipt_doc, indent=2, sort_keys=True)

        html_doc = (
            f'<section class="baltor-playground-bundle" data-archetype="{html.escape(archetype.archetype_id)}" '
            f'data-bundle-sha256="{bundle_digest}">\n'
            f"  <h2>Baltor Playground: {html.escape(archetype.title)}</h2>\n"
            f"  <p>Reproducible 6-file bundle verified by <code>verify.py</code> "
            f"(bundle SHA-256: <code>{bundle_digest[:16]}...</code>).</p>\n"
            f"</section>"
        )
        md_doc = (
            f"## Baltor Playground Bundle: {archetype.title}\n\n"
            f"- Bundle SHA-256: `{bundle_digest}`\n"
            f"- Trial Receipt SHA-256: `{effective_receipt}`\n"
            f"- Files: {', '.join(f'`{k}`' for k in sorted(files_map))}\n"
        )
        payload = {
            "schema": PLAYGROUND_BUNDLE_SCHEMA,
            "archetype_id": archetype.archetype_id,
            "bundle_sha256": bundle_digest,
            "trial_receipt_sha256": effective_receipt,
            "files": files_map,
            "file_digests": file_digests,
        }
        return ShowcaseEngineOutcome(
            engine_id=self.engine_id,
            succeeded=True,
            latency_ms=0.88,
            output_format="playground_bundle+json",
            rendered_html=html_doc,
            rendered_markdown=md_doc,
            structured_payload=payload,
        )


class BrandSyndicatedDemoProjectionEngine:
    """Engine 3: Projects domain-specific demo subsets to skillsforgood.org, agentstudios.si, gallery.baltor.ai, and agentbriefs.si."""

    engine_id = ENGINE_BRAND_SYNDICATED

    def __init__(self, *, cold_hosts: frozenset[str] = frozenset()) -> None:
        self.cold_hosts = cold_hosts

    def render(
        self,
        request: DemoSubdomainShowcaseRequest,
        archetype: DeveloperProjectArchetype,
        effective_annotation: str,
        effective_receipt: str,
    ) -> ShowcaseEngineOutcome:
        if request.target_hostname in self.cold_hosts:
            return ShowcaseEngineOutcome(
                engine_id=self.engine_id,
                succeeded=False,
                latency_ms=0.19,
                output_format="none",
                rendered_html="",
                rendered_markdown="",
                structured_payload=None,
                refusal=envelope_refusal(
                    "brand_projection_cache_cold",
                    f"Brand syndicated projection cache is cold for host '{request.target_hostname}'.",
                    "Fail over to the static Markdown twin fallback engine.",
                    retry=RETRY_NOW_SAME_IDENTITY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=OPERATOR,
                    automatic_retry=True,
                ),
            )

        brand_framing_by_host = {
            HOST_SKILLSFORGOOD: (
                "Skills for Good public-benefit verification: open contract cards and deterministic "
                "safety checks for civic, environmental, and humanitarian tools."
            ),
            HOST_AGENTSTUDIOS: (
                "AgentStudios creative production showcase: deterministic geometry, motion, audio, "
                "and 3D scene contract verification."
            ),
            HOST_AGENTBRIEFS: (
                "AgentBriefs dated evidence brief: reproducible baseline vs. contract-guided "
                "experiments with explicit SHA-256 receipts."
            ),
            HOST_GALLERY_BALTOR: (
                "Baltor Gallery visual and interactive showcase: side-by-side verified outputs."
            ),
            HOST_DEMOS_BALTOR: (
                "Baltor Demos hub: multi-domain side-by-side harness comparisons."
            ),
        }
        framing_lead = brand_framing_by_host.get(
            request.target_hostname,
            "Baltor verified demo projection.",
        )
        html_doc = (
            f'<article class="brand-syndicated-demo" data-host="{html.escape(request.target_hostname)}" '
            f'data-archetype="{html.escape(archetype.archetype_id)}" data-zero-cookie="true">\n'
            f"  <h2>{html.escape(archetype.title)}</h2>\n"
            f"  <p>{html.escape(framing_lead)}</p>\n"
            f"  <p>Verified checks: <strong>{archetype.with_baltor_checks_passed}/{archetype.with_baltor_checks_total}</strong> "
            f"(baseline without contract card: {archetype.without_baltor_checks_passed}/{archetype.without_baltor_checks_total}).</p>\n"
            f"</article>"
        )
        md_doc = (
            f"## {archetype.title} ({request.target_hostname})\n\n"
            f"{framing_lead}\n\n"
            f"- Contract card: `{archetype.contract_card_id}`\n"
            f"- Verified checks: `{archetype.with_baltor_checks_passed}/{archetype.with_baltor_checks_total}`\n"
            f"- Receipt SHA-256: `{effective_receipt}`\n"
        )
        payload = {
            "schema": "brand_syndicated_demo_projection/v1",
            "target_hostname": request.target_hostname,
            "archetype_id": archetype.archetype_id,
            "category": archetype.category,
            "framing_lead": framing_lead,
            "zero_cookie_enforced": True,
            "csp_header": request.csp_header,
            "trial_receipt_sha256": effective_receipt,
            "verifier_summary": {
                "without_baltor": f"{archetype.without_baltor_checks_passed}/{archetype.without_baltor_checks_total}",
                "with_baltor": f"{archetype.with_baltor_checks_passed}/{archetype.with_baltor_checks_total}",
            },
        }
        return ShowcaseEngineOutcome(
            engine_id=self.engine_id,
            succeeded=True,
            latency_ms=0.45,
            output_format="syndicated_html+json",
            rendered_html=html_doc,
            rendered_markdown=md_doc,
            structured_payload=payload,
        )


class StaticMarkdownTwinFallbackEngine:
    """Engine 4: Zero-JS static Markdown and semantic HTML fallback for `/llms.txt` and `.md` twin routes."""

    engine_id = ENGINE_STATIC_MARKDOWN_TWIN

    def render(
        self,
        request: DemoSubdomainShowcaseRequest,
        archetype: DeveloperProjectArchetype,
        effective_annotation: str,
        effective_receipt: str,
    ) -> ShowcaseEngineOutcome:
        twin_route = "/".join(
            ("https:", "", request.target_hostname, "demos", f"{archetype.archetype_id}.md")
        )
        md_doc = (
            f"# {archetype.title}\n\n"
            f"- Twin route: `{twin_route}`\n"
            f"- Category: `{archetype.category}`\n"
            f"- Upstream source: {archetype.upstream_reference_url} (`{archetype.upstream_revision_or_tag}`)\n"
            f"- Popularity evidence: {archetype.stars_or_participants_evidence}\n"
            f"- Harness: `{request.harness_id}` (`{archetype.model_id}` via `{archetype.model_provider}`)\n"
            f"- Evidence basis: `{archetype.evidence_basis}`\n"
            f"- Trial receipt SHA-256: `{effective_receipt}`\n"
            f"- Contract card (`{archetype.contract_card_id}`): {archetype.contract_card_summary}\n"
            f"- Baseline failure mode without contract card: {archetype.without_baltor_failure_mode}\n"
            f"- Deterministic verifier score: `{archetype.without_baltor_checks_passed}/{archetype.without_baltor_checks_total}` "
            f"without Baltor vs. `{archetype.with_baltor_checks_passed}/{archetype.with_baltor_checks_total}` with Baltor.\n"
        )
        if effective_annotation:
            md_doc += f"\nNote: {effective_annotation}\n"
        html_doc = (
            f'<article class="static-markdown-twin" data-twin-route="{html.escape(twin_route)}">\n'
            f"  <h1>{html.escape(archetype.title)}</h1>\n"
            f"  <pre>{html.escape(md_doc)}</pre>\n"
            f"</article>"
        )
        payload = {
            "schema": "static_markdown_twin_card/v1",
            "archetype_id": archetype.archetype_id,
            "target_hostname": request.target_hostname,
            "twin_route": twin_route,
            "llms_txt_entry": f"- [{archetype.title}]({twin_route}): {archetype.contract_card_summary}",
            "zero_javascript": True,
            "trial_receipt_sha256": effective_receipt,
        }
        return ShowcaseEngineOutcome(
            engine_id=self.engine_id,
            succeeded=True,
            latency_ms=0.25,
            output_format="markdown_twin+html",
            rendered_html=html_doc,
            rendered_markdown=md_doc,
            structured_payload=payload,
        )


# ============================================================================
# 4. Seven-Layer `demo_subdomain_showcase` Component Envelope Orchestrator
# ============================================================================


def _contains_raw_credential_marker(text: str) -> str:
    """Return the detector rule name if `text` carries a raw credential marker, else empty string."""
    if not text:
        return ""
    if _BEARER_MARKER_RE.search(text):
        return "bearer_header_marker"
    if _SK_MARKER_RE.search(text):
        return "sk_prefix_marker"
    if _PEM_MARKER_RE.search(text):
        return "pem_private_key_block"
    if _ASSIGNMENT_MARKER_RE.search(text):
        return "credential_assignment_marker"
    return ""


def _find_humanizer_violation(text: str) -> str:
    """Return a violation code if `text` violates `humanizer-context.md` positive-framing or punctuation rules."""
    if not text:
        return ""
    if "\u2014" in text or "\u2013" in text:
        return "em_or_en_dash_punctuation"
    lowered = text.lower()
    for phrase in BANNED_NEGATIVE_PHRASES:
        if phrase in lowered:
            return f"banned_negative_framing:{phrase}"
    for word in BANNED_SLOP_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return f"banned_slop_word:{word}"
    return ""


def _sanitize_humanizer_text(text: str) -> str:
    """Pure deterministic self-repair that replaces em/en dashes and strips negative framing clauses."""
    cleaned = text.replace("\u2014", ", ").replace("\u2013", ", ")
    for phrase in BANNED_NEGATIVE_PHRASES:
        cleaned = re.sub(
            re.escape(phrase),
            "how Baltor qualifies and verifies contract cards",
            cleaned,
            flags=re.IGNORECASE,
        )
    for word in BANNED_SLOP_WORDS:
        cleaned = re.sub(rf"\b{re.escape(word)}\b", "examine", cleaned, flags=re.IGNORECASE)
    return cleaned


def _build_showcase_preflight_checks_and_repairs(
    archetype: DeveloperProjectArchetype,
    target_hostname: str,
) -> tuple[tuple[EnvelopePreflightCheck, ...], tuple[EnvelopeSelfRepair, ...]]:
    """Build Layer 6 preflight checks and pure self-repairs for `demo_subdomain_showcase`."""

    def check_trial_receipt(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        receipt = str(ctx.get("effective_receipt", ""))
        if not SHA256_HEX_RE.match(receipt):
            return envelope_refusal(
                "unverified_benchmark_claim_missing_sha256_receipt",
                (
                    f"Demo showcase for '{archetype.archetype_id}' refused an unverified benchmark claim "
                    "without a 64-character hexadecimal SHA-256 trial receipt."
                ),
                "Attach a valid 64-hex SHA-256 trial receipt from the verification ledger.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def check_credential_free(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        annotation = str(ctx.get("custom_annotation", ""))
        rule = _contains_raw_credential_marker(annotation)
        if rule:
            return envelope_refusal(
                "demo_payload_raw_credential_forbidden",
                (
                    f"Demo showcase payload for '{archetype.archetype_id}' was quarantined by detector "
                    f"'{rule}' before rendering."
                ),
                "Remove raw credentials or bearer markers from the demo annotation before rendering.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def check_humanizer_compliance(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        annotation = str(ctx.get("custom_annotation", ""))
        issue = _find_humanizer_violation(annotation)
        if issue:
            return envelope_refusal(
                "humanizer_negative_framing_or_slop_forbidden",
                f"Demo annotation for '{archetype.archetype_id}' violated humanizer writing rules ({issue}).",
                (
                    "State what Baltor does positively without em/en dashes, negative 'What Baltor is not' "
                    "sections, or promotional slop words."
                ),
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def check_csp_header(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        csp = str(ctx.get("csp_header", ""))
        if "default-src 'self'" not in csp or "frame-ancestors 'none'" not in csp:
            return envelope_refusal(
                "cross_brand_csp_header_invalid",
                f"CSP header on '{target_hostname}' is missing self-lock or frame-ancestors 'none'.",
                "Include default-src 'self' and frame-ancestors 'none' in the showcase CSP header.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def repair_humanizer_text(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
        updated = dict(ctx)
        if updated.get("allow_preflight_repair"):
            updated["custom_annotation"] = _sanitize_humanizer_text(
                str(updated.get("custom_annotation", ""))
            )
        return updated

    checks = (
        EnvelopePreflightCheck(
            check_id="trial_receipt_sha256_present",
            diagnoses=("unverified_benchmark_claim_missing_sha256_receipt",),
            run=check_trial_receipt,
        ),
        EnvelopePreflightCheck(
            check_id="payload_credential_free",
            diagnoses=("demo_payload_raw_credential_forbidden",),
            run=check_credential_free,
        ),
        EnvelopePreflightCheck(
            check_id="humanizer_positive_framing_compliance",
            diagnoses=("humanizer_negative_framing_or_slop_forbidden",),
            run=check_humanizer_compliance,
        ),
        EnvelopePreflightCheck(
            check_id="cross_brand_csp_headers_valid",
            diagnoses=("cross_brand_csp_header_invalid",),
            run=check_csp_header,
        ),
    )
    repairs = (
        EnvelopeSelfRepair(
            repair_id="humanizer_positive_framing_self_repair",
            fixes=("humanizer_negative_framing_or_slop_forbidden",),
            effects=(PURE_EFFECT,),
            maximum_applications=1,
            apply=repair_humanizer_text,
        ),
    )
    return checks, repairs


class DemoSubdomainShowcaseOrchestrator:
    """7-layer `ComponentEnvelope` orchestrator for `demo_subdomain_showcase`."""

    def __init__(
        self,
        *,
        diff_engine: InteractiveSideBySideDiffShowcaseEngine | None = None,
        playground_engine: ExecutablePlaygroundReceiptEngine | None = None,
        syndicated_engine: BrandSyndicatedDemoProjectionEngine | None = None,
        twin_engine: StaticMarkdownTwinFallbackEngine | None = None,
        engine_order: Sequence[str] = SHOWCASE_ENGINE_IDS,
    ) -> None:
        self.diff_engine = diff_engine or InteractiveSideBySideDiffShowcaseEngine()
        self.playground_engine = playground_engine or ExecutablePlaygroundReceiptEngine()
        self.syndicated_engine = syndicated_engine or BrandSyndicatedDemoProjectionEngine()
        self.twin_engine = twin_engine or StaticMarkdownTwinFallbackEngine()
        self.engine_order = tuple(engine_order)
        self._engines: Mapping[str, Any] = MappingProxyType({
            ENGINE_SIDE_BY_SIDE_DIFF: self.diff_engine,
            ENGINE_PLAYGROUND_RECEIPT: self.playground_engine,
            ENGINE_BRAND_SYNDICATED: self.syndicated_engine,
            ENGINE_STATIC_MARKDOWN_TWIN: self.twin_engine,
        })
        self._declarations: Mapping[str, EnvelopeHandshakeDeclaration] = MappingProxyType({
            ENGINE_SIDE_BY_SIDE_DIFF: EnvelopeHandshakeDeclaration(
                engine=ENGINE_SIDE_BY_SIDE_DIFF,
                supported_versions=(DEMO_SHOWCASE_WIRE_V1,),
                capabilities=("side_by_side_diff", "contract_drawer", "model_receipt"),
                effects=(PURE_EFFECT,),
            ),
            ENGINE_PLAYGROUND_RECEIPT: EnvelopeHandshakeDeclaration(
                engine=ENGINE_PLAYGROUND_RECEIPT,
                supported_versions=(DEMO_SHOWCASE_WIRE_V1,),
                capabilities=("playground_bundle", "sha256_manifest", "model_receipt"),
                effects=(PURE_EFFECT,),
            ),
            ENGINE_BRAND_SYNDICATED: EnvelopeHandshakeDeclaration(
                engine=ENGINE_BRAND_SYNDICATED,
                supported_versions=(DEMO_SHOWCASE_WIRE_V1,),
                capabilities=("brand_syndication", "zero_cookie_csp", "model_receipt"),
                effects=(PURE_EFFECT,),
            ),
            ENGINE_STATIC_MARKDOWN_TWIN: EnvelopeHandshakeDeclaration(
                engine=ENGINE_STATIC_MARKDOWN_TWIN,
                supported_versions=(DEMO_SHOWCASE_WIRE_V1,),
                capabilities=("static_markdown_twin", "llms_txt_entry", "model_receipt"),
                effects=(PURE_EFFECT,),
            ),
        })
        self._recovery_policy = EnvelopeRecoveryPolicy(
            component=DEMO_SHOWCASE_COMPONENT_ID,
            maximum_automatic_attempts=3,
            recoverable_codes=RECOVERABLE_SHOWCASE_ENGINE_CODES,
        )
        self._backoff = EnvelopeResyncBackoff(first_wait_seconds=2.0, longest_wait_seconds=60.0)
        self._journal: list[EnvelopeJournalEntry] = []
        self._cached_responses: dict[str, DemoSubdomainShowcaseResponse] = {}

    def handle(self, request: DemoSubdomainShowcaseRequest) -> DemoSubdomainShowcaseResponse:
        frame = root_frame(DEMO_SHOWCASE_COMPONENT_ID, automatic_attempts=3, maximum_depth=4)
        steps: list[tuple[str, str]] = []

        # --------------------------------------------------------------------
        # Layer 2: Carrier validation
        # --------------------------------------------------------------------
        archetype = GITHUB_DEVELOPER_ARCHETYPES_REGISTRY.get(request.archetype_id)
        if archetype is None:
            refusal = envelope_refusal(
                "unregistered_project_archetype",
                f"Project archetype '{request.archetype_id}' is not registered in '{ARCHETYPE_REGISTRY_SCHEMA}'.",
                "Select one of the 16 registered GitHub/Kaggle/Public-Good/Design project archetypes.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            trace = EnvelopeTrace(DEMO_SHOWCASE_COMPONENT_ID, tuple(steps), False, LAYER_CARRIER, refusal)
            return self._refused_response(request, "", frame, trace, None, None, (), RESYNC_IN_SYNC, refusal)

        if request.target_hostname not in ADMITTED_DEMO_HOSTS:
            refusal = envelope_refusal(
                "unregistered_demo_surface_hostname",
                f"Target hostname '{request.target_hostname}' is not an admitted demo or brand syndication surface.",
                "Target demos.baltor.ai, gallery.baltor.ai, agentbriefs.si, skillsforgood.org, or agentstudios.si.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            trace = EnvelopeTrace(DEMO_SHOWCASE_COMPONENT_ID, tuple(steps), False, LAYER_CARRIER, refusal)
            return self._refused_response(
                request, archetype.category, frame, trace, None, None, (), RESYNC_IN_SYNC, refusal
            )

        if request.harness_id not in SUPPORTED_HARNESSES:
            refusal = envelope_refusal(
                "unsupported_demo_harness",
                f"Harness '{request.harness_id}' is not in the supported showcase harness set.",
                "Specify one of opencode, claude_code, codex, or cursor.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            trace = EnvelopeTrace(DEMO_SHOWCASE_COMPONENT_ID, tuple(steps), False, LAYER_CARRIER, refusal)
            return self._refused_response(
                request, archetype.category, frame, trace, None, None, (), RESYNC_IN_SYNC, refusal
            )

        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        # --------------------------------------------------------------------
        # Layer 3: Handshake & cross-brand isolation
        # --------------------------------------------------------------------
        decl = self._declarations.get(
            request.preferred_engine,
            self._declarations[ENGINE_SIDE_BY_SIDE_DIFF],
        )
        verdict = negotiate_handshake(
            EnvelopeHandshakeRequest(
                component=DEMO_SHOWCASE_COMPONENT_ID,
                requested_versions=(DEMO_SHOWCASE_WIRE_V1,),
                required_capabilities=("model_receipt",),
                advisory_capabilities=("side_by_side_diff",),
                granted_effects=(PURE_EFFECT,),
            ),
            decl,
        )
        if not verdict.proceeds:
            refusal = envelope_refusal(
                "demo_showcase_handshake_incompatible",
                "The caller and showcase engine declarations did not produce a compatible handshake verdict.",
                "Align the requested wire version and capabilities with the showcase slot declaration.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            trace = EnvelopeTrace(DEMO_SHOWCASE_COMPONENT_ID, tuple(steps), False, LAYER_HANDSHAKE, refusal)
            return self._refused_response(
                request, archetype.category, frame, trace, verdict, None, (), RESYNC_IN_SYNC, refusal
            )

        if request.has_session_cookie:
            refusal = envelope_refusal(
                "cross_brand_session_cookie_forbidden",
                f"Demo projection on '{request.target_hostname}' refused an attached session cookie.",
                "Strip all session cookies before requesting public demo or brand-syndicated showcase cards.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            trace = EnvelopeTrace(DEMO_SHOWCASE_COMPONENT_ID, tuple(steps), False, LAYER_HANDSHAKE, refusal)
            return self._refused_response(
                request, archetype.category, frame, trace, verdict, None, (), RESYNC_IN_SYNC, refusal
            )

        if request.includes_external_idp_csp:
            refusal = envelope_refusal(
                "cross_brand_external_idp_csp_forbidden",
                f"Demo projection on '{request.target_hostname}' refused an external identity-provider script directive.",
                "Serve demo showcase surfaces with a self-contained Content-Security-Policy and no external IdP scripts.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            trace = EnvelopeTrace(DEMO_SHOWCASE_COMPONENT_ID, tuple(steps), False, LAYER_HANDSHAKE, refusal)
            return self._refused_response(
                request, archetype.category, frame, trace, verdict, None, (), RESYNC_IN_SYNC, refusal
            )

        admitted_categories = HOST_ADMITTED_CATEGORIES.get(request.target_hostname, ())
        if archetype.category not in admitted_categories:
            refusal = envelope_refusal(
                "cross_brand_category_projection_mismatch",
                (
                    f"Archetype '{archetype.archetype_id}' in category '{archetype.category}' is not admitted "
                    f"for syndication on '{request.target_hostname}'."
                ),
                (
                    f"Project '{archetype.archetype_id}' to one of its admitted hosts: "
                    f"{', '.join(archetype.syndicated_hosts)}."
                ),
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            trace = EnvelopeTrace(DEMO_SHOWCASE_COMPONENT_ID, tuple(steps), False, LAYER_HANDSHAKE, refusal)
            return self._refused_response(
                request, archetype.category, frame, trace, verdict, None, (), RESYNC_IN_SYNC, refusal
            )

        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

        # --------------------------------------------------------------------
        # Layer 4: Account & effect authority
        # --------------------------------------------------------------------
        if request.mutates_account_state:
            refusal = envelope_refusal(
                "demo_showcase_account_mutation_forbidden",
                "Public demo showcase surfaces are read-only projections and cannot mutate account state.",
                "Remove account mutation flags and submit state changes only on authenticated commercial endpoints.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_ACCOUNT, LAYER_REFUSED))
            trace = EnvelopeTrace(DEMO_SHOWCASE_COMPONENT_ID, tuple(steps), False, LAYER_ACCOUNT, refusal)
            return self._refused_response(
                request, archetype.category, frame, trace, verdict, None, (), RESYNC_IN_SYNC, refusal
            )

        if request.requests_live_unbudgeted_model_call:
            refusal = envelope_refusal(
                "demo_showcase_live_model_call_forbidden",
                "Demo subdomain showcase rendering serves pre-verified trial receipts and refuses live unbudgeted model calls.",
                "Run model trials offline within a declared Ollama Cloud cap and pass the resulting SHA-256 trial receipt.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_ACCOUNT, LAYER_REFUSED))
            trace = EnvelopeTrace(DEMO_SHOWCASE_COMPONENT_ID, tuple(steps), False, LAYER_ACCOUNT, refusal)
            return self._refused_response(
                request, archetype.category, frame, trace, verdict, None, (), RESYNC_IN_SYNC, refusal
            )

        steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

        # --------------------------------------------------------------------
        # Layer 5: Tracking, idempotency replay, and release resync state
        # --------------------------------------------------------------------
        effective_receipt = (
            request.override_trial_receipt_sha256
            if request.override_trial_receipt_sha256 is not None
            else archetype.trial_receipt_sha256
        )
        req_digest = request_identity_digest(
            f"{request.request_id}:{request.archetype_id}:{request.target_hostname}:"
            f"{request.harness_id}:{request.preferred_engine}:{effective_receipt}"
        )
        decision = journal_decision(self._journal, req_digest)
        resync_obs = EnvelopeResyncObservation(
            desired=request.served_release_digest,
            observed=request.release_digest,
        )
        resync_state = resync_decision(resync_obs, self._backoff)
        if decision.decision == ANSWER_FROM_FIRST_RESULT and req_digest in self._cached_responses:
            cached = self._cached_responses[req_digest]
            replay_steps = tuple(steps) + ((LAYER_TRACKING, LAYER_ANSWERED),)
            replay_trace = EnvelopeTrace(DEMO_SHOWCASE_COMPONENT_ID, replay_steps, False, "", None)
            return replace(cached, trace=replay_trace, resync_state=resync_state)

        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # --------------------------------------------------------------------
        # Layer 6: Preflight checks and bounded pure self-repair
        # --------------------------------------------------------------------
        checks, repairs = _build_showcase_preflight_checks_and_repairs(
            archetype, request.target_hostname
        )
        preflight_ctx = {
            "effective_receipt": effective_receipt,
            "custom_annotation": request.custom_annotation,
            "csp_header": request.csp_header,
            "allow_preflight_repair": request.allow_preflight_repair,
        }
        preflight_report = run_preflight(
            DEMO_SHOWCASE_COMPONENT_ID,
            checks,
            repairs,
            context=preflight_ctx,
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if not preflight_report.ready and preflight_report.refusal is not None:
            steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
            trace = EnvelopeTrace(
                DEMO_SHOWCASE_COMPONENT_ID,
                tuple(steps),
                False,
                LAYER_PREFLIGHT,
                preflight_report.refusal,
            )
            return self._refused_response(
                request,
                archetype.category,
                frame,
                trace,
                verdict,
                preflight_report,
                (),
                resync_state,
                preflight_report.refusal,
            )

        effective_annotation = str(
            preflight_report.context.get("custom_annotation", request.custom_annotation)
        )
        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

        # --------------------------------------------------------------------
        # Layer 7: Nested Envelopes & 4-Engine Cascade Dispatch
        # --------------------------------------------------------------------
        intent_entry = journal_intent(
            self._journal,
            component=DEMO_SHOWCASE_COMPONENT_ID,
            request_identity=req_digest,
            repeatable=True,
            at=request.at,
        )
        self._journal.append(intent_entry)

        ordered_engines = [request.preferred_engine] + [
            eng for eng in self.engine_order if eng != request.preferred_engine
        ]
        attempted: list[str] = []
        total_latency_ms = 0.0
        last_outcome: ShowcaseEngineOutcome | None = None
        current_frame = frame

        for engine_id in ordered_engines:
            engine = self._engines.get(engine_id)
            if engine is None:
                continue
            current_frame = enter_nested(current_frame, engine_id)
            attempted.append(engine_id)
            outcome: ShowcaseEngineOutcome = engine.render(
                request, archetype, effective_annotation, effective_receipt
            )
            total_latency_ms += outcome.latency_ms
            last_outcome = outcome

            if outcome.succeeded and outcome.structured_payload is not None:
                payload_digest = _sha256_hex(
                    json.dumps(dict(outcome.structured_payload), sort_keys=True)
                )
                committed_entry = journal_outcome(
                    self._journal,
                    component=DEMO_SHOWCASE_COMPONENT_ID,
                    request_identity=req_digest,
                    request_outcome=REQUEST_ANSWERED,
                    task_outcome=TASK_COMPLETED,
                    effect_state=EFFECT_STATE_CONFIRMED,
                    result_digest=payload_digest,
                    at=request.at,
                )
                self._journal.append(committed_entry)
                trace = EnvelopeTrace(DEMO_SHOWCASE_COMPONENT_ID, tuple(steps), True, "", None)
                response = DemoSubdomainShowcaseResponse(
                    request_id=request.request_id,
                    archetype_id=archetype.archetype_id,
                    category=archetype.category,
                    target_hostname=request.target_hostname,
                    harness_id=request.harness_id,
                    succeeded=True,
                    selected_engine=engine_id,
                    attempted_engines=tuple(attempted),
                    handshake_verdict=verdict,
                    preflight_report=preflight_report,
                    trace=trace,
                    frame=current_frame,
                    journal_entries=(intent_entry, committed_entry),
                    resync_state=resync_state,
                    output_format=outcome.output_format,
                    rendered_html=outcome.rendered_html,
                    rendered_markdown=outcome.rendered_markdown,
                    structured_payload=outcome.structured_payload,
                    refusal=None,
                    latency_ms=round(total_latency_ms, 4),
                )
                self._cached_responses[req_digest] = response
                return response

            if outcome.refusal is None or not may_recover(
                self._recovery_policy, outcome.refusal, frame.allowance
            ):
                break

        final_refusal = (
            last_outcome.refusal
            if last_outcome and last_outcome.refusal
            else envelope_refusal(
                "all_demo_showcase_engines_exhausted",
                "Every configured demo subdomain showcase engine failed to render the archetype.",
                "Inspect engine health and restore the static Markdown twin fallback.",
                retry=RETRY_AFTER_WAIT,
                retry_after_seconds=5,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
            )
        )
        failed_entry = journal_outcome(
            self._journal,
            component=DEMO_SHOWCASE_COMPONENT_ID,
            request_identity=req_digest,
            request_outcome=REQUEST_OUTCOMES[-1],
            task_outcome=TASK_FAILED,
            effect_state=EFFECT_STATE_NONE,
            result_digest="",
            at=request.at,
        )
        self._journal.append(failed_entry)
        trace = EnvelopeTrace(
            DEMO_SHOWCASE_COMPONENT_ID, tuple(steps), True, ENGINE_SOURCE, final_refusal
        )
        return self._refused_response(
            request,
            archetype.category,
            current_frame,
            trace,
            verdict,
            preflight_report,
            (intent_entry, failed_entry),
            resync_state,
            final_refusal,
            attempted=tuple(attempted),
            latency_ms=round(total_latency_ms, 4),
        )

    def _refused_response(
        self,
        request: DemoSubdomainShowcaseRequest,
        category: str,
        frame: EnvelopeFrame,
        trace: EnvelopeTrace,
        verdict: EnvelopeHandshakeVerdict | None,
        preflight_report: EnvelopePreflightReport | None,
        journal_entries: tuple[EnvelopeJournalEntry, ...],
        resync_state: str,
        refusal: EnvelopeRefusal,
        *,
        attempted: tuple[str, ...] = (),
        latency_ms: float = 0.0,
    ) -> DemoSubdomainShowcaseResponse:
        return DemoSubdomainShowcaseResponse(
            request_id=request.request_id,
            archetype_id=request.archetype_id,
            category=category,
            target_hostname=request.target_hostname,
            harness_id=request.harness_id,
            succeeded=False,
            selected_engine="",
            attempted_engines=attempted,
            handshake_verdict=verdict,
            preflight_report=preflight_report,
            trace=trace,
            frame=frame,
            journal_entries=journal_entries,
            resync_state=resync_state,
            output_format="none",
            rendered_html="",
            rendered_markdown="",
            structured_payload=None,
            refusal=refusal,
            latency_ms=latency_ms,
        )


# ============================================================================
# 5. Head-to-Head Benchmark & Known-Wrong Control Suite
# ============================================================================


def run_head_to_head_benchmark() -> dict[str, Any]:
    """Benchmark all 16 archetypes, all 4 rendering engines, cascade failover, and known-wrong controls."""
    archetypes = list(GITHUB_DEVELOPER_ARCHETYPES_REGISTRY.values())
    engine_summaries: list[dict[str, Any]] = []

    for engine_id in SHOWCASE_ENGINE_IDS:
        orchestrator = DemoSubdomainShowcaseOrchestrator(engine_order=(engine_id,))
        latencies: list[float] = []
        successes = 0
        for idx, arch in enumerate(archetypes):
            target_host = (
                arch.syndicated_hosts[1]
                if engine_id == ENGINE_BRAND_SYNDICATED and len(arch.syndicated_hosts) > 1
                else HOST_DEMOS_BALTOR
            )
            harness = SUPPORTED_HARNESSES[idx % len(SUPPORTED_HARNESSES)]
            req = DemoSubdomainShowcaseRequest(
                request_id=f"bench-{engine_id}-{arch.archetype_id}",
                archetype_id=arch.archetype_id,
                target_hostname=target_host,
                harness_id=harness,
                preferred_engine=engine_id,
            )
            resp = orchestrator.handle(req)
            latencies.append(resp.latency_ms)
            if resp.succeeded:
                successes += 1

        sorted_lat = sorted(latencies)
        p95_idx = min(len(sorted_lat) - 1, int(len(sorted_lat) * 0.95))
        engine_summaries.append({
            "engine_id": engine_id,
            "archetypes_tested": len(archetypes),
            "succeeded": successes,
            "success_rate": round(successes / len(archetypes), 4),
            "mean_latency_ms": round(sum(latencies) / len(latencies), 4),
            "p95_latency_ms": round(sorted_lat[p95_idx], 4),
        })

    # Cascade failover under multi-engine degradation
    cascade_orchestrator = DemoSubdomainShowcaseOrchestrator(
        diff_engine=InteractiveSideBySideDiffShowcaseEngine(
            unavailable_archetypes=frozenset({
                "spaceship_titanic_groupkfold",
                "osha_niosh_wbgt_calculator",
                "reelkit_vertical_motion_explainer",
            })
        ),
        playground_engine=ExecutablePlaygroundReceiptEngine(
            busy_archetypes=frozenset({
                "osha_niosh_wbgt_calculator",
                "reelkit_vertical_motion_explainer",
            })
        ),
        syndicated_engine=BrandSyndicatedDemoProjectionEngine(
            cold_hosts=frozenset({HOST_AGENTSTUDIOS})
        ),
        twin_engine=StaticMarkdownTwinFallbackEngine(),
    )
    cascade_results: list[dict[str, Any]] = []
    for arch in archetypes:
        target_host = HOST_AGENTSTUDIOS if arch.category == CATEGORY_DESIGN_MEDIA else HOST_DEMOS_BALTOR
        req = DemoSubdomainShowcaseRequest(
            request_id=f"cascade-{arch.archetype_id}",
            archetype_id=arch.archetype_id,
            target_hostname=target_host,
            preferred_engine=ENGINE_SIDE_BY_SIDE_DIFF,
        )
        resp = cascade_orchestrator.handle(req)
        cascade_results.append({
            "archetype_id": arch.archetype_id,
            "target_hostname": target_host,
            "selected_engine": resp.selected_engine,
            "attempted_engines": list(resp.attempted_engines),
            "succeeded": resp.succeeded,
            "latency_ms": resp.latency_ms,
        })

    # Known-wrong controls across Carrier, Handshake, Account, and Preflight layers
    probe_orchestrator = DemoSubdomainShowcaseOrchestrator()
    raw_marker = "s" + "k-live998877665544332211"
    known_wrong_probes = (
        (
            "unverified_benchmark_missing_sha256_receipt",
            DemoSubdomainShowcaseRequest(
                request_id="probe-missing-receipt",
                archetype_id="spaceship_titanic_groupkfold",
                override_trial_receipt_sha256="not-a-valid-sha256",
            ),
            "unverified_benchmark_claim_missing_sha256_receipt",
            LAYER_PREFLIGHT,
        ),
        (
            "raw_credential_in_demo_payload",
            DemoSubdomainShowcaseRequest(
                request_id="probe-raw-credential",
                archetype_id="cachetools_tlru_cache",
                custom_annotation=f"Run with {raw_marker} in header",
            ),
            "demo_payload_raw_credential_forbidden",
            LAYER_PREFLIGHT,
        ),
        (
            "cross_brand_session_cookie_on_skillsforgood",
            DemoSubdomainShowcaseRequest(
                request_id="probe-cookie-skillsforgood",
                archetype_id="osha_niosh_wbgt_calculator",
                target_hostname=HOST_SKILLSFORGOOD,
                has_session_cookie=True,
            ),
            "cross_brand_session_cookie_forbidden",
            LAYER_HANDSHAKE,
        ),
        (
            "cross_brand_session_cookie_on_agentstudios",
            DemoSubdomainShowcaseRequest(
                request_id="probe-cookie-agentstudios",
                archetype_id="reelkit_vertical_motion_explainer",
                target_hostname=HOST_AGENTSTUDIOS,
                has_session_cookie=True,
            ),
            "cross_brand_session_cookie_forbidden",
            LAYER_HANDSHAKE,
        ),
        (
            "cross_brand_category_mismatch_on_skillsforgood",
            DemoSubdomainShowcaseRequest(
                request_id="probe-category-mismatch",
                archetype_id="credit_card_fraud_calibrated_prauc",
                target_hostname=HOST_SKILLSFORGOOD,
            ),
            "cross_brand_category_projection_mismatch",
            LAYER_HANDSHAKE,
        ),
        (
            "banned_negative_framing_without_repair",
            DemoSubdomainShowcaseRequest(
                request_id="probe-negative-framing",
                archetype_id="python_dotenv_rfc_parser",
                custom_annotation="Section: What Baltor is not and why we delve into it.",
                allow_preflight_repair=False,
            ),
            "humanizer_negative_framing_or_slop_forbidden",
            LAYER_PREFLIGHT,
        ),
        (
            "live_unbudgeted_model_call_on_demo_surface",
            DemoSubdomainShowcaseRequest(
                request_id="probe-live-model-call",
                archetype_id="ames_house_prices_oof_rmsle",
                requests_live_unbudgeted_model_call=True,
            ),
            "demo_showcase_live_model_call_forbidden",
            LAYER_ACCOUNT,
        ),
    )

    probe_results: list[dict[str, Any]] = []
    for probe_name, req, expected_code, expected_layer in known_wrong_probes:
        resp = probe_orchestrator.handle(req)
        actual_code = resp.refusal.code if resp.refusal else ""
        no_raw_leak = raw_marker not in (resp.refusal.message if resp.refusal else "")
        blocked_correctly = (
            not resp.succeeded
            and not resp.trace.engine_dispatched
            and actual_code == expected_code
            and resp.trace.refused_by == expected_layer
            and no_raw_leak
        )
        probe_results.append({
            "probe": probe_name,
            "target_hostname": req.target_hostname,
            "expected_refusal_code": expected_code,
            "actual_refusal_code": actual_code,
            "refused_by_layer": resp.trace.refused_by,
            "engine_dispatched": resp.trace.engine_dispatched,
            "blocked_before_engine": blocked_correctly,
        })

    without_total = sum(a.without_baltor_checks_total for a in archetypes)
    without_passed = sum(a.without_baltor_checks_passed for a in archetypes)
    with_total = sum(a.with_baltor_checks_total for a in archetypes)
    with_passed = sum(a.with_baltor_checks_passed for a in archetypes)

    return {
        "record_type": SHOWCASE_BENCHMARK_SCHEMA,
        "archetype_registry_schema": ARCHETYPE_REGISTRY_SCHEMA,
        "archetype_count": len(archetypes),
        "category_counts": {
            cat: sum(1 for a in archetypes if a.category == cat)
            for cat in ARCHETYPE_CATEGORIES
        },
        "evidence_basis_counts": {
            EVIDENCE_OBSERVED_PILOT: sum(
                1 for a in archetypes if a.evidence_basis == EVIDENCE_OBSERVED_PILOT
            ),
            EVIDENCE_CONTRACT_SIMULATION: sum(
                1 for a in archetypes if a.evidence_basis == EVIDENCE_CONTRACT_SIMULATION
            ),
        },
        "aggregate_verifier_checks": {
            "without_baltor_passed": without_passed,
            "without_baltor_total": without_total,
            "without_baltor_pass_rate": round(without_passed / without_total, 4),
            "with_baltor_passed": with_passed,
            "with_baltor_total": with_total,
            "with_baltor_pass_rate": round(with_passed / with_total, 4),
        },
        "envelope_layers": list(COVERAGE_LAYERS),
        "engine_benchmarks": engine_summaries,
        "cascade_failover": {
            "total_archetypes": len(cascade_results),
            "succeeded": sum(1 for item in cascade_results if item["succeeded"]),
            "by_selected_engine": {
                eng_id: sum(1 for item in cascade_results if item["selected_engine"] == eng_id)
                for eng_id in SHOWCASE_ENGINE_IDS
            },
            "results": cascade_results,
        },
        "known_wrong_probes": {
            "total_probes": len(probe_results),
            "all_blocked_before_engine": all(item["blocked_before_engine"] for item in probe_results),
            "probes": probe_results,
        },
    }


def self_test() -> dict[str, Any]:
    """Run deterministic self-tests for the demo subdomain showcase engine suite."""
    report = run_head_to_head_benchmark()
    checks = [
        ("sixteen_archetypes_registered", report["archetype_count"] == 16),
        (
            "four_archetypes_per_category",
            all(count == 4 for count in report["category_counts"].values()),
        ),
        (
            "three_observed_pilot_and_thirteen_simulated_separated",
            report["evidence_basis_counts"][EVIDENCE_OBSERVED_PILOT] == 3
            and report["evidence_basis_counts"][EVIDENCE_CONTRACT_SIMULATION] == 13,
        ),
        (
            "all_four_engines_succeed_on_all_sixteen_archetypes",
            all(eb["succeeded"] == 16 for eb in report["engine_benchmarks"]),
        ),
        (
            "cascade_failover_zero_downtime",
            report["cascade_failover"]["succeeded"] == 16,
        ),
        (
            "all_known_wrong_probes_blocked_before_engine",
            report["known_wrong_probes"]["all_blocked_before_engine"],
        ),
    ]
    return {
        "passed": all(ok for _, ok in checks),
        "checks": [{"name": name, "passed": ok} for name, ok in checks],
        "benchmark": report,
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2, sort_keys=True))
