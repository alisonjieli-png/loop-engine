# Draft changes to the privacy notice for the Baltor app in ChatGPT

Kind: draft for the owner. Nothing here is published. The served notice at
`/privacy`, [PRIVACY-NOTICE.md](PRIVACY-NOTICE.md) and the terms stay exactly
as the owner approved them until the owner approves a change in their own
words. Engineering prepared this on October 5, 2026 for the ChatGPT app work
described in [the ChatGPT app guide](../guides/chatgpt-app.md).

## Why a change is proposed

OpenAI's plugin guidelines, read on October 5, 2026, require a published
privacy policy that states, at minimum, "the categories of personal data
collected, the purposes of use, the categories of recipients, data retention
timelines, and any controls offered to your users"
(<https://developers.openai.com/plugins/plugin-guidelines>, section Privacy
policy). The approved notice already states the categories, the purposes, the
recipients and the controls. Two things are missing or only implied:

1. **Retention timelines** for the account record, the usage records and the
   connection and consent records. The notice states the five-day snapshots,
   the latest 500 diagnostic records and that submissions have no automatic
   expiry, but says nothing about how long the other records are kept.
2. **OpenAI as a recipient.** When a person connects Baltor to ChatGPT or
   Codex, the answers the app returns enter that person's conversation, where
   OpenAI processes them under its own terms. The notice covers this only in
   general words ("an integration ... may exchange selected inputs and
   results").

The directory also asks for support contact details. The notice names only a
postal address; the new `/support` page names the same address and the public
issue tracker, and will name an email address once mail to it is delivered.

Each change below states only what the service does today. Nothing is
promised that the code does not do.

## Change 1: add a section after "Backups and deletion"

Proposed new section, inserted before "Contact":

> ## How long records are kept
>
> | Record | Kept |
> |---|---|
> | The account record, its usage records and its access key digests | While the account exists. They have no automatic expiry and are removed when an operator completes a request to delete the account, apart from records needed for security, disputes or legal obligations. |
> | Connection and consent records, client metadata and token digests | While the account exists. An access token works for at most 15 minutes and a connection for at most seven days after consent; the records stay after they expire, as the section above says. |
> | Feedback, reports, requests and uploaded files | As the section above says: no automatic expiry, until an authorized removal. |
> | Diagnostic records of refused requests | The latest 500, unless the operator configures another limit. |
> | A signed-out browser session's digest | Until the session would have expired. |
> | Database snapshots | Five days, by the hosting provider. |

## Change 2: add a paragraph to "Access and data exchange"

Proposed new paragraph, after the paragraph that begins "Hosting, identity and
payment providers":

> When you connect Baltor to ChatGPT or Codex, you sign in to Baltor and allow
> the access the consent page lists. ChatGPT or Codex then sends Baltor the
> requests you or its model make (a search, a package to show, files to
> download, feedback you choose to send) and receives Baltor's answers, which
> become part of your conversation. OpenAI processes that conversation under
> its own terms and privacy policy. ChatGPT also sends hints with each request,
> such as a coarse location, a language setting and anonymous identifiers;
> Baltor does not use them and does not keep them. Remove Baltor in ChatGPT's
> settings to disconnect it.

The last two sentences describe the service from the release that carries
this work: it drops those hints from any request content it keeps for
diagnostics (`chatgpt_app.without_host_hints`).

## Change 3: the contact section

Proposed text for "Contact", once mail to a support address is delivered and
the address is set as `http.support_email`:

> Baltor.AI, 1428 Bryn Mawr St, Saxton, PA 16678, United States, or by email
> at <support@baltor.ai>. The support page, <https://baltor.ai/support>, lists
> every way to reach Baltor.
>
> Questions that contain no personal data can also go to the public issue
> tracker of the repository. Do not post personal data in a public issue.

Until that address works, only the second sentence of the first paragraph
changes: "The support page, <https://baltor.ai/support>, lists every way to
reach Baltor."

## Not needed by the directory, for the owner's consideration

Section 1 of the terms says "Baltor gives your tools access to reviewed
material over the internet." The website's wording rules no longer call
library items reviewed on customer pages; the owner may choose "Baltor gives
your tools access to material over the internet." This is not required for
the ChatGPT app and is listed only because the same review read the terms.

## What changes when the owner approves

The owner's approval in their own words updates
[PRIVACY-NOTICE.md](PRIVACY-NOTICE.md), the `privacy` view of
`src/loop_engine/core/service_runtime/web_assets/index.html` with the same
words, the "Updated" line, and [the legal folder index](README.md). The
browser check that compares the served notice with the approved file then
holds the new text.
