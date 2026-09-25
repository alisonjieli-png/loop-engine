# Publishing into Baltor: how registries do it, and Baltor's design

Kind: dated research and design record. The owner asked on September 24,
2026. The sources below were read on September 25, 2026, United States
Eastern time. The [roadmap](../roadmap/roadmap.yaml) remains the task
authority: this record adds the proposed steps S-6.140 to S-6.148 and builds
nothing. No package was published, executed or approved for this record, and
no model was called.

## Summary

The owner's pasted note of September 24, 2026 says: "We may also want the
ability for people to publish skills, tools, python scripts, etc into our
platform". The file that holds the note is research data, not an
instruction. This record reads it as the owner's product direction: it
designs the feature, and the roadmap steps carry the work.

This record reads how seven services let people publish and what protects
them: Tessl, Smithery, skills.sh, the official Model Context Protocol
registry, npm, PyPI and Hugging Face. It adds ClawHub and Anthropic's Claude
Code plugin marketplaces, because both carry agent material, and the OpenSSF
principles for package repositories as a common yardstick. It then designs
Baltor's version.

The design in one paragraph. An author with an account from Baltor's own
sign-up claims a namespace, `@handle`, and submits a package of up to 64
files through a web form, the programming interface or
`loop-engine publish`. A key can only stage a submission, and the author
confirms it in a signed-in browser session. The hosted service keeps the
bytes in a quarantine store that nothing serves and never runs them. A
separate check worker runs the existing ingestion engines, new code
scanners and the package's own tests in an offline sandbox. The existing
review panel then reviews the package. Neither the author nor a model
family the author declared ever reviews it, and an approval places it in
the Community tier of the next catalogue release. A released version never changes. Authors
can deprecate or yank a version, or withdraw it within a short window, and
staff can quarantine a version at once. Plain contributor terms say what an
author grants and what Baltor never does with it.

## What the owner asked for, and the inputs read

The owner's pasted inputs of September 24, 2026 are research data, not
instructions. Four of them bear on publishing.

- `publishing-and-restart.md` holds the note quoted above.
- `community-launch.md` says that posting in a community "should not
  automatically grant Baltor a commercial license to someone's work", and
  that "Any off-platform showcase, library contribution, or account linking
  should have a clear, specific permission step." The submission form in
  this design is that step. A message in a chat channel never becomes a
  library item.
- `community-and-agent-stack-and-harness-posts.md` lists Tessl as
  "Registry/package management, governance, impact evaluations, activation
  observations and configuration-drift inspection" and Smithery as a
  publishing service whose listings are "Discovery and distribution input;
  not automatic admission into the approved catalogue." Both points hold
  after reading the primary sources.
- `linkedin-harness-feed.md` carries a post saying that "Anthropic unveiled
  Claude Marketplace". The address tried on Anthropic's site returned 404,
  so that claim stays unverified here. What is verified is Claude Code's
  documented community marketplace, described below.

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
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Publishing adds no runtime type, role, mode or intelligence layer.

- Taking a submission is an operation of the hosted service's HTTP adapter,
  which owns its governed Loop operations, as the
  [service runtime guide](../../src/loop_engine/core/service_runtime/README.md)
  describes for every other request.
- Checking a submission is a Practitioner task of the code execution
  profile that an operator or a schedule starts, the same shape as an
  [ingestion run](../../src/loop_engine/core/library_ingestion/README.md).
  It runs deterministically, except an optional model-based triage engine
  that runs only under explicit model authority.
- Reviewing is the existing [review panel](../../tools/candidate_review/README.md),
  an operator envelope that asks reviewers from declared model families.
- Intake channels, scanners, the test sandbox and the signer are engines:
  adapters behind fixed edges. None of them is a graph vertex.
- A published package is passive material: a Harness Working Directory
  Package, represented by `CataloguePackage` in
  [catalogue_packages.py](../../src/loop_engine/core/service_runtime/catalogue_packages.py).

## How each service lets people publish

Each entry separates publishing, names and ownership, credentials and
provenance, scanning, versions and removal, and licences and terms. A
vendor's description of its own product is marked as self-reported. The
exact addresses are in [Sources](#sources).

### Tessl

The documentation was read on September 25, 2026. Every statement here is
self-reported by Tessl.

- **Publishing.** `tessl skill publish ./my-skill --workspace engteam` or
  `tessl plugin publish`. A plugin carries `.tessl-plugin/plugin.json` with
  a semantic version and a `private` flag, and publishing is private to the
  workspace by default.
- **Checks on publish.** "On publish, Tessl lints and reviews the content
  automatically, and the review score appears on the registry."
  Evaluation scenarios can be skipped with `--skip-evals`. A version is
  available, blocked, still being checked or unable to be checked. A
  workspace minimum review score blocks a lower version, and a blocked
  version cannot be overwritten: the author publishes a higher version.
- **Security.** "Security scores are powered by Snyk", with severities from
  LOW to CRITICAL. Install policies at organization, workspace and project
  level warn or block: "A source that hits the block threshold cannot be
  installed. There is no override." Policies can also restrict registries
  and git sources and require a minimum release age.
- **Public listing.** "Once you make a plugin public, you cannot make it
  private again." Tessl's pages disagree on whether a public listing needs
  approval: the publish page describes an approval in the Registry
  interface, and the sharing page describes none. This record keeps both as
  disputed.
- **Removal.** Unpublishing is "only available within 2 days of the
  original publish"; after that, archiving is the lasting alternative.
- **Claiming.** Tessl indexes public GitHub skills itself. An author claims
  one by publishing it from their own workspace through Tessl's GitHub
  action, after which the indexed copies are hidden and redirected. The
  claim page does not say how ownership is proven.
- **Roles and terms.** Workspaces have Member, Manager, Owner and Publisher
  roles. The terms address tried, `tessl.io/terms`, returned 404, so Tessl's
  contributor terms remain unknown.

### Smithery

The documentation was read on September 25, 2026 and is self-reported.

- **Publishing.** Two routes: the public HTTPS address of a server the
  author hosts (Streamable HTTP, with OAuth when authentication is needed),
  or an MCPB bundle of a local server that Smithery distributes. Smithery
  scans a server to extract its tools, prompts and resources, or reads a
  static server card at `/.well-known/mcp/server-card.json`.
- **Names.** "Namespace names must be lowercase alphanumeric with hyphens,
  and are globally unique across Smithery." A server is addressed as
  `namespace/slug`, and the interface can transfer a server between
  namespaces.
- **Skills.** The skills interface creates or updates a "GitHub-backed
  skill" from a git address with a Smithery key, and refuses a repository
  without a valid `SKILL.md`.
- **Verification.** A server's settings page offers an "automatic
  official-vendor verification checklist". Its criteria were not read.
- **Terms.** The address tried, `smithery.ai/terms`, returned 404, so
  Smithery's contributor terms remain unknown. The September 19 competitor
  notes record that Smithery joined Arcade.

### skills.sh

The site was read on September 25, 2026.

- **No publish step.** "Skills appear on the leaderboard automatically
  through anonymous telemetry when users run npx skills add
  <owner/repo>." A skill is named by its GitHub repository.
- **Audits.** Three scanners, Gen Agent Trust Hub, Socket and Snyk, report
  Safe, Low Risk, Med Risk or Pending. The audits page names each result by
  skill and repository, with no version and no commit. On September 25 it
  listed 50 skills with results, 13 of them pending.
- **Terms.** "Skills shown in the directory are the property of their
  authors and distributed under the licenses present in the source
  repositories", and "We do not own, host, or relicense skill content."
  Vercel "will honor reasonable takedown requests for skills that have been
  removed from their source repositories" and says it "cannot guarantee the
  quality, safety, correctness, or security of any skill listed". No
  delisting procedure for authors is documented.

### The official Model Context Protocol registry

The documentation and repository were read on September 25, 2026.

- **Status.** "The MCP Registry is currently in preview. Breaking changes or
  data resets may occur before general availability." The repository's
  README announces an interface freeze at version 0.1.
- **What it holds.** Metadata only, in `server.json`. The code lives in
  npm, PyPI, NuGet, crates.io, five named container registries, or GitHub
  and GitLab releases for MCPB bundles.
- **Names and ownership.** The authentication method decides the
  namespace. Signing in to GitHub, or a GitHub Actions identity token, gives
  `io.github.<user or organization>/*`. A domain proven by a DNS TXT record,
  or by an HTTPS file at `/.well-known/mcp-registry-auth`, carrying an
  Ed25519 or ECDSA P-384 public key, gives the reverse-DNS namespace, such
  as `com.example/*`.
- **Package back-reference.** An npm package must carry `mcpName`, equal to
  the server name, in `package.json`. PyPI, NuGet and crates.io packages
  carry an `mcp-name:` string in their README. Container images carry the
  `io.modelcontextprotocol.server.name` annotation. An MCPB address must
  contain "mcp" and the entry must carry `fileSha256`, which "The MCP
  Registry does not validate"; clients check it before installing.
- **Versions.** "The version string MUST be unique for each publication of
  the server. Once published, the version string (and other metadata)
  cannot be changed." Version strings that look like ranges are refused.
- **Moderation.** "The MCP Registry is quite permissive! We only remove
  illegal content, malware, spam, and completely broken servers." It keeps
  low-quality, vulnerable and duplicate servers and relies on upstream
  package registries and downstream subregistries for deeper moderation. A
  removed server gets the status `"deleted"` and its metadata stays
  readable. Appeals are GitHub issues.
- **Licence.** The project is moving its code from MIT to Apache-2.0.

### npm

The documentation was read on September 25, 2026.

- **Names.** Unscoped names are first come, first served, and a new
  unscoped name must not be "spelled in a similar way to another package
  name". A scope equals a user or organization name, and scoped packages
  are private by default. npm does not transfer names on demand;
  trademark claims go through GitHub's process.
- **Credentials.** "As of November 2025, only Granular access tokens are
  supported. Legacy access tokens have been removed." A granular token is
  limited to at most 50 packages or scopes, read only or read and write, an
  optional address range and an expiry date. A write token can be stage
  only: `npm stage publish` places a version in the registry "in a state
  where it's not available for public access", and only a maintainer with
  two-factor authentication can approve or reject it. The command
  reference read was npm 12.1.0, edited September 24, 2026.
- **Trusted publishing.** OpenID Connect from GitHub Actions and GitLab on
  hosted runners, and from CircleCI cloud, with npm 11.5.1 or later.
  Publishing from GitHub Actions or GitLab out of a public repository adds
  provenance automatically.
  A package can "Require two-factor authentication and disallow tokens".
  The page was last updated on September 3, 2026.
- **Provenance.** "When an npm package is published with provenance, it is
  signed by Sigstore public good servers and logged in a public
  transparency ledger." The `repository` field must match the public
  source repository, and `npm audit signatures` verifies.
- **Removal.** A new package can be unpublished within 72 hours if nothing
  depends on it. Later, only with no dependents, fewer than 300 downloads
  in the last week and a single owner. "Once package@version has been used,
  you can never use it again." Deprecation keeps a version installable
  with the author's warning. After a malware report, npm removes the
  package, publishes a security placeholder and an advisory, and decides
  whether to ban the account.
- **Terms.** The npm Open-Source Terms, last updated March 10, 2022, say
  "at a minimum, you license npm to provide Your Content to users of npm
  Services when you share Your Content", and forbid malicious code,
  name-squatting and packages that mainly display advertising.
- **Incident.** GitHub's plan of September 22, 2025 followed the Shai-Hulud
  worm, found on September 14, 2025, which took over maintainer accounts
  and injected install scripts into popular packages. GitHub reported
  removing over 500 packages (self-reported).

### PyPI

The documentation, blog, policies and proposals were read on September 25,
2026.

- **Accounts.** Since January 1, 2024, every user needs two-factor
  authentication to "perform any management actions, or upload files".
  Organization accounts group people into teams and are free for community
  projects.
- **Trusted publishers.** PyPI exchanges a CI identity token for a
  short-lived token "only valid for 15 minutes". Its security model says to
  "Treat your Trusted Publishers as if they are API tokens", to use GitHub
  environments with required reviewers, and warns that anybody who can
  commit can change the publishing workflow, that a renamed workflow looks
  the same to the token, and that a recreated account can inherit trust.
- **Attestations.** PEP 740 attestations bind each file to a digest and an
  identity. PyPI accepts them from trusted publishers, including GitHub
  Actions, GitLab and Google Cloud, with the predicates SLSA Provenance and
  PyPI Publish, at most two per file.
- **Licences.** Under PEP 639, a `License-Expression` must be a valid SPDX
  expression, and PyPI "MUST reject uploads that do not" meet that rule.
- **States.** PEP 592 yanking: an installer ignores a yanked release unless
  it is pinned exactly. PEP 792, final on July 8, 2025, defines active,
  archived, quarantined and deprecated. A quarantined project offers no
  files. PyPI's quarantine, introduced in August 2024, makes a project
  neither installable nor changeable by its owner. By December 30, 2024,
  about 140 projects had been quarantined and "only a single project has
  exited Quarantine". The post counted one full-time security engineer.
- **Names.** PEP 541: "Under no circumstances will a name be reassigned
  against the wishes of a reachable owner." Abandoned names can transfer
  after documented attempts to reach the owner. Empty squatting projects,
  malware, spam and obfuscated functionality are grounds for removal.
- **Terms.** The Terms of Use, effective February 25, 2025, grant "the PSF
  and all other users of the web site an irrevocable, worldwide,
  royalty-free, nonexclusive license to reproduce, distribute, transmit,
  display, perform, and publish the Content".

### Hugging Face

The documentation, content policy and terms were read on September 25,
2026.

- **Names.** Repositories sit under a user or an organization name.
- **Credentials.** Tokens are read, write or fine-grained to named
  repositories and organizations. Trusted publishers exchange a CI identity
  token for a short-lived token. A public endpoint revokes any leaked
  token, whoever finds it: it always answers 202, so it cannot be used to
  test a token, and it emails the owner.
- **Scanning.** "We run every file of your repositories through a malware
  scanner" (ClamAV) at each commit. Pickle files have their imports listed
  without being run, with the disclaimer "this is not 100% foolproof".
  TruffleHog runs on each push and emails the owner about verified
  secrets. Protect AI's Guardian and JFrog add third-party scans.
- **Signing.** A GPG-signed commit shows Verified when its key is on the
  account. Hugging Face says this "does not guarantee that your file is
  safe, but it does guarantee the origin of the file."
- **Licences and gating.** A `license` field in the card metadata takes a
  value from a list that includes open, restricted, `other` and `unknown`
  licences. A gated repository collects a requester's contact details and
  can require manual approval.
- **Policy and terms.** The content policy, effective April 10, 2025,
  forbids malware and unauthorized remote-management tools, and offers
  report buttons, a safety address, actions from a request for changes to
  account termination, and appeals. The terms, effective September 15,
  2022, license Hugging Face to use content "to provide Services", give
  each user of a public repository a perpetual and irrevocable licence, and
  say "You own the Content you create!"

### ClawHub and Claude Code plugin marketplaces

Both were read on September 25, 2026, and both descriptions are
self-reported.

- **ClawHub publishing.** `clawhub skill publish` after signing in. The
  guide says that "publishing requires a GitHub account old enough to pass
  the upload gate", and otherwise "ClawHub is open by default: anyone can
  upload." Skills have semantic versions, tags and changelogs.
- **ClawHub scanning.** Each release is checked by SkillSpector, by Tencent
  Zhuque Lab's A.I.G and by ClawHub's own ClawScan. The states are Pass,
  Review, Warn and Malicious, where Malicious blocks installation, plus
  Pending and Error. Compiled Python files are refused because A.I.G "cannot
  inspect packaged Python bytecode". OpenClaw's post of February 7, 2026
  added VirusTotal: a SHA-256 of the whole bundle, VirusTotal's model-based
  Code Insight review, "Skills flagged as malicious are instantly blocked
  from download", and "All active skills are re-scanned daily".
- **ClawHub moderation.** Signed-in users report listings. A moderation
  hold can hide a listing or make future publishes start hidden. Accounts
  can lose publishing access, be banned or have tokens revoked, and an
  appeal form exists.
- **Claude Code marketplaces.** Anyone publishes a marketplace as a git
  repository holding `.claude-plugin/marketplace.json`, with no submission
  form. Anthropic's community marketplace, `claude-community`, takes
  submissions through forms on claude.ai (Team or Enterprise) or the
  Console, and listed plugins are "in nearly every case pinned to a
  specific commit SHA". The official marketplace takes no form submissions.
- **Claude Code names.** Official marketplace names are reserved. A name
  that imitates one, such as `official-claude-plugins`, any name with a
  non-ASCII character, control or bidirectional characters, and "another
  spelling of a reserved name", such as a trailing dot or a symbol other
  than an underscore in place of a hyphen, are refused.

### The OpenSSF principles

The OpenSSF Principles for Package Repository Security, version 0.1 of
February 2024, set maturity levels. Level 1 asks for typosquatting
prevention, API keys scoped to packages, multi-factor authentication and a
vulnerability disclosure policy. Level 2 adds an unpublish policy that
stops a version from being replaced, malware reporting, malware scanning
and roles for maintainers. Level 3 adds short-lived tokens from OpenID
Connect, build provenance, secret scanning of the repository's own tokens,
transparency logs and machine-readable malicious package advisories.

### Incidents that shape the design

1. **Smithery's hosted build, June 2025.** GitGuardian reported that the
   `dockerBuildPath` setting of a submitted server "accepts any value,
   including those that point to a location outside of the MCP server code
   repository". A build could read the builder's `.docker/config.json`,
   which held a Fly.io token that "granted privileges on the machines API"
   in an organization with "more than 3000 apps". It was reported on June
   13, 2025 and fixed by June 15, 2025. Baltor also runs on Fly.io.
2. **npm's Shai-Hulud worm, September 2025.** Stolen maintainer credentials
   let an attacker publish install scripts into popular packages. The
   response was two-factor authentication for local publishing, short
   token lifetimes, stage-only tokens and trusted publishing.
3. **A malicious-skill campaign on ClawHub, early 2026.** Security
   researchers reported one. The report tried, from Koi Security, now
   redirects to a vendor product page, so its numbers are not repeated
   here. ClawHub's controls above are what its documentation says today.

### Comparison

| Service | Who publishes, and names | Publishing credential | Provenance or signing | Checks before listing | Removal |
| --- | --- | --- | --- | --- | --- |
| Tessl | Workspace members; private by default | Tessl sign-in or its GitHub action | Not documented on the pages read | Lint and review on publish; Snyk scores; install policies that block | Unpublish within 2 days; archive |
| Smithery | Any account; globally unique namespaces | Smithery key; service tokens | Release records; MCPB bundles | Metadata scan; vendor checklist | Delete, transfer, unlist |
| skills.sh | Any public GitHub repository | None: listing follows installs | None beyond GitHub | Three scanners after listing, not tied to a version | Takedown when removed at the source |
| MCP Registry | Proven GitHub account or domain | GitHub sign-in or Actions token; DNS or HTTP key proof | Back-reference in each package; MCPB hash checked by clients | None; relies on other registries | Status deleted, metadata kept |
| npm | Any account; scope equals user or organization | Granular, stage-only and trusted publishing tokens | Sigstore provenance | Malware reports and removal | 72-hour unpublish; a version is never reused; deprecate |
| PyPI | Accounts with two-factor authentication; organizations | Tokens; trusted publishers with 15-minute tokens | PEP 740 attestations | Malware reports; quarantine | Yank, archive, quarantine; PEP 541 for names |
| Hugging Face | User or organization repositories | Read, write and fine-grained tokens; trusted publishers | GPG-signed commits | ClamAV, pickle imports, TruffleHog, two partner scanners | Content policy actions; gating |
| ClawHub | GitHub account old enough to pass a gate | ClawHub sign-in | Bundle SHA-256 | Three scanners plus VirusTotal; daily rescans | Moderation holds; malicious blocked |
| Claude Code community marketplace | Form submission | Anthropic account | Pinned commit | Not documented on the pages read | Not documented on the pages read |

## Findings

1. The services come in three shapes. Some store the bytes and gate the
   publishers (npm, PyPI, Hugging Face, Tessl, ClawHub). Some store only
   metadata that points elsewhere (the MCP Registry, and Smithery for
   servers hosted by their authors). Some list what already exists on
   GitHub without a publish step (skills.sh, and Tessl's own indexing).
   Baltor stores and serves bytes, so it needs the protections of the first
   shape.
2. None of the services documents an independent review of every package
   before listing, which Baltor's Community tier requires. Tessl comes
   closest, with lint and review on
   publish and minimum scores that block. ClawHub blocks on scanner
   verdicts. Every service says scanning is not a guarantee. Independent
   review is what makes a Baltor item different, and it is the definition
   of the Community tier, so it is never skipped for speed.
3. Ownership proof is cheap when it rests on something the author already
   controls: the account, a GitHub identity or a domain. The MCP Registry's
   back-reference, where the package names its registry entry, stops a
   stranger from listing someone else's package.
4. Publishing credentials are moving away from long-lived keys: short-lived
   CI identity tokens (npm, PyPI, Hugging Face), stage-only tokens that a
   person with a second factor approves (npm), and scopes that only
   publish. The [registry survey](REGISTRY-AND-PACKAGE-INFRASTRUCTURE-SURVEY-2026-09-24.md)
   already recorded the rule that a download credential must never
   authorize publishing.
5. A released version never changes and a version string is never reused.
   Deletion is allowed only briefly (72 hours at npm, 2 days at Tessl).
   After that, authors deprecate or yank. Quarantine is a separate,
   reversible state that stops downloads and freezes the project (PyPI and
   PEP 792).
6. Scanning is layered and advisory, and each result must be tied to exact
   bytes; skills.sh's results are not tied to a version. Model-based
   scanners (VirusTotal Code Insight, A.I.G) sit beside static rules, and
   rescanning after a rule update catches what was missed.
7. A hosted build of submitted material is the most dangerous surface:
   Smithery's exposed a Fly.io token with machine rights over more than
   3,000 apps. Baltor must never build, install or run a submission on the
   service machine, or anywhere a Baltor credential is visible.
8. Only PyPI validates a declared licence expression strictly. Hugging Face
   accepts restricted and unknown licences, and skills.sh relicenses
   nothing. Baltor needs a declared SPDX identifier from its allowlist and
   a matching licence file, which its ingestion licence matcher already
   checks.
9. Contributor terms pair a licence to everyone who receives the content
   (GitHub section D.6, which licenses a contribution under the
   repository's own licence, PyPI's grant to all users, and Hugging Face's
   grant to users of public repositories) with a narrow licence to operate
   the service (npm, Hugging Face). GitHub's current grant to itself
   includes "training AI Features". Baltor can say plainly that it trains
   nothing on submissions, which also answers the community input.
10. Baltor already owns most of the machinery. `catalogue_package/v1` types
    every file role the owner named. The ingestion engines check format,
    licence, secrets, safety, effects and duplicates. The review panel
    excludes declared producer families. Catalogue releases carry durable
    withdrawals. Key scopes exist, with a management scope kept out of the
    defaults. What is missing is namespaces, submission records, staged
    intake, a quarantine record, code scanners, a test sandbox, author
    pages, contributor terms and signed publish records.

## Baltor's design

### What an author can publish

| The owner's word | Files and roles in `catalogue_package/v1` | Extra rules |
| --- | --- | --- |
| Skill | `SKILL.md` as `skill_definition`, with `skill_script`, `skill_reference` and `skill_asset` files | The Agent Skills rules; the folder name equals the skill name |
| Tool | `executable_tool`, with a tool contract naming inputs, outputs and exit codes | Its own tests; `spawns_process` declared |
| Python script | `skill_script` inside a skill, or `executable_tool` on its own | Python 3.12 standard library only at launch; its own tests |
| Hook | `hook`, which may run only files inside the package | Its own tests; `spawns_process` declared; no network unless declared |
| Subagent | `subagent_definition` | The format rules of each target harness |
| Protocol server configuration | `protocol_server_configuration` | Exact package versions, or an HTTPS address with a declared host; no secret written into the file |
| Instruction file, command or plugin | `instruction_file`, `command` or `plugin_manifest` | A plugin manifest is checked against the pinned Agent Plugins schema of S-6.44 |

At launch Baltor refuses model weights and serialized objects such as
pickle files, compiled bytecode (`.pyc`, `.pyo`, `.pyd`), executable
binaries, archives inside a package, minified or obfuscated code, symbolic
links and any media type outside a closed list. Scanners cannot read these
reliably: ClawHub refuses compiled Python for the same reason, and PEP 541
treats hidden functionality as grounds for removal. The existing limits of
`catalogue_package/v1` apply: 64 files, 8 MiB a file, 32 MiB a package,
and safe relative paths.

Scripts and tools may use only the standard library at launch. A
protocol server configuration may name an npm or PyPI package at an exact
version that exists, which the ingestion package check already verifies.
Dependency locks with hashes, a licence check of each dependency and a
GuardDog scan of each one come later.

### The journey of one submission

```text
One submission
├── Author
│   ├── an account from Baltor's own sign-up
│   ├── a namespace, @handle
│   └── a folder with baltor-package.json, read by the form and the command line
├── Intake on the hosted service, which never runs a submitted byte
│   ├── web form at /publish, in a signed-in session
│   ├── interface at /api/v1/publish, with a library:publish key
│   ├── loop-engine publish submit, through the same interface
│   ├── a key stages; the author confirms in a signed-in browser session
│   ├── structural checks: manifest, sizes, paths, media types, licence
│   │   identifier, terms version, namespace, unused version, limits
│   └── a quarantine store: content-addressed, read only, never served
├── Check worker, which holds only a staff scope to read submissions and report
│   ├── format engines
│   ├── licence evidence
│   ├── secret, safety and code engines
│   ├── effects, duplicates and names
│   └── the package's own tests in an offline sandbox
├── Independent review by the review panel
│   ├── never the author, a namespace member or a declared model family
│   ├── approved: Community tier, written as a reviewed catalogue folder
│   └── refused: reasons in plain words to the author
└── Catalogue release, the existing path
    ├── author page, package page, tier label and signed publish record
    └── lifecycle: deprecate, yank, withdraw and quarantine
```

### Accounts, keys and the confirmation step

Any account created through Baltor's own sign-up can publish, and
publishing is free. On the web the author works in a signed-in session.

The interface and the command line use a key with the new scope
`library:publish`. The scope sits outside `DEFAULT_SCOPES` in
[records.py](../../src/loop_engine/core/service_runtime/records.py), as
`billing:manage` does, so a download or search key can never publish.
A key can only stage a submission. The author confirms each staged
submission in a signed-in browser session, and the confirmation binds the
exact manifest digest. This adapts npm's stage-only tokens. Baltor accounts
have no second factor yet, so the signed-in session plus an email to the
account address is the approval step, and a second factor for namespace
owners is a later addition that the OpenSSF principles ask for at level 1.

Baltor stays on the free Resend plan, which sends at most 100 emails a
day. Authors therefore get one daily digest of state changes, and an
immediate email only for a security event: a quarantine, or a Baltor key
found and revoked. Publishing from GitHub Actions with a short-lived
identity token comes in S-6.148.

### Author namespaces and names

- **One personal namespace for each account.** `@handle` has 2 to 39
  characters: lowercase letters, digits and single inner hyphens.
  Organization namespaces come with the Team plan's seats and roles.
- **Package names.** A package name follows the Agent Skills name rule of 1
  to 64 characters, and a package is addressed as `@handle/name`.
- **Reserved names.** Baltor's own names and service words (baltor,
  official, verified, community, staff, admin, support, security, api,
  docs, www and others), and the names of model vendors, harnesses and
  registries (anthropic, claude, openai, codex, google, gemini, github,
  microsoft, meta, ollama, opencode, cursor, huggingface, npm, pypi and
  others). A vendor's name is released only to a namespace that proves the
  vendor's domain.
- **Other spellings.** A handle is refused when it equals a reserved or
  existing handle after removing hyphens, dots and underscores, folding
  case and mapping look-alike characters (0 to o, 1 and i to l, rn to m, vv
  to w). This adapts Claude Code's rule for other spellings and Unicode's
  confusable skeleton to an ASCII-only alphabet.
- **Similar package names.** A new package name one edit away from a
  package in another namespace that at least 25 accounts fetched, or equal
  to it without punctuation, waits for a superadmin. This is npm's rule
  for unscoped names.
- **Domain proof.** A DNS TXT record `baltor-publisher=<token>`, or the same
  token at `https://<domain>/.well-known/baltor-publisher`. Baltor checks it
  again every week, and the verified-domain mark disappears with the
  proof. This simplifies the MCP Registry's method: a random token replaces
  the key pair, because the author already holds a signed-in session.
- **Retention.** Baltor never moves a namespace away from an owner it can
  reach (PEP 541). A namespace with no released package after 180 days can
  be released on request when its owner agrees or cannot be reached. The handle of a closed account is retired and
  never issued again, so nobody can inherit its trust, the risk PyPI's
  security model names for recreated accounts.

### Licences and material written by others

- **One declared licence.** The author chooses one SPDX identifier from the
  list that ingestion already accepts: MIT, Apache-2.0, BSD-2-Clause,
  BSD-3-Clause, ISC, CC0-1.0 or CC-BY-4.0. No expressions at launch, the
  same rule as `library_licence_policy/v1`.
- **A matching licence file.** The package holds the licence text, and the
  existing matcher recognizes it at 98 percent word-set similarity with no
  added words. Every file-level notice, such as a skill's `license` field
  or an SPDX header, must agree.
- **Files written by others.** The manifest lists each one with its own
  allowlisted licence and notice file.
- **The copy rule.** A submission that repeats a refused or outline-only
  source, or nearly duplicates another author's package, is refused or held
  for a superadmin. An author cannot relabel restricted text by submitting
  it.

### Automated checks

| Check | Engine, with its slot | Runs on | Outcome |
| --- | --- | --- | --- |
| Manifest, sizes, paths, media types, licence identifier, terms version, namespace, unused version, limits | Structural rules | Service | Refused at once |
| Skill format | `agent_skills_builtin_rules` and `agent_skills_reference_validator`, existing, `library_format_validation` | Worker | Held |
| Connection files | `connection_builtin_rules` and `connection_schema_validator`, existing | Worker | Held |
| Licence file and notices | The existing licence matcher | Worker | Held |
| Secrets | The repository's secret patterns in `builtin_static_rules`, existing, and gitleaks, new, `library_safety_scan` | Worker | Held; a Baltor key is revoked |
| Unsafe instructions | `builtin_static_rules` and `skillspector_static`, existing | Worker | Blocking findings hold; caution notes go to reviewers |
| Malicious code patterns | GuardDog, new, `library_safety_scan` | Worker | Held |
| Python weaknesses | Bandit, new, caution only | Worker | Notes for reviewers |
| Model-based triage | A.I.G skill scan, optional, only under model authority | Worker | Notes for reviewers, never an approval |
| Effects | The existing effect rules: detected effects must be a subset of declared ones | Worker | Held |
| Duplicates and names | `datasketch_minhash_lsh`, existing, and the name rules | Worker | Refused, or held for a superadmin |
| Own tests | New slot `library_package_tests`, with the existing `process_confinement` slot nested for the sandbox | Worker | Held |

Every engine writes a typed result with its engine name and version, the
finding code, the severity, the file and the line, and never the matched
text. "Nothing found", "not scanned" and "scanner failed" stay separate
states, as the registry survey requires. A Baltor key found in a
submission is revoked at once and its owner is told, as Hugging Face does
for its tokens. Any other secret holds the submission, and Baltor never
tests a found secret against its provider.

The checks run on a worker for three reasons. The Smithery incident shows
what a build on the service's own infrastructure can reach. The service
machine's memory is already the limit that S-6.62 and S-6.70 measure.
SkillSpector already runs in a bubblewrap sandbox without network in the
ingestion runs on the review workstation. The first worker is that
workstation: it reads confirmed submissions through a staff scope,
`library:review`, and posts results back. A cloud worker comes when its
isolation is verified.

`loop-engine publish check <folder>` runs the deterministic engines
offline on the author's machine, with the same versions and codes, the way
`tessl plugin lint` and `claude plugin validate` let authors fix problems
before they submit.

### The package's own tests

A package with a skill script, a hook or an executable tool declares its
tests: the runtime, the command and a time limit of at most 120 seconds.
At launch the runtimes are Python 3.12 and Node.js 22, with the standard
library only. A package with executable files and no tests is refused.

The test runner is a new slot, `library_package_tests`, that owns the test
contract and the result. It does not bring its own sandbox: the existing
`process_confinement` slot is nested under it, and its first engine kind,
`linux_namespace_sandbox` (bubblewrap), runs the tests with no network, the
package mounted read only, one scratch folder, no inherited environment or
home folder, and bounded processor time, memory, processes, file size and
output. A stronger kind, such as a container or a user-space kernel
sandbox, can replace it without changing the runner, and the choice never
moves to a weaker isolation. The worker's own reporting key is outside the sandbox's view. The
result binds the package digest, the sandbox profile digest, the command,
the exit status, the counts and the time. A failed or timed-out run holds
the submission and shows the author the end of the output.

### Independent review into the Community tier

The [Library tiers row](../../AGENTS.md#decisions-that-stand-until-the-owner-changes-them)
of the decision table defines Community: every automated check, including
"its own tests where it has code", and one independent review by a family
that did not produce the item. For a submission this becomes:

- **Producer families.** The author declares model assistance on the form:
  none, one or more of the panel's declared families (anthropic, openai,
  zhipu, deepseek, alibaba, minimax, moonshot, mistral, nvidia, google),
  another family by name, or unknown. The panel never infers a family from
  the text, as its guide requires. Those families never review the package.
  Neither does anyone who owns or maintains the namespace.
- **Quorum.** Community needs one approving family outside the producer
  families. An author who declares unknown assistance needs two approving
  families, because no family can be excluded with confidence. Verified
  keeps its rule of two approving families and every check. As the panel's
  policy already says, any rejection withholds approval.
- **Hold for a new namespace.** The first executable package of a new
  namespace also waits for a second approving family or a superadmin, the
  role ClawHub's upload gate plays.
- **Reading.** Reviewers read package text as quoted material under the
  written criteria, and the verdict binds the exact package digest.
- **Answers.** A refusal returns the failed criteria to the author in plain
  words. An appeal goes to a family that has not seen the package, or to a
  superadmin. A submission waits when no eligible family is reachable; it
  is never reviewed by an excluded family to save time.
- **Release.** An approved package is written as a reviewed catalogue
  folder with its tier, author, reviewers and digests, for the next
  catalogue release.

### Versions and lifecycle states

```text
One package version
├── staged        uploaded with a key, waiting for the author's confirmation
├── submitted     confirmed, and the structural checks passed
├── checking      on the worker
├── held          a check failed; the author sees why and submits a new version
├── in review     with the review panel
├── refused       with reasons; the version string stays used
├── approved      Community tier, waiting for the next catalogue release
├── released      served in a catalogue release
│   ├── deprecated    served with the author's message
│   ├── yanked        served only to an exact pin, never newly selected
│   └── quarantined   not served and not changeable while staff decide
└── withdrawn     not served; its record, digest and review stay
```

A package is active, archived (no new versions), deprecated (with an
optional successor) or quarantined, the four statuses of PEP 792. Yanking
follows PEP 592.

- A version string is used once for each package, forever, and its bytes
  never change. A semantic version is required.
- The latest version is the highest released version that is not a
  prerelease and is not yanked, withdrawn or quarantined.
- An author may withdraw a version within 72 hours of its release when no
  account has fetched it, npm's rule. After that, a withdrawal needs a
  security, legal or personal data reason and a superadmin.
- Clients can already pin a catalogue release, and a withdrawn item is
  refused at download with its reason, as S-6.62 built.

### Reports, quarantine and takedown

- **Reports.** Every package page has a report button for signed-in
  readers, with the reasons malware, exposed secret, licence or copyright,
  personal data, impersonation, spam and broken. Reports reach a staff queue
  in the Administration view. Anyone else writes to the contact address.
- **Quarantine.** A superadmin or a developer quarantines a version with one
  action. A durable withdrawal (`catalogue_withdrawal/v1`) can never be
  undone, and a quarantine sometimes is, so quarantine needs its own
  record, `catalogue_quarantine/v1`. Download and search honour it before
  the next release, and the catalogue state marker changes so that an older
  image, which cannot read the record, refuses to serve.
- **Clearing or withdrawing.** A superadmin clears a quarantine or turns it
  into a durable withdrawal.
- **Targets.** A credible malware report is quarantined within one day. A
  blocking finding from a rescan quarantines automatically. Every active
  submitted package is rescanned when a scanner or its rules change, and at
  least weekly.
- **Notices.** Accounts that fetched a quarantined or withdrawn version are
  told by email. Each security withdrawal publishes an advisory record, and
  the OSV format follows later, as OpenSSF level 3 asks.
- **Copyright.** A notice goes to the contact address, the author may send
  a counter-notice, and repeated infringement ends the author's publishing
  access.

### Author pages, package pages and the dashboard

- **Author page, `/authors/<handle>`.** The handle, an optional display
  name, a verified domain when proven, and each package with its tier,
  latest version, licence, kinds and deprecation notes. It shows no email
  address and nothing about any customer's use.
- **Package page.** Versions with dates and states, reviewers by family,
  the licence, the files with digests, declared effects, test and scan
  summaries, the source link and whether it was verified, and how to
  install it.
- **Dashboard.** The signed-in author's submissions with their states, held
  findings, review reasons and actions, the staged submissions to confirm,
  and the keys with the publish scope.
- **Words.** The pages use plain product words, such as package, author,
  skill, tool and review, and no runtime terms, following the public
  writing rules.

A private package for a team, visible only to its members and labelled
Private, fits the Team plan's shared private library. It takes the same
intake and automated checks and no independent review, because it is not
served to anyone else. It is noted here and left to the Team plan's own
work.

### Provenance and signed publish records

- **Every submission** records `author_submission_provenance/v1`: a digest
  of the account, the namespace, the package and version, the package and
  file digests, the time, the channel, the terms version accepted, the
  declared licence and model assistance, and an optional source repository
  at a full commit.
- **A source link** is marked verified only when the worker fetched that
  commit and every submitted file equals the file there.
- **Trusted publishing.** GitHub Actions can stage a submission with a
  short-lived OpenID Connect token that Baltor checks for issuer, audience,
  repository and owner identifiers, workflow and environment. The owner
  identifier guards against a recreated account. A person still confirms
  the submission.
- **A signed publish record.** Each released version gets a statement in
  the in-toto form, naming the package digest, namespace, version, tier,
  review record digest and release, signed with a Baltor Ed25519 key whose
  public half is served at a well-known address. `loop-engine` checks a
  fetched package against its record before placing it. This is the role
  of npm's publish attestation and PyPI's PyPI Publish predicate. Keyless
  Sigstore signing for Baltor's own release workflow comes later.

### Limits and abuse controls

These are the first choices. The intake step measures them and changes
them on evidence.

- For each account: 10 submissions a day, 3 open submissions at once, and
  100 MiB of stored package bytes. Ten a day covers a very active author
  and keeps the review cost bounded.
- For each network address: 30 submission requests an hour, kept by the
  existing `request_limit_state` slot like the sign-in limiter.
- The same package under several names is spam, as the MCP Registry
  moderation policy says. A package that mainly advertises is refused, as
  npm's terms say.
- The first executable package of a new namespace waits for a second
  approval, as above.
- A reporter whose reports are repeatedly rejected has later reports
  queued behind others.

### Engines behind fixed edges, and existing work

```text
Publishing edges and slots, with their engines
├── library_submission_intake edge, new
│   ├── web_form, first
│   ├── http_interface, first, used by the command line
│   └── github_actions_identity, later
├── publisher_identity edge, new
│   ├── baltor_account, first
│   ├── dns_txt_domain and https_well_known_domain
│   └── github_account, later
├── name_confusability edge, new
│   └── builtin_ascii_skeleton, first
├── library_ingestion_source slot, existing
│   └── author_submission, new
├── library_safety_scan slot, existing
│   ├── builtin_static_rules and skillspector_static, existing
│   ├── gitleaks_secrets and guarddog_static, new, blocking
│   ├── bandit_python, new, caution only
│   └── aig_skill_scan_model, optional, under model authority
├── library_package_tests slot, new
│   ├── declared_test_runner, first, Baltor-native
│   └── process_confinement slot, existing, nested
│       └── linux_namespace_sandbox, first; stronger kinds may replace it
├── publish_record_signer edge, new
│   ├── ed25519_host_key, first, Baltor-native
│   └── sigstore_keyless, later
└── existing slots reused without change
    ├── catalogue_body_store: the quarantine store, a separate root
    ├── request_limit_state: the per-address submission limit
    └── account_email_delivery: the daily digest and the security notices
```

The [functional component standard](../architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
and rule 6 of AGENTS.md apply to every new slot and engine. Each new slot
gets one record in
[`engine_slots.yaml`](../../src/loop_engine/data/engine_slots.yaml) and one
conformance kit that every engine passes alone. Each project taken from
outside enters as an engine adapter pinned to its source revision and
licence, runs in the sandbox its trust requires, and has a Baltor-native
engine beside it or a recorded reason why the slot needs none:

- gitleaks has the repository's own secret patterns beside it, which
  already run in `builtin_static_rules`;
- GuardDog gets new built-in code rules beside it (a decoded payload that
  is run, a network call in an install or setup step, environment data sent
  out, obfuscated code), written in the same module style as the existing
  rules;
- Bandit needs no twin, because its findings are caution notes that never
  refuse a package, and the recorded reason says so;
- the A.I.G skill scan gets a Baltor-native model triage engine beside it,
  which sends the same package through the model gateway with Baltor's own
  written criteria. The `library_safety_scan` slot declares only the
  `static_scanner` kind today, so both need a new `model_triage` kind.

The engine selection records of the ingestion component apply to every new
engine: an engine that is switched off, lacks its dependency or lacks
authority is removed before anything runs, and the decision is recorded
first. The licences and activity below were read from GitHub on September
25, 2026.

| Project | Licence | Decision and reason |
| --- | --- | --- |
| NVIDIA SkillSpector | Apache-2.0 | Adopted already; reused on submissions. ClawHub runs it too. |
| DataDog GuardDog | Apache-2.0 | Adopt as a blocking engine. It scans a local package folder for malicious patterns with YARA and Semgrep rules, for PyPI and npm style code. It runs in the scanner sandbox without network; a rule that needs the network fails closed as "scanner failed". |
| PyCQA Bandit | Apache-2.0 | Adopt as caution only. It finds weaknesses, not intent, and would refuse too much as a gate. |
| gitleaks | MIT | Adopt as a second secret engine beside the repository's own patterns. |
| TruffleHog | AGPL-3.0 | Rejected. Its verification sends found secrets to their providers, which Baltor must never do. |
| ClamAV | GPL-2.0, run as a separate program | Deferred. Binaries are refused at launch, so a virus scanner adds little; it returns when assets such as images are accepted. |
| Tencent A.I.G skill scan | Apache-2.0 | Adapted as optional triage. It is "LLM-driven" and defaults to a model through OpenRouter; Baltor would point it at an authorized route and read its SARIF output as notes only. |
| VirusTotal and Snyk agent-scan | Services | Rejected for submissions. Both send material to an outside service, the reason ingestion already rejected Snyk agent-scan. |
| in-toto attestation | Apache-2.0 | Adopt the statement format for the signed publish record. |
| sigstore-python | Apache-2.0 | Deferred to keyless signing of Baltor's own releases. |
| PyPI Warehouse | Apache-2.0 | Design reference for quarantine, trusted publishers and organization accounts. Not adopted as code: it is a whole registry application. |
| Official MCP Registry | MIT, moving to Apache-2.0 | Design reference for namespace proof and back-references. The registry survey found it is not designed for self-hosting. |
| Microsoft APM | MIT | Already a candidate at the dependency edge; it matters again when dependency locks arrive. |
| Developer Certificate of Origin | Not applicable | Used only as the model for the author's promises in the terms, which are written in Baltor's own words. |

### New records

Each reader refuses another version, an unknown field and a missing field
before anything is built from the record.

| Record | What it holds |
| --- | --- |
| `author_namespace/v1` | The handle, the owning account, the state and the dates |
| `author_domain_proof/v1` | The domain, the method, the token digest and each check |
| `library_submission/v1` | The manifest: name, version, summary, kind, files, licence, effects, network hosts, secret names needed, tests, tool contract, model assistance, source link, changelog and terms version |
| `library_submission_state/v1` | Each state change with its actor, reason and time |
| `author_submission_provenance/v1` | Where the bytes came from, as described above |
| `submission_check_result/v1` | One engine's result on one package digest |
| `package_test_result/v1` | One test run, bound to the package and sandbox digests |
| `candidate_intelligence_specifications/v3` | Staging rows that can carry author provenance; a version two reader refuses them |
| `catalogue_quarantine/v1` | A reversible hold on one item version, honoured at download and search |
| `package_report/v1` | One report, its reason and its outcome |
| `package_advisory/v1` | A published notice for a security withdrawal |
| `publish_record/v1` | The signed statement for one released version |

### Settings and rollout

The feature sits behind a host setting that is off. It opens in stages:
staff first, then named accounts, then every account. Opening it to
outside authors waits for S-6.147, which records the owner's approval of
the contributor terms and the privacy notice addition. Staff can use the
path first with Baltor's own first-party packages under `@baltor`, with the
generating model's family as the producer family, so the whole path is
exercised before any outside author uses it.

## Contributor terms: draft for publication with the feature

This is the draft that S-6.147 moves to `docs/legal/CONTRIBUTOR-TERMS.md`
and serves at `/contributor-terms`. It follows the voice of the published
terms of service. It is not legal advice. Publishing it is a legal
commitment, which the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section keeps with the owner, so S-6.147 records the owner's approval of
this text before the setting opens to outside authors, as was done for the
terms of service on September 23, 2026.

### Baltor contributor terms

Operator: Baltor.AI, 1428 Bryn Mawr St, Saxton, PA 16678, United States.

These terms apply when you publish a package in the Baltor library. A
package is a set of files that a coding tool can use, such as a skill, a
tool, a script, a hook, a subagent, a protocol server configuration, an
instruction file or a command. The [terms of service](../legal/TERMS-OF-SERVICE.md)
still apply to your account.

1. **What you keep.** You keep the copyright in your package. Publishing
   does not transfer it to Baltor.
2. **The licence you choose.** You choose one licence from the list on the
   publishing form and include its text in the package. Everyone who gets
   your package from Baltor, including paying customers, gets it under that
   licence. These licences cannot be taken back, so a person who already
   has a copy keeps the rights the licence gives, even if the package is
   later removed.
3. **What you allow Baltor to do.** You allow Baltor to store, copy and
   scan your package; to have it reviewed by automated tools and by the
   people and model providers named in its review record; to place its
   files in the layout each coding tool expects; to show its name,
   description, files, author name and review results; and to deliver it to
   Baltor users, including paying users. Baltor does not pay authors for
   published packages.
4. **What Baltor does not do.** Baltor does not train any model on your
   package or your submissions. It does not change the files of a version;
   a new version comes only from you. It does not add you to a mailing list
   because you published.
5. **What you promise.** You promise that:
   - you have the right to publish every file under the licence you chose,
     and each file written by someone else carries its own licence and
     notice from the same list;
   - the package holds no password, key, token or other secret, and no
     personal data about another person;
   - the package does what its description says, declares what it does
     (running programs, reading or writing files, using the network,
     reading secrets), and contains no malware and no hidden instruction to
     a model;
   - you told Baltor on the form which model families helped you write it,
     or that you do not know.
6. **Names.** Author names are first come, first served, except reserved
   names. You may not use a name that pretends to be Baltor, another
   company or another person. Baltor never takes a name from an owner it
   can reach, but may retire a name that deceives people, holds no
   package, or infringes a trademark.
7. **Review and refusal.** Baltor may refuse a package, ask you to change
   it, or remove it. Baltor tells you the reason, unless the reason would
   help someone abuse the service.
8. **Versions and removal.** A version never changes once it is published.
   You can mark a version as deprecated or yank it at any time. You can
   remove a version within 72 hours of its release if nobody has fetched
   it. After that, write to Baltor, and a version is removed for a security,
   legal or personal data reason. Baltor keeps the record that a version
   existed, with its digest and its review, after removal.
9. **Reports.** Anyone can report a package. If Baltor believes a package
   may cause harm, it may stop serving it at once while it looks into the
   report. Copyright notices and appeals go to the contact address.
10. **No promise about use.** Baltor provides the publishing service as it
    is. Baltor is not responsible for how others use your package under its
    licence.
11. **Changes.** These terms can change. The date of the last change is
    shown with them, and each submission records the version you accepted.
    A change applies to packages you publish after it.

## Privacy notice addition: draft

This addition joins the privacy notice when the owner approves it under
S-6.147. It adds two rows to the table of what the service stores.

| Data | Why | Where |
| --- | --- | --- |
| Your author handle, your optional display name, the packages you publish, their versions, check results and review records, and the version of the contributor terms you accepted | To publish your packages under your name. Your handle, display name and packages are public on your author page. Your email address is never shown. | The service database and the library's file store on Fly, United States |
| Reports about a package: the reporter's account, the reason, the words of the report and the outcome | To review the report and to protect people who use the library | The service database |

It also adds one sentence: "The packages you submit are reviewed by
automated tools and by the model providers named in each review record,
today Ollama Cloud, OpenAI through the Codex command line, Anthropic
through the Claude Code command line, and a model server that Baltor's
operator runs."

## Roadmap steps

The steps are in [roadmap.yaml](../roadmap/roadmap.yaml) with their
verify, adversarial, acceptance and evidence fields. Their numbers start at
140 because S-6.119 and S-6.120 are each claimed by several lines in
flight, whose merges will take the numbers after them, and the support line
holds S-6.130 to S-6.134.

| Step | Title |
| --- | --- |
| S-6.140 | Author namespaces and a publish scope that a download key never carries |
| S-6.141 | Submission intake: staged by form, interface or command line, confirmed by a signed-in person, kept where nothing serves it |
| S-6.142 | Automated checks on every submission on a worker, and the same deterministic checks on the author's machine |
| S-6.143 | A package's own tests in an offline sandbox on a worker that holds no Baltor secret |
| S-6.144 | Independent review of submissions into the Community tier, never by the author or a declared model family |
| S-6.145 | Versions, deprecation, yanking, withdrawal, reports, quarantine and takedown |
| S-6.146 | Author pages, package pages and the publishing dashboard |
| S-6.147 | Contributor terms and the privacy notice addition, published with the feature |
| S-6.148 | Provenance for submitted packages: verified source links, trusted publishing and a signed publish record |

## Decisions and reasons

| Decision | Choice and reason |
| --- | --- |
| Where submitted bytes are processed | Structural checks only on the service; every content check and every test on a worker that holds no Baltor secret. Smithery's build leaked a Fly.io machine token, and Baltor runs on Fly.io. |
| Who can publish | Any account from Baltor's own sign-up, free, with limits. One way in already exists, and free publishing grows the library. |
| Publishing credential | A `library:publish` scope outside the defaults; keys stage only, and a signed-in person confirms. npm's stage-only tokens and the Artifactory lesson both point here. |
| Namespaces | One `@handle` for each account, reserved and look-alike names refused, domains proven by DNS or HTTPS. This follows the MCP Registry, npm and Claude Code. |
| Licences | One allowlisted SPDX identifier with a matching licence file. The ingestion allowlist and matcher already exist; PyPI validates declared licences the same strict way. |
| Tier | Every submission enters as a candidate and reaches Community only through the checks and one independent review; Verified needs the full review. This is the decision table's definition. |
| Author's family | Declared, never inferred; declared families and the author's namespace are excluded; unknown assistance needs two families. The review panel already declares families. |
| Tests | Required for any executable file, run offline under the existing `process_confinement` slot. The Community definition requires them, and the slot already refuses to move to a weaker isolation. |
| Versions | Immutable, never reused, semantic; withdrawal only within 72 hours when unfetched, then deprecate or yank. npm, the MCP Registry and Tessl agree. |
| Quarantine | A new reversible record beside the permanent withdrawal, honoured before the next release, and refused by older images. PyPI's quarantine and PEP 792 show the need. |
| Scanners | Add gitleaks, GuardDog and Bandit behind the existing slot; reject TruffleHog verification, VirusTotal and Snyk agent-scan for submissions. Nothing leaves Baltor except to the declared review providers. |
| Contributor terms | Inbound equals outbound, a narrow licence to operate, no training, no payment to authors, all said plainly; published after the owner's approval is recorded. Legal commitments stay with the owner. |
| Emails | A daily digest and immediate security notices only. The free Resend plan sends 100 emails a day. |
| Step numbers | S-6.140 to S-6.148, to stay clear of the numbers that lines in flight will take. |

## What this record did not establish

- **Verified today, September 25, 2026.** The MCP Registry pages on
  authentication, package types, moderation and versioning, read in full;
  the npm pages on trusted publishing, provenance, unpublishing, names,
  disputes, scopes, tokens, staging and malware reports; the PyPI pages on
  attestations and trusted publishers, the quarantine and two-factor posts,
  PEP 541, PEP 592, PEP 639, PEP 792 and the Terms of Use; the Hugging Face
  pages on scanning, signing, tokens, licences, gating, the content policy
  and the terms; the skills.sh documentation, audits and terms; the Tessl
  and Smithery documentation pages named above; the ClawHub documentation
  and OpenClaw's VirusTotal post; the Claude Code publishing and
  marketplace references; GitHub's terms, sections D.4 to D.6; the OpenSSF
  principles; and the licences and activity of the listed projects on
  GitHub.
- **Self-reported.** Everything Tessl, Smithery, ClawHub, OpenClaw and
  GitHub say about their own products and incident responses, including
  GitHub's count of removed packages and GitGuardian's account of the
  Smithery fix.
- **Disputed.** Whether Tessl requires approval before a public listing:
  its two pages disagree.
- **Unverified.** The LinkedIn post's "Claude Marketplace" launch; the
  numbers of the ClawHub malicious-skill campaign; the criteria of
  Smithery's vendor verification checklist.
- **Unknown.** The contributor terms of Tessl and Smithery, whose terms
  addresses returned 404; whether GuardDog's local folder scan needs no
  network for every rule, which the S-6.142 sandbox run will show; how a
  model-based scanner's findings compare with the static engines on
  Baltor's regression set.
- **Not done.** Nothing was built, installed or executed. No model was
  called. The contributor terms and the privacy addition are drafts that
  have not been approved.

## Sources

Read on September 25, 2026 unless another date is given.

- Tessl: [distributing through the registry](https://docs.tessl.io/distribute/distributing-via-registry),
  [publish and update](https://docs.tessl.io/creating-skills-and-plugins/publish-and-update.md),
  [sharing publicly](https://docs.tessl.io/distribute/sharing-plugins-publicly.md),
  [claiming a skill](https://docs.tessl.io/distribute/promote-or-claim-a-skill-you-have-created.md),
  [insecure skills](https://docs.tessl.io/tutorials/protecting-against-insecure-skills.md),
  [permissions](https://docs.tessl.io/distribute/permissions.md).
- Smithery: [publishing](https://smithery.ai/docs/build/publish.md),
  [namespaces](https://smithery.ai/docs/concepts/namespaces.md),
  [creating a skill](https://smithery.ai/docs/api-reference/skills/create-or-update-a-skill.md),
  [documentation index](https://smithery.ai/docs/llms.txt), and GitGuardian's
  [report on Smithery's hosting](https://blog.gitguardian.com/breaking-mcp-server-hosting/).
- skills.sh: [documentation](https://www.skills.sh/docs),
  [questions](https://www.skills.sh/docs/faq), [audits](https://www.skills.sh/audits),
  [terms](https://www.skills.sh/terms).
- MCP Registry: [repository](https://github.com/modelcontextprotocol/registry),
  [authentication](https://modelcontextprotocol.io/registry/authentication),
  [package types](https://modelcontextprotocol.io/registry/package-types),
  [moderation policy](https://modelcontextprotocol.io/registry/moderation-policy),
  [versioning](https://modelcontextprotocol.io/registry/versioning).
- npm: [trusted publishing](https://docs.npmjs.com/trusted-publishers),
  [provenance](https://docs.npmjs.com/generating-provenance-statements),
  [unpublish policy](https://docs.npmjs.com/policies/unpublish),
  [name guidelines](https://docs.npmjs.com/package-name-guidelines),
  [disputes](https://docs.npmjs.com/policies/disputes),
  [scopes](https://docs.npmjs.com/about-scopes),
  [access tokens](https://docs.npmjs.com/about-access-tokens),
  [npm stage](https://docs.npmjs.com/cli/v12/commands/npm-stage),
  [malware reports](https://docs.npmjs.com/reporting-malware-in-an-npm-package),
  [open-source terms](https://docs.npmjs.com/policies/open-source-terms),
  and GitHub's [plan for npm](https://github.blog/security/supply-chain-security/our-plan-for-a-more-secure-npm-supply-chain/).
- PyPI: [trusted publishers](https://docs.pypi.org/trusted-publishers/),
  [security model](https://docs.pypi.org/trusted-publishers/security-model/),
  [attestations](https://docs.pypi.org/attestations/),
  [organization accounts](https://docs.pypi.org/organization-accounts/),
  [quarantine](https://blog.pypi.org/posts/2024-12-30-quarantine/),
  [two-factor requirement](https://blog.pypi.org/posts/2024-01-01-2fa-enforced/),
  [PEP 541](https://peps.python.org/pep-0541/), [PEP 592](https://peps.python.org/pep-0592/),
  [PEP 639](https://peps.python.org/pep-0639/), [PEP 792](https://peps.python.org/pep-0792/),
  [Terms of Use](https://policies.python.org/pypi.org/Terms-of-Use/).
- Hugging Face: [security](https://huggingface.co/docs/hub/security),
  [malware scanning](https://huggingface.co/docs/hub/security-malware),
  [pickle scanning](https://huggingface.co/docs/hub/security-pickle),
  [secrets scanning](https://huggingface.co/docs/hub/security-secrets),
  [signed commits](https://huggingface.co/docs/hub/security-gpg),
  [Protect AI](https://huggingface.co/docs/hub/security-protectai),
  [tokens](https://huggingface.co/docs/hub/security-tokens),
  [licences](https://huggingface.co/docs/hub/repositories-licenses),
  [gated models](https://huggingface.co/docs/hub/models-gated),
  [content policy](https://huggingface.co/content-policy),
  [terms](https://huggingface.co/terms-of-service).
- ClawHub and OpenClaw: [repository](https://github.com/openclaw/clawhub),
  [ClawHub guide](https://docs.openclaw.ai/tools/clawhub),
  [security audits](https://github.com/openclaw/clawhub/blob/main/docs/security-audits.md),
  [moderation](https://github.com/openclaw/clawhub/blob/main/docs/moderation.md),
  [VirusTotal partnership](https://openclaw.ai/blog/virustotal-partnership), February 7, 2026.
- Claude Code: [publishing a plugin](https://code.claude.com/docs/en/plugins/publish),
  [creating a marketplace](https://code.claude.com/docs/en/plugin-marketplaces),
  [marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference).
- Other: [GitHub terms of service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service),
  effective April 27, 2026;
  [OpenSSF principles](https://repos.openssf.org/principles-for-package-repository-security.html);
  [GuardDog](https://github.com/DataDog/guarddog);
  [A.I.G](https://github.com/Tencent/AI-Infra-Guard).
- Baltor's own records: the [registry survey](REGISTRY-AND-PACKAGE-INFRASTRUCTURE-SURVEY-2026-09-24.md),
  the [library ingestion component](../../src/loop_engine/core/library_ingestion/README.md),
  the [review panel](../../tools/candidate_review/README.md),
  [catalogue_packages.py](../../src/loop_engine/core/service_runtime/catalogue_packages.py),
  [catalogue_releases.py](../../src/loop_engine/core/service_runtime/catalogue_releases.py),
  and the [legal notices](../legal/README.md).
