# Waiting list and invitations

Kind: operating guide for engineering. Written on September 21, 2026, against
the source in this revision. Updated on September 22, 2026, when the flood
guard stopped storing network addresses.

Anyone can leave an email address and a short note. An operator reads the
list and decides. An approved person receives one invitation that carries a
sign-in link and a discount code the payment account already holds. This is a
technical document, so it uses the exact runtime terms. The public page does
not show them.

## What each part owns

```text
waiting list
├── Get started page /connect      the form leads it; /waitlist opens it
├── POST /api/v1/waitlist          public, no sign-in, four typed refusals
├── ServiceWaitlist                the typed versioned record and its states
├── GET, POST /api/v1/admin/waitlist   operator listing and one decision
├── tools/waitlist_operator.py     read the list, invite one entry, erase one entry
└── tools/setup_stripe_sandbox.py  the coupon and its promotion code
```

The record lives in the existing service collection, in the host namespace,
written through the same atomic batch contract as every other service record.
There is no second store.

## The five states

```text
waiting ──invite──▶ invited ──record_join──▶ joined
   │                   │
   │                   └──record_delivery──▶ invited (delivery only)
   └──decline──▶ declined ◀──decline── invited

waiting ───forget──▶ removed ◀──forget─── invited
                        ▲
declined ───forget──────┘
```

No other transition is applied. A decision carries its own request identity:
repeating it returns the first result and writes nothing, and the same
identity with different content is refused rather than replayed.

`forget` is how the service takes an address off the list. It erases the
address and the note from the entry, leaving the one-way digest of the
address and the decision history. It does not change the flood guard's count
for the source, which ends with its window. Nothing recovers the erased
values, and no row is rewritten by hand:
the erasure is an ordinary versioned decision through the same contract as
every other one. An entry in the joined state is not removed this way,
because that address belongs to an account. The same person may ask again
afterwards, and the new request replaces the removed entry.

## The four refusals

| Code | When | HTTP |
|---|---|---|
| `waitlist_address_invalid` | the address is not one the service can write to | 400 |
| `waitlist_address_already_listed` | this address is on the list already | 409 |
| `waitlist_address_has_account` | this address already has an account | 409 |
| `waitlist_source_flooded` | one source sent too many inside the window | 429 |

Each refusal has a check and a known-wrong case in
`src/loop_engine/core/service_runtime/waitlist_checks.py`. The known-wrong
case removes that one guard and shows the behaviour the guard exists to
prevent.

Two more codes are states of the service rather than refusals of the person:
`waitlist_source_secret_unavailable` and `waitlist_source_secret_unusable`,
both 503. They answer when the host names a source secret that the service
cannot read, or one too short to use, and nothing is written. The section on
what the flood guard keeps says why the service refuses instead of counting
in a weaker way.

The service holds no account addresses, so a host that can ask its identity
provider installs a `WaitlistAccountDirectory`. An answer that is not a plain
yes or no refuses the request instead of admitting an address the directory
was meant to exclude. Without a directory, only an address whose own entry
reached the joined state is known to have an account.

The flood guard counts accepted entries for one source inside a window. It
does not count refused attempts: the transport's failed-attempt limit for
each client address already counts those. It counts only when the host has
declared where the client address comes from, because behind a proxy every
caller would otherwise look like one source, and only when the host names the
secret that keys the source digest.

## What the flood guard keeps about an address

The published privacy notice says the service keeps the times of recent
waiting list requests under a keyed one-way digest of the sending network
address, never the address itself, and removes them once the one-hour
counting window has passed. The source record is built to that sentence:

```text
service_waitlist_source/v2
├── name     HMAC-SHA256 of the source key under the host secret; never the
│            address, and never a digest anyone could recompute from a guess
├── fields   record_type, accepted (times inside the window), window_seconds
│            and nothing else; a record with any other field is refused
└── removal  every request to join removes the times that have left the
             window from every source record, counted or not; a record with
             no time left keeps its version and an empty list
```

An unkeyed digest of a network address protects nothing, because every IPv4
address can be hashed in minutes and a guess confirms itself. That is why the
first version of this record, which was named by the address itself and kept
a plain digest beside it, is refused by the reader: this release never counts
or rewrites it. No deployment ever held one, because the waiting list was
never switched on.

The emptied record stays because the catalogue store has no removal
operation. Its name is the keyed digest, so without the host secret it cannot
be linked to any address, and it holds no time. The window is at most one
hour: a host file that sets `source_window_seconds` above 3600 is refused,
because a longer window would keep the times of an address past the period
the notice promises.

The secret is named in the host's `waitlist` block as an environment
reference, the same form as every other host secret:

| Setting | Default | Meaning |
|---|---|---|
| `source_secret_ref` | empty | `env:NAME` of the secret that keys the source digest. Empty means no count is taken and nothing about the address is stored. |
| `source_window_seconds` | 3600 | The counting window, from 60 to 3600 seconds. |
| `accepted_for_each_source` | 5 | Accepted entries one source may leave inside the window. |

What each state of the secret does:

| The host | Each accepted entry records | What is stored about the address |
|---|---|---|
| declares no address source | `no_declared_source` | nothing |
| declares a source and names no secret | `no_source_secret` | nothing |
| declares a source and names a readable secret of 32 or more characters | `counted` | the times inside the window, under the keyed digest |
| names a secret the service cannot read | nothing; the request is refused with `waitlist_source_secret_unavailable` | nothing |
| names a secret shorter than 32 characters | nothing; the request is refused with `waitlist_source_secret_unusable` | nothing |

A named secret that cannot be read refuses the request rather than letting it
through uncounted, because the host asked for a count and a silent gap would
switch the guard off without anyone seeing it.

Create the secret on the deployment without printing it. The value travels
on standard input and never reaches the terminal or a command line:

```text
python3 -c 'import secrets; print("BALTOR_WAITLIST_SOURCE_SECRET=" + secrets.token_hex(32))' \
  | fly secrets import --app <application> --stage
```

and name it in the host's `waitlist` block as
`"source_secret_ref": "env:BALTOR_WAITLIST_SOURCE_SECRET"`. Replacing the
secret later starts every count afresh and makes every earlier record name
unlinkable, which is safe: the counts only ever cover one hour.

`source_privacy_checks` in
`src/loop_engine/core/service_runtime/waitlist_checks.py` holds each rule over
real records, with a known-wrong case beside it: a record named by the address
or holding an unkeyed digest is found, a count kept after its window is
found, and a host with no secret is shown to store nothing.

## What the host has to declare before the flood guard counts

A host that declares no client address source gets no flood guard on the
public form. The transport supplies no source key, every answer says
`source_counted: no_declared_source`, and the only limit left for a stranger
is one entry for each address. That is the state of any host configuration
with no `request_limits` block inside its `http` block. A host that declares
a source but names no source secret is in the same position, and every
answer says `source_counted: no_source_secret`.

Read on September 21, 2026, from the public profile of the deployed service:

```text
GET https://app.baltor.ai/api/v1/capabilities
  limits.failed_attempts_per_address.active               false
  limits.failed_attempts_per_address.client_address_source not_configured
```

So the deployed pilot declares no source. Set the block below in its host
configuration in the same release that first serves this form, or accept that
the public form has no count for each source.

A service behind its own trusted proxy declares the header that the proxy
overwrites on every request. For the pilot on Fly that header is
`Fly-Client-IP`, and the host configuration block is:

```json
"http": {
  "request_limits": {
    "record_type": "service_request_limits/v1",
    "client_address_source": "header",
    "client_address_header": "Fly-Client-IP"
  }
}
```

A service that callers reach directly declares `socket_peer` instead and no
header. Declaring `socket_peer` behind a proxy is worse than declaring
nothing: every caller is then counted as the proxy. The same setting also
turns on the failed-attempt limit for sign-in and account activation, so a
host that declares it gets both.

`undeclared_source_checks` in
`src/loop_engine/core/service_runtime/waitlist_checks.py` holds all three
cases over a real loopback transport: no declared source accepts every
caller and says it counted nobody; the known-wrong case that names the socket
peer anyway closes the form after five requests from one machine; and the
declared header counts each forwarded address on its own. Those fixtures name
a source secret, as a host that wants the count must.

## Before an invitation can promise a discount

The invitation tells a person to enter a code at checkout, so two separate
facts have to hold first.

| Fact | Where it comes from | What happens without it |
|---|---|---|
| The payment account holds the promotion code | the report `tools/setup_stripe_sandbox.py` writes, passed as `--discount-evidence` | the command refuses before any request, `payment_account_report_does_not_show_this_code_exists` |
| Checkout sessions take a discount code | `billing.discount_code` in `GET /api/v1/capabilities`, which follows `allow_promotion_codes` in the host's session configuration | the command refuses before the invitation is recorded, `checkout_does_not_take_a_discount_code_so_nothing_was_recorded_or_sent` |

Read on September 21, 2026, neither fact holds yet:

```text
GET /v1/promotion_codes on the test payment account
  {"object": "list", "data": [], "has_more": false}

GET https://app.baltor.ai/api/v1/capabilities
  billing holds no discount_code field, because the deployed release
  predates it; a release that serves this page publishes it as false
  until the host's session configuration sets allow_promotion_codes
```

So no invitation can be sent yet, and the served page does not name a
discount either: it shows that sentence only while the same
`billing.discount_code` record is true. Run
`tools/setup_stripe_sandbox.py --confirm-test-mode-writes` and set
`allow_promotion_codes` in the host's billing block first.

## Inviting one person

Prepare the discount once, in the payment account:

```text
tools/setup_stripe_sandbox.py --confirm-test-mode-writes --report <new file>
  └── finds or creates the coupon and its promotion code with everything else
```

Then read the list and invite one entry. Run both through
`tools/operator_credentials.py`, so no credential reaches an argument, a file
or the terminal:

```text
tools/waitlist_operator.py --service-origin https://app.baltor.ai --list
tools/waitlist_operator.py --service-origin https://app.baltor.ai \
  --invite <entry reference> --email <the address the listing showed> \
  --discount-code <the promotion code> \
  --discount-evidence <the setup report that names that code> \
  --sender "Baltor <hello@baltor.ai>" \
  --project-ref <identity project> --redirect-to https://app.baltor.ai/auth/callback \
  --acknowledge-invitation-effects --report <new file>
```

The invitation runs in this order, and the order is the protection against a
second email:

1. read the service profile and stop unless checkout takes a discount code;
2. record the invitation in the service, with its discount code;
3. prepare the account at the identity provider and take its sign-in link;
4. send the email through the mail provider;
5. record what happened to that email, sent or unknown.

## Taking an address off the list

```text
tools/waitlist_operator.py --service-origin https://app.baltor.ai \
  --forget <entry reference> --acknowledge-erasure --report <new file>
```

The command needs no address and sends no message. It records one `forget`
decision and then checks the answer: the entry has to come back in the
removed state with neither an address nor a note, or the run is reported as
refused. The acknowledgement is required because nothing undoes the erasure.

Nothing is repeated automatically at any stage. When the mail answer is lost,
the delivery is recorded as unknown and the operator inspects the mail
provider before deciding anything. The report holds identifiers, digests,
states and counts. It never holds the address, the link or a credential.

## What the page offers and when

Since September 22, 2026 the form is not a page of its own. It sits in the
invitation panel that leads the Get started page, and `/waitlist` opens that
page. Every public action into the journey says "Get started"; the footer no
longer carries a second link with another label.

The page makes no offer before the service answers. The invitation panel, the
form, the link on the registration page and the discount sentence all start
hidden, and the page shows each one only from the record
`GET /api/v1/capabilities` returns:

| Element | Shown when |
|---|---|
| `start-invite`, the invitation panel | `website.waitlist_available` is true and `website.registration_available` is not |
| `waitlist-form`, `signup-waitlist-link` | `website.waitlist_available` is true |
| `waitlist-discount` | the list is available and `billing.discount_code` is true |
| `waitlist-closed`, in the operator's panel | anything else, including an unanswered request |

When the service reports registration open, the account creation panel leads
the page instead. When it reports neither, and until it answers, the
operator's panel leads it.

A host that ships this page without a waiting list block therefore offers
nothing and says plainly that it is not taking requests. Offered and working
stay separate facts.

## What is proved and what is not

The checks cover the record, its five states, the four refusals, the erasure,
what the flood guard stores about an address and for how long, the served
form, the two routes, the order of the invitation and the refusals of the
operator command, all against local fixtures. The browser checks in
`tools/check_service_workspace.mjs` run the visitor's journey against a real
browser and a real loopback service: a service without a waiting list makes
no offer, and a service with one takes an address that then appears in the
operator's listing.

They do not prove that a message arrived, that an invited person joined, or
that checkout applied the discount. Those are separate checks against the
live accounts, and the discount one cannot pass until the payment account
holds the promotion code.

The public words on the page name no release stage and promise no date. A
check reads the served page and fails on either. Another check refuses the
sentence about erasing an address unless an operation erases it.
