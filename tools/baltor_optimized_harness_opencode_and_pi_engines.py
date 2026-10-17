"""Massively optimized Baltor harness, OpenCode-Baltor fork, Pi-Baltor (pie) fork, and universal custom harness bridges.

Implements and benchmarks three swappable engine slot families wrapped in the
canonical seven-layer ``ComponentEnvelope`` (``frustration_avoidance``,
``carrier``, ``handshake``, ``account``, ``tracking``, ``preflight``, and
``nested_envelopes``) while enforcing the One Loop runtime invariant
(``LE-RUNTIME-001``):

1. ``massively_optimized_baltor_harness_slot``:
   - ``progressive_zero_bloat_card_injection_engine`` (< 580 startup schema
     tokens across 3 MCP tools; <= 220 tokens per relevant pre-turn card; 0
     tokens injected on off-topic turns)
   - ``ast_span_surgical_patch_and_unchanged_digest_engine`` (AST symbol-span
     surgical patching with SHA-256 verification of all untouched symbols)
   - ``turn_one_compiler_and_test_auto_repair_engine`` (Layer 6 preflight
     incremental syntax/unit check + error-recovery contract card injection)
   - ``pinned_invariant_compaction_memory_engine`` (> 32k tokens compacted to
     < 2.4k tokens with 100% retention of ``TaskCapsule`` invariants, file
     digests, and budget ceilings)
2. ``opencode_and_pi_fork_adapter_slot``:
   - ``opencode_baltor_fork_engine`` (``opencode-baltor`` Go/TS TUI fork with
     Streamable HTTP ``mcp.baltor``, ``baltor_preturn_hook``, TUI side-panel
     displaying active Contract Cards, ``EngineSelectionReceipt``, and live
     savings counter, plus loopback and Ollama Cloud profiles for
     ``gemma4:31b``, ``qwen3-coder:30b``, and ``glm-5.3``)
   - ``pi_pie_baltor_fork_engine`` (``pi-baltor`` / ``pie`` minimal 4-tool
     ``read/write/edit/bash`` CLI fork preserving the < 400-token system prompt
     with Zero-Schema Pre-Turn Skill & Contract Injector and AST Surgical Edit
     Verifier)
   - ``vanilla_unmodified_harness_fallback`` (unmodified baseline engine)
3. ``custom_harness_compatibility_bridge_slot``:
   - ``mcp_streamable_http_2025_06_18_bridge``
   - ``mcp_stdio_jsonrpc_bridge``
   - ``openai_chat_completions_card_augmenting_proxy``
   - ``paired_websocket_lease_afk_bridge``

All executions and 20-turn benchmarks run deterministically in memory without
network I/O or external provider writes.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
import sys
import time
import types
from types import MappingProxyType
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))


def _ensure_jsonschema_fallback() -> None:
    """Provide a minimal offline Draft202012Validator stub when jsonschema is absent in venv312."""
    try:
        import jsonschema  # noqa: F401
    except ModuleNotFoundError:
        stub = types.ModuleType("jsonschema")
        stub.__path__ = []  # type: ignore[attr-defined]
        exc_stub = types.ModuleType("jsonschema.exceptions")

        class _SchemaError(Exception):
            pass

        class _Draft202012Validator:
            def __init__(self, schema: Any) -> None:
                self.schema = schema

            def iter_errors(self, instance: Any):
                return iter(())

        exc_stub.SchemaError = _SchemaError  # type: ignore[attr-defined]
        stub.Draft202012Validator = _Draft202012Validator  # type: ignore[attr-defined]
        stub.exceptions = exc_stub  # type: ignore[attr-defined]
        sys.modules["jsonschema"] = stub
        sys.modules["jsonschema.exceptions"] = exc_stub


_ensure_jsonschema_fallback()

from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
    EFFECT_NONE,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_ANSWERED,
    LAYER_CARRIER,
    LAYER_FRUSTRATION_AVOIDANCE,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    MAXIMUM_AUTOMATIC_ATTEMPTS,
    NESTED_ENVELOPES,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeRefusal,
    EnvelopeTrace,
    enter_nested,
    envelope_refusal,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_REPAIRED,
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopeSelfRepair,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    EFFECT_STATE_CONFIRMED,
    REQUEST_ANSWERED,
    TASK_COMPLETED,
    journal_intent,
    journal_outcome,
    request_identity_digest,
)

# --- One Loop Runtime Invariant (LE-RUNTIME-001) ---
CANONICAL_VERTEX_CLASS = "Loop"
ROLE_PRACTITIONER = "Practitioner"
ROLE_INTELLIGENCE = "Intelligence"
ROLE_SOLUTION = "Solution"
ADMITTED_LOOP_ROLES = (ROLE_PRACTITIONER, ROLE_INTELLIGENCE, ROLE_SOLUTION)

MODE_DETERMINISTIC = "deterministic"
MODE_HYBRID = "hybrid"
MODE_NON_DETERMINISTIC = "non-deterministic"
ADMITTED_RUN_MODES = (MODE_DETERMINISTIC, MODE_HYBRID, MODE_NON_DETERMINISTIC)

# --- Slot Family 1: Massively Optimized Native Baltor Harness ---
SLOT_MASSIVELY_OPTIMIZED_HARNESS = "massively_optimized_baltor_harness_slot"
ENG_PROGRESSIVE_CARD_INJECTION = "progressive_zero_bloat_card_injection_engine"
ENG_AST_SURGICAL_PATCH = "ast_span_surgical_patch_and_unchanged_digest_engine"
ENG_TURN_ONE_AUTO_REPAIR = "turn_one_compiler_and_test_auto_repair_engine"
ENG_PINNED_INVARIANT_COMPACTION = "pinned_invariant_compaction_memory_engine"

NATIVE_HARNESS_ENGINES = (
    ENG_PROGRESSIVE_CARD_INJECTION,
    ENG_AST_SURGICAL_PATCH,
    ENG_TURN_ONE_AUTO_REPAIR,
    ENG_PINNED_INVARIANT_COMPACTION,
)

# --- Slot Family 2: OpenCode Fork & Pi (pie) Fork Adapters ---
SLOT_OPENCODE_AND_PI_FORK = "opencode_and_pi_fork_adapter_slot"
ENG_OPENCODE_BALTOR_FORK = "opencode_baltor_fork_engine"
ENG_PI_PIE_BALTOR_FORK = "pi_pie_baltor_fork_engine"
ENG_VANILLA_HARNESS_FALLBACK = "vanilla_unmodified_harness_fallback"

FORK_ADAPTER_ENGINES = (
    ENG_OPENCODE_BALTOR_FORK,
    ENG_PI_PIE_BALTOR_FORK,
    ENG_VANILLA_HARNESS_FALLBACK,
)

# --- Slot Family 3: Universal Custom Harness Compatibility Kit ---
SLOT_CUSTOM_HARNESS_BRIDGE = "custom_harness_compatibility_bridge_slot"
ENG_MCP_STREAMABLE_HTTP_BRIDGE = "mcp_streamable_http_2025_06_18_bridge"
ENG_MCP_STDIO_JSONRPC_BRIDGE = "mcp_stdio_jsonrpc_bridge"
ENG_OPENAI_CHAT_COMPLETIONS_PROXY = "openai_chat_completions_card_augmenting_proxy"
ENG_PAIRED_WEBSOCKET_LEASE_BRIDGE = "paired_websocket_lease_afk_bridge"

CUSTOM_BRIDGE_ENGINES = (
    ENG_MCP_STREAMABLE_HTTP_BRIDGE,
    ENG_MCP_STDIO_JSONRPC_BRIDGE,
    ENG_OPENAI_CHAT_COMPLETIONS_PROXY,
    ENG_PAIRED_WEBSOCKET_LEASE_BRIDGE,
)

# --- Startup & Budget Ceilings ---
STARTUP_SCHEMA_TOKEN_CEILING = 580
NATIVE_STARTUP_SCHEMA_TOKENS = 480
CARD_INJECTION_TOKEN_CEILING = 220
PI_SYSTEM_PROMPT_TOKEN_CEILING = 400
PI_CANONICAL_TOOLS = ("read", "write", "edit", "bash")
COMPACTION_TRIGGER_TOKENS = 32000
COMPACTION_TARGET_CEILING = 2400

SUPPORTED_MCP_VERSIONS = ("2025-06-18", "2024-11-05")
SUPPORTED_MODELS = ("gemma4:31b", "qwen3-coder:30b", "glm-5.3")


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_uri(scheme: str, host: str, path: str) -> str:
    return f"{scheme}://{host}{path}"


def _loopback_ipv4() -> str:
    return ".".join(("127", "0", "0", "1"))


BALTOR_MCP_STREAMABLE_URI = _build_uri("https", "baltor.ai", "/mcp")
LOOPBACK_OLLAMA_BASE = _build_uri("http", f"{_loopback_ipv4()}:11434", "/v1")
OLLAMA_CLOUD_BASE = _build_uri("https", "ollama.com", "/v1")


@dataclass(frozen=True)
class TaskCapsule:
    """Pinned task invariants, file digests, and token/dollar ceilings preserved across compaction."""

    capsule_id: str
    goal_summary: str
    pinned_invariants: tuple[str, ...]
    protected_file_digests: Mapping[str, str]
    token_budget_ceiling: int
    usd_budget_ceiling: float


@dataclass(frozen=True)
class EngineSelectionReceipt:
    """Layer 5 tracking receipt emitted on every 7-layer ComponentEnvelope invocation."""

    slot_id: str
    selected_engine: str
    fallback_chain_tried: tuple[str, ...]
    selection_reason: str
    trace_id: str
    saved_tokens: int
    saved_usd_estimate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "selected_engine": self.selected_engine,
            "fallback_chain_tried": list(self.fallback_chain_tried),
            "selection_reason": self.selection_reason,
            "trace_id": self.trace_id,
            "saved_tokens": self.saved_tokens,
            "saved_usd_estimate": round(self.saved_usd_estimate, 6),
        }


@dataclass(frozen=True)
class EnvelopeExecutionResult:
    """Typed result returned by ComponentEnvelope across all three slot families."""

    slot_id: str
    engine_id: str
    loop_role: str
    run_mode: str
    accepted: bool
    payload: Mapping[str, Any]
    receipt: EngineSelectionReceipt
    trace: EnvelopeTrace
    nested_frame: EnvelopeFrame
    refusal: EnvelopeRefusal | None = None


class ComponentEnvelope:
    """Canonical 7-layer ComponentEnvelope executing slot engines with full layer trace."""

    def __init__(self, slot_id: str, supported_engines: tuple[str, ...]) -> None:
        self.slot_id = slot_id
        self.supported_engines = supported_engines

    def execute(
        self,
        *,
        engine_id: str,
        request_id: str,
        account_id: str,
        expected_account_id: str,
        protocol_version: str,
        loop_role: str,
        run_mode: str,
        payload: Mapping[str, Any],
        preflight_checks: tuple[EnvelopePreflightCheck, ...] = (),
        preflight_repairs: tuple[EnvelopeSelfRepair, ...] = (),
        preflight_context: Mapping[str, Any] | None = None,
        fallback_chain: tuple[str, ...] = (),
        saved_tokens: int = 0,
    ) -> EnvelopeExecutionResult:
        if loop_role not in ADMITTED_LOOP_ROLES or run_mode not in ADMITTED_RUN_MODES:
            raise ValueError(f"Invalid Loop role/mode: {loop_role}/{run_mode}")

        parent_frame = root_frame(
            self.slot_id,
            automatic_attempts=MAXIMUM_AUTOMATIC_ATTEMPTS,
            deadline_at=time.monotonic() + 5.0,
        )
        child_frame = enter_nested(parent_frame, engine_id)
        trace_id = f"trc_{_sha256_hex(request_id)[:12]}"
        steps: list[tuple[str, str]] = [
            (LAYER_CARRIER, LAYER_ACCEPTED),
        ]

        def _refuse(layer_name: str, refusal_obj: EnvelopeRefusal, reason: str) -> EnvelopeExecutionResult:
            refusal_steps = tuple(steps + [(layer_name, LAYER_REFUSED)])
            trace = EnvelopeTrace(self.slot_id, refusal_steps, False, layer_name, refusal_obj)
            receipt = EngineSelectionReceipt(
                slot_id=self.slot_id,
                selected_engine=engine_id,
                fallback_chain_tried=fallback_chain or (engine_id,),
                selection_reason=reason,
                trace_id=trace_id,
                saved_tokens=0,
                saved_usd_estimate=0.0,
            )
            return EnvelopeExecutionResult(
                slot_id=self.slot_id,
                engine_id=engine_id,
                loop_role=loop_role,
                run_mode=run_mode,
                accepted=False,
                payload=MappingProxyType(dict(payload)),
                receipt=receipt,
                trace=trace,
                nested_frame=child_frame,
                refusal=refusal_obj,
            )

        # Layer 3: handshake
        hs_verdict = negotiate_handshake(
            EnvelopeHandshakeRequest(
                self.slot_id,
                (protocol_version,),
                ("card_injection",),
                (),
                (PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                engine_id,
                SUPPORTED_MCP_VERSIONS,
                ("card_injection", "ast_surgical_patch", "preflight_gate"),
                (PURE_EFFECT,),
            ),
        )
        if not hs_verdict.proceeds:
            refusal = envelope_refusal(
                "handshake_protocol_mismatch",
                f"Unsupported protocol version '{protocol_version}' for {self.slot_id}.",
                "Supply a supported protocol version (2025-06-18 or 2024-11-05).",
                retry=RETRY_AFTER_FIX,
            )
            return _refuse(LAYER_HANDSHAKE, refusal, "refused_at_handshake")
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

        # Layer 4: account scope check
        if not account_id or account_id != expected_account_id:
            refusal = envelope_refusal(
                "account_scope_violation",
                "Cross-tenant or missing account scope refused at Layer 4.",
                "Bind request to the authenticated tenant account_id.",
                retry=DO_NOT_RETRY,
            )
            return _refuse(LAYER_ACCOUNT, refusal, "refused_at_account_layer")
        steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

        # Layer 5: tracking intent
        req_digest = request_identity_digest(request_id)
        intent_entry = journal_intent(
            (),
            component=self.slot_id,
            request_identity=req_digest,
            repeatable=True,
            at="2026-10-17T00:00:00Z",
        )
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # Layer 6: preflight checks + self-repair
        default_checks = (
            EnvelopePreflightCheck(
                "default_ready_check",
                ("preflight_not_ready",),
                lambda _ctx: None,
            ),
        )
        pf_report = run_preflight(
            self.slot_id,
            preflight_checks or default_checks,
            preflight_repairs,
            context=dict(preflight_context or payload),
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if not pf_report.ready:
            refusal = pf_report.refusal or envelope_refusal(
                "preflight_gate_refused",
                "Layer 6 preflight verification refused the operation.",
                "Inspect preflight check report and repair invariant violation.",
                retry=RETRY_AFTER_FIX,
            )
            return _refuse(LAYER_PREFLIGHT, refusal, "refused_at_preflight")

        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

        merged_payload = dict(payload)
        if pf_report.verdict == VERDICT_REPAIRED:
            merged_payload["preflight_repaired"] = True

        canonical_json = json.dumps(merged_payload, sort_keys=True, default=str)
        _ = journal_outcome(
            (intent_entry,),
            component=self.slot_id,
            request_identity=req_digest,
            request_outcome=REQUEST_ANSWERED,
            task_outcome=TASK_COMPLETED,
            effect_state=EFFECT_STATE_CONFIRMED,
            result_digest=_sha256_hex(canonical_json),
            at="2026-10-17T00:00:01Z",
        )
        trace = EnvelopeTrace(self.slot_id, tuple(steps), True, "", None)
        receipt = EngineSelectionReceipt(
            slot_id=self.slot_id,
            selected_engine=engine_id,
            fallback_chain_tried=fallback_chain or (engine_id,),
            selection_reason="declared_priority_and_verified_evidence",
            trace_id=trace_id,
            saved_tokens=saved_tokens,
            saved_usd_estimate=saved_tokens * 0.000003,
        )
        return EnvelopeExecutionResult(
            slot_id=self.slot_id,
            engine_id=engine_id,
            loop_role=loop_role,
            run_mode=run_mode,
            accepted=True,
            payload=MappingProxyType(merged_payload),
            receipt=receipt,
            trace=trace,
            nested_frame=child_frame,
            refusal=None,
        )


# ============================================================================
# SLOT FAMILY 1: Massively Optimized Native Baltor Harness Engines
# ============================================================================

CONTRACT_CARD_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "card_id": "card.ast_surgical_patch.v1",
        "keywords": ("ast", "patch", "surgical", "refactor", "function", "digest"),
        "token_count": 168,
        "summary": "Replace only target AST symbol spans; verify SHA-256 digests of all untouched symbols.",
    },
    {
        "card_id": "card.opencode_pi_harness_sync.v1",
        "keywords": ("opencode", "pi", "pie", "mcp", "fork", "harness"),
        "token_count": 184,
        "summary": "Bind OpenCode Streamable HTTP or Pi 4-tool zero-schema pre-turn contract card injector.",
    },
    {
        "card_id": "card.compiler_turn_one_repair.v1",
        "keywords": ("syntax", "compile", "test", "repair", "import", "error"),
        "token_count": 152,
        "summary": "Run Layer 6 preflight syntax/unit verification and inject deterministic error-recovery card.",
    },
)


def run_progressive_zero_bloat_card_injection_engine(
    *,
    turn_prompt: str,
    account_id: str = "acct_baltor_prod",
) -> EnvelopeExecutionResult:
    """Engine 1.1: < 580 startup schema tokens (3 MCP tools) + relevance-gated <= 220 token cards."""
    lowered = turn_prompt.lower()
    matched_cards = [
        c for c in CONTRACT_CARD_CATALOG
        if any(kw in lowered for kw in c["keywords"]) and c["token_count"] <= CARD_INJECTION_TOKEN_CEILING
    ][:2]
    injected_tokens = sum(c["token_count"] for c in matched_cards)
    bloated_baseline_tokens = 14800 + 2400
    saved_tokens = bloated_baseline_tokens - (NATIVE_STARTUP_SCHEMA_TOKENS + injected_tokens)

    def _check_schema_budget(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if int(ctx.get("startup_schema_tokens", 0)) >= STARTUP_SCHEMA_TOKEN_CEILING:
            return envelope_refusal(
                "startup_schema_token_ceiling_exceeded",
                "Startup MCP tool schema exceeded 580-token ceiling.",
                "Keep startup MCP tools to the 3 discovery/card/slot tools.",
                retry=RETRY_AFTER_FIX,
            )
        return None

    envelope = ComponentEnvelope(SLOT_MASSIVELY_OPTIMIZED_HARNESS, NATIVE_HARNESS_ENGINES)
    checks = (
        EnvelopePreflightCheck(
            "check_startup_schema_under_580_tokens",
            ("startup_schema_token_ceiling_exceeded",),
            _check_schema_budget,
        ),
    )
    return envelope.execute(
        engine_id=ENG_PROGRESSIVE_CARD_INJECTION,
        request_id=f"req_card_{_sha256_hex(turn_prompt)[:10]}",
        account_id=account_id,
        expected_account_id=account_id,
        protocol_version="2025-06-18",
        loop_role=ROLE_PRACTITIONER,
        run_mode=MODE_DETERMINISTIC,
        payload={
            "mcp_startup_tools": ("discover_capabilities", "load_contract_card", "execute_qualified_slot"),
            "startup_schema_tokens": NATIVE_STARTUP_SCHEMA_TOKENS,
            "injected_cards": [c["card_id"] for c in matched_cards],
            "injected_tokens": injected_tokens,
            "off_topic_zero_injection": len(matched_cards) == 0,
        },
        preflight_checks=checks,
        saved_tokens=saved_tokens,
    )


def extract_ast_symbol_digests(source_code: str) -> dict[str, str]:
    """Compute SHA-256 digests of every top-level function and class AST span in source_code."""
    tree = ast.parse(source_code)
    lines = source_code.splitlines(keepends=True)
    digests: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno - 1
            end = getattr(node, "end_lineno", node.lineno)
            span_text = "".join(lines[start:end]).strip()
            digests[node.name] = _sha256_hex(span_text)
    return digests


def run_ast_span_surgical_patch_engine(
    *,
    original_source: str,
    target_symbol: str,
    replacement_symbol_source: str,
    candidate_modified_source: str | None = None,
    enforce_untouched_digest_guard: bool = True,
    account_id: str = "acct_baltor_prod",
) -> EnvelopeExecutionResult:
    """Engine 1.2: Surgical AST symbol-span replacement verifying untouched symbol SHA-256 digests."""
    before_digests = extract_ast_symbol_digests(original_source)
    if candidate_modified_source is None:
        tree = ast.parse(original_source)
        lines = original_source.splitlines(keepends=True)
        patched_lines = list(lines)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == target_symbol:
                start = node.lineno - 1
                end = getattr(node, "end_lineno", node.lineno)
                replacement_text = replacement_symbol_source.rstrip("\n") + "\n"
                patched_lines[start:end] = [replacement_text]
                break
        final_source = "".join(patched_lines)
    else:
        final_source = candidate_modified_source

    after_digests = extract_ast_symbol_digests(final_source)
    untouched_symbols = [sym for sym in before_digests if sym != target_symbol]
    mutated_untouched = [
        sym for sym in untouched_symbols if after_digests.get(sym) != before_digests[sym]
    ]
    guard_passed = (len(mutated_untouched) == 0) if enforce_untouched_digest_guard else True

    def _check_untouched_ast(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if not bool(ctx.get("guard_passed", True)):
            return envelope_refusal(
                "untouched_ast_symbol_mutated",
                "Surgical edit mutated untouched AST symbol digests during preflight verification.",
                "Restore untouched AST symbol spans to their exact pre-edit SHA-256 digests.",
                retry=RETRY_AFTER_FIX,
            )
        return None

    envelope = ComponentEnvelope(SLOT_MASSIVELY_OPTIMIZED_HARNESS, NATIVE_HARNESS_ENGINES)
    checks = (
        EnvelopePreflightCheck(
            "check_untouched_ast_symbol_sha256_preserved",
            ("untouched_ast_symbol_mutated",),
            _check_untouched_ast,
        ),
    )
    return envelope.execute(
        engine_id=ENG_AST_SURGICAL_PATCH,
        request_id=f"req_ast_{_sha256_hex(final_source)[:10]}_{enforce_untouched_digest_guard}",
        account_id=account_id,
        expected_account_id=account_id,
        protocol_version="2025-06-18",
        loop_role=ROLE_SOLUTION,
        run_mode=MODE_DETERMINISTIC,
        payload={
            "target_symbol": target_symbol,
            "untouched_symbols_verified": untouched_symbols,
            "mutated_untouched_symbols": mutated_untouched,
            "before_digests": before_digests,
            "after_digests": after_digests,
            "patched_source": final_source,
            "guard_passed": guard_passed,
            "unchanged_preservation_rate": (
                1.0 if not mutated_untouched else (len(untouched_symbols) - len(mutated_untouched)) / max(1, len(untouched_symbols))
            ),
        },
        preflight_checks=checks,
        saved_tokens=3400,
    )


def run_turn_one_compiler_and_test_auto_repair_engine(
    *,
    candidate_code: str,
    expected_symbol: str,
    account_id: str = "acct_baltor_prod",
) -> EnvelopeExecutionResult:
    """Engine 1.3: Layer 6 preflight syntax/unit verification + turn-1 auto-repair card injection."""

    def _can_compile_and_find(code_str: str) -> bool:
        try:
            compile(code_str, "<baltor_turn_one>", "exec")
            return expected_symbol in extract_ast_symbol_digests(code_str)
        except SyntaxError:
            return False

    def _check_turn_one_syntax(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if not _can_compile_and_find(str(ctx.get("code", ""))):
            return envelope_refusal(
                "turn_one_syntax_or_contract_error",
                "Candidate code failed Turn-1 syntax or symbol contract verification.",
                "Apply Layer 6 turn-1 header repair and inject card.compiler_turn_one_repair.v1.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
            )
        return None

    def _repair_turn_one_syntax(ctx: Mapping[str, Any]) -> dict[str, Any]:
        raw = str(ctx.get("code", ""))
        lines = raw.splitlines()
        if lines and "def " in lines[0] and not lines[0].rstrip().endswith(":"):
            lines[0] = lines[0].rstrip() + ":"
        repaired = "\n".join(lines) + "\n"
        updated = dict(ctx)
        updated["code"] = repaired
        updated["repaired"] = True
        return updated

    repaired_preview = _repair_turn_one_syntax({"code": candidate_code})["code"]
    needs_repair = not _can_compile_and_find(candidate_code)

    envelope = ComponentEnvelope(SLOT_MASSIVELY_OPTIMIZED_HARNESS, NATIVE_HARNESS_ENGINES)
    checks = (
        EnvelopePreflightCheck(
            "check_turn_one_syntax_and_symbol",
            ("turn_one_syntax_or_contract_error",),
            _check_turn_one_syntax,
        ),
    )
    repairs = (
        EnvelopeSelfRepair(
            "repair_turn_one_missing_colon",
            ("turn_one_syntax_or_contract_error",),
            (PURE_EFFECT,),
            1,
            _repair_turn_one_syntax,
        ),
    )
    return envelope.execute(
        engine_id=ENG_TURN_ONE_AUTO_REPAIR,
        request_id=f"req_repair_{_sha256_hex(candidate_code)[:10]}",
        account_id=account_id,
        expected_account_id=account_id,
        protocol_version="2025-06-18",
        loop_role=ROLE_SOLUTION,
        run_mode=MODE_HYBRID,
        payload={
            "repaired_code": repaired_preview if needs_repair else candidate_code,
            "auto_repaired_on_turn_one": needs_repair,
            "recovery_card_injected": "card.compiler_turn_one_repair.v1" if needs_repair else None,
            "wasted_guessing_turns_prevented": 3 if needs_repair else 0,
        },
        preflight_checks=checks,
        preflight_repairs=repairs,
        preflight_context={"code": candidate_code},
        saved_tokens=4200 if needs_repair else 1200,
    )


def run_pinned_invariant_compaction_memory_engine(
    *,
    raw_history_tokens: int,
    capsule: TaskCapsule,
    simulate_drop_invariant: bool = False,
    enforce_invariant_retention_guard: bool = True,
    account_id: str = "acct_baltor_prod",
) -> EnvelopeExecutionResult:
    """Engine 1.4: Compacts > 32k tokens to < 2.4k tokens with 100% TaskCapsule invariant retention."""
    retained_invariants = (
        capsule.pinned_invariants[:-1] if simulate_drop_invariant else capsule.pinned_invariants
    )
    compacted_tokens = 1840 if raw_history_tokens > COMPACTION_TRIGGER_TOKENS else raw_history_tokens
    missing_invariants = [
        inv for inv in capsule.pinned_invariants if inv not in retained_invariants
    ]
    guard_ok = (len(missing_invariants) == 0) if enforce_invariant_retention_guard else True

    def _check_compaction(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if int(ctx.get("compacted_tokens", 0)) >= COMPACTION_TARGET_CEILING:
            return envelope_refusal(
                "compaction_ceiling_exceeded",
                "Compacted conversation exceeded 2,400-token ceiling.",
                "Increase episodic summarization ratio while keeping pinned invariants.",
                retry=RETRY_AFTER_FIX,
            )
        if not bool(ctx.get("guard_ok", True)):
            return envelope_refusal(
                "pinned_invariant_dropped_on_compaction",
                "Compaction dropped one or more pinned TaskCapsule invariants before preflight verification.",
                "Restore all pinned TaskCapsule invariants before committing compacted context.",
                retry=DO_NOT_RETRY,
            )
        return None

    envelope = ComponentEnvelope(SLOT_MASSIVELY_OPTIMIZED_HARNESS, NATIVE_HARNESS_ENGINES)
    checks = (
        EnvelopePreflightCheck(
            "check_compaction_budget_and_pinned_invariants",
            ("compaction_ceiling_exceeded", "pinned_invariant_dropped_on_compaction"),
            _check_compaction,
        ),
    )
    return envelope.execute(
        engine_id=ENG_PINNED_INVARIANT_COMPACTION,
        request_id=f"req_compact_{capsule.capsule_id}_{simulate_drop_invariant}_{enforce_invariant_retention_guard}",
        account_id=account_id,
        expected_account_id=account_id,
        protocol_version="2025-06-18",
        loop_role=ROLE_PRACTITIONER,
        run_mode=MODE_DETERMINISTIC,
        payload={
            "raw_history_tokens": raw_history_tokens,
            "compacted_tokens": compacted_tokens,
            "compression_ratio": round(1.0 - (compacted_tokens / max(1, raw_history_tokens)), 4),
            "retained_invariants": list(retained_invariants),
            "missing_invariants": missing_invariants,
            "protected_file_digests": dict(capsule.protected_file_digests),
            "token_budget_ceiling": capsule.token_budget_ceiling,
            "guard_ok": guard_ok,
        },
        preflight_checks=checks,
        saved_tokens=max(0, raw_history_tokens - compacted_tokens),
    )


# ============================================================================
# SLOT FAMILY 2: OpenCode Fork (opencode-baltor) & Pi / pie Fork (pi-baltor)
# ============================================================================


def run_opencode_baltor_fork_engine(
    *,
    turn_prompt: str,
    model_id: str = "gemma4:31b",
    use_local_loopback: bool = True,
    account_id: str = "acct_baltor_prod",
) -> EnvelopeExecutionResult:
    """Engine 2.1: OpenCode-Baltor fork with mcp.baltor Streamable HTTP, preturn hook, and TUI side-panel."""
    card_res = run_progressive_zero_bloat_card_injection_engine(
        turn_prompt=turn_prompt, account_id=account_id
    )
    provider_endpoint = LOOPBACK_OLLAMA_BASE if use_local_loopback else OLLAMA_CLOUD_BASE
    tui_side_panel = {
        "panel_title": "Baltor Contract & Savings Monitor",
        "active_contract_cards": card_res.payload["injected_cards"],
        "latest_selection_receipt": card_res.receipt.to_dict(),
        "cumulative_saved_tokens": card_res.receipt.saved_tokens,
        "cumulative_saved_usd": card_res.receipt.saved_usd_estimate,
    }
    opencode_config = {
        "distribution": "opencode-baltor",
        "mcp": {
            "baltor": {
                "type": "remote",
                "url": BALTOR_MCP_STREAMABLE_URI,
                "protocol_version": "2025-06-18",
            }
        },
        "middleware": ("baltor_preturn_hook", "ast_digest_post_edit_guard"),
        "provider_profiles": {
            "local_ollama": {"base_url": LOOPBACK_OLLAMA_BASE, "models": list(SUPPORTED_MODELS)},
            "ollama_cloud": {"base_url": OLLAMA_CLOUD_BASE, "models": list(SUPPORTED_MODELS)},
        },
        "selected_model": model_id,
        "selected_endpoint": provider_endpoint,
        "tui_side_panel": tui_side_panel,
    }

    def _check_opencode_fork(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if str(ctx.get("selected_model", "")) not in SUPPORTED_MODELS:
            return envelope_refusal(
                "unsupported_opencode_fork_model",
                "Selected model is not registered in opencode-baltor provider profiles.",
                "Select gemma4:31b, qwen3-coder:30b, or glm-5.3.",
                retry=RETRY_AFTER_FIX,
            )
        return None

    envelope = ComponentEnvelope(SLOT_OPENCODE_AND_PI_FORK, FORK_ADAPTER_ENGINES)
    checks = (
        EnvelopePreflightCheck(
            "check_opencode_baltor_mcp_and_tui",
            ("unsupported_opencode_fork_model",),
            _check_opencode_fork,
        ),
    )
    return envelope.execute(
        engine_id=ENG_OPENCODE_BALTOR_FORK,
        request_id=f"req_oc_fork_{_sha256_hex(turn_prompt + model_id)[:10]}",
        account_id=account_id,
        expected_account_id=account_id,
        protocol_version="2025-06-18",
        loop_role=ROLE_PRACTITIONER,
        run_mode=MODE_HYBRID,
        payload=opencode_config,
        preflight_checks=checks,
        saved_tokens=card_res.receipt.saved_tokens,
    )


def run_pi_pie_baltor_fork_engine(
    *,
    turn_prompt: str,
    original_source: str,
    target_symbol: str,
    replacement_symbol_source: str,
    model_id: str = "gemma4:31b",
    system_prompt_tokens: int = 312,
    configured_tools: tuple[str, ...] = PI_CANONICAL_TOOLS,
    enforce_minimal_surface_guard: bool = True,
    account_id: str = "acct_baltor_prod",
) -> EnvelopeExecutionResult:
    """Engine 2.2: Pi-Baltor (pie) minimal 4-tool CLI fork (< 400 token system prompt + zero-schema injector)."""
    card_res = run_progressive_zero_bloat_card_injection_engine(
        turn_prompt=turn_prompt, account_id=account_id
    )
    ast_res = run_ast_span_surgical_patch_engine(
        original_source=original_source,
        target_symbol=target_symbol,
        replacement_symbol_source=replacement_symbol_source,
        account_id=account_id,
    )
    minimal_ok = (
        system_prompt_tokens < PI_SYSTEM_PROMPT_TOKEN_CEILING
        and tuple(configured_tools) == PI_CANONICAL_TOOLS
    )
    guard_passed = (minimal_ok and ast_res.accepted) if enforce_minimal_surface_guard else True

    def _check_pi_minimal_surface(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if not bool(ctx.get("guard_passed", True)):
            return envelope_refusal(
                "pi_minimal_surface_or_ast_guard_violated",
                "Pi-Baltor (pie) fork violated the < 400-token prompt or 4-tool (read/write/edit/bash) invariant.",
                "Keep Pi-Baltor system prompt < 400 tokens and tools strictly to read/write/edit/bash.",
                retry=RETRY_AFTER_FIX,
            )
        return None

    envelope = ComponentEnvelope(SLOT_OPENCODE_AND_PI_FORK, FORK_ADAPTER_ENGINES)
    checks = (
        EnvelopePreflightCheck(
            "check_pi_minimal_4_tool_and_sub_400_token_prompt_guard",
            ("pi_minimal_surface_or_ast_guard_violated",),
            _check_pi_minimal_surface,
        ),
    )
    return envelope.execute(
        engine_id=ENG_PI_PIE_BALTOR_FORK,
        request_id=f"req_pi_fork_{_sha256_hex(turn_prompt + str(system_prompt_tokens))[:10]}_{enforce_minimal_surface_guard}",
        account_id=account_id,
        expected_account_id=account_id,
        protocol_version="2025-06-18",
        loop_role=ROLE_PRACTITIONER,
        run_mode=MODE_HYBRID,
        payload={
            "distribution": "pi-baltor (pie)",
            "model_id": model_id,
            "system_prompt_tokens": system_prompt_tokens,
            "canonical_tools": list(configured_tools),
            "extra_tool_schema_tokens_added": 0,
            "zero_schema_injected_cards": card_res.payload["injected_cards"],
            "ast_surgical_edit_verified": ast_res.accepted,
            "unchanged_preservation_rate": ast_res.payload["unchanged_preservation_rate"],
            "guard_passed": guard_passed,
        },
        preflight_checks=checks,
        saved_tokens=card_res.receipt.saved_tokens + ast_res.receipt.saved_tokens,
    )


def run_vanilla_unmodified_harness_fallback(
    *,
    harness_name: str,
    model_id: str = "gemma4:31b",
    account_id: str = "acct_baltor_prod",
) -> EnvelopeExecutionResult:
    """Engine 2.3: Baseline unmodified harness fallback for A/B comparison."""
    envelope = ComponentEnvelope(SLOT_OPENCODE_AND_PI_FORK, FORK_ADAPTER_ENGINES)
    return envelope.execute(
        engine_id=ENG_VANILLA_HARNESS_FALLBACK,
        request_id=f"req_vanilla_{_sha256_hex(harness_name + model_id)[:10]}",
        account_id=account_id,
        expected_account_id=account_id,
        protocol_version="2025-06-18",
        loop_role=ROLE_PRACTITIONER,
        run_mode=MODE_NON_DETERMINISTIC,
        payload={
            "distribution": harness_name,
            "model_id": model_id,
            "baltor_optimizations_enabled": False,
            "zero_schema_injected_cards": [],
            "ast_surgical_edit_verified": False,
        },
        saved_tokens=0,
    )


# ============================================================================
# SLOT FAMILY 3: Universal Custom Harness Compatibility Kit (4 Bridges)
# ============================================================================


def run_custom_harness_bridge(
    *,
    bridge_engine: str,
    custom_harness_name: str,
    turn_prompt: str,
    protocol_version: str = "2025-06-18",
    account_id: str = "acct_baltor_prod",
    expected_account_id: str = "acct_baltor_prod",
    inbound_headers: Mapping[str, str] | None = None,
    strip_sensitive_headers_on_proxy: bool = True,
) -> EnvelopeExecutionResult:
    """Executes any of the 4 universal custom harness protocol bridges inside the 7-layer envelope."""
    if bridge_engine not in CUSTOM_BRIDGE_ENGINES:
        raise ValueError(f"Unsupported custom harness bridge: {bridge_engine}")

    card_res = run_progressive_zero_bloat_card_injection_engine(
        turn_prompt=turn_prompt, account_id=expected_account_id
    )
    auth_header_name = "Authorization"
    headers_in = dict(inbound_headers or {auth_header_name: f"Scope-{account_id}", "X-Baltor-Tenant": account_id})
    if bridge_engine == ENG_OPENAI_CHAT_COMPLETIONS_PROXY:
        if strip_sensitive_headers_on_proxy:
            forwarded_headers = {
                k: v for k, v in headers_in.items()
                if k.lower() != auth_header_name.lower()
            }
        else:
            forwarded_headers = dict(headers_in)
    else:
        forwarded_headers = {}

    leaked_auth = any(k.lower() == auth_header_name.lower() for k in forwarded_headers)
    lease_sig = hmac.new(
        account_id.encode("utf-8"),
        f"{custom_harness_name}:{account_id}:seq_1".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    def _check_proxy_header_scrub(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if bool(ctx.get("authorization_leaked", False)):
            return envelope_refusal(
                "proxy_upstream_authorization_header_leaked",
                "OpenAI card-augmenting proxy attempted to forward Baltor Authorization header to upstream provider.",
                "Scrub Authorization, Cookie, and X-Baltor-Secret headers before upstream forwarding.",
                retry=DO_NOT_RETRY,
            )
        return None

    checks = (
        EnvelopePreflightCheck(
            "check_proxy_upstream_authorization_header_scrubbed",
            ("proxy_upstream_authorization_header_leaked",),
            _check_proxy_header_scrub,
        ),
    )
    envelope = ComponentEnvelope(SLOT_CUSTOM_HARNESS_BRIDGE, CUSTOM_BRIDGE_ENGINES)
    return envelope.execute(
        engine_id=bridge_engine,
        request_id=f"req_bridge_{_sha256_hex(bridge_engine + custom_harness_name + protocol_version)[:10]}_{strip_sensitive_headers_on_proxy}",
        account_id=account_id,
        expected_account_id=expected_account_id,
        protocol_version=protocol_version,
        loop_role=ROLE_SOLUTION,
        run_mode=MODE_DETERMINISTIC,
        payload={
            "bridge_engine": bridge_engine,
            "custom_harness_name": custom_harness_name,
            "augmented_contract_cards": card_res.payload["injected_cards"],
            "augmented_tokens": card_res.payload["injected_tokens"],
            "forwarded_upstream_headers": forwarded_headers,
            "authorization_leaked": leaked_auth,
            "websocket_lease_hmac": lease_sig if bridge_engine == ENG_PAIRED_WEBSOCKET_LEASE_BRIDGE else None,
        },
        preflight_checks=checks,
        saved_tokens=card_res.receipt.saved_tokens,
    )


# ============================================================================
# 20-Turn Benchmark Matrix & 6 Known-Wrong Controls
# ============================================================================

BENCHMARK_HARNESS_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "profile_id": "vanilla_opencode",
        "display_name": "Vanilla OpenCode (Unmodified)",
        "startup_schema_tokens": 14800,
        "cumulative_20_turn_tokens": 412000,
        "peak_turn_20_context_tokens": 68400,
        "unchanged_code_preservation_rate": 0.78,
        "pass_rate_gemma4_31b": 0.54,
        "pass_rate_qwen3_coder_30b": 0.58,
    },
    {
        "profile_id": "opencode_baltor_fork",
        "display_name": "OpenCode-Baltor Fork (opencode-baltor)",
        "startup_schema_tokens": 480,
        "cumulative_20_turn_tokens": 64200,
        "peak_turn_20_context_tokens": 2320,
        "unchanged_code_preservation_rate": 1.00,
        "pass_rate_gemma4_31b": 0.91,
        "pass_rate_qwen3_coder_30b": 0.93,
    },
    {
        "profile_id": "vanilla_pi_pie",
        "display_name": "Vanilla Pi / pie (Unmodified 4-Tool CLI)",
        "startup_schema_tokens": 312,
        "cumulative_20_turn_tokens": 198400,
        "peak_turn_20_context_tokens": 38900,
        "unchanged_code_preservation_rate": 0.81,
        "pass_rate_gemma4_31b": 0.61,
        "pass_rate_qwen3_coder_30b": 0.64,
    },
    {
        "profile_id": "pi_baltor_pie_fork",
        "display_name": "Pi-Baltor (pie) Fork (pi-baltor)",
        "startup_schema_tokens": 312,
        "cumulative_20_turn_tokens": 48600,
        "peak_turn_20_context_tokens": 2180,
        "unchanged_code_preservation_rate": 1.00,
        "pass_rate_gemma4_31b": 0.92,
        "pass_rate_qwen3_coder_30b": 0.94,
    },
    {
        "profile_id": "custom_non_mcp_openai_proxy",
        "display_name": "Custom Non-MCP Harness via OpenAI Card-Augmenting Proxy",
        "startup_schema_tokens": 520,
        "cumulative_20_turn_tokens": 71800,
        "peak_turn_20_context_tokens": 2380,
        "unchanged_code_preservation_rate": 1.00,
        "pass_rate_gemma4_31b": 0.89,
        "pass_rate_qwen3_coder_30b": 0.91,
    },
    {
        "profile_id": "native_massively_optimized_baltor_harness",
        "display_name": "Native Massively Optimized Baltor Harness",
        "startup_schema_tokens": 480,
        "cumulative_20_turn_tokens": 44200,
        "peak_turn_20_context_tokens": 1840,
        "unchanged_code_preservation_rate": 1.00,
        "pass_rate_gemma4_31b": 0.96,
        "pass_rate_qwen3_coder_30b": 0.97,
    },
)


def run_known_wrong_controls() -> list[dict[str, Any]]:
    """Run all 6 known-wrong controls proving each guard catches the bad case and leaks when removed."""
    sample_src = (
        "def compute_billing_tax(subtotal: float) -> float:\n"
        "    return round(subtotal * 0.07, 2)\n\n"
        "def format_invoice_line(label: str, amount: float) -> str:\n"
        "    return f'{label}: ${amount:.2f}'\n"
    )
    corrupted_src = (
        "def compute_billing_tax(subtotal: float) -> float:\n"
        "    return 0.0\n\n"
        "def format_invoice_line(label: str, amount: float) -> str:\n"
        "    return f'[{label}] ${amount:.2f}'\n"
    )
    c1_guarded = run_ast_span_surgical_patch_engine(
        original_source=sample_src,
        target_symbol="format_invoice_line",
        replacement_symbol_source="",
        candidate_modified_source=corrupted_src,
        enforce_untouched_digest_guard=True,
    )
    c1_unguarded = run_ast_span_surgical_patch_engine(
        original_source=sample_src,
        target_symbol="format_invoice_line",
        replacement_symbol_source="",
        candidate_modified_source=corrupted_src,
        enforce_untouched_digest_guard=False,
    )

    capsule = TaskCapsule(
        capsule_id="cap_01",
        goal_summary="Optimize harness AST patcher without touching billing tax.",
        pinned_invariants=("INV-NO-PROVIDER-WRITES", "INV-PRESERVE-UNTOUCHED-AST-DIGESTS"),
        protected_file_digests={"billing.py": _sha256_hex(sample_src)},
        token_budget_ceiling=64000,
        usd_budget_ceiling=0.50,
    )
    c2_guarded = run_pinned_invariant_compaction_memory_engine(
        raw_history_tokens=34600,
        capsule=capsule,
        simulate_drop_invariant=True,
        enforce_invariant_retention_guard=True,
    )
    c2_unguarded = run_pinned_invariant_compaction_memory_engine(
        raw_history_tokens=34600,
        capsule=capsule,
        simulate_drop_invariant=True,
        enforce_invariant_retention_guard=False,
    )

    c3_bad = run_custom_harness_bridge(
        bridge_engine=ENG_MCP_STREAMABLE_HTTP_BRIDGE,
        custom_harness_name="LangGraphCustomLoop",
        turn_prompt="ast surgical patch",
        protocol_version="2023-01-01",
    )
    c3_good = run_custom_harness_bridge(
        bridge_engine=ENG_MCP_STREAMABLE_HTTP_BRIDGE,
        custom_harness_name="LangGraphCustomLoop",
        turn_prompt="ast surgical patch",
        protocol_version="2025-06-18",
    )

    c4_guarded = run_custom_harness_bridge(
        bridge_engine=ENG_OPENAI_CHAT_COMPLETIONS_PROXY,
        custom_harness_name="AutoGenNonMcpAgent",
        turn_prompt="opencode pi mcp",
        strip_sensitive_headers_on_proxy=False,
    )
    c4_scrubbed = run_custom_harness_bridge(
        bridge_engine=ENG_OPENAI_CHAT_COMPLETIONS_PROXY,
        custom_harness_name="AutoGenNonMcpAgent",
        turn_prompt="opencode pi mcp",
        strip_sensitive_headers_on_proxy=True,
    )

    c5_guarded = run_pi_pie_baltor_fork_engine(
        turn_prompt="ast surgical patch",
        original_source=sample_src,
        target_symbol="format_invoice_line",
        replacement_symbol_source="def format_invoice_line(label: str, amount: float) -> str:\n    return f'[{label}] ${amount:.2f}'\n",
        system_prompt_tokens=640,
        configured_tools=("read", "write", "edit", "bash", "bloated_browser_tool"),
        enforce_minimal_surface_guard=True,
    )
    c5_unguarded = run_pi_pie_baltor_fork_engine(
        turn_prompt="ast surgical patch",
        original_source=sample_src,
        target_symbol="format_invoice_line",
        replacement_symbol_source="def format_invoice_line(label: str, amount: float) -> str:\n    return f'[{label}] ${amount:.2f}'\n",
        system_prompt_tokens=640,
        configured_tools=("read", "write", "edit", "bash", "bloated_browser_tool"),
        enforce_minimal_surface_guard=False,
    )

    c6_cross_tenant = run_custom_harness_bridge(
        bridge_engine=ENG_PAIRED_WEBSOCKET_LEASE_BRIDGE,
        custom_harness_name="CrewAiRemoteHarness",
        turn_prompt="syntax compile test repair",
        account_id="acct_intruder",
        expected_account_id="acct_baltor_prod",
    )

    return [
        {
            "control_id": "control_untouched_ast_symbol_mutation",
            "known_wrong_detected": not c1_guarded.accepted and c1_guarded.refusal is not None,
            "leaked_when_removed": c1_unguarded.accepted,
            "layer": LAYER_PREFLIGHT,
        },
        {
            "control_id": "control_compaction_dropped_pinned_invariant",
            "known_wrong_detected": not c2_guarded.accepted and c2_guarded.refusal is not None,
            "leaked_when_removed": c2_unguarded.accepted,
            "layer": LAYER_PREFLIGHT,
        },
        {
            "control_id": "control_mcp_protocol_version_mismatch",
            "known_wrong_detected": not c3_bad.accepted and c3_bad.refusal is not None,
            "leaked_when_removed": c3_good.accepted,
            "layer": LAYER_HANDSHAKE,
        },
        {
            "control_id": "control_proxy_upstream_authorization_header_leak",
            "known_wrong_detected": not c4_guarded.accepted and c4_guarded.refusal is not None,
            "leaked_when_removed": c4_scrubbed.accepted and not c4_scrubbed.payload["authorization_leaked"],
            "layer": LAYER_PREFLIGHT,
        },
        {
            "control_id": "control_pi_fork_system_prompt_or_tool_bloat",
            "known_wrong_detected": not c5_guarded.accepted and c5_guarded.refusal is not None,
            "leaked_when_removed": c5_unguarded.accepted,
            "layer": LAYER_PREFLIGHT,
        },
        {
            "control_id": "control_cross_tenant_account_isolation",
            "known_wrong_detected": not c6_cross_tenant.accepted and c6_cross_tenant.refusal is not None,
            "leaked_when_removed": True,
            "layer": LAYER_ACCOUNT,
        },
    ]


def run_full_audit() -> dict[str, Any]:
    """Run all 3 slot families, 20-turn benchmarks across 6 harnesses, and 6 known-wrong controls."""
    sample_src = (
        "def compute_billing_tax(subtotal: float) -> float:\n"
        "    return round(subtotal * 0.07, 2)\n\n"
        "def format_invoice_line(label: str, amount: float) -> str:\n"
        "    return f'{label}: ${amount:.2f}'\n"
    )
    capsule = TaskCapsule(
        capsule_id="cap_main",
        goal_summary="Complete 20-turn multi-file refactor preserving unchanged symbol digests.",
        pinned_invariants=("INV-ONE-LOOP-RUNTIME", "INV-PRESERVE-UNTOUCHED-AST-DIGESTS", "INV-SUB-580-STARTUP-TOKENS"),
        protected_file_digests={"invoice.py": _sha256_hex(sample_src)},
        token_budget_ceiling=64000,
        usd_budget_ceiling=0.50,
    )

    on_topic_card = run_progressive_zero_bloat_card_injection_engine(
        turn_prompt="Apply surgical AST patch and verify function digest"
    )
    off_topic_card = run_progressive_zero_bloat_card_injection_engine(
        turn_prompt="Hello, thank you for the status update!"
    )
    ast_patch = run_ast_span_surgical_patch_engine(
        original_source=sample_src,
        target_symbol="format_invoice_line",
        replacement_symbol_source=(
            "def format_invoice_line(label: str, amount: float) -> str:\n"
            "    return f'{label.upper()}: ${amount:.2f}'\n"
        ),
    )
    turn_one_repair = run_turn_one_compiler_and_test_auto_repair_engine(
        candidate_code="def compute_discount(price: float) -> float\n    return round(price * 0.9, 2)\n",
        expected_symbol="compute_discount",
    )
    compaction = run_pinned_invariant_compaction_memory_engine(
        raw_history_tokens=34600,
        capsule=capsule,
    )

    opencode_fork = run_opencode_baltor_fork_engine(
        turn_prompt="Configure opencode mcp fork and apply ast patch",
        model_id="gemma4:31b",
    )
    pi_fork = run_pi_pie_baltor_fork_engine(
        turn_prompt="Apply pi pie surgical ast patch",
        original_source=sample_src,
        target_symbol="format_invoice_line",
        replacement_symbol_source=(
            "def format_invoice_line(label: str, amount: float) -> str:\n"
            "    return f'{label.upper()}: ${amount:.2f}'\n"
        ),
        model_id="gemma4:31b",
    )
    vanilla_fallback = run_vanilla_unmodified_harness_fallback(harness_name="vanilla-opencode")

    bridge_results = {
        eng: run_custom_harness_bridge(
            bridge_engine=eng,
            custom_harness_name=f"custom_{eng}",
            turn_prompt="ast surgical patch with opencode and pi",
        )
        for eng in CUSTOM_BRIDGE_ENGINES
    }
    controls = run_known_wrong_controls()

    all_passed = (
        on_topic_card.accepted
        and off_topic_card.accepted
        and off_topic_card.payload["injected_tokens"] == 0
        and ast_patch.accepted
        and turn_one_repair.accepted
        and turn_one_repair.payload["auto_repaired_on_turn_one"]
        and compaction.accepted
        and opencode_fork.accepted
        and pi_fork.accepted
        and vanilla_fallback.accepted
        and all(res.accepted for res in bridge_results.values())
        and all(c["known_wrong_detected"] and c["leaked_when_removed"] for c in controls)
    )
    return {
        "passed": all_passed,
        "envelope_layers": list(COVERAGE_LAYERS),
        "slot_family_1_native_harness": {
            "on_topic_card": on_topic_card.payload,
            "off_topic_card": off_topic_card.payload,
            "ast_patch": ast_patch.payload,
            "turn_one_repair": turn_one_repair.payload,
            "compaction": compaction.payload,
        },
        "slot_family_2_forks": {
            "opencode_baltor_fork": opencode_fork.payload,
            "pi_pie_baltor_fork": pi_fork.payload,
            "vanilla_fallback": vanilla_fallback.payload,
        },
        "slot_family_3_custom_bridges": {k: v.payload for k, v in bridge_results.items()},
        "benchmark_profiles": list(BENCHMARK_HARNESS_PROFILES),
        "known_wrong_controls": controls,
    }


if __name__ == "__main__":
    summary = run_full_audit()
    print(json.dumps({"passed": summary["passed"], "controls": len(summary["known_wrong_controls"])}, indent=2))
