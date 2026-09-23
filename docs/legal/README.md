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
