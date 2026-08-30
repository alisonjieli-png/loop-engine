# HCF pattern review

## Sources

- Loop Engine source revision: `a7db02f25167a68c4d1e0b64b2fe57730fa35e80`
- HCF reference revision: `9cfca7de63c309ee6b5b38088cd446af85e9ff46`
- HCF tag: `hcf--v2.3.0`
- HCF tests observed locally: `152/152`

The review covered the HCF README, changelog, hook contract, four skills,
three agents, all hook scripts, hook registration, the test runner, assertion
library, all test suites, and 22 fixtures.

## Decision summary

```text
ADOPT
└── distinct empty, missing, malformed, failed, and drifted results

ADAPT
├── planning and execution separation
├── grounded discovery before clarification
├── evidence-first work and optional software TDD
├── dependency waves with stronger write/effect safety
├── resolve-once exact handoffs
├── one resolver per concern
├── scoped execution-context fingerprints
├── declarative extension enrollment
├── zero-work fast path
├── independent plan assurance
├── resume reconciliation and blocked terminal states
├── task-conditioned retry and independent-branch continuation
├── verification before publication
├── contribution isolation
├── self-hosting boundaries
└── legacy-authority migration

REJECT AS UNIVERSAL RULES
├── fixed four-phase product lifecycle
├── exactly eight global hooks
├── Claude agent ontology
├── Markdown as execution authority
├── auto-trigger descriptions as authority
├── one global retry count
├── TDD for every domain
├── no-registry dogma
├── dependency-only parallelism
└── user silence as absence of audit evidence
```

## Architecture boundary

No HCF runtime, agent type, graph executor, hook runner, Markdown authority, or
fixed retry policy is transferred. Every adopted behavior maps to existing
Loop Engine Loops, `LoopGraphDefinition`, Run History, Skill admission,
settings, workspaces, effect approval, or verification.

The machine-readable assessments are in
`artifacts/external-patterns/hcf_pattern_assessments.jsonl`.
