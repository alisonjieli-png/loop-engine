# Native packages, task context and current status

Kind: dated Codex handoff, September 23, 2026. The task authority remains
[roadmap.yaml](../roadmap/roadmap.yaml). This document supplies implementation
input and evidence for its existing steps. It does not approve or publish
candidate material.

## Read this against current source

The clean review worktree is `/home/username/.le-codex-review-20260923`, based
on `abcad4f8ce346e7d0759ccad703e0111574148a6`. The shared checkout at
`/home/username/loop-engine` was at `385c6471`, 92 commits behind that base,
with concurrent uncommitted work. Nothing in that checkout was reset or
overwritten. Later origin main `243a8811` changed the branch triage record.
Recheck source and active writers before integrating.

A new pointer document in the shared checkout,
`docs/context/CODEX-REVIEW-WORKTREE-2026-09-23.md`, identifies this complete
review worktree and its artifacts. Claude can read that worktree on the same
filesystem. Existing source, roadmap and generated files in the shared
checkout are not overwritten. Review the tracked diff against its exact base;
integrate it into current main and regenerate derived records there. Do not
replace a newer roadmap wholesale.

## The owner's correction: a skill is only one package type

The earlier generation batches concentrated on standalone skills because
they fit the existing candidate path. That was an implementation limitation,
not the product definition. The hosted catalogue still packages one
Markdown body per item. Existing runtime provisioning already has native
instruction files and a structured assignment, but not the complete tested
startup briefing and mixed-package delivery required by the owner.

The [task context report](../verification/FOCUSED-STEP-CONTEXT-PACKET-2026-09-23.md)
and [native plugin report](../verification/HARNESS-PLUGIN-AND-HOOK-CANDIDATE-2026-09-23.md)
provide separate working examples:

| Artifact | Concrete output | Verified observation | Remaining integration |
|---|---|---|---|
| [Focused task packet](../../artifacts/focused-step-packet-2026-09-23/README.md) | Two packets, 17 payload files and two manifests. Native instructions, `node_context.md`, `task.json`, state, input, JSON contracts and checklist. | 18 tests, seven guard removals and four independent boundary probes. Codex 0.155.1 prompt construction contains objective, first action, state and output shape. Removing `AGENTS.md` removes all four markers despite the auxiliary files. No model call. | Extend the existing assignment and instruction contracts, native launch binding and trusted state source. Qualify actual task use. |
| [Native Claude plugin](../../artifacts/harness-plugin-context-2026-09-23/README.md) | One reusable candidate package, 13 payload files, zero `SKILL.md`: manifest, agent, command, hook, Python tools, five JSON resources and licence. | 26 deterministic checks, native validation and inventory. Independent Claude Code 2.1.280 startup ran the SessionStart hook and accepted 603 characters of additional context without a model call. | Independent admission, complete package serving, client-specific placement, command use, agent permission behavior and task benefit. |

The essential task belongs inline in the harness's supported native
entrypoint. Additional context and structured state can accompany it through
explicit references. Arbitrary filenames such as `agents.state` are not a
universal startup protocol. The two packets demonstrate the requested
`node_context.md` without making that assumption.

Each fresh instance should receive its objective, relevant inputs, completed
work and current state, ordered first actions, output contract, acceptance
conditions and externally enforced authority. The packet renderer composes
through `AssignmentBriefing`, `NodeAssignment` and `TrustedStateSnapshot`;
it introduces no new runtime or store. These examples grant no execution
authority. A trusted host must bind real model, tool and filesystem rights
separately when integrating the runtime path.

Runtime assignment files change with each task and add **zero persistent
library items**. An approved reusable renderer can produce host-validated
packets without a new three-model review on every `task.json`. Reusable
instructions, tools, plugins and procedure bodies still require independent
review of their exact package version. Model-specific wording variants must
preserve task, authority and acceptance semantics and receive comparative
evidence rather than being counted as new methods.

S-6.40 and S-6.44 now record the wider delivery requirement: native
instructions, skills, tools, agents, commands, hooks, plugin and protocol
configuration, contracts, scripts, references and assets. Each package needs
file roles, client/version placement, dependencies, effects, source and
licence information, exact digests and the correct loading mechanism. Search
should return the small package reference and compatibility information;
selection and authorization precede materializing its full tree. A file
extension or successful search must not enable an executable hook.

The plugin's independent review caught an unexpected FIFO being omitted from
the tree check and a PATH-resolved interpreter being replaceable. Both failed
versions remain beside the repaired result. The final candidate is narrowed
to a trusted Linux `/usr/bin/python3` binding and immutable package mount.
This is a deployment constraint, not universal portability or proof of a
secure customer host.

Exact plugin manifest SHA-256:
`fdfd23ea7ea160a66d5d3be7805261050595ea07597497b35c021da8a4ee68ff`.
Exact packet renderer SHA-256:
`6f9e28c6a30c3f409182805fd5c6c65b00d7104398bdca38025f43aa6fda7762`.

## Supply and approval findings

The [supply audit](../research/MILLION-HARNESS-SUPPLY-NEXT-STEPS-2026-09-23.md)
verified the earlier 212 local package records: 123 starter records plus 89
new original candidates. Only 43 starter versions have current approval and
host packaging evidence. Adding this session's plugin gives **90 separate
original candidate packages and 130 payload paths**. That count excludes the
ephemeral task packets and review reports. It includes repeated bodies in
alternative native layouts; it does not claim 130 distinct bodies, methods,
approvals or accepted customer uses.

The existing unmerged importer staged 3,251 source records and refused 511
skills whose required bundled resources were missing. Reuse and extend it;
do not build a competing importer. The new streaming audit processed one
million synthetic metadata rows in 19.898 seconds with 43,532 KiB peak worker
resident memory. It repeated one body digest and adds no intelligence supply.
It is useful scale tooling, not a million generated packages.

Two findings must reach Claude before expanding the live catalogue:

- **S-6.63:** 29 older approvals conflict with newer panel rejections. The
  compared bodies differ only in their closing catalogue revision line.
  Origin `243a8811` proposes carrying 71 older approvals; resolve these
  opposing outcomes and criteria against the current bytes first. No
  approval or withdrawal was changed by this audit.
- **S-6.47:** the phone-number item that harmed the measured model remains
  offered in the saved live catalogue search, although release 20 removed
  it from the homepage. Independently decide applicability, repair or
  withdrawal; keep the exact negative population and evaluation limits.

The [status report](../verification/CLAUDE-AND-ROADMAP-STATUS-2026-09-23-MORNING.md)
preserves the evidence and original review record digests. The panel pilot
reviewed 30 items and approved zero. Its small calibration set is not a
qualified error-rate estimate. These results call for repairing content and
review criteria, not scaling an unchanged generation process.

## Website and editorial work

[Live review](../verification/LIVE-BALTOR-REVIEW-2026-09-23-MORNING.md)
confirmed release 20 and the improved phone header, visible invitation
action, full-width demonstration and signed-in header. Hot catalogue
releases and the tenant-isolation repair have shipped. Earlier descriptions
of those as missing are stale. The saved 100,000-item service probe still
shows a roughly 2 GiB swap and does not qualify a million-item service.

The [editorial preview](../../artifacts/editorial-pages-2026-09-23/README.md)
contains a blog index, three complete articles, a Team page with Taylor
Amarel and existing-logo comparisons at 16 and 32 pixels. Twelve viewport
and page checks passed; a separate reviewer confirmed generated pages match
their source and checked factual claims. Local preview, while its server
is running: `http://127.0.0.1:41487/index.html`.

The [copy repair report](../verification/WEBSITE-COPY-AND-EDITORIAL-CANDIDATES-2026-09-23.md)
records a local homepage change removing the unsupported absolute drift
claim and a benefit-guide correction to the owner's North Star. Eight
owning tests and all 495 browser checks passed; the 76 browser controls and
new claim-guard removal were detected. These changes are not deployed.

Use the existing application shell for blog and Team routes so navigation
preserves sign-in behavior. The negative-result article needs the catalogue
disposition resolved or explicitly disclosed before publication. The final
logo remains undecided. The current documentation setup contradiction,
homepage-alias subdomains and missing HEAD response remain recorded gaps.

## Integration and completion limits

The clean worktree updates existing roadmap entries S-6.33, S-6.40, S-6.44,
S-6.47, S-6.62 and S-6.63, with generated views. No candidate is marked
approved or served. The reports and artifacts can be read directly from the
review worktree named by the shared checkout pointer. Source changes require reconciliation with current main,
full exact-tree checks and the existing release process. This session's
focused and browser checks do not substitute for that complete gate.
