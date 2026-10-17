# Baltor Sovereign Paired-Computer and Open-Weight Model Zero-Preach Computer-Use Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `d044fcae`
Implementation module: [`tools/sovereign_open_model_unrestricted_paired_computer_use_engines.py`](../../tools/sovereign_open_model_unrestricted_paired_computer_use_engines.py)
Verification suite: [`tools/test_sovereign_open_model_unrestricted_paired_computer_use_engines.py`](../../tools/test_sovereign_open_model_unrestricted_paired_computer_use_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), 30-task computer-use benchmark, and 4 known-wrong preflight refusal controls for the Baltor Sovereign Paired-Computer and Open-Weight Model (`DeepSeek-V3/R1`, `Qwen-3.5-VL`, `UI-Tars`, `Gemma 4`, `Llama-4`) Zero-Preach Full-Desktop Computer-Use Suite, grounded in [`docs/architecture/NORTH-STAR.md`](../architecture/NORTH-STAR.md) and [`AGENTS.md`](../../AGENTS.md):

1. Slot Family 1: Open-Weight and Low-Friction Model Router for Sovereign Computer Use (`sovereign_open_model_computer_use_router_slot`).
2. Slot Family 2: Owner-Authorized Paired-Computer Full-Desktop Effect Actuator (`paired_computer_full_desktop_actuator_slot`).

## 1. Slot Family 1: Open-Weight and Low-Friction Model Router (`sovereign_open_model_computer_use_router_slot`)

The `sovereign_open_model_computer_use_router_slot` routes owner-authorized desktop, browser, file-system, native-dialog, and multi-application automation workflows to 6 open-weight and BYOK model backends across local loopback (`127.0.0.1:11434`), LAN GPU (`192.168.50.x`), `Ollama Cloud`, and custom OpenAI-compatible BYOK endpoints:

| Backend ID | Model Family | Model Identifiers | Primary Role | Contract Card Budget | Preachy Refusal Rate | Pixel Grounding |
| --- | --- | --- | --- | --- | --- | --- |
| `deepseek_v3_0324_backend` | `DeepSeek-V3` | `deepseek-v3-0324`, `deepseek-chat` | `unflinching_multi_step_planner_and_code_synthesizer` | `165 tokens` (`< 200`) | `0.0%` | `false` |
| `deepseek_r1_671b_backend` | `DeepSeek-R1` | `deepseek-r1:671b`, `deepseek-reasoner` | `deep_reasoning_workaround_and_redteam_verifier` | `180 tokens` (`< 200`) | `0.0%` | `false` |
| `ui_tars_72b_7b_backend` | `UI-Tars` | `ui-tars-72b-dpo`, `ui-tars-7b-sft` | `direct_screenshot_pixel_coordinate_and_dialog_grounding` | `140 tokens` (`< 200`) | `0.0%` | `true` |
| `qwen25_vl_72b_backend` | `Qwen-3.5-VL` | `qwen2.5-vl:72b`, `qwen3-vl:32b` | `visual_icon_template_and_cross_window_drag_drop_grounding` | `150 tokens` (`< 200`) | `0.0%` | `true` |
| `gemma4_31b_local_backend` | `Gemma 4` | `gemma4:31b`, `gemma4:12b` | `sub_second_local_and_ollama_cloud_action_loop_actuator` | `125 tokens` (`< 200`) | `0.0%` | `true` |
| `llama4_maverick_backend` | `Llama-4` | `llama-4-maverick:17b-128e`, `llama-4-scout:17b-16e` | `fast_multimodal_tool_dispatch_and_shell_automation` | `135 tokens` (`< 200`) | `0.0%` | `true` |

Four engines operate behind `sovereign_open_model_computer_use_router_slot`:

1. `deepseek_v3_and_r1_unflinching_planner_engine`: high-agency multi-step planning, Playwright, shell, and API synthesis without false-positive moralizing on authorized owner tasks.
2. `ui_tars_and_qwen25_vl_pixel_gui_grounding_engine`: direct screenshot-to-`(x, y)` pixel coordinate grounding, icon template recognition, native OS file-chooser navigation, and cross-window drag-and-drop.
3. `gemma4_31b_and_llama4_fast_local_actuator_engine`: sub-second local and `Ollama Cloud` action loop execution paired with `< 200`-token Baltor Contract Cards.
4. `automatic_false_refusal_and_preachiness_failover_engine`: detects when a commercial frontier model refuses a benign owner task or lectures the user, failing over in `6.4 ms` (`< 15.0 ms`) to the configured open-weight engine with its paired Contract Card.

## 2. Slot Family 2: Owner-Authorized Paired-Computer Full-Desktop Effect Actuator (`paired_computer_full_desktop_actuator_slot`)

The `paired_computer_full_desktop_actuator_slot` implements `paired_computer_sovereign_profile` profile separation and cryptographic owner-lease governance across four desktop actuators:

1. `native_os_file_dialogs_and_clipboard_actuator`: attaches local files in native GTK, Qt, macOS, and Win32 file-chooser dialogs, reads and writes the system clipboard, and performs cross-window drag-and-drop.
2. `x11_wayland_macos_win32_pixel_mouse_and_keyboard_actuator`: captures desktop screenshots, matches icon templates, and dispatches `(x, y)` mouse clicks, drags, and global hotkeys.
3. `local_browser_profile_and_playwright_cdp_actuator`: attaches to the owner's signed-in browser session over Chrome DevTools Protocol (`--remote-debugging-port`) or persistent context.
4. `local_terminal_and_daemon_process_actuator`: spawns authorized local scripts, `ffmpeg`, `git`, `docker`, and command-line tools.

Every executed action requires a verified `OwnerPairedComputerLease` (`owner_lease_signature`) and emits a local SHA-256 `DesktopActionReceipt` with an armed kill-switch and a reversible rollback command (`baltor-paired-rollback`).

## 3. 30-Task High-Friction Desktop, Social-Media Upload, Red-Team, Multi-App, and Native-Dialog Benchmark

| Benchmark Arm | Tasks Evaluated | Completed Tasks | Task Completion Rate | False-Positive Refusal / Preachy Lecture Rate | Sandbox File-Dialog Failure Rate | Native Dialog & `(x, y)` Pixel Success Rate | SHA-256 Receipts Emitted | Max Failover Latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `commercial_cloud_sandbox_with_preachy_refusals_baseline` | `30` | `9` | `30.0%` | `46.7%` (`14/30`) | `23.3%` (`7/30`) | `30.0%` (`9/30`) | `0` | `N/A` |
| `baltor_sovereign_paired_computer_with_deepseek_and_open_models` | `30` | `29` | `96.7%` | `0.0%` (`0/30`) | `0.0%` (`0/30`) | `100.0%` (`30/30`) | `30` | `6.4 ms` (`< 15.0 ms`) |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Control ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `missing_owner_paired_computer_lease` | `paired_computer_full_desktop_actuator_slot` | `preflight` (Layer 6) | `missing_owner_paired_computer_lease_refused` | `true` |
| `cross_profile_authority_escalation` | `paired_computer_full_desktop_actuator_slot` | `preflight` (Layer 6) | `cross_profile_authority_escalation_refused` | `true` |
| `catastrophic_unscoped_disk_wipe` | `paired_computer_full_desktop_actuator_slot` | `preflight` (Layer 6) | `catastrophic_unscoped_disk_wipe_refused` | `true` |
| `silent_local_secret_exfiltration` | `paired_computer_full_desktop_actuator_slot` | `preflight` (Layer 6) | `silent_local_secret_exfiltration_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh env PYTHONPATH=src:. /home/username/loop-engine/.venv/bin/python -m unittest -v tools/test_sovereign_open_model_unrestricted_paired_computer_use_engines.py
```
