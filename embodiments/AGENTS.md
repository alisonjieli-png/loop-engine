# Harness development instructions

These instructions complement [the repository rules](../AGENTS.md) for
first-party harness work in this directory. Read [ASTRA.md](../ASTRA.md) and
the [layered harness design](../docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
before changing wrapper composition or native control. Preserve the full
terminology and complete behavioral explanation in those documents.

An outer Loop Engine Loop may govern a harness's inner loop. Keep the outer
assignment, contracts, remaining authority, independent acceptance, and Run
History intact while a native harness performs its permitted internal work.
Native completion is not automatically task completion.

Keep wrapper depth, wrapper order, native control ownership, step profile,
model, prompts, tools, skills, plugins, hooks, and context as separate choices.
Retain initial settings and ordered fallback priorities. The dimension
inventory is open-ended; support richer profiles without removing qualified
restricted profiles.

Use the existing registrations, provider authority, workspace services,
effect approval, and Run History. Do not create another runtime, registry,
or event store. A wrapper with independently governed work becomes a
classified canonical Loop rather than a new runtime class.

Test actual initialization, loaded instructions, applied settings, native
turns, output identities, cancellation, and physical usage. Compare native
and outer control without double retries, reset budgets, duplicated effects,
or hidden context transfer. Unknown outcomes remain unknown.

Do not modify installed `runtime` dependencies or reference snapshots as if
they were first-party source. A new fork or recipe needs an exact identity,
provenance, compatibility checks, and separate qualification. Do not edit
`harness.json` or launch flags solely to propagate development guidance.

Read [HARNESS-GUIDE.md](HARNESS-GUIDE.md) for source and evidence pointers.
