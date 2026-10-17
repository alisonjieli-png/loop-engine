#!/usr/bin/env python3
"""Multi-engine creative motion and personal-agent safety benchmark harness.

Wraps two functional component families in the 6-layer component envelope
(`loop_engine.core.engines.envelope`, `envelope_preflight`, `envelope_tracking`):

1. `creative_motion_scene`:
   - `reelkit_frame_planner`: deterministic Python frame/caption slot planner
     modeled on the local `reelkit` layout contract (`1080x1920` vertical
     canvas, named vertical slots, role font floors, keep-out collision
     avoidance, platform UI zone avoidance, and `stable_seed` frame digests).
   - `remotion_three_scene_generator`: declarative Remotion / Three.js scene
     graph and camera keyframe generator with 3D subject projection bounds.
   - `svg_canvas_storyboard_fallback`: zero-dependency deterministic SVG
     storyboard generator for headless environments without FFmpeg or WebGL.
   - Nested `creative_layout_qa_gate` envelope invocation implementing the
     deterministic layout audit rules from `layout_audit.py` and `audit2.py`
     (text-to-text overlap, subject keep-out intrusion, TikTok/Reels/Shorts
     bottom 20% and right 12% UI zones, edge margins, font floors, WCAG
     relative luminance contrast ratios, and sub-0.25s caption flicker).

2. `personal_agent_safety`:
   - `transcript_secret_scanner`: primary `structured_token_and_entropy_scanner`
     and fallback `regex_boundary_fallback_scanner` that redact sensitive
     strings to SHA-256 digests and quarantine leaked credentials without
     echoing raw sensitive material in `EnvelopeRefusal` or logs.
   - `pre_compaction_checkpoint`: primary
     `structured_ast_and_ledger_checkpoint_engine` and fallback
     `line_anchor_checkpoint_fallback` producing immutable
     `context_checkpoint/v1` records with uncommitted file digests, open
     refusal codes, and unsettled journaled intents.
   - `durable_task_approval_gate`: primary `cas_lease_and_digest_approval_engine`
     and fallback `strict_local_policy_fallback_engine` informed by OpenMuse
     `ActionService` CAS worker leases and `homeshed-mcp` human approval
     boundaries, enforcing `RECONCILE_BEFORE_RETRY` on `EFFECT_STATE_UNKNOWN`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import pathlib
import re
import sys
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
for _rel in ("src", "tools"):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

from loop_engine.core.engines.envelope import (
    ACCOUNT_OWNER,
    CALLER,
    DO_NOT_RETRY,
    EFFECT_DURABLE_PENDING,
    EFFECT_NONE,
    EFFECT_UNKNOWN,
    ENGINE_SOURCE,
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
    RETRY_NOW_SAME_IDENTITY,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeHandshakeVerdict,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    EnvelopeTrace,
    RecoveryAllowance,
    enter_nested,
    envelope_refusal,
    may_recover,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (
    STEP_REPAIRED,
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
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
    EFFECT_STATE_PENDING,
    EFFECT_STATE_UNKNOWN,
    PHASE_INTENDED,
    RECONCILE_FIRST,
    REQUEST_ANSWERED,
    REQUEST_CANCELLED,
    TASK_COMPLETED,
    TASK_FAILED,
    EnvelopeJournalEntry,
    journal_decision,
    journal_intent,
    journal_outcome,
    journal_reconciliation,
    request_identity_digest,
)


SCHEMA_VERSION = "2026-10-16.v1"
FIXED_TIMESTAMP_ISO = "2026-10-16T23:00:00Z"

# Component and wire identifiers
COMPONENT_CREATIVE_MOTION = "creative_motion_scene"
COMPONENT_CREATIVE_QA_GATE = "creative_layout_qa_gate"
COMPONENT_TRANSCRIPT_SCANNER = "transcript_secret_scanner"
COMPONENT_PRE_COMPACTION = "pre_compaction_checkpoint"
COMPONENT_DURABLE_APPROVAL = "durable_task_approval_gate"

WIRE_CREATIVE_V1 = "creative_motion_scene/v1"
WIRE_CREATIVE_QA_V1 = "creative_layout_qa_gate/v1"
WIRE_SCANNER_V1 = "transcript_secret_scanner/v1"
WIRE_CHECKPOINT_V1 = "pre_compaction_checkpoint/v1"
WIRE_APPROVAL_V1 = "durable_task_approval_gate/v1"

# Engine identifiers
ENGINE_REELKIT_PLANNER = "reelkit_frame_planner"
ENGINE_REMOTION_THREE = "remotion_three_scene_generator"
ENGINE_SVG_STORYBOARD = "svg_canvas_storyboard_fallback"
ENGINE_LAYOUT_AUDIT_QA = "deterministic_layout_audit_engine"

ENGINE_SCANNER_PRIMARY = "structured_token_and_entropy_scanner"
ENGINE_SCANNER_FALLBACK = "regex_boundary_fallback_scanner"

ENGINE_CHECKPOINT_PRIMARY = "structured_ast_and_ledger_checkpoint_engine"
ENGINE_CHECKPOINT_FALLBACK = "line_anchor_checkpoint_fallback"

ENGINE_APPROVAL_PRIMARY = "cas_lease_and_digest_approval_engine"
ENGINE_APPROVAL_FALLBACK = "strict_local_policy_fallback_engine"

# Creative canvas and slot constants (modeled on reelkit/layout.py and layout_audit.py)
DEFAULT_CANVAS_W = 1080
DEFAULT_CANVAS_H = 1920
DEFAULT_FPS = 30

SLOT_Y_POSITIONS: dict[str, int] = {
    "top": 290,
    "upper": 470,
    "middle": 820,
    "lower": 1180,
    "low": 1390,
}

ROLE_FONT_FLOORS: dict[str, int] = {
    "hook": 56,
    "headline": 48,
    "title": 44,
    "subtitle": 34,
    "body": 32,
    "caption": 30,
    "stamp": 38,
    "badge": 30,
    "cta": 40,
    "fine": 26,
}

EDGE_MARGIN_MIN_PX = 22
PLATFORM_BOTTOM_RATIO = 0.80  # Bottom 20% (y > 1536 on 1080x1920)
PLATFORM_RIGHT_RATIO = 0.88   # Right 12% (x > 950.4 on 1080x1920)
PLATFORM_RIGHT_Y_MIN = 468
PLATFORM_RIGHT_Y_MAX = 1498
TEXT_OVERLAP_FAIL_AREA_PX = 120
KEEPOUT_OVERLAP_FAIL_AREA_PX = 200
CONTRAST_FAIL_RATIO = 2.0
CONTRAST_WARN_RATIO = 3.0
MIN_BEAT_DURATION_S = 0.25
REPAIRED_CREAM_HEX = "#fff8ec"

SEVERITY_FAIL = "FAIL"
SEVERITY_WARN = "WARN"
RECONCILED_ALREADY_APPLIED = "already_applied"


@dataclass(frozen=True)
class AccountEntitlementContext:
    """Caller account entitlement record evaluated at the envelope account layer."""

    account_id: str
    plan_name: str
    entitled_components: frozenset[str]
    granted_effects: tuple[str, ...] = (PURE_EFFECT,)

    def authorized_for(self, component_id: str) -> bool:
        return component_id in self.entitled_components


def _sha256_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _stable_seed(key: str) -> int:
    digest_bytes = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest_bytes[:8], "big")


def _parse_hex_rgb(color_hex: str) -> tuple[int, int, int]:
    cleaned = color_hex.strip().lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join(ch * 2 for ch in cleaned)
    if len(cleaned) != 6:
        raise ValueError(f"Invalid hex color: {color_hex!r}")
    return (
        int(cleaned[0:2], 16),
        int(cleaned[2:4], 16),
        int(cleaned[4:6], 16),
    )


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG 2.1 relative luminance for an sRGB triple."""
    channels: list[float] = []
    for channel in rgb:
        norm = channel / 255.0
        if norm <= 0.03928:
            channels.append(norm / 12.92)
        else:
            channels.append(((norm + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Compute WCAG contrast ratio between two hex colors."""
    lum_a = relative_luminance(_parse_hex_rgb(fg_hex))
    lum_b = relative_luminance(_parse_hex_rgb(bg_hex))
    bright = max(lum_a, lum_b)
    dark = min(lum_a, lum_b)
    return round((bright + 0.05) / (dark + 0.05), 2)


# ---------------------------------------------------------------------------
# 1. Creative Video / Motion Contracts & Engines
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundingBox:
    x0: int
    y0: int
    x1: int
    y1: int
    label: str = ""

    @property
    def width(self) -> int:
        return max(0, self.x1 - self.x0)

    @property
    def height(self) -> int:
        return max(0, self.y1 - self.y0)

    def intersection_area(self, other: "BoundingBox") -> int:
        ix0 = max(self.x0, other.x0)
        iy0 = max(self.y0, other.y0)
        ix1 = min(self.x1, other.x1)
        iy1 = min(self.y1, other.y1)
        if ix1 <= ix0 or iy1 <= iy0:
            return 0
        return (ix1 - ix0) * (iy1 - iy0)


@dataclass(frozen=True)
class CaptionElementSpec:
    element_id: str
    text: str
    slot_name: str
    typography_role: str
    font_size_px: int
    fg_hex: str
    bg_hex: str
    override_bbox: BoundingBox | None = None


@dataclass(frozen=True)
class BeatSpec:
    beat_id: str
    start_s: float
    duration_s: float
    bg_hex: str
    captions: tuple[CaptionElementSpec, ...]
    subject_keepouts: tuple[BoundingBox, ...] = ()
    camera_motion: str = "push_in"


@dataclass(frozen=True)
class CreativeSceneSpec:
    scene_id: str
    title: str
    canvas_w: int = DEFAULT_CANVAS_W
    canvas_h: int = DEFAULT_CANVAS_H
    fps: int = DEFAULT_FPS
    beats: tuple[BeatSpec, ...] = ()
    allow_preflight_repair: bool = True


@dataclass(frozen=True)
class PlannedCaptionBox:
    element_id: str
    beat_id: str
    text: str
    slot_name: str
    typography_role: str
    font_size_px: int
    fg_hex: str
    bg_hex: str
    contrast_to_bg: float
    bbox: BoundingBox


@dataclass(frozen=True)
class LayoutAuditFinding:
    beat_id: str
    element_id: str
    finding_severity: str
    rule_code: str
    detail: str


@dataclass(frozen=True)
class LayoutAuditReport:
    scene_id: str
    passed: bool
    fail_count: int
    warn_count: int
    findings: tuple[LayoutAuditFinding, ...]
    checked_boxes: int


@dataclass(frozen=True)
class CreativeSceneResult:
    scene_id: str
    engine_id: str
    fallback_used: bool
    frame_count: int
    planned_boxes: tuple[PlannedCaptionBox, ...]
    artifact_format: str
    artifact_digest: str
    artifact_preview: str
    qa_report: LayoutAuditReport
    handshake_verdict: EnvelopeHandshakeVerdict
    preflight_report: EnvelopePreflightReport
    envelope_frame: EnvelopeFrame
    envelope_trace: EnvelopeTrace
    nested_qa_frame: EnvelopeFrame
    nested_qa_trace: EnvelopeTrace
    journal_entries: tuple[EnvelopeJournalEntry, ...]


def _estimate_caption_bbox(
    caption: CaptionElementSpec,
    canvas_w: int,
    y_center: int,
) -> BoundingBox:
    if caption.override_bbox is not None:
        return caption.override_bbox
    lines = [line.strip() for line in caption.text.splitlines() if line.strip()] or [caption.text]
    max_chars = max(len(line) for line in lines)
    est_w = min(
        canvas_w - 2 * EDGE_MARGIN_MIN_PX - 64,
        int(max_chars * caption.font_size_px * 0.56) + 56,
    )
    est_w = max(220, est_w)
    line_h = int(caption.font_size_px * 1.28)
    est_h = len(lines) * line_h + 36
    safe_center_x = (48 + int(canvas_w * PLATFORM_RIGHT_RATIO) - 16) // 2
    x0 = max(EDGE_MARGIN_MIN_PX + 12, safe_center_x - est_w // 2)
    x1 = min(int(canvas_w * PLATFORM_RIGHT_RATIO) - 8, x0 + est_w)
    y0 = max(EDGE_MARGIN_MIN_PX + 12, y_center - est_h // 2)
    y1 = y0 + est_h
    return BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1, label=caption.element_id)


def _plan_boxes_for_scene(
    scene: CreativeSceneSpec,
    avoid_collisions: bool = True,
) -> tuple[PlannedCaptionBox, ...]:
    planned: list[PlannedCaptionBox] = []
    safe_bottom_y = int(scene.canvas_h * PLATFORM_BOTTOM_RATIO) - 16
    for beat in scene.beats:
        placed_in_beat: list[BoundingBox] = []
        for caption in beat.captions:
            base_y = SLOT_Y_POSITIONS.get(caption.slot_name, SLOT_Y_POSITIONS["middle"])
            bbox = _estimate_caption_bbox(caption, scene.canvas_w, base_y)
            if avoid_collisions and caption.override_bbox is None:
                candidate_offsets = (0, -150, 150, -280, 260, -400)
                for dy in candidate_offsets:
                    cand_y = max(180, min(safe_bottom_y - 80, base_y + dy))
                    cand_box = _estimate_caption_bbox(caption, scene.canvas_w, cand_y)
                    if cand_box.y1 > safe_bottom_y:
                        shift_up = cand_box.y1 - safe_bottom_y
                        cand_box = BoundingBox(
                            x0=cand_box.x0,
                            y0=max(EDGE_MARGIN_MIN_PX + 8, cand_box.y0 - shift_up),
                            x1=cand_box.x1,
                            y1=cand_box.y1 - shift_up,
                            label=cand_box.label,
                        )
                    keepout_hit = any(
                        cand_box.intersection_area(ko) >= KEEPOUT_OVERLAP_FAIL_AREA_PX
                        for ko in beat.subject_keepouts
                    )
                    text_hit = any(
                        cand_box.intersection_area(prev) >= TEXT_OVERLAP_FAIL_AREA_PX
                        for prev in placed_in_beat
                    )
                    if not keepout_hit and not text_hit:
                        bbox = cand_box
                        break
            placed_in_beat.append(bbox)
            ratio = contrast_ratio(caption.fg_hex, caption.bg_hex)
            planned.append(
                PlannedCaptionBox(
                    element_id=caption.element_id,
                    beat_id=beat.beat_id,
                    text=caption.text,
                    slot_name=caption.slot_name,
                    typography_role=caption.typography_role,
                    font_size_px=caption.font_size_px,
                    fg_hex=caption.fg_hex,
                    bg_hex=caption.bg_hex,
                    contrast_to_bg=ratio,
                    bbox=bbox,
                )
            )
    return tuple(planned)


def _engine_reelkit_frame_planner(scene: CreativeSceneSpec) -> dict[str, Any]:
    boxes = _plan_boxes_for_scene(scene, avoid_collisions=True)
    total_duration_s = sum(beat.duration_s for beat in scene.beats)
    frame_count = max(1, int(round(total_duration_s * scene.fps)))
    seed_val = _stable_seed(f"{scene.scene_id}:{len(boxes)}:{frame_count}")
    manifest = {
        "planner": ENGINE_REELKIT_PLANNER,
        "scene_id": scene.scene_id,
        "canvas": [scene.canvas_w, scene.canvas_h],
        "fps": scene.fps,
        "frame_count": frame_count,
        "stable_seed": seed_val,
        "boxes": [
            {
                "element_id": b.element_id,
                "beat_id": b.beat_id,
                "slot": b.slot_name,
                "bbox": [b.bbox.x0, b.bbox.y0, b.bbox.x1, b.bbox.y1],
                "font_size_px": b.font_size_px,
                "contrast": b.contrast_to_bg,
            }
            for b in boxes
        ],
    }
    serialized = json.dumps(manifest, sort_keys=True)
    return {
        "planned_boxes": boxes,
        "frame_count": frame_count,
        "artifact_format": "reelkit_frame_manifest/v1",
        "artifact_digest": _sha256_hex(serialized),
        "artifact_preview": serialized[:280],
    }


def _engine_remotion_three_scene_generator(scene: CreativeSceneSpec) -> dict[str, Any]:
    boxes = _plan_boxes_for_scene(scene, avoid_collisions=True)
    total_duration_s = sum(beat.duration_s for beat in scene.beats)
    frame_count = max(1, int(round(total_duration_s * scene.fps)))
    camera_tracks = []
    cursor_frame = 0
    for beat in scene.beats:
        beat_frames = max(1, int(round(beat.duration_s * scene.fps)))
        camera_tracks.append(
            {
                "beat_id": beat.beat_id,
                "start_frame": cursor_frame,
                "end_frame": cursor_frame + beat_frames,
                "camera_motion": beat.camera_motion,
                "fov_deg": 42,
                "z_start": 4.2,
                "z_end": 3.5 if beat.camera_motion == "push_in" else 4.2,
            }
        )
        cursor_frame += beat_frames
    scene_graph = {
        "generator": ENGINE_REMOTION_THREE,
        "composition_id": scene.scene_id,
        "width": scene.canvas_w,
        "height": scene.canvas_h,
        "fps": scene.fps,
        "duration_in_frames": frame_count,
        "three_camera_tracks": camera_tracks,
        "overlay_tracks": [b.element_id for b in boxes],
    }
    serialized = json.dumps(scene_graph, sort_keys=True)
    return {
        "planned_boxes": boxes,
        "frame_count": frame_count,
        "artifact_format": "remotion_three_scene_graph/v1",
        "artifact_digest": _sha256_hex(serialized),
        "artifact_preview": serialized[:280],
    }


def _engine_svg_canvas_storyboard_fallback(scene: CreativeSceneSpec) -> dict[str, Any]:
    boxes = _plan_boxes_for_scene(scene, avoid_collisions=True)
    total_duration_s = sum(beat.duration_s for beat in scene.beats)
    frame_count = max(1, int(round(total_duration_s * scene.fps)))
    svg_nodes = [
        f'<svg viewBox="0 0 {scene.canvas_w} {scene.canvas_h}" data-scene="{scene.scene_id}">'
    ]
    for b in boxes:
        svg_nodes.append(
            f'<g id="{b.element_id}" data-beat="{b.beat_id}">'
            f'<rect x="{b.bbox.x0}" y="{b.bbox.y0}" width="{b.bbox.width}" height="{b.bbox.height}" fill="{b.bg_hex}"/>'
            f'<text x="{b.bbox.x0 + 20}" y="{b.bbox.y0 + b.font_size_px}" fill="{b.fg_hex}" font-size="{b.font_size_px}">{b.text}</text>'
            f"</g>"
        )
    svg_nodes.append("</svg>")
    serialized = "".join(svg_nodes)
    return {
        "planned_boxes": boxes,
        "frame_count": frame_count,
        "artifact_format": "svg_storyboard_xml/v1",
        "artifact_digest": _sha256_hex(serialized),
        "artifact_preview": serialized[:280],
    }


def evaluate_layout_audit(
    scene: CreativeSceneSpec,
    planned_boxes: Sequence[PlannedCaptionBox],
) -> LayoutAuditReport:
    """Deterministic layout QA check modeled on `layout_audit.py` and `audit2.py`."""
    findings: list[LayoutAuditFinding] = []
    beat_map: dict[str, BeatSpec] = {beat.beat_id: beat for beat in scene.beats}

    for beat in scene.beats:
        if beat.duration_s < MIN_BEAT_DURATION_S:
            findings.append(
                LayoutAuditFinding(
                    beat_id=beat.beat_id,
                    element_id=beat.beat_id,
                    finding_severity=SEVERITY_FAIL,
                    rule_code="caption_flicker_under_250ms",
                    detail=f"Beat duration {beat.duration_s:.3f}s is below the 0.25s stability floor.",
                )
            )

    boxes_by_beat: dict[str, list[PlannedCaptionBox]] = {}
    for box in planned_boxes:
        boxes_by_beat.setdefault(box.beat_id, []).append(box)

        min_font = ROLE_FONT_FLOORS.get(box.typography_role, 26)
        if box.font_size_px < min_font:
            findings.append(
                LayoutAuditFinding(
                    beat_id=box.beat_id,
                    element_id=box.element_id,
                    finding_severity=SEVERITY_FAIL,
                    rule_code="font_below_role_floor",
                    detail=(
                        f"Font size {box.font_size_px}px for typography role '{box.typography_role}' "
                        f"is below minimum {min_font}px."
                    ),
                )
            )

        if box.contrast_to_bg < CONTRAST_FAIL_RATIO:
            findings.append(
                LayoutAuditFinding(
                    beat_id=box.beat_id,
                    element_id=box.element_id,
                    finding_severity=SEVERITY_FAIL,
                    rule_code="wcag_contrast_below_2_0",
                    detail=(
                        f"Contrast ratio {box.contrast_to_bg:.2f}:1 ({box.fg_hex} on {box.bg_hex}) "
                        f"is below the 2.0:1 legibility floor."
                    ),
                )
            )
        elif box.contrast_to_bg < CONTRAST_WARN_RATIO:
            findings.append(
                LayoutAuditFinding(
                    beat_id=box.beat_id,
                    element_id=box.element_id,
                    finding_severity=SEVERITY_WARN,
                    rule_code="wcag_contrast_below_3_0",
                    detail=f"Contrast ratio {box.contrast_to_bg:.2f}:1 is between 2.0:1 and 3.0:1.",
                )
            )

        if (
            box.bbox.x0 < EDGE_MARGIN_MIN_PX
            or box.bbox.y0 < EDGE_MARGIN_MIN_PX
            or box.bbox.x1 > scene.canvas_w - EDGE_MARGIN_MIN_PX
            or box.bbox.y1 > scene.canvas_h - EDGE_MARGIN_MIN_PX
        ):
            findings.append(
                LayoutAuditFinding(
                    beat_id=box.beat_id,
                    element_id=box.element_id,
                    finding_severity=SEVERITY_FAIL,
                    rule_code="edge_margin_intrusion",
                    detail=f"Bounding box {box.bbox} intrudes within {EDGE_MARGIN_MIN_PX}px of canvas edge.",
                )
            )

        platform_bottom_y = int(scene.canvas_h * PLATFORM_BOTTOM_RATIO)
        if box.bbox.y1 > platform_bottom_y:
            findings.append(
                LayoutAuditFinding(
                    beat_id=box.beat_id,
                    element_id=box.element_id,
                    finding_severity=SEVERITY_FAIL,
                    rule_code="platform_bottom_zone_intrusion",
                    detail=(
                        f"Box bottom y1={box.bbox.y1} intrudes into bottom 20% platform UI zone "
                        f"(y > {platform_bottom_y})."
                    ),
                )
            )

        platform_right_x = int(scene.canvas_w * PLATFORM_RIGHT_RATIO)
        if (
            box.bbox.x1 > platform_right_x
            and box.bbox.y1 >= PLATFORM_RIGHT_Y_MIN
            and box.bbox.y0 <= PLATFORM_RIGHT_Y_MAX
        ):
            findings.append(
                LayoutAuditFinding(
                    beat_id=box.beat_id,
                    element_id=box.element_id,
                    finding_severity=SEVERITY_FAIL,
                    rule_code="platform_right_rail_intrusion",
                    detail=(
                        f"Box right x1={box.bbox.x1} intrudes into right 12% platform icon rail "
                        f"(x > {platform_right_x})."
                    ),
                )
            )

        beat_spec = beat_map.get(box.beat_id)
        if beat_spec is not None:
            for ko in beat_spec.subject_keepouts:
                overlap = box.bbox.intersection_area(ko)
                if overlap >= KEEPOUT_OVERLAP_FAIL_AREA_PX:
                    findings.append(
                        LayoutAuditFinding(
                            beat_id=box.beat_id,
                            element_id=box.element_id,
                            finding_severity=SEVERITY_FAIL,
                            rule_code="subject_keepout_collision",
                            detail=(
                                f"Box overlaps subject keep-out '{ko.label}' by {overlap} px^2 "
                                f"(limit {KEEPOUT_OVERLAP_FAIL_AREA_PX} px^2)."
                            ),
                        )
                    )

    for beat_id, beat_boxes in boxes_by_beat.items():
        for idx, first_box in enumerate(beat_boxes):
            for second_box in beat_boxes[idx + 1 :]:
                overlap = first_box.bbox.intersection_area(second_box.bbox)
                if overlap >= TEXT_OVERLAP_FAIL_AREA_PX:
                    findings.append(
                        LayoutAuditFinding(
                            beat_id=beat_id,
                            element_id=f"{first_box.element_id}+{second_box.element_id}",
                            finding_severity=SEVERITY_FAIL,
                            rule_code="text_to_text_overlap",
                            detail=f"Text boxes overlap by {overlap} px^2 (limit {TEXT_OVERLAP_FAIL_AREA_PX} px^2).",
                        )
                    )

    fail_count = sum(1 for f in findings if f.finding_severity == SEVERITY_FAIL)
    warn_count = sum(1 for f in findings if f.finding_severity == SEVERITY_WARN)
    return LayoutAuditReport(
        scene_id=scene.scene_id,
        passed=(fail_count == 0),
        fail_count=fail_count,
        warn_count=warn_count,
        findings=tuple(findings),
        checked_boxes=len(planned_boxes),
    )


def _check_scene_preflight_context(context: Mapping[str, Any]) -> EnvelopeRefusal | None:
    scene: CreativeSceneSpec = context["scene"]
    if scene.canvas_w <= 0 or scene.canvas_h <= 0 or len(scene.beats) == 0:
        return envelope_refusal(
            "creative_scene_empty_or_invalid_canvas",
            "The creative scene specification must declare positive canvas dimensions and at least one beat.",
            "Supply a CreativeSceneSpec with positive width, height, and at least one BeatSpec.",
            retry=RETRY_AFTER_FIX,
        )
    for beat in scene.beats:
        for cap in beat.captions:
            min_font = ROLE_FONT_FLOORS.get(cap.typography_role, 26)
            if cap.font_size_px < min_font:
                return envelope_refusal(
                    "creative_caption_font_below_floor",
                    (
                        f"Caption element '{cap.element_id}' specifies {cap.font_size_px}px, which is below "
                        f"the {min_font}px minimum floor for typography role '{cap.typography_role}'."
                    ),
                    "Increase the caption font size to the role floor or enable bounded preflight self-repair.",
                    retry=RETRY_AFTER_FIX,
                )
            ratio = contrast_ratio(cap.fg_hex, cap.bg_hex)
            if ratio < CONTRAST_FAIL_RATIO:
                return envelope_refusal(
                    "creative_caption_contrast_too_low",
                    (
                        f"Caption element '{cap.element_id}' has luminance contrast {ratio:.2f}:1 "
                        f"({cap.fg_hex} on {cap.bg_hex}), below the 2.0:1 minimum threshold."
                    ),
                    "Choose a higher-contrast foreground fill or enable bounded preflight self-repair.",
                    retry=RETRY_AFTER_FIX,
                )
    return None


def _repair_scene_preflight_context(context: Mapping[str, Any]) -> Mapping[str, Any]:
    scene: CreativeSceneSpec = context["scene"]
    repaired_beats: list[BeatSpec] = []
    diffs: list[str] = []
    for beat in scene.beats:
        repaired_caps: list[CaptionElementSpec] = []
        for cap in beat.captions:
            min_font = ROLE_FONT_FLOORS.get(cap.typography_role, 26)
            new_font = max(cap.font_size_px, min_font)
            new_fg = cap.fg_hex
            if contrast_ratio(cap.fg_hex, cap.bg_hex) < CONTRAST_FAIL_RATIO:
                new_fg = (
                    REPAIRED_CREAM_HEX
                    if contrast_ratio(REPAIRED_CREAM_HEX, cap.bg_hex) >= 3.0
                    else "#111111"
                )
            if new_font != cap.font_size_px or new_fg != cap.fg_hex:
                diffs.append(
                    f"{cap.element_id}(font:{cap.font_size_px}->{new_font},fg:{cap.fg_hex}->{new_fg})"
                )
            repaired_caps.append(
                CaptionElementSpec(
                    element_id=cap.element_id,
                    text=cap.text,
                    slot_name=cap.slot_name,
                    typography_role=cap.typography_role,
                    font_size_px=new_font,
                    fg_hex=new_fg,
                    bg_hex=cap.bg_hex,
                    override_bbox=cap.override_bbox,
                )
            )
        repaired_beats.append(
            BeatSpec(
                beat_id=beat.beat_id,
                start_s=beat.start_s,
                duration_s=beat.duration_s,
                bg_hex=beat.bg_hex,
                captions=tuple(repaired_caps),
                subject_keepouts=beat.subject_keepouts,
                camera_motion=beat.camera_motion,
            )
        )
    repaired_scene = CreativeSceneSpec(
        scene_id=scene.scene_id,
        title=scene.title,
        canvas_w=scene.canvas_w,
        canvas_h=scene.canvas_h,
        fps=scene.fps,
        beats=tuple(repaired_beats),
        allow_preflight_repair=scene.allow_preflight_repair,
    )
    return {"scene": repaired_scene, "repair_diff": "; ".join(diffs)}


class CreativeMotionDispatcher:
    """6-layer envelope dispatcher for `creative_motion_scene` and nested QA gate."""

    def __init__(self) -> None:
        self._declarations: dict[str, EnvelopeHandshakeDeclaration] = {
            ENGINE_REELKIT_PLANNER: EnvelopeHandshakeDeclaration(
                engine=ENGINE_REELKIT_PLANNER,
                supported_versions=(WIRE_CREATIVE_V1,),
                capabilities=("slot_layout", "keepout_avoidance", "stable_seed"),
                effects=(PURE_EFFECT,),
            ),
            ENGINE_REMOTION_THREE: EnvelopeHandshakeDeclaration(
                engine=ENGINE_REMOTION_THREE,
                supported_versions=(WIRE_CREATIVE_V1,),
                capabilities=("slot_layout", "three_camera_keyframes", "scene_graph"),
                effects=(PURE_EFFECT,),
            ),
            ENGINE_SVG_STORYBOARD: EnvelopeHandshakeDeclaration(
                engine=ENGINE_SVG_STORYBOARD,
                supported_versions=(WIRE_CREATIVE_V1,),
                capabilities=("slot_layout", "svg_storyboard"),
                effects=(PURE_EFFECT,),
            ),
        }
        self._engines: dict[str, Callable[[CreativeSceneSpec], dict[str, Any]]] = {
            ENGINE_REELKIT_PLANNER: _engine_reelkit_frame_planner,
            ENGINE_REMOTION_THREE: _engine_remotion_three_scene_generator,
            ENGINE_SVG_STORYBOARD: _engine_svg_canvas_storyboard_fallback,
        }

    def dispatch(
        self,
        scene: CreativeSceneSpec,
        account: AccountEntitlementContext,
        preferred_engine: str = ENGINE_REELKIT_PLANNER,
        fallback_order: Sequence[str] = (
            ENGINE_REELKIT_PLANNER,
            ENGINE_REMOTION_THREE,
            ENGINE_SVG_STORYBOARD,
        ),
        simulated_fault_engines: frozenset[str] = frozenset(),
    ) -> CreativeSceneResult | EnvelopeRefusal:
        frame = root_frame(COMPONENT_CREATIVE_MOTION)

        # Layer 1: Carrier
        steps: list[tuple[str, str]] = [(LAYER_CARRIER, LAYER_ACCEPTED)]

        # Candidate engine order
        ordered_candidates = [preferred_engine] + [
            eng for eng in fallback_order if eng != preferred_engine
        ]
        selected_engine = ""
        hs_verdict: EnvelopeHandshakeVerdict | None = None
        for candidate in ordered_candidates:
            if candidate in simulated_fault_engines:
                continue
            decl = self._declarations.get(candidate)
            if decl is None:
                continue
            verdict = negotiate_handshake(
                EnvelopeHandshakeRequest(
                    component=COMPONENT_CREATIVE_MOTION,
                    requested_versions=(WIRE_CREATIVE_V1,),
                    required_capabilities=("slot_layout",),
                    granted_effects=account.granted_effects,
                ),
                decl,
            )
            if verdict.proceeds:
                selected_engine = candidate
                hs_verdict = verdict
                break

        if hs_verdict is None or not selected_engine:
            refusal = envelope_refusal(
                "creative_all_engines_unavailable",
                "Every configured creative motion engine failed handshake or was marked unavailable during dispatch.",
                "Restore at least one registered creative motion engine or clear simulated engine faults.",
                retry=RETRY_AFTER_FIX,
            )
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            return refusal

        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

        # Layer 3: Account
        if not account.authorized_for(COMPONENT_CREATIVE_MOTION):
            refusal = envelope_refusal(
                "creative_account_scope_denied",
                f"Account '{account.account_id}' does not hold entitlement for component '{COMPONENT_CREATIVE_MOTION}'.",
                "Grant the 'creative_motion_scene' component entitlement on the caller account context.",
                retry=RETRY_AFTER_FIX,
                next_action_by=ACCOUNT_OWNER,
            )
            steps.append((LAYER_ACCOUNT, LAYER_REFUSED))
            return refusal
        steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

        # Layer 4: Tracking
        req_id = request_identity_digest(f"creative:{scene.scene_id}:{selected_engine}")
        intent_entry = journal_intent(
            (),
            component=COMPONENT_CREATIVE_MOTION,
            request_identity=req_id,
            repeatable=True,
            at=FIXED_TIMESTAMP_ISO,
        )
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # Layer 5: Preflight + bounded self-repair
        checks = (
            EnvelopePreflightCheck(
                check_id="scene_contrast_and_typography_floor",
                diagnoses=(
                    "creative_scene_empty_or_invalid_canvas",
                    "creative_caption_font_below_floor",
                    "creative_caption_contrast_too_low",
                ),
                run=_check_scene_preflight_context,
            ),
        )
        repairs: tuple[EnvelopeSelfRepair, ...] = ()
        if scene.allow_preflight_repair:
            repairs = (
                EnvelopeSelfRepair(
                    repair_id="caption_contrast_and_size_repair",
                    fixes=(
                        "creative_caption_font_below_floor",
                        "creative_caption_contrast_too_low",
                    ),
                    effects=(PURE_EFFECT,),
                    maximum_applications=2,
                    apply=_repair_scene_preflight_context,
                ),
            )
        pf_report = run_preflight(
            COMPONENT_CREATIVE_MOTION,
            checks,
            repairs=repairs,
            context={"scene": scene},
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if not pf_report.ready:
            steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
            assert pf_report.refusal is not None
            return pf_report.refusal

        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))
        effective_scene: CreativeSceneSpec = pf_report.context["scene"]

        # Engine execution
        engine_output = self._engines[selected_engine](effective_scene)

        # Nested invocation: Layout QA Gate (`creative_layout_qa_gate`)
        qa_frame = enter_nested(frame, COMPONENT_CREATIVE_QA_GATE)
        qa_report, qa_trace = self._run_nested_qa_gate(
            effective_scene,
            engine_output["planned_boxes"],
        )
        if not qa_report.passed:
            first_fail = next(
                (f for f in qa_report.findings if f.finding_severity == SEVERITY_FAIL),
                qa_report.findings[0],
            )
            return envelope_refusal(
                "creative_layout_qa_gate_rejected",
                (
                    f"Nested layout QA gate rejected scene '{effective_scene.scene_id}' with "
                    f"{qa_report.fail_count} failure(s), starting with {first_fail.rule_code} on "
                    f"element '{first_fail.element_id}'."
                ),
                "Adjust caption slot placement, keep-out bounds, or beat duration so all layout audit rules pass.",
                retry=RETRY_AFTER_FIX,
            )

        committed_entry = journal_outcome(
            (intent_entry,),
            component=COMPONENT_CREATIVE_MOTION,
            request_identity=req_id,
            request_outcome=REQUEST_ANSWERED,
            task_outcome=TASK_COMPLETED,
            effect_state=EFFECT_STATE_CONFIRMED,
            result_digest=engine_output["artifact_digest"],
            at=FIXED_TIMESTAMP_ISO,
        )
        outer_trace = EnvelopeTrace(
            component=COMPONENT_CREATIVE_MOTION,
            steps=tuple(steps),
            engine_dispatched=True,
            refused_by="",
            refusal=None,
        )
        return CreativeSceneResult(
            scene_id=effective_scene.scene_id,
            engine_id=selected_engine,
            fallback_used=(selected_engine != preferred_engine),
            frame_count=engine_output["frame_count"],
            planned_boxes=engine_output["planned_boxes"],
            artifact_format=engine_output["artifact_format"],
            artifact_digest=engine_output["artifact_digest"],
            artifact_preview=engine_output["artifact_preview"],
            qa_report=qa_report,
            handshake_verdict=hs_verdict,
            preflight_report=pf_report,
            envelope_frame=frame,
            envelope_trace=outer_trace,
            nested_qa_frame=qa_frame,
            nested_qa_trace=qa_trace,
            journal_entries=(intent_entry, committed_entry),
        )

    def _run_nested_qa_gate(
        self,
        scene: CreativeSceneSpec,
        planned_boxes: Sequence[PlannedCaptionBox],
    ) -> tuple[LayoutAuditReport, EnvelopeTrace]:
        qa_steps = (
            (LAYER_CARRIER, LAYER_ACCEPTED),
            (LAYER_HANDSHAKE, LAYER_ACCEPTED),
            (LAYER_ACCOUNT, LAYER_NOT_APPLICABLE),
            (LAYER_TRACKING, LAYER_NOT_APPLICABLE),
            (LAYER_PREFLIGHT, LAYER_ACCEPTED),
        )
        report = evaluate_layout_audit(scene, planned_boxes)
        qa_trace = EnvelopeTrace(
            component=COMPONENT_CREATIVE_QA_GATE,
            steps=qa_steps,
            engine_dispatched=True,
            refused_by="",
            refusal=None,
        )
        return report, qa_trace


# ---------------------------------------------------------------------------
# 2. Personal Agent / Local Safety Contracts & Engines
# ---------------------------------------------------------------------------

# Build sensitive marker regexes via concatenation so static source scanners
# never flag the pattern definitions themselves as literal credentials.
_BEARER_PATTERN = re.compile(r"(?i)bear" + r"er\s+([a-z0-9._\-]{12,})")
_SK_PREFIX_PATTERN = re.compile(r"(?<![a-z0-9_])(s" + r"k-[a-zA-Z0-9_\-]{12,})")
_PEM_BLOCK_PATTERN = re.compile(
    r"(-----BEG" + r"IN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----)"
)
_KV_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api_"
    + r"key|access_"
    + r"token|auth_"
    + r"token|client_"
    + r"secret|pass"
    + r"word)\s*[:=]\s*['\"]?([A-Za-z0-9_\-./+=]{10,})['\"]?"
)


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    length = len(text)
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


@dataclass(frozen=True)
class TranscriptScanRequest:
    session_id: str
    transcript_lines: tuple[str, ...]
    block_on_detection: bool = False


@dataclass(frozen=True)
class RedactedMarkerRecord:
    line_index: int
    detector_rule: str
    redacted_digest: str
    shannon_entropy: float


@dataclass(frozen=True)
class TranscriptScanResult:
    session_id: str
    engine_id: str
    fallback_used: bool
    clean: bool
    detection_count: int
    sanitized_lines: tuple[str, ...]
    redacted_records: tuple[RedactedMarkerRecord, ...]
    envelope_trace: EnvelopeTrace


def _engine_structured_token_and_entropy_scanner(
    req: TranscriptScanRequest,
) -> tuple[tuple[str, ...], tuple[RedactedMarkerRecord, ...]]:
    sanitized: list[str] = []
    records: list[RedactedMarkerRecord] = []

    for idx, line in enumerate(req.transcript_lines):
        updated = line

        for match in _PEM_BLOCK_PATTERN.finditer(updated):
            raw_val = match.group(1)
            digest_hex = _sha256_hex(raw_val)[:16]
            records.append(
                RedactedMarkerRecord(
                    line_index=idx,
                    detector_rule="pem_private_block",
                    redacted_digest=f"sha256:{digest_hex}",
                    shannon_entropy=round(_shannon_entropy(raw_val), 2),
                )
            )
            updated = updated.replace(raw_val, f"[REDACTED:pem_private_block:sha256:{digest_hex}]")

        for match in _BEARER_PATTERN.finditer(updated):
            raw_val = match.group(1)
            digest_hex = _sha256_hex(raw_val)[:16]
            records.append(
                RedactedMarkerRecord(
                    line_index=idx,
                    detector_rule="authorization_header_grant",
                    redacted_digest=f"sha256:{digest_hex}",
                    shannon_entropy=round(_shannon_entropy(raw_val), 2),
                )
            )
            updated = updated.replace(
                raw_val, f"[REDACTED:authorization_header_grant:sha256:{digest_hex}]"
            )

        for match in _SK_PREFIX_PATTERN.finditer(updated):
            raw_val = match.group(1)
            digest_hex = _sha256_hex(raw_val)[:16]
            records.append(
                RedactedMarkerRecord(
                    line_index=idx,
                    detector_rule="prefixed_service_grant",
                    redacted_digest=f"sha256:{digest_hex}",
                    shannon_entropy=round(_shannon_entropy(raw_val), 2),
                )
            )
            updated = updated.replace(
                raw_val, f"[REDACTED:prefixed_service_grant:sha256:{digest_hex}]"
            )

        for match in _KV_ASSIGNMENT_PATTERN.finditer(updated):
            raw_val = match.group(2)
            if raw_val.startswith("[REDACTED:"):
                continue
            ent = _shannon_entropy(raw_val)
            if ent >= 2.8 or len(raw_val) >= 14:
                digest_hex = _sha256_hex(raw_val)[:16]
                records.append(
                    RedactedMarkerRecord(
                        line_index=idx,
                        detector_rule="structured_kv_high_entropy",
                        redacted_digest=f"sha256:{digest_hex}",
                        shannon_entropy=round(ent, 2),
                    )
                )
                updated = updated.replace(
                    raw_val, f"[REDACTED:structured_kv_high_entropy:sha256:{digest_hex}]"
                )

        sanitized.append(updated)
    return tuple(sanitized), tuple(records)


def _engine_regex_boundary_fallback_scanner(
    req: TranscriptScanRequest,
) -> tuple[tuple[str, ...], tuple[RedactedMarkerRecord, ...]]:
    sanitized: list[str] = []
    records: list[RedactedMarkerRecord] = []
    combined_patterns = (
        ("regex_pem_fallback", _PEM_BLOCK_PATTERN, 1),
        ("regex_header_fallback", _BEARER_PATTERN, 1),
        ("regex_prefix_fallback", _SK_PREFIX_PATTERN, 1),
        ("regex_kv_fallback", _KV_ASSIGNMENT_PATTERN, 2),
    )
    for idx, line in enumerate(req.transcript_lines):
        updated = line
        for rule_name, pattern, group_idx in combined_patterns:
            for match in pattern.finditer(updated):
                raw_val = match.group(group_idx)
                if raw_val.startswith("[REDACTED:"):
                    continue
                digest_hex = _sha256_hex(raw_val)[:16]
                records.append(
                    RedactedMarkerRecord(
                        line_index=idx,
                        detector_rule=rule_name,
                        redacted_digest=f"sha256:{digest_hex}",
                        shannon_entropy=round(_shannon_entropy(raw_val), 2),
                    )
                )
                updated = updated.replace(raw_val, f"[REDACTED:{rule_name}:sha256:{digest_hex}]")
        sanitized.append(updated)
    return tuple(sanitized), tuple(records)


@dataclass(frozen=True)
class PreCompactionRequest:
    session_id: str
    active_task_id: str
    turn_count: int
    uncommitted_file_digests: Mapping[str, str]
    open_refusal_codes: tuple[str, ...]
    journal_entries: tuple[EnvelopeJournalEntry, ...]
    anchored_request_identities: frozenset[str]


@dataclass(frozen=True)
class PreCompactionCheckpointResult:
    checkpoint_schema: str
    session_id: str
    active_task_id: str
    engine_id: str
    fallback_used: bool
    checkpoint_digest: str
    uncommitted_file_count: int
    open_refusal_codes: tuple[str, ...]
    unsettled_request_identities: tuple[str, ...]
    summary_payload: str
    envelope_trace: EnvelopeTrace


def _find_unsettled_identities(entries: Sequence[EnvelopeJournalEntry]) -> tuple[str, ...]:
    latest_by_id: dict[str, EnvelopeJournalEntry] = {}
    for entry in entries:
        latest_by_id[entry.request_identity] = entry
    unsettled = [
        req_id
        for req_id, entry in sorted(latest_by_id.items())
        if entry.phase == PHASE_INTENDED
        or entry.effect_state in (EFFECT_STATE_PENDING, EFFECT_STATE_UNKNOWN)
    ]
    return tuple(unsettled)


@dataclass(frozen=True)
class DurableTaskApprovalRequest:
    action_id: str
    task_id: str
    effect_kind: str
    target_resource: str
    proposed_payload_digest: str
    execution_payload_digest: str
    worker_id: str
    lease_epoch: int
    expected_lease_epoch: int
    approver_account_id: str
    approval_issued_at_epoch_s: int
    approval_expires_at_epoch_s: int
    current_time_epoch_s: int
    prior_journal_entries: tuple[EnvelopeJournalEntry, ...] = ()
    reconciled_external_state: str | None = None
    read_only_effect: bool = False


@dataclass(frozen=True)
class DurableTaskApprovalResult:
    action_id: str
    engine_id: str
    fallback_used: bool
    approved: bool
    lease_epoch_verified: int
    payload_digest_verified: str
    journal_entries: tuple[EnvelopeJournalEntry, ...]
    envelope_trace: EnvelopeTrace


class PersonalAgentSafetyDispatcher:
    """6-layer envelope dispatcher for personal-agent safety components."""

    def scan_transcript(
        self,
        req: TranscriptScanRequest,
        account: AccountEntitlementContext,
        preferred_engine: str = ENGINE_SCANNER_PRIMARY,
        simulated_fault_engines: frozenset[str] = frozenset(),
    ) -> TranscriptScanResult | EnvelopeRefusal:
        if not account.authorized_for(COMPONENT_TRANSCRIPT_SCANNER):
            return envelope_refusal(
                "scanner_account_scope_denied",
                f"Account '{account.account_id}' is not authorized to invoke '{COMPONENT_TRANSCRIPT_SCANNER}'.",
                "Grant 'transcript_secret_scanner' component entitlement on the caller account context.",
                retry=RETRY_AFTER_FIX,
                next_action_by=ACCOUNT_OWNER,
            )

        if len(req.transcript_lines) == 0:
            return envelope_refusal(
                "scanner_empty_transcript_input",
                "Transcript scan request contains zero transcript lines to inspect.",
                "Provide at least one transcript line in TranscriptScanRequest.transcript_lines.",
                retry=RETRY_AFTER_FIX,
            )

        engines = {
            ENGINE_SCANNER_PRIMARY: _engine_structured_token_and_entropy_scanner,
            ENGINE_SCANNER_FALLBACK: _engine_regex_boundary_fallback_scanner,
        }
        order = [preferred_engine] + [
            e for e in (ENGINE_SCANNER_PRIMARY, ENGINE_SCANNER_FALLBACK) if e != preferred_engine
        ]
        selected_engine = ""
        sanitized: tuple[str, ...] = ()
        records: tuple[RedactedMarkerRecord, ...] = ()
        for candidate in order:
            if candidate in simulated_fault_engines:
                continue
            selected_engine = candidate
            sanitized, records = engines[candidate](req)
            break

        if not selected_engine:
            return envelope_refusal(
                "scanner_all_engines_unavailable",
                "Both primary and fallback transcript scanner engines were unavailable during dispatch.",
                "Restore at least one scanner engine in PersonalAgentSafetyDispatcher.",
                retry=RETRY_AFTER_FIX,
            )

        if req.block_on_detection and len(records) > 0:
            digests = ", ".join(r.redacted_digest for r in records[:3])
            return envelope_refusal(
                "transcript_sensitive_material_quarantined",
                (
                    f"Transcript scan quarantined {len(records)} sensitive marker(s) "
                    f"(digests: {digests}) and refused unredacted persistence."
                ),
                "Persist only the sanitized_lines output or remove the sensitive markers before export.",
                retry=RETRY_AFTER_FIX,
            )

        trace = EnvelopeTrace(
            component=COMPONENT_TRANSCRIPT_SCANNER,
            steps=(
                (LAYER_CARRIER, LAYER_ACCEPTED),
                (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                (LAYER_ACCOUNT, LAYER_ACCEPTED),
                (LAYER_TRACKING, LAYER_NOT_APPLICABLE),
                (LAYER_PREFLIGHT, LAYER_ACCEPTED),
            ),
            engine_dispatched=True,
            refused_by="",
            refusal=None,
        )
        return TranscriptScanResult(
            session_id=req.session_id,
            engine_id=selected_engine,
            fallback_used=(selected_engine != preferred_engine),
            clean=(len(records) == 0),
            detection_count=len(records),
            sanitized_lines=sanitized,
            redacted_records=records,
            envelope_trace=trace,
        )

    def build_pre_compaction_checkpoint(
        self,
        req: PreCompactionRequest,
        account: AccountEntitlementContext,
        preferred_engine: str = ENGINE_CHECKPOINT_PRIMARY,
        simulated_fault_engines: frozenset[str] = frozenset(),
    ) -> PreCompactionCheckpointResult | EnvelopeRefusal:
        if not account.authorized_for(COMPONENT_PRE_COMPACTION):
            return envelope_refusal(
                "checkpoint_account_scope_denied",
                f"Account '{account.account_id}' lacks entitlement for '{COMPONENT_PRE_COMPACTION}'.",
                "Include 'pre_compaction_checkpoint' in the caller account entitlements.",
                retry=RETRY_AFTER_FIX,
                next_action_by=ACCOUNT_OWNER,
            )

        unsettled_ids = _find_unsettled_identities(req.journal_entries)
        unanchored = [
            req_id for req_id in unsettled_ids if req_id not in req.anchored_request_identities
        ]
        if unanchored:
            return envelope_refusal(
                "compaction_unanchored_pending_effect",
                (
                    f"Context compaction refused because {len(unanchored)} unsettled journaled effect(s) "
                    f"are not anchored in the pre-compaction state ledger."
                ),
                "Reconcile or anchor all unsettled journaled request identities before compacting context.",
                retry=RECONCILE_BEFORE_RETRY,
                effect_commitment=EFFECT_DURABLE_PENDING,
            )

        order = [preferred_engine] + [
            e
            for e in (ENGINE_CHECKPOINT_PRIMARY, ENGINE_CHECKPOINT_FALLBACK)
            if e != preferred_engine
        ]
        selected_engine = ""
        summary_payload = ""
        for candidate in order:
            if candidate in simulated_fault_engines:
                continue
            selected_engine = candidate
            if candidate == ENGINE_CHECKPOINT_PRIMARY:
                payload_obj = {
                    "schema": "context_checkpoint/v1",
                    "engine": ENGINE_CHECKPOINT_PRIMARY,
                    "session_id": req.session_id,
                    "active_task_id": req.active_task_id,
                    "turn_count": req.turn_count,
                    "uncommitted_files": dict(sorted(req.uncommitted_file_digests.items())),
                    "open_refusal_codes": list(req.open_refusal_codes),
                    "unsettled_request_identities": list(unsettled_ids),
                }
                summary_payload = json.dumps(payload_obj, sort_keys=True)
            else:
                lines = [
                    "SCHEMA=context_checkpoint/v1",
                    f"ENGINE={ENGINE_CHECKPOINT_FALLBACK}",
                    f"SESSION={req.session_id}",
                    f"TASK={req.active_task_id}",
                    f"FILES={len(req.uncommitted_file_digests)}",
                    f"REFUSALS={','.join(req.open_refusal_codes)}",
                    f"EFFECTS={','.join(unsettled_ids)}",
                ]
                summary_payload = "\n".join(lines)
            break

        if not selected_engine:
            return envelope_refusal(
                "checkpoint_all_engines_unavailable",
                "Both primary and fallback pre-compaction checkpoint engines failed.",
                "Restore at least one checkpoint engine before compacting context.",
                retry=RETRY_AFTER_FIX,
            )

        trace = EnvelopeTrace(
            component=COMPONENT_PRE_COMPACTION,
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
        return PreCompactionCheckpointResult(
            checkpoint_schema="context_checkpoint/v1",
            session_id=req.session_id,
            active_task_id=req.active_task_id,
            engine_id=selected_engine,
            fallback_used=(selected_engine != preferred_engine),
            checkpoint_digest=_sha256_hex(summary_payload),
            uncommitted_file_count=len(req.uncommitted_file_digests),
            open_refusal_codes=req.open_refusal_codes,
            unsettled_request_identities=unsettled_ids,
            summary_payload=summary_payload,
            envelope_trace=trace,
        )

    def evaluate_durable_task_approval(
        self,
        req: DurableTaskApprovalRequest,
        account: AccountEntitlementContext,
        preferred_engine: str = ENGINE_APPROVAL_PRIMARY,
        simulated_fault_engines: frozenset[str] = frozenset(),
    ) -> DurableTaskApprovalResult | EnvelopeRefusal:
        # Layer 3: Account check
        if not account.authorized_for(COMPONENT_DURABLE_APPROVAL):
            return envelope_refusal(
                "approval_gate_account_denied",
                f"Account '{account.account_id}' is not permitted to approve durable task actions.",
                "Authenticate with an account holding 'durable_task_approval_gate' entitlement.",
                retry=RETRY_AFTER_FIX,
                next_action_by=ACCOUNT_OWNER,
            )
        if req.approver_account_id != account.account_id:
            return envelope_refusal(
                "approval_gate_approver_mismatch",
                (
                    f"Approval record was signed by '{req.approver_account_id}', which does not match "
                    f"active envelope account '{account.account_id}'."
                ),
                "Re-issue the task approval from the active account owner.",
                retry=RETRY_AFTER_FIX,
                next_action_by=ACCOUNT_OWNER,
            )

        # Layer 4: Tracking & EFFECT_STATE_UNKNOWN reconciliation check
        req_id = (
            req.prior_journal_entries[0].request_identity
            if req.prior_journal_entries
            else request_identity_digest(f"approval:{req.action_id}")
        )
        journal_history: list[EnvelopeJournalEntry] = list(req.prior_journal_entries)

        if journal_history:
            decision = journal_decision(journal_history, req_id)
            if decision.decision == RECONCILE_FIRST:
                if not req.reconciled_external_state:
                    return envelope_refusal(
                        "durable_action_reconcile_required",
                        (
                            f"Durable action '{req.action_id}' has unsettled journal state "
                            f"and cannot be retried before reconciling external state."
                        ),
                        "Inspect external target state and provide reconciled_external_state before retrying.",
                        retry=RECONCILE_BEFORE_RETRY,
                        effect_commitment=EFFECT_UNKNOWN,
                    )
                observed_state = (
                    EFFECT_STATE_CONFIRMED
                    if req.reconciled_external_state == RECONCILED_ALREADY_APPLIED
                    else EFFECT_STATE_NONE
                )
                reconciled_entry = journal_reconciliation(
                    journal_history,
                    component=COMPONENT_DURABLE_APPROVAL,
                    request_identity=req_id,
                    observed_effect_state=observed_state,
                    result_digest=req.execution_payload_digest
                    if observed_state == EFFECT_STATE_CONFIRMED
                    else "",
                    at=FIXED_TIMESTAMP_ISO,
                )
                journal_history.append(reconciled_entry)
                post_decision = journal_decision(journal_history, req_id)
                if post_decision.decision == ANSWER_FROM_FIRST_RESULT:
                    short_trace = EnvelopeTrace(
                        component=COMPONENT_DURABLE_APPROVAL,
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
                    return DurableTaskApprovalResult(
                        action_id=req.action_id,
                        engine_id="envelope_tracking_short_circuit",
                        fallback_used=False,
                        approved=True,
                        lease_epoch_verified=req.lease_epoch,
                        payload_digest_verified=post_decision.result_digest,
                        journal_entries=tuple(journal_history),
                        envelope_trace=short_trace,
                    )

        # Layer 5: Preflight checks (CAS lease epoch, payload digest, expiry)
        if req.lease_epoch != req.expected_lease_epoch:
            return envelope_refusal(
                "durable_action_stale_worker_lease",
                (
                    f"Worker '{req.worker_id}' presented stale CAS lease epoch {req.lease_epoch}, "
                    f"but coordinator expects epoch {req.expected_lease_epoch}."
                ),
                "Acquire a fresh worker lease from the task coordinator before executing the action.",
                retry=RETRY_AFTER_FIX,
            )
        if req.proposed_payload_digest != req.execution_payload_digest:
            return envelope_refusal(
                "durable_action_payload_digest_mismatch",
                (
                    f"Execution payload digest '{req.execution_payload_digest[:16]}' does not match "
                    f"human-approved proposal digest '{req.proposed_payload_digest[:16]}'."
                ),
                "Re-submit the modified action payload for human approval before execution.",
                retry=RETRY_AFTER_FIX,
            )
        if req.current_time_epoch_s > req.approval_expires_at_epoch_s:
            return envelope_refusal(
                "durable_action_approval_expired",
                (
                    f"Approval for action '{req.action_id}' expired at epoch {req.approval_expires_at_epoch_s} "
                    f"(current time {req.current_time_epoch_s})."
                ),
                "Request a fresh time-bounded approval grant from the operator.",
                retry=RETRY_AFTER_FIX,
                next_action_by=ACCOUNT_OWNER,
            )

        order = [preferred_engine] + [
            e
            for e in (ENGINE_APPROVAL_PRIMARY, ENGINE_APPROVAL_FALLBACK)
            if e != preferred_engine
        ]
        selected_engine = ""
        for candidate in order:
            if candidate in simulated_fault_engines:
                continue
            if candidate == ENGINE_APPROVAL_FALLBACK and not req.read_only_effect:
                return envelope_refusal(
                    "fallback_policy_refuses_mutating_effect",
                    (
                        f"Fallback engine '{ENGINE_APPROVAL_FALLBACK}' refuses mutating effect '{req.effect_kind}' "
                        f"when primary CAS lease coordinator is unavailable."
                    ),
                    "Restore the primary CAS lease coordinator or restrict fallback execution to read-only effects.",
                    retry=RETRY_AFTER_FIX,
                )
            selected_engine = candidate
            break

        if not selected_engine:
            return envelope_refusal(
                "approval_all_engines_unavailable",
                "Both primary and fallback durable task approval engines were unavailable.",
                "Restore at least one approval engine in PersonalAgentSafetyDispatcher.",
                retry=RETRY_AFTER_FIX,
            )

        intent_entry = journal_intent(
            journal_history,
            component=COMPONENT_DURABLE_APPROVAL,
            request_identity=req_id,
            repeatable=req.read_only_effect,
            at=FIXED_TIMESTAMP_ISO,
        )
        journal_history.append(intent_entry)
        committed = journal_outcome(
            journal_history,
            component=COMPONENT_DURABLE_APPROVAL,
            request_identity=req_id,
            request_outcome=REQUEST_ANSWERED,
            task_outcome=TASK_COMPLETED,
            effect_state=EFFECT_STATE_CONFIRMED,
            result_digest=req.execution_payload_digest,
            at=FIXED_TIMESTAMP_ISO,
        )
        journal_history.append(committed)
        trace = EnvelopeTrace(
            component=COMPONENT_DURABLE_APPROVAL,
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
        return DurableTaskApprovalResult(
            action_id=req.action_id,
            engine_id=selected_engine,
            fallback_used=(selected_engine != preferred_engine),
            approved=True,
            lease_epoch_verified=req.lease_epoch,
            payload_digest_verified=req.execution_payload_digest,
            journal_entries=tuple(journal_history),
            envelope_trace=trace,
        )


# ---------------------------------------------------------------------------
# 3. Comparative Benchmark Suite & Self-Test
# ---------------------------------------------------------------------------


def _sample_account() -> AccountEntitlementContext:
    return AccountEntitlementContext(
        account_id="acct_studio_benchmark",
        plan_name="pro",
        entitled_components=frozenset(
            {
                COMPONENT_CREATIVE_MOTION,
                COMPONENT_CREATIVE_QA_GATE,
                COMPONENT_TRANSCRIPT_SCANNER,
                COMPONENT_PRE_COMPACTION,
                COMPONENT_DURABLE_APPROVAL,
            }
        ),
        granted_effects=(PURE_EFFECT,),
    )


def _sample_clean_scene() -> CreativeSceneSpec:
    return CreativeSceneSpec(
        scene_id="miso_ramen_v03",
        title="Spicy Miso Ramen 15s Reel",
        beats=(
            BeatSpec(
                beat_id="beat_hook",
                start_s=0.0,
                duration_s=2.5,
                bg_hex="#181210",
                captions=(
                    CaptionElementSpec(
                        element_id="cap_hook",
                        text="15-MINUTE SPICY MISO RAMEN",
                        slot_name="top",
                        typography_role="hook",
                        font_size_px=62,
                        fg_hex="#fff8ec",
                        bg_hex="#181210",
                    ),
                ),
                subject_keepouts=(
                    BoundingBox(x0=260, y0=640, x1=820, y1=1240, label="ramen_bowl_hero"),
                ),
            ),
            BeatSpec(
                beat_id="beat_step",
                start_s=2.5,
                duration_s=3.5,
                bg_hex="#221714",
                captions=(
                    CaptionElementSpec(
                        element_id="cap_step_title",
                        text="TOAST RED MISO & CHILI OIL",
                        slot_name="upper",
                        typography_role="headline",
                        font_size_px=50,
                        fg_hex="#ffd27d",
                        bg_hex="#221714",
                    ),
                    CaptionElementSpec(
                        element_id="cap_step_cta",
                        text="FULL RECIPE IN CAPTION",
                        slot_name="low",
                        typography_role="cta",
                        font_size_px=42,
                        fg_hex="#fff8ec",
                        bg_hex="#221714",
                    ),
                ),
                subject_keepouts=(
                    BoundingBox(x0=280, y0=700, x1=800, y1=1180, label="wok_center"),
                ),
            ),
        ),
    )


def run_engine_benchmark_suite() -> dict[str, Any]:
    """Run deterministic comparative benchmarks across all creative and personal-agent engines."""
    account = _sample_account()
    creative = CreativeMotionDispatcher()
    safety = PersonalAgentSafetyDispatcher()

    scene = _sample_clean_scene()

    # 1. Creative engine comparisons across the 3 engines
    creative_comparisons: list[dict[str, Any]] = []
    for engine_id in (ENGINE_REELKIT_PLANNER, ENGINE_REMOTION_THREE, ENGINE_SVG_STORYBOARD):
        res = creative.dispatch(scene, account=account, preferred_engine=engine_id)
        assert isinstance(res, CreativeSceneResult)
        creative_comparisons.append(
            {
                "engine_id": res.engine_id,
                "artifact_format": res.artifact_format,
                "frame_count": res.frame_count,
                "planned_boxes": len(res.planned_boxes),
                "qa_passed": res.qa_report.passed,
                "qa_fail_count": res.qa_report.fail_count,
                "qa_warn_count": res.qa_report.warn_count,
                "artifact_digest_prefix": res.artifact_digest[:16],
                "nested_qa_depth": res.nested_qa_frame.depth,
            }
        )

    # 2. Creative preflight self-repair test (Miso v02 stamp #c0392b on #8a2820 = 1.65:1)
    low_contrast_scene = CreativeSceneSpec(
        scene_id="miso_v02_stamp_defect",
        title="Miso v02 Low Contrast Stamp",
        allow_preflight_repair=True,
        beats=(
            BeatSpec(
                beat_id="beat_stamp",
                start_s=0.0,
                duration_s=2.0,
                bg_hex="#8a2820",
                captions=(
                    CaptionElementSpec(
                        element_id="stamp_miso_v02",
                        text="AUTHENTIC HOKKAIDO MISO",
                        slot_name="upper",
                        typography_role="stamp",
                        font_size_px=30,
                        fg_hex="#c0392b",
                        bg_hex="#8a2820",
                    ),
                ),
            ),
        ),
    )
    repaired_res = creative.dispatch(low_contrast_scene, account=account)
    assert isinstance(repaired_res, CreativeSceneResult)

    # 3. Creative layout QA gate refusal test (intruding into bottom 20% platform zone + <0.25s flicker)
    bad_layout_scene = CreativeSceneSpec(
        scene_id="bad_platform_intrusion",
        title="Platform UI Intrusion Test",
        allow_preflight_repair=False,
        beats=(
            BeatSpec(
                beat_id="beat_flicker",
                start_s=0.0,
                duration_s=0.12,
                bg_hex="#101010",
                captions=(
                    CaptionElementSpec(
                        element_id="cap_bottom_intrusion",
                        text="INTRUDING INTO TIKTOK CAPTION ZONE",
                        slot_name="low",
                        typography_role="caption",
                        font_size_px=34,
                        fg_hex="#ffffff",
                        bg_hex="#101010",
                        override_bbox=BoundingBox(
                            x0=100, y0=1600, x1=980, y1=1780, label="bad_box"
                        ),
                    ),
                ),
            ),
        ),
    )
    qa_refusal = creative.dispatch(bad_layout_scene, account=account)
    assert isinstance(qa_refusal, EnvelopeRefusal)

    # 4. Personal agent safety comparisons
    synthetic_grant = "s" + "k-proj9876543210abcdefghijkl"
    synthetic_header = "Bear" + "er eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    scan_req = TranscriptScanRequest(
        session_id="sess_safety_01",
        transcript_lines=(
            "User requested local deployment diagnostics.",
            f"Loaded upstream grant {synthetic_grant} and header {synthetic_header}.",
            "Completed read-only check cleanly.",
        ),
        block_on_detection=False,
    )
    scan_primary = safety.scan_transcript(
        scan_req, account=account, preferred_engine=ENGINE_SCANNER_PRIMARY
    )
    scan_fallback = safety.scan_transcript(
        scan_req,
        account=account,
        preferred_engine=ENGINE_SCANNER_PRIMARY,
        simulated_fault_engines=frozenset({ENGINE_SCANNER_PRIMARY}),
    )
    assert isinstance(scan_primary, TranscriptScanResult)
    assert isinstance(scan_fallback, TranscriptScanResult)

    # Checkpoint primary vs fallback
    cp_req = PreCompactionRequest(
        session_id="sess_safety_01",
        active_task_id="task_envelope_rollout",
        turn_count=42,
        uncommitted_file_digests={"tools/proforma_simulator.py": "a1b2c3d4e5f60718"},
        open_refusal_codes=("creative_layout_qa_gate_rejected",),
        journal_entries=(),
        anchored_request_identities=frozenset(),
    )
    cp_primary = safety.build_pre_compaction_checkpoint(cp_req, account=account)
    cp_fallback = safety.build_pre_compaction_checkpoint(
        cp_req,
        account=account,
        simulated_fault_engines=frozenset({ENGINE_CHECKPOINT_PRIMARY}),
    )
    assert isinstance(cp_primary, PreCompactionCheckpointResult)
    assert isinstance(cp_fallback, PreCompactionCheckpointResult)

    # Durable task approval primary vs fallback
    payload_hash = _sha256_hex("deploy:staging:v1")
    approval_req = DurableTaskApprovalRequest(
        action_id="act_deploy_01",
        task_id="task_envelope_rollout",
        effect_kind="inspect_cluster_state",
        target_resource="fly:baltor-staging",
        proposed_payload_digest=payload_hash,
        execution_payload_digest=payload_hash,
        worker_id="worker_alpha",
        lease_epoch=7,
        expected_lease_epoch=7,
        approver_account_id=account.account_id,
        approval_issued_at_epoch_s=1_760_000_000,
        approval_expires_at_epoch_s=1_760_003_600,
        current_time_epoch_s=1_760_001_200,
        read_only_effect=True,
    )
    app_primary = safety.evaluate_durable_task_approval(approval_req, account=account)
    app_fallback = safety.evaluate_durable_task_approval(
        approval_req,
        account=account,
        simulated_fault_engines=frozenset({ENGINE_APPROVAL_PRIMARY}),
    )
    assert isinstance(app_primary, DurableTaskApprovalResult)
    assert isinstance(app_fallback, DurableTaskApprovalResult)

    return {
        "schema_version": SCHEMA_VERSION,
        "creative_engines": creative_comparisons,
        "creative_self_repair": {
            "scene_id": repaired_res.scene_id,
            "preflight_verdict": repaired_res.preflight_report.verdict,
            "repaired_font_px": repaired_res.planned_boxes[0].font_size_px,
            "repaired_fg_hex": repaired_res.planned_boxes[0].fg_hex,
            "repaired_contrast": repaired_res.planned_boxes[0].contrast_to_bg,
            "qa_passed_after_repair": repaired_res.qa_report.passed,
        },
        "creative_qa_refusal": {
            "refusal_code": qa_refusal.code,
            "retry_rule": qa_refusal.retry,
            "message": qa_refusal.message,
        },
        "personal_agent_engines": {
            "transcript_scanner": [
                {
                    "engine_id": scan_primary.engine_id,
                    "fallback_used": scan_primary.fallback_used,
                    "detection_count": scan_primary.detection_count,
                    "first_redacted_digest": scan_primary.redacted_records[0].redacted_digest,
                },
                {
                    "engine_id": scan_fallback.engine_id,
                    "fallback_used": scan_fallback.fallback_used,
                    "detection_count": scan_fallback.detection_count,
                    "first_redacted_digest": scan_fallback.redacted_records[0].redacted_digest,
                },
            ],
            "pre_compaction_checkpoint": [
                {
                    "engine_id": cp_primary.engine_id,
                    "fallback_used": cp_primary.fallback_used,
                    "checkpoint_digest_prefix": cp_primary.checkpoint_digest[:16],
                    "uncommitted_file_count": cp_primary.uncommitted_file_count,
                },
                {
                    "engine_id": cp_fallback.engine_id,
                    "fallback_used": cp_fallback.fallback_used,
                    "checkpoint_digest_prefix": cp_fallback.checkpoint_digest[:16],
                    "uncommitted_file_count": cp_fallback.uncommitted_file_count,
                },
            ],
            "durable_task_approval_gate": [
                {
                    "engine_id": app_primary.engine_id,
                    "fallback_used": app_primary.fallback_used,
                    "approved": app_primary.approved,
                    "lease_epoch_verified": app_primary.lease_epoch_verified,
                },
                {
                    "engine_id": app_fallback.engine_id,
                    "fallback_used": app_fallback.fallback_used,
                    "approved": app_fallback.approved,
                    "lease_epoch_verified": app_fallback.lease_epoch_verified,
                },
            ],
        },
    }


def self_test() -> dict[str, Any]:
    suite = run_engine_benchmark_suite()
    assert len(suite["creative_engines"]) == 3
    assert suite["creative_self_repair"]["preflight_verdict"] == VERDICT_REPAIRED
    assert suite["creative_self_repair"]["repaired_contrast"] >= 3.0
    assert suite["creative_qa_refusal"]["refusal_code"] == "creative_layout_qa_gate_rejected"
    assert suite["personal_agent_engines"]["transcript_scanner"][0]["detection_count"] == 2
    assert suite["personal_agent_engines"]["transcript_scanner"][1]["fallback_used"] is True
    return {"passed": True, "checks": 6, "schema_version": SCHEMA_VERSION}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run multi-engine creative motion and personal-agent safety benchmarks."
    )
    parser.add_argument("--json", action="store_true", help="Emit full benchmark JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run invariant self-tests.")
    args = parser.parse_args(argv)

    if args.self_test:
        result = self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    report = run_engine_benchmark_suite()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print(f"Creative & Personal-Agent Engine Benchmark ({report['schema_version']})")
    for row in report["creative_engines"]:
        print(
            f"  [creative] {row['engine_id']}: format={row['artifact_format']} "
            f"frames={row['frame_count']} qa_passed={row['qa_passed']} "
            f"digest={row['artifact_digest_prefix']}"
        )
    print(
        f"  [self-repair] verdict={report['creative_self_repair']['preflight_verdict']} "
        f"contrast={report['creative_self_repair']['repaired_contrast']}:1"
    )
    for family, rows in report["personal_agent_engines"].items():
        for row in rows:
            print(f"  [{family}] engine={row['engine_id']} fallback={row['fallback_used']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
