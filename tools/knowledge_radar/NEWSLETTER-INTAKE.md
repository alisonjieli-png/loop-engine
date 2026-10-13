# Private newsletter intake

This adapter preserves one email's bytes and a managed receipt for private
research. Every accepted message stays quarantined. It does not subscribe to
newsletters, confirm subscriptions, follow links, call a model or publish
content. `newsletters@agentfeeds.si` is the exact selected recipient;
source code and local tests do not establish that the address receives mail.

The owner can use the local importer for an exported `.eml` file. A deployment
operator can use the email Worker to put incoming MIME bytes into a dedicated
private R2 bucket. The host reader lists receipt identities, displays a selected
message privately, or imports it into managed records. Neither route sends mail
or grants the sender task authority.

## Read mail and confirm subscriptions

The operator first verifies the dedicated bucket's account, private access and
Worker bindings. They then create an owner-only host file with mode `0600`:

```json
{
  "record_type": "newsletter_reader_binding/v1",
  "account_id": "00000000000000000000000000000000",
  "bucket": "private-newsletter-example"
}
```

Those are example identifiers, not provisioned resources. Use the values from
the operator's verified deployment receipt. The existing
`cloudflare-r2-management` credential reference supplies authentication from
the system keyring. Its recorded provider scope is account-wide administration;
the reader restricts itself to `GET` on the selected bucket. A deployment
should select a bucket-scoped read credential before an unattended reader is
enabled. The current command is a host-only operator tool, not a credential
for an agent or remote worker.

Inspect the command's plan, then list at most twenty receipt identities:

```bash
PYTHONPATH=src:tools python3 tools/read_newsletter_email.py list \
  --binding /private/newsletter-reader.json
PYTHONPATH=src:tools python3 tools/read_newsletter_email.py list \
  --binding /private/newsletter-reader.json \
  --execute --authorize-network-reads
```

The listing contains object identities and byte lengths, not message text.
When more results exist, repeat with `--after` set to the returned `next_after`.
The command never follows a cursor automatically. A missing provider pagination
flag remains unknown; it does not mean the mailbox is empty or fully listed.

To read one selected message, copy its exact receipt key:

```bash
PYTHONPATH=src:tools python3 tools/read_newsletter_email.py show \
  --binding /private/newsletter-reader.json \
  --receipt-key newsletter-email/v1/receipts/delivery-one.json \
  --execute --authorize-network-reads --show-private
```

The private view displays the claimed sender and subject, plain text, and up to
32 HTTPS links. It can extract a confirmation link from HTML-only mail without
rendering HTML, loading an image or running a script. Query tokens remain in
this private view because subscription confirmations need them. They do not
become research links or public feed data. Check the hostname and intended
action before opening a link yourself. A displayed link may unsubscribe,
confirm a subscription or perform another action; the tool does not decide
which action is safe.

The output is ASCII JSON with terminal control characters escaped. It may
contain private confirmation tokens. Keep it out of shared terminal recordings,
public reports and model prompts. Nothing opens a browser, follows a link or
confirms a subscription automatically.

Use `import` instead of `show`, with `--library /private/newsletter-records`
and `--authorize-local-writes`, to retain the message through the same managed
record path as a local export. Import prints a body-free acknowledgement.
The reader checks the receipt schema, exact raw length and SHA-256 before
either displaying or importing a message.

Each command permits at most three requests and three MiB of reserved response
bytes. A listing is limited to 64 KiB; a receipt to 4,096 bytes. Requests go to
the fixed Cloudflare API origin with redirects, proxies and compressed
responses disabled. A separate network process receives its credential over
standard input, with a 30-second parent deadline, 512 MiB address-space bound
and no inherited credential environment. A failed or unknown read stops that
session. No automatic polling or retry service is installed.

## Local use

Use the repository's supported Python environment. Keep the library outside
the repository in an owner-only directory. Supply the actual envelope sender
and receipt time; a `From` header is only a sender claim. Preserve the delivery
identity and timestamp when reconciling a repeated import.

```bash
PYTHONPATH=src:tools python3 tools/ingest_newsletter_email.py /private/input.eml \
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
to fetch them. Query-bearing URLs, literal IP addresses and private hostnames
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
email handler. It has no public HTTP handler, forwarding, reply, model or external
fetch operation. The deployment must bind `NEWSLETTER_QUARANTINE` to a
dedicated private R2 bucket and set `NEWSLETTER_RECIPIENT` to the exact address
above. No bucket name or credential is supplied here. The production entry is
[`cloudflare.mjs`](../../integrations/newsletter-email/cloudflare.mjs), which
also exports the internal `NewsletterAdmission` Durable Object class.

Bind `NEWSLETTER_ADMISSION` to a SQLite-backed `NewsletterAdmission`
namespace. Preserve that namespace and the fixed object name
`newsletter-admission-v1` across releases. The internal admission request is
`newsletter_admission/v1`; it binds the delivery identity, raw digest and byte
length. The Worker checks the matching `newsletter_admission_result/v1`
response before writing either R2 object.

Admission uses one durable transaction for the delivery reservation, UTC daily
counter and lifetime counter. It permits 100 messages per UTC day, at most
4,096 messages in total, and at most one GiB of cumulative reserved bytes.
Each reservation includes the raw message size plus 8,192 bytes for receipts
and accounting. Exact duplicate reservations do not charge again; conflicting
identities refuse. Failed and uncertain object writes do not refund their
reservations. The counters have no reset, expiry, deletion or refund endpoint.
Reaching a limit stops intake until an operator reviews capacity and retention.
Changing the namespace to evade a limit is not a recovery procedure.

The Worker caps both the declared MIME size and the bytes read from the
stream. It writes an immutable `newsletter-email/v1/raw/<sha256>` object, then
an immutable `newsletter-email/v1/receipts/<delivery-id>.json` receipt. A
receipt is never written before the raw write is confirmed. Conditional
duplicates are read and digest-checked; uncertain writes throw without retry.
The Worker does not use `Message-ID` as a unique delivery identity.

The host calls `import_private_receipt` with one exact receipt key and the
bounded authenticated `NewsletterR2Reader`. The `NewsletterObjectRead` request
names the bucket, key and byte limit. `read_private_receipt` performs the same
checks without local writes. Neither path is a new credential manager or an
already deployed R2 polling service.

The importer checks the closed receipt fields and exact raw digest before
writing locally. It never lists a bucket, follows a receipt-supplied URL,
changes an object or deletes remote mail. The optional `handle_signed` helper
verifies an exact HMAC-bound local transport envelope; no public HTTP route
uses it, and the R2 path does not need that helper or a new public webhook.

Before deployment, the operator must verify bucket ownership, public access
disabled, no public Worker binding or catalogue-serving path, scope of runtime
credentials, costs and retention. The admission counters bound accepted
storage, not the number or cost of rejected incoming Worker invocations.
Provider delivery and retry behavior, account billing and an actual
received-message journey require live qualification. No retention deletion or
provider setup runs from these files.

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
PYTHONPATH=src:tools python3 -m unittest tools.test_newsletter_intake -q
PYTHONPATH=src:tools python3 -m unittest tools.test_newsletter_reader -q
node --test tools/test_newsletter_worker.mjs tools/test_newsletter_quota.mjs
```

The checks use real managed records and the actual Worker source with a local
object-store fixture. One check imports that Worker's exact receipt into the
Python adapter. They cover wrong recipients, changed bytes, identity
conflicts, stale managed revisions, symlinks, FIFOs, MIME limits, spoofed
authentication headers, forbidden actions and uncertain storage outcomes.
These are offline controls, not proof of production email delivery or R2
service behavior.

`tools/check_newsletter_worker_native.mjs` accepts an installed Miniflare
module path and a new private output directory. It runs the actual Worker and
Durable Object classes in local `workerd`, checks concurrent admission against
SQLite storage, verifies exact R2 bytes, and reopens the same storage in a fresh
runtime. Its local receipt distinguishes these checks from SMTP delivery and
live provider storage. No remote deployment is part of that command.

The implementation uses Python's existing standard-library
[MIME parser](https://docs.python.org/3/library/email.parser.html) with an
explicit policy and bounded object factory. No new parser package is needed.
[Cloudflare's email handler](https://developers.cloudflare.com/email-service/api/route-emails/email-handler/)
provides raw MIME and the delivery envelope. Its
[R2 Worker interface](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/)
provides conditional writes and digest validation. Only those documented
interfaces informed the original adapter; no third-party implementation or
newsletter content is copied into the source.

The selected address uses the owned AgentFeeds apex domain. The operator
preflight found no existing MX records or mail routing on that domain. This
keeps the inbox on the documented
[zone DNS-enable API](https://developers.cloudflare.com/api/resources/email_routing/subresources/dns/methods/create/)
instead of depending on a subdomain onboarding operation whose current API
semantics have not been verified. Only the literal `newsletters` address routes
to this Worker; catch-all remains disabled. Preserve all existing web and
certificate records. A registered domain or source-level recipient constant
is not evidence that an address receives messages.

The reader uses the documented
[R2 object listing](https://developers.cloudflare.com/api/resources/r2/subresources/buckets/subresources/objects/methods/list/)
and [object reads](https://developers.cloudflare.com/api/resources/r2/subresources/buckets/subresources/objects/methods/get/).
It does not reuse the catalogue body's storage layout or expose a catalogue
download route. The admission adapter uses Cloudflare's
[durable transaction contract](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/#transaction).
SQLite-backed Durable Objects are offered on both Workers Free and Paid plans;
the [published pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/)
does not establish this account's current plan or remaining allowance.

[Resend receiving](https://resend.com/docs/dashboard/receiving/introduction)
is a possible alternative, but this implementation does not depend on Resend
access or alter authentication email delivery.
