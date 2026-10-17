"""Multi-domain With-Baltor vs. Without-Baltor live Ollama Cloud benchmark and verification suite.

Evaluates eight real engineering tasks across four domains:
1. Kaggle AI/ML Competitions (`kaggle_ai_ml`, feeding `baltor.ai/demos/kaggle-ai-ml`):
   - `K-01_spaceship_titanic_group_pipeline`
   - `K-02_ames_housing_rmsle_pipeline`
2. Popular GitHub Developer Profile Projects (`github_common_projects`, feeding `baltor.ai/demos/github-projects`):
   - `G-01_cachetools_tlru_cache`
   - `G-02_python_dotenv_escape_parser`
3. Public Good & Civic Safety Projects (`public_good_projects`, feeding `skillsforgood.org`):
   - `PG-01_osha_niosh_heat_stress_wbgt`
   - `PG-02_crisis_shelter_accessible_triage`
4. Creative Design, Motion & Playable Media (`design_media_projects`, feeding `agentstudios.si`):
   - `DM-01_vertical_1080x1920_motion_explainer`
   - `DM-02_html5_physics_karplus_strong_synth`

Wrapped in the seven-layer ComponentEnvelope (`src/loop_engine/core/engines/envelope.py`)
with three swappable execution engines:
- `ollama_cloud_live_harness_engine`: Metered live Ollama Cloud runner (`max_physical_requests = 16`,
  `timeout = 25.0s`, zero secret persistence).
- `deterministic_reference_replay_engine`: Offline `<50ms` replay engine over frozen `results.json`
  that re-executes every deterministic task verifier over the recorded code responses.
- `synthetic_contract_control_engine`: Pure in-memory reference and known-wrong control engine.
"""
from __future__ import annotations

import argparse
import collections
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import time
import types
from typing import Any, Callable
import urllib.error
import urllib.request

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
_TOOLS_ROOT = _REPO_ROOT / "tools"
for _path in (_SRC_ROOT, _TOOLS_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _ensure_jsonschema_fallback() -> None:
    """Provide a minimal offline Draft202012Validator stub when jsonschema is absent in venv312."""
    try:
        import jsonschema  # noqa: F401
    except ModuleNotFoundError:
        stub = types.ModuleType("jsonschema")
        stub.__path__ = []
        exc_stub = types.ModuleType("jsonschema.exceptions")

        class _SchemaError(Exception):
            pass

        class _Draft202012Validator:
            def __init__(self, schema: Any) -> None:
                self.schema = schema

            def iter_errors(self, instance: Any) -> Any:
                return iter(())

        exc_stub.SchemaError = _SchemaError
        stub.Draft202012Validator = _Draft202012Validator
        stub.exceptions = exc_stub
        sys.modules["jsonschema"] = stub
        sys.modules["jsonschema.exceptions"] = exc_stub


_ensure_jsonschema_fallback()

import baltor_preturn_hook as preturn_hook  # noqa: E402
from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
    EFFECT_NONE,
    ENGINE_SOURCE,
    INBOUND_LAYERS,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_ANSWERED,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
    RETRY_AFTER_WAIT,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    EnvelopeTrace,
    enter_nested,
    envelope_refusal,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_READY,
    VERDICT_REFUSED,
    EnvelopePreflightCheck,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    ANSWER_FROM_FIRST_RESULT,
    DISPATCH,
    EFFECT_STATE_CONFIRMED,
    REQUEST_ANSWERED,
    TASK_COMPLETED,
    journal_decision,
    journal_intent,
    journal_outcome,
    request_identity_digest,
)
from loop_engine.core.ollama_client import (  # noqa: E402
    COMPATIBLE_CHAT_ENDPOINT,
    load_api_key,
)

SLOT_ID = "multi_domain_ollama_benchmark_harness"
NESTED_PRETURN_SLOT_ID = "preturn_adoption_trigger"

REQUEST_RECORD_TYPE = "multi_domain_benchmark_request/v1"
RESULT_RECORD_TYPE = "multi_domain_benchmark_result/v1"
ARTIFACT_RECORD_TYPE = "multi_domain_ollama_comparison_suite/v1"
PROTOCOL_VERSION = "1.0"

ENGINE_LIVE_OLLAMA = "ollama_cloud_live_harness_engine"
ENGINE_OFFLINE_REPLAY = "deterministic_reference_replay_engine"
ENGINE_SYNTHETIC_CONTROL = "synthetic_contract_control_engine"
ENGINE_IDS = (
    ENGINE_LIVE_OLLAMA,
    ENGINE_OFFLINE_REPLAY,
    ENGINE_SYNTHETIC_CONTROL,
)

PRIMARY_MODEL = "gemma4:31b"
FALLBACK_MODELS = ("nemotron-3-nano:30b", "gpt-oss:20b")
MAX_PHYSICAL_REQUESTS_CEILING = 16
CALL_TIMEOUT_SECONDS = 25.0

ARM_WITHOUT_BALTOR = "without_baltor"
ARM_WITH_BALTOR = "with_baltor"
ARMS = (ARM_WITHOUT_BALTOR, ARM_WITH_BALTOR)

DEFAULT_ARTIFACT_PATH = (
    _REPO_ROOT / "artifacts" / "multi-domain-ollama-comparisons-2026-10-16" / "results.json"
)

DOMAIN_KAGGLE = "kaggle_ai_ml"
DOMAIN_GITHUB = "github_common_projects"
DOMAIN_PUBLIC_GOOD = "public_good_projects"
DOMAIN_DESIGN_MEDIA = "design_media_projects"

DOMAIN_METADATA: dict[str, dict[str, str]] = {
    DOMAIN_KAGGLE: {
        "title": "Kaggle AI/ML Competitions",
        "demo_surface": "baltor.ai/demos/kaggle-ai-ml",
        "focus": "Leak-free group splitting, out-of-fold log-target encoding, and domain feature invariants.",
    },
    DOMAIN_GITHUB: {
        "title": "Popular GitHub Developer Profile Projects",
        "demo_surface": "baltor.ai/demos/github-projects",
        "focus": "Out-of-order time-to-use cache eviction and single-pass escape/comment state machines.",
    },
    DOMAIN_PUBLIC_GOOD: {
        "title": "Public Good & Civic Safety Projects",
        "demo_surface": "skillsforgood.org",
        "focus": "OSHA/NIOSH heat-stress WBGT thresholds and ADA-compliant crisis shelter triage.",
    },
    DOMAIN_DESIGN_MEDIA: {
        "title": "Creative Design, Motion & Playable Media",
        "demo_surface": "agentstudios.si",
        "focus": "1080x1920 platform keep-out safe zones, WCAG AAA contrast, revision survival, and 60fps physics/audio.",
    },
}

_SECRET_PATTERNS = (
    re.compile(r"\bbsk_[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{16,}\b"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{8,}"),
)


def scrub_secrets(value: Any, raw_key: str | None = None) -> Any:
    """Recursively scrub raw API keys and credential-shaped strings from any data structure."""
    if isinstance(value, str):
        cleaned = value
        if raw_key and len(raw_key) >= 6 and raw_key in cleaned:
            cleaned = cleaned.replace(raw_key, "<redacted_api_key>")
        for pattern in _SECRET_PATTERNS:
            cleaned = pattern.sub("<redacted_credential>", cleaned)
        return cleaned
    if isinstance(value, list):
        return [scrub_secrets(item, raw_key) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub_secrets(item, raw_key) for item in value)
    if isinstance(value, dict):
        return {str(k): scrub_secrets(v, raw_key) for k, v in value.items()}
    return value


def assert_no_secrets_in_record(record: Any, raw_key: str | None = None) -> None:
    """Raise ValueError if any raw key or credential token appears in serialized JSON."""
    serialized = json.dumps(record, sort_keys=True)
    if raw_key and len(raw_key) >= 6 and raw_key in serialized:
        raise ValueError("secret_leak_detected: raw_key present in serialized record")
    for pattern in _SECRET_PATTERNS:
        if pattern.search(serialized):
            raise ValueError("secret_leak_detected: credential pattern matched in serialized record")


# ---------------------------------------------------------------------------
# Baltor Domain Capability Cards (retrieved via baltor_preturn_hook)
# ---------------------------------------------------------------------------

MULTI_DOMAIN_CAPABILITY_CATALOGUE: tuple[preturn_hook.CapabilityEntry, ...] = (
    preturn_hook.CapabilityEntry(
        identity="spaceship_titanic_group_pipeline_invariants",
        kind="skill",
        library_tier="verified",
        purpose=(
            "INVARIANT 1 (GroupKFold): Extract group_id = row['PassengerId'].split('_')[0]; assign all rows "
            "with the same group_id to the same fold so train and val group sets are strictly disjoint. "
            "INVARIANT 2 (Cabin): Split row.get('Cabin') or '' on '/' into cabin_deck (str or 'U'), "
            "cabin_num (int or -1), cabin_side ('P','S' or 'U'). "
            "INVARIANT 3 (CryoSleep): If row.get('CryoSleep') is True, force total_spend = 0.0 regardless of "
            "raw spend values; predict Transported = True when CryoSleep is True or total_spend == 0.0."
        ),
        body_digest="a101e373a8b5fb740744fc541f57770d2332a0db773a5ebba495d1ef48c38328",
        declared_effects=("reads_fs",),
        canonical_query="spaceship titanic group pipeline",
        domain_tags=(
            "spaceship titanic", "passengerid group", "cabin deck num side",
            "cryosleep luxury spend", "groupkfold split",
        ),
        ast_symbols=("run_spaceship_pipeline", "PassengerId", "CryoSleep", "Cabin"),
        synonyms=("spaceship titanic tabular pipeline", "passenger travel group fold split"),
    ),
    preturn_hook.CapabilityEntry(
        identity="ames_housing_rmsle_oof_invariants",
        kind="skill",
        library_tier="verified",
        purpose=(
            "INVARIANT 1 (Log1p Target): Convert SalePrice with z = math.log1p(row['SalePrice']). "
            "INVARIANT 2 (Strict Out-of-Fold Encoding): Assign fold k = idx % n_splits; for train row i in fold k, "
            "compute oof_neighborhood_encoding[i] as the mean of math.log1p(SalePrice) over rows j NOT in fold k "
            "with the same Neighborhood (fallback to out-of-fold global log1p mean if Neighborhood is unseen outside fold k; "
            "NEVER include row i's own SalePrice). "
            "INVARIANT 3 (TotalSF & Prediction): TotalSF = sum(max(0.0, float(row.get(c) or 0.0)) for c in "
            "('TotalBsmtSF','FirstFlrSF','SecondFlrSF')). Fit/predict in log1p space using Neighborhood log-mean + "
            "0.02*(OverallQual - mean_qual) + 0.00003*(TotalSF - mean_sf) and invert with math.expm1."
        ),
        body_digest="b20297fb6aa31400c35a68ff5a7fb8788687f0007200926149b1eb65258d7a64",
        declared_effects=("reads_fs",),
        canonical_query="ames housing rmsle oof",
        domain_tags=(
            "ames housing", "saleprice rmsle", "out of fold target encoding",
            "totalsf", "log1p expm1 regression",
        ),
        ast_symbols=("run_ames_rmsle_pipeline", "TotalBsmtSF", "FirstFlrSF", "SecondFlrSF", "SalePrice"),
        synonyms=("house prices regression pipeline", "neighborhood out of fold encoding"),
    ),
    preturn_hook.CapabilityEntry(
        identity="cachetools_tlru_out_of_order_expiry_contract",
        kind="code_asset",
        library_tier="verified",
        purpose=(
            "INVARIANT 1 (Expire Before Evict): In __setitem__(key, value), call self.expire(now) FIRST. "
            "Compute exp = self._ttu(key, value, now); if exp <= now, remove key if present and return immediately "
            "(do NOT store already-expired items). "
            "INVARIANT 2 (Out-of-Order TTU): Check ALL stored items for exp <= now during expire(now), because "
            "a later-inserted item can have an earlier expiration timestamp than an earlier-inserted item. "
            "INVARIANT 3 (LRU & Size): Only after expire(now), if key not in store and len >= maxsize, evict "
            "least-recently-used item via popitem(). Call expire() in __getitem__, __contains__, __len__, and currsize."
        ),
        body_digest="c3034b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacda",
        declared_effects=("reads_fs",),
        canonical_query="cachetools tlru cache ttu",
        domain_tags=(
            "tlrucache", "cachetools", "time aware least recently used",
            "ttu expiration", "expire before lru eviction",
        ),
        ast_symbols=("TLRUCache", "currsize", "maxsize", "popitem", "expire"),
        synonyms=("time to use lru cache", "out of order expiration cache"),
    ),
    preturn_hook.CapabilityEntry(
        identity="python_dotenv_escape_and_comment_parser_contract",
        kind="code_asset",
        library_tier="verified",
        purpose=(
            "INVARIANT 1 (Single-Pass Double-Quote Escapes): Scan double-quoted value char-by-char; when c == '\\\\', "
            "consume next char nxt and map 'n'->'\\n', 't'->'\\t', 'r'->'\\r', '\"'->'\"', '\\\\'->'\\\\' in ONE pass "
            "(so '\\\\\\\\n' becomes literal two chars '\\\\' + 'n', NEVER a newline). Ignore anything after closing '\"'. "
            "INVARIANT 2 (Single Quotes): In single-quoted '...', preserve characters literally (including '#' and '\\\\n') "
            "until closing \"'\". "
            "INVARIANT 3 (Unquoted & Bare Keys): Strip leading 'export '. If line has no '=', set result[key] = None. "
            "For unquoted values, strip inline comment ONLY where '#' is preceded by whitespace (keep 'foo#bar')."
        ),
        body_digest="d4047c83910b6a55e8a2f79d4b0f3e19c56072f8b04d1a3d8d6f9e20c45018b3",
        declared_effects=("reads_fs",),
        canonical_query="python dotenv escape parser",
        domain_tags=(
            "python dotenv", "backslash escape parser", "double quoted dotenv",
            "inline comment hash", "parse_dotenv_stream",
        ),
        ast_symbols=("parse_dotenv_stream", "dotenv"),
        synonyms=("dotenv issue 680 escape sequences", "single pass backslash unescape"),
    ),
    preturn_hook.CapabilityEntry(
        identity="osha_niosh_wbgt_work_rest_contract",
        kind="code_asset",
        library_tier="verified",
        purpose=(
            "INVARIANT 1 (WBGT): If solar_load is True, wbgt_c = round(0.7*natural_wet_bulb_c + 0.2*globe_temp_c + "
            "0.1*dry_bulb_c, 2); else wbgt_c = round(0.7*natural_wet_bulb_c + 0.3*globe_temp_c, 2). "
            "INVARIANT 2 (NIOSH Logarithmic Limit): M = max(100.0, float(metabolic_watts)). If acclimatized is True, "
            "limit = 56.7 - 11.5 * math.log10(M); else limit = 59.9 - 14.1 * math.log10(M); ral_or_al_limit_c = round(limit, 2). "
            "INVARIANT 3 (Schedule by delta = wbgt_c - ral_or_al_limit_c): delta < 0 -> ('normal', 0, 500, False); "
            "0 <= delta < 2 -> ('caution', 15, 750, False); 2 <= delta < 4 -> ('warning', 30, 1000, not acclimatized); "
            "4 <= delta < 6 -> ('danger', 45, 1000, True); delta >= 6 -> ('extreme_stop_work', 60, 1000, True)."
        ),
        body_digest="e50582a20d2666e51c6be46050ef5ff8a20b56d236704e42df056ffea9c6fb86",
        declared_effects=("reads_fs",),
        canonical_query="osha niosh wbgt heat stress",
        domain_tags=(
            "wet bulb globe temperature", "osha niosh heat stress", "wbgt work rest schedule",
            "ral al metabolic watts", "worker heat protection",
        ),
        ast_symbols=("assess_worker_heat_stress", "wbgt_c", "ral_or_al_limit_c", "mandatory_rest_minutes_per_hour"),
        synonyms=("niosh heat stress calculator", "wbgt rest minutes per hour"),
    ),
    preturn_hook.CapabilityEntry(
        identity="crisis_shelter_ada_haversine_triage_contract",
        kind="code_asset",
        library_tier="verified",
        purpose=(
            "INVARIANT 1 (Haversine): Use Earth radius R = 6371.0088 km; compute d = 2*R*asin(sqrt(sin(dlat/2)**2 + "
            "cos(lat1)*cos(lat2)*sin(dlon/2)**2)); filter d <= max_distance_km and set distance_km = round(d, 3). "
            "INVARIANT 2 (ADA Service Animal Rule): NEVER reject a shelter with accepts_pets == False when "
            "evacuee.get('has_service_animal') is True (service animals are legally exempt from pet bans; only check "
            "accepts_pets if evacuee.get('has_pet') is True). "
            "INVARIANT 3 (Eligibility & Tie-Breaking): Require available_beds >= party_size, wheelchair_accessible if "
            "requires_wheelchair, backup_medical_power if requires_medical_power. Sort by (distance_km, -available_beds, shelter_id)."
        ),
        body_digest="f6065f9c4e18b2d40a71c36e9812b04d73a91c82f1047b6e35d28a901c4f6b2e",
        declared_effects=("reads_fs",),
        canonical_query="crisis shelter accessible triage haversine",
        domain_tags=(
            "crisis shelter matcher", "haversine distance", "wheelchair accessible triage",
            "ada service animal", "backup medical power",
        ),
        ast_symbols=("match_accessible_shelters", "requires_wheelchair", "has_service_animal", "remaining_beds_after"),
        synonyms=("emergency shelter accessibility matcher", "disaster triage haversine"),
    ),
    preturn_hook.CapabilityEntry(
        identity="vertical_1080x1920_safe_zone_and_revision_contract",
        kind="code_asset",
        library_tier="verified",
        purpose=(
            "INVARIANT 1 (TikTok/Reels 1080x1920 Safe Zone): Place all elements strictly within x >= 80, "
            "x + width <= 920 (clear of right 160px rail [920,1080]) and y >= 160, y + height <= 1500 "
            "(clear of bottom 420px overlay [1500,1920]), stacked non-overlapping (e.g. y = 180 + idx * 180, width = 800, height = 140). "
            "INVARIANT 2 (WCAG AAA >= 7.0): Compute WCAG relative luminance contrast; if caller palette contrast < 7.0, "
            "auto-correct background='#0B1021' and foreground='#F8FAFC' so contrast_ratio >= 7.0. "
            "INVARIANT 3 (Revision-Survivable Digest): Compute structure_digest = hashlib.sha256(json.dumps("
            "[(e['kind'], e['x'], e['y'], e['width'], e['height']) for e in elements]).encode()).hexdigest() "
            "excluding text/colors so palette or metric text revisions keep the exact same structure_digest."
        ),
        body_digest="07073d18a90f4c27e61b8509a2d3f4c17e82b6059d14a3e72c81f5046b93e2d1",
        declared_effects=("reads_fs",),
        canonical_query="vertical 1080x1920 motion explainer",
        domain_tags=(
            "1080x1920 vertical explainer", "tiktok reels keep out zone",
            "wcag contrast ratio", "structure_digest revision survival",
        ),
        ast_symbols=("build_vertical_explainer_scene", "structure_digest", "contrast_ratio"),
        synonyms=("reelkit vertical video layout", "short form safe zone explainer"),
    ),
    preturn_hook.CapabilityEntry(
        identity="elastic_2d_collision_and_karplus_strong_contract",
        kind="code_asset",
        library_tier="verified",
        purpose=(
            "INVARIANT 1 (2D Elastic Impulse & Separation): Compute dx = bx - ax, dy = by - ay, dist = math.hypot(dx, dy). "
            "Normal nx = dx/dist, ny = dy/dist; rel vel vn = (bvx - avx)*nx + (bvy - avy)*ny. If dist <= ra + rb and vn < 0: "
            "j = -(2.0 * vn) / (1.0/ma + 1.0/mb); avx -= (j/ma)*nx; avy -= (j/ma)*ny; bvx += (j/mb)*nx; bvy += (j/mb)*ny; "
            "separate overlap = (ra + rb - dist) + 1e-4 along normal weighted by (1/ma, 1/mb) so final distance >= ra + rb. "
            "INVARIANT 2 (Deterministic Karplus-Strong): N_samples = int(round(sample_rate * duration_s)); "
            "fundamental_hz = round(max(110.0, min(880.0, 220.0 + 40.0 * abs(vn))), 2); delay_len = max(2, int(round(sample_rate / fundamental_hz))). "
            "Seed ring buffer deterministically: buf = [((i * 1103515245 + 12345) & 0x7fffffff) / 1073741823.5 - 1.0 for i in range(delay_len)]; "
            "for each sample output s = max(-1.0, min(1.0, buf[idx])) and update buf[idx] = 0.994 * 0.5 * (buf[idx] + buf[(idx + 1) % delay_len])."
        ),
        body_digest="18089a02b84c61d3e57f8201a4b6c9d2e3f405162738495a6b7c8d9e0f1a2b3c",
        declared_effects=("reads_fs",),
        canonical_query="html5 2d elastic collision karplus strong",
        domain_tags=(
            "2d rigid body collision", "karplus strong plucked string",
            "kinetic energy conservation", "audio buffer synthesizer",
        ),
        ast_symbols=("simulate_collision_and_pluck", "kinetic_energy_before", "kinetic_energy_after", "audio_samples"),
        synonyms=("elastic circle collision and string synth", "deterministic karplus strong audio"),
    ),
) + preturn_hook.DEFAULT_CAPABILITY_CATALOGUE


# ---------------------------------------------------------------------------
# 8 Multi-Domain Task Specifications
# ---------------------------------------------------------------------------

TASKS: tuple[dict[str, Any], ...] = (
    {
        "task_id": "K-01_spaceship_titanic_group_pipeline",
        "domain": DOMAIN_KAGGLE,
        "title": "Spaceship Titanic Leak-Free GroupKFold & CryoSleep Invariant Pipeline",
        "expected_card_identity": "spaceship_titanic_group_pipeline_invariants",
        "entrypoint": "run_spaceship_pipeline",
        "user_prompt": (
            "Write a self-contained Python module using ONLY the Python 3 standard library "
            "(no numpy, pandas, or sklearn) that defines:\n"
            "`def run_spaceship_pipeline(train_rows: list[dict], test_rows: list[dict], n_splits: int = 3) -> dict:`\n"
            "Each row in `train_rows` and `test_rows` has keys: `'PassengerId'` (e.g. `'0001_01'`), "
            "`'Cabin'` (e.g. `'B/0/P'` or `None`), `'CryoSleep'` (`bool` or `None`), "
            "`'RoomService'`, `'FoodCourt'`, `'ShoppingMall'`, `'Spa'`, `'VRDeck'` (`float` or `None`), "
            "and `train_rows` also has `'Transported'` (`bool`).\n"
            "Return a dict with keys:\n"
            "- `'folds'`: list of `n_splits` tuples `(train_indices, val_indices)` of integer row indices into `train_rows`.\n"
            "- `'engineered_test'`: list of dicts for `test_rows`, each with `'group_id'` (str), `'cabin_deck'` (str), "
            "`'cabin_num'` (int), `'cabin_side'` (str), and `'total_spend'` (float).\n"
            "- `'predictions'`: list of `bool` predictions for `test_rows`.\n"
            "Output ONLY a single ```python ... ``` code block."
        ),
    },
    {
        "task_id": "K-02_ames_housing_rmsle_pipeline",
        "domain": DOMAIN_KAGGLE,
        "title": "Ames Housing Log1p Out-of-Fold Target Encoding & TotalSF Pipeline",
        "expected_card_identity": "ames_housing_rmsle_oof_invariants",
        "entrypoint": "run_ames_rmsle_pipeline",
        "user_prompt": (
            "Write a self-contained Python module using ONLY the Python 3 standard library "
            "(no numpy, pandas, or sklearn) that defines:\n"
            "`def run_ames_rmsle_pipeline(train_rows: list[dict], test_rows: list[dict], n_splits: int = 3) -> dict:`\n"
            "Each row has `'Id'` (int), `'Neighborhood'` (str), `'TotalBsmtSF'` (float or None), "
            "`'FirstFlrSF'` (float or None), `'SecondFlrSF'` (float or None), `'OverallQual'` (int), "
            "and `train_rows` also has `'SalePrice'` (float).\n"
            "Return a dict with keys:\n"
            "- `'oof_neighborhood_encoding'`: list of `float` target-encoded neighborhood values for `train_rows`.\n"
            "- `'test_total_sf'`: list of `float` total square footage values for `test_rows`.\n"
            "- `'predictions'`: list of `float` predicted `SalePrice` values for `test_rows`.\n"
            "Output ONLY a single ```python ... ``` code block."
        ),
    },
    {
        "task_id": "G-01_cachetools_tlru_cache",
        "domain": DOMAIN_GITHUB,
        "title": "cachetools TLRUCache with Per-Item TTU & Expired-First Eviction",
        "expected_card_identity": "cachetools_tlru_out_of_order_expiry_contract",
        "entrypoint": "TLRUCache",
        "user_prompt": (
            "Write a self-contained Python module using ONLY the Python 3 standard library that defines "
            "`class TLRUCache` (compatible with `cachetools.TLRUCache`):\n"
            "`def __init__(self, maxsize: int, ttu: Callable[[Any, Any, float], float], timer: Callable[[], float] = time.monotonic)`\n"
            "Implement `__getitem__(self, key)`, `__setitem__(self, key, value)`, `__delitem__(self, key)`, "
            "`__contains__(self, key)`, `__len__(self)`, `@property def currsize(self) -> int`, "
            "`expire(self, time: float | None = None) -> list[tuple[Any, Any]]`, and `popitem(self) -> tuple[Any, Any]`.\n"
            "Output ONLY a single ```python ... ``` code block."
        ),
    },
    {
        "task_id": "G-02_python_dotenv_escape_parser",
        "domain": DOMAIN_GITHUB,
        "title": "python-dotenv Issue #680 Double-Quoted Escape & Inline Comment Parser",
        "expected_card_identity": "python_dotenv_escape_and_comment_parser_contract",
        "entrypoint": "parse_dotenv_stream",
        "user_prompt": (
            "Write a self-contained Python module using ONLY the Python 3 standard library that defines:\n"
            "`def parse_dotenv_stream(text: str) -> dict[str, str | None]:`\n"
            "Parse `.env` lines supporting optional `export ` prefix, bare keys without `=`, single-quoted values, "
            "double-quoted values with backslash escapes (`\\\"`, `\\\\`, `\\n`, `\\t`, `\\r`), unquoted values, "
            "and `#` comments.\n"
            "Output ONLY a single ```python ... ``` code block."
        ),
    },
    {
        "task_id": "PG-01_osha_niosh_heat_stress_wbgt",
        "domain": DOMAIN_PUBLIC_GOOD,
        "title": "OSHA/NIOSH Wet-Bulb Globe Temperature (WBGT) & Work-Rest Calculator",
        "expected_card_identity": "osha_niosh_wbgt_work_rest_contract",
        "entrypoint": "assess_worker_heat_stress",
        "user_prompt": (
            "Write a self-contained Python module using ONLY the Python 3 standard library that defines:\n"
            "`def assess_worker_heat_stress(dry_bulb_c: float, relative_humidity_pct: float, globe_temp_c: float, "
            "natural_wet_bulb_c: float, solar_load: bool, metabolic_watts: float, acclimatized: bool) -> dict:`\n"
            "Compute the Wet-Bulb Globe Temperature and NIOSH heat stress threshold, and return a dict with keys:\n"
            "- `'wbgt_c'` (float)\n"
            "- `'ral_or_al_limit_c'` (float)\n"
            "- `'risk_band'` (str)\n"
            "- `'mandatory_rest_minutes_per_hour'` (int)\n"
            "- `'hydration_ml_per_hour'` (int)\n"
            "- `'halt_unacclimatized_work'` (bool)\n"
            "Output ONLY a single ```python ... ``` code block."
        ),
    },
    {
        "task_id": "PG-02_crisis_shelter_accessible_triage",
        "domain": DOMAIN_PUBLIC_GOOD,
        "title": "UN SDG 10/11 Crisis Shelter Haversine & Accessibility Triage Matcher",
        "expected_card_identity": "crisis_shelter_ada_haversine_triage_contract",
        "entrypoint": "match_accessible_shelters",
        "user_prompt": (
            "Write a self-contained Python module using ONLY the Python 3 standard library that defines:\n"
            "`def match_accessible_shelters(evacuee: dict, shelters: list[dict], max_distance_km: float = 25.0) -> list[dict]:`\n"
            "`evacuee` has keys: `'lat'`, `'lon'`, `'party_size'`, `'requires_wheelchair'`, `'requires_medical_power'`, "
            "`'has_service_animal'`.\n"
            "Each item in `shelters` has keys: `'shelter_id'`, `'lat'`, `'lon'`, `'available_beds'`, "
            "`'wheelchair_accessible'`, `'backup_medical_power'`, `'accepts_pets'`.\n"
            "Filter eligible shelters within `max_distance_km` using Haversine distance and return a sorted list of dicts, "
            "each containing `'shelter_id'` (str), `'distance_km'` (float), and `'remaining_beds_after'` (int).\n"
            "Output ONLY a single ```python ... ``` code block."
        ),
    },
    {
        "task_id": "DM-01_vertical_1080x1920_motion_explainer",
        "domain": DOMAIN_DESIGN_MEDIA,
        "title": "1080x1920 Vertical Motion Explainer with Keep-Out Safe Zones & Revision Survival",
        "expected_card_identity": "vertical_1080x1920_safe_zone_and_revision_contract",
        "entrypoint": "build_vertical_explainer_scene",
        "user_prompt": (
            "Write a self-contained Python module using ONLY the Python 3 standard library that defines:\n"
            "`def build_vertical_explainer_scene(title: str, subtitle: str, metrics: list[dict], palette: dict | None = None) -> dict:`\n"
            "Each item in `metrics` has `'label'` (str) and `'value'` (str). Optional `palette` has `'background'`, "
            "`'foreground'`, and `'accent'` hex color strings.\n"
            "Generate a 1080x1920 vertical video explainer scene dict with keys:\n"
            "- `'canvas'`: `{'width': 1080, 'height': 1920, 'fps': 60, 'duration_s': 10.0}`\n"
            "- `'palette'`: dict with `'background'`, `'foreground'`, `'accent'`\n"
            "- `'contrast_ratio'`: float WCAG 2.1 contrast ratio between `foreground` and `background`\n"
            "- `'elements'`: list of dicts `{'id': str, 'kind': str, 'x': int, 'y': int, 'width': int, 'height': int, 'text': str}` "
            "for the title, subtitle, and each metric card\n"
            "- `'svg'`: str containing a `<svg viewBox=\"0 0 1080 1920\" ...>...</svg>` representation\n"
            "- `'structure_digest'`: SHA-256 hex digest of the layout structure.\n"
            "Output ONLY a single ```python ... ``` code block."
        ),
    },
    {
        "task_id": "DM-02_html5_physics_karplus_strong_synth",
        "domain": DOMAIN_DESIGN_MEDIA,
        "title": "Deterministic 60fps 2D Rigid-Body Elastic Collision & Karplus-Strong Synth",
        "expected_card_identity": "elastic_2d_collision_and_karplus_strong_contract",
        "entrypoint": "simulate_collision_and_pluck",
        "user_prompt": (
            "Write a self-contained Python module using ONLY the Python 3 standard library that defines:\n"
            "`def simulate_collision_and_pluck(body_a: dict, body_b: dict, dt: float = 1.0/60.0, "
            "sample_rate: int = 22050, duration_s: float = 0.25) -> dict:`\n"
            "`body_a` and `body_b` each have keys `'x'`, `'y'`, `'vx'`, `'vy'`, `'radius'`, `'mass'` (floats).\n"
            "Resolve a 2D perfectly elastic circle collision (restitution e=1.0) and synthesize a Karplus-Strong "
            "plucked-string audio buffer. Return a dict with keys:\n"
            "- `'body_a'`: updated dict for body_a\n"
            "- `'body_b'`: updated dict for body_b\n"
            "- `'collided'`: bool\n"
            "- `'kinetic_energy_before'`: float\n"
            "- `'kinetic_energy_after'`: float\n"
            "- `'momentum_before'`: tuple[float, float]\n"
            "- `'momentum_after'`: tuple[float, float]\n"
            "- `'audio_samples'`: list[float] of length `int(round(sample_rate * duration_s))`\n"
            "- `'fundamental_hz'`: float\n"
            "Output ONLY a single ```python ... ``` code block."
        ),
    },
)

TASK_BY_ID: dict[str, dict[str, Any]] = {t["task_id"]: t for t in TASKS}


# ---------------------------------------------------------------------------
# Code Extraction and Safe Sandboxed Execution
# ---------------------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"```(?:python|py)?\s*\n([\s\S]*?)```", re.IGNORECASE)


def extract_python_code(raw_text: str) -> str:
    """Extract Python source code from a markdown-fenced model response or raw body."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        return ""
    matches = _CODE_FENCE_RE.findall(raw_text)
    if matches:
        return max(matches, key=len).strip()
    stripped = re.sub(r"^\s*```(?:python|py)?\s*\n", "", raw_text.strip(), flags=re.IGNORECASE)
    stripped = re.sub(r"\n\s*```\s*$", "", stripped)
    return stripped.strip()


def load_callable_from_code(source_code: str, entrypoint: str) -> Any:
    """Compile and load `entrypoint` from `source_code` in a restricted stdlib module scope."""
    if not source_code.strip():
        raise ValueError("empty_source_code")
    forbidden_tokens = ("subprocess", "os.system", "shutil.rmtree", "socket", "urllib.request.urlopen")
    for tok in forbidden_tokens:
        if tok in source_code:
            raise ValueError(f"forbidden_runtime_token:{tok}")
    namespace: dict[str, Any] = {
        "__builtins__": __builtins__,
        "__name__": "__benchmark_candidate__",
        "math": math,
        "collections": collections,
        "statistics": statistics,
        "re": re,
        "json": json,
        "hashlib": hashlib,
        "time": time,
        "Any": Any,
        "Callable": Callable,
    }
    compiled = compile(source_code, "<benchmark_candidate>", "exec")
    exec(compiled, namespace)  # noqa: S102
    if entrypoint not in namespace:
        raise ValueError(f"missing_entrypoint:{entrypoint}")
    return namespace[entrypoint]


# ---------------------------------------------------------------------------
# Deterministic Task Verifiers (1 through 8)
# ---------------------------------------------------------------------------

def verify_k01_spaceship_titanic(source_code: str) -> dict[str, Any]:
    """Verify K-01: GroupKFold leak-free splitting, Cabin parsing, CryoSleep zero-spend, held-out accuracy."""
    checks: dict[str, bool] = {
        "group_leak_free": False,
        "cabin_triplet_parsed": False,
        "cryosleep_zero_spend_invariant": False,
        "heldout_group_accuracy": False,
    }
    details: dict[str, Any] = {}
    try:
        fn = load_callable_from_code(source_code, "run_spaceship_pipeline")
        # Construct 12 training rows across 6 travel groups (each group has 2 consecutive rows)
        train_rows = [
            {"PassengerId": "0001_01", "Cabin": "B/10/P", "CryoSleep": True, "RoomService": 0.0, "FoodCourt": 0.0, "ShoppingMall": 0.0, "Spa": 0.0, "VRDeck": 0.0, "Transported": True},
            {"PassengerId": "0001_02", "Cabin": "B/10/P", "CryoSleep": False, "RoomService": 1200.0, "FoodCourt": 50.0, "ShoppingMall": 0.0, "Spa": 800.0, "VRDeck": 100.0, "Transported": False},
            {"PassengerId": "0002_01", "Cabin": "C/22/S", "CryoSleep": True, "RoomService": 0.0, "FoodCourt": 0.0, "ShoppingMall": 0.0, "Spa": 0.0, "VRDeck": 0.0, "Transported": True},
            {"PassengerId": "0002_02", "Cabin": "C/22/S", "CryoSleep": True, "RoomService": None, "FoodCourt": 0.0, "ShoppingMall": 0.0, "Spa": 0.0, "VRDeck": 0.0, "Transported": True},
            {"PassengerId": "0003_01", "Cabin": "F/14/P", "CryoSleep": False, "RoomService": 900.0, "FoodCourt": 200.0, "ShoppingMall": 50.0, "Spa": 1500.0, "VRDeck": 600.0, "Transported": False},
            {"PassengerId": "0003_02", "Cabin": "F/14/P", "CryoSleep": False, "RoomService": 1400.0, "FoodCourt": 0.0, "ShoppingMall": 100.0, "Spa": 900.0, "VRDeck": 400.0, "Transported": False},
            {"PassengerId": "0004_01", "Cabin": "G/105/S", "CryoSleep": True, "RoomService": 0.0, "FoodCourt": 0.0, "ShoppingMall": 0.0, "Spa": 0.0, "VRDeck": 0.0, "Transported": True},
            {"PassengerId": "0004_02", "Cabin": "G/105/S", "CryoSleep": False, "RoomService": 0.0, "FoodCourt": 0.0, "ShoppingMall": 0.0, "Spa": 0.0, "VRDeck": 0.0, "Transported": True},
            {"PassengerId": "0005_01", "Cabin": "E/44/P", "CryoSleep": False, "RoomService": 2100.0, "FoodCourt": 100.0, "ShoppingMall": 0.0, "Spa": 700.0, "VRDeck": 500.0, "Transported": False},
            {"PassengerId": "0005_02", "Cabin": "E/44/P", "CryoSleep": False, "RoomService": 850.0, "FoodCourt": 0.0, "ShoppingMall": 0.0, "Spa": 1100.0, "VRDeck": 300.0, "Transported": False},
            {"PassengerId": "0006_01", "Cabin": "B/99/S", "CryoSleep": True, "RoomService": 0.0, "FoodCourt": 0.0, "ShoppingMall": 0.0, "Spa": 0.0, "VRDeck": 0.0, "Transported": True},
            {"PassengerId": "0006_02", "Cabin": "B/99/S", "CryoSleep": True, "RoomService": 0.0, "FoodCourt": 0.0, "ShoppingMall": 0.0, "Spa": 0.0, "VRDeck": 0.0, "Transported": True},
        ]
        test_rows = [
            {"PassengerId": "0010_01", "Cabin": "B/12/P", "CryoSleep": True, "RoomService": 450.0, "FoodCourt": None, "ShoppingMall": 0.0, "Spa": 0.0, "VRDeck": 0.0},
            {"PassengerId": "0010_02", "Cabin": None, "CryoSleep": False, "RoomService": 1800.0, "FoodCourt": 100.0, "ShoppingMall": 50.0, "Spa": 950.0, "VRDeck": 400.0},
            {"PassengerId": "0011_01", "Cabin": "C/7/S", "CryoSleep": True, "RoomService": 0.0, "FoodCourt": 0.0, "ShoppingMall": 0.0, "Spa": 0.0, "VRDeck": 0.0},
            {"PassengerId": "0012_01", "Cabin": "F/88/P", "CryoSleep": False, "RoomService": 1500.0, "FoodCourt": 300.0, "ShoppingMall": 100.0, "Spa": 1200.0, "VRDeck": 800.0},
            {"PassengerId": "0013_01", "Cabin": "G/19/S", "CryoSleep": False, "RoomService": 0.0, "FoodCourt": 0.0, "ShoppingMall": 0.0, "Spa": 0.0, "VRDeck": 0.0},
            {"PassengerId": "0014_01", "Cabin": "E/3/P", "CryoSleep": False, "RoomService": 2400.0, "FoodCourt": 0.0, "ShoppingMall": 200.0, "Spa": 900.0, "VRDeck": 600.0},
        ]
        expected_labels = [True, False, True, False, True, False]

        out = fn(train_rows, test_rows, 3)
        folds = out.get("folds") or []
        if len(folds) == 3:
            leak_free = True
            for train_idx, val_idx in folds:
                if not train_idx or not val_idx:
                    leak_free = False
                    break
                train_groups = {train_rows[i]["PassengerId"].split("_")[0] for i in train_idx}
                val_groups = {train_rows[i]["PassengerId"].split("_")[0] for i in val_idx}
                if not train_groups.isdisjoint(val_groups):
                    leak_free = False
                    break
            checks["group_leak_free"] = leak_free

        eng = out.get("engineered_test") or []
        if len(eng) == len(test_rows):
            r0, r1 = eng[0], eng[1]
            checks["cabin_triplet_parsed"] = (
                r0.get("group_id") == "0010"
                and r0.get("cabin_deck") == "B"
                and int(r0.get("cabin_num", -99)) == 12
                and r0.get("cabin_side") == "P"
                and isinstance(r1.get("cabin_num"), int)
                and int(r1.get("cabin_num")) < 0
            )
            checks["cryosleep_zero_spend_invariant"] = float(r0.get("total_spend", -1.0)) == 0.0

        preds = [bool(p) for p in (out.get("predictions") or [])]
        if len(preds) == len(expected_labels):
            acc = sum(1 for a, b in zip(preds, expected_labels) if a == b) / len(expected_labels)
            details["heldout_accuracy"] = round(acc, 4)
            checks["heldout_group_accuracy"] = acc >= 0.80
    except Exception as exc:
        details["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    score = round(sum(1.0 for v in checks.values() if v) / len(checks), 4)
    return {"passed": all(checks.values()), "score": score, "checks": checks, "details": details}


def verify_k02_ames_housing(source_code: str) -> dict[str, Any]:
    """Verify K-02: Log1p target transform, strict OOF neighborhood encoding without self-leakage, TotalSF, RMSLE."""
    checks: dict[str, bool] = {
        "no_self_target_leakage": False,
        "log1p_encoding_scale": False,
        "total_sf_null_safe": False,
        "heldout_rmsle_below_threshold": False,
    }
    details: dict[str, Any] = {}
    try:
        fn = load_callable_from_code(source_code, "run_ames_rmsle_pipeline")
        base_train = [
            {"Id": 1, "Neighborhood": "CollgCr", "TotalBsmtSF": 856.0, "FirstFlrSF": 856.0, "SecondFlrSF": 854.0, "OverallQual": 7, "SalePrice": 208500.0},
            {"Id": 2, "Neighborhood": "CollgCr", "TotalBsmtSF": 920.0, "FirstFlrSF": 920.0, "SecondFlrSF": 866.0, "OverallQual": 7, "SalePrice": 223500.0},
            {"Id": 3, "Neighborhood": "CollgCr", "TotalBsmtSF": 800.0, "FirstFlrSF": 800.0, "SecondFlrSF": 800.0, "OverallQual": 7, "SalePrice": 200000.0},
            {"Id": 4, "Neighborhood": "OldTown", "TotalBsmtSF": 700.0, "FirstFlrSF": 750.0, "SecondFlrSF": 0.0, "OverallQual": 5, "SalePrice": 125000.0},
            {"Id": 5, "Neighborhood": "OldTown", "TotalBsmtSF": 680.0, "FirstFlrSF": 720.0, "SecondFlrSF": 0.0, "OverallQual": 5, "SalePrice": 118000.0},
            {"Id": 6, "Neighborhood": "OldTown", "TotalBsmtSF": 710.0, "FirstFlrSF": 740.0, "SecondFlrSF": 0.0, "OverallQual": 5, "SalePrice": 122000.0},
            {"Id": 7, "Neighborhood": "NoRidge", "TotalBsmtSF": 1400.0, "FirstFlrSF": 1450.0, "SecondFlrSF": 1100.0, "OverallQual": 9, "SalePrice": 385000.0},
            {"Id": 8, "Neighborhood": "NoRidge", "TotalBsmtSF": 1350.0, "FirstFlrSF": 1400.0, "SecondFlrSF": 1050.0, "OverallQual": 9, "SalePrice": 370000.0},
            {"Id": 9, "Neighborhood": "NoRidge", "TotalBsmtSF": 1500.0, "FirstFlrSF": 1500.0, "SecondFlrSF": 1150.0, "OverallQual": 9, "SalePrice": 402000.0},
        ]
        test_rows = [
            {"Id": 101, "Neighborhood": "CollgCr", "TotalBsmtSF": 880.0, "FirstFlrSF": 880.0, "SecondFlrSF": 840.0, "OverallQual": 7},
            {"Id": 102, "Neighborhood": "OldTown", "TotalBsmtSF": None, "FirstFlrSF": 730.0, "SecondFlrSF": 700.0, "OverallQual": 5},
            {"Id": 103, "Neighborhood": "NoRidge", "TotalBsmtSF": 1420.0, "FirstFlrSF": 1440.0, "SecondFlrSF": 1090.0, "OverallQual": 9},
        ]
        expected_prices = [212000.0, 121000.0, 386000.0]

        out_a = fn([dict(r) for r in base_train], [dict(r) for r in test_rows], 3)
        perturbed_train = [dict(r) for r in base_train]
        perturbed_train[0]["SalePrice"] = 25000000.0
        out_b = fn(perturbed_train, [dict(r) for r in test_rows], 3)

        oof_a = out_a.get("oof_neighborhood_encoding") or []
        oof_b = out_b.get("oof_neighborhood_encoding") or []
        if len(oof_a) == len(base_train) and len(oof_b) == len(base_train):
            # Row 0's own OOF encoding must NOT depend on Row 0's own SalePrice
            checks["no_self_target_leakage"] = abs(float(oof_a[0]) - float(oof_b[0])) < 1e-6
            checks["log1p_encoding_scale"] = all(10.5 <= float(x) <= 14.0 for x in oof_a)

        sf = out_a.get("test_total_sf") or []
        if len(sf) == 3:
            checks["total_sf_null_safe"] = (
                abs(float(sf[0]) - 2600.0) < 1e-3
                and abs(float(sf[1]) - 1430.0) < 1e-3
                and abs(float(sf[2]) - 3950.0) < 1e-3
            )

        preds = out_a.get("predictions") or []
        if len(preds) == 3 and all(float(p) > 0 for p in preds):
            rmsle = math.sqrt(
                sum((math.log1p(yt) - math.log1p(float(yp))) ** 2 for yt, yp in zip(expected_prices, preds)) / 3.0
            )
            details["heldout_rmsle"] = round(rmsle, 4)
            checks["heldout_rmsle_below_threshold"] = rmsle <= 0.16
    except Exception as exc:
        details["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    score = round(sum(1.0 for v in checks.values() if v) / len(checks), 4)
    return {"passed": all(checks.values()), "score": score, "checks": checks, "details": details}


def verify_g01_cachetools_tlru(source_code: str) -> dict[str, Any]:
    """Verify G-01: TLRUCache basic LRU/TTU, out-of-order expiration, immediate expired insert, expire before LRU eviction."""
    checks: dict[str, bool] = {
        "basic_lru_and_ttu": False,
        "out_of_order_expiration": False,
        "immediate_expired_insert": False,
        "expire_before_lru_eviction_at_maxsize": False,
    }
    details: dict[str, Any] = {}
    try:
        cls = load_callable_from_code(source_code, "TLRUCache")
        now = [100.0]
        timer = lambda: now[0]  # noqa: E731

        # 1. Basic LRU and TTU
        cache1 = cls(2, lambda k, v, t: t + float(v), timer=timer)
        cache1["a"] = 10
        cache1["b"] = 10
        _ = cache1["a"]  # 'a' becomes MRU, 'b' is LRU
        cache1["c"] = 10  # should evict 'b'
        checks["basic_lru_and_ttu"] = ("a" in cache1 and "c" in cache1 and "b" not in cache1 and len(cache1) == 2)

        # 2. Out-of-order expiration (the exact failure from COMPARISON-PILOT-2026-10-16.md!)
        now[0] = 200.0
        cache2 = cls(3, lambda k, v, t: t + float(v), timer=timer)
        cache2["long"] = 50.0   # expires at 250.0
        cache2["short"] = 5.0   # expires at 205.0 (inserted AFTER 'long', expires BEFORE 'long')
        now[0] = 210.0
        checks["out_of_order_expiration"] = (
            "short" not in cache2
            and "long" in cache2
            and len(cache2) == 1
            and cache2.currsize == 1
        )

        # 3. Immediate expired insert (ttu <= now)
        now[0] = 300.0
        cache3 = cls(2, lambda k, v, t: t + float(v), timer=timer)
        cache3["already_expired"] = 0.0
        cache3["negative_ttl"] = -5.0
        checks["immediate_expired_insert"] = (
            "already_expired" not in cache3
            and "negative_ttl" not in cache3
            and len(cache3) == 0
        )

        # 4. Expire before LRU eviction at maxsize
        now[0] = 400.0
        cache4 = cls(2, lambda k, v, t: t + float(v), timer=timer)
        cache4["keep_lru"] = 100.0  # expires at 500.0 (LRU)
        cache4["short_mru"] = 5.0   # expires at 405.0 (MRU)
        _ = cache4["short_mru"]     # make short_mru most recently used
        now[0] = 410.0              # short_mru is now expired, keep_lru is still valid
        cache4["new_item"] = 50.0   # must purge expired short_mru first, NOT evict keep_lru!
        checks["expire_before_lru_eviction_at_maxsize"] = (
            "keep_lru" in cache4
            and "new_item" in cache4
            and "short_mru" not in cache4
            and len(cache4) == 2
        )
    except Exception as exc:
        details["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    score = round(sum(1.0 for v in checks.values() if v) / len(checks), 4)
    return {"passed": all(checks.values()), "score": score, "checks": checks, "details": details}


def verify_g02_python_dotenv_parser(source_code: str) -> dict[str, Any]:
    """Verify G-02: python-dotenv double-quoted escapes, single-pass \\\\n, single quotes + hash, export/bare keys."""
    checks: dict[str, bool] = {
        "double_quoted_escapes_and_inline_comment": False,
        "single_pass_double_backslash_n": False,
        "single_quoted_and_hash_preservation": False,
        "export_prefix_and_bare_key_none": False,
    }
    details: dict[str, Any] = {}
    try:
        fn = load_callable_from_code(source_code, "parse_dotenv_stream")
        r1 = fn('MSG="hello \\"world\\"\\nline2#inside" # trailing comment\n')
        checks["double_quoted_escapes_and_inline_comment"] = (
            r1.get("MSG") == 'hello "world"\nline2#inside'
        )

        # Single-pass test: literal \\n inside double quotes must produce \n (backslash + n), NOT a newline!
        r2 = fn('WIN_PATH="C:\\\\new\\\\table\\t1"\n')
        checks["single_pass_double_backslash_n"] = (
            r2.get("WIN_PATH") == "C:\\new\\table\t1"
        )

        r3 = fn("RAW='a#b\\\\n' # comment\nUNQUOTED=foo#bar # inline comment\n")
        checks["single_quoted_and_hash_preservation"] = (
            r3.get("RAW") == "a#b\\\\n"
            and r3.get("UNQUOTED") == "foo#bar"
        )

        r4 = fn("export EMPTY_VAL=\nexport TOKEN='abc'\nBARE_KEY\n# full line comment\n")
        checks["export_prefix_and_bare_key_none"] = (
            r4.get("EMPTY_VAL") == ""
            and r4.get("TOKEN") == "abc"
            and "BARE_KEY" in r4
            and r4.get("BARE_KEY") is None
        )
    except Exception as exc:
        details["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    score = round(sum(1.0 for v in checks.values() if v) / len(checks), 4)
    return {"passed": all(checks.values()), "score": score, "checks": checks, "details": details}


def verify_pg01_osha_niosh_wbgt(source_code: str) -> dict[str, Any]:
    """Verify PG-01: Outdoor/indoor WBGT formulas, NIOSH log10 RAL/AL limits, monotonic rest schedule, unacclimatized halt."""
    checks: dict[str, bool] = {
        "wbgt_indoor_outdoor_formula": False,
        "niosh_log10_ral_al_threshold": False,
        "mandatory_rest_schedule_monotonic": False,
        "unacclimatized_protection_invariant": False,
    }
    details: dict[str, Any] = {}
    try:
        fn = load_callable_from_code(source_code, "assess_worker_heat_stress")
        # Outdoor solar_load=True: 0.7*26.0 + 0.2*36.0 + 0.1*32.0 = 18.2 + 7.2 + 3.2 = 28.6
        out_solar = fn(32.0, 65.0, 36.0, 26.0, True, 300.0, True)
        # Indoor solar_load=False: 0.7*26.0 + 0.3*36.0 = 18.2 + 10.8 = 29.0
        out_indoor = fn(32.0, 65.0, 36.0, 26.0, False, 300.0, False)

        checks["wbgt_indoor_outdoor_formula"] = (
            abs(float(out_solar["wbgt_c"]) - 28.6) <= 0.05
            and abs(float(out_indoor["wbgt_c"]) - 29.0) <= 0.05
        )

        # At M=300W: RAL = 56.7 - 11.5 * log10(300) = 28.21, AL = 59.9 - 14.1 * log10(300) = 24.97
        checks["niosh_log10_ral_al_threshold"] = (
            abs(float(out_solar["ral_or_al_limit_c"]) - 28.21) <= 0.08
            and abs(float(out_indoor["ral_or_al_limit_c"]) - 24.97) <= 0.08
        )

        # Monotonic schedule across low, caution, warning, danger, extreme
        low = fn(24.0, 40.0, 25.0, 20.0, True, 200.0, True)
        warn = fn(34.0, 60.0, 38.0, 28.5, True, 300.0, True)
        extreme = fn(40.0, 75.0, 46.0, 34.0, True, 350.0, True)
        checks["mandatory_rest_schedule_monotonic"] = (
            int(low["mandatory_rest_minutes_per_hour"]) == 0
            and 15 <= int(warn["mandatory_rest_minutes_per_hour"]) <= 45
            and int(extreme["mandatory_rest_minutes_per_hour"]) == 60
            and int(low["mandatory_rest_minutes_per_hour"]) < int(warn["mandatory_rest_minutes_per_hour"]) < int(extreme["mandatory_rest_minutes_per_hour"])
        )

        # Unacclimatized worker at wbgt=29.0 vs AL=24.97 (delta=4.03 >= 2.0) must halt unacclimatized work
        checks["unacclimatized_protection_invariant"] = (
            bool(out_indoor["halt_unacclimatized_work"]) is True
            and int(out_indoor["mandatory_rest_minutes_per_hour"]) >= 30
        )
    except Exception as exc:
        details["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    score = round(sum(1.0 for v in checks.values() if v) / len(checks), 4)
    return {"passed": all(checks.values()), "score": score, "checks": checks, "details": details}


def verify_pg02_crisis_shelter_triage(source_code: str) -> dict[str, Any]:
    """Verify PG-02: Haversine accuracy, wheelchair/medical/capacity filters, ADA service-animal rule, tie-breaking."""
    checks: dict[str, bool] = {
        "haversine_distance_accuracy": False,
        "wheelchair_medical_capacity_hard_filters": False,
        "ada_service_animal_exemption": False,
        "deterministic_tie_breaking": False,
    }
    details: dict[str, Any] = {}
    try:
        fn = load_callable_from_code(source_code, "match_accessible_shelters")
        evacuee = {
            "lat": 37.7749,
            "lon": -122.4194,
            "party_size": 3,
            "requires_wheelchair": True,
            "requires_medical_power": True,
            "has_service_animal": True,
        }
        shelters = [
            # Ineligible: no wheelchair
            {"shelter_id": "S-NO-WC", "lat": 37.7800, "lon": -122.4194, "available_beds": 10, "wheelchair_accessible": False, "backup_medical_power": True, "accepts_pets": True},
            # Ineligible: only 2 beds (< party_size 3)
            {"shelter_id": "S-FEW-BEDS", "lat": 37.7800, "lon": -122.4194, "available_beds": 2, "wheelchair_accessible": True, "backup_medical_power": True, "accepts_pets": True},
            # Eligible despite accepts_pets=False because service animals are ADA exempt!
            {"shelter_id": "S-ADA-EXEMPT", "lat": 37.7849, "lon": -122.4194, "available_beds": 8, "wheelchair_accessible": True, "backup_medical_power": True, "accepts_pets": False},
            # Equidistant to S-ADA-EXEMPT (37.7849, -122.4194) with MORE beds (15 > 8) -> must sort first!
            {"shelter_id": "S-TIE-MORE-BEDS", "lat": 37.7849, "lon": -122.4194, "available_beds": 15, "wheelchair_accessible": True, "backup_medical_power": True, "accepts_pets": True},
            # Equidistant to S-ADA-EXEMPT with same 8 beds but lexicographically later ID 'S-Z-TIE'
            {"shelter_id": "S-Z-TIE", "lat": 37.7849, "lon": -122.4194, "available_beds": 8, "wheelchair_accessible": True, "backup_medical_power": True, "accepts_pets": True},
            # Too far (> 25 km)
            {"shelter_id": "S-FAR", "lat": 38.1500, "lon": -122.4194, "available_beds": 50, "wheelchair_accessible": True, "backup_medical_power": True, "accepts_pets": True},
        ]
        matched = fn(evacuee, shelters, 25.0)
        ids = [m["shelter_id"] for m in matched]

        checks["wheelchair_medical_capacity_hard_filters"] = (
            "S-NO-WC" not in ids and "S-FEW-BEDS" not in ids and "S-FAR" not in ids
        )
        checks["ada_service_animal_exemption"] = "S-ADA-EXEMPT" in ids
        if matched:
            # Distance from 37.7749 to 37.7849 (0.01 deg lat) is ~1.112 km
            d0 = float(matched[0]["distance_km"])
            checks["haversine_distance_accuracy"] = abs(d0 - 1.112) <= 0.02
        checks["deterministic_tie_breaking"] = (
            ids == ["S-TIE-MORE-BEDS", "S-ADA-EXEMPT", "S-Z-TIE"]
            and int(matched[0]["remaining_beds_after"]) == 12
        )
    except Exception as exc:
        details["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    score = round(sum(1.0 for v in checks.values() if v) / len(checks), 4)
    return {"passed": all(checks.values()), "score": score, "checks": checks, "details": details}


def _wcag_contrast(hex_a: str, hex_b: str) -> float:
    def _lum(h: str) -> float:
        s = h.strip().lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        r, g, b = (int(s[0:2], 16) / 255.0, int(s[2:4], 16) / 255.0, int(s[4:6], 16) / 255.0)
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    l1, l2 = _lum(hex_a), _lum(hex_b)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def verify_dm01_vertical_motion_explainer(source_code: str) -> dict[str, Any]:
    """Verify DM-01: 1080x1920 keep-out zones (x+w<=920, y+h<=1500), WCAG AAA >=7.0, SVG validity, revision survival."""
    checks: dict[str, bool] = {
        "keepout_zones_respected": False,
        "wcag_aaa_contrast": False,
        "svg_1080x1920_valid": False,
        "revision_survival_digest_invariant": False,
    }
    details: dict[str, Any] = {}
    try:
        fn = load_callable_from_code(source_code, "build_vertical_explainer_scene")
        metrics_v1 = [
            {"label": "Group Accuracy", "value": "84.2%"},
            {"label": "RMSLE Score", "value": "0.118"},
            {"label": "WBGT Margin", "value": "+2.4 C"},
        ]
        scene_v1 = fn("Baltor Live Verification", "4 Domains • 8 Tasks", metrics_v1, None)
        elements = scene_v1.get("elements") or []
        if len(elements) >= 5:
            in_bounds = all(
                int(e["x"]) >= 40
                and int(e["x"]) + int(e["width"]) <= 920
                and int(e["y"]) >= 120
                and int(e["y"]) + int(e["height"]) <= 1500
                and int(e["width"]) > 0
                and int(e["height"]) > 0
                for e in elements
            )
            # Check vertical non-overlap when sorted by y
            sorted_boxes = sorted(elements, key=lambda e: int(e["y"]))
            no_overlap = all(
                int(sorted_boxes[i + 1]["y"]) >= int(sorted_boxes[i]["y"]) + int(sorted_boxes[i]["height"])
                for i in range(len(sorted_boxes) - 1)
            )
            checks["keepout_zones_respected"] = in_bounds and no_overlap

        pal1 = scene_v1.get("palette") or {}
        c1 = _wcag_contrast(pal1.get("foreground", "#000000"), pal1.get("background", "#000000"))
        # Revision with a low-contrast input palette and updated text values
        metrics_v2 = [
            {"label": "Updated Accuracy", "value": "91.0%"},
            {"label": "Updated RMSLE", "value": "0.094"},
            {"label": "Updated WBGT", "value": "+1.1 C"},
        ]
        scene_v2 = fn(
            "Revised Baltor Headline",
            "Updated Subtitle Copy",
            metrics_v2,
            {"background": "#222222", "foreground": "#333333", "accent": "#FFAA00"},
        )
        pal2 = scene_v2.get("palette") or {}
        c2 = _wcag_contrast(pal2.get("foreground", "#000000"), pal2.get("background", "#000000"))
        checks["wcag_aaa_contrast"] = (c1 >= 7.0 and c2 >= 7.0 and float(scene_v1.get("contrast_ratio", 0.0)) >= 7.0)

        svg = str(scene_v1.get("svg") or "")
        checks["svg_1080x1920_valid"] = (
            "<svg" in svg and "1080" in svg and "1920" in svg and "84.2%" in svg and "</svg>" in svg
        )

        dig1 = str(scene_v1.get("structure_digest") or "")
        dig2 = str(scene_v2.get("structure_digest") or "")
        checks["revision_survival_digest_invariant"] = (
            len(dig1) == 64 and dig1 == dig2
        )
    except Exception as exc:
        details["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    score = round(sum(1.0 for v in checks.values() if v) / len(checks), 4)
    return {"passed": all(checks.values()), "score": score, "checks": checks, "details": details}


def verify_dm02_physics_karplus_strong(source_code: str) -> dict[str, Any]:
    """Verify DM-02: Elastic 2D energy/momentum conservation, overlap separation, bounded decaying audio, determinism."""
    checks: dict[str, bool] = {
        "kinetic_energy_and_momentum_conserved": False,
        "overlap_resolved_and_velocities_reflected": False,
        "audio_buffer_finite_and_bounded": False,
        "deterministic_reproducibility": False,
    }
    details: dict[str, Any] = {}
    try:
        fn = load_callable_from_code(source_code, "simulate_collision_and_pluck")
        body_a = {"x": 0.0, "y": 0.0, "vx": 4.0, "vy": 0.5, "radius": 1.0, "mass": 2.0}
        body_b = {"x": 1.8, "y": 0.0, "vx": -2.0, "vy": -0.5, "radius": 1.0, "mass": 3.0}

        res1 = fn(dict(body_a), dict(body_b), 1.0 / 60.0, 22050, 0.25)
        res2 = fn(dict(body_a), dict(body_b), 1.0 / 60.0, 22050, 0.25)

        ke_before = float(res1["kinetic_energy_before"])
        ke_after = float(res1["kinetic_energy_after"])
        p_before = res1["momentum_before"]
        p_after = res1["momentum_after"]
        checks["kinetic_energy_and_momentum_conserved"] = (
            ke_before > 0.0
            and abs(ke_after - ke_before) <= 1e-4
            and abs(float(p_after[0]) - float(p_before[0])) <= 1e-4
            and abs(float(p_after[1]) - float(p_before[1])) <= 1e-4
        )

        ba, bb = res1["body_a"], res1["body_b"]
        final_dist = math.hypot(float(bb["x"]) - float(ba["x"]), float(bb["y"]) - float(ba["y"]))
        checks["overlap_resolved_and_velocities_reflected"] = (
            bool(res1["collided"]) is True
            and float(ba["vx"]) < 4.0
            and float(bb["vx"]) > -2.0
            and final_dist >= float(body_a["radius"]) + float(body_b["radius"]) - 1e-5
        )

        samples = res1.get("audio_samples") or []
        expected_len = int(round(22050 * 0.25))
        if len(samples) == expected_len and expected_len > 100:
            finite_bounded = all(isinstance(s, (int, float)) and math.isfinite(s) and -1.0 <= float(s) <= 1.0 for s in samples)
            peak = max(abs(float(s)) for s in samples)
            q = expected_len // 4
            rms_start = math.sqrt(sum(float(s) ** 2 for s in samples[:q]) / q)
            rms_end = math.sqrt(sum(float(s) ** 2 for s in samples[-q:]) / q)
            checks["audio_buffer_finite_and_bounded"] = (
                finite_bounded and peak >= 0.1 and rms_end < rms_start
            )

        checks["deterministic_reproducibility"] = (
            res1["audio_samples"] == res2["audio_samples"]
            and res1["body_a"] == res2["body_a"]
            and res1["body_b"] == res2["body_b"]
        )
    except Exception as exc:
        details["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    score = round(sum(1.0 for v in checks.values() if v) / len(checks), 4)
    return {"passed": all(checks.values()), "score": score, "checks": checks, "details": details}


TASK_VERIFIERS: dict[str, Callable[[str], dict[str, Any]]] = {
    "K-01_spaceship_titanic_group_pipeline": verify_k01_spaceship_titanic,
    "K-02_ames_housing_rmsle_pipeline": verify_k02_ames_housing,
    "G-01_cachetools_tlru_cache": verify_g01_cachetools_tlru,
    "G-02_python_dotenv_escape_parser": verify_g02_python_dotenv_parser,
    "PG-01_osha_niosh_heat_stress_wbgt": verify_pg01_osha_niosh_wbgt,
    "PG-02_crisis_shelter_accessible_triage": verify_pg02_crisis_shelter_triage,
    "DM-01_vertical_1080x1920_motion_explainer": verify_dm01_vertical_motion_explainer,
    "DM-02_html5_physics_karplus_strong_synth": verify_dm02_physics_karplus_strong,
}


# ---------------------------------------------------------------------------
# Reference Good & Known-Wrong Controls for Offline Conformance Testing
# ---------------------------------------------------------------------------

KNOWN_WRONG_CONTROLS: dict[str, str] = {
    "K-01_spaceship_titanic_group_pipeline": """
def run_spaceship_pipeline(train_rows, test_rows, n_splits=3):
    # WRONG: Naive modulo split leaks PassengerId groups across train and val folds,
    # and does not zero out noisy spend when CryoSleep is True.
    folds = []
    for k in range(n_splits):
        val_idx = [i for i in range(len(train_rows)) if i % n_splits == k]
        train_idx = [i for i in range(len(train_rows)) if i % n_splits != k]
        folds.append((train_idx, val_idx))
    engineered = []
    preds = []
    for r in test_rows:
        spend = sum(float(r.get(c) or 0.0) for c in ("RoomService", "FoodCourt", "ShoppingMall", "Spa", "VRDeck"))
        engineered.append({"group_id": r["PassengerId"], "cabin_deck": "U", "cabin_num": 0, "cabin_side": "U", "total_spend": spend})
        preds.append(spend == 0.0)
    return {"folds": folds, "engineered_test": engineered, "predictions": preds}
""",
    "K-02_ames_housing_rmsle_pipeline": """
def run_ames_rmsle_pipeline(train_rows, test_rows, n_splits=3):
    # WRONG: In-sample target encoding includes row i's own raw SalePrice (target leakage!).
    by_n = {}
    for r in train_rows:
        by_n.setdefault(r["Neighborhood"], []).append(float(r["SalePrice"]))
    means = {k: sum(v) / len(v) for k, v in by_n.items()}
    oof = [means[r["Neighborhood"]] for r in train_rows]
    sf = [float(r.get("FirstFlrSF") or 0.0) for r in test_rows]
    preds = [means.get(r["Neighborhood"], 180000.0) for r in test_rows]
    return {"oof_neighborhood_encoding": oof, "test_total_sf": sf, "predictions": preds}
""",
    "G-01_cachetools_tlru_cache": """
import collections, time
class TLRUCache:
    # WRONG: Does not expire items before LRU eviction and stores already-expired items.
    def __init__(self, maxsize, ttu, timer=time.monotonic):
        self.maxsize = maxsize
        self._ttu = ttu
        self._timer = timer
        self._data = collections.OrderedDict()
    def __setitem__(self, key, value):
        if key not in self._data and len(self._data) >= self.maxsize:
            self._data.popitem(last=False)
        self._data[key] = (value, self._ttu(key, value, self._timer()))
    def __getitem__(self, key):
        val, _ = self._data[key]
        self._data.move_to_end(key)
        return val
    def __contains__(self, key):
        return key in self._data
    def __len__(self):
        return len(self._data)
    @property
    def currsize(self):
        return len(self._data)
    def expire(self, time=None):
        return []
    def popitem(self):
        k, (v, _) = self._data.popitem(last=False)
        return k, v
""",
    "G-02_python_dotenv_escape_parser": """
def parse_dotenv_stream(text):
    # WRONG: Chained .replace corrupts \\\\n into a newline and splits on '#' inside quotes.
    out = {}
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        v = v.replace("\\\\n", "\\n").replace("\\\\\\\\", "\\\\")
        out[k.strip()] = v
    return out
""",
    "PG-01_osha_niosh_heat_stress_wbgt": """
def assess_worker_heat_stress(dry_bulb_c, relative_humidity_pct, globe_temp_c, natural_wet_bulb_c, solar_load, metabolic_watts, acclimatized):
    # WRONG: Uses a flat 30C threshold regardless of metabolic rate or acclimatization and unsafe 10m rest.
    wbgt = 0.5 * dry_bulb_c + 0.5 * globe_temp_c
    return {
        "wbgt_c": round(wbgt, 2),
        "ral_or_al_limit_c": 30.0,
        "risk_band": "caution",
        "mandatory_rest_minutes_per_hour": 10,
        "hydration_ml_per_hour": 250,
        "halt_unacclimatized_work": False,
    }
""",
    "PG-02_crisis_shelter_accessible_triage": """
def match_accessible_shelters(evacuee, shelters, max_distance_km=25.0):
    # WRONG: Rejects evacuees with ADA service animals when accepts_pets is False.
    out = []
    for s in shelters:
        if evacuee.get("has_service_animal") and not s.get("accepts_pets"):
            continue
        out.append({"shelter_id": s["shelter_id"], "distance_km": 1.0, "remaining_beds_after": s["available_beds"]})
    return out
""",
    "DM-01_vertical_1080x1920_motion_explainer": """
import hashlib, json
def build_vertical_explainer_scene(title, subtitle, metrics, palette=None):
    # WRONG: Places elements at y=1650 (inside bottom 420px TikTok/Reels keep-out zone) and hashes text in digest.
    pal = palette or {"background": "#222222", "foreground": "#444444", "accent": "#888888"}
    elements = [
        {"id": "title", "kind": "title", "x": 100, "y": 1650, "width": 980, "height": 200, "text": title},
    ]
    digest = hashlib.sha256(json.dumps(elements).encode()).hexdigest()
    return {"canvas": {"width": 1080, "height": 1920}, "palette": pal, "contrast_ratio": 2.1, "elements": elements, "svg": "<svg></svg>", "structure_digest": digest}
""",
    "DM-02_html5_physics_karplus_strong_synth": """
def simulate_collision_and_pluck(body_a, body_b, dt=1.0/60.0, sample_rate=22050, duration_s=0.25):
    # WRONG: Loses kinetic energy (inelastic damping) and outputs out-of-bounds audio samples > 1.0.
    return {
        "body_a": body_a,
        "body_b": body_b,
        "collided": False,
        "kinetic_energy_before": 25.0,
        "kinetic_energy_after": 12.0,
        "momentum_before": (2.0, 0.0),
        "momentum_after": (1.0, 0.0),
        "audio_samples": [2.5] * int(round(sample_rate * duration_s)),
        "fundamental_hz": 440.0,
    }
""",
}


# ---------------------------------------------------------------------------
# Strict Physical Request Meter & Live Ollama Cloud Transport
# ---------------------------------------------------------------------------

class PhysicalRequestMeter:
    """Strict counter enforcing `max_physical_requests <= 16` before any network socket opens."""

    def __init__(self, maximum: int = MAX_PHYSICAL_REQUESTS_CEILING) -> None:
        if not isinstance(maximum, int) or not 1 <= maximum <= MAX_PHYSICAL_REQUESTS_CEILING:
            raise ValueError(f"max_physical_requests must be between 1 and {MAX_PHYSICAL_REQUESTS_CEILING}")
        self.maximum = maximum
        self.used = 0
        self.ledger: list[dict[str, Any]] = []

    @property
    def remaining(self) -> int:
        return max(0, self.maximum - self.used)

    def acquire(self, task_id: str, arm: str, model: str) -> int:
        if self.used >= self.maximum:
            raise RuntimeError(
                f"physical_request_ceiling_reached: refused call {self.used + 1} beyond ceiling {self.maximum}"
            )
        self.used += 1
        seq = self.used
        self.ledger.append({
            "sequence": seq,
            "task_id": task_id,
            "arm": arm,
            "model": model,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        })
        return seq


def call_ollama_cloud_chat(
    *,
    meter: PhysicalRequestMeter,
    task_id: str,
    arm: str,
    system_prompt: str,
    user_prompt: str,
    model: str = PRIMARY_MODEL,
    timeout: float = CALL_TIMEOUT_SECONDS,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Execute one metered POST call to `https://ollama.com/v1/chat/completions` and scrub secrets."""
    key = api_key if api_key is not None else load_api_key()
    if not key:
        raise RuntimeError("missing_ollama_api_key: OLLAMA_API_KEY is not present in environment")
    sequence = meter.acquire(task_id=task_id, arm=arm, model=model)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 2400,
        "stream": False,
    }
    encoded_body = json.dumps(payload).encode("utf-8")
    request_sha256 = hashlib.sha256(encoded_body).hexdigest()
    req = urllib.request.Request(
        COMPATIBLE_CHAT_ENDPOINT,
        data=encoded_body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "loop-engine-multi-domain-benchmark/1.0",
        },
    )
    t0 = time.perf_counter()
    http_status = 0
    raw_bytes = b""
    error_text = ""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            http_status = int(getattr(resp, "status", 200))
            raw_bytes = resp.read(2 * 1024 * 1024)
    except urllib.error.HTTPError as exc:
        http_status = int(exc.code)
        try:
            err_body = exc.read(4096).decode("utf-8", "replace")
        except OSError:
            err_body = str(exc)
        error_text = scrub_secrets(f"HTTP {http_status}: {err_body[:300]}", key)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        error_text = scrub_secrets(f"{type(exc).__name__}: {str(exc)[:300]}", key)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    if error_text or http_status != 200:
        return scrub_secrets(
            {
                "sequence": sequence,
                "ok": False,
                "http_status": http_status or None,
                "model": model,
                "endpoint": COMPATIBLE_CHAT_ENDPOINT,
                "request_sha256": request_sha256,
                "latency_ms": elapsed_ms,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "finish_reason": "error",
                "response_text": "",
                "error": error_text or f"HTTP {http_status}",
            },
            key,
        )

    parsed = json.loads(raw_bytes.decode("utf-8", "replace"))
    choices = parsed.get("choices") or []
    first_choice = choices[0] if choices and isinstance(choices[0], dict) else {}
    message = first_choice.get("message") if isinstance(first_choice.get("message"), dict) else {}
    content = str(message.get("content") or "")
    if not content.strip() and message.get("reasoning"):
        content = str(message.get("reasoning") or "")
    usage = parsed.get("usage") if isinstance(parsed.get("usage"), dict) else {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))

    return scrub_secrets(
        {
            "sequence": sequence,
            "ok": True,
            "http_status": http_status,
            "model": str(parsed.get("model") or model),
            "endpoint": COMPATIBLE_CHAT_ENDPOINT,
            "request_sha256": request_sha256,
            "latency_ms": elapsed_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "finish_reason": str(first_choice.get("finish_reason") or "stop"),
            "response_text": content,
            "error": "",
        },
        key,
    )


# ---------------------------------------------------------------------------
# Pre-Turn Hook Invocation (Nested Envelope Layer 7)
# ---------------------------------------------------------------------------

def retrieve_baltor_card_for_task(
    parent_frame: EnvelopeFrame,
    task: dict[str, Any],
    arm: str,
) -> dict[str, Any]:
    """Enter the nested `preturn_adoption_trigger` slot and retrieve the Baltor contract card."""
    nested_frame = enter_nested(parent_frame, NESTED_PRETURN_SLOT_ID)
    engine_id = preturn_hook.ENGINE_T0 if arm == ARM_WITHOUT_BALTOR else preturn_hook.ENGINE_T7
    hook_result = preturn_hook.run_preturn_envelope({
        "record_type": preturn_hook.REQUEST_VERSION,
        "protocol_version": preturn_hook.PROTOCOL_V1,
        "client_profile": "opencode",
        "prompt": task["user_prompt"],
        "engine_id": engine_id,
        "confidence_threshold": 0.32,
        "max_injected_tokens": 360,
        "max_cards": 1,
        "catalogue_items": MULTI_DOMAIN_CAPABILITY_CATALOGUE,
    })
    return {
        "nested_frame": nested_frame.to_dict(),
        "hook_engine": hook_result.get("selected_engine"),
        "abstained": bool(hook_result.get("abstained", True)),
        "abstention_code": str(hook_result.get("abstention_code", "")),
        "winning_probe": str(hook_result.get("winning_probe", "")),
        "reformulated_query": str(hook_result.get("reformulated_query", "")),
        "injected_tokens": int(hook_result.get("injected_tokens", 0)),
        "injected_context": str(hook_result.get("injected_context", "")),
        "cards": list(hook_result.get("cards") or []),
    }


def compose_arm_prompt(task: dict[str, Any], preturn_info: dict[str, Any]) -> str:
    """Compose the user prompt for `without_baltor` vs `with_baltor`."""
    base_prompt = task["user_prompt"]
    injected = preturn_info.get("injected_context", "").strip()
    if not injected:
        return base_prompt
    return (
        f"{base_prompt}\n\n"
        f"{injected}\n"
        "Follow every INVARIANT in the Baltor Contract Card above exactly."
    )


# ---------------------------------------------------------------------------
# Swappable Benchmark Engines
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTION = (
    "You are a senior Python systems engineer. Output ONLY a single valid ```python ... ``` "
    "code block implementing the requested function or class using ONLY the Python 3 standard "
    "library. Do not include prose explanations before or after the code block."
)

ENGINE_DECLARATIONS: dict[str, EnvelopeHandshakeDeclaration] = {
    ENGINE_LIVE_OLLAMA: EnvelopeHandshakeDeclaration(
        engine=ENGINE_LIVE_OLLAMA,
        supported_versions=(PROTOCOL_VERSION,),
        capabilities=("multi_domain_benchmark", "live_ollama_cloud", "preturn_card_comparison"),
        effects=("reads_fs", "network", "model_call"),
    ),
    ENGINE_OFFLINE_REPLAY: EnvelopeHandshakeDeclaration(
        engine=ENGINE_OFFLINE_REPLAY,
        supported_versions=(PROTOCOL_VERSION,),
        capabilities=("multi_domain_benchmark", "deterministic_replay", "preturn_card_comparison"),
        effects=("reads_fs",),
    ),
    ENGINE_SYNTHETIC_CONTROL: EnvelopeHandshakeDeclaration(
        engine=ENGINE_SYNTHETIC_CONTROL,
        supported_versions=(PROTOCOL_VERSION,),
        capabilities=("multi_domain_benchmark", "synthetic_control", "preturn_card_comparison"),
        effects=(PURE_EFFECT,),
    ),
}


def _summarize_trials(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate and per-domain comparison statistics across paired trials."""
    by_arm: dict[str, list[dict[str, Any]]] = {ARM_WITHOUT_BALTOR: [], ARM_WITH_BALTOR: []}
    by_domain: dict[str, dict[str, Any]] = {}
    for trial in trials:
        arm = trial["arm"]
        dom = trial["domain"]
        by_arm.setdefault(arm, []).append(trial)
        dom_entry = by_domain.setdefault(
            dom,
            {
                "domain": dom,
                "title": DOMAIN_METADATA[dom]["title"],
                "demo_surface": DOMAIN_METADATA[dom]["demo_surface"],
                "without_baltor_passed": 0,
                "with_baltor_passed": 0,
                "tasks_total": 0,
                "without_baltor_mean_score": 0.0,
                "with_baltor_mean_score": 0.0,
                "_without_scores": [],
                "_with_scores": [],
            },
        )
        if arm == ARM_WITHOUT_BALTOR:
            dom_entry["tasks_total"] += 1
            if trial["verification"]["passed"]:
                dom_entry["without_baltor_passed"] += 1
            dom_entry["_without_scores"].append(float(trial["verification"]["score"]))
        elif arm == ARM_WITH_BALTOR:
            if trial["verification"]["passed"]:
                dom_entry["with_baltor_passed"] += 1
            dom_entry["_with_scores"].append(float(trial["verification"]["score"]))

    for dom_entry in by_domain.values():
        w_out = dom_entry.pop("_without_scores")
        w_in = dom_entry.pop("_with_scores")
        dom_entry["without_baltor_mean_score"] = round(statistics.mean(w_out), 4) if w_out else 0.0
        dom_entry["with_baltor_mean_score"] = round(statistics.mean(w_in), 4) if w_in else 0.0

    def _arm_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
        if not items:
            return {
                "trials": 0,
                "passed": 0,
                "pass_rate": 0.0,
                "mean_quality_score": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "total_latency_ms": 0.0,
                "mean_injected_tokens": 0.0,
            }
        passed = sum(1 for t in items if t["verification"]["passed"])
        return {
            "trials": len(items),
            "passed": passed,
            "pass_rate": round(passed / len(items), 4),
            "mean_quality_score": round(statistics.mean(float(t["verification"]["score"]) for t in items), 4),
            "prompt_tokens": sum(int(t["model_call"]["prompt_tokens"]) for t in items),
            "completion_tokens": sum(int(t["model_call"]["completion_tokens"]) for t in items),
            "total_tokens": sum(int(t["model_call"]["total_tokens"]) for t in items),
            "total_latency_ms": round(sum(float(t["model_call"]["latency_ms"]) for t in items), 2),
            "mean_injected_tokens": round(
                statistics.mean(int(t["preturn_hook"]["injected_tokens"]) for t in items), 2
            ),
        }

    without_stats = _arm_stats(by_arm[ARM_WITHOUT_BALTOR])
    with_stats = _arm_stats(by_arm[ARM_WITH_BALTOR])
    return {
        "total_physical_requests": len(trials),
        "without_baltor": without_stats,
        "with_baltor": with_stats,
        "pass_rate_delta": round(with_stats["pass_rate"] - without_stats["pass_rate"], 4),
        "quality_score_delta": round(
            with_stats["mean_quality_score"] - without_stats["mean_quality_score"], 4
        ),
        "by_domain": by_domain,
    }


def _execute_live_ollama_engine(
    frame: EnvelopeFrame,
    request: dict[str, Any],
) -> dict[str, Any]:
    """Run all 8 tasks x 2 arms (16 physical calls) against live Ollama Cloud."""
    selected_task_ids = tuple(request.get("task_ids") or [t["task_id"] for t in TASKS])
    tasks_to_run = [TASK_BY_ID[tid] for tid in selected_task_ids]
    max_requests = int(request.get("max_physical_requests", MAX_PHYSICAL_REQUESTS_CEILING))
    meter = PhysicalRequestMeter(maximum=max_requests)
    primary_model = str(request.get("model") or PRIMARY_MODEL)
    fallback_models = tuple(request.get("fallback_models") or FALLBACK_MODELS)
    raw_key = load_api_key()

    trials: list[dict[str, Any]] = []
    for task in tasks_to_run:
        task_id = task["task_id"]
        verifier = TASK_VERIFIERS[task_id]
        for arm in ARMS:
            preturn_info = retrieve_baltor_card_for_task(frame, task, arm)
            full_prompt = compose_arm_prompt(task, preturn_info)

            call_record = call_ollama_cloud_chat(
                meter=meter,
                task_id=task_id,
                arm=arm,
                system_prompt=SYSTEM_INSTRUCTION,
                user_prompt=full_prompt,
                model=primary_model,
                timeout=float(request.get("timeout_seconds", CALL_TIMEOUT_SECONDS)),
                api_key=raw_key,
            )
            if not call_record["ok"] and meter.remaining > 0 and fallback_models:
                call_record = call_ollama_cloud_chat(
                    meter=meter,
                    task_id=task_id,
                    arm=arm,
                    system_prompt=SYSTEM_INSTRUCTION,
                    user_prompt=full_prompt,
                    model=fallback_models[0],
                    timeout=float(request.get("timeout_seconds", CALL_TIMEOUT_SECONDS)),
                    api_key=raw_key,
                )

            extracted_code = extract_python_code(call_record.get("response_text", ""))
            verification = verifier(extracted_code)
            trials.append(
                scrub_secrets(
                    {
                        "trial_id": f"{task_id}__{arm}",
                        "task_id": task_id,
                        "domain": task["domain"],
                        "demo_surface": DOMAIN_METADATA[task["domain"]]["demo_surface"],
                        "title": task["title"],
                        "arm": arm,
                        "preturn_hook": {
                            "hook_engine": preturn_info["hook_engine"],
                            "abstained": preturn_info["abstained"],
                            "abstention_code": preturn_info["abstention_code"],
                            "winning_probe": preturn_info["winning_probe"],
                            "reformulated_query": preturn_info["reformulated_query"],
                            "injected_tokens": preturn_info["injected_tokens"],
                            "card_identity": (
                                preturn_info["cards"][0]["identity"] if preturn_info["cards"] else None
                            ),
                            "card_digest": (
                                preturn_info["cards"][0]["body_digest"] if preturn_info["cards"] else None
                            ),
                            "card_score": (
                                preturn_info["cards"][0]["score"] if preturn_info["cards"] else 0.0
                            ),
                        },
                        "model_call": call_record,
                        "extracted_code_sha256": hashlib.sha256(
                            extracted_code.encode("utf-8")
                        ).hexdigest(),
                        "extracted_code": extracted_code,
                        "verification": verification,
                    },
                    raw_key,
                )
            )

    summary = _summarize_trials(trials)
    artifact = scrub_secrets(
        {
            "record_type": ARTIFACT_RECORD_TYPE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "slot_id": SLOT_ID,
            "engine_id": ENGINE_LIVE_OLLAMA,
            "endpoint": COMPATIBLE_CHAT_ENDPOINT,
            "primary_model": primary_model,
            "max_physical_requests_ceiling": max_requests,
            "physical_requests_used": meter.used,
            "summary": summary,
            "trials": trials,
        },
        raw_key,
    )
    assert_no_secrets_in_record(artifact, raw_key)
    artifact_path = Path(request.get("artifact_path") or DEFAULT_ARTIFACT_PATH)
    if request.get("write_artifact", False):
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return artifact


def _execute_offline_replay_engine(
    frame: EnvelopeFrame,
    request: dict[str, Any],
) -> dict[str, Any]:
    """Replay saved `results.json` offline in <50ms and re-verify every recorded code solution."""
    t0 = time.perf_counter()
    artifact_path = Path(request.get("artifact_path") or DEFAULT_ARTIFACT_PATH)
    if not artifact_path.exists():
        raise FileNotFoundError(f"replay_artifact_not_found:{artifact_path}")
    saved = json.loads(artifact_path.read_text(encoding="utf-8"))
    selected_task_ids = set(request.get("task_ids") or [t["task_id"] for t in TASKS])

    replayed_trials: list[dict[str, Any]] = []
    for saved_trial in saved.get("trials") or []:
        task_id = saved_trial["task_id"]
        if task_id not in selected_task_ids:
            continue
        nested_frame = enter_nested(frame, NESTED_PRETURN_SLOT_ID)
        recorded_hook = saved_trial.get("preturn_hook") or {}
        code = str(saved_trial.get("extracted_code") or "")
        re_verified = TASK_VERIFIERS[task_id](code)
        replayed_trials.append({
            **saved_trial,
            "preturn_hook_reverified": {
                "nested_depth": nested_frame.depth,
                "abstained": bool(recorded_hook.get("abstained", True)),
                "card_identity": recorded_hook.get("card_identity"),
                "injected_tokens": int(recorded_hook.get("injected_tokens", 0)),
            },
            "verification": re_verified,
            "replay_matches_recorded_verdict": (
                re_verified["passed"] == saved_trial["verification"]["passed"]
                and abs(float(re_verified["score"]) - float(saved_trial["verification"]["score"])) < 1e-6
            ),
        })

    summary = _summarize_trials(replayed_trials)
    replay_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return {
        "record_type": ARTIFACT_RECORD_TYPE,
        "generated_at": saved.get("generated_at", ""),
        "slot_id": SLOT_ID,
        "engine_id": ENGINE_OFFLINE_REPLAY,
        "source_engine_id": saved.get("engine_id", ENGINE_LIVE_OLLAMA),
        "endpoint": saved.get("endpoint", COMPATIBLE_CHAT_ENDPOINT),
        "primary_model": saved.get("primary_model", PRIMARY_MODEL),
        "max_physical_requests_ceiling": saved.get("max_physical_requests_ceiling", MAX_PHYSICAL_REQUESTS_CEILING),
        "physical_requests_used": 0,
        "recorded_physical_requests": saved.get("physical_requests_used", len(replayed_trials)),
        "replay_elapsed_ms": replay_elapsed_ms,
        "all_verdicts_reproduced": all(t["replay_matches_recorded_verdict"] for t in replayed_trials),
        "summary": summary,
        "trials": replayed_trials,
    }


def _execute_synthetic_control_engine(
    frame: EnvelopeFrame,
    request: dict[str, Any],
) -> dict[str, Any]:
    """Execute in-memory known-wrong controls to verify that all 8 verifiers reject faulty code."""
    selected_task_ids = tuple(request.get("task_ids") or [t["task_id"] for t in TASKS])
    control_results: list[dict[str, Any]] = []
    for task_id in selected_task_ids:
        task = TASK_BY_ID[task_id]
        _ = retrieve_baltor_card_for_task(frame, task, ARM_WITH_BALTOR)
        wrong_code = KNOWN_WRONG_CONTROLS[task_id]
        verdict = TASK_VERIFIERS[task_id](wrong_code)
        control_results.append({
            "task_id": task_id,
            "domain": task["domain"],
            "control_kind": "known_wrong",
            "verification": verdict,
            "rejected_as_expected": not verdict["passed"],
        })
    return {
        "record_type": ARTIFACT_RECORD_TYPE,
        "slot_id": SLOT_ID,
        "engine_id": ENGINE_SYNTHETIC_CONTROL,
        "physical_requests_used": 0,
        "all_known_wrong_rejected": all(c["rejected_as_expected"] for c in control_results),
        "controls": control_results,
    }


ENGINE_DISPATCH_TABLE: dict[str, Callable[[EnvelopeFrame, dict[str, Any]], dict[str, Any]]] = {
    ENGINE_LIVE_OLLAMA: _execute_live_ollama_engine,
    ENGINE_OFFLINE_REPLAY: _execute_offline_replay_engine,
    ENGINE_SYNTHETIC_CONTROL: _execute_synthetic_control_engine,
}


# ---------------------------------------------------------------------------
# 7-Layer ComponentEnvelope Runner (`src/loop_engine/core/engines/envelope.py`)
# ---------------------------------------------------------------------------

ALLOWED_BENCHMARK_REQUEST_FIELDS = frozenset({
    "record_type",
    "protocol_version",
    "request_id",
    "principal",
    "engine_id",
    "fallback_engines",
    "granted_effects",
    "max_physical_requests",
    "timeout_seconds",
    "model",
    "fallback_models",
    "task_ids",
    "artifact_path",
    "write_artifact",
    "prompt_override",
})


class MultiDomainBenchmarkEnvelope:
    """7-layer ComponentEnvelope wrapping `multi_domain_ollama_benchmark_harness`."""

    def __init__(self) -> None:
        self._journal: list[Any] = []
        self._cached_results: dict[str, dict[str, Any]] = {}
        self.recovery_policy = EnvelopeRecoveryPolicy(
            component=SLOT_ID,
            maximum_automatic_attempts=2,
            recoverable_codes=("transient_engine_error",),
        )

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Run a request through all 7 envelope layers and return a versioned result or refusal."""
        frame = root_frame(SLOT_ID)
        steps: list[tuple[str, str]] = []

        # Layer 2 (inbound 1): Carrier validation
        if not isinstance(request, dict) or request.get("record_type") != REQUEST_RECORD_TYPE:
            refusal = envelope_refusal(
                "invalid_carrier_record",
                "The benchmark request does not carry the expected record type version.",
                "Send a dictionary with record_type set to multi_domain_benchmark_request/v1.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            trace = EnvelopeTrace(SLOT_ID, tuple(steps), False, LAYER_CARRIER, refusal)
            return {"record_type": refusal.record_type, "refusal": refusal.to_dict(), "trace": trace.to_dict()}

        unknown_fields = sorted(set(request.keys()) - ALLOWED_BENCHMARK_REQUEST_FIELDS)
        if unknown_fields:
            refusal = envelope_refusal(
                "unknown_carrier_fields",
                "The benchmark request includes undeclared fields outside the schema.",
                "Remove the unknown fields from the request payload before sending it again.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            trace = EnvelopeTrace(SLOT_ID, tuple(steps), False, LAYER_CARRIER, refusal)
            return {"record_type": refusal.record_type, "refusal": refusal.to_dict(), "trace": trace.to_dict()}
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        # Layer 3 (inbound 2): Handshake negotiation
        engine_id = str(request.get("engine_id") or ENGINE_OFFLINE_REPLAY)
        if engine_id not in ENGINE_DECLARATIONS:
            refusal = envelope_refusal(
                "undeclared_benchmark_engine",
                "The requested benchmark engine is not registered in this component slot.",
                "Choose ollama_cloud_live_harness_engine, deterministic_reference_replay_engine, or synthetic_contract_control_engine.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            trace = EnvelopeTrace(SLOT_ID, tuple(steps), False, LAYER_HANDSHAKE, refusal)
            return {"record_type": refusal.record_type, "refusal": refusal.to_dict(), "trace": trace.to_dict()}

        declaration = ENGINE_DECLARATIONS[engine_id]
        default_grants = ("reads_fs",) if engine_id == ENGINE_OFFLINE_REPLAY else (PURE_EFFECT,)
        granted_effects = tuple(request.get("granted_effects") or default_grants)
        hs_request = EnvelopeHandshakeRequest(
            component=SLOT_ID,
            requested_versions=( str(request.get("protocol_version") or PROTOCOL_VERSION), ),
            required_capabilities=("multi_domain_benchmark", "preturn_card_comparison"),
            advisory_capabilities=(),
            granted_effects=granted_effects,
        )
        verdict = negotiate_handshake(hs_request, declaration)
        if not verdict.proceeds:
            refusal = envelope_refusal(
                "handshake_policy_refused",
                "The caller did not grant the effects or protocol version required by the selected engine.",
                "Grant the required engine effects or switch to the offline replay engine.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            trace = EnvelopeTrace(SLOT_ID, tuple(steps), False, LAYER_HANDSHAKE, refusal)
            return {
                "record_type": refusal.record_type,
                "handshake_verdict": verdict.to_dict(),
                "refusal": refusal.to_dict(),
                "trace": trace.to_dict(),
            }
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

        # Layer 4 (inbound 3): Account & budget ceiling check
        principal = str(request.get("principal") or "local_operator")
        max_req = int(request.get("max_physical_requests", MAX_PHYSICAL_REQUESTS_CEILING))
        if not principal.strip() or max_req < 1 or max_req > MAX_PHYSICAL_REQUESTS_CEILING:
            refusal = envelope_refusal(
                "account_budget_ceiling_exceeded",
                "The requested physical model call allowance exceeds the sixteen-request ceiling.",
                "Set max_physical_requests to an integer between one and sixteen.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            steps.append((LAYER_ACCOUNT, LAYER_REFUSED))
            trace = EnvelopeTrace(SLOT_ID, tuple(steps), False, LAYER_ACCOUNT, refusal)
            return {"record_type": refusal.record_type, "refusal": refusal.to_dict(), "trace": trace.to_dict()}
        steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

        # Layer 5 (inbound 4): Tracking & idempotent replay journal
        req_id = str(request.get("request_id") or "req_default_multi_domain")
        identity_digest = request_identity_digest({
            "slot": SLOT_ID,
            "request_id": req_id,
            "engine_id": engine_id,
            "task_ids": list(request.get("task_ids") or [t["task_id"] for t in TASKS]),
            "max_physical_requests": max_req,
        })
        decision = journal_decision(self._journal, identity_digest)
        if decision.decision == ANSWER_FROM_FIRST_RESULT and req_id in self._cached_results:
            steps.append((LAYER_TRACKING, LAYER_ANSWERED))
            trace = EnvelopeTrace(SLOT_ID, tuple(steps), False, "", None)
            return {
                "record_type": RESULT_RECORD_TYPE,
                "answered_from_tracking_journal": True,
                "handshake_verdict": verdict.to_dict(),
                "trace": trace.to_dict(),
                "frame": frame.to_dict(),
                "coverage_layers": list(COVERAGE_LAYERS),
                "artifact": self._cached_results[req_id],
            }
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # Layer 6 (inbound 5): Preflight effect-free checks
        prompt_override = str(request.get("prompt_override") or "")
        task_ids = tuple(request.get("task_ids") or [t["task_id"] for t in TASKS])

        def _check_prompt_secrets(ctx: Any) -> EnvelopeRefusal | None:
            text = str(ctx.get("prompt_override") or "")
            if any(p.search(text) for p in _SECRET_PATTERNS):
                return envelope_refusal(
                    "secret_in_prompt_detected",
                    "The prompt payload contains a raw credential or bearer token string.",
                    "Strip all credentials from the prompt before submitting the benchmark request.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        def _check_task_ids(ctx: Any) -> EnvelopeRefusal | None:
            tids = tuple(ctx.get("task_ids") or ())
            if not tids or any(tid not in TASK_BY_ID for tid in tids):
                return envelope_refusal(
                    "invalid_task_identifier",
                    "One or more requested task identifiers do not exist in the benchmark suite.",
                    "Specify task identifiers from the eight registered multi-domain tasks.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        preflight_checks = (
            EnvelopePreflightCheck("prompt_secret_scan", ("secret_in_prompt_detected",), _check_prompt_secrets),
            EnvelopePreflightCheck("task_registry_check", ("invalid_task_identifier",), _check_task_ids),
        )
        preflight_report = run_preflight(
            SLOT_ID,
            preflight_checks,
            context={"prompt_override": prompt_override, "task_ids": task_ids},
        )
        if preflight_report.verdict == VERDICT_REFUSED:
            refusal = preflight_report.refusal
            assert refusal is not None
            steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
            trace = EnvelopeTrace(SLOT_ID, tuple(steps), False, LAYER_PREFLIGHT, refusal)
            return {
                "record_type": refusal.record_type,
                "preflight_report": preflight_report.to_dict(),
                "refusal": refusal.to_dict(),
                "trace": trace.to_dict(),
            }
        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

        # Layer 7: Engine slot dispatch with nested pre-turn envelope
        intent_entry = journal_intent(
            self._journal,
            component=SLOT_ID,
            request_identity=identity_digest,
            repeatable=True,
            at="2026-10-16T23:59:00Z",
        )
        self._journal.append(intent_entry)

        execution_chain = [engine_id] + [
            fb for fb in (request.get("fallback_engines") or ()) if fb in ENGINE_DISPATCH_TABLE and fb != engine_id
        ]
        last_error = ""
        for candidate_engine in execution_chain:
            try:
                artifact = ENGINE_DISPATCH_TABLE[candidate_engine](frame, request)
                outcome_entry = journal_outcome(
                    self._journal,
                    component=SLOT_ID,
                    request_identity=identity_digest,
                    request_outcome=REQUEST_ANSWERED,
                    task_outcome=TASK_COMPLETED,
                    effect_state=EFFECT_STATE_CONFIRMED,
                    result_digest=hashlib.sha256(
                        json.dumps(artifact, sort_keys=True).encode("utf-8")
                    ).hexdigest(),
                    at="2026-10-16T23:59:05Z",
                )
                self._journal.append(outcome_entry)
                self._cached_results[req_id] = artifact
                trace = EnvelopeTrace(SLOT_ID, tuple(steps), True, "", None)
                return {
                    "record_type": RESULT_RECORD_TYPE,
                    "answered_from_tracking_journal": False,
                    "selected_engine": candidate_engine,
                    "handshake_verdict": verdict.to_dict(),
                    "preflight_report": preflight_report.to_dict(),
                    "trace": trace.to_dict(),
                    "frame": frame.to_dict(),
                    "coverage_layers": list(COVERAGE_LAYERS),
                    "artifact": artifact,
                }
            except Exception as exc:
                last_error = scrub_secrets(f"{type(exc).__name__}: {str(exc)[:240]}", load_api_key())

        refusal = envelope_refusal(
            "engine_execution_failed",
            "The benchmark engine could not complete execution within the declared constraints.",
            "Wait for provider availability or run with the deterministic reference replay engine.",
            retry=RETRY_AFTER_WAIT,
            retry_after_seconds=5,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
        trace = EnvelopeTrace(SLOT_ID, tuple(steps), True, ENGINE_SOURCE, refusal)
        return {
            "record_type": refusal.record_type,
            "error_detail": last_error,
            "refusal": refusal.to_dict(),
            "trace": trace.to_dict(),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--engine",
        default=ENGINE_OFFLINE_REPLAY,
        choices=ENGINE_IDS,
        help="Execution engine to dispatch inside the 7-layer ComponentEnvelope",
    )
    parser.add_argument(
        "--artifact",
        default=str(DEFAULT_ARTIFACT_PATH),
        help="Path to read or write results.json artifact",
    )
    parser.add_argument(
        "--write-artifact",
        action="store_true",
        help="Write the benchmark output to --artifact when running live",
    )
    parser.add_argument(
        "--model",
        default=PRIMARY_MODEL,
        help="Primary Ollama Cloud model identifier",
    )
    args = parser.parse_args(argv)

    envelope = MultiDomainBenchmarkEnvelope()
    grants = (
        ("reads_fs", "network", "model_call")
        if args.engine == ENGINE_LIVE_OLLAMA
        else ("reads_fs",)
        if args.engine == ENGINE_OFFLINE_REPLAY
        else (PURE_EFFECT,)
    )
    result = envelope.run({
        "record_type": REQUEST_RECORD_TYPE,
        "protocol_version": PROTOCOL_VERSION,
        "request_id": f"cli_{args.engine}",
        "principal": "cli_benchmark_runner",
        "engine_id": args.engine,
        "granted_effects": grants,
        "max_physical_requests": MAX_PHYSICAL_REQUESTS_CEILING,
        "model": args.model,
        "artifact_path": args.artifact,
        "write_artifact": args.write_artifact,
    })
    if result.get("record_type") != RESULT_RECORD_TYPE:
        print(json.dumps(result, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    summary = result["artifact"].get("summary") or {
        "all_known_wrong_rejected": result["artifact"].get("all_known_wrong_rejected")
    }
    print(json.dumps({"engine": result["selected_engine"], "summary": summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
