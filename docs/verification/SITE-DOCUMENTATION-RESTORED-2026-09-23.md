# Customer documentation restored and checked

Kind: dated implementation and verification handoff for the restored documentation pages.

## Scope and base

The detached `site-docs` worktree starts at
`9d255944705505d2118efda21327a42f33cb5d72`. It restores the preserved
`site-docs-bc6d44f2.patch`, then completes its seven customer guides, six served
bodies, index, rendering and checks. No commit, push, deployment, production
mutation, model call or intelligence approval was made in this lane.

The old [site documentation handoff](HANDOFF-SITE-DOCS-2026-09-23.md) remains
historical. This record supersedes its unfinished documentation items for this
candidate. It does not supersede the root session's release work or roadmap.

## What changed

- The index has four sections and seven entries. Get set up comes first and
  opens the existing setup guide. Six other pages have explicit routes.
- Each guide distinguishes the hosted library from the local engine and the
  design of a fresh harness for each focused step. Format support, published
  inventory, retrieval, loading, use and accepted work are separate facts.
- Account, usage, selection, package download and protocol explanations follow
  current source. The usage guide includes item rows, null metering fields,
  uncertain commits and request identities that must not be reused across items.
- The package example binds the selected parent digest. Reusable packages do
  not silently supply the current step assignment; the guide explains explicit
  task/context loading and that `node_context.md` is not a universal convention.
- The renderer validates a closed index shape and rebuilds a restricted HTML
  tree. Bad addresses, versions, fields, identities, aliases, dates and markup
  refuse the whole affected index or body. Dynamic reads use `no-store`.
- The builder rejects duplicate JSON members, invalid source paths and shapes
  the browser cannot render. Source and body digests bind the generated files.
- The index checker reads the customer table and served route table, follows
  alias views, checks source facts, freshness and terminology. It does not infer
  customer pages from file names.
- Desktop pages have navigation and contents beside the article. Phone contents
  can expand; tables and examples scroll inside their own frames.

## Evidence

All evidence is under
[`artifacts/site-docs-restoration-2026-09-23`](../../artifacts/site-docs-restoration-2026-09-23/).
Reports keep earlier failed attempts beside their successors.

| Check | Result | Evidence |
| --- | --- | --- |
| Current guide facts and index agreement | 416 facts, no findings, seven pages | `index-frozen-check.json` |
| Python documentation checks | 37 passed | `python-docs-tests-final.txt` |
| Existing workspace browser suite | 548 passed; 91 of 91 mutants detected | `full-workspace-browser.json` |
| Documentation browser suite | 81 passed | `browser-frozen.json` |
| Documentation guard controls | Seven removed guards detected | `documentation-guard-controls-final.json` |
| Ruff on the five Python tools/tests | Passed | `ruff-frozen.txt` |
| Markdown structure | 11 files, no issues | `markdown-final.txt` |
| Generated bodies | Fresh | `build-freshness-final.txt` |

The dedicated browser run uses a real loopback service, tests the exact index
and six body bytes, direct routes, cards, back navigation, the setup alias,
malformed data, removed version/head/element guards, and text contrast in light
and dark appearances. It uses a document-memory sentinel to check navigation
without a reload; it does not use a real customer account or prove external
identity-provider behavior.

Every index/page was inspected at 1440 and 390 pixels. The index is 1760 pixels
high on desktop. All six desktop pages show their title, short summary and
contents in the first screen. No page overflows horizontally on a phone.
The first-screen screenshots and full page heights are recorded in the browser
report. The initial phone screenshot exposed broken table words and an unclear
contents affordance; the successor adds an internal table width and a disclosure
indicator. The phone tables remain horizontally scrollable, not compressed into
single-letter columns.

An independent semantic read by `interop_standards` found no material capability
overclaim in the seven guides. Its recommendation to add `expected_digest` to
the package-file example was applied, as was its task-assignment clarification.
This is a documentation review, not approval of any intelligence candidate.

Public capabilities were fetched without credentials and saved in
`public-capabilities.json`. The primary protocol references consulted are the
[2025-11-25 lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
and [2026-07-28 specification](https://modelcontextprotocol.io/specification/2026-07-28).
A capability response does not prove a native-client task completed.

## Confirmed follow-up: search effect authority

Named desired scenario: `search_can_select_an_authorized_effectful_item`.

The local fixture registers one approved, granted item whose declared effect is
`spawns_process`. The three observations in
`search-effect-authority-gap-v3.json` are:

1. A lexical retrieval request for its unique purpose returns HTTP 200 and no hits.
2. The same request with `authority_effects` returns HTTP 400,
   `unknown_request_field`.
3. A provisioning list with `authority_effects: ["spawns_process"]` returns the
   exact item and its approved reference.

The cause is `ServiceHttpApplication._search`: its authorization callback invokes
`LIST_OPERATION` without effect selection. `_retrieval_arguments` rejects an
`authority_effects` field. The provisioning list supports that selection.
The current customer guides describe this boundary and the explicit-list path.
Selection still grants no authority to execute downloaded material.

Owner: the root session, for the core retrieval/provisioning boundary follow-up
in S-6.40/S-6.44. This lane changes no core search behavior. The first two saved
attempts used an incorrect endpoint/request shape; they are fixture mistakes,
not product findings. Only the corrected v3 comparison supports the finding.

## Integration instructions

Apply the prepared candidate patch to the integration tree and retain the root
release's cache, asset versioning, HEAD behavior and badge changes. This patch
only adds documentation rows to `web_pages.py`, a docs region to `index.html`,
and docs routing to `service.js`; it does not replace the root's release work.
The older base still maps Get started to its waiting-list view; preserve any
newer funnel mapping during integration.

The only changes to the large existing browser checkers are additive docs asset,
layout and retired-word coverage. Preserve their newer version-aware URL
interceptors and badge checks. The 548 count above belongs to this base; the root
release's 551 count includes its additional guards.

Rebuild the records index after all lanes are combined. Run the new documentation
checker and browser suite along with the full required integration checks. The
browser tool supports a read-only live origin as its second argument; run it on
every deployed hostname after a release. This candidate has not been deployed,
and the source-fact checks are not a proof of every semantic statement.
