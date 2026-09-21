# Public website content and domain direction

Kind: public-content direction and publication limits. The owner selected
Baltor as the public brand. This document does not authorize a new domain
change, account creation or payment activation.

The complete single-file system map is an internal engineering reference.
The public website should explain the customer benefit and supported workflow
without shipping internal planning records or the full source inventory.
Use shared, release-bound facts so public copy and engineering status agree.

## Current positioning and presentation

The category line is "Harness and agent optimized operation". That is the
owner's phrase, recorded in the September 20 direction. It appears as the
first line of the homepage, above the headline, and in the page description.

The homepage leads with "Turn complex problems into reusable solutions."
Its subject is the result a person can keep, run again and adapt. Model
selection, useful information, tool choice, code reuse and verification
explain how the product is intended to produce that result.

The homepage sections run in this order:

```text
Homepage
├── Category line and headline
│   ├── One primary action
│   └── One secondary action to How it works
├── Three step strip: connect, ask, keep
├── The five customer problems
├── One workflow for the decisions behind the work
├── What an account gives you: search, selected downloads,
│   connection settings and usage
├── The four persistent intelligence layers
├── A starting point for every step
├── Pricing summary with a link to the pricing view
└── Closing action and the limits note
```

The primary action has two states and the page never chooses between them by
itself. It reads `website.registration_available` from `/api/v1/capabilities`.
When the service reports registration, the action reads "Get started" and
leads to `/signup`. Otherwise it reads "Request access" and leads to
`/signup#request-access`, where the page explains that access is by
invitation. Before the service answers, and if it never answers, the page
keeps the careful state. The same rule drives the payment state on the
pricing view, which reads `billing.checkout`, and the personal-key wording
on the homepage and the pricing view, which reads
`website.client_access_available`. While that field is false, both places say
that creating and revoking a key for each device is being prepared and that
the person who runs the service issues the key. The deployed release reports
it as false, so the page may not state the control as working today.

The page reads those three fields only from the record version it was written
against, `service_capabilities/v1`. Any other record version keeps the careful
state, because another version may rename a field or give it a different
meaning. The careful wording is also the wording the server sends, so a
visitor whose browser does not run the page script reads the honest statement
instead of "Checking payment".

`tools/check_service_workspace.mjs` holds every state as a named check. Each
state is produced by a real service on its own loopback origin, not by a
rewritten reply, and nine removed-guard controls prove that a page which
ignores the reported state, or which ignores the record version, fails a
named check.

Do not position Baltor as a context-layer product. Context is one input to
work whose execution can also use an existing function, a small decision
call or a native harness. Keep "agent", "harness", "prompt cycle" and
precise Loop terminology in technical documentation and GitHub. The owner
explicitly excludes those internal terms from the homepage and How it works.
Use each step, selected information, tools and checked results on those pages.
Do not rename the repository, runtime or serialized contracts.

The five customer problems are excessive context, expensive models applied
indiscriminately, missing domain expertise, regenerated code and repeated
mistakes. Pair each question with a specific approach, not an invented
percentage improvement. More context or a more capable model can be justified
when it improves the required outcome.

The website defaults to light appearance, with white surfaces, restrained
blue accents, readable spacing and an optional dark appearance. Hosting
diagrams belong on How it works. The public homepage should not open with
where a container runs, a source inventory or an internal release checklist.

The broader product remains under development. Do not promise to replace
specialist teams, solve every problem, select a globally optimal model or
improve performance every day. Compare total cost and accepted outcomes,
including preparation, retries and verification, before claiming savings.

## Connection guidance from adjacent products

[SenseLab](https://www.sense-lab.ai/) makes its public entry sequence short:
account, credential, then client connection. Its authenticated setup was not
reviewed here; the application entry required sign-in.
[Stripe's connection guide](https://docs.stripe.com/mcp) provides separate
client instructions, distinguishes OAuth from keys, explains permissions
and documents how access is revoked. Those are useful interface patterns,
not evidence that Baltor already supports the same authentication methods.

The next connection interface should guide a person through obtaining a
scoped test token, selecting an exact supported client version, copying
secret-free configuration, confirming a real connection and retrieving one
permitted reference. Native loading and successful use are later checks.
Show the actual server origin, protocol and authentication mode. Do not ask
for model keys to establish intelligence-service access.

### Structure survey, September 21, 2026

Four public pages for comparable developer products were read for structure
only. Nothing was copied. Observed on September 21, 2026; these pages change.

| Page | Structure worth reusing | Not reused |
|---|---|---|
| [SenseLab](https://www.sense-lab.ai/) | Category line above the headline, one primary action, a short strip explaining the idea, a named problems section, then pricing on the same page. Light surfaces and generous spacing. | Adoption counts, star ratings and customer logos. Baltor has no such evidence. |
| [Stripe connection guide](https://docs.stripe.com/mcp) | One reviewed configuration for each named client, the secret shown as a reference, and a separate section on revoking access. | Install links and one-click buttons for paths Baltor has not tested. |
| [Mem0](https://mem0.ai/) | A three step strip with plain verbs, and a short list of what the product gives you. | Developer counts, compliance badges and benchmark claims. |
| [Tavily](https://www.tavily.com/) | A hero that names the job in one line, then a small number of wide feature bands, and a closing action that repeats the primary action. | A metrics strip of latency, uptime and request volume. Baltor has no measured figures to publish. |

The shared pattern is: category line, one headline, one primary action, a
three step explanation, the problems, what you get, pricing, closing action.
The homepage now follows that order. The parts that every one of these pages
carries and Baltor does not are adoption numbers, customer names and measured
performance. Those stay off the page until there is saved evidence for them.

Copyable examples must use the client's supported secret-reference mechanism.
Do not publish an OAuth login button, install link or client support badge
before its real path is tested. The current email-free service token is not
a Stripe credential and is not a Supabase customer access token.

## Content by page

| Page | Suitable content | Hold back or qualify |
|---|---|---|
| Homepage | The category line, reusable solutions, one primary action, the three step strip, the five customer problems, what an account gives you, the four intelligence layers, the pricing summary and a closing action. | Unverified cost savings, automatic task-success promises, customer counts, uptime guarantees, and a signup or purchase button that does not work. |
| How it works | A concrete task becomes understandable steps: find useful information, choose an approach, reuse or build, and check the result. Explain what the service supplies and what the user's tools may send to a model. | No runtime taxonomy, Loop branding or unsupported end-to-end success claim. Technical definitions belong in documentation. |
| Getting started | Exact released package and supported platform, installation, inspection, one bounded working example, expected output, errors and recovery. | Working-tree-only commands must not be advertised as available from the published package or GitHub main branch. |
| Harness and context guide | The generated instruction and assignment files, reference-first context, permitted write locations, supported versioned native layouts, and observed loading status. | Empty folders and offered skill references are not installed or loaded material. Do not copy the entire repository into every instance. |
| Integration reference | Tested protocol version, request and response schemas, effects, authentication scopes, limits, refused combinations and version negotiation. | A listed adapter or successful import is not end-to-end support for every native client. |
| Security and privacy | Actual permission and disclosure boundaries, credential handling, retention settings, local versus external data flows, and known limitations. | Do not promise that all data stays local when queries or model calls can leave the machine. Do not claim formal certification or instantaneous in-flight revocation without evidence. |
| Examples | Small reproducible tasks with the exact configuration, observed result, evaluator and limitations. | Component fixtures are not full-system benchmarks or proof of general task-solving quality. |
| Research and roadmap | Dated experiments, candidates such as AutoRAG, measured failures, and a concise public roadmap. | Internal owner decisions, investor or acquisition research, detailed security findings before disclosure review, and old comparison cells presented as current facts. |
| Pricing and account pages | The plan name, the price, what is free, the measured unit, the beta entitlement, and the payment state read from the service. | A local signed-event fixture or a checkout redirect is not proof of a live paid service. Do not show a purchase button while the service reports that checkout is unavailable. |

## Pricing view

The pricing view answers at `/pricing`. It states one plan and nothing else.

| Fact | Published wording |
|---|---|
| Plan | Baltor Pro |
| Price | 29 US dollars each month |
| Free | Search is free |
| Measured unit | One downloaded item |
| Beta | Invited beta users are free |

These figures come from the owner's September 20 direction, recorded in
`CLAUDE.md`. Engineering may not change a figure on the page alone. Change the
recorded decision first, then the page, then the checks that hold the page to
it.

The payment state is not written into the page. The view reads
`billing.checkout` from `/api/v1/capabilities`. While that field is false the
view says plainly that payment is not open yet and shows no purchase button.
`tools/check_service_workspace.mjs` holds both states, and two removed-guard
controls prove that a page which always claims one state fails a named check.
The named check `pricing_view_offers_no_purchase_control_while_checkout_is_closed`
owns the rule against a purchase control in the closed state. It reads every
button, link, form and submit control inside the pricing view, and its
known-wrong case plants a "Subscribe now" control and requires the check to
report it.

Two things are still missing on September 21, 2026.

The serving route table does not yet list `/pricing`. A direct visit to
`https://baltor.ai/pricing`, a shared link, a bookmark and a reload while the
pricing view is open therefore return HTTP 401 with the JSON body
`{"record_type":"service_http_error/v1","error":{"code":"unauthorized"}}` and a
`WWW-Authenticate: Bearer` header, because an unknown address falls past the
served web assets into the authenticated dispatcher. The address works only
through a click inside the page, which the page handles itself. The exact
repair is one entry in `WEB_ASSETS` in
`src/loop_engine/core/service_runtime/http.py`:
`"/pricing": ("index.html", HTML_MEDIA_TYPE)`. That file belongs to the
service route owner, so the gap is held by the failing named checks
`pricing_address_is_served_on_a_direct_visit`,
`pricing_address_opens_the_pricing_view_after_a_reload`,
`responsive_<width>_/pricing` and `enlarged_text_<width>_/pricing`. Do not
release the navigation entries while those checks fail.

The account page holds the subscription controls, and those remain behind the
payment state.

The live public page describes a private pilot and the broader product direction.
Keep the internal report available to the owner, and build the public content
from an explicit allowlist. Hiding an internal panel with a browser control
does not remove its data from the downloaded file.

## Public content checks

1. Bind every available-feature claim and copyable command to a released
   revision and its verification evidence.
2. Check two tenants, denied and revoked access, wrong client versions,
   missing providers, model limits and incomplete output. Preserve failures.
3. Render Markdown as readable, sanitized documentation with working links.
4. Do not preload the complete repository inventory, internal worklist or
   compressed archives on public pages. Measure the smaller public payload.
5. Test keyboard use, contrast, narrow screens and representative mobile
   hardware. Browser width alone is not a mobile performance test.
6. Keep candidate, locally tested, native-client tested and live-provider
   qualified statuses distinct. Self-improvement remains an evaluated
   candidate workflow, not a promise of continuous gains.

Two check tools read the public pages. `tools/check_service_workspace.mjs`
reads a local service in a real browser. `tools/check_hosted_website.mjs`
reads a deployed origin. They enforce the same rule about the words that may
not appear on the homepage, How it works, the pricing view and the shared
footer, so both carry the same line, and the named check
`both_public_page_checks_use_one_plain_word_rule` compares the two. Change the
rule in both files together, or that check fails.

The text-size survey of September 21, 2026 recorded overflow that this work
did not introduce and does not own. At 200 percent text the workspace view
`/app` overflows by 74 pixels at 390 pixels wide, 104 pixels at 360 and 144
pixels at 320, and the sign-in view `/login` overflows by 22 pixels at 320.
The pages this guide covers, the homepage, How it works, the pricing view,
Connect, Examples and Access and data, showed no overflow at any measured
width or text size.

## Brand and existing domain

The owner reports owning `baltor.ai`, inspired by Balto, and selected Baltor
as the public-facing brand. Loop Engine remains the engine and repository
identity. The Python command, import, schemas and profiles must not change
merely to match marketing copy. The table
[Names and where they may appear](product-style-guide.md#names-and-where-they-may-appear)
lists where each name may appear. It also lists the technical identifiers
that a customer can see and that still carry the engine name. Those
identifiers are an open owner decision.

Baltor is short and pronounceable, and the existing domain avoids a new
purchase. Its meaning needs a short product description. Test whether people
who hear the name spell the final letter correctly. Use the Balto inspiration
as optional background on an About page rather than requiring visitors to know
the story.

The main caution is proximity to [Balto](https://www.balto.ai/), an existing
AI software brand. There are also other businesses named Baltor. This limited
search is not trademark clearance or a guarantee of exclusive use.

The pilot answers on four hostnames. All four serve the same release with
valid certificates. The
[current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
section is the current statement of these facts. Follow that section when
this guide differs from it.

| Address | State on September 20, 2026 | Purpose |
|---|---|---|
| `baltor.ai` and `www.baltor.ai` | Live | Public website, with `/how-it-works` and `/docs` paths. |
| `app.baltor.ai` | Live. It serves the same release as the public website. | Planned address of the signed-in subscriber dashboard. Browser sign-in is switched off today. |
| `baltor-pilot.fly.dev` | Live | The name supplied by the host. The host configuration still names it as the canonical protocol and account origin. |
| `api.baltor.ai` | Proposed only. No address record was found for it. | A possible separate address for the serving application and its exact `/mcp` resource. |

The first three rows are configured endpoints, not proposals. An earlier
version of this section called all of these addresses proposed. It was
corrected on September 20, 2026. Moving the canonical origin, a callback
address or a token audience to `app.baltor.ai` is separate migration work.
Follow the [endpoint migration design](../architecture/SERVICE-IDENTITY-ENDPOINTS-AND-MIGRATION.md#domain-migration-procedure).
Confirm exact allowed origins before changing another domain record. Website
sign-in and protocol authorization remain separate integrations.

The [publication review](../../artifacts/architecture-audit-2026-09-19/publication-adversarial-review.md)
records the current findings, source evidence and earlier domain checks.
