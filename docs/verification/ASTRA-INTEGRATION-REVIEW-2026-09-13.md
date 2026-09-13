# Astra integration review, September 13, 2026

The owner authorized Codex to take over Claude's unfinished work, review it,
and commit and push the verified result to `main`. Review started from
`f01758929241d729d25b5a5e02a2a4bc0231d0e8`, with 26 modified tracked files
and seven new source or test files. Four older local audit artifacts were
outside this change and were not added.

## Corrections made during integration

| Boundary | Finding and correction |
|---|---|
| Native instance composition | A symlinked `.opencode` root could write outside the workspace even when composition later failed. Refusal precedes materialization. Reserved manifest paths and aliases cannot replace another configured file. |
| Native configuration | Description, model, and permission strings could inject YAML fields. Strings are quoted. Permission patterns preserve declared order, including OpenCode's last-match semantics. Validated control mappings cannot change through mutable aliases. |
| Session request | System instructions, temperature, model overrides, and other gateway fields were silently ignored. Unsupported fields receive a pre-execution refusal. Supported structural expectations and validators are checked. This native session is not a complete gateway replacement. |
| Session accounting | Multiple reported model calls became one attempt; incomplete usage could become a known subtotal or zero. Each reported call has an attempt. Missing usage remains unknown. Transport failure is retained as uncertain and cannot restart under a finite ceiling. |
| Native completion | Partial text from a failed process could be accepted. A failed native process is refused. An earlier valid object cannot replace an invalid final answer. |
| Prompt files | Every native invocation owns a private prompt directory. Concurrent sessions cannot replace each other's prompt, and a pre-existing workspace prompt file is preserved. |
| Acceptance | Generated attempts could agree, override failed checks, and clear unresolved criteria. Agreement is advisory. Dissent may tighten acceptance, but agreement cannot approve work or remove requirements. |
| Host verification | Ranking and checkpoint creation could execute generated code without a separate grant. Host diagnostic execution requires an explicit Boolean permission. It remains a trusted-host facility, not a sandbox. |
| Process lifetime | Driver and queue subprocess cleanup targets their own process groups, including descendants. It does not search for or stop unrelated processes. |
| Checkpoint freshness | Missing trees, changed source, and removed attempts cannot retain a current ranking. Saved ranking and current source identity remain separate. |
| Overnight tools | Claude's worktree ownership checks, opt-in transcript execution, environment allowlists, shared call accounting, and graceful interruption changes were retained. Integration also carries uncertainty across fresh step sessions and removes a direct deletion fallback after Git removal. |
| Audit scanner | A credential pattern matched part of `task-campaign-runs`. Matching requires a token boundary; bare, assigned, and quoted credential-shaped fixtures remain detected. The audit baseline and allowlist were not weakened. |

OpenCode documents permission order in its official
[agent configuration guide](https://opencode.ai/docs/agents/#permissions).
This supports the serializer correction, not a claim of new live provider
qualification.

## Design boundaries retained

The complete explanation and classification in [ASTRA.md](../../ASTRA.md)
remain authoritative development context. The original dimension inventory
is a required baseline, not a maximum. Further prompts, cognitive steps,
actions, intelligence, wrappers, and native controls remain possible
configurations, subject to typed implementation and qualification.

The existing wrapper records support ordered alternatives and per-control
ownership declarations. Their presence does not install wrapper executors
or native goal controllers. The direct adapter remains a supported choice.
The native OpenCode session has narrower request support than the canonical
gateway and detects internal call overruns only after execution.

Agreement across different models does not prove statistical independence.
The overnight selector is a campaign-specific recommendation policy, not a
general optimizer. No new provider call, model-quality experiment,
cross-task learning qualification, or full-system benchmark was performed
for this integration.

## Verification

The [saved verification evidence](../../artifacts/astra-integration-20260913-BszOIr/README.md)
records the final package digests and results. Earlier source counts in
Claude's review refer to earlier revisions.

| Check | Observed result |
|---|---|
| Source self-test | 4,331 of 4,331 passed. |
| Fresh wheel installation | 4,296 of 4,296 passed with base dependencies and DuckDB. Optional adapters absent from that installation are listed in the saved result. |
| Conformance | All 27 gates passed in source and the clean installation. |
| Repository conformance | Passed with 497 indexed package files. |
| Development command tests | 93 of 93 passed; the hosted workflow now runs these tests. |
| Harness laboratory | 42 of 42 passed. |
| Host-runtime tests | 140 of 140 passed. |
| Independent qualification laboratory | 3 of 3 passed. |
| Development assurance canaries | 23 of 23 passed, including the credential-boundary regression. |
| Offline examples | 19 scripts exited successfully. The provider-connecting example was excluded to avoid an unrequested live probe. |
| Documentation | Markdown structure and repository prose checks passed on the changed guides and report. |

An early in-progress source run passed 4,329 of 4,330 checks. Its failing
expectation treated a missing directory like an empty directory. That
expectation was corrected to match the explicit missing-source result.
The failed run remains in local evidence. Final source bytes match the
clean-wheel build input. No provider calls were made.

## Audit gate still failing

The hardcoding gate remains failed against its saved baseline. Using the
same corrected scanner, both the starting revision and reviewed working
tree have 499 new high-severity findings relative to that baseline. Five
high-severity identities appeared and five disappeared during integration;
the [saved delta](../../artifacts/astra-integration-20260913-BszOIr/hardcoding-delta.json)
names them. The new locations cover verdict handling, ranking, explicit
gate environments, and a moved credential-environment reference. They are
visible review findings, not suppressed exceptions.

There are no critical findings after the token-boundary correction. The
baseline and allowlist remain unchanged. These passing functional checks
do not establish a green hosted workflow; the audit backlog still blocks
that claim.
