# Host-owned execution through the canonical Loop

Status: implemented, with a bounded live repository example.

`core.generated_project` is one available execution capability. It does not
define the universal meaning of task input, action, verification, or output.
The public solver may instead use a caller's typed host binding and return
the host's verified result without constructing a Python project.

The normative fields and invariants are in `architecture.yaml`, under
`host_task_execution` and `source_admission`. The
[embedding guide](../guides/embedding-loop-engine.md) contains the complete
Loop classification tree, API, trust boundary, and adoption checks.

## Boundaries

```text
Task and explicit host registration
  -> Starting Practitioner Loop
  -> selected capability and scoped permission request
  -> schema, binding, state, and exact host approval checks
  -> Code Intelligence invocation Loop
  -> typed host observation
  -> separate Practitioner verifier using host-owned gates
  -> recorded local progress or task completion
```

The existing Capability Directory remains the registry. `CustomPluginsPort`
remains the public port. Host bindings and invocation policies are passive
configuration, not another runtime or intelligence layer. Models cannot
register trusted callbacks, change protected verifier code, or grant themselves
permission by emitting a capability description.

The host supplies the actual environment and effects. Its operations may use
files, commands, databases, services, or other systems. Domain knowledge belongs
in these implementations and their contracts, sources, and evaluators. No
industry name chooses a core workflow.

## Acceptance

The host must authorize each exact operation and explicitly grant model
visibility of host output. These grants do not enable unrelated core effects.
The framework checks schemas, pins registrations, preserves result identity,
and requires current issued verification. It distinguishes intermediate
observations from completed tasks.

The host is trusted for callback behavior, snapshot coverage, sandboxing, and
the meaning of its gates. These declarations do not prove an arbitrary host
adapter safe. Unknown effects require reconciliation; version 1 does not
promise autonomous cross-process recovery or exactly-once external effects.

## Source access

The built-in source reader uses bounded UTF-8 content inspection instead of a
programming-language suffix allowlist. Admitted bodies still require disclosure
authority and complete-text validation. Exclusion records explain binary,
unsupported, protected, missing, unreadable, and pruned sources without exposing
their bodies.

This removes silent language exclusions. It does not mean every encoding,
file format, protocol, or deployment target has an installed executor.

## Evidence standard

The JavaScript repair demonstrates the host path with a populated project and
fixed repository tests. It is not proof of arbitrary unseen-task performance,
automatic capability promotion, or Git-branch automation. Broader claims require
frozen held-out tasks, independent evaluator contracts, exact outcome records,
and explicit infrastructure and semantic failure reporting.
