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
