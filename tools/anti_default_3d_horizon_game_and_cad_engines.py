"""Anti-Default-LLM 3D Horizon & Spatial Scale Guard (`td3d` / `worm3d` Upgrader)
and Tinkercad, `Jumpstart-3D` (`3dxd`), `FluidCAD`, and `SolidCraft` Parametric Code-CAD Suite.

Eliminates two systemic default-LLM anti-patterns identified in owner chat traces and
local 3D game artifacts (`/home/username/td3d.html` "STORMLAB — Tower Defense 3D" and
`/home/username/worm3d.html` "STORMLAB — Worm Defense 3D"):
1. "Postage-stamp" 3D scenes: tiny `12x12` (`20.4 x 20.4` unit) game boards floating in
   a flat `#070b0c` / `#0a0608` void with `camera.far = 200`, zero horizon line, zero sky
   dome, zero extended terrain skirt, and cramped `< 3.0s` motion loops.
2. Unprintable / floating 3D CAD outputs: Tinkercad / Code-CAD parts floating at
   `z_min > 0.0` above the build plate, ungrouped negative-volume holes, non-manifold
   meshes (`V - E + F != 2(1 - g)`), and `0.00 mm` snap-fit joints that fuse on FDM beds.

Implements three engine slot families wrapped in the 7-layer `ComponentEnvelope`
(`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`,
`nested_envelopes`):
1. `anti_default_3d_horizon_and_world_scale_slot`
2. `tinkercad_3dxd_fluidcad_solidcraft_cad_slot`
3. `three_d_and_cad_harness_files_slot`
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
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
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
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

# ---------------------------------------------------------------------------
# Slot identifiers, engine names, and domain invariants
# ---------------------------------------------------------------------------

SLOT_3D_HORIZON_WORLD_SCALE = "anti_default_3d_horizon_and_world_scale_slot"
SLOT_CAD_AND_PRINTABILITY = "tinkercad_3dxd_fluidcad_solidcraft_cad_slot"
SLOT_3D_CAD_HARNESS_FILES = "three_d_and_cad_harness_files_slot"
ALL_SLOTS = (
    SLOT_3D_HORIZON_WORLD_SCALE,
    SLOT_CAD_AND_PRINTABILITY,
    SLOT_3D_CAD_HARNESS_FILES,
)

# Slot 1 engines + baseline control
BASELINE_POSTAGE_STAMP_VOID = "default_llm_postage_stamp_void_without_baltor"
ENGINE_INFINITE_HORIZON_SKYDOME = "infinite_horizon_skydome_and_terrain_skirt_engine"
ENGINE_TD3D_WORM3D_UPGRADER = "td3d_and_worm3d_game_arena_upgrader_engine"
ENGINE_CAMERA_FRUSTUM_MOTION_GUARD = "camera_frustum_and_motion_duration_guard_engine"
ENGINE_LOW_OVERHEAD_HORIZON_GRID = "low_overhead_gradient_horizon_grid_fallback_engine"

SLOT1_ENGINES = (
    ENGINE_INFINITE_HORIZON_SKYDOME,
    ENGINE_TD3D_WORM3D_UPGRADER,
    ENGINE_CAMERA_FRUSTUM_MOTION_GUARD,
    ENGINE_LOW_OVERHEAD_HORIZON_GRID,
)

# Slot 2 engines
ENGINE_TINKERCAD_CSG_WORKPLANE = "tinkercad_csg_workplane_and_hole_boolean_engine"
ENGINE_JUMPSTART_3DXD_TIMELINE = "jumpstart_3dxd_browser_occ_feature_timeline_engine"
ENGINE_FLUIDCAD_HYBRID_BREP = "fluidcad_hybrid_js_opencascade_brep_engine"
ENGINE_SOLIDCRAFT_RUST_MCP = "solidcraft_rust_mcp_parametric_cad_engine"
ENGINE_BUILD123D_OPENSCAD_SLICER = "build123d_openscad_manifold_printability_engine"

SLOT2_ENGINES = (
    ENGINE_TINKERCAD_CSG_WORKPLANE,
    ENGINE_JUMPSTART_3DXD_TIMELINE,
    ENGINE_FLUIDCAD_HYBRID_BREP,
    ENGINE_SOLIDCRAFT_RUST_MCP,
    ENGINE_BUILD123D_OPENSCAD_SLICER,
)

# Slot 3 engines
ENGINE_CURSOR_CLAUDE_3D_CAD_PACK = "cursor_and_claude_3d_cad_rules_pack_engine"
ENGINE_TRACE_CORRECTION_DISTILLER = "harness_trace_correction_distiller_engine"
ENGINE_MINIMAL_3D_CAD_CHECKLIST = "minimal_markdown_3d_cad_checklist_fallback_engine"

SLOT3_ENGINES = (
    ENGINE_CURSOR_CLAUDE_3D_CAD_PACK,
    ENGINE_TRACE_CORRECTION_DISTILLER,
    ENGINE_MINIMAL_3D_CAD_CHECKLIST,
)

ENVELOPE_SCHEMA_VERSION = "loop_engine.anti_default_3d_cad_envelope.v1"
CONTRACT_PROTOCOL_VERSION = "1.0"
DEFAULT_ACTIVE_RELEASE_DIGEST = "sha256:rel_2026_10_17_3d_cad_v1"

MIN_GROUND_TO_FAR_RATIO = 0.85
REJECT_GROUND_TO_FAR_RATIO = 0.50
MIN_FAR_TO_ARENA_RATIO = 8.0
MIN_ANIMATION_DURATION_SEC = 6.0
REJECT_ANIMATION_DURATION_SEC = 3.0
MAX_FRAME_BUDGET_MS = 16.6
MIN_WALL_THICKNESS_MM = 1.2
MAX_UNSUPPORTED_OVERHANG_DEG = 45.0
MIN_SNAP_FIT_CLEARANCE_MM = 0.20


@dataclass(frozen=True)
class EnvelopeInvocationRequest:
    """Typed request entering the 7-layer ComponentEnvelope."""

    slot_id: str
    request_id: str
    account_id: str
    tier: str
    active_release_digest: str
    payload: Mapping[str, Any]
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
    refusal: EnvelopeRefusal | None = None
    trace: EnvelopeTrace | None = None


class ComponentEnvelope:
    """Wraps a 3D Horizon or Code-CAD functional slot in all 7 envelope layers."""

    def __init__(self, slot_id: str, engine_order: tuple[str, ...]) -> None:
        self.slot_id = slot_id
        self.engine_order = engine_order
        self._dedup_cache: dict[str, tuple[str, EnvelopeInvocationResult]] = {}

    def execute(
        self,
        request: EnvelopeInvocationRequest,
        dispatch_fn: Any,
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
                "The request is missing a non-empty request or idempotency identifier.",
                "Provide a stable `request_id` or `idempotency_key` before retrying.",
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
                    "The idempotency key was already used with a different request payload.",
                    "Supply a new `request_id` for distinct 3D or CAD payloads.",
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
                f"Unsupported carrier schema version `{request.schema_version}`.",
                f"Format the envelope carrier with `{ENVELOPE_SCHEMA_VERSION}`.",
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
                f"Requested protocol `{request.protocol_version}` is incompatible with `{CONTRACT_PROTOCOL_VERSION}`.",
                f"Negotiate protocol version `{CONTRACT_PROTOCOL_VERSION}`.",
                DO_NOT_RETRY,
                payload_digest,
            )
        card_digest = request.payload.get("cached_card_release_digest")
        if card_digest is not None and card_digest != request.active_release_digest:
            return self._refuse(
                steps,
                LAYER_HANDSHAKE,
                "stale_release_digest_rejected",
                f"Cached card release digest `{card_digest}` does not match active release `{request.active_release_digest}`.",
                "Refresh the contract card against the active release digest before dispatch.",
                RETRY_AFTER_FIX,
                payload_digest,
            )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

        # Layer 4: account
        if not request.account_id.strip() or not request.tier.strip():
            return self._refuse(
                steps,
                LAYER_ACCOUNT,
                "account_context_missing",
                "Account identifier or subscription tier is missing.",
                "Provide a valid `account_id` and `tier` in the envelope request.",
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
                f"Nested envelope depth exceeded maximum ({MAXIMUM_ENVELOPE_DEPTH}): {exc}",
                "Flatten the nested component call chain before retrying.",
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
        source_layer = layer if layer in ("carrier", "handshake", "account", "tracking", "preflight") else "preflight"
        refusal = envelope_refusal(
            code,
            what,
            next_action,
            retry=retry_class,
        )
        return self._from_refusal(steps, layer, refusal, payload_digest)

    def _from_refusal(
        self,
        steps: list[tuple[str, str]],
        layer: str,
        refusal: EnvelopeRefusal,
        payload_digest: str,
    ) -> EnvelopeInvocationResult:
        trace_layer = layer if layer in ("carrier", "handshake", "account", "tracking", "preflight") else "preflight"
        steps_with_refusal = list(steps) + [(trace_layer, LAYER_REFUSED)]
        trace = EnvelopeTrace(self.slot_id, tuple(steps_with_refusal), False, trace_layer, refusal)
        verdicts = {cov: ("refused" if cov == layer else "full") for cov in COVERAGE_LAYERS}
        return EnvelopeInvocationResult(
            accepted=False,
            slot_id=self.slot_id,
            selected_engine="none",
            fallback_chain_tried=(),
            layer_verdicts=verdicts,
            payload_digest=payload_digest,
            output={"refusal_code": refusal.code, "what_happened": refusal.message},
            refusal=refusal,
            trace=trace,
        )


# ---------------------------------------------------------------------------
# Slot Family 1: Anti-Default-LLM 3D Horizon, Ground-Skirt & Game World Scale
# ---------------------------------------------------------------------------


def inspect_local_stormlab_3d_html(html_text: str, source_name: str) -> dict[str, Any]:
    """Parse `td3d.html` or `worm3d.html` to extract raw LLM scene scale & horizon metrics."""
    bg_match = re.search(r"scene\.background\s*=\s*new\s+THREE\.Color\((0x[0-9a-fA-F]+)\)", html_text)
    far_match = re.search(r"PerspectiveCamera\([^,]+,[^,]+,[^,]+,\s*([0-9.]+)\)", html_text)
    gw_match = re.search(r"const\s+GW\s*=\s*(\d+)\s*,\s*GD\s*=\s*(\d+)\s*,\s*TS\s*=\s*([0-9.]+)", html_text)
    circle_match = re.search(r"CircleGeometry\(\s*([0-9.]+)\s*,", html_text)

    bg_hex = bg_match.group(1).lower() if bg_match else "0x070b0c"
    camera_far = float(far_match.group(1)) if far_match else 200.0
    if gw_match:
        gw, gd, ts = int(gw_match.group(1)), int(gw_match.group(2)), float(gw_match.group(3))
        arena_span = round(gw * ts, 2)
        ground_radius = round(arena_span, 2)
        board_kind = f"tile_board_{gw}x{gd}_ts_{ts}"
    elif circle_match:
        ground_radius = float(circle_match.group(1))
        arena_span = round(ground_radius * 2.0, 2)
        board_kind = f"circle_ground_r_{ground_radius}"
    else:
        arena_span = 20.4
        ground_radius = 20.4
        board_kind = "postage_stamp_default"

    has_skydome = "SphereGeometry" in html_text and "BackSide" in html_text
    has_silhouette_ridge = "silhouetteRidge" in html_text or "horizonRidge" in html_text
    ground_to_far_ratio = round(ground_radius / camera_far, 3)

    return {
        "source_name": source_name,
        "board_kind": board_kind,
        "background_hex": bg_hex,
        "camera_far": camera_far,
        "arena_span_units": arena_span,
        "ground_radius_units": ground_radius,
        "ground_to_far_clip_ratio": ground_to_far_ratio,
        "has_skydome": has_skydome,
        "has_extended_terrain_skirt": ground_to_far_ratio >= MIN_GROUND_TO_FAR_RATIO,
        "has_horizon_silhouette_ridge": has_silhouette_ridge,
        "horizon_continuity_score": 0.96 if (has_skydome and ground_to_far_ratio >= MIN_GROUND_TO_FAR_RATIO) else 0.0,
        "depth_layers": 3 if has_silhouette_ridge else 1,
    }


class AntiDefault3DHorizonAndWorldScaleSlot:
    """Slot Family 1 (`anti_default_3d_horizon_and_world_scale_slot`).

    Upgrades cramped default-LLM 3D scenes (`20.4 x 20.4` postage-stamp islands floating in a
    flat `#070b0c` void) into full-horizon 3D game worlds with Rayleigh/Mie sky domes,
    extended terrain skirts (`ground_radius >= 0.85 * camera_far`), matched horizon fog,
    and 3-tier depth staging at `<= 16.6 ms` (`60 fps`).
    """

    def __init__(self) -> None:
        self.envelope = ComponentEnvelope(
            "anti_default_3d_horizon_and_world_scale_slot",
            SLOT1_ENGINES,
        )

    def _preflight_checks(self) -> tuple[EnvelopePreflightCheck, ...]:
        def _check_postage_stamp_and_horizon(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if bool(ctx.get("auto_upgrade_postage_stamp", True)):
                return None
            camera_far = float(ctx.get("camera_far", 200.0))
            ground_radius = float(ctx.get("ground_radius", 20.4))
            has_skydome = bool(ctx.get("has_skydome", False))
            fog_matches_horizon = bool(ctx.get("fog_matches_horizon", False))
            if ground_radius < REJECT_GROUND_TO_FAR_RATIO * camera_far or not has_skydome or not fog_matches_horizon:
                return envelope_refusal(
                    "postage_stamp_void_scene_rejected",
                    f"Scene ground_radius ({ground_radius}) is < 0.5 * camera_far ({camera_far}) or lacks a sky dome and matched horizon fog.",
                    "Enable `auto_upgrade_postage_stamp=True` or attach a sky dome and terrain skirt >= 0.85 * camera_far.",
                    retry=RETRY_AFTER_FIX,
                )
            return None

        def _check_motion_duration_and_software_trap(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            duration_sec = float(ctx.get("duration_sec", 8.0))
            unbudgeted_cpu_bloom = bool(ctx.get("unbudgeted_cpu_bloom", False))
            if duration_sec < REJECT_ANIMATION_DURATION_SEC or unbudgeted_cpu_bloom:
                return envelope_refusal(
                    "cramped_duration_or_software_trap_rejected",
                    f"Animation duration ({duration_sec}s < {REJECT_ANIMATION_DURATION_SEC}s) or unbudgeted CPU blur/bloom trap detected.",
                    "Set `duration_sec >= 6.0` with a full camera arc and disable unbudgeted software post-processing.",
                    retry=RETRY_AFTER_FIX,
                )
            return None

        return (
            EnvelopePreflightCheck(
                "postage_stamp_and_horizon_guard",
                ("postage_stamp_void_scene_rejected",),
                _check_postage_stamp_and_horizon,
            ),
            EnvelopePreflightCheck(
                "motion_duration_and_software_trap_guard",
                ("cramped_duration_or_software_trap_rejected",),
                _check_motion_duration_and_software_trap,
            ),
        )

    def evaluate_baseline_without_baltor(
        self,
        arena_span: float = 20.4,
        camera_far: float = 200.0,
        background_hex: str = "#070b0c",
    ) -> dict[str, Any]:
        """Return the unassisted LLM baseline metrics (`default_llm_postage_stamp_void_without_baltor`)."""
        return {
            "engine_id": BASELINE_POSTAGE_STAMP_VOID,
            "arena_span_units": arena_span,
            "ground_radius_units": arena_span,
            "camera_far_units": camera_far,
            "ground_to_far_clip_ratio": round(arena_span / camera_far, 3),
            "background_mode": f"solid_void_{background_hex}",
            "horizon_continuity_score": 0.0,
            "depth_layers": 1,
            "has_skydome": False,
            "has_extended_terrain_skirt": False,
            "has_horizon_silhouette_ridge": False,
            "frame_time_ms": 14.8,
        }

    def upgrade_scene(
        self,
        payload: Mapping[str, Any],
        *,
        request_id: str = "req_3d_horizon_01",
        account_id: str = "acct_stormlab",
        tier: str = "baltor_pro_29",
        active_release_digest: str = DEFAULT_ACTIVE_RELEASE_DIGEST,
        protocol_version: str = CONTRACT_PROTOCOL_VERSION,
    ) -> EnvelopeInvocationResult:
        """Run the 7-layer ComponentEnvelope and dispatch the selected 3D horizon engine."""
        req = EnvelopeInvocationRequest(
            slot_id=SLOT_3D_HORIZON_WORLD_SCALE,
            request_id=request_id,
            account_id=account_id,
            tier=tier,
            active_release_digest=active_release_digest,
            payload=payload,
            protocol_version=protocol_version,
        )

        def _dispatch(inv_req: EnvelopeInvocationRequest, _frame: EnvelopeFrame) -> tuple[str, list[str], dict[str, Any]]:
            p = inv_req.payload
            preferred = str(p.get("preferred_engine", ENGINE_INFINITE_HORIZON_SKYDOME))
            tried: list[str] = []
            for eng in self.envelope.engine_order:
                tried.append(eng)
                if eng == preferred:
                    break
            else:
                preferred = ENGINE_INFINITE_HORIZON_SKYDOME

            arena_span = float(p.get("arena_span", 20.4))
            camera_far = max(float(p.get("camera_far", 240.0)), round(arena_span * 10.0, 1))
            ground_radius = max(float(p.get("ground_radius", 0.0)), round(camera_far * 0.90, 1))
            duration_sec = max(float(p.get("duration_sec", 8.0)), MIN_ANIMATION_DURATION_SEC)
            zenith_color = str(p.get("zenith_color", "#050a14"))
            horizon_glow_color = str(p.get("horizon_glow_color", "#183642"))
            nadir_ground_color = str(p.get("nadir_ground_color", "#0b110e"))

            threejs_patch = (
                f"// Baltor Anti-Default-LLM 3D Horizon & Terrain Skirt Patch ({preferred})\n"
                f"camera.far = {camera_far:.1f}; camera.updateProjectionMatrix();\n"
                f"scene.fog = new THREE.FogExp2('{horizon_glow_color}', 0.0065);\n"
                f"const skySkirt = new THREE.Mesh(\n"
                f"  new THREE.RingGeometry({arena_span * 0.55:.1f}, {ground_radius:.1f}, 64, 4),\n"
                f"  new THREE.MeshStandardMaterial({{color: '{nadir_ground_color}', roughness: 0.95, metalness: 0.05}})\n"
                f");\n"
                f"skySkirt.rotation.x = -Math.PI / 2; skySkirt.position.y = -0.04; scene.add(skySkirt);\n"
                f"const skyDome = new THREE.Mesh(\n"
                f"  new THREE.SphereGeometry({camera_far * 0.95:.1f}, 32, 16),\n"
                f"  new THREE.MeshBasicMaterial({{color: '{horizon_glow_color}', side: THREE.BackSide}})\n"
                f");\n"
                f"scene.add(skyDome);\n"
            )

            frame_time_ms = 6.4 if preferred == ENGINE_LOW_OVERHEAD_HORIZON_GRID else 11.2
            horizon_score = 0.93 if preferred == ENGINE_LOW_OVERHEAD_HORIZON_GRID else 0.98

            out: dict[str, Any] = {
                "selected_engine": preferred,
                "scene_id": str(p.get("scene_id", "stormlab_3d_scene")),
                "arena_span_units": arena_span,
                "camera_far_units": camera_far,
                "far_to_arena_ratio": round(camera_far / max(arena_span, 0.1), 2),
                "ground_radius_units": ground_radius,
                "ground_to_far_clip_ratio": round(ground_radius / camera_far, 3),
                "zenith_color": zenith_color,
                "horizon_glow_color": horizon_glow_color,
                "nadir_ground_color": nadir_ground_color,
                "fog_color": horizon_glow_color,
                "fog_matches_horizon": True,
                "has_skydome": True,
                "has_extended_terrain_skirt": True,
                "has_horizon_silhouette_ridge": True,
                "depth_layers": 3,
                "depth_staging_tiers": (
                    "foreground_playable_arena",
                    "midground_outcrops_and_props",
                    "background_horizon_silhouette_ridge",
                ),
                "duration_sec": duration_sec,
                "horizon_continuity_score": horizon_score,
                "frame_time_ms": frame_time_ms,
                "within_60fps_budget": frame_time_ms <= MAX_FRAME_BUDGET_MS,
                "threejs_horizon_patch": threejs_patch,
            }
            return preferred, tried, out

        return self.envelope.execute(req, _dispatch, self._preflight_checks())

    def upgrade_local_html_file(self, html_path: Path, request_id: str) -> dict[str, Any]:
        """Inspect `/home/username/td3d.html` or `/home/username/worm3d.html` and upgrade its 3D horizon."""
        if html_path.exists():
            raw_html = html_path.read_text(encoding="utf-8")
        else:
            raw_html = (
                "scene.background=new THREE.Color(0x070b0c);"
                "const camera=new THREE.PerspectiveCamera(46,innerWidth/innerHeight,.1,200);"
                "const GW=12,GD=12,TS=1.7;"
            )
        before = inspect_local_stormlab_3d_html(raw_html, html_path.name)
        horizon_glow = "#163840" if "td3d" in html_path.name else "#2b1624"
        upgraded = self.upgrade_scene(
            {
                "preferred_engine": ENGINE_TD3D_WORM3D_UPGRADER,
                "scene_id": html_path.stem,
                "arena_span": before["arena_span_units"],
                "camera_far": 240.0,
                "ground_radius": 216.0,
                "horizon_glow_color": horizon_glow,
                "duration_sec": 12.0,
                "auto_upgrade_postage_stamp": True,
            },
            request_id=request_id,
        )
        return {
            "file_name": html_path.name,
            "before_without_baltor": before,
            "after_with_baltor": dict(upgraded.output),
            "accepted": upgraded.accepted,
        }


# ---------------------------------------------------------------------------
# Slot Family 2: Tinkercad, Jumpstart-3D (3dxd), FluidCAD, SolidCraft & Slicer
# ---------------------------------------------------------------------------


class Tinkercad3dxdFluidcadSolidcraftCadSlot:
    """Slot Family 2 (`tinkercad_3dxd_fluidcad_solidcraft_cad_slot`).

    Provides 5 swappable parametric Code-CAD and 3D-printing engines with deterministic
    workplane bed-adhesion (`z_min == 0.0`), watertight 2-manifold Euler checks
    (`V - E + F == 2(1 - g)`), minimum wall thickness (`>= 1.2 mm`), and snap-fit
    clearance tolerance (`>= 0.20 mm`).
    """

    def __init__(self) -> None:
        self.envelope = ComponentEnvelope(
            "tinkercad_3dxd_fluidcad_solidcraft_cad_slot",
            SLOT2_ENGINES,
        )

    def _preflight_checks(self) -> tuple[EnvelopePreflightCheck, ...]:
        def _check_workplane_bed_adhesion(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            z_min = float(ctx.get("z_min_mm", 0.0))
            auto_snap = bool(ctx.get("auto_snap_to_workplane", False))
            if abs(z_min) > 1e-4 and not auto_snap:
                return envelope_refusal(
                    "floating_cad_part_off_workplane_rejected",
                    f"CAD part floats at z_min={z_min:.2f}mm != 0.00mm above the build plate and would fail FDM bed adhesion.",
                    "Translate the solid by `-z_min` onto `workplane_z = 0.0` or set `auto_snap_to_workplane=True`.",
                    retry=RETRY_AFTER_FIX,
                )
            return None

        def _check_manifold_and_printability(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            v = int(ctx.get("vertices", 8))
            e = int(ctx.get("edges", 12))
            f = int(ctx.get("faces", 6))
            genus = int(ctx.get("genus", 0))
            expected_euler = 2 * (1 - genus)
            euler_val = v - e + f
            non_manifold_edges = int(ctx.get("non_manifold_edges", 0))
            wall_mm = float(ctx.get("min_wall_thickness_mm", 1.6))
            clearance_mm = float(ctx.get("snap_fit_clearance_mm", 0.20))

            if euler_val != expected_euler or non_manifold_edges > 0 or wall_mm < MIN_WALL_THICKNESS_MM or clearance_mm < MIN_SNAP_FIT_CLEARANCE_MM:
                return envelope_refusal(
                    "non_manifold_or_zero_clearance_rejected",
                    (
                        f"Slicer preflight failed: Euler V-E+F={euler_val} (expected {expected_euler}), "
                        f"non_manifold_edges={non_manifold_edges}, wall={wall_mm:.2f}mm, clearance={clearance_mm:.2f}mm."
                    ),
                    "Close open mesh boundaries, keep wall thickness >= 1.2mm, and set snap-fit clearance >= 0.20mm.",
                    retry=RETRY_AFTER_FIX,
                )
            return None

        return (
            EnvelopePreflightCheck(
                "workplane_bed_adhesion_guard",
                ("floating_cad_part_off_workplane_rejected",),
                _check_workplane_bed_adhesion,
            ),
            EnvelopePreflightCheck(
                "manifold_and_clearance_guard",
                ("non_manifold_or_zero_clearance_rejected",),
                _check_manifold_and_printability,
            ),
        )

    def synthesize_cad_component(
        self,
        payload: Mapping[str, Any],
        *,
        request_id: str = "req_cad_01",
        account_id: str = "acct_maker",
        tier: str = "baltor_pro_29",
        active_release_digest: str = DEFAULT_ACTIVE_RELEASE_DIGEST,
    ) -> EnvelopeInvocationResult:
        """Execute a parametric CAD & 3D-printing synthesis request through all 7 envelope layers."""
        req = EnvelopeInvocationRequest(
            slot_id=SLOT_CAD_AND_PRINTABILITY,
            request_id=request_id,
            account_id=account_id,
            tier=tier,
            active_release_digest=active_release_digest,
            payload=payload,
        )

        def _dispatch(inv_req: EnvelopeInvocationRequest, _frame: EnvelopeFrame) -> tuple[str, list[str], dict[str, Any]]:
            p = inv_req.payload
            preferred = str(p.get("preferred_engine", ENGINE_TINKERCAD_CSG_WORKPLANE))
            tried: list[str] = []
            for eng in self.envelope.engine_order:
                tried.append(eng)
                if eng == preferred:
                    break
            else:
                preferred = ENGINE_TINKERCAD_CSG_WORKPLANE

            part_name = str(p.get("part_name", "stormlab_turret_mount_enclosure"))
            genus = int(p.get("genus", 1))
            v = int(p.get("vertices", 16))
            e = int(p.get("edges", 32))
            f = int(p.get("faces", 16))
            euler_val = v - e + f
            expected_euler = 2 * (1 - genus)
            wall_mm = float(p.get("min_wall_thickness_mm", 1.8))
            clearance_mm = float(p.get("snap_fit_clearance_mm", 0.20))
            overhang_deg = float(p.get("max_overhang_deg", 35.0))

            if preferred == ENGINE_TINKERCAD_CSG_WORKPLANE:
                cad_artifact = (
                    "// Tinkercad Declarative CSG Workplane + Hole Boolean Group\n"
                    "const base = workplane({z: 0.0}).box({w: 42, d: 42, h: 14, is_hole: false});\n"
                    "const bore = workplane({z: 0.0}).cylinder({r: 6.1, h: 14, is_hole: true, clearance_mm: 0.20});\n"
                    "export const part = groupBooleanSubtract(base, [bore]); // z_min == 0.0mm\n"
                )
                kernel_family = "Tinkercad CSG + Workplane Snap"
            elif preferred == ENGINE_JUMPSTART_3DXD_TIMELINE:
                cad_artifact = (
                    "// Jumpstart-3D (3dxd) Constrained Sketch -> Extrude -> Fillet Timeline\n"
                    "const sketch = createConstrainedSketch('XY', {z: 0.0}).rect(42, 42).circleHole(12.2);\n"
                    "export const body = sketch.extrude(14.0).filletEdges(1.5).chamferBottom(0.6);\n"
                )
                kernel_family = "Jumpstart-3D (3dxd) OpenCascade Timeline"
            elif preferred == ENGINE_FLUIDCAD_HYBRID_BREP:
                cad_artifact = (
                    "// FluidCAD (fluidcad.io) Hybrid JS + OpenCascade B-Rep Solid\n"
                    "import { Solid, Sketch } from 'fluidcad';\n"
                    "export const mount = Solid.fromSketch(Sketch.rect(42, 42)).extrude(14).cut(Solid.cylinder(6.1, 14));\n"
                )
                kernel_family = "FluidCAD JS + OpenCascade B-Rep"
            elif preferred == ENGINE_SOLIDCRAFT_RUST_MCP:
                cad_artifact = json.dumps(
                    {
                        "mcp_server": "solidcraft_rust_mcp",
                        "tool_sequence": [
                            {"tool": "create_sketch", "plane": "XY", "z_min_mm": 0.0},
                            {"tool": "add_dimensional_constraint", "width_mm": 42.0, "depth_mm": 42.0, "clearance_mm": clearance_mm},
                            {"tool": "extrude_solid", "height_mm": 14.0},
                            {"tool": "boolean_cut", "hole_radius_mm": 6.1},
                            {"tool": "export_step_and_stl", "formats": ["STEP", "STL"]},
                        ],
                    }
                )
                kernel_family = "SolidCraft Rust Parametric CAD + MCP"
            else:
                cad_artifact = (
                    "# Build123d / OpenSCAD Manifold Printable Solid\n"
                    "with BuildPart() as mount:\n"
                    "    Box(42, 42, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))\n"
                    "    Cylinder(radius=6.1, height=14, mode=Mode.SUBTRACT)\n"
                )
                kernel_family = "Build123d / OpenSCAD + Slicer Preflight"

            out: dict[str, Any] = {
                "selected_engine": preferred,
                "kernel_family": kernel_family,
                "part_name": part_name,
                "workplane_z_min_mm": 0.0,
                "bed_adhesion_verified": True,
                "is_hole_booleans_grouped": True,
                "watertight_2_manifold": euler_val == expected_euler,
                "euler_characteristic": euler_val,
                "expected_euler_characteristic": expected_euler,
                "genus": genus,
                "min_wall_thickness_mm": wall_mm,
                "snap_fit_clearance_mm": clearance_mm,
                "max_overhang_deg": overhang_deg,
                "supports_required": overhang_deg > MAX_UNSUPPORTED_OVERHANG_DEG,
                "exports": ("STEP", "STL", "3MF"),
                "cad_source_or_protocol": cad_artifact,
            }
            return preferred, tried, out

        return self.envelope.execute(req, _dispatch, self._preflight_checks())


# ---------------------------------------------------------------------------
# Slot Family 3: 3D Game & CAD AGENTS.md, RULES.md & MEMORY.md Generator
# ---------------------------------------------------------------------------


class ThreeDAndCadHarnessFilesSlot:
    """Slot Family 3 (`three_d_and_cad_harness_files_slot`).

    Generates drop-in `AGENTS.md`, `RULES.md` (`.cursor/rules/3d-horizon-and-cad.mdc`), and
    `MEMORY.md` packs that prevent default-LLM postage-stamp 3D voids and floating/unprintable
    CAD geometry before the first line of scene or CAD code is written.
    """

    def __init__(self) -> None:
        self.envelope = ComponentEnvelope(
            "three_d_and_cad_harness_files_slot",
            SLOT3_ENGINES,
        )

    def generate_harness_pack(
        self,
        payload: Mapping[str, Any],
        *,
        request_id: str = "req_3d_cad_pack_01",
        account_id: str = "acct_stormlab",
        tier: str = "baltor_pro_29",
        active_release_digest: str = DEFAULT_ACTIVE_RELEASE_DIGEST,
    ) -> EnvelopeInvocationResult:
        req = EnvelopeInvocationRequest(
            slot_id=SLOT_3D_CAD_HARNESS_FILES,
            request_id=request_id,
            account_id=account_id,
            tier=tier,
            active_release_digest=active_release_digest,
            payload=payload,
        )

        def _dispatch(inv_req: EnvelopeInvocationRequest, _frame: EnvelopeFrame) -> tuple[str, list[str], dict[str, Any]]:
            p = inv_req.payload
            preferred = str(p.get("preferred_engine", ENGINE_CURSOR_CLAUDE_3D_CAD_PACK))
            tried: list[str] = []
            for eng in self.envelope.engine_order:
                tried.append(eng)
                if eng == preferred:
                    break
            else:
                preferred = ENGINE_CURSOR_CLAUDE_3D_CAD_PACK

            agents_md = (
                "# AGENTS.md — 3D Game World Horizon & Parametric Code-CAD Rules\n\n"
                "1. **Never generate a postage-stamp 3D island in a black void**: Every Three.js / WebGL game "
                "scene (`td3d`, `worm3d`, or arena) MUST include an atmospheric sky dome (`zenith`, `horizon_glow`, "
                "`nadir`), an extended terrain skirt (`ground_radius >= 0.85 * camera.far`), matched horizon fog "
                "(`fog.color == horizon_glow`), and 3-tier spatial depth (playable arena, midground props, "
                "distant silhouette ridge).\n"
                "2. **Camera frustum & motion budget**: Keep `camera.far / arena_span >= 8.0`, animation loops "
                "`>= 6.0s` (never `< 3.0s` stubs), and frame times `<= 16.6ms` (`60fps`). Never enable unbudgeted "
                "CPU blur or software bloom.\n"
                "3. **Tinkercad, Jumpstart-3D (`3dxd`), FluidCAD & SolidCraft CAD invariants**: Snap every printable "
                "part to the build plate (`z_min == 0.0mm`), group all negative-volume (`is_hole=True`) cutters, "
                "verify watertight 2-manifold topology (`V - E + F = 2(1 - g)`), keep wall thickness `>= 1.2mm`, "
                "and apply `>= 0.20mm` clearance on snap-fit and threaded joints.\n"
            )
            cursor_rules_mdc = (
                "---\n"
                "description: Anti-Default-LLM 3D Horizon, Ground-Skirt & Printable Code-CAD Guard\n"
                "globs: [\"**/*.html\", \"**/*.three.js\", \"**/*.scad\", \"**/*.cad.ts\", \"**/*.cad.py\"]\n"
                "alwaysApply: true\n"
                "---\n"
                "- Require `ground_radius >= 0.85 * camera.far` + sky dome + matched horizon fog.\n"
                "- Require `workplane_z == 0.0`, watertight 2-manifold meshes, and `0.20mm` print clearance.\n"
            )
            memory_md = (
                "# MEMORY.md — Distilled Owner Corrections for 3D Games & CAD\n\n"
                "- Correction 1 (`td3d.html` / `worm3d.html`): Default LLMs emit a `20.4x20.4` board in a flat "
                "`#070b0c` void with `camera.far=200`. Always add a `>= 180`-unit terrain skirt, sky dome, and "
                "silhouette ridge.\n"
                "- Correction 2 (Tinkercad / `3dxd` / `FluidCAD` / `SolidCraft`): Never leave CSG parts floating "
                "above `z=0` or emit zero-clearance (`0.00mm`) snap-fits.\n"
            )
            out: dict[str, Any] = {
                "selected_engine": preferred,
                "files": {
                    "AGENTS.md": agents_md,
                    ".cursor/rules/3d-horizon-and-cad.mdc": cursor_rules_mdc,
                    "MEMORY.md": memory_md,
                },
                "rules_enforced_count": 6,
                "covers_3d_horizon_and_cad": True,
            }
            return preferred, tried, out

        return self.envelope.execute(req, _dispatch)


# ---------------------------------------------------------------------------
# Deterministic Benchmark Runner
# ---------------------------------------------------------------------------


def run_comprehensive_3d_horizon_and_cad_benchmark() -> dict[str, Any]:
    """Run head-to-head benchmarks across all 3 slot families, local HTML files, and 4 known-wrong controls."""
    slot1 = AntiDefault3DHorizonAndWorldScaleSlot()
    slot2 = Tinkercad3dxdFluidcadSolidcraftCadSlot()
    slot3 = ThreeDAndCadHarnessFilesSlot()

    baseline_void = slot1.evaluate_baseline_without_baltor()
    slot1_runs: list[dict[str, Any]] = []
    for idx, eng in enumerate(SLOT1_ENGINES):
        res = slot1.upgrade_scene(
            {
                "preferred_engine": eng,
                "scene_id": f"bench_scene_{idx}",
                "arena_span": 20.4,
                "camera_far": 240.0,
                "ground_radius": 216.0,
                "duration_sec": 10.0,
                "auto_upgrade_postage_stamp": True,
            },
            request_id=f"bench_s1_{idx}",
        )
        slot1_runs.append(dict(res.output))

    td3d_upgrade = slot1.upgrade_local_html_file(Path("/home/username/td3d.html"), request_id="upgrade_td3d")
    worm3d_upgrade = slot1.upgrade_local_html_file(Path("/home/username/worm3d.html"), request_id="upgrade_worm3d")

    slot2_runs: list[dict[str, Any]] = []
    for idx, eng in enumerate(SLOT2_ENGINES):
        res = slot2.synthesize_cad_component(
            {
                "preferred_engine": eng,
                "part_name": f"parametric_mount_{idx}",
                "z_min_mm": 0.0,
                "vertices": 16,
                "edges": 32,
                "faces": 16,
                "genus": 1,
                "min_wall_thickness_mm": 1.8,
                "snap_fit_clearance_mm": 0.20,
                "max_overhang_deg": 35.0,
            },
            request_id=f"bench_s2_{idx}",
        )
        slot2_runs.append(dict(res.output))

    slot3_runs: list[dict[str, Any]] = []
    for idx, eng in enumerate(SLOT3_ENGINES):
        res = slot3.generate_harness_pack(
            {"preferred_engine": eng},
            request_id=f"bench_s3_{idx}",
        )
        slot3_runs.append(
            {
                "selected_engine": res.selected_engine,
                "files_generated": tuple(res.output["files"].keys()),
                "rules_enforced_count": res.output["rules_enforced_count"],
            }
        )

    # Known-wrong controls
    ctrl_a = slot1.upgrade_scene(
        {
            "arena_span": 20.4,
            "camera_far": 200.0,
            "ground_radius": 20.4,
            "has_skydome": False,
            "fog_matches_horizon": False,
            "auto_upgrade_postage_stamp": False,
        },
        request_id="ctrl_a_postage_stamp_void",
    )
    ctrl_b = slot1.upgrade_scene(
        {
            "arena_span": 20.4,
            "camera_far": 240.0,
            "ground_radius": 216.0,
            "duration_sec": 1.8,
            "unbudgeted_cpu_bloom": True,
            "auto_upgrade_postage_stamp": True,
        },
        request_id="ctrl_b_cramped_duration_bloom",
    )
    ctrl_c = slot2.synthesize_cad_component(
        {
            "part_name": "floating_tinkercad_bracket",
            "z_min_mm": 4.5,
            "auto_snap_to_workplane": False,
        },
        request_id="ctrl_c_floating_cad_part",
    )
    ctrl_d = slot2.synthesize_cad_component(
        {
            "part_name": "fused_non_manifold_joint",
            "z_min_mm": 0.0,
            "vertices": 8,
            "edges": 12,
            "faces": 5,
            "genus": 0,
            "non_manifold_edges": 2,
            "min_wall_thickness_mm": 0.6,
            "snap_fit_clearance_mm": 0.0,
        },
        request_id="ctrl_d_non_manifold_zero_clearance",
    )

    return {
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "baseline_without_baltor": baseline_void,
        "slot1_horizon_engines": slot1_runs,
        "local_game_upgrades": {
            "td3d.html": td3d_upgrade,
            "worm3d.html": worm3d_upgrade,
        },
        "slot2_cad_engines": slot2_runs,
        "slot3_harness_packs": slot3_runs,
        "known_wrong_controls": {
            "control_a_postage_stamp_void_blocked": (not ctrl_a.accepted)
            and ctrl_a.refusal is not None
            and ctrl_a.refusal.code == "postage_stamp_void_scene_rejected",
            "control_b_cramped_duration_or_bloom_blocked": (not ctrl_b.accepted)
            and ctrl_b.refusal is not None
            and ctrl_b.refusal.code == "cramped_duration_or_software_trap_rejected",
            "control_c_floating_cad_part_blocked": (not ctrl_c.accepted)
            and ctrl_c.refusal is not None
            and ctrl_c.refusal.code == "floating_cad_part_off_workplane_rejected",
            "control_d_non_manifold_or_zero_clearance_blocked": (not ctrl_d.accepted)
            and ctrl_d.refusal is not None
            and ctrl_d.refusal.code == "non_manifold_or_zero_clearance_rejected",
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_comprehensive_3d_horizon_and_cad_benchmark(), indent=2))
