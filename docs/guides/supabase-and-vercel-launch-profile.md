# Supabase and Vercel launch profile

Kind: proposed deployment profile. Sources checked: 2026-09-19.
No account, region, paid plan, or production deployment is selected by this
document. The [portable hosting procedures](hosting-and-deployment-procedures.md)
remain the common operating contract.

Vercel, Supabase, and Stripe are a strong candidate combination for the first
release. The product serves intelligence to customer-run harnesses, so its
hosted surface does not need to run the customer's full problem-solving work.
Keep the existing Python domain implementation portable while evaluating
whether its serving slice fits Vercel Functions or a small container service.
This is an engineering recommendation, not measured deployment qualification.

## Runtime classification

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

Hosting products, database adapters, authentication services, and payment
providers are infrastructure and internal mechanics. They do not add runtime
types or grant authority to a Loop.

## Proposed allocation

```text
First hosted product
├── Vercel
│   ├── public website and installation instructions
│   └── subscriber dashboard and consent interface
├── Supabase
│   ├── authentication and optional protocol authorization
│   ├── Postgres catalog, tenant, entitlement, and usage records
│   └── private object storage for larger intelligence bodies
├── Stripe
│   └── subscriptions and billing events through a payment adapter
└── Portable Python intelligence service
    ├── protocol and web request adapters
    ├── the existing access, qualification, retrieval, and metering rules
    └── Vercel Functions or one qualified container hosting profile
```

Supabase Auth documents user authentication and an OAuth 2.1 server with
discovery, client registration, consent, and token management for Model
Context Protocol clients. A Python resource server can use a standards-based
identity adapter without replacing the existing domain code. Qualify the exact
authorization package, client, and protocol versions before selecting one;
an integration mentioned in documentation is not an observed working path.
[Authentication architecture](https://supabase.com/docs/guides/auth/architecture),
[protocol authentication](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication).

Stripe provides the subscription lifecycle. Translate authenticated payment
events into one durable entitlement decision used by the dashboard and
protocol service. A successful browser redirect is not proof of payment.
[Subscription lifecycle](https://docs.stripe.com/billing/subscriptions/overview).

## Two Python deployment candidates

| Candidate | Advantage | Qualification required |
|---|---|---|
| Website and stateless Python serving on Vercel, durable state in Supabase | Fewer hosting systems to operate. | Actual application packaging, cold starts, request and body limits, protocol streaming, disconnect handling, database pooling, and authorization discovery. |
| Website on Vercel, durable state in Supabase, Python service in a container | Retains the existing Python service shape and allows independent resource settings. | Image, service health, process restart, region alignment, database connections, network policy, and the same client acceptance suite. |

Vercel supports Python web applications and streaming responses. Its standard
Python bundle limit is 500 megabytes; a larger public-beta option exists.
Build the lean serving dependencies and measure the result instead of
installing every data-science extra. Functions still have duration and resource
limits. Do not rely on process-local sessions or local files as durable state.
[Python runtime](https://vercel.com/docs/functions/runtimes/python),
[function limits](https://vercel.com/docs/functions/limitations).

Supabase Edge Functions are another possible thin request adapter. Their
documented hosted limits include 256 megabytes of memory and two seconds of
active processor time per request. That is a reason to measure the serving
work and preserve the Python service boundary, not to move the entire engine
there or rewrite its rules in a second language for deployment convenience.
[Function limits](https://supabase.com/docs/guides/functions/limits).

## Data and authorization requirements

Keep compact searchable metadata in Postgres. Keep large instructions,
program bodies, and exported packages in private object storage with exact
versioned references and digests. The existing local SQLite and DuckDB
adapters remain separate local deployment options; they are not writable
shared production databases merely because a function can open a file.

Supabase row-level security is an additional enforcement layer, not a
replacement for Loop Engine's qualification, license, tenant, and entitlement
decisions. Keep administrative credentials out of browser code and tool
arguments. Test two tenants, revoked membership, expired access, wrong
audience, forged claims, and stale body identity before enabling public access.
[Row-level security](https://supabase.com/docs/guides/database/postgres/row-level-security).

Use current versioned contracts at the existing store, authentication,
artifact, and payment boundaries. Keep provider-specific settings in the
deployment profile. Portability means that another implementation passes the
same contract tests; it does not mean every provider is already supported.

## Cost and recovery controls

Vercel's Hobby plan is for non-commercial use. Its Pro platform fee is
currently 20 United States dollars per month with one deploying seat and
usage credit. Supabase Pro starts at 25 United States dollars per month.
Together, those starting plan fees are about 45 United States dollars per
month, before usage, additional compute, a separate service, payment fees,
email, domains, taxes, and optional features. This is not a spending ceiling
or an approved purchase.
[Vercel plans](https://vercel.com/pricing),
[Vercel Pro](https://vercel.com/docs/plans/pro-plan),
[Supabase pricing](https://supabase.com/pricing).

Supabase's spend cap excludes compute and several explicitly enabled
features. Review the complete projected bill and configure independent
spending alerts. Its database backups exclude object-storage contents, so
backup and restore tests must cover both records and intelligence bodies.
[Cost controls](https://supabase.com/docs/guides/platform/cost-control),
[backup coverage](https://supabase.com/docs/guides/platform/backups).

## Acceptance before selection

Prepare both Python candidates with the same application and contract tests.
Measure installation size, first and subsequent requests, authorized search
and body retrieval, incorrect and revoked credentials, duplicate payment
events, usage persistence, restart, and restore. Record platform-specific
failures rather than silently moving state or changing contract semantics.

Other supported hosting families remain in the portability guide. Do not add
a separate queue, cache, vector database, identity provider, or monitoring
vendor unless a measured requirement needs it. Optional components can remain
behind the current interfaces without becoming launch dependencies.

The owner still needs to choose account ownership, region, public domain,
initial price, permitted paid plans, and a spending ceiling. Local build and
verification work can continue before those choices.
