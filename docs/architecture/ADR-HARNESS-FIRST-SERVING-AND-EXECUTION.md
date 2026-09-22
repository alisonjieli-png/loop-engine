# ADR: Harness-first serving, and the retirement of the in-process Loop-native execution path

Status: accepted (owner direction, September 21, 2026). Phased.

## The decision

Two decisions, recorded together because they came together:

1. The private beta and the hosted main line serve **harness intelligence
   first**. A host declares, as typed policy, which intelligence families its
   catalogue serves. The default policy serves the harness family alone, for
   the same reason the default licence policy serves one licence: the safe
   default is the smallest set that covers what a customer can actually use
   today, and a host that wants more declares more.
2. The **in-process Loop-native execution path is retired from the main
   line**, in phases, once the harness delegation path carries the same
   guarantees. Every executable step delegates to a standard harness
   (OpenCode, Codex, Claude Code, and others) through the existing adapter
   contracts. The wrapper, comparison, middleware and adapter layers stay, so
   any engine or harness can be replaced or added later.

## The owner's words

> Can we create a branch of this code that is a checkpoint of all of the
> functionality we have now, and move forward with a branch (as the main
> branch) that only uses harness intelligence? While maintaining the ability
> to add new types of intelligence in later? I want to streamline it, and get
> rid of loop native intelligence, open knowledge format intelligence, as well
> as any non-harness implementations of a loop-node, all loop-node should use
> a harness and we can remove any capabilities that conflict with that. Once
> we have a large number of users we can consider adding in a custom
> loop-node type of harness that we build. However, for the moment I don't
> think we need it, however, we still need the layers, types, abstract
> classes, encapsulation, middlewares, etc to allow easily replacement, and
> switch out of different engines or harnesses.

## What is preserved

- `checkpoint/full-capability-2026-09-21` holds the full-capability tree:
  every layer, the in-process execution path, the solve engine, the campaign
  runner and the Kaggle executor, exactly as they passed 6229/6229 checks.
  Nothing is deleted from history; the checkpoint branch is the rollback
  target and the source for any future custom engine.
- The typed boundaries stay: `HarnessIntelligenceItem`, the family axis
  (committed `a3bd0f1`), the catalogue, the provisioning contracts, the
  grants, the licence policy, the host configuration records, the protocol
  service. Adapter and recipe modules for each supported harness stay.
- The four persistent layers stay as storage layers. The families organize
  the same bodies by what they follow. Removing a family from a host's
  serving policy does not remove the bodies from the library.

## What changes

### Phase 1 (this record): family serving policy

A host configuration declares `intelligence_family_policy`, a typed record
exactly parallel to `license_policy`. The default accepts the harness family
alone. An item whose family is not accepted is refused before the manifest is
served, with a stable refusal code, the same way an unlicensed item is
refused today. Adding a family later is a host configuration change, not a
code change.

### Phase 2: execution delegation

Every step that today executes in-process through the spawned kernel delegates
to a harness through the existing `HarnessProcessSpec` contract. The in-process
solution runner, the campaign runner and the Kaggle executor move behind the
same typed executor interface so a host chooses the executor the way it
chooses a harness: by declared, tested profile, not by import path.

Sequencing condition, recorded September 21, 2026: phase 3 began with the
suite retirement (`ea59df0`) before phase 2 existed, because the owner
directed the main line to stop paying for the in-process checks. That order
is deliberate, not an accident, and it narrows the proof: until the first
delegated execution runs, phase 2's own acceptance is that one executable
step goes only through a harness — the retired in-process path may not be
used to meet it. A delegation claim met by the in-process path, however
the call site is disguised, is the known-wrong case for phase 2.

### Phase 3: retirement from the main line

When the delegated path carries the same checks (cancellation, deadline,
budget accounting, effect approval, checkpoint and resume), the in-process
execution modules are removed from the main line and live only on the
checkpoint branch. The Loop class remains the single operational runtime
vertex and the envelope for delegated work; no second runtime type is
created, and no `*Node` class is introduced.

## What is explicitly not decided here

- No removal of the four persistent layers, Runtime Memory, or the family
  axis. They are the storage taxonomy; the decision is about serving and
  execution.
- No automatic migration. Historical records keep their bytes; a host file
  that declares no family policy gets the harness-only default and a
  recorded reason in the host loader's output.
- The Open Knowledge Format family stays declared in the vocabulary for
  material imported later; a host that wants it declares it.

## The future custom loop-node harness

Owner direction, September 21, 2026: once the service has a large number of
users, we may build our own custom loop-node in the format of a harness, a
loop-node harness we own, alongside OpenCode, Codex and Claude Code. That
engine will be added behind the same typed executor interface the delegation
phase creates: a recipe and adapter module, a tested capability profile, and
a declared host choice. It is not a new runtime type, not a `*Node` class,
and not a fork of the Loop runtime. Until the owner decides to build it, the
full in-process execution path it would replace remains frozen and working
on `checkpoint/full-capability-2026-09-21`, and the restore path is the
typed boundary named in [the branch strategy](BRANCH-STRATEGY-2026-09-21.md).

## Checks that hold this decision

- `host_serves_only_the_declared_intelligence_families` — a manifest item
  whose family is outside the declared policy is refused before serving.
- `removed_family_policy_guard_is_detected` — the phase 1 guard, removed,
  fails a named check.
- `family_policy_is_versioned_and_refuses_unknown_keys` — the record is
  typed and versioned like the licence policy it mirrors.
- `default_family_policy_serves_the_harness_family_alone` — the safe default
  is one family, and the refusal names the family it does not serve.
