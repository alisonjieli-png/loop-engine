# Product style guide

Kind: operating guide. This is the initial design direction for the public
website, subscriber dashboard, setup instructions, and operational views.
Existing architecture terms remain governed by `humanizer-context.md`.

## Product voice

Lead with what a person can do: break a problem into clear steps, use relevant
expertise, reuse existing work, check results or manage access. Explain the required
account, permission, resource, and next action in plain English.

On the homepage and How it works, use Baltor, task, step, tools, model,
information and results. Do not display Loop, Loop node, Loop Engine, runtime
classification or role-profile explanations there, including the shared
footer. Technical documentation and GitHub retain the exact architecture
names, complete definitions and existing code identifiers. Public examples
illustrate work; they are not labeled executable runtime diagrams.

### Marketing language and factual claims are different things

Owner decision of 2026-09-21. Marketing language does not have to be
measurable, and treating it as though it must produces flat, lifeless copy
that says nothing. Two categories, and only one of them needs evidence.

**Write freely.** Evaluative and aspirational words, energy, and a strong
point of view. "Supercharge your developers and AI agents", "powerful",
"built for", "stop starting from nothing". A reader understands these as
the writer's enthusiasm, not as a measurement, and nobody is misled. Also
write freely about what the product is designed to do and about how it
works, because the mechanism is real and can be read in the source.

**These need evidence, every time.** A number nobody measured, such as a
percentage, a multiple or a time saved. A comparison to a named product.
The words guaranteed, always, never, every or any applied to an outcome. A
customer, a testimonial, a logo or a count of users that does not exist. A
capability the product does not have. Each of these is a statement of fact
that a reader can check and we cannot support, which is a different thing
from enthusiasm.

The test is simple. Ask whether a reasonable reader would take the sentence
as a fact they could verify. "Supercharge your agents" fails that test and
is fine. "Cut your token bill in half" passes it and needs data.

The [launch benefit guide](launch-benefits-and-evidence.md) records the
proof the three benefit themes need before they are stated as results
rather than as aims.

Keep statements about available behavior separate from planned work. Use
"candidate", "qualified", "unavailable", "failed", and "not verified" where
they describe the actual state. A subscription grants the declared service
access. It does not grant a model allowance, permission to execute code, or
access to a competition's data.

Describe what the product does and how it works, because that is observable in
the source. Do not state or imply a measured outcome that nobody has measured.
Write "give each step only the material it needs", not "cut your token bill".
Write "designed so a smaller model can finish a bounded step", not "solve
problems overnight". Where a benefit is an intention rather than a result, the
page says so in a sentence the reader will actually read, not in small print.
No percentage, no "always", no "guaranteed", no comparison to a named
competitor, and no invented customer, testimonial, logo or number.

Use full descriptive terms. Keep exact identifiers in technical details and
copyable configuration. Avoid hype, decorative slogans, invented performance
claims, em dashes, and en dashes. Artificial general intelligence remains a
research ambition.

## Names and where they may appear

Baltor is the public brand. Loop Engine is the repository, the Python package
and the technical name. This table is the single reference for where each
name and word may appear. It renames nothing.

| Name or word | Kind | What it names | May appear | Must not appear | Status |
|---|---|---|---|---|---|
| Baltor | Public brand | The product, the website and the hosted service as a customer sees them. | Every page that a customer reads, including the homepage, How it works and their shared footer. Email from the service. Copied client settings, where the entry is named `baltor` and the credential variable is `BALTOR_SERVICE_TOKEN`. Technical documentation when it describes the product. | In place of a code identifier, a package name, a record type, a contract field or the repository name. | Decided by the owner. |
| Loop Engine | Technical name | The repository, the engine, the Python distribution and command `loop-engine`, and the Python import `loop_engine`. | Technical documentation, the Documentation view of the website, GitHub, the README, source code and command output. | The homepage, How it works and their shared footer. | Decided by the owner. |
| Building with Loops | README title | The title of the public README. | The README. | Anywhere as a product name. | Decided by the owner. |
| task, each step, information, tools, model, checks, results, reusable solution | Public words | The work as a customer describes it. | Every page. On the homepage, How it works and their shared footer, only these words describe the work. | In technical documentation, in place of an exact runtime term. | Decided by the owner. |
| Loop, Loop node, discrete cognitive or act step Loop node, runtime classification, role profile, Practitioner, Intelligence, Solution, run mode, step profile | Technical words | The exact runtime terms with their complete definitions. | Technical documentation, the Documentation view of the website, GitHub and source code. Keep the full phrase [discrete cognitive or act step Loop node](../../ASTRA.md#complete-behavioral-explanation) together with its complete behavioral explanation. | The homepage, How it works and their shared footer. | Decided by the owner. |
| agent, AI agent | Customer words | The thing the customer runs, in the words the customer already uses for it. | Every page a customer reads, including the homepage and How it works. | In place of a code identifier, a record type or the exact runtime term in technical documentation. | Changed on September 21, 2026. The reason is below the table. |
| harness, prompt cycle | Technical words | The customer's own tools and how they call a model, in the words this repository uses for them. | Technical documentation, connection guidance and GitHub. | The homepage, How it works, Get started and their shared footer. Write "your coding tool". | Decided by the owner. The [public content direction](public-website-content-and-domain.md#current-positioning-and-presentation) records it. |
| pilot, beta, private beta, early access | Retired words | A trial. Being invited changes only who can create an account. | Nowhere on a page a customer reads. Dated records and historical evidence keep their original wording. | Every page a customer reads. Write "accounts open in small groups", "invited member", "join the waiting list" and "X is being built". | Changed on September 21, 2026, on the owner's direction. |
| `le_` | Customer-visible technical identifier: key prefix | The first characters of every client key that the service issues. | Issued keys, and technical documentation that explains them. | The homepage, How it works and their shared footer. | Open owner decision. Do not rename it. |
| `loop-engine-intelligence` | Customer-visible technical identifier: protocol server name | The server name that a Model Context Protocol client shows after it connects. | The protocol handshake and technical documentation. | The homepage, How it works and their shared footer. | Open owner decision. Do not rename it. |
| `X-Loop-Engine-Record-Type` | Customer-visible technical identifier: response header | The header on a downloaded body that names its record type. A browser client can read it. | Service responses and technical documentation. | The homepage, How it works and their shared footer. | Open owner decision. Do not rename it. |
| `Loop Engine Intelligence` | Customer-visible technical identifier: protected resource name | The `resource_name` field of the protected resource metadata at `/.well-known/oauth-protected-resource`. A client can show this name to the person who authorizes it. The service returns that record only when the host configuration lists the authentication mode `external_jwt`. The pilot lists only `host_key`, so the pilot does not return it today. | The protected resource metadata and technical documentation. | The homepage, How it works and their shared footer. | Open owner decision. Do not rename it. |
| `loop-engine` | Customer-visible technical identifier: command and package name | The command that a customer types and the package that a customer installs. | Installation and setup instructions, the Documentation view of the website and technical documentation. | The homepage, How it works and their shared footer. | Open owner decision. Do not rename it. |

### Why the word agent is now allowed on a customer page

An earlier row of this table kept "agent" off the homepage and How it works,
next to "harness" and "prompt cycle". That row was changed on September 21,
2026, and the reason is recorded here rather than left as a silent break.

1. It is the word the buyer already uses for the thing they run. The owner's
   own direction for the homepage proposes "Give your AI agents what they
   need", and the reader is a developer who calls their tool an agent.
2. It is a customer word, not a runtime word. The rule that matters keeps
   Loop, Loop node, Loop Engine, runtime classification, role profiles and
   Practitioner off the public pages, and that rule is unchanged.
3. "harness" stays off the public pages. It is jargon that only this
   repository and a small group use. Write "your coding tool".

The category line "Harness and agent optimized operation" was retired from
the homepage in the same change, because it carried "harness" and because the
owner's later direction rewrites the top of the page. The recorded decision
table in `CLAUDE.md` still names that phrase under public positioning. An
operator should update that row so the record and the page agree. Engineering
does not edit that file.

### Open owner decision: identifiers that carry the engine name

Five identifiers in the table are visible to a customer and still carry the
engine name. The key prefix `le_` is set in
`src/loop_engine/core/service_runtime/runtime.py` and `access.py`. The
protocol server name `loop-engine-intelligence`, the response header
`X-Loop-Engine-Record-Type` and the protected resource name
`Loop Engine Intelligence` are set in
`src/loop_engine/core/service_runtime/http.py`. The command `loop-engine` is
the Python distribution name. The older worker command `loop-engine serve api`
also reads the request header `X-Loop-Engine-Key`. It is not the product
service.

The service display name is a setting, not a fixed identifier. The field
`display_name` of `ServiceHttpConfiguration` in the same `http.py` has the
default value `Loop Engine`. The service shows that value in the page title,
the header and the shared footer of the website, and in its public
capabilities record. The public capabilities record of the pilot reports
`Baltor`, and the value can only come from the host configuration, so the
host configuration of the pilot sets it. A self-hosted service that does not
set it shows `Loop Engine` in those places. Whether that default changes
belongs to the same owner decision. The help text of the service command also
names Loop Engine. That is command output, where the technical name may
appear.

This list covers what a search for the engine name found in
`src/loop_engine/core/service_runtime/` and its served website files on
September 20, 2026. Repeat that search before the owner decides, because a
later change can add another identifier.

The owner has not decided whether these identifiers stay as they are or
receive Baltor names. Until the owner decides, do not rename them and do not
hide them. A rename is a contract change, not a copy change. Issued keys
already begin with `le_`. A client can display or store the server name and
the protected resource name. A browser client reads the header by its name.
Installation instructions depend on the command. A rename therefore needs a
new explicit version, updated callers and checks in the same change, and an
explicit refusal of the old form where the [version policy](../architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md)
requires one.

## Page structure

The public website should have a clear explanation, examples, catalogue
previews, accurate pricing, installation guidance, documentation, and sign-in.
Show the supported client and protocol versions beside connection guidance.

The subscriber dashboard should organize work by user goals: connect a
client, browse intelligence and templates, inspect a task graph, view history
and usage, manage access, and manage billing. Keep operator-only controls
behind the appropriate role. Empty states should explain what is missing and
provide the next supported action.

Show a task's goal and state before implementation details. Graph views can
reveal role, exact profile, mode, typed input and output, conditions, and
relationships when a user inspects a Loop. Passive records, files, ports,
services, and edges must not appear as executable vertices.

## Visual foundations

Use a restrained technical style with readable typography, clear spacing,
and little decoration. Start with the following proposed design tokens and
adjust them through visual checks in the actual application:

| Token family | Initial direction |
|---|---|
| Typography | System sans-serif for interface text; system monospace for commands and identifiers; 16-pixel body text. |
| Spacing | Multiples of 4 pixels, with 16 to 24 pixels between related sections. |
| Content width | Comfortable reading width for guides; wider tables and graph views when inspection requires it. |
| Color | Neutral surfaces and one principal action color; distinct success, pending, warning, and failure treatments with text labels. |
| Controls | Visible labels, clear focus treatment, consistent heights, and adequate touch targets. |
| Density | Compact catalogue rows; progressive detail for evidence, versions, and permissions. |

Support light and dark appearance. Verify contrast against the actual surface.
Never use color as the only indication of state. Respect reduced-motion
preferences. Test keyboard navigation, screen-reader labels, responsive
layouts, loading, empty, denied, failed, and expired-session states.

## Catalogue and evidence presentation

Each capability page should show its purpose, kind, source, version, digest,
license, qualification scope, declared effects, compatible harnesses, and
required access. Show how to obtain it and what the harness will actually see.
Distinguish offered, fetched, loaded, exposed, used, and independently verified
material. These are not synonyms.

Do not present a confidence percentage without explaining its basis. Keep
unknown cost and missing usage visible. A customer-reported result needs that
label; it cannot appear as independently verified merely because the service
received it.

## Setup and billing flows

Every setup page names prerequisites, versions, commands that exist, expected
output, the next step, and the failure recovery path. Provide copy controls
for commands without embedding real secrets. Do not place secrets in example
URLs, screenshots, recordings, or exported diagnostics.

Billing pages state the unit, allowance, renewal terms, and what happens when
access changes. Cancellation and access revocation should be discoverable.
Payment completion, subscription activation, and a successful client
connection are separate observed states.

## Design acceptance

Before launch, complete the same new-user journey on a narrow mobile layout
and a desktop layout. Check long capability names, empty catalogues, refused
permissions, an expired login, a failed payment, an unavailable model route,
and a disconnected client. Save screenshots and browser checks for the exact
release candidate. A static mockup does not pass this gate.
