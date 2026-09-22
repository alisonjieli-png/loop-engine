# Promotion codes

Kind: operating guide. It describes current behavior in the repository on
September 21, 2026, and it names the parts that are planned but not built.

A promotion code gives one account the paid service entitlement without a
payment. A person who has a code redeems it themselves. No operator has to do
anything for each person.

This guide covers what a promotion code is, how it differs from a Stripe
discount, exactly what redeeming one grants and does not grant, and how an
operator runs the whole path from creating a code to seeing who used it.

## What a promotion code is

A promotion code is a passive typed record in the existing service catalogue.
It is not a new runtime type, it is not a new store, and it is not a Loop. It
holds separate declared fields, and every effect of the code comes from one of
those fields:

```text
Promotion code record (service_promotion_code/v1)
├── code_digest, the stored identity of the code text
├── code_id, the identity an operator uses; it is not secret
├── label, a display name for the operator listing
├── grant (service_promotion_grant/v1)
│   ├── entitlement, which is bodies
│   └── seconds, how long one redemption lasts
├── redemptions_allowed, the total this code permits
├── redemptions_used, the total it has had
├── repeat_allowed_for_one_account, whether one account may redeem it twice
├── starts_at and expires_at, the window it can be redeemed in
├── approved_by and approval_ref, who approved it and against what record
└── enabled, which an operator can turn off
```

The code text decides nothing. A code named `BALTOR-FREE-FOREVER` grants
exactly the seconds its `grant` field declares, which may be seven days. A
check named `a_codes_text_never_decides_what_it_grants` creates two codes whose
text says the opposite of their records and proves that the records win.

The service never stores the code text. It stores the digest of the code. That
is why the operator listing cannot show a code: there is nothing to show. A
code is displayed once, by the command that created it, and never again.

## How it differs from a Stripe discount

| | Promotion code (this guide) | Stripe promotion code and coupon |
|---|---|---|
| Where it lives | The service catalogue, in the Loop Engine database | The payment provider |
| What it changes | The account's entitlement record | The amount on an invoice |
| Whether a payment happens | No payment is created at all | A payment still happens, for less |
| Whether a card is needed | No | Yes |
| What the records say | Source is `promotion_code_grant` | Source is `stripe_snapshot` |
| Whether it counts as revenue | Never | Yes, at the discounted amount |

Use a Stripe coupon when you want a paying customer who pays less. Use a
promotion code when you want a person to have the service for a period without
becoming a customer of the payment provider at all, such as an invited beta
user, a reviewer or a conference attendee.

The two can coexist. They write different records and they are counted
separately, so one is never mistaken for the other.

## What redeeming a code grants, and what it does not

Redeeming a code grants the declared service entitlement until the recorded
moment, and nothing else.

It grants:

- the body entitlement, which is the right to download the body of a reviewed
  catalogue item that the account has a grant for, exactly as a paid
  subscription grants it;
- that entitlement until the recorded moment, after which the account returns
  to free access.

It does not grant:

- a model allowance. Customers pay their own provider for model calls, and a
  code changes nothing about that;
- permission to execute code, locally or in a sandbox;
- any spending authority;
- access to catalogue items the account has no grant for;
- an administrator scope, a billing scope or any other permission;
- a Stripe customer, a subscription or an invoice.

These three sentences are carried in the redemption result itself, under
`limitations`, so a client that shows the result to a person shows them too.

## The entitlement record

Redemption writes the same `service_entitlement` record that
`set_operator_entitlement` writes. That was deliberate: there is one
entitlement path, and promotion codes extend it rather than running beside it.

The record names its own source:

| Source | What it means | Written by |
|---|---|---|
| `stripe_snapshot` | Paid access resolved from a provider subscription | The billing webhook |
| `explicit_host_grant` | Comped access an operator granted directly | `set_operator_entitlement` |
| `promotion_code_grant` | Comped access a person granted themselves with a code | Redemption |

A code grant also records `promotion_code_id`, `approved_by` and
`approval_ref`, so every comped account can be traced back to the code and to
the approval that created it. It carries no `subscription_ids` and no
`policy_digest`, because there is no subscription and no payment.

A release that predates this source reads an unknown source as metadata only.
An older server therefore refuses the access instead of honoring a record
whose rules it does not know. That is the safe direction, and it is why no new
entitlement record version was needed.

A redemption never shortens access an account already has. When the account
already holds comped access that lasts longer than the code grants, the longer
moment is kept and the earlier source and expiry are recorded alongside it.

## Comped accounts are never revenue

`ServiceRuntime.access_source_report()` walks every entitlement record and
separates the accounts. Only `stripe_snapshot` is revenue bearing. Everything
else is comped. The report lists `revenue_bearing_tenants` and
`comped_tenants` separately and counts them separately.

The classification reads the recorded `source` field. It never infers money
from an expiry, from a grant or from a name. The check
`a_comped_account_is_never_counted_as_revenue_in_the_access_source_report`
builds one paying account, one account comped by a code and one account comped
by a host grant, and proves that the two comped accounts appear in neither the
revenue count nor the revenue list. Moving `promotion_code_grant` into
`REVENUE_BEARING_SOURCES` makes that check fail.

The report counts accounts, not money. The amount invoiced is held by the
payment provider.

## Refusals

Redemption refuses in ten ways. Each has its own exact reason inside the
service and its own check.

```text
Refusal
├── Depends on the offered code, and is disclosed as one word
│   ├── unknown_code
│   ├── code_suspended
│   ├── code_has_not_started
│   ├── code_expired
│   └── code_redemptions_exhausted
└── Depends on the account, and is disclosed on its own
    ├── account_already_redeemed_this_code, when repeats are not allowed
    ├── account_already_has_paid_access_from_a_payment
    ├── account_body_access_revoked_by_the_host
    ├── no_authenticated_account
    └── redemption_not_installed
```

Every refusal that depends on the code answers with one word,
`promotion_code_unusable`, and one status, 403. Someone guessing codes cannot
tell a code the service never issued from a real code that has run out. The
exact reason stays inside the service and reaches an operator; it is never
returned to the person who offered the code. The two answers are the same byte
for byte except `request_reference`, which names the request, is issued at
random before the code is read, and so says nothing about the code.

The service also does the same work for both. An unknown code is evaluated
against a stand-in record, so every state condition runs and the per-account
record is read before the refusal is decided. A check compares the number of
store reads on both paths and requires them to be equal. What remains is one
index lookup that finds no row, which is why guessing is also rate limited.

## Rate limiting

Redemption uses the failed-attempt limiter the service already has, in
`request_limits.py`. A refused redemption is counted for the client address,
exactly as a refused sign-in and a refused account activation are. When an
address reaches its allowance the service refuses its next attempt with status
429 and a `Retry-After` header, before any work and before a worker slot is
used. The capabilities record names `refused_promotion_redemption` in its
`counted` list.

The limit is active only when the host has stated where the client address
comes from. Behind a proxy that is the configured header, not the socket peer.

## The served address

One address was added: `POST /api/v1/account/promotion`. An authenticated
account posts

```json
{"record_type": "service_promotion_redemption_request/v1",
 "code": "BALTOR-XXXX-XXXX-XXXX", "request_id": "one-request-identity"}
```

and receives a `service_promotion_redemption_result/v1` record. There is no
address that reads a code back, because the service holds only a digest.

The `request_id` is the request identity. Sending the same request twice
returns the same result with `replayed` set to true and spends one redemption,
not two. Sending a different code under a request identity that was already
used is refused with `promotion_request_identity_conflict`.

The address is served only when the host configuration installs it:

```json
"promotions": {"record_type": "service_promotion_policy/v1",
               "redemption_enabled": true, "maximum_listed_codes": 500}
```

Without that block the address answers 503 `promotion_redemption_unavailable`.

Planned, not built: there is no page on the website that offers the code box.
This guide describes the address and the records. A signed-in person cannot
redeem a code from the browser until that page exists.

## Atomic and idempotent

One redemption commits four records in one atomic batch over the existing
catalogue read set: the code record with its exact revision, the per-account
record, the request identity record and the entitlement. They commit together
or not at all.

Two accounts redeeming the last remaining redemption at the same moment both
read the same code revision, and only one of them can write the next revision.
The other is refused with `concurrent_update`. A check runs both attempts from
separate connections against a barrier and requires exactly one success, one
account with access, and a used count that never passes the allowed count.

The count is checked twice. `promotion_code_state` decides whether an attempt
may proceed at all, and the last step before the write compares the count with
the allowance once more, against the same record that is about to be written.
The check
`a_committed_redemption_count_never_passes_the_allowance_even_when_the_state_permits_it`
replaces the state evaluation with one that calls every code redeemable, which
is exactly the mistake the second layer exists to catch, and requires the
redemption to be refused and the stored count to stay where it was.

An unknown commit is not a success. The check
`an_unknown_commit_is_not_a_spent_redemption_and_the_same_request_still_works`
proves that a lost acknowledgment leaves the count at zero and that repeating
the same request identity then works.

The account's entitlement record is part of that read set at the exact revision
the redemption read. A payment that lands between the read and the write
therefore refuses the redemption with `concurrent_update` instead of replacing
the payment with a code grant. The check
`a_payment_that_lands_during_a_redemption_is_never_overwritten_by_a_code_grant`
lands a paying entitlement in that gap and requires the payment to survive with
its own source and the code count to stay at zero.

## How an operator runs the whole path

The command is `tools/promotion_codes.py`. It reads the host configuration that
the service itself serves from, so it writes to the same database. It makes no
network request and it calls no payment provider.

### 1. Create a code

```bash
python3 tools/promotion_codes.py create --config /data/host.json \
    --label "invited beta, October" --days 90 --redemptions 25 \
    --window-days 30 --approved-by reviewer.name \
    --approval-ref review:2026-09-21 \
    --acknowledge-promotion-grant
```

Creating a code requires `--acknowledge-promotion-grant`, the same way the
other operator commands in that folder require an explicit confirmation before
an effect. Without it nothing is written and the command exits with status 2.

The command generates the code itself. Do not pass a code in an argument: an
argument reaches the shell history and the process list. The generated code is
a prefix, then three groups of four characters from an alphabet without I, O,
zero and one, which is about sixty bits of randomness.

The code is written once to standard output and nowhere else. The summary on
standard error holds the `code_id`, the label, the counts and the window, and
never the code. Copy the code before you close the terminal. No later command
can show it.

### 2. Give the code to the person

Send it however you send it. The person signs in and redeems it.

### 3. See who used it

```bash
python3 tools/promotion_codes.py list --config /data/host.json
```

Each row holds the `code_id`, the label, the grant, `redemptions_allowed`,
`redemptions_used`, the window, the approver, the approval reference, whether
the code can be redeemed right now, and `redeemed_by`, which lists the accounts
that redeemed it. No row holds a code.

### 4. Stop a code

```bash
python3 tools/promotion_codes.py suspend --config /data/host.json --code-id <identity>
python3 tools/promotion_codes.py expire --config /data/host.json --code-id <identity>
```

Suspend turns the code off. Expire closes its window at this moment. Both stop
new redemptions.

Neither removes access that was already granted. A person who redeemed the code
yesterday keeps their access until it expires. To remove that access, revoke
the account's entitlement with `ServiceRuntime.revoke_entitlement`, which is a
separate deliberate act and which also stops the account redeeming another
code until an operator restores it.

### 5. Check the books

`ServiceRuntime.access_source_report()` separates paying accounts from comped
accounts. Run it before you read any number as revenue.

## What is not built

- No page on the website offers a code box. The address exists; the browser
  journey does not.
- No email carries a code. An operator sends it.
- There is no limit on how many different codes one account may redeem over
  time, only on repeating one code.
- Suspending a code does not notify anyone who holds it.

## Where the code lives

| Part | File |
|---|---|
| Records, refusals, creation and redemption | `src/loop_engine/core/service_runtime/promotions.py` |
| Entitlement sources and the access source report | `src/loop_engine/core/service_runtime/runtime.py` |
| The served address | `src/loop_engine/core/service_runtime/http.py` |
| Checks | `src/loop_engine/core/service_runtime/promotion_checks.py` |
| Operator command | `tools/promotion_codes.py` |
| Operator command checks | `tools/test_promotion_codes.py` |

Related guides: [billing setup and pricing](billing-setup-and-pricing.md) for
what the paid plan is and what is measured, and
[private beta operations](private-beta-operations.md) for inviting a person to
an account in the first place.
