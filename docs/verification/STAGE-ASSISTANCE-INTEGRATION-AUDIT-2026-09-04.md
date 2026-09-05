# Stage assistance integration audit, 2026-09-04

Status: initial stop-ship defects repaired in offline product plumbing.
Canonical paired outcomes, live quality, causal benefit, and command-line or
live-provider configuration remain unproven.

Later update: programmatic public-solve integration, hydrated prompt material,
provider-request digests, exact selection, execution, and verification
occurrence references, and a pre-run control manifest now have offline
injected-provider evidence. The manifest classifies that fixture as
mechanism-only, not as a valid causal pair. The original findings below remain
the historical audit. See the
[current verification report](PREDICTIVE-STATE-PROCEDURAL-MEMORY-AND-STAGE-ASSISTANCE-2026-09-04.md)
for the new results and remaining limits.

This report records a focused review of the dirty checkout at repository
revision `22ee44052b027ba96ce50c37e4cc6a659e1b91c8`. It is not architecture
authority and does not assign ownership to any dirty file.

## What the current evidence supports

```text
Stage assistance evidence
├── Supported by offline checks
│   ├── exact Loop activation occurrence is separate from similarity signatures
│   ├── advisory and fresh assignments use independent activation identity
│   ├── candidate compatibility and prior-not-proof fields are explicit
│   ├── stage outcome dimensions remain separate
│   └── SQLite/WAL projection is rebuildable and non-authoritative
├── Supported by runtime correlation fixtures
│   ├── one logical semantic call can contain several physical attempts
│   ├── every physical attempt keeps its own Loop ID
│   ├── semantic call and owner IDs survive into Run History
│   ├── advisory material reaches an injected product-path prompt
│   └── a valid exact use decision is required before downstream work
└── Not supported
    ├── canonical per-stage paired product outcomes
    ├── complete stage contribution attribution
    ├── command-line or live-provider stage-assistance configuration
    └── evidence that assistance improves quality, cost, or latency
```

Initial focused offline results before the remediation below:

- stage assistance contracts: 31 of 31 passed;
- model gateway: 18 of 18 passed;
- Solution model port: 8 of 8 passed;
- model-call Loop boundary: 9 of 9 passed.

A retained adaptive fixture produced seven distinct logical semantic-call IDs,
seven physical model-attempt Loop IDs, and no missing owner IDs. Its 497-event
Run History has an intact digest chain with head
`c6e7481e2d4f7cfc3cee0d10c4e4b901e7fbb8d37e5a76baa27660544c0d432c`.
The fixture used injected responses and made no provider call. Its private
local run ID is
`adaptive-89b5add069653a3fa0778bca` under
`artifacts/verification/semantic_call_correlation_runs_20260904`.

The same fixture wrote seven `stage_observation/v1` rows and labeled all seven
`helped=true`. That uniform pass-wide label is not valid stage-contribution
evidence. The local run tree is owner-only and Git-ignored because it contains
full fixture artifacts and the unsafe learning projection.

## Findings that prompted remediation

The first audit found the following product-path defects even though the
aggregate suite was green at the time.

1. Pass-wide grading applies one verdict to every observed stage in a pass.
   One successful action can therefore label unrelated, redundant, or harmful
   stages as helpful. A repair verdict can similarly label unrelated stages as
   harmful.
2. Output admission is treated as evidence that a stage helped. Schema-valid
   output is not semantic correctness or downstream contribution.
3. The lossy `helped` Boolean can feed the model ladder even when stage-level
   attribution is unavailable.
4. Stage observations are replaced immutably. A caller retaining an older
   object can later overwrite a newer close or update.
5. The existing control arm is bookkeeping, not a fresh control. It can still
   receive the same templates or prior material, and one semantic digest can
   overwrite several independent occurrences.
6. Some stage records have an empty model route and missing call, latency, or
   token values because the observation path reads a request field that does
   not exist.
7. Instrumentation exceptions can still be suppressed, making unavailable
   evidence look like zero evidence.
8. Product Run History does not yet contain the complete occurrence, exposure,
   model decision, action, observation, local evaluation, and later
   contribution chain.

Do not use rows produced by the pre-remediation pass-wide Boolean as a training
target, route promotion signal, template qualification signal, or
assisted-versus-fresh result.

## Post-audit remediation

The current dirty checkout repairs the listed defects at the offline product
plumbing level:

- Active advisory and fresh responses need a schema-admitted assistance
  decision before downstream use. Missing or malformed decisions enter bounded
  format repair and then fail closed.
- An exposure event is recorded only after a physical model-attempt Loop
  exists. The decision binds the exact exposure, work packet, prompt assembly,
  and physical attempt IDs.
- Canonical paired records require different Loop activations and the same
  source revision. Retrieval candidates must match the source semantic
  signature. Projection rejects retrieval evidence that occurs before its
  source evidence.
- Frozen request mappings are copied and rechecked at execution. Local source
  replacement changes the frozen source facts. Complete cryptographic freezing
  of directories and remote sources remains unimplemented.
- Session budgets count physical attempts, including failover. Token usage is
  aggregated across attempts, partial usage remains unknown, cumulative limits
  are enforced, and a preflight refusal is not a physical call.
- Versioned `model_usage/v2` records preserve positive, missing, partial, and
  real-zero provider usage through Run History, analytics, quality reports, and
  playback. Mixed known and missing calls produce an unknown aggregate.
- Contradicted stage evidence yields `UNKNOWN`. Locally verified but unused
  work yields `NEUTRAL`.
- The stage JSONL v2 reader validates exact types and record identity, preserves
  contradictions, and keeps a separate explicit v1 migration path.
- Storage, projection, temporal validation, runtime binding, and accounting
  helpers were split into passive modules so first-party source files remain at
  or below the 800-line conformance cap.

At the intermediate remediation snapshot, offline evidence was 250 of 250
focused assertions passed. It included
37 of 37 stage-assistance contract checks, 22 of 22 injected product-plumbing
fixture checks, and 6 of 6 model-accounting checks. The fixture contains one
calibration run, two independent request arms from one frozen task state, 21
logical calls overall, and 14 calls in the comparison. All 21 stage rows keep
local contribution unknown. It uses injected responses and makes no live
provider call. The current verification report supersedes these counts and
records one locally checked action stage per arm.

A separate token-propagation regression set passes 183 of 183 focused
assertions across the model Loop boundary, Run History, gateway accounting,
stage plumbing, analytics, quality, and playback. These checks overlap the
component counts above and are not added to them as an independent denominator.

This is product-path plumbing evidence. The request-wide trial label is not a
canonical per-stage paired trial, equal fixture outcomes do not measure an
assistance effect, and monetary values still lack a price and currency
authority. Some in-memory degradation collections are also absent from the
returned adaptive result, although ledger diagnostics remain visible.

## Safe integration order

```text
semantic call and physical-attempt correlation
→ exact activation occurrence
→ retrieval candidate packet
→ exposure record
→ model USE, MODIFY, COMBINE, IGNORE, RETRIEVE_DEEPER,
  START_FRESH, or SPAWN_CHALLENGER decision
→ action and local observation
→ local mechanical and semantic verification
→ downstream consumption
→ later branch and task contribution
→ paired comparison from one controlled stage state
```

The path through exact action selection, execution, and same-Practitioner
local verification now has offline injected-provider evidence. Canonical
projection records, independent evaluation, delayed contribution, and a valid
paired comparison remain unproven.

## Required adversarial cases

A product integration test must include at least:

- a successful run with one useless stage;
- a failed run with one locally correct reusable stage;
- admitted but semantically wrong output;
- a later-invalidated stage;
- two occurrences of the same semantic region assigned to different arms;
- a fresh arm whose prompt, context, templates, and retrieval are proven clean;
- a provider retry that keeps one semantic-call ID and several attempt IDs;
- a storage failure that emits degradation evidence instead of returning a
  silent zero.

The current truthful maturity is fail-closed offline advisory and fresh
product-path plumbing, plus model-call correlation. Canonical per-stage control
applications and outcomes, complete stage attribution, live-provider
execution, live-model quality, and causal benefit remain unproven.
