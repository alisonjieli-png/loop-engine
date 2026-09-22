# Waiting list and invitations

Kind: operating guide for engineering. Written on September 21, 2026, against
the source in this revision.

Anyone can leave an email address and a short note. An operator reads the
list and decides. An approved person receives one invitation that carries a
sign-in link and a discount code the payment account already holds. This is a
technical document, so it uses the exact runtime terms. The public page does
not show them.

## What each part owns

```text
waiting list
├── served page /waitlist          the form, the plain confirmation
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
address, the decision history and the count of accepted entries for the
source. Nothing recovers the erased values, and no row is rewritten by hand:
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

The service holds no account addresses, so a host that can ask its identity
provider installs a `WaitlistAccountDirectory`. An answer that is not a plain
yes or no refuses the request instead of admitting an address the directory
was meant to exclude. Without a directory, only an address whose own entry
reached the joined state is known to have an account.

The flood guard counts accepted entries for one source inside a window. It
does not count refused attempts: the transport's failed-attempt limit for
each client address already counts those. It counts only when the host has
declared where the client address comes from, because behind a proxy every
caller would otherwise look like one source.

## What the host has to declare before the flood guard counts

A host that declares no client address source gets no flood guard on the
public form. The transport supplies no source key, every answer says
`source_counted: no_declared_source`, and the only limit left for a stranger
is one entry for each address. That is the state of any host configuration
with no `request_limits` block inside its `http` block.

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
declared header counts each forwarded address on its own.

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

The page makes no offer before the service answers. The form, the footer
link, the link on the registration page and the discount sentence all start
hidden, and the page shows each one only from the record
`GET /api/v1/capabilities` returns:

| Element | Shown when |
|---|---|
| `waitlist-form`, `waitlist-link`, `signup-waitlist-link` | `website.waitlist_available` is true |
| `waitlist-discount` | the list is available and `billing.discount_code` is true |
| `waitlist-closed` | anything else, including an unanswered request |

A host that ships this page without a waiting list block therefore offers
nothing and says plainly that it is not taking requests. Offered and working
stay separate facts.

## What is proved and what is not

The checks cover the record, its five states, the four refusals, the erasure,
the served form, the two routes, the order of the invitation and the refusals
of the operator command, all against local fixtures. The browser checks in
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
