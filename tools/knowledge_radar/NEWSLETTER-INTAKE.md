# Private newsletter intake

This adapter preserves one email's bytes and a managed receipt for private
research. Every accepted message stays quarantined. It does not subscribe to
newsletters, confirm subscriptions, follow links, call a model or publish
content. `newsletters@inbox.agentfeeds.si` is the exact proposed recipient;
source code and local tests do not establish that the address receives mail.

The owner can use the local importer for an exported `.eml` file. A deployment
operator can use the email Worker to put incoming MIME bytes into a dedicated
private R2 bucket, then import named receipts through an authenticated host
reader. Neither route sends mail or grants the sender task authority.

## Local use

Use the repository's supported Python environment. Keep the library outside
the repository in an owner-only directory. Supply the actual envelope sender
and receipt time; a `From` header is only a sender claim. Preserve the delivery
identity and timestamp when reconciling a repeated import.

```bash
PYTHONPATH=src:tools python tools/ingest_newsletter_email.py /private/input.eml \
  --library /private/newsletter-records \
  --delivery-id owner-export-001 \
  --envelope-sender newsletter@example.org \
  --received-at 2026-10-13T23:00:00Z
```

Without `--authorize-local-writes`, the command inspects the input and prints
counts and a digest. It creates no library. Add that flag to retain exact raw
bytes and a private managed receipt. The printed acknowledgement contains a
record identity, version and digest, not the email's body or subject.

Identical delivery envelopes return the existing record. Different delivery
identities retain separate receipts but share identical raw bytes. A reused
delivery identity with different metadata or bytes refuses. Dismissal remains
unchanged when a message arrives again.

An uncertain record commit returns no success. Inspect the managed record
before repeating that operation. An artifact written before a failed record
commit remains available for reconciliation; this tool does not delete it.
Missing or changed artifact bytes also refuse an acknowledgement.

## Boundaries and limits

`NewsletterEmail` carries the versioned `newsletter_email/v1` envelope. Its
raw bytes, recipient, envelope sender, receipt time and ingress identity are
immutable inputs. Raw MIME is limited to 2 MiB. The parser limits the initial
header block to 64 KiB, allocates at most 32 MIME message objects, and rejects
nesting deeper than eight parts.

Only plain text gets a private preview, at most 4,096 characters. HTML,
embedded messages and attachments stay in the raw artifact. The parser does
not render markup or load remote images. It records at most ten query-free
HTTPS references; these are candidates for later research, not instructions
to fetch them. Token-bearing URLs, literal IP addresses and private hostnames
are excluded by the existing URL guard. The original bytes remain unchanged.

An `Authentication-Results` header cannot authenticate itself. The adapter
records whether that header exists but always sets sender authentication to
`not_verified`. A verified ingress signature or authenticated object-store
read establishes transport provenance only. Neither proves that a sender is
the publisher, that a claim is true, or that redistribution is allowed.

The local directory must be owned by the current user with no group or other
access. Existing symlink paths refuse. The host directory is trusted against
concurrent same-user filesystem changes; this is not a sandbox for hostile
local processes. The local file reader rejects a final symlink, hardlink,
FIFO or other non-regular input.

## Email Worker and private storage

[`worker.mjs`](../../integrations/newsletter-email/worker.mjs) exports only an
email handler. It has no HTTP handler, forwarding, reply, model or external
fetch operation. The deployment must bind `NEWSLETTER_QUARANTINE` to a
dedicated private R2 bucket and set `NEWSLETTER_RECIPIENT` to the exact address
above. No bucket name, credential or deploy configuration is supplied here.

The Worker caps both the declared MIME size and the bytes read from the
stream. It writes an immutable `newsletter-email/v1/raw/<sha256>` object, then
an immutable `newsletter-email/v1/receipts/<delivery-id>.json` receipt. A
receipt is never written before the raw write is confirmed. Conditional
duplicates are read and digest-checked; uncertain writes throw without retry.
The Worker does not use `Message-ID` as a unique delivery identity.

The host calls `import_private_receipt` with one exact receipt key, a selected
bucket and a bounded authenticated reader. The `NewsletterObjectRead` request
names the bucket, key and byte limit. The host must enforce those limits while
streaming, bind its account and bucket, refuse redirects, and avoid automatic
retry of an unknown outcome. This repository provides the import seam, not a
new credential manager or an already deployed R2 polling service.

The importer checks the closed receipt fields and exact raw digest before
writing locally. It never lists a bucket, follows a receipt-supplied URL,
changes an object or deletes remote mail. The optional `handle_signed` helper
verifies an exact HMAC-bound local transport envelope; no public HTTP route
uses it, and the R2 path does not need that helper or a new public webhook.

Before deployment, the operator must verify bucket ownership, public access
disabled, no public Worker binding or catalogue-serving path, scope of runtime
credentials, costs, retention and an aggregate admission budget. Per-message
limits do not bound total storage under sustained mail. Provider delivery and
retry behavior, quota controls and an actual received-message journey remain
unqualified. No retention deletion or provider setup runs from these files.

## Existing owners and research admission

`CommunityStore` owns private `email_receipt` documents through
`RecordOperationService`, its schema and compare-and-swap checks. Raw bytes
use `ContextArtifactStore` in `newsletter-quarantine`; they do not become
catalogue bodies. This reuses the `record_store` engine owner and the existing
deterministic intake work under `step_executor`, not another runtime or store.

The public `knowledge_radar_source/v1` observation edge and the planned
`library_ingestion_source` slot have different purposes. This private adapter
does not install itself in either public source registry. In particular, the
planned library source protocol is not a verified private-mail reader.

The current `community_work` queue requires public-link lead data. Raw email
cannot be placed into that queue with an invented public URL. This increment
therefore records private receipts but admits no research activation. A later
private-source review must establish source authenticity and select a bounded
research task through the existing scheduler. Corroborated public links can
then enter the existing lead path without disclosing the newsletter body.
Intake, research admission, execution, approval and publication remain separate.

## Checks and source research

```bash
PYTHONPATH=src:tools python -m unittest tools.test_newsletter_intake -q
node --test tools/test_newsletter_worker.mjs
```

The checks use real managed records and the actual Worker source with a local
object-store fixture. One check imports that Worker's exact receipt into the
Python adapter. They cover wrong recipients, changed bytes, identity
conflicts, stale managed revisions, symlinks, FIFOs, MIME limits, spoofed
authentication headers, forbidden actions and uncertain storage outcomes.
These are offline controls, not proof of production email delivery or R2
service behavior.

The implementation uses Python's existing standard-library
[MIME parser](https://docs.python.org/3/library/email.parser.html) with an
explicit policy and bounded object factory. No new parser package is needed.
[Cloudflare's email handler](https://developers.cloudflare.com/email-service/api/route-emails/email-handler/)
provides raw MIME and the delivery envelope. Its
[R2 Worker interface](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/)
provides conditional writes and digest validation. Only those documented
interfaces informed the original adapter; no third-party implementation or
newsletter content is copied into the source.

[Cloudflare's subdomain documentation](https://developers.cloudflare.com/email-service/configuration/subdomains/)
supports a literal address on a subdomain. Subdomain catch-all routing is not
used. [Resend receiving](https://resend.com/docs/dashboard/receiving/introduction)
is a possible alternative, but this implementation does not depend on Resend
access or alter authentication email delivery.
