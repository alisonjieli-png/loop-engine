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

The [launch benefit guide](launch-benefits-and-evidence.md) separates proposed
overnight work, token efficiency and expert-context messages from their
required proof. Do not publish absolute or quantified claims without that proof.

Keep statements about available behavior separate from planned work. Use
"candidate", "qualified", "unavailable", "failed", and "not verified" where
they describe the actual state. A subscription grants the declared service
access. It does not grant a model allowance, permission to execute code, or
access to a competition's data.

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
| agent, harness, prompt cycle | Technical words | The customer's own tools and how they call a model. | Technical documentation, connection guidance and GitHub. | The homepage and How it works. | Decided by the owner. The [public content direction](public-website-content-and-domain.md#current-positioning-and-presentation) records it. |
| `le_` | Customer-visible technical identifier: key prefix | The first characters of every client key that the service issues. | Issued keys, and technical documentation that explains them. | The homepage, How it works and their shared footer. | Open owner decision. Do not rename it. |
| `loop-engine-intelligence` | Customer-visible technical identifier: protocol server name | The server name that a Model Context Protocol client shows after it connects. | The protocol handshake and technical documentation. | The homepage, How it works and their shared footer. | Open owner decision. Do not rename it. |
| `X-Loop-Engine-Record-Type` | Customer-visible technical identifier: response header | The header on a downloaded body that names its record type. A browser client can read it. | Service responses and technical documentation. | The homepage, How it works and their shared footer. | Open owner decision. Do not rename it. |
| `Loop Engine Intelligence` | Customer-visible technical identifier: protected resource name | The `resource_name` field of the protected resource metadata at `/.well-known/oauth-protected-resource`. A client can show this name to the person who authorizes it. The service returns that record only when the host configuration lists the authentication mode `external_jwt`. The pilot lists only `host_key`, so the pilot does not return it today. | The protected resource metadata and technical documentation. | The homepage, How it works and their shared footer. | Open owner decision. Do not rename it. |
| `loop-engine` | Customer-visible technical identifier: command and package name | The command that a customer types and the package that a customer installs. | Installation and setup instructions, the Documentation view of the website and technical documentation. | The homepage, How it works and their shared footer. | Open owner decision. Do not rename it. |

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
