# Baltor privacy notice

Kind: privacy notice. Updated October 1, 2026 with the owner's approval of
voluntary submissions, uploads and data exchange for service operation and
improvement. Available features and account permissions determine which
operations a person or connected tool can use.

Operator: Baltor.AI, 1428 Bryn Mawr St, Saxton, PA 16678, United States.

## What Baltor is

Baltor supplies reusable material and tools and supports research, feedback,
testing and collaboration. It processes the inputs needed for the operations
you request. Browsing and downloading material do not give Baltor automatic
access to your computer, local files, prompts or model keys.

You or a tool acting with your permission may send messages, feedback,
research, source links, reports, files and other inputs through available
forms, uploads, APIs, command-line tools or connections. Baltor may receive,
read, store, organize, analyze and return that content to provide requested
features, respond to questions, investigate problems, evaluate quality and
improve its services and reusable materials. Send only content you have
permission to provide, and leave passwords, access keys and unrelated
personal information out of submissions.

Where an integration is available, it may exchange selected inputs and results
with the service or tool you connect, within the permissions you grant.
Private submissions do not become public library material just because they
were uploaded. Publication and reuse require the relevant permissions and
review. This notice does not grant access to an account, authorize executing
uploaded code or make every described interface available to every account.

## What the service stores

| Data | Why | Where |
|---|---|---|
| Your email address and password | To sign you in. The password is kept only by the identity provider, in hashed form. Baltor never stores or sees it after sign-up. | Supabase, United States |
| An account record that links your sign-in to your account | To know which material you may read | The service database on Fly, United States (`iad`) |
| A digest of each access key | To check a key without being able to show it again. The key itself is shown once and never stored. | The service database |
| One usage record for each downloaded item: the item name, its digest and the time | To show usage and reconcile access | The service database |
| Feedback, ratings, requests and other content you explicitly submit, together with the account, dates and version or request references needed to understand it | To respond, reproduce problems, identify missing material and improve the service | The service database on Fly, United States (`iad`) |
| Submitted reports and files, source links, replies, checksums and immutable revision records | To support collaboration, review, reliable retrieval and improvement work | The service database and private file storage on Fly, United States (`iad`) |
| Connection and consent records, client metadata, granted scopes, expiry information and token digests | To operate authorized connections, check their permissions and investigate access problems | The service database |
| A digest of a browser session that you signed out of, until it would have expired | To refuse that session afterwards | The service database |
| A waiting list entry, if you ask to join the list: your email address, an optional note of at most 280 characters, the state of the entry and its dates | To invite people in small groups | The service database |
| Diagnostic records of refused requests: a random reference, address path, reason code, account when known, time and service version; request content only when detailed capture is explicitly enabled | To find and fix problems. The default retains the latest 500 failures with metadata only; configured capture and retention limits apply. | The service database |
| Your payment details when you use an available billing feature | Stripe collects and keeps payment details. Baltor receives the customer identifier and subscription information needed to manage access. | Stripe |

The service keeps a count of refused sign-in attempts for each network
address in memory for a short time, to slow down guessing. It is not written
to disk. To stop one machine from flooding the waiting list, the service also
keeps the times of recent waiting list requests under a keyed one-way digest
of the sending network address, never the address itself, and removes them
once the one-hour counting window has passed.

The default diagnostic profile does not store request bodies or network
addresses. Explicitly enabled detailed diagnostics may retain supplied request
content for troubleshooting within the configured limits. That content can
include project or personal information present in a request. Diagnostic
records are restricted, not a public feed; do not rely on automatic removal
of every sensitive detail before submitting content.

## Access and data exchange

Access to private submissions follows the account and feature permissions.
Authorized service operators may review submissions for support, security,
quality evaluation and improvement. Content displayed in a private work log
is not an anonymous public feedback feed. Removing a name alone may not make
a report anonymous; public summaries need review for identifying details.

Hosting, identity and payment providers process the information needed to run
their respective parts of the service. Optional connected tools or model
providers may process content when that workflow is enabled and authorized;
their own terms and data practices also apply. Uploading a file by itself
does not trigger a model call or send it to an unrelated external service.
Baltor does not sell personal information. A connection or this notice does
not authorize unrelated advertising disclosure or unrestricted access to
other accounts.

## Browser and operational records

- It sets no cookies. When you sign in with your email address, the page
  keeps your sign-in in your browser tab's session storage until you close
  the tab or sign out, so reloading the page keeps you signed in. A key you
  enter on the sign-in page is kept only in the memory of the page.
- It runs no analytics, advertising or tracking scripts. Every script on the
  site is served from the site itself.
- It records the account, download, submission and connection events
  described above, rather than a general log of every successful request.
  Search-gap counts do not retain the search text. Refused requests use
  the diagnostic records described above.
- Email sent to you has open and click tracking switched off.

## Backups and deletion

The hosting provider keeps daily snapshots of the service database for five
days. Feedback, reports, uploaded files and their revision history currently
have no automatic expiry. They remain available for the purposes above until
an authorized removal; deleting a browser session or ending a connection does
not erase the records it created. Token expiry limits access, not the lifetime
of the associated registration or consent history.

To request deletion of your account or submitted content, write to the contact
address below and identify the relevant account or report. Requests are
handled by an operator; self-service deletion is not available. Removal must
account for stored copies, attachments and revision history, not just hide a
listing. Records needed for security, disputes or applicable legal obligations
may require separate retention. To leave the waiting list, ask
in the same way: the entry keeps only a one-way digest of the address and
the history of decisions, so the address itself is gone. Database snapshots
expire within the provider's five-day window.

## Contact

Baltor.AI, 1428 Bryn Mawr St, Saxton, PA 16678, United States.

Questions that contain no personal data can also go to the public issue
tracker of the repository. Do not post personal data in a public issue.

## Changes

This notice changes when the service changes what it stores. The history of
this file is the record of those changes. A revised notice does not by itself
authorize a materially different use of information collected under earlier
promises. Additional notice or consent is needed where applicable.
