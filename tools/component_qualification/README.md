# Qualification and sampled review of generated components

Kind: tool component. It serves the owner's goal of September 27, 2026: one
million harness component files within days, with a library that is not
overweighted with skills. The command is
[`tools/qualify_generated_components.py`](../qualify_generated_components.py).

The supply lines (`tools/supply_lines`, builder e) write generated packages
into the import store's `library.supply` namespace: protocol server
configurations, API operation functions with tests, program install recipes
with wrappers, and reference data tables. Reviewing each of them with one
model call per twelve packages would take the reviewer about five days for
100,000 components. This component admits them by two independent layers
instead: a deterministic, test-based qualification of every component, and a
model review of a random sample of each generator batch.

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

A qualification run is a Starting Practitioner task of the code execution
profile that an operator or the scheduled job starts; it runs
deterministically. A sampled review run is a hybrid Practitioner task:
sampling and the decision rule are deterministic, and the verdicts come from
one model family through the existing review panel, its ledger and its
ceilings. The checks, the sandbox and the panel are adapters these runs use;
none is a graph vertex, a role, a mode or a runtime type, and none grants
authority.

## The route

```text
Generated component admission
├── 1. qualification (separate process from every generator, no model call)
│   ├── self-test first: every check passes two known-good fixtures and refuses
│   │   each of its known-wrong controls; one failure stops the run
│   ├── per component, in parallel workers
│   │   ├── manifest: record type, authoring, line, kind and form, identity bound
│   │   │   to the package digest, file list, required files
│   │   ├── licence_provenance: accepted licence expression, licence texts,
│   │   │   attribution naming every file digest, generator version and commit,
│   │   │   pinned fact sources, pinned launcher packages and downloads
│   │   ├── parse and schema: Python, strict JSON, TOML, CSV, JSON Schema,
│   │   │   harness configuration shapes
│   │   ├── effects: declared effects cover the syntax tree of the code and the
│   │   │   instruction and configuration files
│   │   ├── safety and secrets: the licensed import's scan engines, the review
│   │   │   panel's static rules, minified code, test report tampering, the
│   │   │   repository's secret patterns
│   │   └── sandbox: every module imports and the package's own tests pass,
│   │       in bubblewrap with no network, hidden home and runtime folders,
│   │       and CPU, memory, file size, open file and time limits
│   └── population pass: exact copies, same-job packages (a job key per line,
│       declared in the policy data) and near copies
├── 2. sampled review (one model family that did not write the generators)
│   ├── plan per generator batch: sample size and acceptance number from the
│   │   batch size and the generator's observed defect rate
│   ├── calibration: the frozen native controls, one at a time and in a mixed
│   │   batch of twelve; a reviewer that approves one reviews nothing admissible
│   ├── batch calls through the unchanged panel, native criteria and native
│   │   reviewer instructions, with a planted known-wrong control in each call
│   └── decision per batch by the written rule
└── 3. admission folder for accepted batches, in the format the combine and
    bundle tools read; rejected samples are recorded and never bundled
```

## The acceptance rule

The plan is a lot tolerance percent defective plan in the style of Dodge and
Romig. With the default policy (`generated_batch_sampling_policy/v1`):

- A batch whose true defect rate is 5 percent or more is accepted with
  probability at most 5 percent. This probability is computed exactly from
  the hypergeometric distribution for the batch size.
- A generator with at least 50 sampled components of history has its
  acceptance number chosen so that a batch at its observed defect rate is
  withheld with probability at most 10 percent (binomial). Without that
  history the plan accepts zero defects, the smallest sample that meets the
  first bound: 59 components for a batch of 5,592.
- A generator whose observed rate is at or above the tolerance cannot be
  sampled into acceptance.
- A batch is accepted when the reviewer passed its calibration, rejected
  every planted control, and the sample holds no more defective components
  than the acceptance number; a sampled component without a valid verdict
  counts as defective. Otherwise the whole batch is withheld and the generator
  flagged. A rejected sampled component is never published, even in an
  accepted batch. Identities of a withheld batch are not sampled again; a
  repaired generator produces new bytes and a new batch.

## Records

| Record | Purpose |
|---|---|
| `component_qualification_policy/v1` | Vocabularies, thresholds, job keys and their measured reasons (`resources/qualification-policy.json`). |
| `component_qualification_self_test/v1` | The known-good and known-wrong results that allowed a run. |
| `component_qualification/v1` | One component: every check's result, the vetting dimensions and the qualifier revision. |
| `component_qualification_run/v1` | Counts by batch, refusal reasons, timings and throughput. |
| `component_sandbox_run/v1` | One sandbox run: engine, limits, interpreter, imports and test counts. |
| `generated_batch_sampling_policy/v1`, `generated_batch_sampling_plan/v1`, `generated_batch_sampling_decision/v1` | The rule, the plan with its operating characteristic, and the decision. |
| `generated_batch_sampled_review/v1` | The seed, samples, planted controls, calibration, verdicts, decisions and admissibility of one review run. |
| `generated_component_admission_report/v1` | What an admission folder holds, by line, form and harness kind. |
| `generated_admission_composition/v1` | Counts by component family against the composition targets. |

The vetting dimensions stay separate: `source_identity_checked`,
`implementation_tested`, `compatibility_tested`,
`publication_safety_checked` and `publication_approved`. Qualification never
sets the last one; only an accepted batch decision does, for the community
scope.

## Commands

```bash
PYTHONPATH=src:tools python tools/qualify_generated_components.py self-test \
  --output SELF-TEST.json --work-root WORK
PYTHONPATH=src:tools python tools/qualify_generated_components.py qualify \
  --store-root /home/username/baltor-library/import-store --output-folder RUN \
  --work-root WORK --workers 10 --known-bundle BUNDLE --exclude-identities DECIDED
PYTHONPATH=src:tools python tools/qualify_generated_components.py sample-review \
  --qualification RUN --store-root STORE --ledger LEDGER --output REVIEW.json \
  --history HISTORY --calibrate --authorize-model-calls --call-ceiling 120
PYTHONPATH=src:tools python tools/qualify_generated_components.py admit \
  --qualification RUN --review REVIEW.json --store-root STORE --output FOLDER \
  --recorded-at DATE
PYTHONPATH=src:tools python tools/qualify_generated_components.py composition \
  --bundle BUNDLE --admitted FOLDER
```

Without `--authorize-model-calls` the review sends nothing and decides
nothing. `--measurement-only REASON` asks an uncalibrated reviewer for
measurement; every decision it records is withheld, and `admit` refuses it.

## Checks

```bash
PYTHONPATH=src:tools python -m unittest tools.test_component_qualification \
  tools.test_component_qualification_sampling
```

## Existing work: adopted, adapted and rejected

| Project | Decision and reason |
|---|---|
| Library ingestion `sandbox_argv` (bubblewrap, no network) | Adapted: the same engine with home, runtime and removable folders hidden, the package mounted at a neutral path, and resource limits. |
| Licensed import `StaticChecks`, `package_effects` | Adopted for safety scanning and for instruction and configuration effects; not for README or schema words, which describe a remote API. |
| Review panel prechecks: safety rules, secret patterns | Adopted unchanged. |
| Review panel, native criteria and instructions, ledger | Adopted unchanged for the sampled review; the pre-check edge is served by the qualification record. |
| `tools/global_component_duplicates.py` prefix filtering | Adopted for near copies with exact Jaccard confirmation. |
| ANSI/ASQ Z1.4 and ISO 2859 switching tables | Rejected as tables: they index by lot size classes and inspection levels. The exact hypergeometric and binomial computation gives the same guarantees for any batch size and states them directly. |
| Dodge and Romig LTPD plans | Adopted as the method: consumer's risk at the tolerance defect rate, producer's risk at the process average. |

## Limits

- Protocol server packages are configuration only: their implementation is
  validated as harness formats and pinned packages, not started.
- The sandbox runs the system interpreter; other interpreters and platforms
  are not tested.
- The sandbox bounds what a test can do; static rules refuse test code that
  exits early or replaces the test report, but a test written to deceive can
  still pass. The sampled review and publish-then-feedback withdrawal are the
  later layers.
- The sampled review measures defects the reviewer can see. On September 28,
  2026 the Tactical reviewer failed the native calibration (it approved three
  of four known-wrong controls), so its verdicts from that day admit nothing.
