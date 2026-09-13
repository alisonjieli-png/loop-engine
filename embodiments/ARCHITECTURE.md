# Experimental embodiment architecture contract

Scope: the experiments inside this repository use canonical Loop Engine. The independent projects in the sibling `solver-lab` workspace do not import this lab or inherit its evaluator. They keep their own source and architecture rules. This contract does not govern those peer projects.

Current harness work, including installed dependencies and logs, stays inside
`/home/username/loop-engine`. Sibling projects are reference inputs only.

The boundary owns independently launchable experimental distributions and their qualification metadata. An embodiment is a configuration and implementation of execution mechanics, not a new operational runtime type.

Folders are justified because alternatives own different launch code, dependency requirements, process lifetimes, qualification cases and reproduction instructions. Attributes and catalog queries classify those alternatives, but cannot contain their independently reviewable launch and test files.

The runtime classification, profiles, typed contracts, permissions and Run History remain owned by the authorities named in the root `architecture.yaml`. This directory does not introduce a second registry of runtime profiles or another event/history store. `catalog.json` is a discovery index for experiments. It grants no execution authority.

The implementation direction is `embodiment launcher -> development lab -> public Loop Engine runtime`. Product code must never import `embodiments` or `embodiment_lab`. The lab does not import sibling repositories. Every independently governed calculation and verifier runs through canonical `Loop` with an exact registered profile.

Reference mirrors are immutable data archives of source revisions, not active first-party runtime implementations. Preparation into a new workspace is explicit and does not execute them. An integrated legacy engine must be an independently qualified external harness used by a Loop. Remixes and mutations retain exact provenance and do not gain authority from source availability.

The original mechanism-study backends execute trusted deterministic data
transformations. The newer semantic harness adapters use explicitly selected
installed software through the existing external-harness registry and model
gateway. Their Linux process boundary uses Bubblewrap, private configuration,
a private broker socket and a separate network namespace. Native harness tools
are disabled. The owning Loop still controls capability execution, model
authority, budgets, acceptance and Run History. A Python process alone is not
advertised as a security sandbox. Neither route performs automatic promotion,
deployment, commit or push. The historical raw-host OpenCode adapter remains
quarantined.

Unsupported combinations refuse; failed and missing attempts remain reported. Existing files and studies are not overwritten. Sources and input identities are frozen per comparison. Each candidate stays separate from acceptance and from the current verified portfolio.

Required checks cover per-folder catalog consistency, product import boundaries, no alternate runtime subclasses, exact payload delivery, fresh and pooled process identity, cross-request state isolation, independent oracle canaries, source/input drift, failure accounting, bounded concurrency, cancellation cleanup, durable history, and persisted output queries.
