# ADR: Self-orienting abstraction governance

Status: implemented vertical slice on 2026-08-31.

## Context

Loop Engine had strong architecture and call-boundary checks, but no single
development artifact that bound conceptual concerns to the exact live symbols
and enforcing checks for one working state. It also lacked a contextual audit
for behavior hidden in literals, defaults, raw keys, and prompt text.

`LoopConfigOverride` used raw empty strings, empty tuples, and `None` as
compatibility omission sentinels. This made explicit null and explicit empty
values impossible to represent. The campaign and external harness adapters
also assembled model instructions inline without one versioned bundle identity.

## Decision

```text
Development Assurance Plane
├── Repository orientation Practitioner Loop
│   ├── deterministic repository discovery
│   ├── parsed symbol, import, call, and configuration-flow indexes
│   ├── concept-to-authority bindings
│   └── digest-bound passive snapshot
├── Hardcoding audit Practitioner Loop
│   ├── Python AST and structured-resource inspection
│   ├── context-aware classification
│   ├── secret-safe findings
│   ├── exact owned allowlist
│   └── baseline and delta gate
└── Product contracts reused by the reviewed fixes
    ├── RuntimeSettings
    ├── ParameterDefinition and ParameterInput
    ├── bounded Intelligence Loop proposal
    └── PromptResourceBundle and PromptSlotDefinition
```

Self-orientation and whole-repository scanning remain in
`loop_engine_devtools`. The product package never imports devtools. Normal Loop
execution consumes typed settings, profiles, resources, and exact references;
it does not scan the repository.

Parameter resolution is a passive product contract under the existing
`RuntimeSettings` owner. It is not another settings system. The visible
precedence is:

1. explicit invocation value;
2. authorized run override;
3. Loop profile;
4. capability profile;
5. domain policy;
6. deployment configuration;
7. repository default;
8. deterministic derivation;
9. bounded Intelligence proposal;
10. unresolved or rejected.

The resolver distinguishes omitted, explicit null, empty collection, empty
string, false, zero, and an ordinary value. Invalid explicit values fail and do
not fall through to a default. Sensitive values are redacted but digest-bound.

Prompt text remains under the existing `strings.prompt_fragments` resource
boundary. A prompt bundle declares components, composition order, slot types,
trust classes, sensitivity, escaping, size policy, omission behavior,
provenance, output schema, interpreter profile, and policy identity.

## Compatibility

Raw `None`, empty string, and empty tuple values in `LoopConfigOverride` keep
their pre-1.0 omission behavior. A caller uses `ParameterInput` when it must
express explicit null, empty, false, or zero. `RuntimeSettings.loop_config()`
keeps its return type. `loop_config_with_record()` adds inspectable source
evidence without breaking existing callers.

## Configuration-theater rejection

The campaign prompt was not moved to YAML. A text file alone would not provide
slot types, trust boundaries, size policy, provenance, identity, validation,
or Run History evidence. It was moved to a typed versioned bundle owned by the
existing prompt-resource module.

The 65,536-byte source-hashing chunk remains a local implementation literal.
It is listed in the exact allowlist because changing it does not change digest
semantics, policy, deployment behavior, or caller contracts. Moving it to
global settings would add configuration without adding authority or value.

## Intelligence boundary

A parameter Intelligence Loop receives one parameter definition, a bounded
context, and an admitted value set. It returns a proposal, confidence,
evidence, assumptions, unknowns, alternatives, abstention state, rejection
reason, and validator. The deterministic resolver can reject the proposal. The
proposal cannot override an explicit value or expand the allowed set.

## Consequences

- Repository changes invalidate orientation only when bound authority,
  metadata, or enforcing checks change. The full working-tree digest remains
  visible without making every documentation edit invalidate bindings.
- The audit scans every relevant source file but gates only precise new high
  severity findings.
- Finding counts are not a success metric. A typed field may add literals while
  improving ownership and traceability.
- One source may still contain intentional local literals.
- Graphify can provide optional descriptive Code Intelligence, but its graph is
  passive evidence and not execution authority.
- The canonical executable runtime remains `Loop`, with exactly three modes.

## Verification

Current focused evidence covers:

- 7 repository-orientation canaries;
- 12 hardcoding-audit canaries;
- 16 parameter-resolution and RuntimeSettings tests;
- 13 prompt-resource tests;
- 21 external-harness adapter tests;
- one real Ollama provider probe;
- one real OpenRouter accepted zero-price gateway call;
- one real bounded Ollama parameter-inference call;
- a cold and unchanged Graphify code-only extraction.

Full source, conformance, packaging, and clean-install results belong in the
final verification report. They are not implied by these focused checks.
