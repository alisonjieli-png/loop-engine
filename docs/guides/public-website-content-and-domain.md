# Public website content and domain direction

Kind: public-content direction and publication limits. The owner selected
Baltor as the public brand. This document does not authorize a new domain
change, account creation or payment activation.

The complete single-file system map is an internal engineering reference.
The public website should explain the customer benefit and supported workflow
without shipping internal planning records or the full source inventory.
Use shared, release-bound facts so public copy and engineering status agree.

## Current positioning and presentation

The buyer is one developer who already runs a coding tool that calls a model,
who pays for those calls out of their own budget, and who is tired of their
tools working out the same things again on every task. There is no team
account, no shared workspace and one plan, so the page speaks to that person
and not to an engineering manager.

The line above the headline is the owner's category line, "Harness and agent
optimized operation", written out in full. An earlier version of this
document retired it on September 21, 2026, on the reasoning that it carried
the word harness. That reasoning did not hold and the line is back the same
day. The buyer is a developer who runs coding agents and already uses the
word, and the recorded owner decision in `CLAUDE.md` names that phrase under
public positioning, so the record and the page now agree.

The word is still jargon outside this repository, so a plain sentence sits
directly beside the phrase and says what a harness is: the program that runs
your coding agent, such as OpenCode, Codex or Claude Code. A reader who has
never met the word reads the next sentence and follows. Two named checks in
`tools/check_service_workspace.mjs` hold both halves,
`homepage_opens_with_the_owner_category_line` and
`the_owner_category_line_is_explained_in_plain_words`, and each has a
known-wrong case: a page that prints the phrase and leaves the reader to
guess fails the second one.

The headline is the owner's line, "Supercharge your developers and AI
agents". It names the two readers it addresses. It is evaluative language,
which the
[product style guide](product-style-guide.md#marketing-language-and-factual-claims-are-different-things)
says needs no evidence, and it makes no checkable claim.

The sentence under the headline is "Give your AI agents what they need for
each step." It names the unit of work the product sells and was the headline
of an earlier draft. The owner's own proposal for it was "Give your AI agents
exactly what they need". The word "exactly" was removed because search is
text matching over metadata and a selection can miss, so precision would be
claimed that nobody measured.

Below that sentence the page says what the product is, then that the part you
install is free and access to the library is paid, then that model keys stay
with the customer. The one primary action is Get started. The action whose
wording the service controls sits in the caption under it.

The homepage sections run in this order:

```text
Homepage
├── Category line, headline and the sentence under it
│   ├── The plain reading of the category line
│   ├── What the product is, then the free and paid split
│   ├── Model keys stay with the customer
│   ├── One primary action to Get started
│   ├── One secondary action to How it works
│   └── The waiting list caption, whose wording the service controls
├── Three step strip: connect, ask, keep the record
├── What works right now: search, selected downloads,
│   connection settings and usage, with the size of the library
├── Six benefits, each opening to say how it works
│   and to name a real limit where there is one
├── One workflow for the decisions behind the work
├── A starting point for every step
├── Pricing summary with a link to the pricing view
└── Closing action and the limits note
```

The hero is one column. The earlier right-hand customer-import workflow
illustration moved out of the first screen because it described a broader
workflow than the current search and selected-download service. The first
section after the hero now shows the three actions a visitor can take. The
page still links to the illustrative task on How it works.

The five customer problems and the four persistent intelligence layers moved
to How it works on September 21, 2026. They are the vendor's model of the
world, and they asked the reader to diagnose themselves before they knew what
the product was. They are still shown to every customer, and
`tools/check_service_workspace.mjs` holds them by name on the page they now
live on.

### The six benefits and how they open

Each benefit is a title and a detail. The detail says how the product does it
and names the file or the behaviour behind it. It then describes what the
reader gets, in the present tense. Where the part behind a benefit has a real
limit today, the detail names that limit in a sentence the reader will
actually read.

An earlier draft ended every one of the six with a sentence apologising for a
measurement nobody had asked for. The owner removed those on September 21,
2026. A real limit is a fact about the product and stays. A missing
measurement is not a limit, and the page already carries the evidence
position twice, in the limits note under the closing action and in the notice
on How it works.

| Benefit | The real limit the detail names |
|---|---|
| Each step gets the material it needs | None. The step carries the material it asked for |
| Reuse code instead of writing it again | The library on our server holds a small first collection of reviewed items today, so this works best beside your own material |
| Not every step needs a large model | None. Each real call writes a cost record, and an unknown cost stays unknown |
| Solutions you can run without us | None. The package is started in an interpreter that cannot load Baltor at all |
| A failed check is examined, not obeyed | The ranking work is written down and that part is not connected to a live run yet |
| Work that can stop and start again | None. Reserving, pausing, checkpointing and cancelling stay four separate actions |

The website has a strict content security policy with no inline script and no
inline style, so the opening behaviour lives in `service.js` and `service.css`.
Every detail is written into the page source, so a reader whose browser never
receives the script sees all six. Once the script runs, one benefit is open at
a time. Pointing at a title, moving keyboard focus to it and pressing it each
open that one and close the others, so a touch screen and a keyboard reach the
same detail that a mouse reaches. Each title is a button inside a heading, it
names its own detail through `aria-controls`, the detail names the title back
through `aria-labelledby`, and `aria-expanded` follows the state. Nothing
moves or fades, so a reduced-motion setting changes nothing.

`tools/check_service_workspace.mjs` holds all of that by name, including the
page read without the script, and five removed-guard controls prove that a
page which drops one way of reaching a detail fails a named check.

### The retired trial words

The words pilot, beta, private beta and early access do not appear on any page
a customer reads. Being invited changes only who can create an account. It
does not change how the product looks or how carefully it is built.

| Do not write | Write |
|---|---|
| private pilot, beta, early access programme | accounts open in small groups |
| pilot user, beta tester | invited member |
| join the beta | join the waiting list |
| the pilot does not support X yet | X is being built |

The scan that holds this rule carries no exception. One sentence used to need
one, "Your operator manages pilot access." in
`src/loop_engine/core/service_runtime/web_assets/client-access.js`, shown on
the account page when customer token management is switched off. It now reads
"Your operator issues and revokes your access." The class name
`pilot-callout` in the two served stylesheets was retired in the same change;
the box it styled is `closing-band`.

Eight named checks in `tools/check_service_workspace.mjs` hold the rule, and
each scan has a known-wrong case beside it.

| Check | What it reads |
|---|---|
| `no_customer_page_describes_the_product_as_a_trial` | The header, the shown view and the footer of all eleven served addresses and of `/get-started` |
| `retired_word_check_rejects_a_known_wrong_page` | Five known-wrong sentences, one for each retired phrase, each of which the rule must report, and one accepted sentence it must not |
| `no_served_file_carries_a_retired_word` | Every file the browser fetches for a customer page: the markup, the four scripts, the two stylesheets, the recipe record and the open-source notices the footer links to |
| `served_file_scan_rejects_a_file_that_carries_a_retired_word` | Each of those served files with one retired sentence appended, twice: once naming a private beta and once asking for early access |
| `every_served_asset_route_is_scanned_for_retired_words` | The scanned list against `WEB_ASSETS` in `src/loop_engine/core/service_runtime/web_pages.py`, so an asset added to the route table alone cannot escape the scan |
| `served_asset_coverage_check_rejects_a_route_left_out_of_the_scan` | The same comparison with each served asset route removed from the list in turn, which must report exactly that route |
| `both_public_page_checks_use_one_retired_word_rule` | The rule text of `retiredAccessWords` here and of `liveRetired` in `tools/check_hosted_website.mjs`, which must be the same string |
| `retired_word_rule_comparison_rejects_a_drifted_copy` | The same rule with its `early access` branch dropped, which must then miss a page that asks for early access |

The deployed pages are read the same way by
`no_live_customer_page_describes_the_product_as_a_trial` in
`tools/check_hosted_website.mjs`, with its own known-wrong case.

The two rules had drifted. Until September 21, 2026 the workspace rule read
pilot and beta only, while the hosted rule also read early access, so a page
offering early access passed the check that gates a commit and failed only
after a deployment. The workspace rule now carries all four phrases, and
`both_public_page_checks_use_one_retired_word_rule` makes a future
disagreement a named failure instead of a silent one.

### Get started

Get started is the first item in the navigation and in the footer, ahead of
How it works. Connect is no longer a destination in the navigation, because a
reader meets the word before they know what it means. It is step two of Get
started and is always written as "Connect your tools".

The Get started page names three steps in order: download, connect your tools,
sign up. It keeps the copyable connection settings, the environment variable
guidance and the connection check that the Connect page already held. Step one
says plainly that the packaged download and its email link are being built and
sends the reader to the installation guide. Step three says plainly that the
waiting list form is being built.

The page answers at `/connect`, which the serving route table lists. The
address `/get-started` opens the same page through the navigation, and a
direct visit to it is not served yet. It needs one entry in `WEB_ASSETS` in
`src/loop_engine/core/service_runtime/web_pages.py`, next to the entry that
`/pricing` received on September 21, 2026. Until it has one, every link on
the website points at `/connect`, so no customer reaches a refused address.

The account action has two states and the page never chooses between them by
itself. It reads `website.registration_available` from `/api/v1/capabilities`.
When the service reports that account creation is open, the action reads
"Create your account" and leads to `/signup`. Otherwise it reads "Join the
waiting list" and leads to `/signup#waiting-list`, where the page explains
that accounts open in small groups. Before the service answers, and if it
never answers, the page keeps the careful state. The same rule drives the
payment state on the pricing view, which reads `billing.checkout`, and the
personal-key wording on the homepage and the pricing view, which reads
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
call or a native harness. Keep "prompt cycle" and precise Loop terminology in
technical documentation and GitHub. The owner excludes those internal terms
from the homepage and How it works. Use each step, selected information,
tools and checked results on those pages. Do not rename the repository,
runtime or serialized contracts.

The words "agent" and "harness" were on that excluded list until September
21, 2026. They came off it because the owner's category line is harness and
agent optimized operation, and a rule cannot refuse the words the owner's own
line is made of. [terminology.yaml](../../terminology.yaml) records both words
as customer words with that decision as their status, and
[the developer language guide](developer-language.md) explains the surfaces.

The five customer problems are excessive context, expensive models applied
indiscriminately, missing domain expertise, regenerated code and repeated
mistakes. They live on How it works. Pair each question with a specific
approach, not an invented percentage improvement. More context or a more
capable model can be justified when it improves the required outcome.

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
three step explanation, what works now, broader benefits, pricing and a
closing action.
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
| Homepage | The owner's category line with its plain reading, the headline, the sentence that names each step, the free and paid split, one primary action to Get started, the six benefits with their real limits named, what works right now, the three step strip, the pricing summary and a closing action. | Unverified cost savings, automatic task-success promises, customer counts, uptime guarantees, and a signup or purchase button that does not work. |
| How it works | A concrete task becomes understandable steps: find useful information, choose an approach, reuse or build, and check the result. The five customer problems and the four intelligence layers. Explain what the service supplies and what the user's tools may send to a model. | No runtime taxonomy, Loop branding or unsupported end-to-end success claim. Technical definitions belong in documentation. |
| Get started | Download, connect your tools and sign up, in that order. Exact released package and supported platform, installation, inspection, one bounded working example, expected output, errors and recovery. | Working-tree-only commands must not be advertised as available from the published package or GitHub main branch. Do not show a download form or a waiting list form before it works. |
| Harness and context guide | The generated instruction and assignment files, reference-first context, permitted write locations, supported versioned native layouts, and observed loading status. | Empty folders and offered skill references are not installed or loaded material. Do not copy the entire repository into every instance. |
| Integration reference | Tested protocol version, request and response schemas, effects, authentication scopes, limits, refused combinations and version negotiation. | A listed adapter or successful import is not end-to-end support for every native client. |
| Security and privacy | Actual permission and disclosure boundaries, credential handling, retention settings, local versus external data flows, and known limitations. | Do not promise that all data stays local when queries or model calls can leave the machine. Do not claim formal certification or instantaneous in-flight revocation without evidence. |
| Examples | Small reproducible tasks with the exact configuration, observed result, evaluator and limitations. | Component fixtures are not full-system benchmarks or proof of general task-solving quality. |
| Research and roadmap | Dated experiments, candidates such as AutoRAG, measured failures, and a concise public roadmap. | Internal owner decisions, investor or acquisition research, detailed security findings before disclosure review, and old comparison cells presented as current facts. |
| Pricing and account pages | The plan name, the price, what is free, the measured unit, the invited entitlement, and the payment state read from the service. | A local signed-event fixture or a checkout redirect is not proof of a live paid service. Do not show a purchase button while the service reports that checkout is unavailable. |

## Pricing view

The pricing view answers at `/pricing`. It states one plan and nothing else.

| Fact | Published wording |
|---|---|
| Plan | Baltor Pro |
| Price | 29 United States dollars each month |
| Free | Search is free |
| Measured unit | One downloaded item |
| Invited accounts | Invited accounts are free |

These figures come from the owner's September 20 direction, recorded in
`CLAUDE.md`. Engineering may not change a figure on the page alone. Change the
recorded decision first, then the page, then the checks that hold the page to
it.

Two wordings changed on September 21, 2026 without changing a figure. The
price now reads "29 United States dollars", which is the wording of the
recorded decision itself and not the abbreviation the page had used. The
entitlement row now reads "Invited accounts are free", because the owner asked
that the word beta not appear on a customer page. The fact behind it, an
operator entitlement that costs nothing, is unchanged.

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

The address `/pricing` must be served by the server, not only handled by the
page. While the serving route table did not list it, a direct visit, a shared
link, a bookmark and a reload while the pricing view was open all returned
HTTP 401 with a `service_http_error/v1` body whose only content was
`"code":"unauthorized"`, and a
`WWW-Authenticate: Bearer` header, because an unknown address falls past the
served web assets into the authenticated dispatcher. A visitor read that raw
text where the website should be. Since September 21, 2026 an address the
service does not serve is decided before authentication and answers
`404 route_unavailable`, and a browser asking for HTML gets a page that says so
with a link back, so this failure can no longer look like a credential fault.
The entry
`"/pricing": ("index.html", HTML_MEDIA_TYPE)` in `WEB_ASSETS` in
`src/loop_engine/core/service_runtime/web_pages.py` is now on the main branch, so
the source serves the address. Four named checks hold it:
`pricing_address_is_served_on_a_direct_visit`,
`pricing_address_opens_the_pricing_view_after_a_reload`, and `/pricing` in the
`responsive_<width>_<path>` and `enlarged_text_<width>_<path>` loops of
`tools/check_service_workspace.mjs`. A release that drops the entry fails all
four. The deployed service serves the address only from the release that
carries this source.

The address `/get-started` is still not in the serving route table, so it
works through the navigation only and every link on the website points at
`/connect` instead.

One thing is still missing on September 21, 2026. The account page holds the
subscription controls, and those remain behind the payment state.

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
merely to match marketing copy. [terminology.yaml](../../terminology.yaml)
records where each name may appear, explained by
[the developer language guide](developer-language.md). It also carries the
technical identifiers that a customer can see and that still carry the engine
name, each with `status: open_owner_decision`.

Baltor is short and pronounceable, and the existing domain avoids a new
purchase. Its meaning needs a short product description. Test whether people
who hear the name spell the final letter correctly. Use the Balto inspiration
as optional background on an About page rather than requiring visitors to know
the story.

The main caution is proximity to [Balto](https://www.balto.ai/), an existing
AI software brand. There are also other businesses named Baltor. This limited
search is not trademark clearance or a guarantee of exclusive use.

The service answers on four hostnames. All four serve the same release with
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
