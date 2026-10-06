# Baltor in ChatGPT and Codex

Kind: operating guide for the Baltor app in OpenAI's plugin directory, the one
directory that ChatGPT and Codex share. It lists the directory's requirements
with the source and the date each was read, what the live service did on
October 5, 2026 before this work, what was built, the proof, and the steps
that remain for the release owner and for the owner.

The app is not a second server. `https://baltor.ai/mcp` answers every client;
after it authenticates a request it chooses one of two presentations of the
same operations:

```text
/mcp, one endpoint, one set of operations
├── harness presentation      every other client, unchanged: provisioning_* tool names, full records,
│                             the Loop execution record, the plan offer and its links
└── OpenAI host presentation  a delegation whose OAuth client redirects only to an OpenAI host
    │                         (chatgpt.com, *.openai.com), or any request with the header
    │                         Baltor-Client-Profile: openai_apps
    ├── eight tools with plain verb names, titles, explicit readOnly, destructive and openWorld
    │   hints, output schemas and their OAuth scheme, each mapped onto one existing operation
    ├── answers with no account identity, Loop execution record or meter record
    ├── refusals in the same codes; a plan refusal explains and links the plans page only
    ├── one MCP Apps view, ui://baltor/library-v1.html, for search results and a package's files
    └── server instructions that treat a downloaded file as material, never as instructions
```

The code is
[`chatgpt_app.py`](../../src/loop_engine/core/service_runtime/chatgpt_app.py),
the view is
[`app_widgets/library.html`](../../src/loop_engine/core/service_runtime/app_widgets/library.html),
and the submission package is
[`integrations/chatgpt-app/`](../../integrations/chatgpt-app/README.md).

## Sources

Every requirement below was read on October 5, 2026 (UTC 23:24) from the
page named, through its Markdown twin where OpenAI publishes one. The Apps SDK
pages now live under `/plugins`: the old `/apps-sdk` addresses serve the same
documentation set, and `https://developers.openai.com/apps-sdk/llms.txt` names
the `/plugins` pages. The SHA-256 prefix is of the bytes read.

| Id | Page | Address | SHA-256 prefix |
|---|---|---|---|
| S1 | Plugin guidelines | https://developers.openai.com/plugins/plugin-guidelines | d756819aa5e7c9db |
| S2 | Upload and submit your plugin | https://developers.openai.com/plugins/deploy/submission | b04f4d248b3fd7b4 |
| S3 | Remote MCP server review requirements | https://developers.openai.com/plugins/deploy/app-review | 70480e0967ef3df6 |
| S4 | Plugin submission errors | https://developers.openai.com/plugins/deploy/submission-errors | 48fa811989b30179 |
| S5 | Authentication | https://developers.openai.com/plugins/build/auth | 30906090c8e55b0e |
| S6 | Build an MCP server | https://developers.openai.com/plugins/build/mcp-server | db5ccf6e3b692ff1 |
| S7 | Add UI to your MCP server | https://developers.openai.com/plugins/build/chatgpt-ui | 9403394ff61d97fd |
| S8 | Reference | https://developers.openai.com/plugins/reference | c4479095e718215f |
| S9 | Security and privacy | https://developers.openai.com/plugins/guides/security-privacy | 2354bba4b09c87d3 |
| S10 | Optimize metadata | https://developers.openai.com/plugins/guides/optimize-metadata | a553d71ee2adf6c8 |
| S11 | Define tools | https://developers.openai.com/plugins/plan/tools | c0cb4c691004aedd |
| S12 | Connect and test your plugin | https://developers.openai.com/plugins/deploy/connect-chatgpt | 979f47ad47e83757 |
| S13 | Checkout and monetization | https://developers.openai.com/plugins/build/monetization | ddca306881a79679 |
| S14 | UI guidelines | https://developers.openai.com/plugins/concepts/ui-guidelines | 20f5a48aec06032d |
| S15 | Package your plugin | https://developers.openai.com/plugins/build/plugins | 41410752fccb74ba |
| S16 | App Developer Terms, updated September 28, 2026 | https://openai.com/policies/developer-apps-terms/ | 9b39599e63e7e4dc |
| S17 | Usage policies, effective October 29, 2025 | https://openai.com/policies/usage-policies/ | bfb44a7e07683f63 |
| S18 | MCP Apps specification 2026-01-26 | https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx | ee452a7d1b9b7fb9 |

The two openai.com policy pages refuse plain HTTP clients, so they were read
through a real browser. Two public reports from September and October 2026
describe how ChatGPT's connector speaks the protocol: it opens with the
2026-07-28 `server/discover` request, sends `User-Agent: openai-mcp/1.0.0`,
and declares the MCP Apps extension
([macuse-mcp issue 5](https://github.com/macuse-app/macuse-mcp/issues/5),
[SwiftMCP issue 197](https://github.com/Cocoanetics/SwiftMCP/issues/197)).
They are observations, not OpenAI requirements; they are why the checks run
both protocol eras.

## Requirements checklist

Status: **met** means the live service already met it before this work;
**built** means this work adds it and the checks named hold it; **owner** and
**lead** mean a step only that person can take, listed at the end.

| Id | Requirement | Source | Status |
|---|---|---|---|
| R1 | Listing text: display name and subtitle one line of at most 30 characters, description at most 4,000, developer name at most 80, a category from the list, at most 20 capabilities of 120 characters, at most three unique starter prompts of 128 characters without mentions. No "MCP" or "Plugin" after the name, no comparison, pricing, subscription, trial, discount or promotion. | S1 Plugin name; S2 Listing metadata; S4 Final directory submission | Built: `plugin.json`, held by `tools/build_chatgpt_app_package.py` |
| R2 | Four HTTPS listing addresses, at most 1,024 characters each: website, support, privacy policy, terms. | S2; S4 | Built: `/support` is new; the other three were live |
| R3 | A square primary icon and composer icon, 48 to 4,096 pixels, PNG, JPEG, WebP or SVG, at most 5 MiB. | S2 Icons and screenshots; S4 Image errors | Built: `assets/logo.png` 512, `assets/icon.png` 256 |
| R4 | Brand colours: at least 2:1 against white, and the dark colour at least 2:1 against #212121. | S4 | Built: #D95B0F (3.85:1) and #FB9D59 (7.72:1) |
| R5 | Screenshots only when the server returns a view; then one per starter prompt, PNG or JPEG, exactly 706 pixels wide and 400 to 860 tall. | S4 Final directory submission | Built: three, from live answers |
| R6 | Exactly five positive cases (description, prompt, tools, expected result) and three negative cases, release notes, and a reviewer-accessible video walkthrough. | S2 Complete review information; S4 MCP and review errors | Built: cases and notes in `plugin.json`. Video: owner |
| R7 | Reviewer credentials: a dedicated account with sample data and full features, signing in with no MFA, email or text code, magic link or private network; entered in the dashboard, never in the package. | S1 Test credentials; S2; S3 Common rejection reasons | Met: email and password sign-in works. Account: lead and owner |
| R8 | Package format: root `plugin.json` with the Agent Plugins schema and OpenAI settings under `extensions.com.openai`; `mcp.json` with one remote server; no app references or hooks; no `test_credentials` or `reviewer_instructions`. | S2; S15 | Built |
| R9 | A verified developer identity, organization owner or `api.apps.write`, and a project with global data residency. | S2; S3 | Owner |
| R10 | Domain verification: the exact token as plain text at `https://<host>/.well-known/openai-apps-challenge`. | S2 Domain verification details; S4 | Built: host setting `http.openai_apps_challenge`. Token: owner and lead |
| R11 | A public HTTPS Streamable HTTP endpoint at a stable address, not local or a tunnel. | S3; S6 Deploy the endpoint | Met |
| R12 | Tool names unique, plain, ideally verbs; no promotional words, jargon or opaque identifiers. | S1 Clear and accurate tool names; S11 | Built: eight new names in the OpenAI presentation only |
| R13 | Every tool has a description that matches its behaviour and says when to use it, its limits and side effects. | S1 Descriptions that match behavior; S10 | Built |
| R14 | `readOnlyHint`, `destructiveHint` and `openWorldHint` as explicit booleans on every tool, with values that match behaviour. | S1 Correct annotation; S3; S4 `annotations_required`; S8 Annotations | Built: the live tools set no `openWorldHint` |
| R15 | A justification for each annotation, if the portal asks (S1 says no longer required; S4 lists `justification_required`). | S1; S4 | Built: the table below |
| R16 | Each operation its own tool; no discovery, operation selection or generic executor. | S1 Tool independence | Met |
| R17 | Minimal inputs: no conversation history, prior turns or raw location. | S1 Minimal and purpose-driven inputs | Met |
| R18 | Answers hold only what the request needs: no session, trace or request identifiers, timestamps, internal account identifiers or logs. | S1 Tool data handling; S3 Common rejection reasons | Built: projections; see the decision on the refusal reference |
| R19 | An output schema for every tool that returns structured content. | S8 Tool descriptor parameters | Built |
| R20 | Server instructions, the most important in the first 512 characters. | S6 Create the server | Built |
| R21 | Predictable behaviour: no hidden side effects, safe to retry or saying when not. | S1 Predictable, auditable behavior | Built: downloads count once per item version a month; a request for material is keyed by its text |
| R22 | Errors handled with clear messages. | S1 Quality and reliability | Met: typed refusals with message and next action |
| R23 | OAuth 2.1 by the MCP authorization specification: protected resource metadata naming the resource and issuer. | S5 | Met |
| R24 | Authorization server metadata with S256 in `code_challenge_methods_supported`, the token endpoint methods, and registration (DCR) or client ID metadata documents. | S5 | Met: DCR, method `none` |
| R25 | The `resource` echoed through authorization and token requests, tokens bound to it, and every request verified. | S5 | Met |
| R26 | The redirect ChatGPT uses: `https://chatgpt.com/connector/oauth/{callback_id}` without issuer advertisement, or `https://chatgpt.com/connector_platform_oauth_redirect` with it; the exact address the management page shows must be allowed. | S5 Redirect URL | Met for both; built: host setting `http.openai_oauth_redirect_uris` for any further exact address |
| R27 | 401 with `WWW-Authenticate` naming the resource metadata, per-tool `securitySchemes`, and `_meta["mcp/www_authenticate"]` on a tool's authentication refusal. | S5 Triggering authentication UI | Met for 401 and the refusal metadata; built: per-tool schemes |
| R28 | The registered client and its secret stay valid while the connection is used. | S5 Client registration | Met with a limit, see Limits |
| R29 | Requested permissions shown to the person, and only what the app needs. | S1 Authentication and permissions | Met: the consent page names the client, its destination and each scope in plain words |
| R30 | A view as `text/html;profile=mcp-app` linked by `_meta.ui.resourceUri`, a CSP with the exact domains, and a dedicated `_meta.ui.domain`, required when submitting a view. | S7; S8 Component resource fields; S3 | Built |
| R31 | The view works on desktop and phone, in light and dark, with system fonts, at most two primary actions per card, no nested scrolling, WCAG AA contrast. | S1 Testing; S14 | Built and measured at 706 and 390 pixels; ChatGPT's own rendering: owner |
| R32 | No embedded frames without a justification. | S1 Iframes | Met: the view embeds none |
| R33 | Commerce: nothing digital sold; no plans shown, no subscription started, no upgrade promoted, no link to a checkout or a page that starts one; a plan limit may be explained with a link to an informational page. | S1 Commerce and monetization; S13; S16 7.7 | Built: the plan refusal; `review.commerce` false |
| R34 | No advertising. | S1 Advertising | Met |
| R35 | A published privacy policy with the categories of personal data, purposes, recipients, retention timelines and user controls. | S1 Privacy policy | Partly met: retention of account, usage and connection records is not stated; a draft change waits for the owner |
| R36 | No restricted data (payment card, health, government identifiers, credentials); minimal collection. | S1 Data collection; S16 2.4 | Met; built: ChatGPT's hints are dropped from captured diagnostic bodies |
| R37 | Suitable for general audiences from 13; not aimed at minors under 13. | S1 Appropriateness | Met: a developer library |
| R38 | Usage policies, intellectual property and third-party terms. | S1 Usage policies, Third-party content; S17 | Met: every served item carries a licence from the host's licence allowlist and its source |
| R39 | Support contact details where people reach the developer. | S1 Support contact details | Built: `/support`; an email address needs inbound mail (lead) |
| R40 | No implied endorsement by OpenAI. | S1 Purpose and originality; S16 3.2 | Met |
| R41 | No wording that steers the model toward or away from other apps. | S1 Fair play | Built: held by the wording checks |
| R42 | Personal data processed under a notice shown before processing; security incidents reported to OpenAI. | S16 2.1, 2.3 | Met: sign-up shows the terms and the notice; incident reporting: owner |

## The live service before this work

Read on October 5, 2026 between 23:24 and 23:58 UTC with the official MCP
Python client 2.2.0, as the fresh account `baltor-check-2852a122@maxxspace.com`
made through Baltor's own sign-up (`tools/check_live_account_journeys.mjs
--fresh-only`), and with plain HTTP reads.

| Area | Observed | Gap |
|---|---|---|
| Discovery | Both protected resource addresses name `https://baltor.ai/mcp` and the issuer `https://baltor.ai`; the authorization server offers S256, DCR at `/register`, method `none`, code and refresh grants, revocation. An unauthenticated `initialize` is answered 401 with the resource metadata address. | None |
| OAuth | DCR, an S256 authorization request with the resource, sign-in on the consent page, explicit consent naming the client, its destination and three scopes, a callback with `code`, `state` and `iss`, the code exchange, refresh rotation and revocation all worked from a real browser. | None for the flow; no issuer advertisement or client ID metadata documents, both optional |
| Tools | Twelve tools: `provisioning_discover`, `_list`, `_manifest`, `_read`, `intelligence_search`, `public_good_files`, `provisioning_report`, `_rate`, `_request_material`, `feedback_review`, `staff_work_read`, `staff_work_submit`. | No `openWorldHint` and no title on any tool; no output schemas or OAuth schemes; three staff tools listed to a customer delegation; internal names; `provisioning_report` can withdraw a Community item yet said not destructive |
| Answers | `tenant_id` in discover, manifest and read answers; the Loop execution record (`loop_id`, `definition_digest`) in every answer; the meter record in reads. | Internal identifiers in answers |
| Refusals | A plan refusal names `get_started_url`, `account_url` and the founding offer; an effects refusal asks for a client header ChatGPT cannot send. | The commerce rule; a dead end in ChatGPT |
| View | `resources/list` answered "Method not found". | No view |
| Domain verification | `/.well-known/openai-apps-challenge` answered 404. | No route |
| Pages | `/privacy` and `/terms` served; `/support`, `/contact` and `/help` answered 404; no MX record exists for baltor.ai. | No support page or address |
| Delivery | Three files of a skill package and one Public Good file downloaded with their SHA-256 matching the published digests. | None |

## What was built

- The OpenAI host presentation in
  [`chatgpt_app.py`](../../src/loop_engine/core/service_runtime/chatgpt_app.py),
  served by a second protocol library server object behind the same
  transport in [`http.py`](../../src/loop_engine/core/service_runtime/http.py)
  (`_openai_sdk_server`). Both presentations call one dispatch,
  `_protocol_output`.
- The presentation follows the OAuth client:
  [`oauth_authorization.py`](../../src/loop_engine/core/service_runtime/oauth_authorization.py)
  names it from the registered redirects and
  [`http_auth.py`](../../src/loop_engine/core/service_runtime/http_auth.py)
  carries it on the request. It grants nothing.
- The view
  [`app_widgets/library.html`](../../src/loop_engine/core/service_runtime/app_widgets/library.html):
  result cards with a "Show files" action, a package with its files and
  digests, the folder Claude Code, Codex, OpenCode and Pi read a skill from,
  and a "Download files" action that asks in the conversation, so the person
  agrees to any declared effects there.
- Host settings in the `http` section of the host file:
  `openai_apps_challenge`, `openai_oauth_redirect_uris` and `support_email`.
- The support page `/support`
  ([`support_page.py`](../../src/loop_engine/core/service_runtime/support_page.py)),
  in the site map and the footer.
- Dynamic registration of a client that asks for the code grant alone.
- The package in [`integrations/chatgpt-app/`](../../integrations/chatgpt-app/README.md),
  its checker `tools/build_chatgpt_app_package.py`, the live proof
  `tools/check_chatgpt_app_live.py` with `tools/chatgpt_app_consent.mjs`, and
  the screenshot host `tools/capture_chatgpt_app_screens.mjs`.

## Tools of the OpenAI host presentation

| Tool | Calls | Read only | Destructive | Open world | Scope |
|---|---|---|---|---|---|
| `search_library` | `intelligence_search` | true | false | false | `provisioning:metadata` |
| `get_package` | `provisioning_manifest`, with the package's file list | true | false | false | `provisioning:metadata` |
| `download_package_files` | `provisioning_read` | false | false | false | `provisioning:read` |
| `find_public_good_files` | `public_good_files` | true | false | false | `provisioning:metadata` |
| `check_library_access` | `provisioning_discover` | true | false | false | `provisioning:metadata` |
| `rate_item` | `provisioning_rate` | false | true | false | `provisioning:metadata` |
| `request_material` | `provisioning_request_material` | false | false | false | `provisioning:metadata` |
| `report_item_problem` | `provisioning_report` | false | true | false | `provisioning:metadata` |

## Annotation justifications

For the portal, if it asks for one per value.

| Tool | Justification |
|---|---|
| `search_library` | Read only: it searches the library's metadata and changes nothing; it returns no file contents and is never counted. Not destructive: it writes nothing. Not open world: it reads Baltor's own catalogue, a bounded set of items, not the public web. |
| `get_package` | Read only: it reads one item's metadata and file list. Not destructive: it writes nothing. Not open world: Baltor's catalogue only. |
| `download_package_files` | Not read only: the first download of an item version in a calendar month writes one usage record on the account. Not destructive: that record is additive, repeating the download that month writes nothing, and nothing is deleted or overwritten. Not open world: it reads files from Baltor's own store. |
| `find_public_good_files` | Read only: it lists Public Good file metadata. Not destructive: it writes nothing. Not open world: Baltor's catalogue only. |
| `check_library_access` | Read only: it counts what the account can reach. Not destructive: it writes nothing. Not open world: the person's own account. |
| `rate_item` | Not read only: it stores a rating. Destructive: a later rating of the same item replaces the earlier one. Not open world: the rating stays with the account for Baltor staff and is never published. |
| `request_material` | Not read only: it stores a request for staff. Not destructive: it only adds, and the same text again records nothing new. Not open world: it reaches Baltor staff only. |
| `report_item_problem` | Not read only: it stores a report. Destructive: one report withdraws a Community item from the library for every account, and a second report from another account withdraws a Verified one. Not open world: it acts on Baltor's own catalogue. |

## Decisions

- **One endpoint, a presentation per client.** A second server would split
  authentication, limits and records. The presentation is chosen after
  authentication from the OAuth client's registered redirects, which only an
  OpenAI host can complete, or from a header any client may send, because a
  presentation grants nothing.
- **New tool names only for OpenAI hosts.** The directory rejects internal
  names, and harness clients (the Pi extension, client recipes) already call
  the `provisioning_*` names, so each presentation keeps its own.
- **Effects stay a person's choice.** An item may declare that its steps write
  files, run commands or use the network. ChatGPT cannot send the
  `Baltor-Step-Effects` header, so the download tool takes
  `authority_effects`, and its description and refusal tell the model to ask
  the person first. The tool is not read only, so ChatGPT shows its own
  confirmation with those arguments.
- **The refusal reference stays.** `request_reference` is the code a person
  quotes to support, and the operator finds the one failure record by it; that
  is the strict need S1 allows. Answers that succeed carry no identifier.
- **Not built yet:** client ID metadata documents, issuer advertisement for
  the stable redirect, an OpenID UserInfo endpoint for workspace domain
  restrictions, and a profile tool. Each is optional (S5); DCR and the
  callback-specific redirect already work, and each adds a provider surface
  that deserves its own review.
- **United States only at first.** The privacy notice is written for a United
  States operator and has no section for other jurisdictions; widening the
  countries is the owner's decision.
- **Screenshots from live answers.** They are made by the live check from the
  service's own answers and its served view, at the directory's exact width,
  so they show what a person sees and not a mock.

## Proof

| Check | Result on October 5, 2026 |
|---|---|
| `tools/test_chatgpt_app.py` | 19 tests: every tool against the directory rules and against eleven known-wrong descriptors; the kind words held to the catalogue's own; presentation selection and its known-wrong addresses; both protocol eras; search, package and exact file delivery; refusals; the plan and effects refusal wording; host hints dropped; a ChatGPT delegation reads the presentation and a loopback one does not |
| `tools/test_build_chatgpt_app_package.py` | 4 tests: the committed package passes; 29 known-wrong packages and five known-wrong files each fail; the archive is deterministic |
| Mutation controls | Removing the presentation choice, leaking `tenant_id`, keeping the harness plan refusal and a string annotation each fail an owning test |
| Owning tests on the release candidate | 374 tests in 19 modules, among them the OAuth, website site map, Public Good, customer delivery, feedback, transport and documentation modules |
| HTTP self-test | 744 checks, none failed |
| `tools/check_chatgpt_app_live.py` before the release | 23 of 23 checks on `https://baltor.ai` with `presentation_served` false: OAuth through a real browser, both eras, exact files, a Public Good file, refresh, revocation, screenshots from the packaged view |

After the release that serves this work, the same command with
`--expect-presentation --screens integrations/chatgpt-app/assets` must pass
with `presentation_served` true; it then remakes the screenshots from the view
the service serves.

## Steps for the release owner

1. Release the commits through the guarded workflow; no catalogue or host
   change is needed for the release itself.
2. Run the live proof above with a fresh account and keep its report with the
   release record.
3. When the owner has the portal's token, set `http.openai_apps_challenge` in
   the host file and restart; `curl https://baltor.ai/.well-known/openai-apps-challenge`
   must print exactly the token.
4. If the portal's management page shows a redirect address other than the two
   documented ChatGPT callbacks, add it to `http.openai_oauth_redirect_uris`.
5. Route mail for a support address (for example `support@baltor.ai` through
   the DNS provider's email routing to the owner's inbox), confirm a test
   message arrives, then set `http.support_email`; `/support` then shows it.
6. Make the reviewer account through Baltor's own sign-up with an address the
   owner reads, and grant it free monthly Baltor Pro from Administration.
7. Revoke the founding place of the check account
   `baltor-check-2852a122@maxxspace.com`, which the live check made on
   October 5 and which took one founding place.

## Steps for the owner

1. Verify the developer identity in the OpenAI Platform dashboard
   (https://platform.openai.com/settings/organization/general): individual
   verification to publish under your own name, business verification to
   publish as Baltor.AI. Use a project with global data residency.
2. Open https://platform.openai.com/plugins, choose **Upload new or existing
   plugin**, select the verified identity and upload the archive from
   `tools/build_chatgpt_app_package.py --zip`.
3. In **MCPs**, connect `https://baltor.ai/mcp` with OAuth, complete the domain
   verification with the token (the release owner serves it), sign in with the
   reviewer account, and run the tool scan.
4. In **Review details**, enter the reviewer account's address, password and
   the sign-in page `https://baltor.ai/login`.
5. Record the walkthrough video of the eight review cases in ChatGPT on the web
   and on a phone, and give its address.
6. Approve or change the drafted privacy notice change in
   [the notice change draft](../legal/CHATGPT-APP-NOTICE-CHANGES-DRAFT.md).
7. Submit for review, accept the attestations, and publish once approved.

## Limits

- The proof uses the official MCP client and a real browser on the live
  service, not ChatGPT itself. ChatGPT's own rendering, its model's choice of
  tools and the directory's review are seen only in ChatGPT.
- An OAuth grant lasts seven days from consent and is not extended by a
  refresh, so a ChatGPT connection asks the person to connect again after a
  week. OpenAI's daily scan of a published server uses its own connection in
  the same way.
- At the registered client ceiling (128), the service reclaims a client with
  no live grant after its first authorization lifetime. ChatGPT reuses one
  registered client per connection, so a connection unused for that long and
  then reclaimed answers `invalid_client` until it connects again.
