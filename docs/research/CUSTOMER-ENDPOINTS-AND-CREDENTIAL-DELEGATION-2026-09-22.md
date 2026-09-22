# Customer endpoints and credential delegation across fresh harnesses

Kind: dated source and repository research with a proposed integration design.
Reviewed September 22, 2026. This is input for S-6.8, S-6.31, S-6.42,
S-6.43 and S-6.60 in the [roadmap](../roadmap/roadmap.yaml). It grants no
provider, network, secret, spending or tool authority. No real credential,
provider call or external tool call was used for this review.

## Recommendation

Keep a **customer-side connection and credential broker** in the local Loop
Engine host. A newly started harness gets its task material and, only when
needed, a short-lived capability to request a named model or tool operation.
The proposed broker would resolve the customer's credential at physical use
against an already selected exact endpoint. Current provider settings instead
read a named environment variable when the gateway is constructed.
The hosted Baltor intelligence service should neither collect those provider
credentials nor become the route through which a customer's local model runs.
This follows the existing [customer and service split](../architecture/MVP-CLIENT-SERVER.md).

The existing confined harness path already has the model half of this design:
it gives the harness process a local compatible model address and a dummy key, then
relays the request through a Unix socket to the owning Loop's gateway. The
harness process inherits neither the host environment nor host network. Extend and
qualify this boundary instead of starting a second generic secret store.
Model Context Protocol tool access requires a separate typed bridge because
the current process path disables native tools. Passing a provider or tool
credential to a process remains an explicit, narrower-trust fallback for a
qualified harness that cannot use the broker.

## Complete runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

A broker, vault, connection, lease and harness process are mechanics under an
owning Loop. None is a new executable graph vertex or an authority source.

## Three identities that should not be pooled

| Identity | Who needs it | Initial delivery to a fresh step |
|---|---|---|
| Baltor library client credential | Customer-side client searching and fetching approved intelligence from Baltor | The host fetches selected, digest-bound material before launch. The harness receives material or scoped references, not the account credential. A later dynamic search needs a separate scoped host bridge. |
| Model endpoint credential | The local Loop Engine host calling a customer-selected local or cloud provider | The existing broker keeps the key out of the harness process. In the proposed extension, the host resolves a local reference at physical use. Current settings read a named environment variable at gateway construction. An unauthenticated local endpoint needs no credential. |
| Third-party Model Context Protocol or other tool credential | The customer-side connection to that specific tool server | The host controls the upstream connection and credential reference. A stdio server process still receives the exact credential it needs; the harness does not. The harness sees only its approved tool names and a bounded local capability. |

Neither a Baltor client key nor a model key can stand in for a tool-server
token. A remote Model Context Protocol access token must be issued for that
server's resource audience and sent with each authorized HTTP request. It
must not be forwarded as another service's token. See the
[2026-07-28 authorization specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
and its [token-passthrough rule](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices).
The protocol makes authorization optional overall; an unprotected server
still needs explicit network and tool-effect authority from the owning Loop.

## What the repository already does

| Boundary | Observed behavior and limit |
|---|---|
| [Confined harness process](../../src/loop_engine/core/harness_process.py) and [relay](../../src/loop_engine/core/harness_process_relay.py) | Bubblewrap clears the host environment, separates the network namespace and mounts one Unix socket. The harness process sees a local compatible model server with a dummy key. The parent validates model identity, output allowance and absence of native tools before calling its model broker. The [gateway-backed adapter](../../src/loop_engine/core/harness_semantic.py) records physical attempts. This is a text-only, locally checked path; it does not prove every native harness loaded instructions or handled tools. |
| [Provider settings](../../src/loop_engine/core/runtime_settings.py), [custom endpoints](../../src/loop_engine/core/custom_endpoint.py) and [provider guide](../guides/providers-and-keys.md) | A custom OpenAI-compatible or Ollama route can name an endpoint, model, output source, authentication scheme and `credential_env`. Gateway construction reads the named environment variable into a provider object; it does not yet resolve the key per physical call. `auth_scheme: none` supports an unauthenticated local service. `locality` is descriptive, not reachability or cost authority. A route needs explicit configuration and eligibility; a URL alone does not qualify it. |
| [Credential leases](../../src/loop_engine/core/credential_leases.py) | An offline-verified record holds reference, owner, scope, expiry and use ceiling without the value. It is not wired to ordinary harness process lifetime; S-6.8 is proposed. `LeaseBroker.resolve()` by itself does not authenticate which process called or bind one exact model or tool operation. |
| [Model Context Protocol registry](../../src/loop_engine/core/mcp_adapter.py) and [transport](../../src/loop_engine/core/mcp_sdk_transport.py) | Registered servers and tools have effects, allowlists, approvals and timeouts. The transport resolves declared `env:` or `secret:` references only at connection, passes available named values to a stdio server and uses a Bearer header for remote HTTP. A missing `env:` value is silently skipped today, whereas an unresolved `secret:` reference refuses. It creates a 2025-11-25 session per operation. It has no qualified shared OAuth refresh or harness-process bridge, and the current remote HTTP binding chooses the first resolved credential rather than an exact audience-bound authentication profile. Registered stdio commands are executed without a sandbox or package pin at this boundary. |
| [Hosted provisioning transport](../../src/loop_engine/core/provisioning_mcp.py) | Its current profile is the older 2025-11-25 in-process transport. The 2026-07-28 negotiation work is proposed separately in S-6.43. A customer's hosted-library connection is not a provider or tool credential. |

A local offline recheck during this review passed all 7 credential-lease
self-checks, 11 confined-harness-process checks and 7 Model Context Protocol
transport checks. These fixtures exercise contracts and isolation, not a
customer's endpoint, remote OAuth or a live native tool bridge.

Two source-inspection risks deserve named negative checks before a customer
setup flow accepts arbitrary configurations. `McpServerSpec` checks the
syntax of declared credential references but does not currently reject a
secret embedded in its command or URL. `CustomEndpoint.describe()` records the URL while URL
validation only requires an HTTP scheme, and the older
`LOOP_ENGINE_ENDPOINTS` parser still accepts a literal `key=`. These are
potential disclosure paths, not reproduced leaks. Refuse URL userinfo and
raw credential query parameters. Prefer query-free endpoint URLs unless a
typed allowlist admits a documented non-secret parameter. Admit only
reviewed, pinned stdio commands and typed arguments, with credentials
supplied through references, and refuse literal endpoint key fields. A
secret-pattern scan alone cannot prove an arbitrary string is safe. The
[provider guide](../guides/providers-and-keys.md)
also describes repository `.env` lookup, while the [takeover checkpoint](../context/TAKEOVER-CHECKPOINT-2026-09-20.md)
forbids credential values anywhere in the repository, including ignored
files. Customer setup should use a private local reference or a deliberately
supplied runtime environment variable.

## Endpoint placement and reachability

`127.0.0.1` names the loopback of the **calling process's network
namespace**. In the existing confined path it names the harness process's relay; the
parent can separately reach a customer's model server on the parent's
localhost. In a container, the same address names the container, not the
user's host; Docker documents an explicit
[host connection name](https://docs.docker.com/desktop/features/networking/networking-how-tos/)
for Docker Desktop. A remote Baltor service cannot connect to a user's
localhost. A remote worker would need a customer-operated local companion or
an explicitly authorized tunnel, with its own identity and network policy.
Never rewrite `127.0.0.1` to a public bind address automatically.

| Customer configuration | Credential and route consequence |
|---|---|
| Local Ollama at `http://127.0.0.1:11434` | [Ollama says its local API has no authentication](https://docs.ollama.com/api/authentication). Configure a parent-side route with `auth_scheme: none` and a source-backed exact model output capacity. A compatible client may demand a dummy key, which [Ollama ignores locally](https://docs.ollama.com/api/openai-compatibility). |
| Ollama Cloud direct | The customer's local host resolves `OLLAMA_API_KEY` or a private key reference and sends it only to the exact Ollama Cloud origin. [Direct cloud inference requires a Bearer key](https://docs.ollama.com/api/authentication). The hosted Baltor service does not receive it. |
| Ollama signed in locally and selecting a cloud model | The local API may forward to cloud under the user's Ollama sign-in. [Ollama documents this path](https://docs.ollama.com/api/authentication). Local address and absent API key do not imply no external call or no provider allowance; classify the exact selected model and authority. |
| Local server with its own token or reverse proxy | Resolve the credential in the parent and pin the permitted origin, route and TLS policy. A customer-supplied `127.0.0.1` address works only where the parent actually runs. |
| Native harness account or credential store | Let a qualified native adapter use its own local account when broker routing is unavailable and the customer selects that profile. Record that the host may be unable to preempt native calls or reconcile exact usage; refuse a task that requires those controls unless they are demonstrated. |
| Container or remote worker | Probe from the actual parent namespace. A connection on the user's laptop is not evidence the worker can reach it. Offer a local companion or explicit authorized route; do not send the endpoint credential to Baltor by default. |

Reachability, authentication, model capability, price class, and permission
are five separate checks. An endpoint listing or configured key proves none
of the later checks. In particular, a local endpoint can reach a paid cloud
model and a key can be present but revoked.

## Proposed customer-side bridge

```text
Customer-side Loop Engine host
├── Exact user, task, Loop, endpoint, tool and effect authority
├── Local credential references and resolver
│   ├── Operating-system credential store or user-controlled native account
│   ├── Named runtime environment variable, when explicitly selected
│   └── Per-server OAuth access and refresh state, when supported
├── Existing per-instance credential lease contract
│   └── Extend binding and authenticate the caller at use
├── Existing model request broker and ModelGateway
│   └── Customer-configured local or cloud endpoint; no provider key in harness process
├── Proposed Model Context Protocol tool bridge
│   ├── Filtered exact tool manifest for this step
│   ├── Local harness process facade with a step-scoped, expiring capability
│   ├── Parent-owned upstream stdio or HTTP connection and credential
│   └── Existing schema, effect approval, artifact and Run History boundaries
└── One fresh native harness process for the focused step
    ├── Selected instruction and intelligence material
    ├── Local model relay address and dummy compatibility key
    └── Only its authorized tool facade, if the adapter supports one
```

The facade must authenticate each harness-process request. At step launch, bind its
capability to the instance, owning Loop, permitted servers and tools, schema
versions, expiry, use ceiling and remaining cumulative budget. At each tool
invocation, bind the actual argument digest and exact effect decision before
dispatch. Existing credential leases can supply the revocation lifecycle,
but a lease reference alone is not a bearer permission to invoke any tool.
Revalidate the exact effect before the physical call and preserve unknown
completion after a timeout or disconnect. A proxy must never silently replay an external
mutation. Reuse `McpRegistry`, `EffectApprovalService`, the artifact manager
and Run History rather than creating a parallel tool authority.

The harness process-facing adapter can take the form each qualified harness actually
supports: a generated configuration for a fixed stdio shim, a confined local
HTTP facade, or a native tool callback. Each must expose the same filtered
tool set and refuse unsupported protocol behavior. A harness that cannot
register one of these surfaces remains without brokered tools; merely adding
a server configuration file does not prove the harness loaded it.

For an upstream stdio server, the host can start a fresh reviewed, pinned
and isolated server process per step with only its named credential
environment. The host may reuse its credential reference, but the stdio
server can read the injected value and is part of the trusted boundary. The
current transport does not enforce a command pin or sandbox. Sharing one
stateful server process across steps is a later option only after tenant,
user, task, concurrency and state isolation are demonstrated. For remote
HTTP, the host can retain the OAuth state and attach an upstream token issued
for that exact server. The harness process receives neither the
refresh token nor upstream access token. The
[2026-07-28 transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
uses independent POST requests with no protocol session, while a 2025-11-25
server uses `initialize` and may assign an HTTP session identifier. Negotiate
the exact supported protocol and qualified adapter; do not assume one
session model fits both. The [official Python library](https://py.sdk.modelcontextprotocol.io/protocol-versions/)
documents discovery with an older-server fallback and an
[OAuth client provider](https://py.sdk.modelcontextprotocol.io/client/oauth-clients/)
with token storage. Those are reuse candidates, not current Loop Engine
behavior.

If the facade uses local HTTP, binding to loopback is not enough: authenticate
requests, validate `Origin`, reject DNS rebinding and keep the service inside
the declared namespace. The [current protocol transport specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
calls out these controls. A per-instance Unix socket is a simpler first
comparison because the existing model broker already uses one, but its
calling process and granted operations still need validation.

## Initial choices and ordered fallback

These are proposed choices for the future qualified integration. The current
confined model relay supplies the first part; the customer-side tool bridge
and per-use credential resolution do not yet run.

| Dimension | Initial choice | Fallback trigger and permitted next choice |
|---|---|---|
| Model credential delivery | Existing parent-side model broker; the harness process sees no real key. | If the customer-configured route is unavailable, choose only a separately eligible and explicitly authorized route. Otherwise report the missing endpoint, key, capability or reachability. Do not silently switch to direct harness process access. |
| Model endpoint placement | Parent calls the exact customer-configured endpoint from its own namespace. | A container or remote parent that cannot reach it needs a separately configured companion or tunnel. A public bind and a different provider are never inferred from `locality: local`. |
| Tool connection | Parent-owned, version-qualified Model Context Protocol connection behind a per-step tool bridge. | If a harness cannot use that bridge, select a separately qualified native connection profile with the customer's exact grants; otherwise return unavailable. Do not turn a tool error into a new login or repeat an uncertain effect. |
| Credential source | Local private reference resolved by the host at physical use. | Named runtime environment variable when the customer chooses it. An absent or revoked value stops the call and requests a new reference; it never becomes an empty secret or anonymous fallback. |
| Direct process injection | Disabled for the confined default. | An explicit trusted-adapter profile may inject only named credentials needed by one process or stdio server, with a bounded lifetime and no inherited parent environment. The receiving harness can read and potentially copy the value. This profile cannot claim credential isolation, model-call accounting, or spending enforcement unless independent egress or provider-side controls prove them. |

Environment variables are a practical compatibility mechanism, and the
[protocol specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
expects stdio servers to obtain credentials that way. They are not a secret
boundary from the process that receives them or from descendants it launches.
A short-lived local broker capability is also a secret, but it can be limited
to one step's operations, expire, and be revoked without rotating the
upstream provider credential. These delivery methods do not themselves
enforce the owning Loop's file, network, model, spending or external-effect
authority. The parent and sandbox must enforce those limits. A harness that
receives a real key and unrestricted network access can bypass the broker;
refuse that profile when exact call, spending or tool-effect bounds are
required unless independent controls demonstrate equivalent enforcement.

## Setup and evidence for a customer

The setup should ask separately where the engine runs, where the endpoint
runs, how the endpoint authenticates, what the model costs, and which tools
the step may use. Suggested choices: local Ollama without a key; local server
with a named key; direct cloud provider with a local credential reference;
native harness-managed account; and a third-party tool server with its own
authorization flow. Show the connection result from the **actual parent
namespace**. Keep configured, reachable, authenticated, model-qualified,
tool-discovered, native-loaded and independently accepted as distinct states.

The existing [provider guide](../guides/providers-and-keys.md) can describe
the supported setup paths after each is tested. Never display a raw secret
again after intake, include it in a URL or command, or put it in a task file,
prompt, downloaded skill, event, report or exported trace.

## Discriminating checks for Claude Code

1. Two fresh confined harnesses use one host-side `127.0.0.1` model route;
   neither sees the real endpoint credential, host environment or provider
   socket. One credential acquisition or consent and two separately accounted calls are
   observed. A container-parent variant fails reachability honestly.
2. Local unauthenticated Ollama, direct Ollama Cloud, an authenticated local
   proxy, and a locally signed-in cloud model are separate fixtures and live
   trials only under exact authority. Their credential and spending states
   cannot collapse into one `local` flag.
3. A revoked, expired, spent, wrong-instance or wrong-origin lease refuses
   before model or tool dispatch. The broker authenticates the caller rather
   than trusting a lease identifier copied into another step.
4. A tool facade lists only the selected tool schema. Wrong server, tool,
   argument digest, effect, scope, protocol version and cumulative budget
   each refuse before connection or approval consumption. Removing each
   guard fails a named check.
5. One upstream Model Context Protocol authorization serves two fresh steps
   without exposing its access or refresh token. Test both the 2025-11-25
   initialization path, including a server with an optional HTTP session
   identifier, and the 2026-07-28 independent-request path,
   including a token for the wrong audience and an expired token.
6. A harness process crash, cancellation, broker restart or lost upstream reply cannot
   replay a committed tool effect or record unknown use as zero. Revocation
   stops later calls and does not claim to undo an in-flight effect.
7. A URL containing userinfo or a raw credential query parameter, an
   unreviewed stdio command or untyped argument carrying a token, a literal
   endpoint `key=`, an inherited extra environment variable, a disclosed
   token in stdout, and a forged local HTTP `Origin` all fail their
   appropriate admission or disclosure checks. A named but unset Model
   Context Protocol `env:` credential must refuse before connection when
   that server requires it.
8. A harness whose native model or tool calls cannot be bounded is marked
   incompatible with a step demanding those limits. A passed process exit or
   tool listing is not evidence of material loading or accepted task work.

The first qualification can use local fake providers, tool servers and
deliberately invalid credentials. Real provider integration and native
harness claims need separately authorized calls and saved evidence. This
report proposes the connection design; it does not mark S-6.8 or S-6.31
complete.
