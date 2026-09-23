# Customer-facing notices

Kind: notices for customers of the hosted service. The privacy notice is
published. The owner approved it on September 22, 2026, with Baltor.AI as the
operator and a postal contact address, and the website serves it at
`/privacy`. The beta terms are a draft written by engineering. The owner has
not approved them, they are not published, and they are not in force. Neither
document is legal advice.

| Document | State |
|---|---|
| [Privacy notice](PRIVACY-NOTICE.md) | Published. Approved by the owner on September 22, 2026. The website serves the same text at `/privacy`, linked from the footer of every page. |
| [Beta terms](BETA-TERMS-DRAFT.md) | Draft. Not approved and not published. |

The privacy notice lives in two places: this Markdown file, which is the
approved text word for word, and the `privacy` view of
`src/loop_engine/core/service_runtime/web_assets/index.html`, which renders
the same text as plain HTML. The browser check
`privacy_notice_says_the_same_words_as_the_approved_text` in
`tools/check_service_workspace.mjs` reads this file and fails when the served
page says anything else.

When the service changes what it stores, change the privacy notice and the
served page in the same commit. The published text changes only with the
owner's approval.

## Time limits in the notice and what keeps them

Three sentences of the notice promise that something is removed. Each one is
kept by code and held by named checks, so a change that breaks a promise fails
a check before it can reach the service.

| Promise | Kept by | Held by |
|---|---|---|
| A digest of a signed-out browser session is kept until it would have expired | `retention.py` removes it after every sign-out, from a periodic task and through `loop-engine service remove-expired`, never before the session expires | `retention_checks.py` and `browser_identity_checks.py` |
| Waiting list request times are removed once the one-hour window has passed | `waitlist.py` on every request to join, and the same periodic task when nobody joins | `waitlist_source_checks.py` |
| The last 500 refused-request records are kept and older ones are removed | the bounded ring of `observability.py` | `observability_checks.py` |

The checks live in `src/loop_engine/core/service_runtime`.
