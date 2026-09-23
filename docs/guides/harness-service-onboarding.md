# Harness service installation and onboarding

Kind: operating guide and acceptance plan. The local engine commands, Python
service, authenticated transport, and same-origin subscriber workspace are
implemented. Local checks exercise search, downloads, usage, and
payment-session routes without real provider accounts. A private pilot of the
service is deployed for Baltor; the
[current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
section records what runs. Automated account signup and live payment
qualification remain work under the
[continuation plan](../roadmap/CONTINUATION-AND-LAUNCH.md).

Start with the [launch setup runbook](launch-setup-runbook.md) for account and
hosting instructions and the [decision-tool guide](jev-and-harness-decision-tools.md)
for optional Jev configuration. A configured client is not evidence of a
successful provider call or native harness use.

## The user journey

The frontend must take a new user through installation, account sign-in,
subscription, client authorization, provider configuration, intelligence and
template selection, a task graph, and the first independently checked result.
Every page names the tested operating system, package, harness, protocol, and
provider versions. Provide expected output and a remedy for each failed step.

The user's model credentials stay with the authorized client or credential
host. Paying for intelligence access does not include a model allowance,
permission to execute code, or access to third-party datasets.

## Install and inspect the existing engine

Use the [installation guide](../getting-started.md) for the tested environment
and the [main README](../../README.md) for current installation options.
Inspect configuration without a provider call:

```bash
loop-engine doctor
loop-engine configure
loop-engine extensions providers
loop-engine models inventory
```

The command-line `configure` operation inspects configuration. The similarly
named Python helper can make real provider calls. The frontend instructions
must distinguish them.

Before publishing installation instructions for a release, install its exact
distribution in a clean environment and run the supported walkthrough. Show
the installed release version; a moving branch URL is not a reproducible
release identity.

## Sign in and connect a protocol client

The planned dashboard should show the user's service URL, supported protocol
versions, granted scopes, subscription entitlement, and connection status.
Generate client-specific configuration from a tested template. Use the
selected authorization flow; do not ask users to paste private tokens into
URLs or publicly shared configuration.

Test discovery, a scoped search, one manifest, a selected body with digest
verification, an expired session, and revocation. A successful connection
does not prove that the harness loaded or used a skill. Record each of those
observations separately.

Current behavior: the source in this repository serves Model Context
Protocol versions `2025-11-25` and `2026-07-28` at the same endpoint. A client
reaches `2025-11-25` through the `initialize` handshake. When it asks for
another version there, the answer names `2025-11-25`, as the lifecycle rule of
that version requires, and the client decides whether to continue. A client
reaches `2026-07-28` with no handshake, naming the version on every request.
Any request that names a version the service does not serve is refused before
any effect with the error that lists the served versions. A deployment serves
this after a release that includes the change of September 22, 2026; the
release that ran on September 21 served `2025-11-25` alone. The versions are
documented in the
[2025-11-25 transport specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports),
the
[2025-11-25 authorization specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization),
the
[2026-07-28 transport specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
and the
[2026-07-28 versioning rules](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning).
Client templates must identify their tested compatibility profile.

## Configure local Ollama

Install and run Ollama using its [official quickstart](https://docs.ollama.com/quickstart).
Select a model that fits the machine and the intended work. Configure the
existing native Ollama custom-endpoint adapter using the local server URL,
typically `http://127.0.0.1:11434`, and a source-backed output capability.
Use the repository [provider guide](providers-and-keys.md) and
[custom endpoint guide](custom-endpoints.md) for the declared route fields.

Inspect the route first. A live probe is a separate authorized action. The
guide must explain missing models, unavailable servers, incompatible thinking
settings, insufficient resources, and unknown output capacity. Locality does
not grant file, network, or execution authority.

## Configure Ollama Cloud

Use the [official cloud guide](https://docs.ollama.com/cloud) to establish the
provider account and credential. The built-in Loop Engine provider reads the
`OLLAMA_API_KEY` reference. Keep the value outside source files and exported
diagnostics. Use the repository's
[provider verification instructions](providers-and-keys.md#preferred-first-setup)
for an explicitly authorized probe.

A model appearing in a listing is not proof that its generation allowance is
available. Explain `usage_limit_reached`, authentication failure, unsupported
settings, and exact-request token-bound refusal. Do not silently replace a
failed route, infer a paid allowance from a subscription, or weaken a declared
budget to make the walkthrough pass.

## Configure Kaggle

Use a Kaggle account with the required credentials and personally accepted
rules for the selected competition. Keep credentials outside generated
packages and Run History. The frontend should distinguish access setup,
download authority, local experimentation, and submission authority.

The [existing competition example](../../examples/05_kaggle_competition/README.md)
is a narrow top-level delimited-table workflow. It is not a general claim
about arbitrary competitions, nested archives, image tasks, or official
leaderboard results. Do not submit merely to prove that configuration works.
Start the walkthrough with local fixtures, then perform an authorized data
access check and a separately approved submission when needed.

## One harness for each atomic assignment

The setup pages must demonstrate a concrete task decomposed through the
canonical graph contract into typed subgraphs and atomic assignments.
Show the assignment contract, selected resources, initial harness, ordered
fallbacks, workspace scope, and independent acceptance check. The client
executes the selected harnesses locally or through the customer's approved
environment; the intelligence subscription service need not execute them.

The complete meaning of a discrete cognitive or act step Loop node is retained
in the [continuation plan](../roadmap/CONTINUATION-AND-LAUNCH.md#complete-behavioral-explanation)
and the [original explanation](../context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md).
The actual frontend guide must include that explanation, not replace it with
an unexplained label. An assignment can iterate, publish alternatives, and
continue within its conditions and authority. Publication is separate from
completion, and repeated external effects require their own protection.

## Required frontend pages and tests

| Page | Acceptance |
|---|---|
| Install | A clean environment installs the exact release and passes diagnostics. |
| Account and subscription | Sign-in, checkout, activation, billing management, and cancellation have distinct observed states. |
| Connect a client | A supported client authenticates and accesses only entitled material. |
| Intelligence and templates | All permitted layers and template families can be searched; body access requires selection and qualification. |
| Local Ollama | A declared local route is inspected and, when authorized, actually answers. |
| Ollama Cloud | Credential, route, capacity, allowance, and budget failures have correct explanations. |
| Kaggle | Credentials and competition access are distinguished from permission to submit. |
| Task graphs and harnesses | A real assignment has typed graph relationships, separate harness resources, and independently checked outputs. |
| Recovery | Restart, revoked access, failed provider, missing skill, and failed verification preserve useful work and explain the next action. |

Save the release identity and the browser or command output for each tested
page. Pending or unavailable profiles remain visibly unqualified.
