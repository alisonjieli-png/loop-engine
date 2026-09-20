# Files and context for a harness instance

Kind: operating guide with explicitly proposed extensions.

Loop Engine has typed assignment and instruction templates and a working
folder provisioner. It does not yet have a fully qualified native-layout
compiler for every harness. A file being offered, downloaded, placed on disk,
loaded into context, used, and independently helpful are different observations.

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
    ├── Role: Practitioner, Intelligence, or Solution
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

The harness is an adapter used by a Loop. A folder, template, instruction
file, skill, or catalogue reference is not another runtime. Folder names and
instruction prose never grant permissions.

## Generated layout today

The [provisioner](../../src/loop_engine/core/node_provisioning.py) writes this
layout into an existing, confined instance directory:

```text
instance/
├── AGENTS.md             composed instruction sections and digest marker
├── harness-specific file when the configured style declares another name
├── task.json             typed assignment, requirements and authority
├── provisioning.json     exact offers, withheld items, digests and exposure
├── contracts/            created empty; contract references are in task.json
└── artifacts/            created empty; permitted work can produce outputs
```

The [instruction composer](../../src/loop_engine/core/instance_instructions.py)
uses typed sections for assignment, authority, capabilities, working folder,
reporting, and refusals. The current adapter data supports additional names
such as `CLAUDE.md`, `GEMINI.md`, and `QWEN.md`. These are declarations in our
adapter, not a guarantee that every installed native harness loads them.
Exact harness version, discovery settings and observed loading need checking.

`task.json` carries the objective, output contract references, dependency
identifiers, required capabilities, allowed effects, selected harness style,
mode and explicit model-call permission. Preparation authority is separate
from what the running harness may do.

`provisioning.json` records what was offered and withheld, why it was withheld,
and offered versus exposed byte counts. Its current `bodies_included` field
is false. The existence of `contracts/` does not mean contracts were fetched,
and offering a skill does not mean its native directory was installed.

Provisioning refuses traversal, symbolic-link escapes, unsafe overwrite,
excess authority and unresolved blocking guardrails. It does not launch a
process or call a model. The owning run records the exact instruction identity;
the process adapter separately records the material it mounts.

## Recommended context organization

Use a versioned layout profile and compile it into the selected harness's
supported native paths. Keep the profile passive and keep the existing
provisioning boundary as its owner. This extension is not fully implemented.

```text
Scoped assignment material
├── Always available briefing
│   └── objective, input and output contracts, limits and reporting rules
├── Selected read-only intelligence
│   └── exact revisions of context, skills, contracts and dependencies
├── Explicitly writable work
│   └── temporary working files and candidate artifacts
└── Host-owned records outside model-editable context
    └── permissions, credential references, usage, checkpoints and acceptance
```

The native adapter should choose where a supported harness expects its skill,
plugin and context files. Do not invent one universal skills directory or copy
the complete repository into every instance. Some assignments need only a
briefing; others need substantial material. The selected configuration and
measured task need decide that, not a universal minimum-context rule.

Keep exact source identities, licenses, digests, dependencies, trust and
qualification state beside selected material. Retain explicit read-only and
writable scopes. Provider refresh tokens and secret keys stay in the host's
credential mechanism, not in Markdown or shared context folders.

## Remaining integration checks

1. Fetch the selected service reference and verify its exact bytes before
   preparing the harness folder.
2. Populate only the selected native-layout files and their required
   dependencies under explicit authority. Do not infer promotion from placement.
3. Check what the actual harness loaded, including unexpected inherited
   instructions, user-level configuration, disabled discovery and truncation.
4. Compare a useful-resource case with a withheld or changed resource. A
   mounted-file digest alone does not establish use or benefit.
5. Preserve outputs, records and unresolved effects across restart and allowed
   harness changes. Reject a retry that would repeat an uncertain external action.

The [onboarding guide](harness-service-onboarding.md),
[configuration requirements](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md),
and [layered wrapper direction](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
describe the wider requirements. The existing task template library is a
separate source of typed task patterns, not evidence that every native
harness context layout is complete.
