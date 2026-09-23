# Agent Harness: architecture, ownership and adoption conditions

Research date: September 23, 2026. This is source research and an isolated
component experiment, not an installation, a security certification, or a
claim that Baltor already uses this project. The authoritative work state
remains the roadmap. This report supplies evidence for its existing component
and harness-intelligence work.

## Decision

Use madebywild/agent-harness as a candidate source of configuration-rendering
ideas and a possible versioned export engine. Keep Baltor's package admission,
byte storage, authority, credentials, placement and execution ownership. Do not
run its general `apply` writer over customer workspaces as our default installer.
The source audit and fifteen isolated checks below explain that decision.

Its useful organizing idea is one canonical source with explicit entities,
ordered instruction sections, provider renderers, a desired-output plan and
recorded provenance. Its job differs from executing each focused task in a
fresh governed harness. A generated native subagent file is a configuration
artifact; it is not an independently budgeted Loop.

The companion [compatibility and adoption report](MADEBYWILD-AGENT-HARNESS-COMPATIBILITY-AND-ADOPTION-2026-09-23.md)
examines actual native output and installed-client discovery. This report owns
file effects, source provenance and transformation semantics.

## Exact source and experiment

The inspected main HEAD and `v2.1.0` tag both resolve to
`2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17`. Its commit time is
August 30, 2026, 01:49:41 +0200. The public framework and manifest-schema packages
are version 2.1.0; the private monorepo root package still says 1.7.0. These are
different package records, not evidence that the published framework is 1.7.0.
The license is MIT, copyright 2025 Wild.
[Release](https://github.com/madebywild/agent-harness/releases/tag/v2.1.0),
[framework package](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/package.json),
[license](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/LICENSE).

The [source inventory](../../artifacts/madebywild-agent-harness-2026-09-23/ownership/source-inventory.json)
records exact source hashes and retrieval time. The shared clone was checked out
detached with hooks disabled. No upstream lifecycle scripts, CLI commands,
remote registry imports, generated tool executions or model calls ran for this
audit. The root `prepare` script installs lefthook; avoiding an ordinary install
was deliberate.

The [reproducible component probe](../../artifacts/madebywild-agent-harness-2026-09-23/ownership/README.md)
transpiled selected source using TypeScript 5.9.3, with isolated Zod 4.4.3 and
YAML 2.8.2. These satisfy the relevant dependency ranges but are not a replay of
the complete upstream lockfile. Native renderers were replaced by fixture
artifacts. The exact `apply` method ran in a wrapper accepting a precomputed
plan. Registry reader, inheritance and migration helpers were exported from
exact source slices. This isolates the behavior being measured without claiming
an installed end-to-end upstream run.

Execution used Node 22.22.1 in a network namespace with an empty environment,
a read-only host filesystem, one writable scratch directory, a 128 MB JS heap
ceiling and a 30-second process timeout. Only synthetic canary values were used.
The [results](../../artifacts/madebywild-agent-harness-2026-09-23/ownership/component-probe-results.json)
contain fifteen checked observations, including positive refusal controls.

## How its pipeline fits our architecture

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

```text
Configuration work owned by a classified Loop
├── Resolve a selected, admitted package and exact dependencies
├── Prepare typed assignment and authoritative capability restrictions
├── Render a native representation through an eligible engine
│   ├── Existing direct native layout
│   └── Proposed Agent Harness renderer adapter, pinned and qualified
├── Validate the entire rendered tree and preserve opaque bytes
├── Install through Baltor's existing placement boundary
├── Observe native discovery separately from writing files
└── Execute and independently accept the focused step
```

| Existing boundary | Applicable upstream idea | Baltor ownership retained |
| --- | --- | --- |
| `core.instance_instructions` | Ordered, named instruction sections | Typed assignment, effect limits, exact final bytes and verified native entrypoint |
| `core.node_provisioning`, `core.spawned_provisioning` | A complete preparation plan | Owning Loop authority, offered versus installed material, fresh step assignment |
| `core.service_runtime.catalogue_packages` | Multi-file entity composition | Canonical package digest, raw-byte bodies, roles, dependencies and independent approval |
| `tools/install_selected_material.py`, `ClientLayoutProfile` | Provider-specific output paths and collision diagnostics | Confined paths, expected-current-byte checks, supported client/interface/version binding |
| Existing fresh-instance and executor edges | Configuration suitable for selected harness | Process isolation, endpoint bindings, credential access, limits and acceptance |

This is a proposed engine behind existing edges, not another registry, store,
task class or operational runtime. Existing code does not automatically gain
every proposed transaction or transformation-record property below.

## Ownership: distinguish a plan from a verified installation

The planner collects rendered artifacts, normalizes relative paths and combines
matching outputs. Different providers claiming one path are refused, even if
their bytes match. One provider producing different bytes for the same path is
also refused. Matching same-provider outputs merge their entity owners. These
are valuable controls to preserve.
[Planner](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/planner.ts#L205-L258).

**Correction to a parallel source-only-hash description:** the lock includes
`entities[].sourceSha256` and `outputs[].contentSha256`. The latter hashes the
desired rendered content, including substitution results. It is incorrect to
say the lock hashes only raw sources. The lock does not re-read the output after
writing and does not prove native discovery, usage or task acceptance.
[Output lock construction](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/planner.ts#L397-L437).

Our fixture confirmed that the rendered digest equals SHA-256 of the desired
body. It also showed an unchanged lock despite a later disk edit: the planner
keeps the same desired digest and plans to restore desired content. That is
consistent desired-state management, but does not protect a user's edit.

| Observed fixture | Condition | Consequence for our installer |
| --- | --- | --- |
| Existing unmanaged file refuses installation | File already exists during planning and is absent from managed index | Preserve this check; do not silently adopt it |
| Managed edited file becomes an update | Path is listed as managed; disk differs from desired text | Require expected old byte digest or an explicit user-owned replacement decision |
| Removed source causes deletion of edited managed output | Path remains managed but is no longer desired | Do not treat path membership as current deletion authority |
| File created after planning is overwritten | Another writer creates the same path before `apply` effects | Recheck preconditions at the effect boundary |
| First write survives a later write failure | Second parent path cannot be created | Record partial effects; do not advertise a package transaction |
| Failed deletion still appears in pruned list | Exact scratch delete throws EACCES | Confirm absence before reporting deletion or removing ownership |
| Stale managed path that became a directory is recursively deleted | Old managed filename now names a directory | Refuse unexpected file type and recursive removal |

The writer uses direct `fs.writeFile` for each generated artifact, then writes
lock and managed index separately. `writeFileAtomic` gives metadata files an
individual temporary-file/rename operation; it does not make the artifact tree
or the three phases one transaction. No advisory mutual-exclusion mechanism
appears in this apply path. The filename `manifest.lock.json` denotes a state
snapshot, not a concurrent-writer lock.
[Apply](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/engine.ts#L526-L578),
[atomic helper](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/utils.ts#L84-L105),
[best-effort delete](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/repository.ts#L438-L445).

### Path validation is lexical

The path helper rejects absolute paths, drive prefixes and parent traversal.
It does not establish filesystem confinement. In our fixture, `native` was a
symlink to another disposable scratch directory: writing `native/AGENTS.md`
wrote outside the designated fake workspace. Both locations were inside the
sandbox, and no real user files were touched. This is a condition to guard when
the workspace can contain symlinks, not evidence of a deployed incident.

Directory listing ignores symlink entries encountered inside the tree, but its
base existence check and initial readdir can follow a symlink base. Case-folded
output collisions were not exercised on a case-insensitive filesystem; source
normalization retains case, so that remains a platform qualification case.
[Path helper](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/utils.ts#L10-L35),
[directory listing](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/repository.ts#L320-L340).

## Full packages must preserve binary bytes

The registry skill reader decodes every file as UTF-8 and hashes the resulting
string. The canonical skill loader uses the same text assumption, then runs
substitution on supporting files. An opaque image, archive or binary executable
cannot safely pass through this route unchanged.
[Registry skill reader](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/entity-registries.ts#L425-L480),
[canonical skill loader](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/loader.ts#L502-L595).

The real registry-reader helper converted the fixture bytes `00 ff 80 41` to
`00 ef bf bd ef bf bd 41` on re-encoding. Its recorded digest matched decoded
text, not the original four bytes. This is a direct binary round-trip result;
we did not run a corrupted binary. The existing Baltor `CataloguePackage`
contract already gives every file its own raw-byte digest, size, media type and
role. Preserve that contract and treat binary bodies as opaque. Permit text
transforms only on explicitly declared text roles, with before/after digests.

## Registry provenance is useful, but is not admission

The registry fetch records the actual Git commit as well as the configured ref.
It checks registry shape and ambiguous categorized IDs. During pull, the
imported-source digest can detect local source changes and refuse an unforced
overwrite. These are useful provenance and local-edit controls.
[Checkout](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/entity-registries.ts#L256-L326),
[pull conflict handling](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/engine/entities.ts#L859-L955).

Configured branch/tag references can move. Recording the resolved commit after
fetch is valuable, but is not enforcement of a previously authorized commit.
The pull path fetches entities separately; the inference is that a moving ref
can produce different commits across one multi-entity pull. This scenario was
not tested against a live remote. Use one frozen source snapshot per admission
batch, with exact dependencies, rights evidence and review records. An upstream
registry title or preset does not supply those controls.

### Credential transport needs a different boundary

The Git helper places an Authorization header in clone argv through `git clone
-c http.extraHeader=...`. The isolated argument-builder test used a nonsecret
canary and confirmed that construction. Its error helper successfully redacts
the known token/header in our positive control. No real clone with credentials
was run, and this audit makes no claim that an actual credential was exposed.

Source inspection also shows inherited process environment and no explicit
timeout in the clone invocation. Baltor should use a narrowly authorized fetch
engine with bounded execution and a credential mechanism whose lifetime and
visibility are deliberately controlled. Do not give remotely supplied source
templates general access to the parent environment.
[Clone argument and redaction helpers](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/entity-registries.ts#L517-L555).

## Substitution: keep preferences separate from authority

Environment substitutions intentionally search local files and then the process
environment. They run on raw text before native parsing, across prompts,
supporting skill files and configuration. The upstream guide explicitly warns
that resolved secrets are written into generated output. This is documented
behavior, not an undisclosed defect discovered by the audit.
[Environment guide](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/docs/environment-variables.md).

Our harmless fixture established three precise implications:

- An environment replacement containing JSON punctuation added a new JSON
  property. Values are not escaped as typed strings.
- A replacement containing a behavior placeholder expanded during the second
  pass; a behavior replacement containing an environment placeholder remained
  literal. Disjoint placeholder names do not make pass order irrelevant.
- An unresolved environment placeholder stayed in output with a warning. A
  required credential or endpoint therefore needs a separate readiness gate.

Use a typed parameter map for nonsecret preferences, with schema constraints
and explicit missing-value policy. Keep credential references as references
until the execution binding that needs them. A behavior choice may select
phrasing or an eligible model-specific representation; it cannot grant network,
write, process or spending authority.

### A narrow behavior membership defect

Both the behavior map schema and resolver use JavaScript's `in` operator when
checking allowed values. The real parsed fixture accepted an undeclared default
`toString` and an undeclared configured value `constructor`, with zero diagnostics;
the resolved value was a function inherited from the object's prototype rather
than a declared string instruction. No prototype mutation was involved.
[Schema](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/manifest-schema/src/index.ts#L223-L243),
[resolver](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/behavior.ts#L98-L164).

If we adapt this mechanism, require own-property membership plus a string
value after parsing. Add the exact inherited-name counterexamples before a
repair. This is an input-validation finding with stated preconditions, not a
claim of arbitrary execution.

## Presets and migrations need explicit semantics

Registry preset inheritance resolves siblings from one checkout and rejects
missing parents and cycles. Only skills and prompt sections inherit. Hooks,
MCP, subagents, settings, commands and provider operations come from the derived preset.
Our fixture confirmed that a parent hook disappears from the flattened result,
while a skill from the derived preset overrides its inherited counterpart. A parent preset must
therefore never be treated as a transitive safety-policy bundle.
[Inheritance implementation](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/presets.ts#L113-L180).

The normal schema parsers reject unsupported document versions. Package 2.1.0
currently uses schema major 1 for its versioned documents. The explicit migration
helper has an empty named migration registry and, when no chain exists, bumps an
older document's version then reparses. Our shape-compatible version-0 manifest
was refused by the normal parser but accepted by this explicit helper after
only changing the version. Newer version 2 was refused.
[Migration helper](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/versioning/migrate.ts#L342-L390),
[migration registry](https://github.com/madebywild/agent-harness/blob/2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17/packages/toolkit/src/versioning/registry.ts).

Source inspection finds another distinction: migration's derived-state path
filters initial unmanaged-output collisions, rebuilds managed paths and plans
again. It can establish ownership of desired paths without the ordinary apply
collision refusal. We did not run that full migration CLI; the report does not
claim a tested end-to-end deletion through migration. Baltor should retain its
explicit unsupported-version refusal and should never use schema migration as
implicit authority to adopt customer files.

## Adoption criteria and useful improvements

| Candidate | Decision and discriminating evidence needed |
| --- | --- |
| Ordered instruction sections | Adapt the composition idea behind `InstanceInstructionWriter`; test authority sections cannot be overridden by package prose |
| Native renderer library | Experiment behind the existing layout boundary; pin compiler, client, interface and final tree; refuse missing required outputs |
| Preset inheritance | Consider explicit bounded dependency composition; show an effective flattened manifest, including omitted hooks and scope changes |
| Managed-index writer | Do not adopt as Baltor's writer; first require byte preconditions, confinement, type checks, truthful deletes and partial-effect records |
| Registry importer | Reuse provenance concepts; retain quarantine, exact commit binding, rights evidence, independent review and credential isolation |
| Raw substitution | Restrict to declared nonsecret text transforms; use typed native config rendering and explicit secret references |
| Full skill-tree pipeline | Text-only experiment until opaque-byte preservation is qualified |
| Version migration fallback | Do not adopt automatic version bump into Loop Engine's current contract policy |

For a useful first experiment, compare the existing direct layout engine and a
pure upstream-renderer adapter on the **same admitted text package**. Give both
the same assignment, client profile and effect ceiling. Compare the final file
tree, transformation lineage, native discovery and accepted task result. A
clean render or passing schema is only one stage.

For a large library, index a canonical package once, then record qualified
representations by model and harness profile. Do not multiply the headline count
for identical payloads in four client folders. Every representation should name
the canonical source digest, transformation/version, final file digests and
its qualification evidence. Search can then filter by role, task, dependency,
effect and verified native compatibility without treating filenames as proof.

The most valuable product additions suggested by this audit are an effective
configuration preview, a clear explanation of why each file is present, visible
scope changes, a local-edit conflict report and a distinction between rendered,
installed, discovered and used. These improve customer confidence more directly
than silently exporting more formats.

No code from this project was installed in the Loop Engine runtime, no catalogue
item was approved or published, and no customer workspace was changed by this
research.
