# Server language recommendation

Date: 2026-09-19. Status: architecture recommendation, not deployment qualification.
Repository inspected: `main` at `48cc954322691e492aad69a465ba470a112730e7`, with
the current uncommitted implementation. No runtime code was changed.

Keep the qualification, disclosure, retrieval, and metering rules in Python
for the first release. Use TypeScript for the website and dashboard. Start
with a Python web and Model Context Protocol adapter around the same domain
implementation. Add a thin TypeScript or Deno adapter only when a tested
hosting or client requirement justifies it. Do not rewrite the domain simply
because the website uses TypeScript or the identity provider is Supabase.

This recommendation is an engineering inference from the existing code and
the official documentation below. It is not a measured claim that Python is
faster, cheaper, or always preferable.

## Execution classification does not change

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Language and deployment services are implementation choices, not additional
executable graph vertices. Customer task execution remains customer-run.

```text
Proposed first-release allocation
├── TypeScript website and dashboard
│   └── presentation, setup, sign-in and subscription interfaces
├── Python intelligence service
│   ├── web and Model Context Protocol request adapters
│   └── one qualification, disclosure, retrieval and metering implementation
├── External identity and payment providers
│   └── identity tokens and authenticated payment events, not item approval
├── Durable catalog, entitlement and artifact adapters
│   └── versioned store interfaces, independent of serving language
└── Customer-controlled Loop Engine execution
    └── graphs, harnesses, scoped effects, verification and local Run History
```

## What the repository actually contains

The domain in [provisioning_server.py](../../src/loop_engine/core/provisioning_server.py)
already checks exact tenant grants, source bindings, qualification responses,
body digests, and committed usage acknowledgments. The protocol adapter invokes
that domain through the canonical Loop. Reimplementing these rules would create
another behavior set to qualify, not just another serializer.

[pyproject.toml](../../pyproject.toml) keeps the default dependencies to
`PyYAML`, `jsonschema`, and conditional `tomli`. Data-science libraries are
optional. The integration extra declares `mcp>=1.29,<2`; the inspected
environment has `mcp==1.29.1`.

A fresh-interpreter import probe of `provisioning_server`, `provisioning_mcp`,
and `intelligence_layers` loaded none of `numpy`, `pandas`, `sklearn`, `torch`,
`lightgbm`, `xgboost`, `duckdb`, `lancedb`, or `model2vec`. This only establishes
import behavior. It is not a deployment-size, cold-start, or throughput test.
Actual protocol operation also requires its declared runtime dependencies,
including the Model Context Protocol package, `anyio`, `pydantic`, and
`jsonschema`.

The current [provisioning transport](../../src/loop_engine/core/provisioning_mcp.py)
is in-process, uses a host-bound credential, and permits `2025-11-25` only.
It explicitly reports no remote web transport or OAuth support. The generic
web service is not a completed hosted provisioning application.

Important missing work is language-independent: authoritative qualification
adapters across all four intelligence layers, authenticated template and graph
delivery, durable usage and billing reconciliation, and production storage.
The reference meter is process-local. The server also holds a process-local
lock across request dispatch. Neither becomes horizontally consistent merely
by changing language.

## Current official protocol support

Both official Python and TypeScript repositories identify version 2 as the
stable release line implementing the `2026-07-28` specification. Python supports
Streamable HTTP; TypeScript supports Node.js, Bun, and Deno. Current protocol
availability is therefore not a TypeScript-only advantage.
[Python software development kit](https://github.com/modelcontextprotocol/python-sdk),
[TypeScript software development kit](https://github.com/modelcontextprotocol/typescript-sdk).

Both provide resource-server authorization support while leaving token
verification and application policy to the application. An identity provider
signs users in and issues tokens. Loop Engine still checks tenant membership,
entitlement, exact item approval, and revocation. Token validity is not
permission to disclose every catalogue item.
[Python authorization](https://py.sdk.modelcontextprotocol.io/run/authorization/),
[TypeScript authorization](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/serving/authorization.md).

The newer protocol changes discovery and connection behavior. An upgrade is
not just changing a dependency bound. Keep an explicit supported protocol
profile and test its discovery, authorization, cancellation, retries, and
unsupported-version refusal. Do not inherit automatic legacy fallback merely
because an upstream client offers it.
[Python protocol versions](https://py.sdk.modelcontextprotocol.io/protocol-versions/).

Supabase documents OAuth 2.1 authorization for Model Context Protocol clients.
Its current deployment tutorial uses the official TypeScript version 2 package
and a fresh server per request. That is a viable thin-adapter option, not proof
that Loop Engine's domain must move into that runtime. Using Supabase identity
with a Python resource server is a standards-based integration proposal that
still needs our acceptance tests.
[Supabase authorization](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication),
[Supabase server tutorial](https://supabase.com/docs/guides/ai-tools/byo-mcp).

## Hosting and language are separate choices

Vercel documents Python web applications and streaming responses. Its Python
page, updated August 12, 2026, states a standard 500 megabyte uncompressed
bundle limit and no automatic Python tree-shaking. A five gigabyte option is
public beta. Package only the serving dependencies and measure the actual
artifact; do not install the full data extra.
[Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python).

The current Vercel limits page gives Node.js, Bun, and Python the same listed
Fluid compute duration table: 300 seconds by default, 800 seconds generally
available on Pro and Enterprise, and an 1,800-second beta extension under
additional conditions. It also lists a 4.5 megabyte request or response payload
limit. Switching to TypeScript does not remove those platform limits. Large
artifact delivery needs a qualified storage-delivery contract, not an
assumption that every package fits a tool response.
[Vercel limits](https://vercel.com/docs/functions/limitations).

Supabase Edge Functions use a TypeScript-first Deno-compatible runtime. Their
hosted limits currently include 256 megabytes of memory and two seconds of
processor time per request, excluding asynchronous input/output waiting.
A small adapter may fit; the complete Python engine cannot be assumed to run
there unchanged. Keep a portable Python container deployment as an alternative
to Vercel Functions.
[Supabase runtime](https://supabase.com/docs/guides/functions),
[Supabase limits](https://supabase.com/docs/guides/functions/limits).

## Comparison for this first release

| Choice | Main benefit | Main cost or risk | Recommendation |
|---|---|---|---|
| TypeScript website with Python service | Preserves one tested domain while allowing normal website tooling. | Two language environments; remote authentication and storage still need implementation. | Preferred starting point. |
| Thin TypeScript or Deno transport calling Python | Fits a proven platform-specific request or authentication integration. | Extra network boundary, identity propagation, failure handling, and duplicate-charge risk. | Add only for a demonstrated requirement. |
| Full TypeScript or Deno domain rewrite | One server language and direct use of its ecosystem. | Requalification of disclosure, identity, graph, admission, storage, and accounting semantics. | Not justified by current evidence. |
| Go service or bounded component | An option when a measured deployment or concurrency requirement favors it. | New implementation and operational surface. | Revisit after profiling and contract tests. |
| Rust service or bounded component | An option for measured processor-heavy work or a specific memory-control requirement. | New implementation, integration, and qualification work. | Prefer a narrow proven bottleneck over a rewrite. |

Official Go and Rust implementations also document `2026-07-28` support.
That establishes alternatives exist, not that either outperforms this workload.
No cross-language benchmark was run.
[Go software development kit](https://github.com/modelcontextprotocol/go-sdk),
[Rust software development kit](https://github.com/modelcontextprotocol/rust-sdk).

## Actionable next steps

1. Freeze the domain contracts and their negative checks. Keep qualification,
   entitlement, retrieval, and metering decisions in one Python authority.
2. Qualify a current Python protocol profile and a small web application
   entrypoint. Keep the older tested profile explicit until the replacement
   passes; do not silently broaden negotiation.
3. Implement identity verification and durable entitlement and usage adapters.
   If a TypeScript adapter is added, authenticate that internal boundary,
   preserve exact request identity, and never trust a caller-supplied tenant
   header or convert an unknown commit into success.
4. Run the same acceptance population on a portable Python container and the
   proposed Vercel profile. Measure artifact size, startup, concurrent retrieval,
   body limits, disconnects, revocation, restart, and usage persistence. Keep
   all failed cases. No such deployment comparison has been performed here.
5. Reconsider language only if those measurements isolate a language-specific
   problem that cannot be reasonably fixed at the existing adapter or storage
   boundary. Do not attribute a catalogue scan, blocking callback, database
   query, or process-local lock to Python without that evidence.

Sources were opened on September 19, 2026. Repository and documentation main
branches are mutable; the version statements above are observed release-line
claims, not a nominated dependency lock. No library was upgraded, account
created, provider called, paid resource used, or untrusted code executed.

Retrieval discrepancy: the coordinating agent received a representation of
the Supabase authorization page that explicitly linked a built-in FastMCP
integration at `https://gofastmcp.com/integrations/supabase`. This agent's
retrieved representation instead emphasized the TypeScript deployment guide.
The differing representations do not establish that the FastMCP integration
is absent. Neither retrieval qualifies an exact package, protocol profile, or
Loop Engine integration. The recommendation does not depend on that disputed
documentation detail.
