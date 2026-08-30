# HCF concept fit

HCF remains a read-only operational reference. Its transferable behaviors map
to existing Loop Engine authorities.

| Pattern | Existing authority | Smallest extension |
|---|---|---|
| Planning boundary | Practitioner and LoopGraphDefinition | Passive planning authority and plan records |
| Evidence-first tasks | Verification obligations | Criterion-to-evidence bindings |
| Dependency waves | LoopGraphDefinition and scheduling | Task slices plus concurrency decisions |
| Exact handoff | DelegationSpec and LoopRuntimeContext | WorkerAssignmentEnvelope |
| Extension discovery | Plugin bundles and SkillRegistry | Lifecycle extensions and resolved snapshot |
| Drift detection | Exact digests and Run History | Narrow fingerprint policies |
| Plan review | Practitioner verifier | PlanAssuranceResult |
| Resume | Run History and checkpoints | Reality reconciliation result |
| Retry | Repair and liveness policies | Task-conditioned RetryPolicy |
| Publication | EffectApprovalService | Commit and publish authorization requests |
| Self hosting | AGENTS.md and bootstrap checks | Explicit SelfHostingProfile |
| Migration | Legacy readers and conformance | One-authority detection and migration result |

Rejected duplicates include an Agent runtime, HookRunner, TaskGraph executor,
Markdown state authority, second plugin registry, or second event history.
