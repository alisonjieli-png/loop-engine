# Self-orienting abstraction evaluation

This report records the current vertical slice. It separates deterministic
fixtures, real provider calls, and external-tool observations.

## Orientation

The live snapshot discovers two package roots, `src` and `devtools/src`, and
binds 18 conceptual concerns to exact symbols. The current bindings include:

- `Loop` and `LoopDefinition`;
- the three canonical modes and three roles;
- `LoopProfileSpec` and `LoopContract`;
- `RuntimeSettings` and `load_runtime_settings`;
- Code Intelligence admission and reusable-capability lifecycle;
- `UnifiedCatalog`;
- reactive execution and Run History;
- model and effect authorities;
- intelligence layers, prompt resources, and call-boundary auditing.

The snapshot identity excludes generation time. A change to an unrelated guide
changes the visible working-tree digest but not the semantic binding identity.
A bound source change invalidates the snapshot.

## Whole-repository audit

The baseline was generated before the external-harness prompt extraction.

| Measurement | Baseline | Final |
|---|---:|---:|
| Files scanned | 769 | 770 |
| Literal candidates scanned | 179,045 | 179,141 |
| Material findings | 9,374 | 9,379 |
| High severity | 770 | 770 |
| Medium severity | 8,604 | 8,609 |
| Prompt-resource findings | 106 | 105 |

The final delta resolved one inline Deep Agents instruction finding. It added
six medium findings for the new version and digest fields on typed external
harness records. No new high-severity finding appeared.

This is an intentional example of why lower literal count is not the objective.
The result has five more material findings but clearer semantic ownership,
version identity, safe Run History evidence, and no inline runtime instruction
for the selected adapter path.

Machine evidence:

- `artifacts/verification/hardcoding_audit_baseline.jsonl`
- `artifacts/verification/hardcoding_audit_final.jsonl`
- `devtools/hardcoding-allowlist.yaml`

## Parameter resolution

The deterministic suite proves:

- explicit value before profile, policy, deployment, and default;
- separate domain, deployment, and repository-default sources;
- unresolved required no-default behavior;
- invalid explicit value cannot fall back;
- omitted, null, empty collection, empty string, false, and zero are distinct;
- explicit null and zero resolve without conflation;
- sensitive values are redacted and digest-bound;
- intelligence cannot override an explicit value;
- invalid and low-confidence proposals fail safely;
- deterministic resolution makes no intelligence call;
- legacy `LoopConfigOverride` omission behavior remains compatible;
- an explicit empty mode set fails rather than inheriting;
- a deterministic Loop derives an empty model setting without intelligence.

## Prompt resources

The campaign prompt now separates:

```text
campaign.problem.solve@1.0.0
├── untrusted goal
├── untrusted structured inputs
├── optional untrusted deterministic baseline
└── trusted output contract
```

The resource tests cover required and unexpected slots, provenance, size
limits, deterministic identity, optional-component omission, trust labels, and
closing-tag injection neutralization.

The external Pydantic AI, Deep Agents, and OpenAI Agents instructions are now
versioned resource compositions. The normalized result records bundle, slot
schema, and render digests without storing the prompt text.

## Real provider checks

### Ollama Cloud probe

One authorized call used `ollama_cloud`, route `cloud.default`, and model
`deepseek-v4-flash:0731`.

| Measurement | Observed value |
|---|---:|
| Status | accepted |
| Physical model calls | 1 |
| Input tokens | 66 |
| Output tokens | 119 |
| Total tokens | 185 |
| Usage accounting | complete |
| Exact output maximum | 65,536 |
| Elapsed time | 9.605751 seconds |

The exact maximum came from an Ollama HTTP 400 capability response. Raw prompt,
output, credentials, and provider error text were not saved.

### OpenRouter

The prior user-supplied OpenRouter key was recovered from a local Codex session
record without printing or writing it. The built-in `models probe` command
refused OpenRouter before making a call, so the existing dynamic zero-price
gateway was used.

One accepted call used `liquid/lfm-2.5-2.6b:free` at zero listed input and
output price.

| Measurement | Observed value |
|---|---:|
| Physical model calls | 1 |
| Input tokens | 38 |
| Output tokens | 63 |
| Usage accounting | complete |
| Exact output maximum | 8,192 |
| Output contract | exact JSON status |

The live test also found a selector defect. Ranking only by the largest maximum
selected a 943,718-token MiniMax route that returned an invalid-request error.
The selector now requires text-only output, can honor an explicit capacity cap,
and prefers native `structured_outputs` before generic `response_format`.
Offline selector tests pass. Later repeated free-tier calls returned rate-limit
errors, which remain visible external availability failures.

### Mistral and OpenCode

Their keys are not present in the current process, active settings, user
service environment, or recoverable user-message records. Mistral and OpenCode
were not called in this run. Prior possession is not current integration proof.

## Real bounded parameter inference

The first real inference attempt refused before a provider call because its
Intelligence Loop did not delegate non-deterministic model work. The authority
contract was corrected and the deterministic suite remained green.

The next provider response contained every required key but returned list
fields as strings and a null rejection reason. Deterministic schema validation
rejected it and the resolver safely abstained. The prompt bundle was corrected
to state exact field types.

The final real call produced:

| Measurement | Observed value |
|---|---:|
| Provider | Ollama Cloud |
| Model | `deepseek-v4-flash:0731` |
| Physical model calls | 1 |
| Input tokens | 234 |
| Output tokens | 184 |
| Usage accounting | complete |
| Proposal confidence | 0.9 |
| Evidence references | 2 |
| Assumptions | 1 |
| Unknowns | 1 |
| Alternatives | 1 |
| Deterministic disposition | resolved |
| Selected value | `stable` |
| Source precedence | 9, Intelligence proposal |

The exact prompt bundle, slot schema, context, render, output, and resolved
value digests were recorded. The model could choose only `stable` or `fast`.
It could abstain. It could not create a third value or override an explicit
caller value.

## Graphify

See [Graphify as an optional Code Intelligence producer](../research/GRAPHIFY-CODE-INTELLIGENCE-EVALUATION.md).
The observed Graphify results support optional structural evidence ingestion,
not a runtime or authority replacement.

## Limits

- The whole-repository audit is a triage system. Its medium findings require
  semantic review and are not all defects.
- Finding precision has planted canaries but no independent human sample label
  set yet.
- Mistral and OpenCode are not current live proofs.
- The Graphify evaluation is one repository and one version.
- Real provider probes establish connectivity and contract behavior, not model
  quality for the full product solve path.
- The full source suite, conformance, package build, and clean-install suite
  must be rerun after all documentation and source edits.
