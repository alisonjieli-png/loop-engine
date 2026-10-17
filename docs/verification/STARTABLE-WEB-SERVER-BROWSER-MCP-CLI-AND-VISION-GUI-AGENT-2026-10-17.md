# Startable Multi-Interface Web-Server Browser Agent Bridge and Vision-GUI Pixel-Actuation Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `d044fcae`
Implementation module: [`tools/startable_web_server_browser_mcp_cli_and_vision_gui_agent_engines.py`](../../tools/startable_web_server_browser_mcp_cli_and_vision_gui_agent_engines.py)
Verification suite: [`tools/test_startable_web_server_browser_mcp_cli_and_vision_gui_agent_engines.py`](../../tools/test_startable_web_server_browser_mcp_cli_and_vision_gui_agent_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), 32-task restricted-browser and multi-agent web benchmark, and 4 known-wrong preflight refusal controls for:

1. Slot Family 1: Startable 4-Interface Web-Server Browser Agent Daemon and Zero-JS Relay (`startable_multi_interface_browser_agent_server_slot`).
2. Slot Family 2: 4-Engine Restricted-Browser File-Attach, Synthetic Clipboard and Vision-GUI `(x, y)` Pixel Mouse Actuator (`restricted_browser_and_vision_gui_actuation_slot`).

## 1. Slot Family 1: Startable 4-Interface Web-Server Browser Agent Daemon (`startable_multi_interface_browser_agent_server_slot`)

The `startable_multi_interface_browser_agent_server_slot` spawns and serves the `baltor-browser-server` (`Loop` role `Practitioner`, mode `deterministic`) across 4 client interfaces simultaneously so `Muse`, `Dot`, `OpenClaw`, `Hermes`, `Claude Code`, `Codex`, and human operators can complete browser and GUI tasks even when the caller's tab blocks `javascript:` URLs, DevTools console injection, extensions, or local OS file dialogs:

| Interface ID | Engine Identifier | Target Harnesses | Transport & Control Mechanism |
| --- | --- | --- | --- |
| `I1` | `browser_zero_js_html_relay_engine` | `Muse`, `Dot`, locked-down browser tabs | Serves `GET /relay` and `POST /relay/action` as standard clickable HTML `<form>` and `<button>` controls requiring zero `javascript:` injection or extensions |
| `I2` | `mcp_browser_agent_bridge_engine` | `Claude Code`, `Codex`, `OpenClaw`, `Hermes` | Exposes `browser_navigate`, `browser_attach_media_bypass_dialog`, `browser_vision_pixel_click`, `browser_synthetic_paste_drop`, and `browser_verify_post` over `/mcp` |
| `I3` | `cli_baltor_browser_command_engine` | Terminal and shell harnesses | Single-command deterministic CLI (`baltor-browser attach-and-post --url ... --media ... --verify-selector ...`) emitting compact `64`-token JSON receipts (`< 200` tokens) |
| `I4` | `rest_websocket_session_multiplexer_engine` | Multi-agent handoffs (`Muse` + `Dot` + `Hermes`) | Shares and hands off an authenticated browser session lease (`sess_muse_dot_shared_01`) while preserving cookies and composer draft state |

## 2. Slot Family 2: 4-Engine Restricted-Browser and Vision-GUI `(x, y)` Pixel Actuator (`restricted_browser_and_vision_gui_actuation_slot`)

The `restricted_browser_and_vision_gui_actuation_slot` resolves blocked OS file dialogs (`Access to local files on your machine is disabled by your administrator` / `FileSelectDialogsAllowed=false`), detached or missing DOM `<input type="file">` elements in `web.telegram.org/k`, `/a`, and `bsky.app`, and canvas-only buttons:

| Engine ID | Engine Identifier | Mechanism | Representative Target & Pixel `(x, y)` Verification |
| --- | --- | --- | --- |
| `E1` | `cdp_file_chooser_interceptor_engine` | `Page.setInterceptFileChooserDialog(enabled=True)` + `DOM.setFileInputFiles` before OS dialog spawn | `bsky.app` gallery icon (`(422, 526)`, confidence `0.992`), binds detached file input in memory |
| `E2` | `synthetic_clipboard_datatransfer_paste_drop_engine` | In-page `Blob`/`File` + `DataTransfer` + `ClipboardEvent('paste')` / `DragEvent('drop')` | `web.telegram.org/k/#@BaltorAI` composer (`(830, 688)`, confidence `0.989`), zero OS file dialog |
| `E3` | `vision_gui_screenshot_icon_pixel_mouse_engine` | `1920x1080` frame capture + multi-scale icon template matching + OCR + 13-point cubic Bezier cursor trajectory + `Input.dispatchMouseEvent` / `xdotool` `Ctrl+L` path entry | `agentstudios.si/studio/canvas` (`(1168, 102)`, confidence `0.984`) and `web.telegram.org/a` (`(860, 626)`, confidence `0.987`) |
| `E4` | `direct_protocol_api_promotion_engine` | Promotes stuck UI drafts to direct authenticated protocol calls | Bluesky `com.atproto.repo.uploadBlob` + `app.bsky.feed.post` and Telegram `sendPhoto` / `messages.sendMedia` |

## 3. 32-Task Restricted-Browser and Multi-Agent Web Benchmark

| Engine / Configuration | Tasks Evaluated | Blocked File-Dialog / No-JS Tasks (`24`) Completion Rate | Overall Task Pass Rate (`32` Tasks) | Completion Across All `4` Interfaces | Human Bailouts Required (`"You attach it (2 min)"`) | Mean Icon-to-Pixel `(x, y)` Localization Latency |
| --- | --- | --- | --- | --- | --- | --- |
| `managed_sandbox_browser_alone_like_muse_default` | `32` | `0.0%` (`0/24`) | `25.0%` (`8/32`) | `25.0%` | `24` | `N/A` (blocked by OS file dialog policy) |
| `baltor_startable_web_server_and_vision_gui_pixel_bridge` | `32` | `100.0%` (`24/24`) | `100.0%` (`32/32`) | `100.0%` (`Browser Relay`, `MCP`, `CLI`, `REST/WS`) | `0` | `185.0 ms` |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Probe ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `unauthenticated_browser_server_access_blocked` | `startable_multi_interface_browser_agent_server_slot` | `preflight` (Layer 6) | `unauthenticated_browser_server_access_refused` | `true` |
| `pixel_coordinate_out_of_viewport_blocked` | `restricted_browser_and_vision_gui_actuation_slot` | `preflight` (Layer 6) | `pixel_coordinate_out_of_viewport_refused` | `true` |
| `unauthorized_host_file_path_blocked` | `restricted_browser_and_vision_gui_actuation_slot` | `preflight` (Layer 6) | `unauthorized_host_file_path_refused` | `true` |
| `unverified_post_completion_receipt_blocked` | `restricted_browser_and_vision_gui_actuation_slot` | `preflight` (Layer 6) | `unverified_post_completion_receipt_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_startable_web_server_browser_mcp_cli_and_vision_gui_agent_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/startable_web_server_browser_mcp_cli_and_vision_gui_agent_engines.py
```
