# Finding out what went wrong in the hosted service

Kind: operator procedure for the deployed Baltor service. It explains what the
service records about a refused request, how a customer and an operator name
the same request, how to read the records, what the health route measures, and
what the first failure of each dependency looks like. Every command in this
guide reads. None of them changes anything.

Written on September 21, 2026, against the branch `wave5/operator-observability`.
The measurements below were taken on that day by starting the real service as a
separate process and driving real requests through it. Check the current source
and the current provider state before you rely on a dated statement.

## What the service recorded before this change

These are observed facts, measured by running the service at revision `e146e56`
as its own process, driving two successful requests and five failing ones, and
reading everything the process and the store held afterwards.

```text
What existed when a customer's request failed
├── Process output: nothing about the request
│   ├── Eight lines for the whole session, all of them server start and stop
│   └── Zero lines for any of the seven requests, successful or refused
├── Durable store: nothing about the request
│   └── No record of a refusal of any kind was written
├── The customer's refusal: a code and nothing else
│   └── Two different customers refused for different reasons received
│       byte-identical answers, so neither could be told apart
└── Operator command: none
    └── `loop-engine service failures` did not exist
```

The service runs its web server with request logging switched off, in
`http_entrypoint.py`, so the absence of per-request output is by configuration
and not an accident of the test. The consequence is exact: when a customer said
"it failed", there was no record anywhere that an operator could search, and no
way for the customer to name the request they meant.

## The name of one request

Every request now receives a reference before any work begins, so a refusal
raised by the very first check still carries one.

```text
ref_sfe2cxaztnfrs6sm7znepnnrx4
```

A reference is four characters of prefix and twenty-six characters of lower
case base32, which carries one hundred and twenty-eight random bits. Three
properties matter and each one is enforced by a check.

- It comes from the operating system random source and from nothing else. The
  function that issues one takes no argument, so there is no way for a
  credential, an address, a tenant name or a request body to reach it. A
  reference therefore tells an attacker nothing about the caller.
- It cannot be guessed. One hundred and twenty-eight random bits are far beyond
  searching, so knowing one reference does not help anyone find another.
- The service refuses a reference it did not issue. A value of the right shape
  that some other code computed, for example from a digest of a credential, is
  rejected with `unissued_request_reference` instead of being recorded.

The alphabet has no zero, no one, no eight and no nine, so a person reading a
reference out of a refusal over the telephone cannot confuse a zero with the
letter O, or a one with the letter I.

The customer sees the reference in the refusal:

```json
{
  "record_type": "service_http_error/v1",
  "error": {"code": "item_unavailable"},
  "effect_commitment": "not_asserted",
  "automatic_retry": false,
  "request_reference": "ref_sfe2cxaztnfrs6sm7znepnnrx4"
}
```

A successful answer carries no reference. The field exists only on a refusal,
so it cannot be mistaken for part of a result record.

## What a failure record holds

One record is written for each refused request, into the same service
collection and namespace as every other service record. No parallel store is
created.

```text
service_request_failure/v1
├── request_reference: the name the customer was shown
├── route: a declared route, or the word unmatched
├── method: a declared request method, or the word other
├── refusal_code: the typed code the customer received
├── status: the numeric answer the customer received
├── tenant_id: the account, or empty text when the request never authenticated
├── at: the time, in whole seconds
├── sequence: the position of this record in the journal
├── service_version: the installed distribution version
├── release_reference: the build the operator deployed, when the host states one
└── payload_capture: which of the two recording choices was in force
```

What it never holds matters as much.

- No credential. The record is built from the route, the method, the code and
  the tenant. A header is never read into it, so a key cannot arrive by
  accident.
- No header that carries authority. Nothing copies request headers anywhere
  near this record.
- No private payload by default. The body of a request is kept only when the
  host has written `metadata_and_request_body` into its configuration. Under
  the default setting, asking to record a body is refused with
  `payload_capture_not_authorized` rather than quietly honoured.
- No path the service does not declare. A stranger chooses the text of an
  unknown path and it can carry anything, so an undeclared path is recorded as
  `unmatched` and the text is discarded. The same rule applies to an unusual
  request method, which is recorded as `other`.

The journal keeps a bounded number of records, five hundred by default. Each
record takes the slot given by its sequence number, so the newest records
replace the oldest and the number stored never passes the retained count. A
stranger who sends refused requests all day cannot fill the volume. After a
restart the sequence continues from the highest number already stored, so a
restart does not overwrite the newest records from the beginning.

A failure of the journal itself never turns into a different failure for the
customer. The customer is already being refused; the write is attempted, and
any problem is returned as a typed outcome rather than raised.

## Reading the records

```bash
loop-engine service failures --config /data/host.json --limit 20
loop-engine service failures --config /data/host.json --tenant alpha
loop-engine service failures --config /data/host.json --reference ref_sfe2cxaztnfrs6sm7znepnnrx4
```

The three forms answer the three questions an operator actually asks: what has
been failing, what is failing for this one customer, and what happened to the
exact request this customer is asking about.

The command reads and cannot write. It builds its view of the journal directly
from the host configuration with host write authority withheld, so it answers
even when the service is refusing every request or is not running at all, and
a future change that tried to write through it would be refused rather than
altering a record an operator is reading.

## Health that can fail

The health route separates two different answers.

- Alive means this process is running and answering. A reply at all proves it.
- Ready means every required dependency answered just now. It is measured on
  each request, and it can report not ready.

A service that is not ready answers with status 503, so the load balancer in
front of it stops sending customers to a machine that cannot serve them.

A dependency is required when the machine cannot give any correct answer
without it, so that taking it out of service or restarting it is the right
response. Three qualify.

```text
Required, and a failure means not ready
├── durable_store_answers: the durable store answered a read just now
├── volume_has_write_headroom: the volume still has room to write
└── authentication_mode_installed: some way to authenticate a customer exists

Reported, and a failure does not remove the machine
├── catalogue_registered: how much there is to serve
├── interface_page_readable: the packaged sign-in page can be read
├── browser_identity_installed: browser sign-in is configured
├── billing_sessions_installed: subscription checkout is configured
├── billing_webhook_installed: payment provider callbacks are configured
└── retention_sweep_current: the last removal of expired records finished
```

The second group is deliberate. An empty catalogue is a configuration state and
not a dependency that failed: the service still authenticates, still answers its
capabilities and still returns an accurate empty list. A missing interface page
stops a person signing in through a browser and stops nothing else. The service
runs on one machine, so reporting not ready for either would take the working
programming interface down as well, and restarting cannot put a file back into
an image. An operator reads them in the health record and decides.

`retention_sweep_current` reports the periodic task that removes the records
the privacy notice keeps for a bounded time. Reading it never runs a removal.
When it does not pass, its code says why: `retention_sweep_not_run_yet` in the
first moments after start, `retention_sweep_not_running` on a service without
host write authority, or the code of the last failed run, such as
`store_unavailable`. The task keeps its schedule after a failure, and the
[service runtime guide](../../src/loop_engine/core/service_runtime/README.md#retention-of-expired-records)
describes it.

The volume check is the one that the store check cannot replace. When a volume
fills, a read still answers and only writes fail, so a health route that only
read would report a perfectly healthy service while every usage record, account
record and failure record was being lost. Free space is measured with one system
call and nothing is written, so asking the question does not consume the space
it is measuring.

## The first failure of each dependency

Each row below names what the customer sees, what the operator sees, and what to
do. The typed codes are the ones in the source, not invented examples.

### The identity provider, for browser sign-in

The service verifies a browser sign-in token against the identity provider's
key set endpoint on each request.

- The customer sees status 503 with the code `identity_key_set_unavailable`.
  A person signing in through a browser cannot sign in. A customer using a
  personal client key is unaffected, because a client key is verified against
  the durable store and never against the identity provider.
- The operator sees those refusals in the journal, grouped on the account
  routes, with the same code repeating across different tenants. Health stays
  ready, because browser sign-in is reported and not required.
- What to do: confirm the key set address answers from the machine. Nothing in
  the service needs restarting; the refusal clears when the provider answers.
  Do not change the issuer or the key set address to work around it.

### The email provider

The service itself sends no email. The confirmation link is created and sent by
the operator invitation command, not by a customer request.

- The customer sees nothing at all, because no customer request touches the
  email provider. An invited person simply never receives their link.
- The operator sees the failure in the output of the invitation command, at the
  moment they run it. There is no service record, because there was no request.
- What to do: read the command's own result. Treat an unknown outcome as
  unknown and do not send a second invitation until you have established
  whether the first was delivered, because a repeated send is a repeated
  external effect.

### The payment provider

- The customer sees the typed refusal of the billing route they called, for
  example `billing_sessions_not_installed` or `billing_webhook_unavailable`
  when the adapter is absent, or a pending or uncertain billing code when the
  provider answered in a way the service will not interpret. Every other route
  keeps working, so a customer who already has access keeps their access.
- The operator sees those codes in the journal against the billing routes, and
  sees the billing rows in the health record reporting not installed.
- What to do: a billing code that says the outcome is unknown, such as
  `billing_commit_unknown` or `billing_session_uncertain`, means the service
  has refused to guess. Reconcile against the payment provider's own record
  before taking any action, and never retry a charge on the strength of an
  unknown result.

### The volume

This is the failure most likely to arrive without warning, because the service
runs on one encrypted volume of one gigabyte.

- The customer sees successful reads continuing while anything that records
  something fails. This is the confusing case: the service looks like it works.
- The operator sees health reporting not ready with
  `volume_has_write_headroom` failing and the code `volume_nearly_full`, while
  `durable_store_answers` still passes. That exact combination means the volume
  filled rather than the store breaking. If the volume is not there at all, the
  code is `volume_unavailable` and the store check fails too.
- What to do: the journal is bounded and is not what filled the volume, so look
  at what else is written there. Extending the volume is a provider change and
  needs the authority that covers it. Destroying anything to make room is not
  an operator decision.

### The container host

- The customer sees no answer at all, or an error page from the edge, because
  there is no process to refuse them. There is no reference, because no request
  reached the service.
- The operator sees nothing new in the journal for the period, which is itself
  the signal: a gap with no records at all is different from a period full of
  refusals. Health does not answer.
- What to do: read the machine state and the platform's own logs. The records
  in this guide describe requests the service answered, so they cannot explain
  a period when the service was not running. Deploy by digest and keep the
  previous image, so a rollback is available.

## Privacy

Three settings, in order of how much they keep.

```text
Recording choices
├── record_failures: false
│   └── Nothing is written. A read says why, rather than reporting records that
│       do not exist.
├── payload_capture: metadata_only, the default
│   └── The declared metadata above and nothing from the request body.
└── payload_capture: metadata_and_request_body
    └── A bounded excerpt of the request body as well, kept only because the
        host wrote that choice into its configuration.
```

Credentials are never recorded under any of the three. That is not a setting.
Two request bodies are themselves credentials: sign-up carries the password of
the new account, and promotion redemption carries a code that grants paid
access to whoever holds it. Neither body is kept under any choice. The refusal
is still recorded, without the body. The check
`a_body_that_carries_a_credential_is_never_captured_even_when_the_host_captures_bodies`
sends both through the real transport with body capture chosen and reads every
byte of the store afterwards.

## Checks

The behaviour in this guide is covered by `observability_checks.py`, which runs
inside `loop-engine service smoke` and the service self-test. Each guard is
shown twice: once doing its job, and once refusing the case it exists to
prevent. The privacy guard drives a real credential and a private text through
the real transport and then reads every byte of the durable store to confirm
neither appears.

## What this guide does not cover

- It does not describe a full customer journey. Records of refusals are not
  evidence that the paid path works.
- It does not qualify any provider. Reading a record proves nothing about the
  identity, email or payment provider being correctly configured.
- It does not cover periods when the service was not running, for the reason
  given in the container host section above.
