#!/usr/bin/env python3
"""Unit tests for `tools/creative_and_personal_agent_engines.py`."""

from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
for rel in ("src", "tools"):
    candidate = str(REPO_ROOT / rel)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from loop_engine.core.engines.envelope import (
    EFFECT_DURABLE_PENDING,
    EFFECT_UNKNOWN,
    LAYER_ANSWERED,
    LAYER_TRACKING,
    RECONCILE_BEFORE_RETRY,
    EnvelopeRefusal,
)
from loop_engine.core.engines.envelope_preflight import (
    STEP_REPAIRED,
    VERDICT_REPAIRED,
)
from loop_engine.core.engines.envelope_tracking import (
    EFFECT_STATE_UNKNOWN,
    REQUEST_CANCELLED,
    TASK_FAILED,
    journal_intent,
    journal_outcome,
    request_identity_digest,
)

import creative_and_personal_agent_engines as cpae


class CreativeMotionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dispatcher = cpae.CreativeMotionDispatcher()
        self.account = cpae._sample_account()

    def test_three_creative_engines_produce_valid_qa_checked_outputs(self) -> None:
        scene = cpae._sample_clean_scene()
        digests: set[str] = set()
        for engine_id in (
            cpae.ENGINE_REELKIT_PLANNER,
            cpae.ENGINE_REMOTION_THREE,
            cpae.ENGINE_SVG_STORYBOARD,
        ):
            res = self.dispatcher.dispatch(scene, account=self.account, preferred_engine=engine_id)
            self.assertIsInstance(res, cpae.CreativeSceneResult)
            assert isinstance(res, cpae.CreativeSceneResult)
            self.assertEqual(res.engine_id, engine_id)
            self.assertFalse(res.fallback_used)
            self.assertEqual(res.frame_count, 180)
            self.assertTrue(res.qa_report.passed)
            self.assertEqual(res.qa_report.fail_count, 0)
            self.assertEqual(res.nested_qa_frame.depth, 1)
            self.assertEqual(
                res.nested_qa_frame.path,
                (cpae.COMPONENT_CREATIVE_MOTION, cpae.COMPONENT_CREATIVE_QA_GATE),
            )
            digests.add(res.artifact_digest)
        self.assertEqual(len(digests), 3)

    def test_creative_engine_fallback_on_simulated_fault(self) -> None:
        scene = cpae._sample_clean_scene()
        res = self.dispatcher.dispatch(
            scene,
            account=self.account,
            preferred_engine=cpae.ENGINE_REELKIT_PLANNER,
            simulated_fault_engines=frozenset({cpae.ENGINE_REELKIT_PLANNER}),
        )
        self.assertIsInstance(res, cpae.CreativeSceneResult)
        assert isinstance(res, cpae.CreativeSceneResult)
        self.assertEqual(res.engine_id, cpae.ENGINE_REMOTION_THREE)
        self.assertTrue(res.fallback_used)

        res_svg = self.dispatcher.dispatch(
            scene,
            account=self.account,
            preferred_engine=cpae.ENGINE_REELKIT_PLANNER,
            simulated_fault_engines=frozenset(
                {cpae.ENGINE_REELKIT_PLANNER, cpae.ENGINE_REMOTION_THREE}
            ),
        )
        self.assertIsInstance(res_svg, cpae.CreativeSceneResult)
        assert isinstance(res_svg, cpae.CreativeSceneResult)
        self.assertEqual(res_svg.engine_id, cpae.ENGINE_SVG_STORYBOARD)
        self.assertTrue(res_svg.fallback_used)

    def test_preflight_self_repair_fixes_low_contrast_and_undersized_font(self) -> None:
        defect_scene = cpae.CreativeSceneSpec(
            scene_id="miso_v02_defect",
            title="Miso v02 Defect",
            allow_preflight_repair=True,
            beats=(
                cpae.BeatSpec(
                    beat_id="beat_1",
                    start_s=0.0,
                    duration_s=2.0,
                    bg_hex="#8a2820",
                    captions=(
                        cpae.CaptionElementSpec(
                            element_id="stamp_bad",
                            text="HOKKAIDO MISO",
                            slot_name="upper",
                            typography_role="stamp",
                            font_size_px=28,
                            fg_hex="#c0392b",
                            bg_hex="#8a2820",
                        ),
                    ),
                ),
            ),
        )
        res = self.dispatcher.dispatch(defect_scene, account=self.account)
        self.assertIsInstance(res, cpae.CreativeSceneResult)
        assert isinstance(res, cpae.CreativeSceneResult)
        self.assertEqual(res.preflight_report.verdict, VERDICT_REPAIRED)
        self.assertEqual(res.preflight_report.steps[0].outcome, STEP_REPAIRED)
        box = res.planned_boxes[0]
        self.assertEqual(box.font_size_px, cpae.ROLE_FONT_FLOORS["stamp"])
        self.assertEqual(box.fg_hex, cpae.REPAIRED_CREAM_HEX)
        self.assertGreaterEqual(box.contrast_to_bg, 7.0)

        no_repair_scene = cpae.CreativeSceneSpec(
            scene_id="miso_v02_no_repair",
            title="Miso v02 No Repair",
            allow_preflight_repair=False,
            beats=defect_scene.beats,
        )
        refusal = self.dispatcher.dispatch(no_repair_scene, account=self.account)
        self.assertIsInstance(refusal, EnvelopeRefusal)
        assert isinstance(refusal, EnvelopeRefusal)
        self.assertEqual(refusal.code, "creative_caption_font_below_floor")

    def test_nested_layout_qa_gate_catches_overlap_keepout_and_platform_zones(self) -> None:
        overlapping_scene = cpae.CreativeSceneSpec(
            scene_id="overlap_and_zones",
            title="Overlap and Platform Zone Intrusion",
            allow_preflight_repair=False,
            beats=(
                cpae.BeatSpec(
                    beat_id="beat_bad",
                    start_s=0.0,
                    duration_s=0.15,
                    bg_hex="#121212",
                    subject_keepouts=(
                        cpae.BoundingBox(x0=200, y0=400, x1=700, y1=800, label="hero_face"),
                    ),
                    captions=(
                        cpae.CaptionElementSpec(
                            element_id="cap_a",
                            text="FIRST OVERLAPPING CAPTION",
                            slot_name="upper",
                            typography_role="headline",
                            font_size_px=50,
                            fg_hex="#ffffff",
                            bg_hex="#121212",
                            override_bbox=cpae.BoundingBox(
                                x0=10, y0=450, x1=990, y1=600, label="cap_a"
                            ),
                        ),
                        cpae.CaptionElementSpec(
                            element_id="cap_b",
                            text="SECOND OVERLAPPING CAPTION IN BOTTOM ZONE",
                            slot_name="low",
                            typography_role="caption",
                            font_size_px=34,
                            fg_hex="#ffffff",
                            bg_hex="#121212",
                            override_bbox=cpae.BoundingBox(
                                x0=100, y0=500, x1=970, y1=1650, label="cap_b"
                            ),
                        ),
                    ),
                ),
            ),
        )
        refusal = self.dispatcher.dispatch(overlapping_scene, account=self.account)
        self.assertIsInstance(refusal, EnvelopeRefusal)
        assert isinstance(refusal, EnvelopeRefusal)
        self.assertEqual(refusal.code, "creative_layout_qa_gate_rejected")

        boxes = cpae._plan_boxes_for_scene(overlapping_scene, avoid_collisions=False)
        report = cpae.evaluate_layout_audit(overlapping_scene, boxes)
        codes = {f.rule_code for f in report.findings}
        self.assertIn("caption_flicker_under_250ms", codes)
        self.assertIn("edge_margin_intrusion", codes)
        self.assertIn("platform_right_rail_intrusion", codes)
        self.assertIn("platform_bottom_zone_intrusion", codes)
        self.assertIn("subject_keepout_collision", codes)
        self.assertIn("text_to_text_overlap", codes)


class PersonalAgentSafetyEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dispatcher = cpae.PersonalAgentSafetyDispatcher()
        self.account = cpae._sample_account()

    def test_transcript_scanner_redacts_and_never_echoes_raw_values_in_refusal(self) -> None:
        raw_marker_a = "s" + "k-live998877665544332211"
        raw_marker_b = "Bear" + "er tok_998877665544332211"
        req = cpae.TranscriptScanRequest(
            session_id="sess_01",
            transcript_lines=(f"Connecting with {raw_marker_a} and {raw_marker_b}",),
            block_on_detection=False,
        )
        res = self.dispatcher.scan_transcript(req, account=self.account)
        self.assertIsInstance(res, cpae.TranscriptScanResult)
        assert isinstance(res, cpae.TranscriptScanResult)
        self.assertFalse(res.clean)
        self.assertEqual(res.detection_count, 2)
        self.assertNotIn(raw_marker_a, res.sanitized_lines[0])
        self.assertNotIn(raw_marker_b, res.sanitized_lines[0])

        res_fb = self.dispatcher.scan_transcript(
            req,
            account=self.account,
            simulated_fault_engines=frozenset({cpae.ENGINE_SCANNER_PRIMARY}),
        )
        self.assertIsInstance(res_fb, cpae.TranscriptScanResult)
        assert isinstance(res_fb, cpae.TranscriptScanResult)
        self.assertTrue(res_fb.fallback_used)
        self.assertEqual(res_fb.detection_count, 2)
        self.assertNotIn(raw_marker_a, res_fb.sanitized_lines[0])

        blocking_req = cpae.TranscriptScanRequest(
            session_id="sess_02",
            transcript_lines=req.transcript_lines,
            block_on_detection=True,
        )
        refusal = self.dispatcher.scan_transcript(blocking_req, account=self.account)
        self.assertIsInstance(refusal, EnvelopeRefusal)
        assert isinstance(refusal, EnvelopeRefusal)
        self.assertEqual(refusal.code, "transcript_sensitive_material_quarantined")
        self.assertNotIn(raw_marker_a, refusal.message)
        self.assertNotIn(raw_marker_b, refusal.message)
        self.assertNotIn(raw_marker_a, refusal.next_action)

    def test_pre_compaction_checkpoint_refuses_unanchored_pending_effect(self) -> None:
        req_id = request_identity_digest("dns_mutation:baltor.ai")
        pending_entry = journal_intent(
            (),
            component=cpae.COMPONENT_DURABLE_APPROVAL,
            request_identity=req_id,
            repeatable=False,
            at=cpae.FIXED_TIMESTAMP_ISO,
        )
        req_unanchored = cpae.PreCompactionRequest(
            session_id="sess_cp",
            active_task_id="task_dns",
            turn_count=19,
            uncommitted_file_digests={"src/app.py": "1234abcd"},
            open_refusal_codes=(),
            journal_entries=(pending_entry,),
            anchored_request_identities=frozenset(),
        )
        refusal = self.dispatcher.build_pre_compaction_checkpoint(
            req_unanchored, account=self.account
        )
        self.assertIsInstance(refusal, EnvelopeRefusal)
        assert isinstance(refusal, EnvelopeRefusal)
        self.assertEqual(refusal.code, "compaction_unanchored_pending_effect")
        self.assertEqual(refusal.retry, RECONCILE_BEFORE_RETRY)
        self.assertEqual(refusal.effect_commitment, EFFECT_DURABLE_PENDING)

        req_anchored = cpae.PreCompactionRequest(
            session_id="sess_cp",
            active_task_id="task_dns",
            turn_count=19,
            uncommitted_file_digests={"src/app.py": "1234abcd"},
            open_refusal_codes=(),
            journal_entries=(pending_entry,),
            anchored_request_identities=frozenset({req_id}),
        )
        cp_res = self.dispatcher.build_pre_compaction_checkpoint(
            req_anchored, account=self.account
        )
        self.assertIsInstance(cp_res, cpae.PreCompactionCheckpointResult)
        assert isinstance(cp_res, cpae.PreCompactionCheckpointResult)
        self.assertEqual(cp_res.unsettled_request_identities, (req_id,))

    def test_durable_task_approval_enforces_cas_lease_digest_and_reconciliation(self) -> None:
        req_id = request_identity_digest("approval:act_01")
        intent = journal_intent(
            (),
            component=cpae.COMPONENT_DURABLE_APPROVAL,
            request_identity=req_id,
            repeatable=False,
            at=cpae.FIXED_TIMESTAMP_ISO,
        )
        unknown_entry = journal_outcome(
            (intent,),
            component=cpae.COMPONENT_DURABLE_APPROVAL,
            request_identity=req_id,
            request_outcome=REQUEST_CANCELLED,
            task_outcome=TASK_FAILED,
            effect_state=EFFECT_STATE_UNKNOWN,
            at=cpae.FIXED_TIMESTAMP_ISO,
        )
        digest = cpae._sha256_hex("transfer:baltor.ai")

        # 1. Retry without reconciliation is refused with RECONCILE_BEFORE_RETRY
        unreconciled_req = cpae.DurableTaskApprovalRequest(
            action_id="act_01",
            task_id="task_01",
            effect_kind="transfer_domain",
            target_resource="baltor.ai",
            proposed_payload_digest=digest,
            execution_payload_digest=digest,
            worker_id="worker_1",
            lease_epoch=4,
            expected_lease_epoch=4,
            approver_account_id=self.account.account_id,
            approval_issued_at_epoch_s=100,
            approval_expires_at_epoch_s=500,
            current_time_epoch_s=200,
            prior_journal_entries=(intent, unknown_entry),
            reconciled_external_state=None,
        )
        refusal = self.dispatcher.evaluate_durable_task_approval(
            unreconciled_req, account=self.account
        )
        self.assertIsInstance(refusal, EnvelopeRefusal)
        assert isinstance(refusal, EnvelopeRefusal)
        self.assertEqual(refusal.code, "durable_action_reconcile_required")
        self.assertEqual(refusal.retry, RECONCILE_BEFORE_RETRY)
        self.assertEqual(refusal.effect_commitment, EFFECT_UNKNOWN)

        # 2. Reconciled as already_applied short-circuits at LAYER_TRACKING (LAYER_ANSWERED)
        reconciled_req = cpae.DurableTaskApprovalRequest(
            action_id="act_01",
            task_id="task_01",
            effect_kind="transfer_domain",
            target_resource="baltor.ai",
            proposed_payload_digest=digest,
            execution_payload_digest=digest,
            worker_id="worker_1",
            lease_epoch=4,
            expected_lease_epoch=4,
            approver_account_id=self.account.account_id,
            approval_issued_at_epoch_s=100,
            approval_expires_at_epoch_s=500,
            current_time_epoch_s=200,
            prior_journal_entries=(intent, unknown_entry),
            reconciled_external_state="already_applied",
        )
        short_res = self.dispatcher.evaluate_durable_task_approval(
            reconciled_req, account=self.account
        )
        self.assertIsInstance(short_res, cpae.DurableTaskApprovalResult)
        assert isinstance(short_res, cpae.DurableTaskApprovalResult)
        self.assertFalse(short_res.envelope_trace.engine_dispatched)
        self.assertEqual(
            short_res.envelope_trace.steps[-1],
            (LAYER_TRACKING, LAYER_ANSWERED),
        )

        # 3. Stale CAS lease epoch is refused
        stale_req = cpae.DurableTaskApprovalRequest(
            action_id="act_02",
            task_id="task_01",
            effect_kind="transfer_domain",
            target_resource="baltor.ai",
            proposed_payload_digest=digest,
            execution_payload_digest=digest,
            worker_id="worker_1",
            lease_epoch=3,
            expected_lease_epoch=4,
            approver_account_id=self.account.account_id,
            approval_issued_at_epoch_s=100,
            approval_expires_at_epoch_s=500,
            current_time_epoch_s=200,
        )
        stale_refusal = self.dispatcher.evaluate_durable_task_approval(
            stale_req, account=self.account
        )
        self.assertIsInstance(stale_refusal, EnvelopeRefusal)
        assert isinstance(stale_refusal, EnvelopeRefusal)
        self.assertEqual(stale_refusal.code, "durable_action_stale_worker_lease")

        # 4. Fallback engine refuses mutating effects when primary CAS coordinator is down
        mutating_fallback_req = cpae.DurableTaskApprovalRequest(
            action_id="act_03",
            task_id="task_01",
            effect_kind="transfer_domain",
            target_resource="baltor.ai",
            proposed_payload_digest=digest,
            execution_payload_digest=digest,
            worker_id="worker_1",
            lease_epoch=4,
            expected_lease_epoch=4,
            approver_account_id=self.account.account_id,
            approval_issued_at_epoch_s=100,
            approval_expires_at_epoch_s=500,
            current_time_epoch_s=200,
            read_only_effect=False,
        )
        fb_refusal = self.dispatcher.evaluate_durable_task_approval(
            mutating_fallback_req,
            account=self.account,
            simulated_fault_engines=frozenset({cpae.ENGINE_APPROVAL_PRIMARY}),
        )
        self.assertIsInstance(fb_refusal, EnvelopeRefusal)
        assert isinstance(fb_refusal, EnvelopeRefusal)
        self.assertEqual(fb_refusal.code, "fallback_policy_refuses_mutating_effect")

    def test_self_test_and_cli_json(self) -> None:
        res = cpae.self_test()
        self.assertTrue(res["passed"])
        self.assertEqual(res["checks"], 6)


if __name__ == "__main__":
    unittest.main()
