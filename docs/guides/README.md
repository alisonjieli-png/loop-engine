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

The first-release guides are [hosting procedures](hosting-and-deployment-procedures.md),
[owner actions](launch-owner-checklist.md),
[product style](product-style-guide.md), and
[harness service onboarding](harness-service-onboarding.md). Their planned
service paths are labeled separately from commands available today. The
hosting procedures name the [current host](hosting-and-deployment-procedures.md#current-host).
The product style guide holds the table
[Names and where they may appear](product-style-guide.md#names-and-where-they-may-appear)
for Baltor, Loop Engine, the public words and the technical words.

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

The [public content and domain plan](public-website-content-and-domain.md)
separates customer pages from the internal engineering report. The
[launch benefit guide](launch-benefits-and-evidence.md) records the overnight,
token-efficiency and expert-context drafts with their required evidence. The
[frontier harness wording](frontier-harness-positioning.md) is a copy
exploration, not approved copy or a capability claim. It does not rename the
repository. The owner's selection of Baltor as the public brand is recorded in
the table Names and where they may appear.
