# Troubleshooting the Baltor service

Kind: operating guide for a paying customer. It covers the failures people
meet first. For each one: what you see, what it means, and what to do.

Every refusal in this page was produced on 2026-09-21, either against
`https://app.baltor.ai`, marked **deployed**, or against a local instance
started from this repository, marked **local**. The complete refusal table is
in [serving and connections](service-serving-and-connections.md).

## Read the refusal before you change anything

Every refusal is the same record and it names one stable code:

```json
{"record_type": "service_http_error/v1",
 "error": {"code": "unauthorized"},
 "effect_commitment": "not_asserted",
 "automatic_retry": false}
```

Two fields matter as much as the code. `effect_commitment` is `not_asserted`
when the service makes no statement about a durable effect, and
`durable_pending` when a durable write is known to be pending.
`automatic_retry` is always false, which means the service has not repeated
anything for you and will not.

The fastest first move is almost always the same:

```bash
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" \
  https://app.baltor.ai/api/v1/session
```

That answer tells you which account you are, which scopes the token carries
and which entitlement the account holds. Most of the failures below are
visible in it.

## The token has expired

**What you see.** Status 401 and the code `unauthorized`, on every address,
including `/api/v1/session`. The `WWW-Authenticate` header carries `Bearer`.

**Local**, using a token whose expiry had passed:

```json
{"record_type": "service_http_error/v1",
 "error": {"code": "unauthorized"},
 "effect_commitment": "not_asserted", "automatic_retry": false}
```

**What it means.** Client tokens expire. The service refuses an expired token
in exactly the same way as an unknown one, on purpose: a refusal never tells a
caller whether a credential once existed.

**What to do.** Open `/account`, look at Your client tokens, and read the
`state` beside each one. A token whose state is `expired` or `revoked` is
finished. Create a new one, put it in `BALTOR_SERVICE_TOKEN`, and restart the
client so that it reads the new value. Revoke the old token while you are
there.

This is also what you see when the account itself has been disabled. If a new
token is refused the same way, ask your operator.

## The token belongs to a different account

**What you see.** Nothing is refused at the credential level. You connect, you
search, and the material you expected is simply absent. A manifest for an
item you know exists answers 404 with `item_unavailable`.

**Deployed**, using a valid token for an account with no grants:

```json
{"record_type": "service_http_result/v1",
 "operation": "list",
 "result": {"record_type": "provisioning_list/v2",
            "tenant_id": "pilot-boundary", "entitlement": "bodies",
            "items": [], "withheld": [], "metered": false}}
```

and, for a named item:

```json
{"record_type": "service_http_error/v1",
 "error": {"code": "item_unavailable"},
 "effect_commitment": "not_asserted", "automatic_retry": false}
```

**What it means.** Material is granted to one account. A token carries the
grants of the account that issued it, and nothing else. The service answers
`item_unavailable` whether the item does not exist or exists for somebody
else, so that a caller cannot map another account's catalogue.

**What to do.** Read `tenant_id` from `/api/v1/session` and check that it is
your account. If it is a machine that several people use, check that the
environment variable holds your token and not a colleague's. If the account is
right and the material is still missing, the grant is missing: ask your
operator to grant the item to this account.

The discover answer is a quick second opinion. It reports `items_held`, which
is how many items this account may see, and `bodies_available`, which is
whether any of them can be downloaded at all.

## The client and the service share no protocol version

**What you see.** Status 400. In a harness this usually appears as the server
failing to connect, or as the tool list never arriving.

**Deployed**, the release that ran on 2026-09-21, from an `initialize` that
asked for `2025-06-18`:

```json
{"record_type": "service_http_error/v1",
 "error": {"code": "unsupported_protocol_version"},
 "effect_commitment": "not_asserted", "automatic_retry": false}
```

**Local**, the source in this repository on 2026-09-22, from a `tools/list`
that named `2025-06-18` in `MCP-Protocol-Version`:

```json
{"jsonrpc": "2.0", "id": 2,
 "error": {"code": -32022, "message": "Unsupported protocol version",
           "data": {"supported": ["2026-07-28", "2025-11-25"], "requested": "2025-06-18"}}}
```

**What it means.** The source in this repository serves two protocol
versions: `2025-11-25` through the `initialize` handshake, and `2026-07-28`
named on every request. An `initialize` for any other version is answered with
`2025-11-25`, and the client decides whether to continue; the release that ran
on 2026-09-21 refused it instead, as shown above. Any other request that names
a version the service does not serve is refused with protocol error `-32022`,
which lists the served versions, and nothing is done for it. A request with no
`MCP-Protocol-Version` header, or a header that is not a version, is refused
with protocol error `-32020`.

**What to do.** Update the client. Check the version you have with the
client's own version option, and compare against the versions the service
publishes:

```bash
curl -sS https://app.baltor.ai/api/v1/capabilities
```

Read `protocol.versions` from that answer. `protocol.handshake_versions` are
reached with `initialize` and `protocol.per_request_versions` are named on
every request. If your client can speak none of them, use the direct JSON
addresses instead. `/api/v1/retrieval`, `/api/v1/provisioning` and
`/api/v1/download` do everything the tools do and have no protocol version
requirement of their own.

## A body request without a grant, a scope or an entitlement

Three different things refuse a download, and the code tells you which one.

| Code | Status | What is missing |
|---|---|---|
| `item_unavailable` | 404 | The grant. This account may not see the item at all. |
| `insufficient_scope` | 403 | The scope. The token does not carry `provisioning:read`. |
| `body_forbidden` | 403 | The entitlement. The account may see the item but may not take its body. |

**Local**, a download attempted with a token whose only scope was
`provisioning:metadata`:

```json
{"record_type": "service_http_error/v1",
 "error": {"code": "insufficient_scope"},
 "effect_commitment": "not_asserted", "automatic_retry": false}
```

The same token could still list the item, and the listing honestly reported
`body_allowed` as false for it.

**What to do**, in this order:

1. Read `/api/v1/session`. If `scopes` does not contain
   `provisioning:read`, create a new client token that does. Your account
   cannot give a token a scope the account does not hold.
2. If the scope is present, read `entitlement` in the same answer. `metadata`
   means search and manifests only. `bodies` means downloads are permitted.
   An entitlement comes from a subscription or from an operator grant, not
   from the token.
3. If both are right, ask your operator for a grant on that item.

Nothing above is measured. A refusal before the body is released is never
charged, and the service lists that in `never_metered`.

## The host does not accept the item's licence

**What you see.** As a customer, the item is absent from search and from your
listing, and never appears with an explanation. Licence acceptance is decided
by the host before an item is registered, so there is no item to refuse later.

**What your operator sees.** The service refuses to start, naming the item and
one of these codes:

| Code | Meaning |
|---|---|
| `item_license_missing` | The item declares no licence at all. |
| `item_license_unknown` | The item declares a state such as unknown, rather than a licence. |
| `item_license_needs_review` | The item declares that its licence still waits for review. |
| `item_license_not_accepted` | The item declares a real licence that this host's list does not contain. |

**What it means.** The host holds one list of exact licence identifiers, and
it compares them as written. A licence in another letter case or with extra
spaces is a different, unlisted name. A state is never treated as a licence,
so no host list can accept one.

**What to do.** Ask your operator which licences the host accepts and under
which licence the material you want is published. Nothing you can send changes
this: it is a host decision made before serving.

## Too many refused attempts from one address

**What you see.** Status 429 and the code `failed_attempt_limit_reached`, with
a `Retry-After` header.

**Local**, after three refused attempts from one address:

```json
{"record_type": "service_http_error/v1",
 "error": {"code": "failed_attempt_limit_reached",
           "details": {"record_type": "service_request_limit_refusal/v1",
                       "retry_after_seconds": 21}},
 "effect_commitment": "not_asserted", "automatic_retry": false}
```

**What it means.** The service counts refused attempts that carried a
credential, for each client address, inside a window. A request with no
credential at all is refused without being counted. An accepted request is
never counted and never clears the count.

**What to do.** Wait the number of seconds in `retry_after_seconds`. Then fix
the credential before trying again, because retrying with the same bad token
only extends the wait. A loop that retries on 401 will keep an address locked
out; make it stop on 401 instead.

The published limit is in the capabilities record, under
`failed_attempts_per_address`. It reports whether the limit is active, how
many failures are allowed, the window in seconds and where the client address
comes from. It is kept in the memory of one service process, so it is not
shared between machines and it is empty again after a restart.

Checked on 2026-09-21, the deployed pilot answers from an image built before
this limit was published, so its capabilities record does not carry
`failed_attempts_per_address` yet. If the key is absent, the limit is not part
of the running service.

## The client says the answer is not acceptable

**What you see.** Status 406 from `/mcp`, with a message that the client must
accept both `application/json` and `text/event-stream`. The answer is a
JSON-RPC error object, not the service's own refusal record.

**What it means.** The protocol transport refused the request before the
service saw it, because the `Accept` header did not offer the event stream the
transport uses.

**What to do.** This is a client configuration problem, not a permission
problem. Use one of the published client settings from
[getting set up](service-getting-set-up.md), which send the right headers, or
send `Accept` as `application/json, text/event-stream` yourself. Verified
**local** on 2026-09-21.

## The service is busy or the request ran out of time

| Code | Status | What to do |
|---|---|---|
| `service_busy` | 503 | Every worker slot is in use. Pause briefly and lower your concurrency. Nothing was started. |
| `deadline_exceeded` | 504 | The operation did not finish in time. Work may still be running on the server. |

`deadline_exceeded` is the one to be careful with. It is not proof that
nothing happened. Before repeating a body read, either read `/api/v1/usage` to
see whether the unit was recorded, or simply repeat the read with the **same**
`request_id`, which cannot be measured twice.

## Something durable may or may not have happened

| Code | Status | What to do |
|---|---|---|
| `meter_commit_unknown` | 503 | The measured unit may or may not be recorded. Retry with the same `request_id`. |
| `commit_unknown` | 503 | A durable write was attempted and its outcome is unknown. Read the current state before acting. |
| `concurrent_update` | 409 | Another change landed first. Read the current state and try again. |

None of these is a failure you should turn into a blind retry. Read first, act
second. The service will not repeat an effect for you, and an unknown outcome
is not the same as a failure.

## A quick checklist

1. `curl` `/api/v1/session` and read `tenant_id`, `scopes` and `entitlement`.
2. `curl` `/api/v1/capabilities` and read `protocol` and `limits`.
3. List what this account may see, and check `body_allowed` on the item.
4. Read `/api/v1/usage` before you repeat anything that downloads a body.
5. If the answer still does not make sense, send your operator the code, the
   address and the time. The code is stable and is enough to find the cause.

Never send anyone your token. The operator cannot read it either: the service
stores only its digest.

## Related pages

- [Getting set up](service-getting-set-up.md)
- [Searching and retrieving](service-searching-and-retrieving.md)
- [Serving and connections](service-serving-and-connections.md)
- [Troubleshooting ladder](../TROUBLESHOOTING-LADDER.md), for the engine
  itself rather than the service
