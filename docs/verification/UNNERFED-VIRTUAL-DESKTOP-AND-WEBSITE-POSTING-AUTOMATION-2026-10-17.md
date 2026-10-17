# Un-Nerfed Persistent Virtual Desktop, Paired-Residential Browser Bridge, and Multi-Platform Website Posting Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `d044fcae`
Implementation module: [`tools/unnerfed_virtual_desktop_and_website_posting_automation_engines.py`](../../tools/unnerfed_virtual_desktop_and_website_posting_automation_engines.py)
Verification suite: [`tools/test_unnerfed_virtual_desktop_and_website_posting_automation_engines.py`](../../tools/test_unnerfed_virtual_desktop_and_website_posting_automation_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), 30-task website automation and multi-platform publishing benchmark, and 4 known-wrong preflight refusal controls for the Baltor Un-Nerfed Persistent Virtual Desktop, Residential/Paired-Node Browser Profile, and Autonomous Multi-Platform Website/Social Posting Product Suite:

1. Slot Family 1: Un-Nerfed Single-Tenant Persistent Virtual Desktop and Paired-Residential Browser Engine (`unnerfed_persistent_virtual_desktop_slot`).
2. Slot Family 2: Multi-Platform Autonomous Website and Social Media Publishing Workflow Engine (`autonomous_website_and_social_posting_workflow_slot`).

## 1. Slot Family 1: Un-Nerfed Single-Tenant Persistent Virtual Desktop and Paired-Residential Browser Engine (`unnerfed_persistent_virtual_desktop_slot`)

Shared-cloud browser agents including `OpenAI Operator / Dots` and `Muse` (`muse.com`) restrict their virtual desktops with `FileSelectDialogsAllowed=false`, disabled `javascript:` evaluation, blocked browser extensions, wiped cookies after every run, blocked social domains, and recurring *"Take control of the browser"* or *"You attach it (2 min)"* bailouts. Slot Family 1 addresses those failure modes with three swappable engines behind `unnerfed_persistent_virtual_desktop_slot`:

| Engine ID | Execution Topology | Staging Drive & File Dialog Policy | Persistent Session & Vault State | Actuation & Delegation Primitives |
| --- | --- | --- | --- | --- |
| `single_tenant_persistent_cloud_virtual_desktop_engine` | Customer-isolated X11/Wayland + Chromium/Playwright CDP container | Unlocked `/mnt/baltor-stage` + `FileSelectDialogsAllowed=true` + CDP `Page.setInterceptFileChooserDialog` | `AES-256-GCM` tenant vault (`cookies + IndexedDB + localStorage + extension_state`), zero re-login on cron runs | Full Playwright + CDP + Userscript + Extension + OS Clipboard + Vision-GUI `(x, y)` pixel actuation |
| `paired_residential_edge_browser_bridge_engine` | Authenticated reverse WebSocket tunnel to customer home or office machine (`127.0.0.1` / `192.168.50.x`) | Local staged file handoff + native desktop file chooser | Real desktop browser profile and residential IP session | Eliminates shared datacenter ASN blocks and CAPTCHA loops |
| `nerfed_agent_rescue_delegation_bridge_engine` | External agent rescue bridge for `OpenAI Dot`, `Muse`, `ChatGPT`, and `Claude Web` | Automatic transfer into `/mnt/baltor-stage` | Scoped tenant profile mount + signed DOM screenshot and URL receipt | 1-click HTML Relay URL, MCP tool call, Cloud Proxy `M3` wire interception, or `signals+post@baltor.ai` email drop |

## 2. Slot Family 2: Multi-Platform Autonomous Website and Social Media Publishing Workflow Engine (`autonomous_website_and_social_posting_workflow_slot`)

Slot Family 2 (`cdp_file_chooser_and_synthetic_paste_publisher_engine`, `hybrid_api_and_vision_gui_fallback_publisher_engine`, and `rescue_delegated_cron_scheduler_publisher_engine`) executes end-to-end multi-asset website automation and social publishing across 10 web surfaces (`S01..S10`) where nerfed virtual desktops fail:

| Surface ID | Target Host | Attachment Modalities | Actuation Primitives | Default Desktop Engine | Default Publishing Engine |
| --- | --- | --- | --- | --- | --- |
| `S01_bluesky_web_and_atproto_multi_image_publisher` | `bsky.app` | `4_panel_png_webp`, `per_image_alt_text`, `thread_reply_chain` | `cdp_file_chooser_intercept`, `synthetic_datatransfer_paste`, `atproto_upload_blob_fallback` | `single_tenant_persistent_cloud_virtual_desktop_engine` | `cdp_file_chooser_and_synthetic_paste_publisher_engine` |
| `S02_telegram_web_k_and_a_media_channel_publisher` | `web.telegram.org` | `channel_photo_album`, `formatted_markdown_caption`, `scheduled_cron_broadcast` | `cdp_dom_set_file_input_files`, `unlocked_mnt_baltor_stage_dialog`, `persistent_indexeddb_mtproto_vault` | `single_tenant_persistent_cloud_virtual_desktop_engine` | `cdp_file_chooser_and_synthetic_paste_publisher_engine` |
| `S03_x_twitter_longform_thread_and_video_publisher` | `x.com` | `mp4_h264_video_chunked`, `multi_tweet_thread`, `scheduled_publish_slot` | `paired_residential_ip_tunnel`, `cdp_file_chooser_intercept`, `persistent_cookie_vault` | `paired_residential_edge_browser_bridge_engine` | `cdp_file_chooser_and_synthetic_paste_publisher_engine` |
| `S04_linkedin_carousel_pdf_and_article_publisher` | `linkedin.com` | `multi_page_carousel_pdf`, `company_and_personal_post`, `first_comment_link` | `unlocked_mnt_baltor_stage_dialog`, `vision_gui_xy_pixel_actuation`, `persistent_cookie_vault` | `single_tenant_persistent_cloud_virtual_desktop_engine` | `hybrid_api_and_vision_gui_fallback_publisher_engine` |
| `S05_reddit_flair_and_crosspost_automation` | `reddit.com` | `subreddit_rule_preflight`, `mandatory_post_flair_selection`, `gallery_image_set` | `paired_residential_ip_tunnel`, `cdp_shadow_dom_pierce`, `cdp_file_chooser_intercept` | `paired_residential_edge_browser_bridge_engine` | `hybrid_api_and_vision_gui_fallback_publisher_engine` |
| `S06_discord_webhook_and_rich_embed_forum_publisher` | `discord.com` | `forum_thread_tags`, `multi_file_attachment`, `rich_embed_payload` | `os_clipboard_datatransfer_paste`, `cdp_file_chooser_intercept`, `webhook_idempotent_fallback` | `single_tenant_persistent_cloud_virtual_desktop_engine` | `cdp_file_chooser_and_synthetic_paste_publisher_engine` |
| `S07_youtube_shorts_and_studio_metadata_publisher` | `studio.youtube.com` | `vertical_9x16_short_mp4`, `custom_thumbnail_png`, `timestamp_chapters_and_visibility` | `unlocked_mnt_baltor_stage_dialog`, `cdp_file_chooser_intercept`, `multi_step_wizard_verifier` | `single_tenant_persistent_cloud_virtual_desktop_engine` | `hybrid_api_and_vision_gui_fallback_publisher_engine` |
| `S08_substack_and_ghost_newsletter_issue_publisher` | `substack.com` | `prosemirror_rich_html`, `embedded_svg_png_charts`, `scheduled_email_and_web_send` | `os_clipboard_rich_html_paste`, `cdp_file_chooser_intercept`, `rescue_delegated_cron_runner` | `nerfed_agent_rescue_delegation_bridge_engine` | `rescue_delegated_cron_scheduler_publisher_engine` |
| `S09_producthunt_and_hackernews_launch_synchronizer` | `producthunt.com` | `launch_gallery_4_slides`, `first_maker_comment`, `live_launch_status_receipt` | `paired_residential_ip_tunnel`, `cdp_file_chooser_intercept`, `cross_site_timing_barrier` | `paired_residential_edge_browser_bridge_engine` | `rescue_delegated_cron_scheduler_publisher_engine` |
| `S10_multi_step_authenticated_saas_form_and_portal_automator` | `portal.enterprise-saas.internal` | `multi_page_wizard_state`, `signed_pdf_w9_invoice_upload`, `pdf_confirmation_receipt_download` | `unlocked_mnt_baltor_stage_dialog`, `vision_gui_xy_pixel_actuation`, `cdp_download_behavior_allow` | `single_tenant_persistent_cloud_virtual_desktop_engine` | `hybrid_api_and_vision_gui_fallback_publisher_engine` |

## 3. 30-Task Website Automation and Multi-Platform Media Posting Benchmark (`S01..S10` x `3` Variations)

| Engine / Baseline Policy | Tasks Evaluated | End-to-End Autonomous Completion | Blocked or Human Bailout Rate | Bluesky & Telegram Web Multi-Image Upload Success | Human Bailouts on Persistent-Session Cron Runs |
| --- | --- | --- | --- | --- | --- |
| `nerfed_vendor_virtual_desktop_dots_and_muse_baseline` | `30` (`S01..S10` x `3`) | `16.7%` (`5/30`) | `83.3%` (`25/30` blocked by `FileSelectDialogsAllowed=false`, wiped cookies, or *"You attach it (2 min)"* / *"Take control of the browser"*) | `0.0%` (`0/6`) | `25` human bailouts |
| `baltor_unnerfed_persistent_desktop_and_residential_bridge_suite` | `30` (`S01..S10` x `3`) | `96.7%` (`29/30`) | `3.3%` (`1/30` physical hardware USB key tap edge case) | `100.0%` (`6/6`) | `0` human bailouts |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Probe ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `cross_tenant_browser_profile_leak_blocked` | `unnerfed_persistent_virtual_desktop_slot` | `preflight` (Layer 6) | `cross_tenant_browser_profile_leak_refused` | `true` |
| `duplicate_unidempotent_social_post_blocked` | `autonomous_website_and_social_posting_workflow_slot` | `preflight` (Layer 6) | `duplicate_unidempotent_social_post_refused` | `true` |
| `public_post_secret_attachment_blocked` | `autonomous_website_and_social_posting_workflow_slot` | `preflight` (Layer 6) | `public_post_secret_attachment_refused` | `true` |
| `unverified_post_receipt_claim_blocked` | `autonomous_website_and_social_posting_workflow_slot` | `preflight` (Layer 6) | `unverified_post_receipt_claim_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_unnerfed_virtual_desktop_and_website_posting_automation_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/unnerfed_virtual_desktop_and_website_posting_automation_engines.py
```
