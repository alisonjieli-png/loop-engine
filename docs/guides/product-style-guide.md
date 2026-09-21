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

Separate a real limit from a missing measurement. A real limit is a fact
about the product as it exists today: the library holds one example item
while a reviewed collection is prepared, or a part is written and not
connected to a live run yet. Say that on the page, in a sentence the reader
will actually read, not in small print. A missing measurement is different.
Nobody owes the reader an apology for a number that was never promised, and
a page that ends every sentence with one reads as an apology. Describe what
the product does, in the present tense. The
[public content direction](public-website-content-and-domain.md#the-six-benefits-and-how-they-open)
records which of the six homepage benefits carries a real limit, and
`benefit_details_state_the_real_limits_without_a_measurement_apology` in
`tools/check_service_workspace.mjs` holds that split, with a known-wrong case
for a dropped limit and for a returned apology.

Use full descriptive terms. Keep exact identifiers in technical details and
copyable configuration. Avoid hype, decorative slogans, invented performance
claims, em dashes, and en dashes. Artificial general intelligence remains a
research ambition.

## Names and where they may appear

Baltor is the public brand. Loop Engine is the repository, the Python package
and the technical name.

The list of names used to live in a table on this page. It now lives in
[terminology.yaml](../../terminology.yaml), which is the single structured
source. Every term there carries its kind, its definition, the surfaces where
it may appear, the surfaces that refuse it and its status, and the
conformance gate `undefined_terms_retired_names_and_misplaced_words` reads
the same fields. A table repeated here would drift away from the file that
the gate reads, so this page points at the file instead.

Read [the developer language guide](developer-language.md) first. It explains
the surfaces, the words a customer page uses, the words a technical document
uses, the phrase that must stay whole, and how to propose a rename. Then open
terminology.yaml for the exact entry.

Two placements on this page changed on September 21, 2026, and terminology.yaml
records both with their reason:

- The words harness and agent may now appear on a public page. The owner's
  category line is harness and agent optimized operation, so refusing the two
  words that the line is made of was no longer the owner's rule.
- The four intelligence layer names are public words. The homepage already
  shows Context Intelligence, Code Intelligence, Runtime History and Solution
  Intelligence, and User Feedback Intelligence, and `LAYER_PUBLIC_LABEL` in
  `src/loop_engine/core/intelligence_layers.py` calls them product-facing
  names. The bare role words are the technical ones, so terminology.yaml
  refuses Practitioner, Intelligence Loop and Solution Loop on a public page
  and allows the layer names everywhere.
- The words pilot, beta, private beta and early access are retired words.
  They describe the product as a trial, and being invited changes only who
  can create an account. terminology.yaml refuses all four on the public
  pages, on the signed-in views and in the Documentation view, and leaves
  technical documents and dated records with their original wording. The
  [public content direction](public-website-content-and-domain.md#the-retired-trial-words)
  names the checks that read the served pages and every served file.

### Why the words agent and harness may appear on a customer page

An earlier entry kept "agent" off the homepage and How it works, next to
"harness" and "prompt cycle". That placement was changed on September 21,
2026, and the reason is recorded here rather than left as a silent break.

1. Agent is the word the buyer already uses for the thing they run. The
   owner's own direction for the homepage proposes "Give your AI agents what
   they need", and the reader is a developer who calls their tool an agent.
2. Agent is a customer word, not a runtime word. The rule that matters keeps
   Loop, Loop node, Loop Engine, runtime classification, role profiles and
   Practitioner off the public pages, and that rule is unchanged.

An earlier version of this guide also retired the category line "harness and
agent optimized operation" from the homepage, on the reasoning that it
carried the word harness. That reasoning does not hold, and the line is back.
The phrase is the owner's name for the positioning, the recorded decision in
`CLAUDE.md` stands, and the buyer is a developer who runs coding agents and
already uses the word. So two more rules:

1. The phrase "harness and agent optimized operation" belongs on the
   homepage, written out in full. Because the word is jargon outside this
   repository, a plain sentence sits beside it and says what a harness is, so
   a reader who does not know the word still follows. Two named checks in
   `tools/check_service_workspace.mjs` hold both halves:
   `homepage_opens_with_the_owner_category_line` and
   `the_owner_category_line_is_explained_in_plain_words`, each with a
   known-wrong case.
2. Outside that phrase and its explanation, "harness" still does not belong
   on the homepage, on How it works, on Get started or in the shared footer.
   Write "your coding tool".

### Open owner decision: identifiers that carry the engine name

Five identifiers carry `status: open_owner_decision` in terminology.yaml.
They are visible to a customer and still carry the engine name. The key
prefix `le_` is set in
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
capabilities record. The public capabilities record of the deployed service
reports `Baltor`, and the value can only come from the host configuration, so
the host configuration of that service sets it. A self-hosted service that does not
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
