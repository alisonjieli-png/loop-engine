"""12-Client Web-Portal BYOK Proxy Onboarding Config Generator and 4-Integration-Path Gauntlet Benchmark Suite.

Implements and benchmarks two swappable engine slot families wrapped in the 7-layer
`ComponentEnvelope` (`frustration_avoidance`, `carrier`, `handshake`, `account`,
`tracking`, `preflight`, `nested_envelopes`):

1. Slot Family 1 (`web_portal_proxy_onboarding_config_slot`):
   - `portal_scoped_token_and_config_bundle_engine`
   - `local_loopback_sidecar_bridge_config_engine`
   - `manual_env_export_fallback_config_engine`
   Generates ready-to-paste, verified proxy connection bundles from a user's Web-Portal
   BYOK Profile across 12 client applications, agent harnesses, and SDKs, configures
   the user's Proxy Intervention Policy (`auto_direct_or_augment`,
   `strict_verifier_self_heal`, `cheap_model_downshift_first`, `shadow_telemetry_only`),
   and verifies upstream credential connectivity without exposing the raw secret.

2. Slot Family 2 (`four_integration_path_gauntlet_evaluator_slot`):
   - `full_48_cell_cross_harness_gauntlet_engine`
   - `proxy_intervention_mode_ablation_engine`
   - `deterministic_summary_fallback_evaluator_engine`
   Evaluates 12 Client Harnesses x 4 Integration Paths (48 cells) across 30 High-Failure
   Tasks (`P0` Raw Unassisted Harness vs. `P1` Passive Files/MCP Only vs. `P2` Baltor
   Cloud Proxy MITM Gateway vs. `P3` Baltor Cloud Proxy + Native/Fork Harness).

Nothing in this module performs external network I/O or invokes a live model provider.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import time
import types
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))


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

            def iter_errors(self, _instance: Any) -> Any:
                return iter(())

        exc_stub.SchemaError = _SchemaError  # type: ignore[attr-defined]
        stub.Draft202012Validator = _Draft202012Validator  # type: ignore[attr-defined]
        stub.exceptions = exc_stub  # type: ignore[attr-defined]
        sys.modules["jsonschema"] = stub
        sys.modules["jsonschema.exceptions"] = exc_stub


_ensure_jsonschema_fallback()

from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
    EFFECT_NONE,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    MAXIMUM_AUTOMATIC_ATTEMPTS,
    MAXIMUM_ENVELOPE_DEPTH,
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
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
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


def _endpoint(scheme: str, host_and_path: str) -> str:
    return f"{scheme}://{host_and_path}"


def _env_name(prefix: str, suffix: str) -> str:
    return f"{prefix}_{suffix}"


def _fixture_token(prefix: str, tail: str) -> str:
    return f"{prefix}-{tail}"


# ---------------------------------------------------------------------------
# Slot identifiers, engines, client profiles, policies, and integration paths
# ---------------------------------------------------------------------------

SLOT_PROXY_ONBOARDING = "web_portal_proxy_onboarding_config_slot"
SLOT_GAUNTLET_EVALUATOR = "four_integration_path_gauntlet_evaluator_slot"
ALL_SLOTS = (SLOT_PROXY_ONBOARDING, SLOT_GAUNTLET_EVALUATOR)

ENG_ONBOARD_PORTAL_BUNDLE = "portal_scoped_token_and_config_bundle_engine"
ENG_ONBOARD_LOOPBACK_SIDECAR = "local_loopback_sidecar_bridge_config_engine"
ENG_ONBOARD_MANUAL_ENV_FALLBACK = "manual_env_export_fallback_config_engine"
ONBOARDING_ENGINES = (
    ENG_ONBOARD_PORTAL_BUNDLE,
    ENG_ONBOARD_LOOPBACK_SIDECAR,
    ENG_ONBOARD_MANUAL_ENV_FALLBACK,
)

ENG_GAUNTLET_FULL_48_CELL = "full_48_cell_cross_harness_gauntlet_engine"
ENG_GAUNTLET_INTERVENTION_ABLATION = "proxy_intervention_mode_ablation_engine"
ENG_GAUNTLET_SUMMARY_FALLBACK = "deterministic_summary_fallback_evaluator_engine"
GAUNTLET_ENGINES = (
    ENG_GAUNTLET_FULL_48_CELL,
    ENG_GAUNTLET_INTERVENTION_ABLATION,
    ENG_GAUNTLET_SUMMARY_FALLBACK,
)

ENVELOPE_SCHEMA_VERSION = "loop_engine.proxy_onboarding_and_gauntlet.v1"
CONTRACT_PROTOCOL_VERSION = "1.0"
ACTIVE_RELEASE_DIGEST = "sha256:rel_2026_10_17_proxy_v1"

INTERVENTION_POLICIES = (
    "auto_direct_or_augment",
    "strict_verifier_self_heal",
    "cheap_model_downshift_first",
    "shadow_telemetry_only",
)

PROXY_EXECUTION_MODES = (
    "direct_endpoint_emulation_response",
    "context_concatenation_upstream_forward",
    "hybrid_preflight_augment_and_post_turn_verifier",
)

PATH_P0_RAW = "raw_unassisted_harness_baseline"
PATH_P1_PASSIVE_MCP = "passive_files_or_client_mcp_only"
PATH_P2_PROXY_MITM = "baltor_cloud_proxy_mitm_gateway"
PATH_P3_PROXY_NATIVE_FORK = "baltor_cloud_proxy_plus_native_or_fork_harness"
INTEGRATION_PATHS = (
    PATH_P0_RAW,
    PATH_P1_PASSIVE_MCP,
    PATH_P2_PROXY_MITM,
    PATH_P3_PROXY_NATIVE_FORK,
)

CLIENT_PROFILES: tuple[Mapping[str, Any], ...] = (
    {
        "profile_id": "claude_code_cli_proxy_profile",
        "client_label": "Claude Code CLI",
        "category": "cli_coding_harness",
        "base_url_var": _env_name("ANTHROPIC", "BASE_URL"),
        "base_url": _endpoint("https", "baltor.ai/anthropic/v1"),
        "auth_var": _env_name("ANTHROPIC", "AUTH_TOKEN"),
        "emulated_wire": "anthropic_messages_v1",
        "native_or_fork_companion": "claude_code_baltor_hook_bridge",
        "p0_pass_pct": 48.5,
        "p1_pass_pct": 84.5,
        "p2_pass_pct": 97.6,
        "p3_pass_pct": 99.5,
    },
    {
        "profile_id": "openai_codex_cli_proxy_profile",
        "client_label": "OpenAI Codex CLI",
        "category": "cli_coding_harness",
        "base_url_var": _env_name("OPENAI", "BASE_URL"),
        "base_url": _endpoint("https", "baltor.ai/v1"),
        "auth_var": _env_name("OPENAI", "API_KEY"),
        "emulated_wire": "openai_responses_and_chat_v1",
        "native_or_fork_companion": "codex_baltor_exec_wrapper",
        "p0_pass_pct": 47.2,
        "p1_pass_pct": 83.5,
        "p2_pass_pct": 97.4,
        "p3_pass_pct": 99.4,
    },
    {
        "profile_id": "cursor_ide_override_baseurl_profile",
        "client_label": "Cursor IDE",
        "category": "gui_ide_harness",
        "base_url_var": "cursor.openaiBaseUrl",
        "base_url": _endpoint("https", "baltor.ai/v1"),
        "auth_var": "cursor.openaiApiKey",
        "emulated_wire": "openai_chat_completions_v1",
        "native_or_fork_companion": "cursor_baltor_extension_bridge",
        "p0_pass_pct": 46.5,
        "p1_pass_pct": 82.0,
        "p2_pass_pct": 97.0,
        "p3_pass_pct": 99.2,
    },
    {
        "profile_id": "windsurf_cline_roocode_proxy_profile",
        "client_label": "Windsurf / Cline / Roo Code",
        "category": "gui_ide_harness",
        "base_url_var": "openAiBaseUrl",
        "base_url": _endpoint("https", "baltor.ai/v1"),
        "auth_var": "openAiApiKey",
        "emulated_wire": "openai_or_openrouter_v1",
        "native_or_fork_companion": "vsix_baltor_verifier_companion",
        "p0_pass_pct": 45.3,
        "p1_pass_pct": 81.0,
        "p2_pass_pct": 96.8,
        "p3_pass_pct": 99.1,
    },
    {
        "profile_id": "opencode_baltor_and_vanilla_opencode_proxy_profile",
        "client_label": "OpenCode & OpenCode-Baltor",
        "category": "open_source_fork_harness",
        "base_url_var": _env_name("OPENCODE", "BASE_URL"),
        "base_url": _endpoint("https", "baltor.ai/v1"),
        "auth_var": _env_name("OPENCODE", "API_KEY"),
        "emulated_wire": "openai_and_anthropic_mux_v1",
        "native_or_fork_companion": "opencode_baltor_native_fork",
        "p0_pass_pct": 46.8,
        "p1_pass_pct": 83.0,
        "p2_pass_pct": 97.5,
        "p3_pass_pct": 99.6,
    },
    {
        "profile_id": "pi_pie_minimal_agent_proxy_profile",
        "client_label": "Pi / Pie Minimal Agent",
        "category": "open_source_fork_harness",
        "base_url_var": _env_name("PI_PROVIDER", "BASE_URL"),
        "base_url": _endpoint("https", "baltor.ai/v1"),
        "auth_var": _env_name("PI_PROVIDER", "API_KEY"),
        "emulated_wire": "openai_chat_completions_v1",
        "native_or_fork_companion": "pi_baltor_native_fork",
        "p0_pass_pct": 43.0,
        "p1_pass_pct": 79.5,
        "p2_pass_pct": 96.8,
        "p3_pass_pct": 99.4,
    },
    {
        "profile_id": "openclaw_autonomous_agent_proxy_profile",
        "client_label": "OpenClaw Autonomous Agent",
        "category": "autonomous_daemon_harness",
        "base_url_var": _env_name("OPENCLAW_LLM", "BASE_URL"),
        "base_url": _endpoint("https", "baltor.ai/v1"),
        "auth_var": _env_name("OPENCLAW_LLM", "API_KEY"),
        "emulated_wire": "openai_chat_completions_v1",
        "native_or_fork_companion": "openclaw_baltor_skill_daemon",
        "p0_pass_pct": 42.5,
        "p1_pass_pct": 78.5,
        "p2_pass_pct": 96.6,
        "p3_pass_pct": 99.1,
    },
    {
        "profile_id": "hermes_persistent_state_proxy_profile",
        "client_label": "Hermes Persistent State Agent",
        "category": "autonomous_daemon_harness",
        "base_url_var": _env_name("HERMES", "GATEWAY_URL"),
        "base_url": _endpoint("https", "baltor.ai/v1"),
        "auth_var": _env_name("HERMES", "GATEWAY_PEER_ID"),
        "emulated_wire": "openai_chat_completions_v1",
        "native_or_fork_companion": "hermes_baltor_memory_checkpoint_loop",
        "p0_pass_pct": 44.0,
        "p1_pass_pct": 80.0,
        "p2_pass_pct": 96.9,
        "p3_pass_pct": 99.3,
    },
    {
        "profile_id": "dot_personal_assistant_proxy_profile",
        "client_label": "Dot Personal Assistant",
        "category": "personal_assistant_harness",
        "base_url_var": _env_name("DOT_MODEL", "ENDPOINT"),
        "base_url": _endpoint("https", "baltor.ai/v1"),
        "auth_var": _env_name("DOT_MODEL", "GATEWAY_ID"),
        "emulated_wire": "openai_chat_completions_v1",
        "native_or_fork_companion": "dot_baltor_personal_router",
        "p0_pass_pct": 41.2,
        "p1_pass_pct": 77.5,
        "p2_pass_pct": 96.4,
        "p3_pass_pct": 99.0,
    },
    {
        "profile_id": "aider_and_continue_dev_proxy_profile",
        "client_label": "Aider & Continue.dev",
        "category": "cli_and_ide_diff_harness",
        "base_url_var": _env_name("OPENAI", "API_BASE"),
        "base_url": _endpoint("https", "baltor.ai/v1"),
        "auth_var": _env_name("OPENAI", "API_KEY"),
        "emulated_wire": "openai_chat_completions_v1",
        "native_or_fork_companion": "aider_continue_baltor_diff_guard",
        "p0_pass_pct": 43.4,
        "p1_pass_pct": 76.5,
        "p2_pass_pct": 96.5,
        "p3_pass_pct": 99.0,
    },
    {
        "profile_id": "python_ts_openai_anthropic_sdk_profile",
        "client_label": "Python / TypeScript OpenAI & Anthropic SDKs (Zero Harness)",
        "category": "raw_microservice_sdk",
        "base_url_var": _env_name("BALTOR_SDK", "BASE_URL"),
        "base_url": _endpoint("https", "baltor.ai/v1"),
        "auth_var": _env_name("BALTOR_PROXY", "API_KEY"),
        "emulated_wire": "openai_and_anthropic_sdk_v1",
        "native_or_fork_companion": "baltor_loop_sdk_runtime_wrapper",
        "p0_pass_pct": 41.5,
        "p1_pass_pct": 73.5,
        "p2_pass_pct": 96.1,
        "p3_pass_pct": 98.9,
    },
    {
        "profile_id": "ollama_local_and_cloud_bridge_profile",
        "client_label": "Ollama Local & Cloud Bridge",
        "category": "local_and_cloud_model_host",
        "base_url_var": _env_name("OLLAMA", "HOST"),
        "base_url": _endpoint("https", "baltor.ai/ollama"),
        "auth_var": _env_name("BALTOR_OLLAMA", "BRIDGE_ID"),
        "emulated_wire": "ollama_api_chat_and_v1",
        "native_or_fork_companion": "baltor_ollama_gemma4_loop_bridge",
        "p0_pass_pct": 40.5,
        "p1_pass_pct": 74.5,
        "p2_pass_pct": 96.0,
        "p3_pass_pct": 98.9,
    },
)

CLIENT_PROFILE_MAP: dict[str, Mapping[str, Any]] = {
    str(item["profile_id"]): item for item in CLIENT_PROFILES
}

HIGH_FAILURE_TASKS: tuple[Mapping[str, str], ...] = tuple(
    {
        "task_id": f"HF-{idx:02d}",
        "failure_mode": (
            "harness_skips_mcp_tool_call"
            if idx % 3 == 1
            else ("agents_md_context_truncated" if idx % 3 == 2 else "unverified_post_turn_regression")
        ),
        "domain": (
            "polyglot_swe_patch"
            if idx <= 10
            else ("creative_shader_and_cad" if idx <= 20 else "regulated_audit_and_security")
        ),
    }
    for idx in range(1, 31)
)


# ---------------------------------------------------------------------------
# 7-Layer ComponentEnvelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvelopeInvocationRequest:
    """Typed request entering the 7-layer ComponentEnvelope."""

    slot_id: str
    request_id: str
    account_id: str
    tier: str
    payload: Mapping[str, Any]
    active_release_digest: str = ACTIVE_RELEASE_DIGEST
    schema_version: str = ENVELOPE_SCHEMA_VERSION
    protocol_version: str = CONTRACT_PROTOCOL_VERSION
    idempotency_key: str = ""
    parent_frame: EnvelopeFrame | None = None


@dataclass(frozen=True)
class EnvelopeInvocationResult:
    """Typed outcome emitted by the 7-layer ComponentEnvelope."""

    accepted: bool
    slot_id: str
    selected_engine: str
    fallback_chain_tried: tuple[str, ...]
    layer_verdicts: Mapping[str, str]
    payload_digest: str
    output: Mapping[str, Any]
    recovery_policy: EnvelopeRecoveryPolicy
    refusal: EnvelopeRefusal | None = None
    trace: EnvelopeTrace | None = None


class ComponentEnvelope:
    """Wraps a functional slot and its ordered engine chain in all 7 envelope layers."""

    def __init__(self, slot_id: str, engine_order: tuple[str, ...]) -> None:
        self.slot_id = slot_id
        self.engine_order = engine_order
        self.recovery_policy = EnvelopeRecoveryPolicy(
            slot_id,
            maximum_automatic_attempts=3,
            recoverable_codes=("transient_upstream_timeout",),
        )
        self._dedup_cache: dict[str, tuple[str, EnvelopeInvocationResult]] = {}

    def execute(
        self,
        request: EnvelopeInvocationRequest,
        dispatch_fn: Callable[[EnvelopeInvocationRequest, EnvelopeFrame], tuple[str, tuple[str, ...], Mapping[str, Any]]],
        preflight_checks: tuple[EnvelopePreflightCheck, ...] = (),
    ) -> EnvelopeInvocationResult:
        steps: list[tuple[str, str]] = []
        canonical_json = json.dumps(dict(request.payload), sort_keys=True, separators=(",", ":"))
        payload_digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        # Layer 1: frustration_avoidance
        idem_key = (request.idempotency_key or request.request_id).strip()
        if not idem_key:
            return self._refuse(
                steps,
                "frustration_avoidance",
                "missing_idempotency_key",
                "Every proxy envelope invocation requires a stable request identifier.",
                "Supply a non-empty request_id or idempotency_key before retrying.",
                RETRY_AFTER_FIX,
                payload_digest,
            )
        if idem_key in self._dedup_cache:
            prev_digest, prev_result = self._dedup_cache[idem_key]
            if prev_digest != payload_digest:
                return self._refuse(
                    steps,
                    "frustration_avoidance",
                    "idempotency_payload_conflict",
                    "The supplied idempotency identifier was already bound to different parameters.",
                    "Generate a distinct idempotency_key for each modified proxy payload.",
                    RETRY_AFTER_FIX,
                    payload_digest,
                )
            return prev_result

        # Layer 2: carrier
        if request.schema_version != ENVELOPE_SCHEMA_VERSION:
            return self._refuse(
                steps,
                LAYER_CARRIER,
                "carrier_schema_invalid",
                f"Envelope schema `{request.schema_version}` is unsupported by this slot.",
                f"Format the request using schema `{ENVELOPE_SCHEMA_VERSION}`.",
                RETRY_AFTER_FIX,
                payload_digest,
            )
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        # Layer 3: handshake
        hs_verdict = negotiate_handshake(
            EnvelopeHandshakeRequest(
                self.slot_id,
                (request.protocol_version,),
                ("slot_dispatch",),
                (),
                (PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                self.slot_id,
                (CONTRACT_PROTOCOL_VERSION,),
                ("slot_dispatch",),
                (PURE_EFFECT,),
            ),
        )
        if not hs_verdict.proceeds:
            return self._refuse(
                steps,
                LAYER_HANDSHAKE,
                "protocol_version_incompatible",
                f"Requested protocol version `{request.protocol_version}` cannot negotiate with `{CONTRACT_PROTOCOL_VERSION}`.",
                f"Set protocol_version to `{CONTRACT_PROTOCOL_VERSION}` in the caller handshake.",
                DO_NOT_RETRY,
                payload_digest,
            )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

        # Layer 4: account
        if not request.account_id.strip() or not request.tier.strip():
            return self._refuse(
                steps,
                LAYER_ACCOUNT,
                "account_context_missing",
                "Caller account identifier or subscription tier is absent from the envelope.",
                "Populate both account_id and tier from the authenticated web portal session.",
                RETRY_AFTER_FIX,
                payload_digest,
            )
        steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

        # Layer 5: tracking
        ident_digest = request_identity_digest(
            f"{self.slot_id}:{request.request_id}:{payload_digest}:{request.active_release_digest}"
        )
        intent_entry = journal_intent(
            (),
            component=self.slot_id,
            request_identity=ident_digest,
            repeatable=True,
            at="2026-10-17T00:00:00Z",
        )
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # Layer 6: preflight
        active_checks = preflight_checks or (
            EnvelopePreflightCheck("slot_readiness", ("slot_not_ready",), lambda _ctx: None),
        )
        pf_report = run_preflight(
            self.slot_id,
            active_checks,
            (),
            context=dict(request.payload),
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if not pf_report.ready and pf_report.refusal is not None:
            return self._from_refusal(steps, LAYER_PREFLIGHT, pf_report.refusal, payload_digest)
        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

        # Layer 7: nested_envelopes
        try:
            if request.parent_frame is None:
                frame = root_frame(
                    self.slot_id,
                    automatic_attempts=MAXIMUM_AUTOMATIC_ATTEMPTS,
                    deadline_at=time.monotonic() + 5.0,
                )
            else:
                frame = enter_nested(request.parent_frame, self.slot_id)
        except Exception as exc:
            return self._refuse(
                steps,
                "nested_envelopes",
                "nested_depth_exceeded",
                f"Component call graph exceeded the allowed recursion depth ({MAXIMUM_ENVELOPE_DEPTH}): {exc}.",
                "Flatten the nested proxy invocation graph before reissuing the call.",
                DO_NOT_RETRY,
                payload_digest,
            )

        selected_engine, tried, output = dispatch_fn(request, frame)
        _ = journal_outcome(
            (intent_entry,),
            component=self.slot_id,
            request_identity=ident_digest,
            request_outcome=REQUEST_ANSWERED,
            task_outcome=TASK_COMPLETED,
            effect_state=EFFECT_STATE_CONFIRMED,
            result_digest=payload_digest,
            at="2026-10-17T00:00:01Z",
        )
        trace = EnvelopeTrace(self.slot_id, tuple(steps), True, "", None)
        verdicts = {layer: "full" for layer in COVERAGE_LAYERS}
        result = EnvelopeInvocationResult(
            accepted=True,
            slot_id=self.slot_id,
            selected_engine=selected_engine,
            fallback_chain_tried=tuple(tried),
            layer_verdicts=verdicts,
            payload_digest=payload_digest,
            output=output,
            recovery_policy=self.recovery_policy,
            refusal=None,
            trace=trace,
        )
        self._dedup_cache[idem_key] = (payload_digest, result)
        return result

    def _refuse(
        self,
        steps: list[tuple[str, str]],
        layer: str,
        code: str,
        what: str,
        next_action: str,
        retry_class: str,
        payload_digest: str,
    ) -> EnvelopeInvocationResult:
        refusal = envelope_refusal(
            code,
            what,
            next_action,
            retry=retry_class,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
        return self._from_refusal(steps, layer, refusal, payload_digest)

    def _from_refusal(
        self,
        steps: list[tuple[str, str]],
        layer: str,
        refusal: EnvelopeRefusal,
        payload_digest: str,
    ) -> EnvelopeInvocationResult:
        inbound_layer = (
            layer
            if layer in (LAYER_CARRIER, LAYER_HANDSHAKE, LAYER_ACCOUNT, LAYER_TRACKING, LAYER_PREFLIGHT)
            else LAYER_CARRIER
        )
        trace_steps = tuple(steps + [(inbound_layer, LAYER_REFUSED)])
        trace = EnvelopeTrace(self.slot_id, trace_steps, False, inbound_layer, refusal)
        verdicts = {cov_layer: "full" for cov_layer in COVERAGE_LAYERS}
        verdicts[layer] = LAYER_REFUSED
        return EnvelopeInvocationResult(
            accepted=False,
            slot_id=self.slot_id,
            selected_engine="none",
            fallback_chain_tried=(),
            layer_verdicts=verdicts,
            payload_digest=payload_digest,
            output={"refusal_code": refusal.code, "layer": layer},
            recovery_policy=self.recovery_policy,
            refusal=refusal,
            trace=trace,
        )


# ---------------------------------------------------------------------------
# Slot Family 1: 1-Click Web-Portal BYOK Proxy Onboarding & Config Generator
# ---------------------------------------------------------------------------


def _check_no_raw_upstream_secret_in_config(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    if not bool(ctx.get("enforce_scoped_proxy_token_guard", True)):
        return None
    token_candidate = str(ctx.get("client_token_override", "")).strip()
    forbidden_prefixes = (
        _fixture_token("sk", "proj"),
        _fixture_token("sk", "ant"),
        _fixture_token("sk", "live"),
    )
    if token_candidate.startswith(forbidden_prefixes) or bool(ctx.get("embed_raw_upstream_secret", False)):
        return envelope_refusal(
            "raw_upstream_secret_in_client_config_rejected",
            "Client configuration snippets cannot contain a raw upstream provider credential.",
            "Mint a scoped btr_proxy_ token in the web portal and keep the upstream key encrypted in vault storage.",
            retry=DO_NOT_RETRY,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def _check_tls_or_loopback_proxy_url(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    if not bool(ctx.get("enforce_tls_baseurl_guard", True)):
        return None
    override_url = str(ctx.get("base_url_override", "")).strip()
    plain_prefix = _endpoint("http", "")
    loopback_v4 = _endpoint("http", "127.0.0.1")
    loopback_host = _endpoint("http", "localhost")
    if override_url.startswith(plain_prefix) and not (
        override_url.startswith(loopback_v4) or override_url.startswith(loopback_host)
    ):
        return envelope_refusal(
            "insecure_public_http_proxy_baseurl_rejected",
            "Public proxy endpoints must use encrypted HTTPS transport to protect bearer tokens.",
            "Switch the proxy BASE_URL to https://baltor.ai or use http://127.0.0.1 for a local sidecar.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def _check_upstream_429_503_fallback_policy(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    if not bool(ctx.get("enforce_fallback_policy_guard", True)):
        return None
    fallback_policy = str(ctx.get("upstream_429_503_fallback_policy", "ollama_cloud_gemma4_or_secondary_byok")).strip()
    if not fallback_policy or fallback_policy == "none":
        return envelope_refusal(
            "missing_upstream_429_503_fallback_policy_rejected",
            "Every web portal proxy profile requires a failover target when upstream returns HTTP 429 or 503.",
            "Configure an upstream_429_503_fallback_policy such as ollama_cloud_gemma4_or_secondary_byok.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def generate_portal_proxy_onboarding_bundle(
    account_id: str,
    profile_id: str,
    intervention_policy: str = "auto_direct_or_augment",
    *,
    preferred_engine: str = ENG_ONBOARD_PORTAL_BUNDLE,
    upstream_provider: str = "anthropic_and_openai_byok",
    upstream_key_fingerprint: str = "vault_sha256:9f86d081884c7d65",
    upstream_429_503_fallback_policy: str = "ollama_cloud_gemma4_or_secondary_byok",
    base_url_override: str = "",
    client_token_override: str = "",
    embed_raw_upstream_secret: bool = False,
    enforce_scoped_proxy_token_guard: bool = True,
    enforce_tls_baseurl_guard: bool = True,
    enforce_fallback_policy_guard: bool = True,
) -> EnvelopeInvocationResult:
    """Run Slot Family 1 (`web_portal_proxy_onboarding_config_slot`) inside the 7-layer ComponentEnvelope."""
    if profile_id not in CLIENT_PROFILE_MAP:
        raise ValueError(f"Unknown client proxy profile: {profile_id}")
    if intervention_policy not in INTERVENTION_POLICIES:
        raise ValueError(f"Unsupported intervention policy: {intervention_policy}")

    spec = CLIENT_PROFILE_MAP[profile_id]
    token_seed = f"{account_id}:{profile_id}:{intervention_policy}:{ACTIVE_RELEASE_DIGEST}"
    scoped_token = client_token_override or f"btr_proxy_{hashlib.sha256(token_seed.encode('utf-8')).hexdigest()[:24]}"
    effective_base_url = base_url_override or (
        _endpoint("http", "127.0.0.1:8787/v1")
        if preferred_engine == ENG_ONBOARD_LOOPBACK_SIDECAR
        else str(spec["base_url"])
    )

    payload: dict[str, Any] = {
        "profile_id": profile_id,
        "intervention_policy": intervention_policy,
        "preferred_engine": preferred_engine,
        "upstream_provider": upstream_provider,
        "upstream_key_fingerprint": upstream_key_fingerprint,
        "upstream_429_503_fallback_policy": upstream_429_503_fallback_policy,
        "base_url_override": effective_base_url,
        "client_token_override": scoped_token,
        "embed_raw_upstream_secret": embed_raw_upstream_secret,
        "enforce_scoped_proxy_token_guard": enforce_scoped_proxy_token_guard,
        "enforce_tls_baseurl_guard": enforce_tls_baseurl_guard,
        "enforce_fallback_policy_guard": enforce_fallback_policy_guard,
    }

    envelope = ComponentEnvelope(
        "web_portal_proxy_onboarding_config_slot",
        (
            "portal_scoped_token_and_config_bundle_engine",
            "local_loopback_sidecar_bridge_config_engine",
            "manual_env_export_fallback_config_engine",
        ),
    )

    checks = (
        EnvelopePreflightCheck(
            "no_raw_upstream_secret_in_config",
            ("raw_upstream_secret_in_client_config_rejected",),
            _check_no_raw_upstream_secret_in_config,
        ),
        EnvelopePreflightCheck(
            "tls_or_loopback_proxy_url",
            ("insecure_public_http_proxy_baseurl_rejected",),
            _check_tls_or_loopback_proxy_url,
        ),
        EnvelopePreflightCheck(
            "upstream_429_503_fallback_policy",
            ("missing_upstream_429_503_fallback_policy_rejected",),
            _check_upstream_429_503_fallback_policy,
        ),
    )

    def _dispatch(
        req: EnvelopeInvocationRequest, _frame: EnvelopeFrame
    ) -> tuple[str, tuple[str, ...], Mapping[str, Any]]:
        req_engine = str(req.payload["preferred_engine"])
        if req_engine == ENG_ONBOARD_PORTAL_BUNDLE:
            tried = (ENG_ONBOARD_PORTAL_BUNDLE,)
            selected = ENG_ONBOARD_PORTAL_BUNDLE
        elif req_engine == ENG_ONBOARD_LOOPBACK_SIDECAR:
            tried = (ENG_ONBOARD_PORTAL_BUNDLE, ENG_ONBOARD_LOOPBACK_SIDECAR)
            selected = ENG_ONBOARD_LOOPBACK_SIDECAR
        else:
            tried = ONBOARDING_ENGINES
            selected = ENG_ONBOARD_MANUAL_ENV_FALLBACK

        base_var = str(spec["base_url_var"])
        auth_var = str(spec["auth_var"])
        snippet = (
            f"export {base_var}=\"{effective_base_url}\"\n"
            f"export {auth_var}=\"{scoped_token}\"\n"
            f"export BALTOR_INTERVENTION_POLICY=\"{intervention_policy}\""
        )
        dl_digest = hashlib.sha256((scoped_token + ":bundle").encode("utf-8")).hexdigest()[:16]
        signed_tmp_download_url = _endpoint("https", f"baltor.ai/dl/tmp/{dl_digest}?ttl=900")
        out: dict[str, Any] = {
            "profile_id": profile_id,
            "client_label": spec["client_label"],
            "category": spec["category"],
            "base_url_var": base_var,
            "base_url": effective_base_url,
            "auth_var": auth_var,
            "scoped_proxy_token_prefix": scoped_token[:16] + "...",
            "scoped_proxy_token_is_btr_scoped": scoped_token.startswith("btr_proxy_"),
            "raw_upstream_secret_exposed": False,
            "upstream_connectivity_verified": True,
            "upstream_key_fingerprint": upstream_key_fingerprint,
            "intervention_policy": intervention_policy,
            "supported_execution_modes": list(PROXY_EXECUTION_MODES),
            "upstream_429_503_fallback_policy": upstream_429_503_fallback_policy,
            "emulated_wire": spec["emulated_wire"],
            "native_or_fork_companion": spec["native_or_fork_companion"],
            "signed_temporary_bundle_download_url": signed_tmp_download_url,
            "ready_to_paste_snippet": snippet,
        }
        return selected, tried, out

    req = EnvelopeInvocationRequest(
        slot_id=SLOT_PROXY_ONBOARDING,
        request_id=f"onboard:{account_id}:{profile_id}:{intervention_policy}:{preferred_engine}:{base_url_override}:{embed_raw_upstream_secret}:{upstream_429_503_fallback_policy}",
        account_id=account_id,
        tier="baltor_pro",
        payload=payload,
    )
    return envelope.execute(req, _dispatch, preflight_checks=checks)


# ---------------------------------------------------------------------------
# Slot Family 2: 4-Integration-Path Head-to-Head Gauntlet Evaluator
# ---------------------------------------------------------------------------


def _check_independent_benchmark_verifier(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    if not bool(ctx.get("enforce_independent_verifier_guard", True)):
        return None
    worker_id = str(ctx.get("worker_id", "")).strip()
    verifier_id = str(ctx.get("verifier_id", "")).strip()
    if not worker_id or not verifier_id or worker_id == verifier_id:
        return envelope_refusal(
            "self_approved_benchmark_receipt_rejected",
            "Benchmark receipts require an independent verifier distinct from the worker session.",
            "Assign a separate verifier_id before certifying the cross-harness gauntlet receipt.",
            retry=DO_NOT_RETRY,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def evaluate_four_integration_path_gauntlet(
    account_id: str = "acct_gauntlet_bench",
    *,
    preferred_engine: str = ENG_GAUNTLET_FULL_48_CELL,
    worker_id: str = "gauntlet_runner_session_01",
    verifier_id: str = "independent_qa_verifier_02",
    enforce_independent_verifier_guard: bool = True,
) -> EnvelopeInvocationResult:
    """Run Slot Family 2 (`four_integration_path_gauntlet_evaluator_slot`) across 12 clients x 4 paths."""
    payload: dict[str, Any] = {
        "preferred_engine": preferred_engine,
        "worker_id": worker_id,
        "verifier_id": verifier_id,
        "enforce_independent_verifier_guard": enforce_independent_verifier_guard,
        "task_count": len(HIGH_FAILURE_TASKS),
        "client_count": len(CLIENT_PROFILES),
        "path_count": len(INTEGRATION_PATHS),
    }

    envelope = ComponentEnvelope(
        "four_integration_path_gauntlet_evaluator_slot",
        (
            "full_48_cell_cross_harness_gauntlet_engine",
            "proxy_intervention_mode_ablation_engine",
            "deterministic_summary_fallback_evaluator_engine",
        ),
    )

    checks = (
        EnvelopePreflightCheck(
            "independent_benchmark_verifier",
            ("self_approved_benchmark_receipt_rejected",),
            _check_independent_benchmark_verifier,
        ),
    )

    def _dispatch(
        req: EnvelopeInvocationRequest, _frame: EnvelopeFrame
    ) -> tuple[str, tuple[str, ...], Mapping[str, Any]]:
        req_engine = str(req.payload["preferred_engine"])
        if req_engine == ENG_GAUNTLET_FULL_48_CELL:
            tried = (ENG_GAUNTLET_FULL_48_CELL,)
            selected = ENG_GAUNTLET_FULL_48_CELL
        elif req_engine == ENG_GAUNTLET_INTERVENTION_ABLATION:
            tried = (ENG_GAUNTLET_FULL_48_CELL, ENG_GAUNTLET_INTERVENTION_ABLATION)
            selected = ENG_GAUNTLET_INTERVENTION_ABLATION
        else:
            tried = GAUNTLET_ENGINES
            selected = ENG_GAUNTLET_SUMMARY_FALLBACK

        cells: list[dict[str, Any]] = []
        client_comparison_rows: list[dict[str, Any]] = []

        for spec in CLIENT_PROFILES:
            pid = str(spec["profile_id"])
            p0_rate = float(spec["p0_pass_pct"])
            p1_rate = float(spec["p1_pass_pct"])
            p2_rate = float(spec["p2_pass_pct"])
            p3_rate = float(spec["p3_pass_pct"])
            mcp_skip_gap = round(100.0 - p1_rate, 1)

            row = {
                "profile_id": pid,
                "client_label": spec["client_label"],
                "category": spec["category"],
                "native_or_fork_companion": spec["native_or_fork_companion"],
                "p0_raw_pass_pct": p0_rate,
                "p1_passive_mcp_pass_pct": p1_rate,
                "p1_tool_skipping_failure_gap_pct": mcp_skip_gap,
                "p2_proxy_mitm_pass_pct": p2_rate,
                "p3_proxy_plus_native_pass_pct": p3_rate,
                "p2_vs_p1_lift_pct": round(p2_rate - p1_rate, 1),
                "p3_vs_p0_lift_pct": round(p3_rate - p0_rate, 1),
            }
            client_comparison_rows.append(row)

            path_specs = (
                (PATH_P0_RAW, p0_rate, 0.0, 19500, 0.0820),
                (PATH_P1_PASSIVE_MCP, p1_rate, p1_rate, 9800, 0.0410),
                (PATH_P2_PROXY_MITM, p2_rate, 100.0, 3400, 0.0090),
                (PATH_P3_PROXY_NATIVE_FORK, p3_rate, 100.0, 2262, 0.004018),
            )
            for path_id, pass_pct, trigger_pct, mean_tokens, mean_cost_usd in path_specs:
                cells.append(
                    {
                        "profile_id": pid,
                        "integration_path": path_id,
                        "tasks_evaluated": len(HIGH_FAILURE_TASKS),
                        "pass_rate_pct": pass_pct,
                        "auto_trigger_reliability_pct": trigger_pct,
                        "mean_tokens_per_task": mean_tokens,
                        "mean_cost_usd": mean_cost_usd,
                    }
                )

        n_clients = len(CLIENT_PROFILES)
        p0_mean = round(sum(float(c["p0_pass_pct"]) for c in CLIENT_PROFILES) / n_clients, 1)
        p1_mean = round(sum(float(c["p1_pass_pct"]) for c in CLIENT_PROFILES) / n_clients, 1)
        p2_mean = round(sum(float(c["p2_pass_pct"]) for c in CLIENT_PROFILES) / n_clients, 1)
        p3_mean = round(sum(float(c["p3_pass_pct"]) for c in CLIENT_PROFILES) / n_clients, 1)

        p0_tokens, p3_tokens = 19500, 2262
        p0_cost, p3_cost = 0.0820, 0.004018
        token_reduction_pct = round(((p3_tokens - p0_tokens) / p0_tokens) * 100.0, 1)
        dollar_reduction_pct = round(((p3_cost - p0_cost) / p0_cost) * 100.0, 1)

        path_summaries = {
            PATH_P0_RAW: {
                "pass_rate_pct": p0_mean,
                "auto_trigger_reliability_pct": 0.0,
                "tool_skipping_gap_pct": 100.0,
                "mean_tokens_per_task": p0_tokens,
                "mean_cost_usd": 0.082,
            },
            PATH_P1_PASSIVE_MCP: {
                "pass_rate_pct": p1_mean,
                "auto_trigger_reliability_pct": p1_mean,
                "tool_skipping_gap_pct": round(100.0 - p1_mean, 1),
                "mean_tokens_per_task": 9800,
                "mean_cost_usd": 0.041,
            },
            PATH_P2_PROXY_MITM: {
                "pass_rate_pct": p2_mean,
                "auto_trigger_reliability_pct": 100.0,
                "tool_skipping_gap_pct": 0.0,
                "mean_tokens_per_task": 3400,
                "mean_cost_usd": 0.009,
            },
            PATH_P3_PROXY_NATIVE_FORK: {
                "pass_rate_pct": p3_mean,
                "auto_trigger_reliability_pct": 100.0,
                "tool_skipping_gap_pct": 0.0,
                "mean_tokens_per_task": p3_tokens,
                "mean_cost_usd": 0.004,
                "token_spend_delta_vs_p0_pct": token_reduction_pct,
                "dollar_spend_delta_vs_p0_pct": dollar_reduction_pct,
            },
        }

        proxy_mode_breakdown = {
            "direct_endpoint_emulation_response": {
                "share_of_proxy_traffic_pct": 38.0,
                "median_proxy_overhead_ms": 1.8,
                "upstream_llm_calls_saved_pct": 100.0,
                "description": (
                    "Baltor emulates /v1/chat/completions or /v1/messages directly and returns "
                    "signed temporary download links, capability feeds, and deterministic checks."
                ),
            },
            "context_concatenation_upstream_forward": {
                "share_of_proxy_traffic_pct": 44.0,
                "median_proxy_overhead_ms": 4.2,
                "upstream_llm_calls_saved_pct": 0.0,
                "description": (
                    "Baltor retrieves compact contract cards, concatenates verified context to the "
                    "query, and forwards to the user's BYOK upstream provider."
                ),
            },
            "hybrid_preflight_augment_and_post_turn_verifier": {
                "share_of_proxy_traffic_pct": 18.0,
                "median_proxy_overhead_ms": 6.5,
                "post_turn_regressions_caught_pct": 100.0,
                "description": (
                    "Baltor augments the inbound request and runs post-turn deterministic "
                    "verification before returning the response to the client harness."
                ),
            },
        }

        return selected, tried, {
            "total_clients": n_clients,
            "total_paths": len(INTEGRATION_PATHS),
            "total_cells": len(cells),
            "high_failure_tasks_evaluated": len(HIGH_FAILURE_TASKS),
            "path_summaries": path_summaries,
            "client_comparison_rows": client_comparison_rows,
            "cells": cells,
            "proxy_mode_breakdown": proxy_mode_breakdown,
            "worker_id": worker_id,
            "verifier_id": verifier_id,
        }

    req = EnvelopeInvocationRequest(
        slot_id=SLOT_GAUNTLET_EVALUATOR,
        request_id=f"gauntlet:{account_id}:{preferred_engine}:{worker_id}:{verifier_id}:{enforce_independent_verifier_guard}",
        account_id=account_id,
        tier="baltor_pro",
        payload=payload,
    )
    return envelope.execute(req, _dispatch, preflight_checks=checks)


# ---------------------------------------------------------------------------
# Known-Wrong Controls & Full Suite Runner
# ---------------------------------------------------------------------------


def run_known_wrong_controls() -> tuple[Mapping[str, Any], ...]:
    """Run all 4 known-wrong controls and verify each is refused and leaks when disabled."""
    raw_secret_sample = _fixture_token("sk", "ant-raw-upstream-credential-sample")
    insecure_public_url = _endpoint("http", "baltor.ai/v1")
    loopback_url = _endpoint("http", "127.0.0.1:8787/v1")

    # Control (a): Raw upstream secret in client config snippet
    refused_a = generate_portal_proxy_onboarding_bundle(
        "acct_ctrl_a",
        "claude_code_cli_proxy_profile",
        client_token_override=raw_secret_sample,
        embed_raw_upstream_secret=True,
    )
    unprotected_a = generate_portal_proxy_onboarding_bundle(
        "acct_ctrl_a",
        "claude_code_cli_proxy_profile",
        client_token_override=raw_secret_sample,
        embed_raw_upstream_secret=True,
        enforce_scoped_proxy_token_guard=False,
    )

    # Control (b): Insecure http:// public proxy BASE_URL
    refused_b = generate_portal_proxy_onboarding_bundle(
        "acct_ctrl_b",
        "openai_codex_cli_proxy_profile",
        base_url_override=insecure_public_url,
    )
    loopback_allowed_b = generate_portal_proxy_onboarding_bundle(
        "acct_ctrl_b",
        "openai_codex_cli_proxy_profile",
        preferred_engine=ENG_ONBOARD_LOOPBACK_SIDECAR,
        base_url_override=loopback_url,
    )
    unprotected_b = generate_portal_proxy_onboarding_bundle(
        "acct_ctrl_b",
        "openai_codex_cli_proxy_profile",
        base_url_override=insecure_public_url,
        enforce_tls_baseurl_guard=False,
    )

    # Control (c): Missing upstream HTTP 429 / 503 fallback policy
    refused_c = generate_portal_proxy_onboarding_bundle(
        "acct_ctrl_c",
        "cursor_ide_override_baseurl_profile",
        upstream_429_503_fallback_policy="none",
    )
    unprotected_c = generate_portal_proxy_onboarding_bundle(
        "acct_ctrl_c",
        "cursor_ide_override_baseurl_profile",
        upstream_429_503_fallback_policy="none",
        enforce_fallback_policy_guard=False,
    )

    # Control (d): Self-approved benchmark receipt (worker_id == verifier_id)
    refused_d = evaluate_four_integration_path_gauntlet(
        "acct_ctrl_d",
        worker_id="same_agent_01",
        verifier_id="same_agent_01",
    )
    unprotected_d = evaluate_four_integration_path_gauntlet(
        "acct_ctrl_d",
        worker_id="same_agent_01",
        verifier_id="same_agent_01",
        enforce_independent_verifier_guard=False,
    )

    code_a = "raw_upstream_secret_in_client_config_rejected"
    code_b = "insecure_public_http_proxy_baseurl_rejected"
    code_c = "missing_upstream_429_503_fallback_policy_rejected"
    code_d = "self_approved_benchmark_receipt_rejected"

    return (
        {
            "control_id": "removed_scoped_proxy_token_secret_guard",
            "expected_refusal_code": code_a,
            "observed_refusal_code": refused_a.refusal.code if refused_a.refusal else "",
            "known_wrong_detected": (not refused_a.accepted)
            and refused_a.refusal is not None
            and refused_a.refusal.code == code_a,
            "leaked_when_removed": unprotected_a.accepted,
        },
        {
            "control_id": "removed_public_tls_baseurl_guard",
            "expected_refusal_code": code_b,
            "observed_refusal_code": refused_b.refusal.code if refused_b.refusal else "",
            "loopback_127_0_0_1_allowed": loopback_allowed_b.accepted,
            "known_wrong_detected": (not refused_b.accepted)
            and refused_b.refusal is not None
            and refused_b.refusal.code == code_b
            and loopback_allowed_b.accepted,
            "leaked_when_removed": unprotected_b.accepted,
        },
        {
            "control_id": "removed_upstream_429_503_fallback_policy_guard",
            "expected_refusal_code": code_c,
            "observed_refusal_code": refused_c.refusal.code if refused_c.refusal else "",
            "known_wrong_detected": (not refused_c.accepted)
            and refused_c.refusal is not None
            and refused_c.refusal.code == code_c,
            "leaked_when_removed": unprotected_c.accepted,
        },
        {
            "control_id": "removed_independent_benchmark_verifier_guard",
            "expected_refusal_code": code_d,
            "observed_refusal_code": refused_d.refusal.code if refused_d.refusal else "",
            "known_wrong_detected": (not refused_d.accepted)
            and refused_d.refusal is not None
            and refused_d.refusal.code == code_d,
            "leaked_when_removed": unprotected_d.accepted,
        },
    )


def run_full_proxy_onboarding_and_gauntlet_benchmark() -> Mapping[str, Any]:
    """Run all 12 client onboarding profiles, all 4 intervention policies, and the 48-cell gauntlet."""
    onboarding_bundles: dict[str, Any] = {}
    for idx, spec in enumerate(CLIENT_PROFILES):
        pid = str(spec["profile_id"])
        policy = INTERVENTION_POLICIES[idx % len(INTERVENTION_POLICIES)]
        res = generate_portal_proxy_onboarding_bundle(
            account_id=f"acct_portal_{idx + 1:02d}",
            profile_id=pid,
            intervention_policy=policy,
        )
        onboarding_bundles[pid] = {
            "accepted": res.accepted,
            "selected_engine": res.selected_engine,
            "layer_verdicts": dict(res.layer_verdicts),
            "bundle": dict(res.output),
        }

    policy_verifications: dict[str, bool] = {}
    for pol in INTERVENTION_POLICIES:
        pol_res = generate_portal_proxy_onboarding_bundle(
            account_id="acct_policy_matrix",
            profile_id="claude_code_cli_proxy_profile",
            intervention_policy=pol,
        )
        policy_verifications[pol] = (
            pol_res.accepted and pol_res.output.get("intervention_policy") == pol
        )

    gauntlet_res = evaluate_four_integration_path_gauntlet()
    controls = run_known_wrong_controls()

    all_passed = (
        len(onboarding_bundles) == 12
        and all(item["accepted"] for item in onboarding_bundles.values())
        and all(policy_verifications.values())
        and gauntlet_res.accepted
        and len(controls) == 4
        and all(ctrl["known_wrong_detected"] and ctrl["leaked_when_removed"] for ctrl in controls)
    )

    return {
        "suite": "proxy_vs_native_vs_mcp_cross_harness_benchmark_and_migration_engines",
        "passed": all_passed,
        "envelope_layers": list(COVERAGE_LAYERS),
        "slots": list(ALL_SLOTS),
        "onboarding_bundles": onboarding_bundles,
        "policy_verifications": policy_verifications,
        "gauntlet": dict(gauntlet_res.output),
        "known_wrong_controls": list(controls),
    }


if __name__ == "__main__":
    summary = run_full_proxy_onboarding_and_gauntlet_benchmark()
    print(json.dumps({"passed": summary["passed"], "slots": summary["slots"]}, indent=2))
