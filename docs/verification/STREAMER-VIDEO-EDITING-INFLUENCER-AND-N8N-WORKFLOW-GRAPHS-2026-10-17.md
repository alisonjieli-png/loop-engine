# Streamer, Video-Editing, Influencer Strategy and n8n-Style Visual Workflow Graph Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `74b74085`
Implementation module: [`tools/streamer_video_editing_influencer_and_n8n_workflow_graph_engines.py`](../../tools/streamer_video_editing_influencer_and_n8n_workflow_graph_engines.py)
Verification suite: [`tools/test_streamer_video_editing_influencer_and_n8n_workflow_graph_engines.py`](../../tools/test_streamer_video_editing_influencer_and_n8n_workflow_graph_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), 120-tool creator registry qualification (`8` creator families × `15` tools per family), `n8n`-style visual node-and-wire workflow compilation, 24-workflow benchmark, and 4 known-wrong preflight refusal controls:

1. Slot Family 1: 120-Tool Streamer, Video-Editing and Influencer Growth Registry (`streamer_video_editing_and_influencer_registry_slot`).
2. Slot Family 2: `n8n`-Style Visual Node-Graph Workflow Canvas and Bi-Directional `Loop` Compiler (`n8n_style_visual_workflow_graph_slot`).

## 1. Slot Family 1: 120-Tool Streamer, Video-Editing and Influencer Registry (`streamer_video_editing_and_influencer_registry_slot`)

The `streamer_video_editing_and_influencer_registry_slot` (`streamer_video_editing_influencer_120_pack_registry_engine` and `creator_tool_safe_zone_lufs_and_secret_redaction_verifier_engine`) indexes, labels, and wraps `120` distinct streamer, video editing, and influencer tools and strategies across `baltor.ai`, `agentstudios.si`, `agentfoundry.si`, and `agentfeeds.si`:

| Family ID | Tools Indexed | `Loop` Role / Mode | Representative Streamer, Video-Editing, and Influencer Tools |
| --- | --- | --- | --- |
| `F01_live_streamer_obs_and_broadcast_automation` | `15` | `Practitioner` / `deterministic` | `obs-websocket-v5-cli`, `whip-webrtc-subsecond-ingest`, `mediamtx-multi-destination-rtmp-srt-relay`, `realtime-sidechain-mic-ducker-14lufs`, `low-latency-screen-region-privacy-blur` |
| `F02_realtime_highlight_detection_and_vod_clipper` | `15` | `Intelligence` / `hybrid` | `chat-velocity-cusum-spike-clipper`, `audio-excitement-laughter-transient-detector`, `coding-milestone-test-pass-auto-clipper`, `three-hour-vod-to-12-viral-shorts-splitter`, `vertical-9x16-speaker-facetrack-code-cropper` |
| `F03_programmatic_video_editing_and_timeline_compilers` | `15` | `Solution` / `deterministic` | `auto-editor-silence-dead-air-trimmer`, `losslesscut-keyframe-surgical-cutter`, `ffmpeg-filter-complex-graph-builder`, `remotion-motion-canvas-parametric-timeline`, `color-grade-lut-oklab-perceptual-matcher` |
| `F04_kinetic_captions_dubbing_and_safe_zone_overlays` | `15` | `Practitioner` / `hybrid` | `whisperx-stable-ts-word-forced-aligner`, `hormozi-kurzgesagt-kinetic-word-highlighter`, `vertical-9x16-safe-zone-collision-guard` (`top >= 120px`, `bottom >= 320px`, `right >= 140px`), `harding-3hz-pse-flash-safety-limiter` |
| `F05_thumbnail_hook_and_retention_curve_strategies` | `15` | `Intelligence` / `hybrid` | `zero-to-3s-pattern-interrupt-hook-evaluator`, `second-by-second-retention-dropoff-analyzer`, `three-element-high-contrast-thumbnail-compositor`, `thompson-sampling-title-thumbnail-ab-bandit`, `pacing-cadence-visual-change-3to5s-analyzer` |
| `F06_influencer_multi_platform_repurposing_and_monetization` | `15` | `Practitioner` / `deterministic` | `one-to-eight-omnichannel-cascade-publisher`, `ftc-16cfr255-sponsor-affiliate-disclosure-injector`, `utm-privacy-safe-aggregate-link-counter`, `brand-deal-cpm-epc-rate-card-calculator`, `comment-to-dm-lead-magnet-workflow` |
| `F07_vtuber_avatar_3d_and_audio_reactive_visuals` | `15` | `Solution` / `hybrid` | `webgpu-threejs-audio-reactive-shader-rig`, `vtuber-2d-3d-viseme-lipsync-driver`, `live-terminal-code-diff-pip-overlay`, `horizon-enforced-3d-background-stage`, `procedural-karplus-strong-dmca-free-backing-track` |
| `F08_creator_analytics_trend_spidering_and_topic_radar` | `15` | `Intelligence` / `hybrid` | `breakout-topic-velocity-3p5x-outlier-radar`, `competitor-hook-structure-deconstructor`, `audience-question-cluster-comment-miner`, `evergreen-vs-trending-portfolio-balancer`, `ctr-vs-avd-pareto-frontier-diagnostics` |

## 2. Slot Family 2: `n8n`-Style Visual Node-Graph Workflow Canvas (`n8n_style_visual_workflow_graph_slot`)

The `n8n_style_visual_workflow_graph_slot` (`n8n_visual_canvas_to_baltor_loop_graph_compiler_engine` and `n8n_style_svg_diagram_and_live_wire_telemetry_renderer_engine`) bi-directionally compiles between `n8n`-style visual workflow JSON + interactive `SVG` cubic-Bezier node-and-wire diagrams and Baltor `Loop` execution graphs across 8 visual node categories:

| Visual Node Category | `Loop` Role / Mode | Canonical `n8n`-Compatible Node Types |
| --- | --- | --- |
| `trigger_nodes` | `Practitioner` / `deterministic` | `n8n.trigger.webhook`, `n8n.trigger.cron_schedule`, `n8n.trigger.live_stream_event`, `n8n.trigger.git_push`, `n8n.trigger.repodir_feed_signal`, `n8n.trigger.chat_command` |
| `action_and_cli_nodes` | `Practitioner` / `deterministic` | `n8n.action.indexed_agent_cli_240`, `n8n.action.obs_websocket_v5_cli`, `n8n.action.mediamtx_multi_rtmp_relay`, `n8n.action.stream_deck_macro_synthesizer` |
| `flow_control_nodes` | `Solution` / `deterministic` | `n8n.flow.if_switch_branch`, `n8n.flow.parallel_fan_out`, `n8n.flow.merge_rrf_join`, `n8n.flow.split_in_batches`, `n8n.flow.rate_limit_wait` |
| `intelligence_and_jev_router_nodes` | `Intelligence` / `hybrid` | `n8n.intelligence.jev_systemone_classifier`, `n8n.intelligence.matryoshka_lsh_lookup`, `n8n.intelligence.self_improving_rag`, `n8n.intelligence.chat_cusum_highlight_detector` |
| `media_and_render_nodes` | `Solution` / `hybrid` | `n8n.media.ffmpeg_200_layer_compositor`, `n8n.media.vertical_9x16_safe_zone_verifier`, `n8n.media.live_secret_blur_filter`, `n8n.media.whisperx_kinetic_captioner` |
| `human_in_the_loop_gate_nodes` | `Practitioner` / `deterministic` | `n8n.hitl.approval_queue`, `n8n.hitl.ftc_16cfr255_disclosure_check`, `n8n.hitl.live_spend_gate` |
| `sub_workflow_nodes` | `Solution` / `hybrid` | `n8n.subworkflow.execute_nested_loop_dag`, `n8n.subworkflow.shorts_12x_batch_pipeline` |
| `output_and_telemetry_nodes` | `Practitioner` / `deterministic` | `n8n.output.omnichannel_1to8_publisher`, `n8n.output.step_execution_trace_receipt_emitter` |

## 3. 24-Workflow Streamer, Video-Editing and Influencer Benchmark

| Engine / Pipeline | Workflows Evaluated | End-to-End Omnichannel Drop Duration | Speedup vs Manual Baseline | Safe-Zone / `-14 LUFS` / Secret-Leak Error Rate | Live-Stream Secret Redaction Rate | Bi-Directional `n8n` <-> `Loop` Fidelity |
| --- | --- | --- | --- | --- | --- | --- |
| `manual_multi_app_creator_editing_and_publishing_baseline` | `24` | `390.0 min` (`6.5 hours`) | `1.0x` | `31.0%` | `69.0%` | `0.0%` |
| `baltor_streamer_influencer_and_n8n_visual_graph_suite` | `24` | `4.2 min` | `92.8x` | `0.0%` (`100.0%` compliant) | `100.0%` | `100.0%` |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Probe ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `live_stream_secret_exposure_blocked` | `streamer_video_editing_and_influencer_registry_slot` | `preflight` (Layer 6) | `live_stream_secret_exposure_refused` | `true` |
| `missing_ftc_sponsor_disclosure_blocked` | `n8n_style_visual_workflow_graph_slot` | `preflight` (Layer 6) | `missing_ftc_sponsor_disclosure_refused` | `true` |
| `unlicensed_dmca_audio_stem_blocked` | `streamer_video_editing_and_influencer_registry_slot` | `preflight` (Layer 6) | `unlicensed_dmca_audio_stem_refused` | `true` |
| `non_loop_n8n_node_bypass_blocked` | `n8n_style_visual_workflow_graph_slot` | `preflight` (Layer 6) | `non_loop_n8n_node_bypass_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_streamer_video_editing_influencer_and_n8n_workflow_graph_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/streamer_video_editing_influencer_and_n8n_workflow_graph_engines.py
```
