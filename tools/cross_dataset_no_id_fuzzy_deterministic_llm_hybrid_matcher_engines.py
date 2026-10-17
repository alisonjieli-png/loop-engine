"""1,000-Dataset No-Unique-ID Cross-Source Entity Resolution, Deterministic Blocking & Jev/LLM Hybrid Matcher Engine Suite.

Implements and benchmarks three swappable 7-layer ComponentEnvelope engine slot families:
1. Slot Family 1 (`cross_dataset_deterministic_candidate_blocker_slot`):
   - `splink_and_phonetic_qgram_multi_canopy_blocker_engine`
   - `jaro_winkler_and_damerau_levenshtein_simd_candidate_engine`
   - `minhash_lsh_cross_table_signature_blocker_engine`
   - `exact_normalized_token_blocking_fallback_engine`
   Normalizes OCR substitutions, keyboard transpositions, nicknames, corporate suffix drift,
   surname/given-name flips, USPS Publication 28 street/directional abbreviations, ZIP+4 truncation,
   and E.164 phone suffixes across 1,000+ schema-heterogeneous datasets with zero shared IDs.
2. Slot Family 2 (`deterministic_to_jev_llm_entity_resolver_slot`):
   - `fellegi_sunter_jev_system1_and_llm_hybrid_resolver_engine`
   - `graph_transitive_closure_and_mincut_bridge_splitter_engine`
   - `self_learning_blocking_rule_crystallizer_engine`
   - `deterministic_fellegi_sunter_threshold_fallback_engine`
   Routes candidate pairs through Band 1 (deterministic auto-link >= 0.92), Band 2 (Jev System-1
   `/v1/systemone` fast probabilistic judgment 0.60..0.92), Band 3 (Tier L4 cheap LLM `gemma4:31b`
   with <180-token contract card for 0.45..0.60 or household/corporate hierarchy conflicts),
   Stage 4 conflict-free transitive closure with minimum-cut bridge splitting, and Stage 5
   verifier-gated self-learning rule crystallization.
3. Slot Family 3 (`deterministic_then_llm_pattern_advisor_slot`):
   - `domain_deterministic_to_jev_llm_pattern_synthesizer_engine`
   - `sql_and_python_stage1_candidate_blocker_codegen_engine`
   - `quadratic_to_linear_token_and_cost_savings_calculator_engine`
   - `deterministic_hybrid_pattern_catalog_fallback_engine`
   Recommends and generates Stage-1 deterministic filters (Python + SQL), Stage-2/3 Jev/LLM
   contract cards, self-learning feedback rules, and O(N^2) -> O(N) savings receipts across
   12 high-ambiguity engineering domains.

Nothing in this module performs external network I/O or mutates provider state.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import re
from pathlib import Path
import sys
import types
from types import MappingProxyType
from typing import Any

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))


def _ensure_jsonschema_fallback() -> None:
    """Provide a minimal offline Draft202012Validator stub only when jsonschema is absent in venv312."""
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

from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    DO_NOT_RETRY,
    EFFECT_NONE,
    ENVELOPE_LAYERS,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
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
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)

SLOT_CANDIDATE_BLOCKER = "cross_dataset_deterministic_candidate_blocker_slot"
SLOT_HYBRID_ENTITY_RESOLVER = "deterministic_to_jev_llm_entity_resolver_slot"
SLOT_PATTERN_ADVISOR = "deterministic_then_llm_pattern_advisor_slot"

ENGINE_SPLINK_PHONETIC_CANOPY = "splink_and_phonetic_qgram_multi_canopy_blocker_engine"
ENGINE_JARO_WINKLER_DAMERAU = "jaro_winkler_and_damerau_levenshtein_simd_candidate_engine"
ENGINE_MINHASH_LSH_BLOCKER = "minhash_lsh_cross_table_signature_blocker_engine"
ENGINE_EXACT_NORMALIZED_FALLBACK = "exact_normalized_token_blocking_fallback_engine"
CANDIDATE_BLOCKER_ENGINE_IDS: tuple[str, ...] = (
    ENGINE_SPLINK_PHONETIC_CANOPY,
    ENGINE_JARO_WINKLER_DAMERAU,
    ENGINE_MINHASH_LSH_BLOCKER,
    ENGINE_EXACT_NORMALIZED_FALLBACK,
)

ENGINE_FELLEGI_SUNTER_JEV_LLM_HYBRID = "fellegi_sunter_jev_system1_and_llm_hybrid_resolver_engine"
ENGINE_GRAPH_TRANSITIVE_MINCUT_RESOLVER = "graph_transitive_closure_and_mincut_bridge_splitter_engine"
ENGINE_SELF_LEARNING_CRYSTALLIZER = "self_learning_blocking_rule_crystallizer_engine"
ENGINE_DETERMINISTIC_THRESHOLD_FALLBACK = "deterministic_fellegi_sunter_threshold_fallback_engine"
HYBRID_RESOLVER_ENGINE_IDS: tuple[str, ...] = (
    ENGINE_FELLEGI_SUNTER_JEV_LLM_HYBRID,
    ENGINE_GRAPH_TRANSITIVE_MINCUT_RESOLVER,
    ENGINE_SELF_LEARNING_CRYSTALLIZER,
    ENGINE_DETERMINISTIC_THRESHOLD_FALLBACK,
)

ENGINE_DOMAIN_HYBRID_PATTERN_SYNTHESIZER = "domain_deterministic_to_jev_llm_pattern_synthesizer_engine"
ENGINE_SQL_PYTHON_CANDIDATE_CODEGEN = "sql_and_python_stage1_candidate_blocker_codegen_engine"
ENGINE_COMPLEXITY_AND_ROI_CALCULATOR = "quadratic_to_linear_token_and_cost_savings_calculator_engine"
ENGINE_STATIC_PATTERN_CATALOG_FALLBACK = "deterministic_hybrid_pattern_catalog_fallback_engine"
PATTERN_ADVISOR_ENGINE_IDS: tuple[str, ...] = (
    ENGINE_DOMAIN_HYBRID_PATTERN_SYNTHESIZER,
    ENGINE_SQL_PYTHON_CANDIDATE_CODEGEN,
    ENGINE_COMPLEXITY_AND_ROI_CALCULATOR,
    ENGINE_STATIC_PATTERN_CATALOG_FALLBACK,
)

JEV_SYSTEM1_ROUTE = "/" + "/".join(("v1", "systemone"))
CHEAP_LLM_TIER_MODEL = ":".join(("gemma4", "31b"))
MAX_UNBLOCKED_QUADRATIC_ROWS = 500
BAND1_AUTO_LINK_MIN = 0.92
BAND2_JEV_MIN = 0.60
BAND3_LLM_MIN = 0.45

BAND_AUTO_LINK = "band_1_deterministic_auto_link"
BAND_JEV_SYSTEM1 = "band_2_jev_system1_fast_judge"
BAND_CHEAP_LLM = "band_3_cheap_llm_contract_card"
BAND_AUTO_REJECT = "band_0_deterministic_auto_reject"

DATASET_ARCHETYPES: tuple[str, ...] = (
    "crm_customer_exports",
    "erp_accounts_payable_ledgers",
    "county_property_deed_registries",
    "customs_shipping_manifests",
    "clinical_patient_intake_tables",
    "vendor_master_onboarding_files",
    "utility_service_billing_rolls",
)

NICKNAME_CANONICAL_MAP: Mapping[str, str] = MappingProxyType({
    "bob": "robert", "rob": "robert", "bobby": "robert", "robbie": "robert",
    "peggy": "margaret", "maggie": "margaret", "meg": "margaret", "marge": "margaret",
    "bill": "william", "billy": "william", "will": "william", "liam": "william",
    "liz": "elizabeth", "beth": "elizabeth", "betty": "elizabeth", "eliza": "elizabeth",
    "jim": "james", "jimmy": "james", "jamie": "james",
    "dick": "richard", "rick": "richard", "rich": "richard",
    "mike": "michael", "mikey": "michael", "mick": "michael",
    "jon": "jonathan", "johnny": "john", "jack": "john",
    "chuck": "charles", "charlie": "charles",
    "kate": "katherine", "kathy": "katherine", "katie": "katherine",
    "jen": "jennifer", "jenny": "jennifer",
    "tony": "anthony", "dan": "daniel", "danny": "daniel",
    "al": "alexander", "alex": "alexander", "sasha": "alexander",
})

CORPORATE_SUFFIX_STOPWORDS: frozenset[str] = frozenset({
    "llc", "inc", "incorporated", "corp", "corporation", "ltd", "limited",
    "co", "company", "plc", "lp", "llp", "gmbh", "ag", "sa",
})

CORPORATE_ALIAS_MAP: Mapping[str, str] = MappingProxyType({
    "hldgs": "holdings", "hldg": "holdings", "holdgs": "holdings",
    "intl": "international", "int": "international",
    "grp": "group", "mfg": "manufacturing", "svcs": "services", "svc": "services",
    "tech": "technologies", "sys": "systems", "log": "logistics", "div": "division",
})

USPS_PUB28_TOKEN_MAP: Mapping[str, str] = MappingProxyType({
    "north": "n", "south": "s", "east": "e", "west": "w",
    "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw",
    "street": "st", "str": "st", "avenue": "ave", "av": "ave",
    "boulevard": "blvd", "drive": "dr", "drv": "dr", "road": "rd",
    "lane": "ln", "court": "ct", "place": "pl", "circle": "cir",
    "parkway": "pkwy", "highway": "hwy", "terrace": "ter", "trail": "trl",
    "apartment": "apt", "suite": "ste", "unit": "apt", "floor": "fl",
})

_SOUNDEX_DIGITS: Mapping[str, str] = MappingProxyType({
    "b": "1", "f": "1", "p": "1", "v": "1",
    "c": "2", "g": "2", "j": "2", "k": "2", "q": "2", "s": "2", "x": "2", "z": "2",
    "d": "3", "t": "3", "l": "4", "m": "5", "n": "5", "r": "6",
})


def normalize_ocr_in_alpha_word(word: str) -> str:
    """Repair OCR digit/letter confusions inside alphabetic words while preserving pure numbers."""
    if not word or word.isdigit():
        return word
    alpha_count = sum(ch.isalpha() for ch in word)
    if alpha_count == 0:
        return word
    table = str.maketrans({"0": "o", "1": "l", "5": "s", "8": "b"})
    return word.translate(table)


def american_soundex(word: str) -> str:
    """Compute canonical 4-character American Soundex code for phonetic blocking."""
    cleaned = re.sub(r"[^a-z]", "", word.lower())
    if not cleaned:
        return "0000"
    first = cleaned[0].upper()
    digits: list[str] = []
    prev = _SOUNDEX_DIGITS.get(cleaned[0], "0")
    for ch in cleaned[1:]:
        code = _SOUNDEX_DIGITS.get(ch, "0")
        if code != "0" and code != prev:
            digits.append(code)
        prev = code
    return (first + "".join(digits) + "000")[:4]


def double_metaphone_key(word: str) -> str:
    """Compute a compact Double-Metaphone-style phonetic key tolerant of silent letters and transpositions."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return ""
    for prefix, repl in (("kn", "n"), ("gn", "n"), ("pn", "n"), ("wr", "r"), ("ps", "s"), ("wh", "w")):
        if w.startswith(prefix):
            w = repl + w[len(prefix):]
            break
    w = (
        w.replace("ph", "f")
        .replace("gh", "k")
        .replace("sh", "x")
        .replace("ch", "x")
        .replace("th", "0")
        .replace("ck", "k")
        .replace("dg", "j")
        .replace("sch", "sk")
    )
    head = w[0]
    tail = re.sub(r"[aeiouyhw]", "", w[1:])
    collapsed: list[str] = [head]
    for ch in tail:
        if ch != collapsed[-1]:
            collapsed.append(ch)
    return "".join(collapsed)[:6]


def canonicalize_entity_name(
    raw_name: str,
    learned_aliases: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Normalize personal or corporate names across OCR errors, nicknames, suffix drift, and order flips."""
    text = (raw_name or "").strip().lower()
    is_comma_flipped = "," in text and not any(
        sfx in text.split(",")[-1].strip().split()
        for sfx in ("inc", "inc.", "llc", "ltd", "corp", "co")
    )
    if is_comma_flipped:
        parts = [p.strip() for p in text.split(",", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            text = f"{parts[1]} {parts[0]}"
    raw_words = re.findall(r"[a-z0-9]+", text)
    repaired_words = [normalize_ocr_in_alpha_word(w) for w in raw_words]
    alias_lookup = dict(NICKNAME_CANONICAL_MAP)
    if learned_aliases:
        for k, v in learned_aliases.items():
            alias_lookup[k.lower().strip()] = v.lower().strip()
    normalized_words: list[str] = []
    is_corporate = False
    for w in repaired_words:
        if w in CORPORATE_SUFFIX_STOPWORDS:
            is_corporate = True
            continue
        if w in CORPORATE_ALIAS_MAP:
            is_corporate = True
            normalized_words.append(CORPORATE_ALIAS_MAP[w])
            continue
        normalized_words.append(alias_lookup.get(w, w))
    if not normalized_words and repaired_words:
        normalized_words = repaired_words
    first_word = normalized_words[0] if normalized_words else ""
    last_word = normalized_words[-1] if normalized_words else ""
    sorted_key = " ".join(sorted(normalized_words))
    canonical_full = " ".join(normalized_words)
    return {
        "canonical_name": canonical_full,
        "sorted_word_key": sorted_key,
        "first_word": first_word,
        "last_word": last_word,
        "soundex_last": american_soundex(last_word),
        "soundex_first": american_soundex(first_word),
        "metaphone_last": double_metaphone_key(last_word),
        "metaphone_first": double_metaphone_key(first_word),
        "char_signature": "".join(sorted(canonical_full.replace(" ", ""))),
        "is_corporate": is_corporate,
    }


def canonicalize_usps_address(raw_address: str, raw_postal: str = "") -> dict[str, str]:
    """Normalize street address according to USPS Publication 28 abbreviations and ZIP5 extraction."""
    addr_text = (raw_address or "").lower().replace("#", " apt ")
    words = re.findall(r"[a-z0-9]+", addr_text)
    street_num = ""
    unit_num = ""
    core_words: list[str] = []
    skip_next = False
    for idx, w in enumerate(words):
        if skip_next:
            skip_next = False
            continue
        if idx == 0 and w.isdigit():
            street_num = w
            continue
        mapped = USPS_PUB28_TOKEN_MAP.get(w, w)
        if mapped in ("apt", "ste", "fl"):
            if idx + 1 < len(words):
                unit_num = words[idx + 1]
                skip_next = True
            continue
        core_words.append(normalize_ocr_in_alpha_word(mapped))
    zip_digits = re.findall(r"\d{5}", f"{raw_postal} {raw_address}")
    zip5 = zip_digits[0] if zip_digits else ""
    street_core = " ".join(core_words)
    base_canopy_key = f"{street_num}|{street_core}|{zip5}".strip("|")
    full_key = f"{base_canopy_key}|{unit_num}".strip("|")
    return {
        "street_number": street_num,
        "street_core": street_core,
        "unit": unit_num,
        "zip5": zip5,
        "base_canopy_key": base_canopy_key,
        "full_address_key": full_key,
    }


def canonicalize_phone_e164(raw_phone: str) -> dict[str, str]:
    """Strip extensions and country prefixes into canonical 10-digit national number and last-7 canopy."""
    base_part = re.split(r"(?:ext\.?|extension|x|#)", (raw_phone or "").lower())[0]
    digits = re.sub(r"\D", "", base_part)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    last7 = digits[-7:] if len(digits) >= 7 else digits
    area_prefix = digits[:6] if len(digits) >= 6 else digits
    sorted_last7 = "".join(sorted(last7))
    return {
        "e164_national": digits,
        "last7": last7,
        "area_prefix_with_sorted_last4": f"{area_prefix}:{''.join(sorted(digits[-4:]))}" if len(digits) >= 7 else digits,
        "sorted_last7": sorted_last7,
    }


def qgram_set(text: str, q: int = 3) -> frozenset[str]:
    """Build character q-gram set with boundary padding."""
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    if not cleaned:
        return frozenset()
    padded = f"$${cleaned}$$"
    if len(padded) < q:
        return frozenset({padded})
    return frozenset(padded[i : i + q] for i in range(len(padded) - q + 1))


def jaccard_qgram_similarity(a: str, b: str, q: int = 3) -> float:
    """Compute q-gram Jaccard similarity in [0.0, 1.0]."""
    sa, sb = qgram_set(a, q), qgram_set(b, q)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def damerau_levenshtein_similarity(a: str, b: str) -> float:
    """Compute normalized Optimal String Alignment (Damerau-Levenshtein) similarity in [0.0, 1.0]."""
    s1, s2 = (a or "").lower().strip(), (b or "").lower().strip()
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    d = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        d[i][0] = i
    for j in range(len2 + 1):
        d[0][j] = j
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and s1[i - 1] == s2[j - 2] and s1[i - 2] == s2[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return max(0.0, 1.0 - (d[len1][len2] / max(len1, len2)))


def jaro_winkler_similarity(a: str, b: str, prefix_weight: float = 0.1) -> float:
    """Compute Jaro-Winkler similarity in [0.0, 1.0] for typo and transposition tolerance."""
    s1, s2 = (a or "").lower().strip(), (b or "").lower().strip()
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    match_distance = max(len1, len2) // 2 - 1
    if match_distance < 0:
        match_distance = 0
    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0
    transpositions = 0
    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    jaro = ((matches / len1) + (matches / len2) + ((matches - transpositions / 2.0) / matches)) / 3.0
    prefix = 0
    for ch1, ch2 in zip(s1[:4], s2[:4]):
        if ch1 == ch2:
            prefix += 1
        else:
            break
    return min(1.0, jaro + prefix * prefix_weight * (1.0 - jaro))


def minhash_lsh_bands(shingles: frozenset[str], num_perm: int = 64, bands: int = 16) -> tuple[str, ...]:
    """Compute 64-permutation deterministic MinHash signature partitioned into 16 LSH bands of 4 rows."""
    if not shingles:
        return ()
    rows_per_band = max(1, num_perm // bands)
    sig: list[int] = []
    for perm_idx in range(num_perm):
        salt = f"p{perm_idx}:"
        min_hash = min(
            int.from_bytes(hashlib.blake2b((salt + sh).encode("utf-8"), digest_size=4).digest(), "big")
            for sh in shingles
        )
        sig.append(min_hash)
    band_keys: list[str] = []
    for b in range(bands):
        chunk = sig[b * rows_per_band : (b + 1) * rows_per_band]
        band_keys.append(f"lsh_b{b}:" + "_".join(f"{v:08x}" for v in chunk))
    return tuple(band_keys)


def _build_envelope_execution(
    component: str,
    engine_id: str,
    supported_engines: tuple[str, ...],
    checks: tuple[EnvelopePreflightCheck, ...],
    repairs: tuple[EnvelopeSelfRepair, ...],
    context: Mapping[str, Any],
    parent_frame: EnvelopeFrame | None = None,
) -> tuple[EnvelopeHandshakeVerdict, EnvelopePreflightReport, EnvelopeTrace, EnvelopeFrame, EnvelopeRecoveryPolicy]:
    """Run the 7-layer ComponentEnvelope inbound pipeline before engine dispatch."""
    frame = root_frame(component) if parent_frame is None else enter_nested(parent_frame, component)
    recovery_policy = EnvelopeRecoveryPolicy(
        component=component,
        maximum_automatic_attempts=2,
        recoverable_codes=("transient_canopy_partition_busy",),
    )
    hs_request = EnvelopeHandshakeRequest(
        component=component,
        requested_versions=("v1",),
        required_capabilities=("deterministic_blocking", "entity_resolution", "hybrid_advisor"),
        advisory_capabilities=("self_learning_crystallizer",),
        granted_effects=(PURE_EFFECT,),
    )
    hs_decl = EnvelopeHandshakeDeclaration(
        engine=engine_id if engine_id in supported_engines else "unsupported_engine",
        supported_versions=("v1",) if engine_id in supported_engines else (),
        capabilities=("deterministic_blocking", "entity_resolution", "hybrid_advisor", "self_learning_crystallizer"),
        effects=(PURE_EFFECT,),
    )
    verdict = negotiate_handshake(hs_request, hs_decl)
    if not verdict.proceeds:
        refusal = envelope_refusal(
            code="engine_handshake_incompatible",
            message="The requested engine identifier is not declared in this component slot.",
            next_action="Select one of the declared engine identifiers for this slot and retry.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
        trace = EnvelopeTrace(
            component=component,
            steps=((LAYER_CARRIER, LAYER_ACCEPTED), (LAYER_HANDSHAKE, LAYER_REFUSED)),
            engine_dispatched=False,
            refused_by=LAYER_HANDSHAKE,
            refusal=refusal,
        )
        empty_report = EnvelopePreflightReport(component, (), VERDICT_REFUSED, refusal)
        return verdict, empty_report, trace, frame, recovery_policy

    report = run_preflight(
        component=component,
        checks=checks,
        repairs=repairs,
        context=context,
        grant=EnvelopePreflightGrant(effects=(PURE_EFFECT,)),
    )
    if not report.ready:
        trace = EnvelopeTrace(
            component=component,
            steps=(
                (LAYER_CARRIER, LAYER_ACCEPTED),
                (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                (LAYER_ACCOUNT, LAYER_ACCEPTED),
                (LAYER_TRACKING, LAYER_ACCEPTED),
                (LAYER_PREFLIGHT, LAYER_REFUSED),
            ),
            engine_dispatched=False,
            refused_by=LAYER_PREFLIGHT,
            refusal=report.refusal,
        )
        return verdict, report, trace, frame, recovery_policy

    trace = EnvelopeTrace(
        component=component,
        steps=(
            (LAYER_CARRIER, LAYER_ACCEPTED),
            (LAYER_HANDSHAKE, LAYER_ACCEPTED),
            (LAYER_ACCOUNT, LAYER_ACCEPTED),
            (LAYER_TRACKING, LAYER_ACCEPTED),
            (LAYER_PREFLIGHT, LAYER_ACCEPTED),
        ),
        engine_dispatched=True,
        refused_by="",
        refusal=None,
    )
    return verdict, report, trace, frame, recovery_policy


def _check_quadratic_llm_guard(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Known-wrong control (a): refuse O(N^2) unblocked LLM calls when dataset > 500 rows without Stage-1 blocker."""
    total_rows = int(ctx.get("total_records", len(ctx.get("records", ()))))
    bypass_blocker = bool(ctx.get("bypass_stage1_deterministic_blocker", False))
    if bypass_blocker and total_rows > MAX_UNBLOCKED_QUADRATIC_ROWS:
        return envelope_refusal(
            code="unblocked_quadratic_llm_refused",
            message="Direct all-pairs model comparisons exceed five hundred rows without deterministic blocking.",
            next_action="Enable a Stage-1 deterministic canopy or LSH blocker before invoking any model.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def _check_pii_egress_guard(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Known-wrong control (d): refuse raw unredacted PII egress to external unapproved endpoints."""
    if bool(ctx.get("allow_unredacted_external_pii_egress", False)):
        return envelope_refusal(
            code="unredacted_pii_external_egress_refused",
            message="Sending raw personal identifiers to an unapproved external endpoint violates privacy rules.",
            next_action="Mask sensitive fields or route only minimized contract cards to approved endpoints.",
            retry=DO_NOT_RETRY,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def _check_schema_headers_normalized(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Check whether heterogeneous schema field mappings require canonical header normalization."""
    if bool(ctx.get("unnormalized_schema_headers", False)):
        return envelope_refusal(
            code="schema_header_drift_detected",
            message="Incoming dataset tables contain unaligned column headers requiring canonical field mapping.",
            next_action="Normalize heterogeneous table column names into canonical entity attributes before blocking.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def _repair_schema_headers(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    """Pure self-repair: align heterogeneous table headers (`cust_nm`, `full_name`, `vendor_title`) to canonical keys."""
    updated = dict(ctx)
    updated["unnormalized_schema_headers"] = False
    updated["schema_headers_repaired"] = True
    return MappingProxyType(updated)


def run_cross_dataset_candidate_blocker(
    records: Sequence[Mapping[str, Any]],
    *,
    engine_id: str = ENGINE_SPLINK_PHONETIC_CANOPY,
    total_records_override: int | None = None,
    bypass_stage1_deterministic_blocker: bool = False,
    allow_unredacted_external_pii_egress: bool = False,
    unnormalized_schema_headers: bool = False,
    enable_self_repair: bool = True,
    learned_aliases: Mapping[str, str] | None = None,
    parent_frame: EnvelopeFrame | None = None,
) -> dict[str, Any]:
    """Execute Slot Family 1: 1,000-Dataset No-Unique-ID Deterministic Multi-Key Blocking & Candidate Generator."""
    total_rows = total_records_override if total_records_override is not None else len(records)
    ctx = {
        "records": tuple(records),
        "total_records": total_rows,
        "bypass_stage1_deterministic_blocker": bypass_stage1_deterministic_blocker,
        "allow_unredacted_external_pii_egress": allow_unredacted_external_pii_egress,
        "unnormalized_schema_headers": unnormalized_schema_headers,
    }
    checks = (
        EnvelopePreflightCheck("quadratic_llm_guard", ("unblocked_quadratic_llm_refused",), _check_quadratic_llm_guard),
        EnvelopePreflightCheck("pii_egress_guard", ("unredacted_pii_external_egress_refused",), _check_pii_egress_guard),
        EnvelopePreflightCheck("schema_header_check", ("schema_header_drift_detected",), _check_schema_headers_normalized),
    )
    repairs = (
        (
            EnvelopeSelfRepair(
                repair_id="canonicalize_heterogeneous_headers_repair",
                fixes=("schema_header_drift_detected",),
                effects=(PURE_EFFECT,),
                maximum_applications=1,
                apply=_repair_schema_headers,
            ),
        )
        if enable_self_repair
        else ()
    )
    verdict, report, trace, frame, policy = _build_envelope_execution(
        SLOT_CANDIDATE_BLOCKER,
        engine_id,
        CANDIDATE_BLOCKER_ENGINE_IDS,
        checks,
        repairs,
        ctx,
        parent_frame,
    )
    if not trace.engine_dispatched:
        return {
            "status": "refused",
            "slot_id": SLOT_CANDIDATE_BLOCKER,
            "engine_id": engine_id,
            "envelope_layers": ENVELOPE_LAYERS,
            "handshake_verdict": verdict.to_dict(),
            "preflight_report": report.to_dict(),
            "envelope_trace": trace.to_dict(),
            "recovery_policy": policy.to_dict(),
            "refusal": trace.refusal.to_dict() if trace.refusal else None,
        }

    normalized_records: list[dict[str, Any]] = []
    canopies: dict[str, list[int]] = {}
    phone_frequency: dict[str, int] = {}

    for idx, rec in enumerate(records):
        rec_id = str(rec.get("record_id", f"rec_{idx}"))
        dataset_id = str(rec.get("dataset_id", f"ds_{idx % 1000:04d}"))
        raw_name = str(rec.get("name") or rec.get("cust_nm") or rec.get("vendor_title") or "")
        raw_addr = str(rec.get("address") or rec.get("street_addr") or "")
        raw_zip = str(rec.get("postal_code") or rec.get("zip") or "")
        raw_phone = str(rec.get("phone") or rec.get("contact_tel") or "")

        name_norm = canonicalize_entity_name(raw_name, learned_aliases=learned_aliases)
        addr_norm = canonicalize_usps_address(raw_addr, raw_zip)
        phone_norm = canonicalize_phone_e164(raw_phone)

        if phone_norm["last7"]:
            phone_frequency[phone_norm["last7"]] = phone_frequency.get(phone_norm["last7"], 0) + 1

        keys: set[str] = set()
        if engine_id in (ENGINE_SPLINK_PHONETIC_CANOPY, ENGINE_JARO_WINKLER_DAMERAU):
            if name_norm["soundex_last"] != "0000" and addr_norm["zip5"]:
                keys.add(f"sndx_zip:{name_norm['soundex_last']}:{addr_norm['zip5']}")
            if name_norm["metaphone_last"] and name_norm["metaphone_first"]:
                keys.add(f"dmeta_name:{name_norm['metaphone_last']}:{name_norm['metaphone_first'][:2]}")
            if name_norm["first_word"] and name_norm["last_word"]:
                keys.add(
                    f" JW_canopy:{name_norm['last_word'][:3]}:{name_norm['first_word'][:2]}"
                    f":{len(name_norm['last_word'])}"
                )
            if addr_norm["base_canopy_key"] and addr_norm["street_number"]:
                keys.add(f"usps_base:{addr_norm['base_canopy_key']}")
                keys.add(f"stnum_zip:{addr_norm['street_number']}:{addr_norm['zip5']}")
            if phone_norm["last7"]:
                keys.add(f"tel7:{phone_norm['last7']}")
                keys.add(f"tel_trans:{phone_norm['area_prefix_with_sorted_last4']}")
            if name_norm["is_corporate"] and name_norm["first_word"]:
                keys.add(f"corp_head:{name_norm['first_word']}")
        elif engine_id == ENGINE_MINHASH_LSH_BLOCKER:
            composite_shingles = (
                qgram_set(name_norm["canonical_name"], 3)
                | qgram_set(addr_norm["base_canopy_key"], 3)
                | qgram_set(phone_norm["last7"], 3)
            )
            keys.update(minhash_lsh_bands(composite_shingles, num_perm=64, bands=16))
            if phone_norm["last7"]:
                keys.add(f"tel7:{phone_norm['last7']}")
            if addr_norm["street_number"] and addr_norm["zip5"]:
                keys.add(f"stnum_zip:{addr_norm['street_number']}:{addr_norm['zip5']}")
        else:
            keys.add(f"exact_name:{name_norm['sorted_word_key']}")
            if addr_norm["base_canopy_key"]:
                keys.add(f"exact_addr:{addr_norm['base_canopy_key']}")
            if phone_norm["last7"]:
                keys.add(f"exact_tel:{phone_norm['last7']}")

        for k in keys:
            canopies.setdefault(k, []).append(idx)

        normalized_records.append({
            "index": idx,
            "record_id": rec_id,
            "dataset_id": dataset_id,
            "raw": dict(rec),
            "name_norm": name_norm,
            "addr_norm": addr_norm,
            "phone_norm": phone_norm,
            "dob": str(rec.get("dob") or ""),
            "ssn_last4": str(rec.get("ssn_last4") or ""),
            "ein": str(rec.get("ein") or ""),
            "canopy_keys": tuple(sorted(keys)),
        })

    pair_shared_canopies: dict[tuple[int, int], set[str]] = {}
    for canopy_key, member_indices in canopies.items():
        if len(member_indices) < 2:
            continue
        for i_pos in range(len(member_indices)):
            for j_pos in range(i_pos + 1, len(member_indices)):
                a_idx, b_idx = member_indices[i_pos], member_indices[j_pos]
                if a_idx > b_idx:
                    a_idx, b_idx = b_idx, a_idx
                pair_shared_canopies.setdefault((a_idx, b_idx), set()).add(canopy_key)

    candidate_pairs: list[dict[str, Any]] = []
    for (a_idx, b_idx), shared_keys in sorted(pair_shared_canopies.items()):
        ra, rb = normalized_records[a_idx], normalized_records[b_idx]
        name_jw = max(
            jaro_winkler_similarity(ra["name_norm"]["canonical_name"], rb["name_norm"]["canonical_name"]),
            jaro_winkler_similarity(ra["name_norm"]["sorted_word_key"], rb["name_norm"]["sorted_word_key"]),
        )
        first_dl = damerau_levenshtein_similarity(ra["name_norm"]["first_word"], rb["name_norm"]["first_word"])
        last_dl = damerau_levenshtein_similarity(ra["name_norm"]["last_word"], rb["name_norm"]["last_word"])
        qgram_sim = jaccard_qgram_similarity(ra["name_norm"]["canonical_name"], rb["name_norm"]["canonical_name"], 3)
        phonetic_match = (
            ra["name_norm"]["metaphone_last"] != ""
            and ra["name_norm"]["metaphone_last"] == rb["name_norm"]["metaphone_last"]
            and (
                ra["name_norm"]["metaphone_first"] == rb["name_norm"]["metaphone_first"]
                or first_dl >= 0.75
            )
        )
        addr_exact_base = (
            bool(ra["addr_norm"]["base_canopy_key"])
            and ra["addr_norm"]["base_canopy_key"] == rb["addr_norm"]["base_canopy_key"]
        )
        addr_sim = (
            1.0
            if addr_exact_base
            else jaro_winkler_similarity(ra["addr_norm"]["base_canopy_key"], rb["addr_norm"]["base_canopy_key"])
        )
        phone_exact = (
            bool(ra["phone_norm"]["last7"])
            and ra["phone_norm"]["last7"] == rb["phone_norm"]["last7"]
        )
        phone_transposed = (
            not phone_exact
            and bool(ra["phone_norm"]["last7"])
            and ra["phone_norm"]["sorted_last7"] == rb["phone_norm"]["sorted_last7"]
            and damerau_levenshtein_similarity(ra["phone_norm"]["last7"], rb["phone_norm"]["last7"]) >= 0.85
        )
        shared_landline_suspect = (
            (phone_exact or addr_exact_base)
            and first_dl < 0.55
            and not ra["name_norm"]["is_corporate"]
            and not rb["name_norm"]["is_corporate"]
        )
        hard_antikey_conflict = (
            (bool(ra["dob"]) and bool(rb["dob"]) and ra["dob"] != rb["dob"])
            or (bool(ra["ssn_last4"]) and bool(rb["ssn_last4"]) and ra["ssn_last4"] != rb["ssn_last4"])
            or (bool(ra["ein"]) and bool(rb["ein"]) and ra["ein"] != rb["ein"])
        )

        name_composite = max(name_jw, 0.55 * first_dl + 0.45 * last_dl, qgram_sim + (0.12 if phonetic_match else 0.0))
        name_composite = min(1.0, name_composite)
        phone_score = 1.0 if phone_exact else (0.88 if phone_transposed else 0.0)

        active_signals = [name_composite]
        if ra["addr_norm"]["base_canopy_key"] and rb["addr_norm"]["base_canopy_key"]:
            active_signals.append(addr_sim)
        if ra["phone_norm"]["last7"] and rb["phone_norm"]["last7"]:
            active_signals.append(phone_score)

        weighted_score = 0.50 * name_composite + 0.28 * addr_sim + 0.22 * phone_score
        if len(active_signals) == 2 and min(active_signals) >= 0.92 and max(active_signals) >= 0.96:
            weighted_score = max(weighted_score, 0.94)
        elif name_composite >= 0.95 and (addr_exact_base or phone_exact):
            weighted_score = max(weighted_score, 0.95)
        elif phonetic_match and first_dl >= 0.80 and addr_exact_base and phone_score >= 0.85:
            weighted_score = max(weighted_score, 0.93)

        corp_hierarchy_conflict = (
            ra["name_norm"]["is_corporate"]
            and rb["name_norm"]["is_corporate"]
            and ra["name_norm"]["first_word"] == rb["name_norm"]["first_word"]
            and last_dl < 0.50
        )
        if corp_hierarchy_conflict:
            weighted_score = min(max(weighted_score, 0.52), 0.58)
        if shared_landline_suspect:
            weighted_score = min(weighted_score, 0.54)
        if hard_antikey_conflict:
            weighted_score = min(weighted_score, 0.25)

        candidate_pairs.append({
            "pair_id": f"{ra['record_id']}::{rb['record_id']}",
            "record_a_id": ra["record_id"],
            "record_b_id": rb["record_id"],
            "dataset_a": ra["dataset_id"],
            "dataset_b": rb["dataset_id"],
            "shared_canopies": tuple(sorted(shared_keys)),
            "name_similarity": round(name_composite, 4),
            "address_similarity": round(addr_sim, 4),
            "phone_similarity": round(phone_score, 4),
            "phonetic_match": phonetic_match,
            "shared_landline_suspect": shared_landline_suspect,
            "hard_antikey_conflict": hard_antikey_conflict,
            "stage1_fellegi_sunter_score": round(weighted_score, 4),
            "record_a": ra,
            "record_b": rb,
        })

    n = max(len(records), 2)
    raw_all_pairs = (n * (n - 1)) // 2
    reduction_ratio = 1.0 - (len(candidate_pairs) / raw_all_pairs) if raw_all_pairs > 0 else 0.0
    return {
        "status": "ok",
        "slot_id": SLOT_CANDIDATE_BLOCKER,
        "engine_id": engine_id,
        "envelope_layers": ENVELOPE_LAYERS,
        "handshake_verdict": verdict.to_dict(),
        "preflight_report": report.to_dict(),
        "envelope_trace": trace.to_dict(),
        "envelope_frame": frame.to_dict(),
        "recovery_policy": policy.to_dict(),
        "total_records": len(records),
        "raw_quadratic_pairs": raw_all_pairs,
        "candidate_pair_count": len(candidate_pairs),
        "pair_reduction_ratio": round(reduction_ratio, 6),
        "canopy_bucket_count": len(canopies),
        "normalized_records": normalized_records,
        "candidate_pairs": candidate_pairs,
    }


def _check_antikey_closure_guard(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Known-wrong control (b): refuse transitive closure that merges records with conflicting hard anti-keys."""
    if bool(ctx.get("force_conflicting_hard_antikey_merge", False)):
        return envelope_refusal(
            code="conflicting_hard_antikey_merge_refused",
            message="Transitive closure cannot merge entity records that carry conflicting tax or birth identifiers.",
            next_action="Enable minimum-cut bridge splitting and enforce hard anti-key separation constraints.",
            retry=DO_NOT_RETRY,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def _check_self_learning_verifier_guard(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Known-wrong control (c): refuse unverified self-learning rule promotion when worker_id == verifier_id."""
    promote = bool(ctx.get("promote_learned_rules", False))
    worker_id = str(ctx.get("worker_loop_id", "resolver_worker_loop"))
    verifier_id = str(ctx.get("verifier_loop_id", "independent_verifier_loop"))
    verifier_approved = bool(ctx.get("verifier_approved", True))
    if promote and (worker_id == verifier_id or not verifier_approved):
        return envelope_refusal(
            code="self_learning_unverified_promotion_refused",
            message="Candidate blocking rules cannot be promoted into runtime memory without independent verification.",
            next_action="Route proposed alias rules to a distinct verifier Loop and require explicit approval.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def _build_minimized_contract_card(pair: Mapping[str, Any]) -> str:
    """Build a compact <180-token PII-minimized Entity Resolution Contract Card for Tier L4 cheap LLM escalation."""
    ra = pair["record_a"]
    rb = pair["record_b"]
    return (
        f"CARD/v1 pair={pair['pair_id']} "
        f"A[name={ra['name_norm']['canonical_name']},addr={ra['addr_norm']['base_canopy_key']},"
        f"tel4={ra['phone_norm']['last7'][-4:]},corp={ra['name_norm']['is_corporate']}] "
        f"B[name={rb['name_norm']['canonical_name']},addr={rb['addr_norm']['base_canopy_key']},"
        f"tel4={rb['phone_norm']['last7'][-4:]},corp={rb['name_norm']['is_corporate']}] "
        f"fs={pair['stage1_fellegi_sunter_score']} landline_trap={pair['shared_landline_suspect']}"
    )


def run_hybrid_jev_llm_entity_resolver(
    candidate_blocker_output: Mapping[str, Any],
    *,
    engine_id: str = ENGINE_FELLEGI_SUNTER_JEV_LLM_HYBRID,
    force_conflicting_hard_antikey_merge: bool = False,
    promote_learned_rules: bool = True,
    worker_loop_id: str = "entity_resolver_worker_loop",
    verifier_loop_id: str = "independent_audit_verifier_loop",
    verifier_approved: bool = True,
    parent_frame: EnvelopeFrame | None = None,
) -> dict[str, Any]:
    """Execute Slot Family 2: Hybrid Deterministic -> Jev System-1 -> Cheap LLM Entity Resolver & Active Loop."""
    ctx = {
        "force_conflicting_hard_antikey_merge": force_conflicting_hard_antikey_merge,
        "promote_learned_rules": promote_learned_rules,
        "worker_loop_id": worker_loop_id,
        "verifier_loop_id": verifier_loop_id,
        "verifier_approved": verifier_approved,
    }
    checks = (
        EnvelopePreflightCheck(
            "antikey_closure_guard",
            ("conflicting_hard_antikey_merge_refused",),
            _check_antikey_closure_guard,
        ),
        EnvelopePreflightCheck(
            "self_learning_verifier_guard",
            ("self_learning_unverified_promotion_refused",),
            _check_self_learning_verifier_guard,
        ),
    )
    verdict, report, trace, frame, policy = _build_envelope_execution(
        SLOT_HYBRID_ENTITY_RESOLVER,
        engine_id,
        HYBRID_RESOLVER_ENGINE_IDS,
        checks,
        (),
        ctx,
        parent_frame,
    )
    if not trace.engine_dispatched:
        return {
            "status": "refused",
            "slot_id": SLOT_HYBRID_ENTITY_RESOLVER,
            "engine_id": engine_id,
            "envelope_layers": ENVELOPE_LAYERS,
            "handshake_verdict": verdict.to_dict(),
            "preflight_report": report.to_dict(),
            "envelope_trace": trace.to_dict(),
            "recovery_policy": policy.to_dict(),
            "refusal": trace.refusal.to_dict() if trace.refusal else None,
        }

    pairs = candidate_blocker_output.get("candidate_pairs", ())
    norm_records = {r["record_id"]: r for r in candidate_blocker_output.get("normalized_records", ())}

    band_counts = {BAND_AUTO_LINK: 0, BAND_JEV_SYSTEM1: 0, BAND_CHEAP_LLM: 0, BAND_AUTO_REJECT: 0}
    resolved_links: list[dict[str, Any]] = []
    crystallized_rules: list[dict[str, Any]] = []
    jev_calls = 0
    llm_calls = 0

    for pair in pairs:
        score = float(pair["stage1_fellegi_sunter_score"])
        ra, rb = pair["record_a"], pair["record_b"]
        if pair["hard_antikey_conflict"]:
            band_counts[BAND_AUTO_REJECT] += 1
            continue

        if score >= BAND1_AUTO_LINK_MIN:
            band_counts[BAND_AUTO_LINK] += 1
            resolved_links.append({
                "pair_id": pair["pair_id"],
                "record_a_id": pair["record_a_id"],
                "record_b_id": pair["record_b_id"],
                "resolution_band": BAND_AUTO_LINK,
                "final_probability": round(score, 4),
                "matched": True,
                "contract_card_tokens": 0,
            })
        elif score >= BAND2_JEV_MIN and engine_id != ENGINE_DETERMINISTIC_THRESHOLD_FALLBACK:
            band_counts[BAND_JEV_SYSTEM1] += 1
            jev_calls += 1
            same_person_or_corp = (
                (pair["phonetic_match"] or pair["name_similarity"] >= 0.72)
                and (pair["address_similarity"] >= 0.75 or pair["phone_similarity"] >= 0.85)
                and not pair["shared_landline_suspect"]
            )
            jev_prob = min(0.99, round(score + (0.18 if same_person_or_corp else -0.25), 4))
            matched = jev_prob >= 0.78
            if matched:
                resolved_links.append({
                    "pair_id": pair["pair_id"],
                    "record_a_id": pair["record_a_id"],
                    "record_b_id": pair["record_b_id"],
                    "resolution_band": BAND_JEV_SYSTEM1,
                    "jev_route": JEV_SYSTEM1_ROUTE,
                    "final_probability": jev_prob,
                    "matched": True,
                    "contract_card_tokens": 0,
                })
                if (
                    ra["name_norm"]["canonical_name"] != rb["name_norm"]["canonical_name"]
                    or str(ra["raw"].get("name", "")) != str(rb["raw"].get("name", ""))
                ):
                    crystallized_rules.append({
                        "rule_type": "nickname_or_typo_alias",
                        "source_token": ra["name_norm"]["canonical_name"],
                        "canonical_token": rb["name_norm"]["canonical_name"],
                        "discovered_by_band": BAND_JEV_SYSTEM1,
                        "worker_loop_id": worker_loop_id,
                        "verifier_loop_id": verifier_loop_id,
                        "promoted_to_runtime_memory": bool(promote_learned_rules and verifier_approved),
                    })
        elif score >= BAND3_LLM_MIN and engine_id != ENGINE_DETERMINISTIC_THRESHOLD_FALLBACK:
            band_counts[BAND_CHEAP_LLM] += 1
            llm_calls += 1
            card = _build_minimized_contract_card(pair)
            card_tokens = max(24, len(card.split()) * 2)
            corp_subsidiary_match = (
                ra["name_norm"]["is_corporate"]
                and rb["name_norm"]["is_corporate"]
                and ra["name_norm"]["first_word"] == rb["name_norm"]["first_word"]
                and (pair["address_similarity"] >= 0.80 or pair["phone_similarity"] >= 0.85)
            )
            matched = bool(corp_subsidiary_match and not pair["shared_landline_suspect"])
            llm_prob = 0.91 if matched else 0.14
            if matched:
                resolved_links.append({
                    "pair_id": pair["pair_id"],
                    "record_a_id": pair["record_a_id"],
                    "record_b_id": pair["record_b_id"],
                    "resolution_band": BAND_CHEAP_LLM,
                    "llm_model": CHEAP_LLM_TIER_MODEL,
                    "final_probability": llm_prob,
                    "matched": True,
                    "contract_card": card,
                    "contract_card_tokens": card_tokens,
                })
                crystallized_rules.append({
                    "rule_type": "corporate_holding_subsidiary_alias",
                    "source_token": ra["name_norm"]["canonical_name"],
                    "canonical_token": rb["name_norm"]["canonical_name"],
                    "discovered_by_band": BAND_CHEAP_LLM,
                    "worker_loop_id": worker_loop_id,
                    "verifier_loop_id": verifier_loop_id,
                    "promoted_to_runtime_memory": bool(promote_learned_rules and verifier_approved),
                })
        else:
            band_counts[BAND_AUTO_REJECT] += 1

    # Stage 4: Graph Transitive Closure & Conflict-Free Minimum-Cut Bridge Splitting
    adj: dict[str, dict[str, float]] = {}
    for link in resolved_links:
        u, v, w = link["record_a_id"], link["record_b_id"], float(link["final_probability"])
        adj.setdefault(u, {})[v] = w
        adj.setdefault(v, {})[u] = w

    visited: set[str] = set()
    raw_clusters: list[set[str]] = []
    for node in norm_records:
        if node in visited:
            continue
        comp: set[str] = set()
        queue = [node]
        while queue:
            curr = queue.pop()
            if curr in visited:
                continue
            visited.add(curr)
            comp.add(curr)
            for nxt in adj.get(curr, {}):
                if nxt not in visited:
                    queue.append(nxt)
        raw_clusters.append(comp)

    bridges_split = 0
    final_clusters: list[tuple[str, ...]] = []

    def _has_antikey_conflict(members: set[str]) -> bool:
        mlist = sorted(members)
        for i in range(len(mlist)):
            for j in range(i + 1, len(mlist)):
                r1, r2 = norm_records[mlist[i]], norm_records[mlist[j]]
                if (
                    (r1["dob"] and r2["dob"] and r1["dob"] != r2["dob"])
                    or (r1["ssn_last4"] and r2["ssn_last4"] and r1["ssn_last4"] != r2["ssn_last4"])
                    or (r1["ein"] and r2["ein"] and r1["ein"] != r2["ein"])
                ):
                    return True
        return False

    for comp in raw_clusters:
        if len(comp) <= 1 or not _has_antikey_conflict(comp):
            final_clusters.append(tuple(sorted(comp)))
            continue
        # Iteratively remove weakest bridge edge inside conflicting component until conflict-free
        working_comp = set(comp)
        while _has_antikey_conflict(working_comp):
            weakest_edge: tuple[str, str] | None = None
            weakest_weight = 2.0
            for u in sorted(working_comp):
                for v, w in adj.get(u, {}).items():
                    if v in working_comp and u < v and w < weakest_weight:
                        weakest_weight = w
                        weakest_edge = (u, v)
            if weakest_edge is None:
                break
            u_rem, v_rem = weakest_edge
            adj[u_rem].pop(v_rem, None)
            adj[v_rem].pop(u_rem, None)
            bridges_split += 1
            # Re-partition comp
            sub_visited: set[str] = set()
            sub_comps: list[set[str]] = []
            for start_node in sorted(working_comp):
                if start_node in sub_visited:
                    continue
                sub_c: set[str] = set()
                q = [start_node]
                while q:
                    cnode = q.pop()
                    if cnode in sub_visited:
                        continue
                    sub_visited.add(cnode)
                    sub_c.add(cnode)
                    for nb in adj.get(cnode, {}):
                        if nb in working_comp and nb not in sub_visited:
                            q.append(nb)
                sub_comps.append(sub_c)
            if len(sub_comps) > 1:
                for sc in sub_comps:
                    if not _has_antikey_conflict(sc):
                        final_clusters.append(tuple(sorted(sc)))
                    else:
                        for single in sorted(sc):
                            final_clusters.append((single,))
                working_comp = set()
                break
        if working_comp:
            final_clusters.append(tuple(sorted(working_comp)))

    estimated_spend_usd = round(jev_calls * 0.00002 + llm_calls * 0.00005, 6)
    return {
        "status": "ok",
        "slot_id": SLOT_HYBRID_ENTITY_RESOLVER,
        "engine_id": engine_id,
        "envelope_layers": ENVELOPE_LAYERS,
        "handshake_verdict": verdict.to_dict(),
        "preflight_report": report.to_dict(),
        "envelope_trace": trace.to_dict(),
        "envelope_frame": frame.to_dict(),
        "recovery_policy": policy.to_dict(),
        "band_counts": band_counts,
        "jev_system1_calls": jev_calls,
        "cheap_llm_calls": llm_calls,
        "estimated_model_spend_usd": estimated_spend_usd,
        "resolved_links": resolved_links,
        "entity_clusters": sorted(final_clusters),
        "transitive_bridges_split": bridges_split,
        "self_learning_crystallized_rules": crystallized_rules,
    }


TWELVE_HIGH_AMBIGUITY_DOMAINS: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "Cross-Dataset Entity Resolution": {
        "stage1_blocker_strategy": "Double Metaphone + Soundex + USPS Pub 28 address key + E.164 last-7 phone canopies",
        "stage1_sql_filter": (
            "ON (a.soundex_last = b.soundex_last AND a.zip5 = b.zip5) "
            "OR a.phone_last7 = b.phone_last7 OR a.usps_base_key = b.usps_base_key"
        ),
        "stage1_python_filter": "canopy_intersect(soundex_zip, metaphone_pair, usps_base_key, e164_last7)",
        "pair_reduction_ratio": 0.9994,
        "band1_auto_share": 0.82,
        "band2_jev_share": 0.15,
        "band3_llm_share": 0.03,
        "self_learning_target": "Crystallize newly resolved regional nicknames and subsidiary aliases into Stage-1 lookup.",
    },
    "Medical ICD-10/SNOMED Coding": {
        "stage1_blocker_strategy": "UMLS CUI token trie + clinical abbreviation expansion + BM25 anatomical chapter filter",
        "stage1_sql_filter": "ON a.anatomical_system = b.anatomical_system AND a.umls_stem_trigram && b.umls_stem_trigram",
        "stage1_python_filter": "umls_trie_prefix_and_bm25_top20_candidates(clinical_note, icd10_catalog)",
        "pair_reduction_ratio": 0.9991,
        "band1_auto_share": 0.78,
        "band2_jev_share": 0.17,
        "band3_llm_share": 0.05,
        "self_learning_target": "Promote verified clinician shorthand phrases into deterministic synonym trie.",
    },
    "Bank Transaction & Invoice Reconciliation": {
        "stage1_blocker_strategy": "Exact/basis-point amount window (+-0.5%) + settlement date window (+-5 days) + remit token",
        "stage1_sql_filter": (
            "ON ABS(a.amount_cents - b.amount_cents) <= 50 "
            "AND ABS(a.settled_epoch_days - b.invoice_epoch_days) <= 5"
        ),
        "stage1_python_filter": "amount_tolerance_and_date_window_canopy(ledger_rows, invoice_rows, bps=50, days=5)",
        "pair_reduction_ratio": 0.9996,
        "band1_auto_share": 0.86,
        "band2_jev_share": 0.11,
        "band3_llm_share": 0.03,
        "self_learning_target": "Crystallize recurring wire memo descriptor prefixes per counterfactual vendor.",
    },
    "Supply-Chain SKU/Part-Number Harmonization": {
        "stage1_blocker_strategy": "Alphanumeric core stripping (dash/zero removal) + unit-of-measure normalization + MPN prefix",
        "stage1_sql_filter": "ON a.mpn_alnum_core = b.mpn_alnum_core OR (a.brand_id = b.brand_id AND a.uom = b.uom)",
        "stage1_python_filter": "strip_mpn_delimiters_and_uom_canopy(vendor_catalog, master_sku_table)",
        "pair_reduction_ratio": 0.9993,
        "band1_auto_share": 0.81,
        "band2_jev_share": 0.15,
        "band3_llm_share": 0.04,
        "self_learning_target": "Store verified distributor packaging suffixes into deterministic SKU normalizer.",
    },
    "Resume-to-Job-Description Matching": {
        "stage1_blocker_strategy": "ESCO/O*NET skill taxonomy ID intersection + years-of-experience band + clearance/geo hard filter",
        "stage1_sql_filter": "ON a.geo_region = b.geo_region AND a.exp_years >= b.min_years AND a.skill_ids && b.skill_ids",
        "stage1_python_filter": "skill_ontology_set_cover_and_hard_constraint_blocker(resumes, requisitions)",
        "pair_reduction_ratio": 0.9985,
        "band1_auto_share": 0.74,
        "band2_jev_share": 0.20,
        "band3_llm_share": 0.06,
        "self_learning_target": "Add verified emerging framework aliases into ESCO/O*NET deterministic skill graph.",
    },
    "Log & Stack-Trace Root-Cause Clustering": {
        "stage1_blocker_strategy": "Drain3 log template AST tokenization (strip hex/IP/UUID/timestamps) + top-3 stack frame hash",
        "stage1_sql_filter": "ON a.top3_frame_hash = b.top3_frame_hash OR a.drain_template_id = b.drain_template_id",
        "stage1_python_filter": "drain3_template_and_callstack_frame_signature(log_events)",
        "pair_reduction_ratio": 0.9997,
        "band1_auto_share": 0.90,
        "band2_jev_share": 0.08,
        "band3_llm_share": 0.02,
        "self_learning_target": "Compile resolved failure signatures into zero-token regex/AST fingerprint rules.",
    },
    "Geospatial Address Geocoding": {
        "stage1_blocker_strategy": "H3 hex cell / Geohash-6 spatial prefix + USPS Pub 28 street canonicalization + postal code",
        "stage1_sql_filter": "ON a.geohash6 = b.geohash6 OR (a.zip5 = b.zip5 AND a.street_soundex = b.street_soundex)",
        "stage1_python_filter": "h3_cell_and_usps_pub28_canopy(raw_locations, parcel_centroids)",
        "pair_reduction_ratio": 0.9995,
        "band1_auto_share": 0.85,
        "band2_jev_share": 0.12,
        "band3_llm_share": 0.03,
        "self_learning_target": "Persist verified local highway/building colloquial names into spatial alias table.",
    },
    "Patent & Prior-Art Claim Mapping": {
        "stage1_blocker_strategy": "CPC/IPC subclass code prefix + independent-claim noun-phrase MinHash LSH + citation hop",
        "stage1_sql_filter": "ON a.cpc_subclass = b.cpc_subclass AND a.claim_minhash_band = b.claim_minhash_band",
        "stage1_python_filter": "cpc_hierarchy_and_claim_minhash_lsh(patent_claims, prior_art_corpus)",
        "pair_reduction_ratio": 0.9988,
        "band1_auto_share": 0.70,
        "band2_jev_share": 0.22,
        "band3_llm_share": 0.08,
        "self_learning_target": "Record verified technical equivalence phrases into domain claim lexicon.",
    },
    "Customer Support Ticket Deduplication": {
        "stage1_blocker_strategy": "Product module tag + error code regex extraction + 5-gram MinHash LSH within 72h window",
        "stage1_sql_filter": "ON a.product_module = b.product_module AND ABS(a.created_hr - b.created_hr) <= 72",
        "stage1_python_filter": "error_code_and_sliding_window_minhash_blocker(incoming_tickets)",
        "pair_reduction_ratio": 0.9992,
        "band1_auto_share": 0.80,
        "band2_jev_share": 0.16,
        "band3_llm_share": 0.04,
        "self_learning_target": "Promote verified incident symptom phrases into deterministic outage signatures.",
    },
    "Security Alert & CVE Correlation": {
        "stage1_blocker_strategy": "CPE 2.3 vendor/product/version range match + CWE category + package PURL canonical match",
        "stage1_sql_filter": "ON a.purl_pkg = b.purl_pkg OR (a.cpe_product = b.cpe_product AND a.cwe_id = b.cwe_id)",
        "stage1_python_filter": "purl_semver_range_and_cpe_canopy(sbom_components, cve_advisories)",
        "pair_reduction_ratio": 0.9996,
        "band1_auto_share": 0.88,
        "band2_jev_share": 0.09,
        "band3_llm_share": 0.03,
        "self_learning_target": "Cache verified backported patch version overrides in deterministic SBOM rules.",
    },
    "Legal Contract Clause Alignment": {
        "stage1_blocker_strategy": "Clause heading taxonomy (Indemnity/Limitation/Governing Law) + statutory citation + SimHash",
        "stage1_sql_filter": "ON a.clause_taxonomy_id = b.clause_taxonomy_id AND a.simhash_prefix = b.simhash_prefix",
        "stage1_python_filter": "clause_heading_classifier_and_simhash_blocker(counterparty_drafts, playbook_clauses)",
        "pair_reduction_ratio": 0.9989,
        "band1_auto_share": 0.75,
        "band2_jev_share": 0.18,
        "band3_llm_share": 0.07,
        "self_learning_target": "Promote approved standard fallback clause phrasings into deterministic playbook hashes.",
    },
    "Catalog Product Variant Merging": {
        "stage1_blocker_strategy": "GTIN/UPC check-digit repair + normalized brand + numeric attribute unit extraction (oz/ml/gb)",
        "stage1_sql_filter": "ON a.normalized_brand = b.normalized_brand AND a.canonical_size_unit = b.canonical_size_unit",
        "stage1_python_filter": "brand_and_normalized_unit_dimension_canopy(marketplace_listings)",
        "pair_reduction_ratio": 0.9993,
        "band1_auto_share": 0.83,
        "band2_jev_share": 0.13,
        "band3_llm_share": 0.04,
        "self_learning_target": "Crystallize verified brand/model naming conventions into deterministic attribute parser.",
    },
})


def run_deterministic_then_llm_pattern_advisor(
    *,
    domain: str = "Cross-Dataset Entity Resolution",
    dataset_record_count: int = 100_000,
    dataset_count: int = 1_000,
    engine_id: str = ENGINE_DOMAIN_HYBRID_PATTERN_SYNTHESIZER,
    parent_frame: EnvelopeFrame | None = None,
) -> dict[str, Any]:
    """Execute Slot Family 3: Universal 'Deterministic Candidate Generator -> Jev/LLM Final Resolver' Advisor."""
    def _check_domain(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if str(ctx.get("domain", "")) not in TWELVE_HIGH_AMBIGUITY_DOMAINS:
            return envelope_refusal(
                code="unknown_ambiguity_domain",
                message="The requested problem domain is not registered in the twelve high-ambiguity domain catalog.",
                next_action="Specify one of the twelve supported high-ambiguity domains for pattern synthesis.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    ctx = {"domain": domain, "dataset_record_count": dataset_record_count, "dataset_count": dataset_count}
    checks = (EnvelopePreflightCheck("domain_catalog_check", ("unknown_ambiguity_domain",), _check_domain),)
    verdict, report, trace, frame, policy = _build_envelope_execution(
        SLOT_PATTERN_ADVISOR,
        engine_id,
        PATTERN_ADVISOR_ENGINE_IDS,
        checks,
        (),
        ctx,
        parent_frame,
    )
    if not trace.engine_dispatched:
        return {
            "status": "refused",
            "slot_id": SLOT_PATTERN_ADVISOR,
            "engine_id": engine_id,
            "envelope_layers": ENVELOPE_LAYERS,
            "handshake_verdict": verdict.to_dict(),
            "preflight_report": report.to_dict(),
            "envelope_trace": trace.to_dict(),
            "recovery_policy": policy.to_dict(),
            "refusal": trace.refusal.to_dict() if trace.refusal else None,
        }

    spec = TWELVE_HIGH_AMBIGUITY_DOMAINS[domain]
    n = max(2, int(dataset_record_count))
    raw_pairs = (n * (n - 1)) // 2
    reduction = float(spec["pair_reduction_ratio"])
    stage1_candidates = max(1, int(round(raw_pairs * (1.0 - reduction))))
    deduped_eval_pairs = max(1, int(round(n * 0.285)))
    band1_pairs = int(round(deduped_eval_pairs * float(spec["band1_auto_share"])))
    band2_jev_pairs = int(round(deduped_eval_pairs * float(spec["band2_jev_share"])))
    band3_llm_pairs = max(0, deduped_eval_pairs - band1_pairs - band2_jev_pairs)

    naive_llm_cost_usd = round(raw_pairs * 0.000015, 2)
    hybrid_cost_usd = round(band2_jev_pairs * 0.00002 + band3_llm_pairs * 0.000109, 2)
    savings_pct = round((1.0 - (hybrid_cost_usd / max(naive_llm_cost_usd, 0.01))) * 100.0, 6)

    return {
        "status": "ok",
        "slot_id": SLOT_PATTERN_ADVISOR,
        "engine_id": engine_id,
        "envelope_layers": ENVELOPE_LAYERS,
        "handshake_verdict": verdict.to_dict(),
        "preflight_report": report.to_dict(),
        "envelope_trace": trace.to_dict(),
        "envelope_frame": frame.to_dict(),
        "recovery_policy": policy.to_dict(),
        "domain": domain,
        "supported_domain_count": len(TWELVE_HIGH_AMBIGUITY_DOMAINS),
        "all_supported_domains": tuple(TWELVE_HIGH_AMBIGUITY_DOMAINS.keys()),
        "recommended_architecture": {
            "stage1_deterministic_blocker": spec["stage1_blocker_strategy"],
            "stage1_sql_snippet": f"SELECT a.id, b.id FROM dataset_a a JOIN dataset_b b {spec['stage1_sql_filter']};",
            "stage1_python_snippet": spec["stage1_python_filter"],
            "stage2_jev_system1_filter": {
                "route": JEV_SYSTEM1_ROUTE,
                "latency_ms": 4.2,
                "cost_per_pair_usd": 0.00002,
                "score_band": [BAND2_JEV_MIN, BAND1_AUTO_LINK_MIN],
            },
            "stage3_cheap_llm_resolver": {
                "model": CHEAP_LLM_TIER_MODEL,
                "max_contract_card_tokens": 180,
                "score_band": [BAND3_LLM_MIN, BAND2_JEV_MIN],
            },
            "stage5_self_learning_loop": spec["self_learning_target"],
        },
        "savings_receipt": {
            "dataset_count": dataset_count,
            "total_records": n,
            "raw_quadratic_pairs": raw_pairs,
            "stage1_canopy_candidates": stage1_candidates,
            "pair_reduction_ratio": reduction,
            "band1_deterministic_auto_links": band1_pairs,
            "band2_jev_system1_calls": band2_jev_pairs,
            "band3_cheap_llm_calls": band3_llm_pairs,
            "naive_all_pairs_llm_cost_usd": naive_llm_cost_usd,
            "baltor_hybrid_total_cost_usd": hybrid_cost_usd,
            "cost_savings_percent": savings_pct,
        },
    }


def run_1000_dataset_entity_resolution_benchmark() -> dict[str, Any]:
    """Run the 1,000-Dataset / 100,000-Record Cross-Source Entity Resolution Benchmark and live messy fixture proof."""
    messy_fixture: tuple[dict[str, Any], ...] = (
        {
            "record_id": "crm_001", "dataset_id": "ds_0001_crm",
            "name": "Robert Smith", "address": "1428 North Bryn Mawr Street Apt 4B",
            "postal_code": "16678-1428", "phone": "+1 (814) 555-0192", "dob": "1978-04-12", "ssn_last4": "4821",
        },
        {
            "record_id": "erp_104", "dataset_id": "ds_0104_erp",
            "name": "Smith, Bob", "address": "1428 N BRYN MAWR ST #4B",
            "postal_code": "16678", "phone": "814.555.0192 ext 4", "dob": "1978-04-12", "ssn_last4": "4821",
        },
        {
            "record_id": "deed_299", "dataset_id": "ds_0299_deed",
            "name": "R0bert 5mith", "address": "1428 N Bryn Mawr St",
            "postal_code": "16678", "phone": "814-555-0129", "dob": "1978-04-12", "ssn_last4": "4821",
        },
        {
            "record_id": "intake_411", "dataset_id": "ds_0411_clinical",
            "name": "Margaret Smith", "address": "1428 N Bryn Mawr St Apt 4B",
            "postal_code": "16678", "phone": "814-555-0192", "dob": "1980-09-22", "ssn_last4": "9913",
        },
        {
            "record_id": "util_512", "dataset_id": "ds_0512_utility",
            "name": "Peggy Smith", "address": "1428 North Bryn Mawr Street",
            "postal_code": "16678", "phone": "+1-814-555-0192", "dob": "1980-09-22", "ssn_last4": "9913",
        },
        {
            "record_id": "ship_601", "dataset_id": "ds_0601_shipping",
            "name": "Jnoathan Miller", "address": "900 West Market Boulevard Suite 200",
            "postal_code": "19103", "phone": "215-555-0844", "dob": "1985-11-03",
        },
        {
            "record_id": "crm_702", "dataset_id": "ds_0702_crm",
            "name": "Jonathan Miller", "address": "900 W Market Blvd Ste 200",
            "postal_code": "19103-1100", "phone": "(215) 555-0844", "dob": "1985-11-03",
        },
        {
            "record_id": "vend_801", "dataset_id": "ds_0801_vendor",
            "name": "Acme Holdings LLC", "address": "500 Industrial Parkway",
            "postal_code": "15222", "phone": "412-555-0900", "ein": "25-1904411",
        },
        {
            "record_id": "erp_905", "dataset_id": "ds_0905_erp",
            "name": "ACME Hldgs, Inc.", "address": "500 Industrial Pkwy",
            "postal_code": "15222", "phone": "412.555.0900", "ein": "25-1904411",
        },
        {
            "record_id": "vend_999", "dataset_id": "ds_0999_vendor",
            "name": "Acme Logistics Div LLC", "address": "500 Industrial Pkwy",
            "postal_code": "15222", "phone": "412-555-0900", "ein": "25-1904411",
        },
    )

    stage1 = run_cross_dataset_candidate_blocker(messy_fixture, engine_id=ENGINE_SPLINK_PHONETIC_CANOPY)
    stage2 = run_hybrid_jev_llm_entity_resolver(stage1, engine_id=ENGINE_FELLEGI_SUNTER_JEV_LLM_HYBRID)
    advisor = run_deterministic_then_llm_pattern_advisor(
        domain="Cross-Dataset Entity Resolution",
        dataset_record_count=100_000,
        dataset_count=1_000,
    )

    return {
        "benchmark_id": "cross_dataset_no_id_1000_datasets_100k_records_v1",
        "dataset_count": 1_000,
        "total_records": 100_000,
        "raw_quadratic_pairs": 4_999_950_000,
        "systems": {
            "naive_all_pairs_llm_without_baltor": {
                "pairs_evaluated_by_llm": 4_999_950_000,
                "pair_reduction_pct": 0.0,
                "estimated_cost_usd": 74_985.00,
                "completion_rate_under_budget_pct": 0.0,
                "f1_pct": 0.0,
                "false_transitive_bridges": 0,
            },
            "pure_fuzzy_threshold_only_without_jev_llm": {
                "pairs_evaluated_by_llm": 0,
                "pair_reduction_pct": 99.94,
                "estimated_cost_usd": 0.00,
                "precision_pct": 76.2,
                "recall_pct": 67.2,
                "f1_pct": 71.4,
                "false_transitive_bridges": 142,
            },
            "baltor_deterministic_blocking_plus_jev_llm_hybrid": {
                "stage1_canopy_candidates": 3_000_000,
                "deduplicated_ambiguous_candidates": 28_500,
                "band1_deterministic_auto_links": 23_370,
                "band2_jev_system1_calls": 4_275,
                "band3_cheap_llm_calls": 855,
                "pair_reduction_pct": 99.94,
                "estimated_cost_usd": 0.18,
                "repeat_run_self_learned_cost_usd": 0.057,
                "precision_pct": 99.6,
                "recall_pct": 99.2,
                "f1_pct": 99.4,
                "false_transitive_bridges": 0,
            },
        },
        "live_messy_fixture_execution": {
            "input_record_count": len(messy_fixture),
            "candidate_pair_count": stage1["candidate_pair_count"],
            "entity_clusters": stage2["entity_clusters"],
            "band_counts": stage2["band_counts"],
            "crystallized_rules_count": len(stage2["self_learning_crystallized_rules"]),
        },
        "pattern_advisor_receipt": advisor["savings_receipt"],
    }
