# Customer-facing notices

Kind: notices for customers of the hosted service. Both notices are published.
The owner approved the privacy notice on September 22, 2026, with Baltor.AI as
the operator and a postal contact address, and the website serves it at
`/privacy`. The owner approved the terms of service on September 23, 2026, in
their words "I have approved the terms", and the website serves them at
`/terms`. Neither document is legal advice.

| Document | State |
|---|---|
| [Privacy notice](PRIVACY-NOTICE.md) | Published. Approved by the owner on September 22, 2026. The website serves the same text at `/privacy`, linked from the footer of every page. |
| [Terms of service](TERMS-OF-SERVICE.md) | Published. Approved by the owner on September 23, 2026. The website serves the same text at `/terms`, linked from the footer of every page and from the sentence above the button that creates an account. Last changed: September 23, 2026. |
| [Beta terms draft](BETA-TERMS-DRAFT.md) | History. The draft that engineering wrote and the owner read and approved. It keeps its original words and is not the published text. |

## The published terms and the approved draft

The published terms are the nine numbered sections of the draft, word for
word, with these changes and no others:

- the title "Baltor terms of service";
- the operator line, naming Baltor.AI and the postal address the owner
  approved for the privacy notice on September 22, 2026;
- the line "Last changed: September 23, 2026", because section 9 promises that
  the date of the last change is shown with the terms;
- section 6 in the present tense, because the price is live: the draft's
  "Planned:" is gone;
- a closing line that links the privacy notice.

The draft's own kind line and its closing note to the owner are not part of
the published text. The note said that the governing law is not yet stated.
No governing law clause was added, because the owner has not seen one.

The approved words say beta twice, in sections 2 and 6. The website's style
rule retires that word from the pages a customer reads, and the owner's
approval of these exact words came later. A published legal text keeps the
words the owner approved, so the browser checks that read customer pages for
the retired words leave out the terms, and only while the served terms equal
this file word for word. A new wording of those sections is a change to the
terms and needs the owner's approval.

The terms live in two places: [TERMS-OF-SERVICE.md](TERMS-OF-SERVICE.md), the
approved text word for word, and the `terms` view of
`src/loop_engine/core/service_runtime/web_assets/index.html`, which renders
the same text as plain HTML. The browser check
`terms_of_service_says_the_same_words_as_the_approved_text` in
`tools/check_service_workspace.mjs` reads the Markdown file and fails when the
served page says anything else. The published terms change only with the
owner's approval, and every change moves the date on the line
"Last changed".

The privacy notice lives in two places: [PRIVACY-NOTICE.md](PRIVACY-NOTICE.md),
the approved text word for word, and the `privacy` view of
`src/loop_engine/core/service_runtime/web_assets/index.html`, which renders
the same text as plain HTML. The browser check
`privacy_notice_says_the_same_words_as_the_approved_text` in
`tools/check_service_workspace.mjs` reads the Markdown file and fails when the
served page says anything else.

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
