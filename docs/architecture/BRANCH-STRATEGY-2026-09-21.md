# Branch strategy: the streamlined main line and the full-capability checkpoint

Kind: decision record with reasoning and context. Date: September 21, 2026.
Owner direction recorded the same day; see
[the harness-first decision record](ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md)
for the phased plan this branch layout serves.

## The two branches and what each is for

```text
GitHub
├── main
│   ├── serves harness intelligence first
│   ├── default family policy: harness family alone
│   ├── every executable step delegates to a standard harness
│   │   (OpenCode, Codex, Claude Code, and others) through the
│   │   existing adapter contracts
│   ├── retires the in-process Loop-native execution path in
│   │   recorded phases, each phase gated by checks
│   └── keeps every typed boundary: items, families, catalogue,
│       provisioning, grants, licences, host records, protocol
└── checkpoint/full-capability-2026-09-21
    ├── the complete tree as of 2026-09-21, revision a3bd0f1
    ├── all four persistent layers serving all three families
    ├── the in-process solve engine, the campaign runner, the
    │   Kaggle executor, the spawned kernel
    ├── 6229 of 6229 self-test checks passing
    └── frozen: no further development, the rollback target and
        the source for any future custom engine
```

## Why the owner chose this

The product is a hosted intelligence service plus a local engine, and the
customer runs their own harness and their own models. The private beta's
first promise is the drop-in files a customer's existing harness already
knows how to read: SKILL.md, AGENTS.md, plugin declarations, protocol server
configurations. That material is the harness family, and it is the material a
customer can use in the first five minutes.

The in-process Loop-native execution path is the larger, older half of the
repository. It carries the solve engine, the campaign runner and the Kaggle
executor, and it is not what a first customer touches. Keeping both halves
live on the main line means every change pays for both, and every release
qualifies both, while the served product needs one of them.

The owner's words, September 21, 2026:

> I want to streamline it, and get rid of loop native intelligence, open
> knowledge format intelligence, as well as any non-harness implementations
> of a loop-node, all loop-node should use a harness and we can remove any
> capabilities that conflict with that. Once we have a large number of users
> we can consider adding in a custom loop-node type of harness that we build.
> However, for the moment I don't think we need it, however, we still need
> the layers, types, abstract classes, encapsulation, middlewares, etc to
> allow easily replacement, and switch out of different engines or
> harnesses.

## What "streamlined" does not mean

- It does not delete the Loop runtime. The Loop stays the one operational
  runtime vertex and the envelope for delegated work. No second runtime type
  is created and no `*Node` class is introduced.
- It does not delete the four persistent layers, Runtime Memory, or the
  family axis. They remain the storage taxonomy; the harness family is
  served first by policy, not by burning the others down.
- It does not delete the wrapper, adapter, recipe and middleware layers.
  They are the point: any harness or engine is replaced or added by
  declaring a tested profile, not by editing call sites. Adding a family
  later is a host configuration change, not a code change.
- Nothing is lost from history. The checkpoint branch holds the full tree,
  and every removal on main names the phase and the decision record.

## How to work on each branch

On `main`:

1. Follow the working cycle in
   [the takeover checkpoint](../context/TAKEOVER-CHECKPOINT-2026-09-20.md):
   check first, repair, gate, commit, confirm continuous integration.
2. Phase work for the harness-first retirement lives in
   [the decision record](ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md);
   each phase adds its named checks before its removals.
3. Never weaken a surviving check to make a phase land. A check that no
   longer applies moves to the checkpoint branch with a recorded reason.

On `checkpoint/full-capability-2026-09-21`:

1. Read this document and the decision record before proposing changes.
2. The branch is frozen for development. If a defect in shared code affects
   both branches, fix it on main and cherry-pick with the reason recorded.
3. When a customer or a benchmark needs a capability the main line retired,
   the answer is a recorded owner decision, either restoring from this
   branch or rebuilding behind the typed boundary, not a silent merge.

## Parked capabilities keep their folders, with a marker file

The main line keeps the existing folder structure. Nothing is hollowed out
or renamed. Where a phase removes a capability from the main line, the
folder stays and one marker file, `PARKED.md`, records what was parked, why,
and the exact path back:

```text
src/loop_engine/
└── (a folder whose capability is parked)
    └── PARKED.md
```

Each marker file holds five facts, so a reader never has to ask:

1. What capability lived here, and what it did.
2. The date and the owner decision that parked it.
3. The last revision on this branch where it worked, with its check count.
4. The branch and revision where the full working implementation is frozen:
   `checkpoint/full-capability-2026-09-21`, revision `a3bd0f1`.
5. The typed boundary it would be rebuilt behind, if the owner turns it on
   later, and the record that decision would be written into.

A parked folder is documentation that stays beside the code that replaced
it, not a deletion. Turning a capability back on is a recorded owner
decision implemented behind the named boundary, never a silent merge from
the checkpoint branch. The marker files are committed, so the reasoning
travels with every clone and every future session.

## Where each capability lives after phase 3

| Capability | main | checkpoint |
|---|---|---|
| Harness intelligence serving (family policy, drop-in files) | live, default | present |
| Loop-native family serving | host-declared policy only | present |
| Open Knowledge Format family | vocabulary + host-declared policy | present |
| In-process solve engine, campaign runner, Kaggle executor | retired (phase 3) | present, frozen |
| Harness adapters and recipes (OpenCode, Codex, Claude Code, ...) | live | present |
| The Loop runtime, envelope, profiles, contracts | live | present |
| Four persistent layers, Runtime Memory | live (storage taxonomy) | present |
| The hosted service, accounts, billing, protocol | live | present |

## Restoring or adding later

The typed boundaries are the restore path. A family is added by a host
configuration record; a harness is added by a recipe and adapter module
behind `HarnessProcessSpec`; a custom engine, if the owner decides to build
one after the user base exists, is added behind the same executor interface
the delegation phase creates, never by forking the runtime.