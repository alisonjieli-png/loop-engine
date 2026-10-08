# Customer-facing notices

Kind: notices for customers of the hosted service. Both notices are published.
The owner approved the privacy notice on September 22, 2026, with Baltor.AI as
the operator and a postal contact address, and the website serves it at
`/privacy`. The owner approved the terms of service on September 23, 2026, in
their words "I have approved the terms", and the website serves them at
`/terms`. Neither document is legal advice.

The same evening the owner told engineering to amend them: "you can fix the
terms of service". Section 2 is now "Availability" and no longer calls the
service a beta, and section 6 now states the price as "$29 a month" without the
sentences about free search and invited beta users. The meaning of both
sections is otherwise unchanged.

On October 8, 2026, the owner approved a flexible pricing clause: "Update the
terms to be more flexible so we can have more pricing changes in the future".
Section 6 now refers to the plan price, currency, billing interval and taxes
shown before subscription instead of fixing one plan at one dollar amount.
It permits prospective changes, protects paid periods, requires advance
notice and any legally required consent for changes to existing subscription
prices, preserves cancellation, and requires explicit opt-in from free access.
Changing the terms alone changes no subscription price. Sections 1–5 and 7–9,
the operator and the privacy notice are unchanged. The last-changed date is
October 8, 2026; verify the current deployment before treating this edit as live.

| Document | State |
|---|---|
| [Privacy notice](PRIVACY-NOTICE.md) | Published. Approved by the owner on September 22, 2026. The website serves the same text at `/privacy`, linked from the footer of every page. |
| [Terms of service](TERMS-OF-SERVICE.md) | Owner-approved text, including the October 8 flexible pricing amendment. The website must serve the same text at `/terms`, linked from every footer and signup. Last changed: October 8, 2026. |
| [Beta terms draft](BETA-TERMS-DRAFT.md) | History. The draft that engineering wrote and the owner read and approved. It keeps its original words and is not the published text. |

## The published terms and the approved draft

The published terms retain the draft's nine-section structure, with these
recorded changes:

- the title "Baltor terms of service";
- the operator line, naming Baltor.AI and the postal address the owner
  approved for the privacy notice on September 22, 2026;
- the current "Last changed" line, because section 9 promises that
  the date of the last change is shown with the terms;
- the September 23 Availability wording and removal of the draft's invitation
  language, as recorded above;
- the October 8 flexible pricing clause in section 6;
- a closing line that links the privacy notice.

The draft's own kind line and its closing note to the owner are not part of
the published text. The note said that the governing law is not yet stated.
No governing law clause was added, because the owner has not seen one.

The historical draft says beta in sections 2 and 6. The later amendments are
recorded above; the draft itself keeps its original bytes. A legal text keeps the
words the owner approved, so the browser checks that read customer pages for
the retired words leave out the terms, and only while the served terms equal
[TERMS-OF-SERVICE.md](TERMS-OF-SERVICE.md) word for word. A new wording of
those sections is a change to the terms and needs the owner's approval.

The terms live in two places: [TERMS-OF-SERVICE.md](TERMS-OF-SERVICE.md), the
approved text word for word, and the `terms` view of
`src/loop_engine/core/service_runtime/web_assets/index.html`, which renders
the same text as plain HTML. The browser check
`terms_of_service_says_the_same_words_as_the_approved_text` in
`tools/check_service_workspace.mjs` reads the Markdown file and fails when the
served page says anything else. The published terms change only with the
owner's approval, and every change moves the date on the line
"Last changed".

The October 8 check also protects the absence of a hard-coded price, paid
period protection, notice, consent and cancellation. Those words are not a
substitute for applying jurisdiction-specific requirements. The
[FTC subscription guidance](https://www.ftc.gov/news-events/news/press-releases/2021/10/ftc-ramp-enforcement-against-illegal-dark-patterns-trick-or-trap-consumers-subscriptions)
supports clear material terms, informed consent and straightforward cancellation.
The [current rule page](https://www.ftc.gov/legal-library/browse/rules/negative-option-rule)
records further rulemaking in 2026; this amendment does not rely on the vacated
2024 rule as a current nationwide compliance assurance.

For a later price activation, use a new Stripe Price and retain existing
subscription bindings unless a separately authorized migration is intended.
[Stripe's price documentation](https://docs.stripe.com/products-prices/manage-prices)
states that an existing Price amount is not editable. No subscription was
changed by this legal-text edit.

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
