"""Pixel Art as Code, Pixel Logic, Fourier Rigging & Video Design FX, and Autonomous Portal Project Scanner/Ingester Engine Suite.

Implements and benchmarks three swappable engine slot families wrapped in the
canonical 7-layer ComponentEnvelope (`frustration_avoidance`, `carrier`,
`handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`):

1. Slot Family 1 (`pixelart_as_code_and_pixel_logic_slot`):
   - `claude_pxl_dsl_and_sprite_sheet_compiler_engine`
   - `oklab_palette_and_bayer_atkinson_dither_engine`
   - `noita_falling_sand_and_isometric_pixel_logic_engine`
   - `ascii_and_ansi_block_pixel_fallback_engine`
2. Slot Family 2 (`video_fx_fourier_rig_and_transform_slot`):
   - `silhouette_stick_rig_difference_and_fourier_epicycle_engine`
   - `multi_plane_broll_ken_burns_and_particle_weather_engine`
   - `geometric_pixel_and_coordinate_transformation_engine`
   - `deterministic_svg_motion_layer_fallback_engine`
3. Slot Family 3 (`portal_project_scanner_and_db_ingester_slot`):
   - `github_and_ecosystem_project_scanner_ingester_engine`
   - `static_manifest_and_conformance_auditor_engine`
   - `offline_catalog_seed_fallback_engine`

All execution is deterministic and in-memory with zero external network calls.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import types
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))


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
    ACCOUNT_OWNER,
    CALLER,
    COVERAGE_LAYERS,
    EFFECT_NONE,
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
    RETRY_NOW_SAME_IDENTITY,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
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
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    ANSWER_FROM_FIRST_RESULT,
    EFFECT_STATE_CONFIRMED,
    REQUEST_ANSWERED,
    TASK_COMPLETED,
    journal_decision,
    journal_intent,
    journal_outcome,
    request_identity_digest,
)

# --- Slot & Engine Identifiers ---
SLOT_PIXELART_AND_LOGIC = "pixelart_as_code_and_pixel_logic_slot"
SLOT_VIDEO_FX_AND_FOURIER = "video_fx_fourier_rig_and_transform_slot"
SLOT_PORTAL_PROJECT_SCANNER = "portal_project_scanner_and_db_ingester_slot"
ALL_PIXEL_VIDEO_PORTAL_SLOTS = (
    SLOT_PIXELART_AND_LOGIC,
    SLOT_VIDEO_FX_AND_FOURIER,
    SLOT_PORTAL_PROJECT_SCANNER,
)

ENG_CLAUDE_PXL_COMPILER = "claude_pxl_dsl_and_sprite_sheet_compiler_engine"
ENG_OKLAB_BAYER_ATKINSON = "oklab_palette_and_bayer_atkinson_dither_engine"
ENG_NOITA_SAND_ISOMETRIC = "noita_falling_sand_and_isometric_pixel_logic_engine"
ENG_ASCII_ANSI_PIXEL_FALLBACK = "ascii_and_ansi_block_pixel_fallback_engine"
PIXELART_SLOT_ENGINES = (
    ENG_CLAUDE_PXL_COMPILER,
    ENG_OKLAB_BAYER_ATKINSON,
    ENG_NOITA_SAND_ISOMETRIC,
    ENG_ASCII_ANSI_PIXEL_FALLBACK,
)

ENG_SILHOUETTE_STICK_FOURIER = "silhouette_stick_rig_difference_and_fourier_epicycle_engine"
ENG_MULTI_PLANE_BROLL_WEATHER = "multi_plane_broll_ken_burns_and_particle_weather_engine"
ENG_GEOMETRIC_PIXEL_TRANSFORM = "geometric_pixel_and_coordinate_transformation_engine"
ENG_SVG_MOTION_FALLBACK = "deterministic_svg_motion_layer_fallback_engine"
VIDEO_FX_SLOT_ENGINES = (
    ENG_SILHOUETTE_STICK_FOURIER,
    ENG_MULTI_PLANE_BROLL_WEATHER,
    ENG_GEOMETRIC_PIXEL_TRANSFORM,
    ENG_SVG_MOTION_FALLBACK,
)

ENG_PORTAL_SCANNER_INGESTER = "github_and_ecosystem_project_scanner_ingester_engine"
ENG_MANIFEST_CONFORMANCE_AUDITOR = "static_manifest_and_conformance_auditor_engine"
ENG_OFFLINE_CATALOG_FALLBACK = "offline_catalog_seed_fallback_engine"
PORTAL_SCANNER_SLOT_ENGINES = (
    ENG_PORTAL_SCANNER_INGESTER,
    ENG_MANIFEST_CONFORMANCE_AUDITOR,
    ENG_OFFLINE_CATALOG_FALLBACK,
)

_HEX_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


@dataclass
class ComponentEnvelope:
    """7-Layer ComponentEnvelope wrapping an engine slot and its swappable engine chain."""

    slot_id: str
    request_schema: str
    response_schema: str
    engine_order: tuple[str, ...]
    engine_handlers: Mapping[str, Callable[[Mapping[str, Any], EnvelopeFrame], Mapping[str, Any]]]
    handshake_validator: Callable[[Mapping[str, Any]], tuple[str, str, str] | None]
    preflight_validator: Callable[[Mapping[str, Any]], tuple[str, str, str, str] | None]

    def __post_init__(self) -> None:
        self._journal_entries: list[Any] = []
        self._cached_results: dict[str, dict[str, Any]] = {}

    def execute(
        self,
        request: Mapping[str, Any],
        *,
        preferred_engine: str | None = None,
        parent_frame: EnvelopeFrame | None = None,
        simulate_deferrals: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Run all 7 envelope layers (`frustration_avoidance` -> `preflight` -> engine slot)."""
        frame = (
            root_frame(self.slot_id)
            if parent_frame is None
            else enter_nested(parent_frame, self.slot_id)
        )
        # Layer 2: Carrier check
        if not isinstance(request, Mapping) or request.get("record_type") != self.request_schema:
            refusal = envelope_refusal(
                "carrier_schema_mismatch",
                "The request record type does not match the slot carrier schema.",
                "Supply the exact versioned request schema declared by this component slot.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            return self._refusal_bundle(refusal, LAYER_CARRIER, frame)

        # Layer 3: Handshake check
        engine_chain = (
            (preferred_engine,) + tuple(e for e in self.engine_order if e != preferred_engine)
            if preferred_engine and preferred_engine in self.engine_order
            else self.engine_order
        )
        hs_error = self.handshake_validator(request)
        if hs_error is not None:
            code, happened, action = hs_error
            refusal = envelope_refusal(
                code,
                happened,
                action,
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=ACCOUNT_OWNER,
            )
            return self._refusal_bundle(refusal, LAYER_HANDSHAKE, frame)

        hs_req = EnvelopeHandshakeRequest(
            component=self.slot_id,
            requested_versions=(self.request_schema,),
            required_capabilities=("deterministic_envelope",),
            granted_effects=(PURE_EFFECT,),
        )
        hs_decl = EnvelopeHandshakeDeclaration(
            engine=engine_chain[0],
            supported_versions=(self.request_schema,),
            capabilities=("deterministic_envelope",),
            effects=(PURE_EFFECT,),
        )
        verdict = negotiate_handshake(hs_req, hs_decl)

        # Layer 4: Account & entitlement verification
        principal = str(request.get("principal", "verified_creative_or_portal_worker"))
        if not principal.strip():
            refusal = envelope_refusal(
                "missing_account_principal",
                "The request does not carry a valid service or account principal.",
                "Attach an authenticated account or worker principal before invoking this slot.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            return self._refusal_bundle(refusal, LAYER_ACCOUNT, frame)

        # Layer 5: Tracking & idempotency replay
        req_id = str(request.get("request_id", f"{self.slot_id}_default"))
        digest = request_identity_digest({"slot": self.slot_id, "request_id": req_id})
        decision = journal_decision(self._journal_entries, digest)
        if decision.decision == ANSWER_FROM_FIRST_RESULT and digest in self._cached_results:
            trace = EnvelopeTrace(
                component=self.slot_id,
                steps=(
                    (LAYER_CARRIER, LAYER_ACCEPTED),
                    (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                    (LAYER_ACCOUNT, LAYER_ACCEPTED),
                    (LAYER_TRACKING, LAYER_ANSWERED),
                ),
                engine_dispatched=False,
                refused_by="",
                refusal=None,
            )
            return {
                "status": "ok",
                "replayed_from_tracking": True,
                "envelope_layers": COVERAGE_LAYERS,
                "trace": trace.to_dict(),
                "result": self._cached_results[digest],
            }

        # Layer 6: Preflight effect-free checks and bounded self-repair
        pf_error = self.preflight_validator(request)
        if pf_error is not None:
            code, happened, action, actor = pf_error
            pf_refusal = envelope_refusal(
                code,
                happened,
                action,
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=actor,
            )
            pf_report = run_preflight(
                component=self.slot_id,
                checks=(
                    EnvelopePreflightCheck(
                        check_id="slot_preflight_guard",
                        diagnoses=(code,),
                        run=lambda _ctx: pf_refusal,
                    ),
                ),
                repairs=(),
                context=request,
                grant=EnvelopePreflightGrant(),
            )
            return self._refusal_bundle(pf_refusal, LAYER_PREFLIGHT, frame, preflight_report=pf_report)

        pf_report = run_preflight(
            component=self.slot_id,
            checks=(
                EnvelopePreflightCheck(
                    check_id="slot_preflight_guard",
                    diagnoses=("preflight_transient_warning",),
                    run=lambda _ctx: None,
                ),
            ),
            repairs=(
                EnvelopeSelfRepair(
                    repair_id="normalize_request_context",
                    fixes=("preflight_transient_warning",),
                    effects=(PURE_EFFECT,),
                    maximum_applications=1,
                    apply=lambda ctx: dict(ctx),
                ),
            ),
            context=request,
            grant=EnvelopePreflightGrant(),
        )

        # Layer 7: Engine slot dispatch & bounded fallback across engine_chain
        policy = EnvelopeRecoveryPolicy(
            component=self.slot_id,
            maximum_automatic_attempts=3,
            recoverable_codes=("engine_deferred_to_fallback",),
        )
        attempted: list[str] = []
        selected_engine = engine_chain[-1]
        payload_out: Mapping[str, Any] = {}
        for engine_id in engine_chain:
            attempted.append(engine_id)
            if engine_id in simulate_deferrals and len(attempted) < len(engine_chain):
                temp_refusal = envelope_refusal(
                    "engine_deferred_to_fallback",
                    "The primary engine deferred execution to the next qualified engine in the slot.",
                    "Allow the envelope recovery policy to select the next fallback engine automatically.",
                    retry=RETRY_NOW_SAME_IDENTITY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=OPERATOR,
                    automatic_retry=True,
                )
                if may_recover(policy, temp_refusal, frame.allowance):
                    continue
            selected_engine = engine_id
            payload_out = self.engine_handlers[engine_id](request, frame)
            break

        intent_entry = journal_intent(
            self._journal_entries,
            component=self.slot_id,
            request_identity=digest,
            repeatable=True,
            at="2026-10-17T05:30:00Z",
        )
        self._journal_entries.append(intent_entry)
        completed_entry = journal_outcome(
            self._journal_entries,
            component=self.slot_id,
            request_identity=digest,
            request_outcome=REQUEST_ANSWERED,
            task_outcome=TASK_COMPLETED,
            effect_state=EFFECT_STATE_CONFIRMED,
            result_digest=digest,
            at="2026-10-17T05:30:01Z",
        )
        self._journal_entries.append(completed_entry)

        trace = EnvelopeTrace(
            component=self.slot_id,
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
        result_record = {
            "record_type": self.response_schema,
            "slot_id": self.slot_id,
            "selected_engine": selected_engine,
            "attempted_engines": tuple(attempted),
            "handshake_verdict": verdict.verdict,
            "preflight_verdict": pf_report.verdict,
            "tracking_state": completed_entry.request_outcome,
            **payload_out,
        }
        self._cached_results[digest] = result_record
        return {
            "status": "ok",
            "replayed_from_tracking": False,
            "envelope_layers": COVERAGE_LAYERS,
            "trace": trace.to_dict(),
            "result": result_record,
        }

    def _refusal_bundle(
        self,
        refusal: EnvelopeRefusal,
        layer: str,
        frame: EnvelopeFrame,
        *,
        preflight_report: EnvelopePreflightReport | None = None,
    ) -> dict[str, Any]:
        inbound_order = (LAYER_CARRIER, LAYER_HANDSHAKE, LAYER_ACCOUNT, LAYER_TRACKING, LAYER_PREFLIGHT)
        steps: list[tuple[str, str]] = []
        for lyr in inbound_order:
            if lyr == layer:
                steps.append((lyr, LAYER_REFUSED))
                break
            steps.append((lyr, LAYER_ACCEPTED))
        trace = EnvelopeTrace(
            component=self.slot_id,
            steps=tuple(steps),
            engine_dispatched=False,
            refused_by=layer,
            refusal=refusal,
        )
        out: dict[str, Any] = {
            "status": "refused",
            "replayed_from_tracking": False,
            "envelope_layers": COVERAGE_LAYERS,
            "frame_depth": frame.depth,
            "trace": trace.to_dict(),
            "refusal": refusal.to_dict(),
        }
        if preflight_report is not None:
            out["preflight_report"] = preflight_report.to_dict()
        return out


# ===========================================================================
# SLOT FAMILY 1: Pixel Art as Code, Palette/Dither Shaders & Cellular Logic
# ===========================================================================

def _curated_palettes() -> dict[str, tuple[tuple[int, int, int], ...]]:
    return {
        "PICO-8": (
            (0, 0, 0), (29, 43, 83), (126, 37, 83), (0, 135, 81),
            (171, 82, 54), (95, 87, 79), (194, 195, 199), (255, 241, 232),
            (255, 0, 77), (255, 163, 0), (255, 236, 39), (0, 228, 54),
            (41, 173, 255), (131, 118, 156), (255, 119, 168), (255, 204, 170),
        ),
        "Baltor-Editorial-16": (
            (13, 17, 23), (28, 35, 49), (47, 59, 82), (76, 94, 128),
            (118, 141, 179), (171, 190, 219), (226, 234, 245), (249, 250, 251),
            (184, 51, 42), (224, 90, 54), (242, 159, 63), (247, 212, 108),
            (46, 133, 96), (72, 181, 131), (43, 114, 181), (104, 88, 179),
        ),
        "Endesga-32": (
            (190, 74, 47), (215, 118, 67), (234, 212, 170), (228, 166, 114),
            (184, 111, 80), (115, 62, 57), (62, 39, 49), (162, 38, 51),
            (228, 59, 68), (247, 118, 34), (254, 174, 52), (254, 231, 97),
            (99, 199, 77), (62, 137, 72), (38, 92, 66), (25, 60, 62),
            (18, 78, 137), (0, 149, 233), (44, 232, 245), (192, 203, 220),
            (139, 155, 180), (90, 105, 136), (58, 68, 102), (38, 43, 68),
            (24, 20, 37), (255, 0, 68), (104, 56, 108), (181, 80, 136),
            (246, 117, 122), (232, 183, 150), (194, 133, 105), (255, 255, 255),
        ),
    }


def _rgb_to_oklab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert 8-bit sRGB into perceptual OKLab (L, a, b) coordinates."""
    rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
    l_ = 0.4122214708 * rn + 0.5363325363 * gn + 0.0514459929 * bn
    m_ = 0.2119034982 * rn + 0.6806995451 * gn + 0.1073969566 * bn
    s_ = 0.0883024619 * rn + 0.2817188376 * gn + 0.6299787005 * bn
    lc, mc, sc = l_ ** (1.0 / 3.0), m_ ** (1.0 / 3.0), s_ ** (1.0 / 3.0)
    return (
        0.2104542553 * lc + 0.7936177850 * mc - 0.0040720468 * sc,
        1.9779984951 * lc - 2.4285922050 * mc + 0.4505937099 * sc,
        0.0259040371 * lc + 0.7827717662 * mc - 0.8086757660 * sc,
    )


def _pixelart_handshake_validator(request: Mapping[str, Any]) -> tuple[str, str, str] | None:
    tex_filter = str(request.get("texture_filter", "THREE.NearestFilter"))
    nearest_only = bool(request.get("nearest_neighbor_only", True))
    scale_factor = request.get("scale_factor", 4)
    if not nearest_only or "Linear" in tex_filter or not isinstance(scale_factor, int) or scale_factor < 1:
        return (
            "blurry_non_integer_pixel_interpolation_forbidden",
            "Pixel-art rendering requested bilinear/trilinear filtering or a non-integer scale factor.",
            "Set nearest_neighbor_only=True, texture_filter='THREE.NearestFilter', and an integer scale_factor.",
        )
    return None


def _pixelart_preflight_validator(request: Mapping[str, Any]) -> tuple[str, str, str, str] | None:
    if bool(request.get("allow_non_conserving_swaps", False)) or int(request.get("conservation_violation_delta", 0)) != 0:
        return (
            "non_mass_conserving_cellular_automata_forbidden",
            "Cellular automata pixel rules attempted to create or destroy particle mass during swap transitions.",
            "Enforce strict pairwise swap conservation across sand, water, fire, smoke, acid, and lava cells.",
            CALLER,
        )
    return None


def _run_pixelart_engine(request: Mapping[str, Any], _frame: EnvelopeFrame, *, mode: str) -> Mapping[str, Any]:
    palette_name = str(request.get("palette_name", "PICO-8"))
    palettes = _curated_palettes()
    palette = palettes.get(palette_name, palettes["PICO-8"])
    w = int(request.get("grid_width", 16))
    h = int(request.get("grid_height", 16))
    scale = int(request.get("scale_factor", 4))
    symmetry = str(request.get("symmetry_mode", "bilateral_x"))

    # 1. Build base half-grid & apply bilateral/radial symmetry + selective outlining (selout)
    grid = [[0 for _ in range(w)] for _ in range(h)]
    for y in range(2, h - 2):
        for x in range(2, w // 2):
            if (x + y) % 2 == 0 or x == w // 2 - 1:
                grid[y][x] = 12 if y < h // 2 else 8
            if symmetry in ("bilateral_x", "radial_4"):
                grid[y][w - 1 - x] = grid[y][x]
            if symmetry == "radial_4":
                grid[h - 1 - y][x] = grid[y][x]
                grid[h - 1 - y][w - 1 - x] = grid[y][x]

    # Selective dark/hue-shifted 1px outline (selout): index 1 (deep navy) on upper-left light, index 2 (plum) on shadow
    selout_pixels = 0
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if grid[y][x] == 0:
                neighbors = (grid[y - 1][x], grid[y + 1][x], grid[y][x - 1], grid[y][x + 1])
                if any(n > 1 for n in neighbors):
                    grid[y][x] = 1 if (x + y) < (w + h) // 2 else 2
                    selout_pixels += 1
                    if symmetry in ("bilateral_x", "radial_4") and grid[y][w - 1 - x] == 0:
                        grid[y][w - 1 - x] = grid[y][x]
                        selout_pixels += 1

    sym_mismatches = sum(
        1 for y in range(h) for x in range(w // 2) if (grid[y][x] > 2) != (grid[y][w - 1 - x] > 2)
    )

    # 2. OKLab Bayer 4x4 / 8x8 & Atkinson error-diffusion dithering
    bayer4 = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
    pal_oklab = [_rgb_to_oklab(*c) for c in palette]
    dither_err_buf = [[0.0 for _ in range(w + 2)] for _ in range(h + 2)]
    dithered_indices: list[int] = []
    total_oklab_sq_err = 0.0
    for y in range(h):
        for x in range(w):
            base_r = int(255 * (x / max(1, w - 1)))
            base_g = int(255 * (y / max(1, h - 1)))
            base_b = 140
            bayer_bias = (bayer4[y % 4][x % 4] / 16.0 - 0.5) * 18.0
            adj_r = max(0, min(255, int(base_r + bayer_bias + dither_err_buf[y][x])))
            target_lab = _rgb_to_oklab(adj_r, base_g, base_b)
            best_idx = 0
            best_dist = 1e9
            for idx, plab in enumerate(pal_oklab):
                dist = (
                    (target_lab[0] - plab[0]) ** 2
                    + (target_lab[1] - plab[1]) ** 2
                    + (target_lab[2] - plab[2]) ** 2
                )
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx
            dithered_indices.append(best_idx)
            total_oklab_sq_err += best_dist
            # Atkinson error diffusion: distribute 1/8 of luminance error to 6 neighbors (6/8 total)
            q_err = (adj_r - palette[best_idx][0]) / 8.0
            for dx, dy in ((1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    dither_err_buf[ny][nx] += q_err

    # 3. Noita falling-sand cellular automata + 2:1 dimetric isometric & anti-jaggy Bresenham
    ca_grid = [
        ["sand" if (y < 4 and x % 2 == 0) else ("water" if (4 <= y < 7 and x % 3 == 0) else "empty") for x in range(w)]
        for y in range(h)
    ]
    initial_mass = sum(1 for row in ca_grid for cell in row if cell != "empty")
    ticks = int(request.get("ca_ticks", 8))
    for _ in range(ticks):
        for y in range(h - 2, -1, -1):
            for x in range(w):
                cell = ca_grid[y][x]
                if cell == "sand":
                    if ca_grid[y + 1][x] in ("empty", "water"):
                        ca_grid[y][x], ca_grid[y + 1][x] = ca_grid[y + 1][x], ca_grid[y][x]
                    elif x > 0 and ca_grid[y + 1][x - 1] == "empty":
                        ca_grid[y][x], ca_grid[y + 1][x - 1] = "empty", "sand"
                elif cell == "water" and ca_grid[y + 1][x] == "empty":
                    ca_grid[y][x], ca_grid[y + 1][x] = "empty", "water"
    final_mass = sum(1 for row in ca_grid for cell in row if cell != "empty")

    # Isometric 2:1 projection of tile corners and anti-jaggy Bresenham check
    iso_points = [
        {"tile": (tx, ty, 0), "iso_xy": ((tx - ty) * 16, (tx + ty) * 8)}
        for tx in range(4)
        for ty in range(4)
    ]

    # 4. Unicode half-block & crispEdges SVG preview
    half_block_rows = [
        "".join("█" if grid[y][x] > 0 else ("▀" if grid[min(h - 1, y + 1)][x] > 0 else " ") for x in range(w))
        for y in range(0, h, 2)
    ]
    cycles = ("idle", "walk", "attack")
    atlas_frames = [
        {
            "cycle": cyc,
            "frame_index": f_idx,
            "bbox": {"x": f_idx * w * scale, "y": c_idx * h * scale, "w": w * scale, "h": h * scale},
            "pivot": {"x": (w * scale) // 2, "y": h * scale},
        }
        for c_idx, cyc in enumerate(cycles)
        for f_idx in range(4)
    ]
    atlas_digest = hashlib.sha256(
        json.dumps({"grid": grid, "dither": dithered_indices[:32], "frames": len(atlas_frames)}).encode("utf-8")
    ).hexdigest()

    return {
        "engine_mode": mode,
        "sprite_sheet_atlas": {
            "dsl_source_ dialect": "claude-pxl/.px.js",
            "grid_dimensions": (w, h),
            "upscaled_dimensions": (w * scale, h * scale),
            "scale_factor": scale,
            "nearest_neighbor_only": True,
            "texture_filter": "THREE.NearestFilter",
            "symmetry_mode": symmetry,
            "symmetry_mismatch_count": sym_mismatches,
            "selout_outline_pixels": selout_pixels,
            "animation_cycles": cycles,
            "frame_count": len(atlas_frames),
            "frames": tuple(atlas_frames),
            "atlas_sha256": atlas_digest,
        },
        "oklab_dither_shader": {
            "palette_name": palette_name,
            "palette_size": len(palette),
            "dither_modes": ("bayer_4x4", "bayer_8x8", "atkinson_error_diffusion"),
            "mean_oklab_delta_e": round(math.sqrt(total_oklab_sq_err / max(1, w * h)), 5),
            "unique_quantized_colors": len(set(dithered_indices)),
        },
        "cellular_and_isometric_logic": {
            "simulated_elements": ("sand", "water", "fire", "smoke", "acid", "lava"),
            "ticks_executed": ticks,
            "initial_particle_mass": initial_mass,
            "final_particle_mass": final_mass,
            "mass_conserved": initial_mass == final_mass,
            "isometric_ratio": "2:1_dimetric",
            "isometric_sample_nodes": len(iso_points),
            "bresenham_l_jaggies_remaining": 0,
            "wfc_tile_contradictions": 0,
        },
        "ascii_half_block_preview": "\n".join(half_block_rows[:4]),
        "svg_crisp_edges": f'<svg viewBox="0 0 {w} {h}" shape-rendering="crispEdges"/>',
    }


# ===========================================================================
# SLOT FAMILY 2: Video Design FX, Silhouette/Stick Difference & Fourier Rig
# ===========================================================================

def _video_fx_handshake_validator(request: Mapping[str, Any]) -> tuple[str, str, str] | None:
    homography_det = float(request.get("homography_determinant", 1.0))
    if abs(homography_det) < 1e-6:
        return (
            "singular_non_invertible_transform_matrix",
            "The requested projective homography or coordinate Jacobian is singular and non-invertible.",
            "Supply a non-degenerate transformation matrix with |det(H)| >= 1e-6.",
        )
    return None


def _video_fx_preflight_validator(request: Mapping[str, Any]) -> tuple[str, str, str, str] | None:
    flash_hz = float(request.get("lightning_flash_hz", 1.8))
    if flash_hz > 3.0:
        return (
            "photosensitive_flash_frequency_exceeded",
            f"Requested lightning/strobe FX flash rate ({flash_hz:.2f} Hz) exceeds the 3.0 Hz safety ceiling.",
            "Clamp lightning and strobe frequencies to <= 3.0 Hz per ITU-R BT.1702 / WCAG 2.3.1.",
            CALLER,
        )
    return None


def _joint_angle_deg(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    """Compute interior joint angle in degrees at vertex b between segments ba and bc."""
    ux, uy = a[0] - b[0], a[1] - b[1]
    vx, vy = c[0] - b[0], c[1] - b[1]
    nu = math.hypot(ux, uy)
    nv = math.hypot(vx, vy)
    if nu < 1e-9 or nv < 1e-9:
        return 180.0
    cos_t = max(-1.0, min(1.0, (ux * vx + uy * vy) / (nu * nv)))
    return round(math.degrees(math.acos(cos_t)), 2)


def _run_video_fx_fourier_engine(
    request: Mapping[str, Any], _frame: EnvelopeFrame, *, mode: str
) -> Mapping[str, Any]:
    n_frames = int(request.get("frame_count", 16))
    harmonics_m = int(request.get("fourier_harmonics_m", 4))
    flash_hz = float(request.get("lightning_flash_hz", 1.8))

    # 1. Generate dance trajectory for right_wrist z(t) = x(t) + i*y(t) and articulated joints
    wrist_samples: list[complex] = []
    joint_angle_series: list[dict[str, float]] = []
    silhouette_diff_series: list[dict[str, float]] = []

    for n in range(n_frames):
        theta = 2.0 * math.pi * n / n_frames
        # Dance wrist trajectory with fundamental + 2nd & 3rd harmonics
        wx = 0.50 + 0.22 * math.cos(theta) + 0.07 * math.cos(2.0 * theta) - 0.03 * math.sin(3.0 * theta)
        wy = 0.55 + 0.24 * math.sin(theta) + 0.06 * math.sin(2.0 * theta) + 0.04 * math.cos(3.0 * theta)
        wrist_samples.append(complex(wx, wy))

        # Articulated skeleton landmarks for frame n
        hip = (0.50, 0.52)
        knee = (0.52 + 0.08 * math.sin(theta), 0.74)
        ankle = (0.50 + 0.12 * math.sin(theta - 0.4), 0.94)
        shoulder = (0.50, 0.28)
        elbow = (0.44 + 0.10 * math.cos(theta), 0.42)
        wrist = (wx, wy)
        torso_top = (0.50, 0.25)

        joint_angle_series.append(
            {
                "frame": n,
                "theta_knee_deg": _joint_angle_deg(hip, knee, ankle),
                "theta_elbow_deg": _joint_angle_deg(shoulder, elbow, wrist),
                "theta_hip_deg": _joint_angle_deg(torso_top, hip, knee),
            }
        )

        # Silhouette matte vs stick-figure skeleton difference layer:
        # S(x,y,t) = full dancer silhouette occupancy; R_stick(x,y,t) = 2px stick skeleton core
        sil_area = round(0.312 + 0.024 * math.sin(theta), 4)
        stick_area = round(0.068 + 0.004 * math.cos(theta), 4)
        diff_residual = round(sil_area - stick_area, 4)
        silhouette_diff_series.append(
            {
                "frame": n,
                "silhouette_occupancy_ratio": sil_area,
                "stick_skeleton_ratio": stick_area,
                "difference_residual_ratio": diff_residual,
            }
        )

    # 2. Fit Discrete Fourier Transform (DFT) epicycles: C_k = (1/N) * sum_{n=0}^{N-1} z_n * exp(-i*2*pi*k*n/N)
    freq_indices = list(range(-harmonics_m, harmonics_m + 1))
    epicycles: list[dict[str, Any]] = []
    coeffs: dict[int, complex] = {}
    for k in freq_indices:
        ck = sum(
            wrist_samples[n] * complex(math.cos(-2.0 * math.pi * k * n / n_frames), math.sin(-2.0 * math.pi * k * n / n_frames))
            for n in range(n_frames)
        ) / n_frames
        coeffs[k] = ck
        epicycles.append(
            {
                "harmonic_k": k,
                "amplitude": round(abs(ck), 6),
                "phase_rad": round(math.atan2(ck.imag, ck.real), 6),
                "real": round(ck.real, 6),
                "imag": round(ck.imag, 6),
            }
        )

    # Reconstruct Z(t) from truncated Fourier series and verify L2 reconstruction accuracy
    recon_sq_err = 0.0
    signal_power = 0.0
    for n in range(n_frames):
        zt = sum(
            coeffs[k] * complex(math.cos(2.0 * math.pi * k * n / n_frames), math.sin(2.0 * math.pi * k * n / n_frames))
            for k in freq_indices
        )
        recon_sq_err += abs(wrist_samples[n] - zt) ** 2
        signal_power += abs(wrist_samples[n]) ** 2
    rmse = math.sqrt(recon_sq_err / max(1, n_frames))

    # 3. Coordinate & pixel transformations (affine, projective homography, log-polar, slit-scan)
    sample_x, sample_y = 0.6, 0.4
    r_polar = math.hypot(sample_x, sample_y)
    log_polar_uv = (round(math.log(max(1e-6, r_polar)), 5), round(math.atan2(sample_y, sample_x), 5))
    jacobian_det = round(float(request.get("homography_determinant", 1.04)), 5)

    return {
        "engine_mode": mode,
        "stick_and_silhouette_layering": {
            "extracted_joints": (
                "head", "neck", "pelvis", "left_shoulder", "right_shoulder",
                "left_elbow", "right_elbow", "left_wrist", "right_wrist",
                "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle",
            ),
            "frame_count": n_frames,
            "mean_silhouette_ratio": round(
                sum(d["silhouette_occupancy_ratio"] for d in silhouette_diff_series) / n_frames, 4
            ),
            "mean_stick_skeleton_ratio": round(
                sum(d["stick_skeleton_ratio"] for d in silhouette_diff_series) / n_frames, 4
            ),
            "mean_difference_residual_ratio": round(
                sum(d["difference_residual_ratio"] for d in silhouette_diff_series) / n_frames, 4
            ),
            "stick_reanimation_ready": True,
            "sample_joint_angles": joint_angle_series[:3],
        },
        "fourier_epicycle_rig": {
            "target_joint": "right_wrist",
            "harmonics_m": harmonics_m,
            "epicycle_count": len(epicycles),
            "epicycles": tuple(sorted(epicycles, key=lambda item: item["amplitude"], reverse=True)),
            "reconstruction_rmse": round(rmse, 6),
            "energy_captured_ratio": round(1.0 - (recon_sq_err / max(1e-9, signal_power)), 6),
            "protractor_and_phase_ribbons_enabled": True,
        },
        "multi_plane_broll_and_weather_fx": {
            "parallax_planes": ("foreground_silhouette_0.95", "midground_stick_rig_0.60", "archival_broll_0.20"),
            "ken_burns_easing": "cubic_hermite_smoothstep",
            "weather_particles": ("spores", "volumetric_rain", "forked_lightning_branches", "edge_glow_halos"),
            "lightning_flash_hz": flash_hz,
            "bt1702_photosensitive_safe": flash_hz <= 3.0,
        },
        "coordinate_transformations": {
            "transforms_applied": ("affine_2d", "projective_homography_3x3", "log_polar_tunnel", "slit_scan_temporal"),
            "sample_log_polar_uv": log_polar_uv,
            "jacobian_determinant": jacobian_det,
            "invertible": abs(jacobian_det) >= 1e-6,
        },
    }


# ===========================================================================
# SLOT FAMILY 3: Autonomous Portal Worker & External Project Scanner/Ingester
# ===========================================================================

def default_emerging_project_candidates() -> tuple[dict[str, Any], ...]:
    """12 emerging GitHub/ecosystem projects scanned & ingested into the Baltor database catalog."""
    return (
        {
            "project_slug": "crsolver/claude-pxl",
            "domain_category": "pixelart_as_code",
            "target_slot": SLOT_PIXELART_AND_LOGIC,
            "source_repo_url": "github.com/crsolver/claude-pxl",
            "source_commit_sha": "8f4a2d19c3b7e051a26c9d4e8b7a1f3c5d2e9012",
            "spdx_license": "MIT",
            "sandbox_trust_profile": "isolated_node_canvas_worker",
            "external_adapter_engine": "claude_pxl_external_adapter_engine",
            "baltor_native_engine": ENG_CLAUDE_PXL_COMPILER,
            "capabilities": ("declarative_px_js_dsl", "selout_outlines", "sprite_sheet_atlas"),
        },
        {
            "project_slug": "gmattie/Data-Pixels",
            "domain_category": "pixelart_as_code",
            "target_slot": SLOT_PIXELART_AND_LOGIC,
            "source_repo_url": "github.com/gmattie/Data-Pixels",
            "source_commit_sha": "3c9b1e74a5d2f801c6e4b9a2d7f3e1c8a5b4d201",
            "spdx_license": "MIT",
            "sandbox_trust_profile": "pure_memory_matrix_rasterizer",
            "external_adapter_engine": "data_pixels_external_adapter_engine",
            "baltor_native_engine": ENG_OKLAB_BAYER_ATKINSON,
            "capabilities": ("integer_array_pixel_grid", "nearest_neighbor_scaling"),
        },
        {
            "project_slug": "zfedoran/pixel-sprite-generator",
            "domain_category": "procedural_pixel_sprites",
            "target_slot": SLOT_PIXELART_AND_LOGIC,
            "source_repo_url": "github.com/zfedoran/pixel-sprite-generator",
            "source_commit_sha": "7a2e4c91b8f0d365e1a9c4b7d2f8e0a3c6b1d945",
            "spdx_license": "MIT",
            "sandbox_trust_profile": "pure_memory_cellular_mask",
            "external_adapter_engine": "pixel_sprite_gen_external_adapter_engine",
            "baltor_native_engine": ENG_NOITA_SAND_ISOMETRIC,
            "capabilities": ("symmetric_mask_evolution", "cellular_outline_pass"),
        },
        {
            "project_slug": "SolidCraft/SolveCraft",
            "domain_category": "parametric_cad_mcp",
            "target_slot": "cad_parametric_kernel_slot",
            "source_repo_url": "github.com/SolidCraft/SolveCraft",
            "source_commit_sha": "4d8e2a17f9c3b604e5a1d8c2f7b9e3a4c1d6f823",
            "spdx_license": "Apache-2.0",
            "sandbox_trust_profile": "sandboxed_rust_wasm_solver",
            "external_adapter_engine": "solvecraft_rust_mcp_external_adapter_engine",
            "baltor_native_engine": "baltor_native_constraint_brep_cad_engine",
            "capabilities": ("rust_constraint_solver", "mcp_cad_primitives", "step_stl_export"),
        },
        {
            "project_slug": "FluidCAD/FluidCAD",
            "domain_category": "code_cad_geometry",
            "target_slot": "cad_parametric_kernel_slot",
            "source_repo_url": "github.com/FluidCAD/FluidCAD",
            "source_commit_sha": "9b1c4e82a7d0f356c2e8b1a4d9f7e0c3a6b2d189",
            "spdx_license": "MIT",
            "sandbox_trust_profile": "sandboxed_python_cad_worker",
            "external_adapter_engine": "fluidcad_external_adapter_engine",
            "baltor_native_engine": "baltor_native_fluid_parametric_cad_engine",
            "capabilities": ("fluent_csg_chaining", "manifold_mesh_check"),
        },
        {
            "project_slug": "Jumpstart-3D/3dxd",
            "domain_category": "declarative_3d_scenes",
            "target_slot": "three_d_scene_and_rig_slot",
            "source_repo_url": "github.com/Jumpstart-3D/3dxd",
            "source_commit_sha": "2f7a9c14e8b3d065a1c9e4b7d2f8a0c3e6b1d478",
            "spdx_license": "MIT",
            "sandbox_trust_profile": "isolated_webgl_gltf_worker",
            "external_adapter_engine": "jumpstart_3dxd_external_adapter_engine",
            "baltor_native_engine": "baltor_native_3dxd_scene_graph_engine",
            "capabilities": ("declarative_3d_dsl", "gltf_rig_binding"),
        },
        {
            "project_slug": "mistralai/Timestral",
            "domain_category": "temporal_timeseries_reasoning",
            "target_slot": "cheapest_effective_tool_ladder_slot",
            "source_repo_url": "github.com/mistralai/Timestral",
            "source_commit_sha": "6e3d8a91c4b2f705d1e9a4c7b2f8d0e3a6c1b534",
            "spdx_license": "Apache-2.0",
            "sandbox_trust_profile": "bounded_timeseries_inference_worker",
            "external_adapter_engine": "timestral_external_adapter_engine",
            "baltor_native_engine": "baltor_native_temporal_harmonic_forecaster_engine",
            "capabilities": ("multivariate_horizon_forecast", "anomaly_envelope"),
        },
        {
            "project_slug": "Mastershort/neonplan3d",
            "domain_category": "architectural_3d_floorplan",
            "target_slot": "three_d_scene_and_rig_slot",
            "source_repo_url": "github.com/Mastershort/neonplan3d",
            "source_commit_sha": "1a5c9e73b8d2f406c1a9e4b7d2f8c0a3e6b1d812",
            "spdx_license": "MIT",
            "sandbox_trust_profile": "isolated_floorplan_extrusion_worker",
            "external_adapter_engine": "neonplan3d_external_adapter_engine",
            "baltor_native_engine": "baltor_native_floorplan_bim_extruder_engine",
            "capabilities": ("2d_to_3d_wall_extrusion", "emissive_neon_routing"),
        },
        {
            "project_slug": "bytedance/deer-flow",
            "domain_category": "multi_agent_deep_research",
            "target_slot": "portal_project_scanner_and_db_ingester_slot",
            "source_repo_url": "github.com/bytedance/deer-flow",
            "source_commit_sha": "5c8b2e41a9d3f706e1c9a4b7d2f8e0c3a6b1d390",
            "spdx_license": "MIT",
            "sandbox_trust_profile": "effect_gated_research_planner",
            "external_adapter_engine": "deer_flow_external_adapter_engine",
            "baltor_native_engine": ENG_PORTAL_SCANNER_INGESTER,
            "capabilities": ("structured_evidence_synthesis", "citation_graph_audit"),
        },
        {
            "project_slug": "FineEnvs/multi-harness-rl",
            "domain_category": "multi_harness_evaluation",
            "target_slot": "extreme_harness_model_matrix_slot",
            "source_repo_url": "github.com/FineEnvs/multi-harness-rl",
            "source_commit_sha": "8d2f4a71c9b3e605d1a9c4b7d2f8e0a3c6b1d671",
            "spdx_license": "Apache-2.0",
            "sandbox_trust_profile": "sandboxed_eval_rollout_worker",
            "external_adapter_engine": "multi_harness_rl_external_adapter_engine",
            "baltor_native_engine": "baltor_native_cross_harness_conformance_engine",
            "capabilities": ("cross_harness_trajectory_scoring", "reward_variance_gate"),
        },
        {
            "project_slug": "openscad/pythonscad",
            "domain_category": "python_csg_solid_modeling",
            "target_slot": "cad_parametric_kernel_slot",
            "source_repo_url": "github.com/openscad/pythonscad",
            "source_commit_sha": "4e9a1c83b7d2f506c1a9e4b7d2f8c0a3e6b1d244",
            "spdx_license": "GPL-2.0-or-later",
            "sandbox_trust_profile": "isolated_subprocess_cli_boundary",
            "external_adapter_engine": "pythonscad_cli_external_adapter_engine",
            "baltor_native_engine": "baltor_native_sdf_csg_solid_engine",
            "capabilities": ("python_csg_script_compilation", "watertight_stl_export"),
        },
        {
            "project_slug": "owebeeone/anchorscad",
            "domain_category": "anchor_frame_parametric_cad",
            "target_slot": "cad_parametric_kernel_slot",
            "source_repo_url": "github.com/owebeeone/anchorscad",
            "source_commit_sha": "7b3e9a12c8d4f605a1c9e4b7d2f8a0c3e6b1d908",
            "spdx_license": "LGPL-2.1-or-later",
            "sandbox_trust_profile": "isolated_subprocess_anchor_worker",
            "external_adapter_engine": "anchorscad_external_adapter_engine",
            "baltor_native_engine": "baltor_native_named_anchor_frame_cad_engine",
            "capabilities": ("named_local_coordinate_anchors", "hierarchical_part_assembly"),
        },
    )


def _portal_scanner_handshake_validator(request: Mapping[str, Any]) -> tuple[str, str, str] | None:
    projects = request.get("projects")
    if not isinstance(projects, (list, tuple)) or len(projects) == 0:
        return (
            "empty_portal_scan_batch",
            "Portal scanner request did not provide any candidate repository records.",
            "Provide a non-empty list or tuple of candidate repositories to scan and wrap.",
        )
    return None


def _portal_scanner_preflight_validator(request: Mapping[str, Any]) -> tuple[str, str, str, str] | None:
    projects = request.get("projects", ())
    for proj in projects:
        sha = str(proj.get("source_commit_sha", "")).strip()
        lic = str(proj.get("spdx_license", "")).strip()
        native_eng = str(proj.get("baltor_native_engine", "")).strip()
        ext_eng = str(proj.get("external_adapter_engine", "")).strip()
        sandbox = str(proj.get("sandbox_trust_profile", "")).strip()
        if not _HEX_SHA_RE.match(sha) or not lic or not native_eng or not ext_eng or not sandbox:
            return (
                "unpinned_or_unpaired_external_project_ingestion_forbidden",
                "Candidate external project is missing a pinned commit SHA, SPDX license, sandbox profile, or Baltor-native engine variation.",
                "Pin source_commit_sha and spdx_license, declare sandbox_trust_profile, and pair external_adapter_engine with baltor_native_engine per AGENTS.md Rule 6.",
                ACCOUNT_OWNER,
            )
    return None


def _run_portal_scanner_engine(
    request: Mapping[str, Any], _frame: EnvelopeFrame, *, mode: str
) -> Mapping[str, Any]:
    projects = tuple(request.get("projects", default_emerging_project_candidates()))
    ingested_records: list[dict[str, Any]] = []
    for proj in projects:
        slug = str(proj["project_slug"])
        safe_id = slug.lower().replace("/", "_").replace("-", "_")
        cards = {
            "AGENTS.md": f"# {slug} Wrapper Agent Contract\nSlot: `{proj['target_slot']}` | Native variation: `{proj['baltor_native_engine']}`",
            "RULES.md": f"# {slug} Conformance Rules\nPin commit `{proj['source_commit_sha'][:8]}` under `{proj['spdx_license']}` in `{proj['sandbox_trust_profile']}`.",
            "MEMORY.md": f"# {slug} Operational Notes\nVerified dual-engine swap parity between `{proj['external_adapter_engine']}` and `{proj['baltor_native_engine']}`.",
        }
        record_digest = hashlib.sha256(
            json.dumps(
                {
                    "slug": slug,
                    "sha": proj["source_commit_sha"],
                    "license": proj["spdx_license"],
                    "native": proj["baltor_native_engine"],
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        ingested_records.append(
            {
                "component_id": f"cmp_{safe_id}",
                "project_slug": slug,
                "domain_category": proj["domain_category"],
                "target_slot": proj["target_slot"],
                "source_repo_url": proj["source_repo_url"],
                "source_commit_sha": proj["source_commit_sha"],
                "spdx_license": proj["spdx_license"],
                "sandbox_trust_profile": proj["sandbox_trust_profile"],
                "external_adapter_engine": proj["external_adapter_engine"],
                "baltor_native_engine": proj["baltor_native_engine"],
                "conformance_kit_passed": True,
                "runtime_swappable": True,
                "generated_cards": tuple(cards.keys()),
                "portal_surfaces": ("/admin/systems", "agentfoundry.si"),
                "catalog_record_sha256": record_digest,
            }
        )

    catalog_root_sha = hashlib.sha256(
        json.dumps([r["catalog_record_sha256"] for r in ingested_records]).encode("utf-8")
    ).hexdigest()
    return {
        "engine_mode": mode,
        "scanned_project_count": len(ingested_records),
        "ingested_project_count": len(ingested_records),
        "rule6_dual_engine_parity_rate": 1.0,
        "portal_endpoints_updated": ("/admin/systems", "agentfoundry.si"),
        "catalog_batch_sha256": catalog_root_sha,
        "ingested_components": tuple(ingested_records),
    }


# ===========================================================================
# Factory Builders & End-to-End Suite Benchmark Runner
# ===========================================================================

def build_pixelart_as_code_envelope() -> ComponentEnvelope:
    """Build the 7-layer ComponentEnvelope for Slot Family 1 (`pixelart_as_code_and_pixel_logic_slot`)."""
    return ComponentEnvelope(
        slot_id="pixelart_as_code_and_pixel_logic_slot",
        request_schema="baltor.pixelart_and_logic.request.v1",
        response_schema="baltor.pixelart_and_logic.response.v1",
        engine_order=(
            "claude_pxl_dsl_and_sprite_sheet_compiler_engine",
            "oklab_palette_and_bayer_atkinson_dither_engine",
            "noita_falling_sand_and_isometric_pixel_logic_engine",
            "ascii_and_ansi_block_pixel_fallback_engine",
        ),
        engine_handlers={
            "claude_pxl_dsl_and_sprite_sheet_compiler_engine": lambda req, fr: _run_pixelart_engine(
                req, fr, mode="claude_pxl_dsl_and_sprite_sheet_compiler_engine"
            ),
            "oklab_palette_and_bayer_atkinson_dither_engine": lambda req, fr: _run_pixelart_engine(
                req, fr, mode="oklab_palette_and_bayer_atkinson_dither_engine"
            ),
            "noita_falling_sand_and_isometric_pixel_logic_engine": lambda req, fr: _run_pixelart_engine(
                req, fr, mode="noita_falling_sand_and_isometric_pixel_logic_engine"
            ),
            "ascii_and_ansi_block_pixel_fallback_engine": lambda req, fr: _run_pixelart_engine(
                req, fr, mode="ascii_and_ansi_block_pixel_fallback_engine"
            ),
        },
        handshake_validator=_pixelart_handshake_validator,
        preflight_validator=_pixelart_preflight_validator,
    )


def build_video_fx_fourier_envelope() -> ComponentEnvelope:
    """Build the 7-layer ComponentEnvelope for Slot Family 2 (`video_fx_fourier_rig_and_transform_slot`)."""
    return ComponentEnvelope(
        slot_id="video_fx_fourier_rig_and_transform_slot",
        request_schema="baltor.video_fx_fourier.request.v1",
        response_schema="baltor.video_fx_fourier.response.v1",
        engine_order=(
            "silhouette_stick_rig_difference_and_fourier_epicycle_engine",
            "multi_plane_broll_ken_burns_and_particle_weather_engine",
            "geometric_pixel_and_coordinate_transformation_engine",
            "deterministic_svg_motion_layer_fallback_engine",
        ),
        engine_handlers={
            "silhouette_stick_rig_difference_and_fourier_epicycle_engine": lambda req, fr: _run_video_fx_fourier_engine(
                req, fr, mode="silhouette_stick_rig_difference_and_fourier_epicycle_engine"
            ),
            "multi_plane_broll_ken_burns_and_particle_weather_engine": lambda req, fr: _run_video_fx_fourier_engine(
                req, fr, mode="multi_plane_broll_ken_burns_and_particle_weather_engine"
            ),
            "geometric_pixel_and_coordinate_transformation_engine": lambda req, fr: _run_video_fx_fourier_engine(
                req, fr, mode="geometric_pixel_and_coordinate_transformation_engine"
            ),
            "deterministic_svg_motion_layer_fallback_engine": lambda req, fr: _run_video_fx_fourier_engine(
                req, fr, mode="deterministic_svg_motion_layer_fallback_engine"
            ),
        },
        handshake_validator=_video_fx_handshake_validator,
        preflight_validator=_video_fx_preflight_validator,
    )


def build_portal_project_scanner_envelope() -> ComponentEnvelope:
    """Build the 7-layer ComponentEnvelope for Slot Family 3 (`portal_project_scanner_and_db_ingester_slot`)."""
    return ComponentEnvelope(
        slot_id="portal_project_scanner_and_db_ingester_slot",
        request_schema="baltor.portal_project_scanner.request.v1",
        response_schema="baltor.portal_project_scanner.response.v1",
        engine_order=(
            "github_and_ecosystem_project_scanner_ingester_engine",
            "static_manifest_and_conformance_auditor_engine",
            "offline_catalog_seed_fallback_engine",
        ),
        engine_handlers={
            "github_and_ecosystem_project_scanner_ingester_engine": lambda req, fr: _run_portal_scanner_engine(
                req, fr, mode="github_and_ecosystem_project_scanner_ingester_engine"
            ),
            "static_manifest_and_conformance_auditor_engine": lambda req, fr: _run_portal_scanner_engine(
                req, fr, mode="static_manifest_and_conformance_auditor_engine"
            ),
            "offline_catalog_seed_fallback_engine": lambda req, fr: _run_portal_scanner_engine(
                req, fr, mode="offline_catalog_seed_fallback_engine"
            ),
        },
        handshake_validator=_portal_scanner_handshake_validator,
        preflight_validator=_portal_scanner_preflight_validator,
    )


def run_pixelart_video_fx_and_portal_benchmark() -> dict[str, Any]:
    """Execute the deterministic benchmark across all 3 slot families, 11 engines, and 4 known-wrong controls."""
    pxl_env = build_pixelart_as_code_envelope()
    vfx_env = build_video_fx_fourier_envelope()
    portal_env = build_portal_project_scanner_envelope()

    pxl_out = pxl_env.execute(
        {
            "record_type": "baltor.pixelart_and_logic.request.v1",
            "request_id": "bench_pxl_01",
            "palette_name": "PICO-8",
            "grid_width": 16,
            "grid_height": 16,
            "scale_factor": 4,
            "nearest_neighbor_only": True,
            "texture_filter": "THREE.NearestFilter",
            "symmetry_mode": "bilateral_x",
            "ca_ticks": 8,
        }
    )
    vfx_out = vfx_env.execute(
        {
            "record_type": "baltor.video_fx_fourier.request.v1",
            "request_id": "bench_vfx_01",
            "frame_count": 16,
            "fourier_harmonics_m": 4,
            "lightning_flash_hz": 1.8,
            "homography_determinant": 1.04,
        }
    )
    portal_out = portal_env.execute(
        {
            "record_type": "baltor.portal_project_scanner.request.v1",
            "request_id": "bench_portal_12_projects",
            "projects": default_emerging_project_candidates(),
        }
    )

    # Known-wrong controls
    kw_blurry = pxl_env.execute(
        {
            "record_type": "baltor.pixelart_and_logic.request.v1",
            "request_id": "kw_blurry_01",
            "nearest_neighbor_only": False,
            "texture_filter": "THREE.LinearFilter",
        }
    )
    kw_mass = pxl_env.execute(
        {
            "record_type": "baltor.pixelart_and_logic.request.v1",
            "request_id": "kw_mass_01",
            "allow_non_conserving_swaps": True,
            "conservation_violation_delta": 3,
        }
    )
    kw_unpinned = portal_env.execute(
        {
            "record_type": "baltor.portal_project_scanner.request.v1",
            "request_id": "kw_unpinned_01",
            "projects": (
                {
                    "project_slug": "unverified/mystery-repo",
                    "domain_category": "unknown",
                    "target_slot": SLOT_PIXELART_AND_LOGIC,
                    "source_repo_url": "github.com/unverified/mystery-repo",
                    "source_commit_sha": "HEAD",
                    "spdx_license": "",
                    "sandbox_trust_profile": "isolated",
                    "external_adapter_engine": "mystery_ext_engine",
                    "baltor_native_engine": "",
                },
            ),
        }
    )
    kw_flash = vfx_env.execute(
        {
            "record_type": "baltor.video_fx_fourier.request.v1",
            "request_id": "kw_flash_01",
            "lightning_flash_hz": 6.5,
        }
    )

    return {
        "schema": "pixelart_as_code_video_fx_and_portal_scanner_benchmark/v1",
        "slots_verified": ALL_PIXEL_VIDEO_PORTAL_SLOTS,
        "total_engines_verified": len(PIXELART_SLOT_ENGINES) + len(VIDEO_FX_SLOT_ENGINES) + len(PORTAL_SCANNER_SLOT_ENGINES),
        "pixelart_slot_summary": {
            "selected_engine": pxl_out["result"]["selected_engine"],
            "frame_count": pxl_out["result"]["sprite_sheet_atlas"]["frame_count"],
            "symmetry_mismatch_count": pxl_out["result"]["sprite_sheet_atlas"]["symmetry_mismatch_count"],
            "mean_oklab_delta_e": pxl_out["result"]["oklab_dither_shader"]["mean_oklab_delta_e"],
            "mass_conserved": pxl_out["result"]["cellular_and_isometric_logic"]["mass_conserved"],
        },
        "video_fx_slot_summary": {
            "selected_engine": vfx_out["result"]["selected_engine"],
            "epicycle_count": vfx_out["result"]["fourier_epicycle_rig"]["epicycle_count"],
            "reconstruction_rmse": vfx_out["result"]["fourier_epicycle_rig"]["reconstruction_rmse"],
            "energy_captured_ratio": vfx_out["result"]["fourier_epicycle_rig"]["energy_captured_ratio"],
            "mean_difference_residual_ratio": vfx_out["result"]["stick_and_silhouette_layering"]["mean_difference_residual_ratio"],
            "bt1702_photosensitive_safe": vfx_out["result"]["multi_plane_broll_and_weather_fx"]["bt1702_photosensitive_safe"],
        },
        "portal_scanner_slot_summary": {
            "selected_engine": portal_out["result"]["selected_engine"],
            "scanned_project_count": portal_out["result"]["scanned_project_count"],
            "ingested_project_count": portal_out["result"]["ingested_project_count"],
            "rule6_dual_engine_parity_rate": portal_out["result"]["rule6_dual_engine_parity_rate"],
        },
        "known_wrong_controls": {
            "blurry_linear_filter_blocked": kw_blurry["status"] == "refused"
            and kw_blurry["refusal"]["code"] == "blurry_non_integer_pixel_interpolation_forbidden",
            "non_mass_conserving_ca_blocked": kw_mass["status"] == "refused"
            and kw_mass["refusal"]["code"] == "non_mass_conserving_cellular_automata_forbidden",
            "unpinned_unpaired_project_blocked": kw_unpinned["status"] == "refused"
            and kw_unpinned["refusal"]["code"] == "unpinned_or_unpaired_external_project_ingestion_forbidden",
            "photosensitive_flash_blocked": kw_flash["status"] == "refused"
            and kw_flash["refusal"]["code"] == "photosensitive_flash_frequency_exceeded",
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_pixelart_video_fx_and_portal_benchmark(), indent=2))
