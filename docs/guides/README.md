# Operating guides

Kind: operating guides.

This folder holds task-focused instructions: how to install, configure,
run, view, verify, deploy, package, and extend Loop Engine. Guides are
undated (`kebab-case.md`) and kept current; superseded guidance is
rewritten in place, not preserved under a date.

What does not belong here: design decisions (see `../architecture/`),
point-in-time check results (see `../verification/`), research (see
`../research/`), and the working rules for changing the code (see the
[engineering standards](../standards/README.md), which cover names, records
and versions, checks and evidence, service interface conventions, and the
language each component uses).

Start with [getting started](../getting-started.md) and the
[documentation index](../README.md).

A new developer or a new coding agent starts with
[developer language](developer-language.md). It is the one page that explains
the words this repository uses, the surfaces where each word may appear and
the check that enforces them. The single structured source it points at is
[terminology.yaml](../../terminology.yaml).

## For a paying customer of the hosted service

These seven pages explain account access, client setup, selection and downloads.
They separate a configured connection from a harness loading and using material. Every command, address, record type,
refusal code and refusal status in them is held to the service source by
`tools/check_service_documentation.py`. Examples are request shapes for the reader to fill with actual selected values;
they are not transcripts or proof of a completed native-client task. A refusal status is not restated in that check: it compiles
the transport's own status function out of the source and asks it, so a
refusal whose status moves makes every page that states the old status fail.

| Page | Scope |
|---|---|
| [What Baltor is](service-what-baltor-is.md) | What the hosted service holds, what stays on your machine, and the families and layers that sort the material. |
| [Your account](service-your-account.md) | Browser sessions, personal client tokens, scopes, grants and entitlements. |
| [Getting set up](service-getting-set-up.md) | Account, client token, where the token is kept, the settings entry for each supported client, and how to tell the connection succeeded. |
| [Searching and retrieving](service-searching-and-retrieving.md) | What a search returns, how to read and select a reference, how to download a body, and what one measured unit is. |
| [Usage and what you pay for](service-usage-and-what-you-pay-for.md) | One measured unit is one downloaded item, what is free, where your usage is, and how a retry avoids a second measured unit. |
| [Serving and connections](service-serving-and-connections.md) | Protocol versions, transport, addresses and common refusal codes. |
| [Troubleshooting](service-troubleshooting.md) | The failures a customer meets first, with what they see, what it means and what to do. |

The saved requests and answers are in
[the service usage transcripts](../evidence/service-usage-2026-09-21/README.md).

The first-release guides are [hosting procedures](hosting-and-deployment-procedures.md),
[owner actions](launch-owner-checklist.md),
[product style](product-style-guide.md), and
[harness service onboarding](harness-service-onboarding.md). Their planned
service paths are labeled separately from commands available today. The
hosting procedures name the [current host](hosting-and-deployment-procedures.md#current-host).

The [service failure diagnosis guide](service-failure-diagnosis.md) is the
operator procedure for the deployed service: the reference that names one
request in both the customer's refusal and the durable record, the read-only
command that finds those records, what the health route measures, and the first
failure of each dependency. Every command in it reads and changes nothing.

The [staff tools guide](staff-tools.md) is the procedure for the people who
run the service: a staff key for Claude Code, Codex, OpenCode or an operator
agent, the protocol endpoint that answers staff keys only, the plan and apply
of every change, download credits, service messages, sign-up links for people
who signed up offline, and publishing new library files without a redeploy.

The [launch setup runbook](launch-setup-runbook.md) lists the account, hosting,
identity, storage, payment and secret-reference work for the owner. The
[decision-tool guide](jev-and-harness-decision-tools.md) covers optional Jev
configuration, direct calls, and local Model Context Protocol tools. These
guides distinguish locally checked behavior from live provider qualification.

The [developer credential handoff](developer-credential-handoff.md) explains
prepared Claude Code connections and private keyring references. It does not
export credential values into repository files or grant missing access.

The [harness instance layout](harness-instance-context-layout.md) distinguishes
the generated instruction and assignment files from proposed native context
materialization and observed-loading requirements.

The [overnight local solving guide](overnight-solving-on-local-models.md)
covers the machine tiers a local model needs, the memory arithmetic behind
them, connecting a local inference server as a custom provider, declaring an
unattended night's authority, budget and wait, and reading the result in the
morning. It names the parts that were executed and the parts that were not.

The [website design standards](website-design-standards.md) state how the
public website looks and what it holds: tokens, spacing, the scroll budget,
the header and footer, the page template and the rule that nothing is removed
without a dated reason. The site map record and two checks hold them.

The [public content and domain plan](public-website-content-and-domain.md)
separates customer pages from the internal engineering report. The
[launch benefit guide](launch-benefits-and-evidence.md) records the overnight,
token-efficiency and expert-context drafts with their required evidence. The
[frontier harness wording](frontier-harness-positioning.md) is a copy
exploration, not approved copy or a capability claim. It does not rename the
repository. The owner's selection of Baltor as the public brand is recorded in
the table Names and where they may appear.

## Maintain the public documentation

See [the website documentation guide](website-documentation-view.md) for the
versioned index, body build, explicit routes and browser checks.
