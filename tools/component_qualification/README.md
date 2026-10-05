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
│   │   │   pinned fact sources, pinned launcher packages and downloads, and
│   │   │   upstream notice files (Apache-2.0 section 4(d)) that are verbatim
│   │   │   upstream copies, which the duplicate pass leaves out like licence texts
│   │   ├── parse and schema: Python, strict JSON, TOML, CSV, JSON Schema,
│   │   │   harness configuration shapes
│   │   ├── effects: declared effects cover the syntax tree of the code and the
│   │   │   instruction and configuration files
│   │   ├── safety and secrets: the licensed import's scan engines, the review
│   │   │   panel's static rules, minified code, test report tampering, the
│   │   │   repository's secret patterns
│   │   └── optional sandbox: every module imports and the package's own tests pass,
│   │       in bubblewrap with no network, hidden home and runtime folders,
│   │       and CPU, memory, file size, open file and time limits
│   └── population pass: exact copies, same-job packages (a job key per line,
│       declared in the policy data) and near copies
├── 2. sampled review (one model family that did not write the generators)
│   ├── decision ledger, read first: a run that may call a model refuses
│   │   without it, and a batch whose frame it already decided is refused
│   ├── plan per generator batch: sample size and acceptance number from the
│   │   batch size and the generator's defect rate recorded in the ledger
│   ├── calibration: the frozen native controls, one at a time and in a mixed
│   │   batch of twelve; a reviewer that approves one reviews nothing admissible
│   ├── batch calls through the unchanged panel, native criteria and native
│   │   reviewer instructions, with a planted known-wrong control in each call
│   ├── each call planned within the reviewer's declared window less its output
│   │   allocation, at 1.35 reported tokens per estimated token; a run that may
│   │   call a model refuses before its first call when a planned call cannot fit
│   └── decision per batch by the written rule, appended to the decision ledger
└── 3. admission folder for accepted batches, in the format the combine and
    bundle tools read, only for decisions the decision ledger records;
    rejected samples are recorded and never bundled
```

The default fast route runs static checks and population deduplication.
`--checks all` additionally requests sandbox and mutation checks. A fast
record cannot stand in for these extra checks on a later full run. Sampled
review reads package bytes; it does not execute the package. Omitted execution
is recorded as not tested, not failed or passed. Community admission and
execution qualification therefore make different claims.
Execution checks run again even when a previous record contains them, because
the current record does not pin every interpreter, dependency and sandbox
image required to validate an execution-cache hit.

Sampled review version 2 binds the complete qualified population by identity,
store version and package digest. Admission also checks sample membership and
each verdict's body digest. Equal batch counts do not establish the same
population. Version 1 review records cannot admit material through this path;
rerun review rather than retroactively attaching a population claim.

## What the reviewer is sent

Each sampled package reaches the reviewer through the native package prompt:
its file tree with every size and digest, the written criteria, the item
declaration and every file in full, with one exception. A text file under a
data folder of the qualification policy (`data/`) that is larger than 16 KiB
is shown as an excerpt by the rule `data_file_excerpt/v1`
([`excerpts.py`](excerpts.py)):

- delimited text (`.csv`, `.tsv`): the header record, then the first 20 and
  the last 20 data records, each as the file's own lines;
- JSON: an array's first 20 and last 20 elements, or an object's first 20
  and last 20 members in file order, each as compact JSON on a line of its
  own;
- any other text: the first 20 and the last 20 lines;
- a shown record, element or line longer than 400 characters is cut there
  and says how many characters it leaves out, so an excerpt holds at most
  19,120 characters whatever the file's size.

The prompt labels the file `EXCERPT, NOT THE WHOLE FILE`, names the rule and
states the file's media type, size and SHA-256, its row count, its field
inventory (the header's columns, or every JSON field with each type it
takes), which rows are shown and how many are not. The request still carries
every byte, so the package binding and every digest are unchanged.
Qualification parsed the whole file and ran its safety rules and secret
patterns over it, and the supply line ran the package's own tests, which
check every row against its `schema.json`, before it stored the package. The
reviewer does not see the rows left out. Of the 1,870 data files of the
September 28 and October 1, 2026 data table runs, 578 are excerpted and
1,127 are sent whole; the longest excerpt is 18,535 characters.

Calls are filled within the reviewer's context window. A call's allowance is
the window less the answer allowance, divided by 1.35, the largest ratio of
provider-reported to estimated input tokens seen, so a call fits the
provider's own count as well as the gateway's estimate. The room for a call's
sampled members and planted controls is that allowance less the batch
instructions and the batch prompt's own words (200 tokens, and 100 for each of
up to twelve members). Members leave 20,000 tokens for each planted control,
and a control is planted only where it fits the call's leftover room;
otherwise another member is tried. Before any model call the run builds every
planned call exactly as the panel will and refuses when one is over the
allowance, does not fit the window with its answer allowance, or holds fewer
planted controls than asked, because the model gateway refuses a call over
the window before it reaches the provider. For `ollama.kimi-k2.6` the
allowance is 91,022 estimated tokens of its 131,072-token window and the room
88,909. The fixed 150,000-token budget that planned the September 30, 2026
data table calls exceeded the window, and the gateway refused all three calls
unanswered. A reviewer that declares no window keeps the fixed budget.

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
  sampled into acceptance: its next batch is planned for review of every
  component, and the written rule withholds it whatever that review finds.
- A batch is accepted when the reviewer passed its calibration, rejected
  every planted control, and the sample holds no more defective components
  than the acceptance number; a sampled component without a valid verdict
  counts as defective. Otherwise the whole batch is withheld and the generator
  flagged. A rejected sampled component is never published, even in an
  accepted batch. A decided frame is never sampled again (see the decision
  ledger below); a repaired generator produces new bytes and a new batch.

## The decision ledger

The guarantee above holds for one sampled review of one population. Until
October 5, 2026 the earlier decisions were an optional file (`--history`),
read per batch string, and the batch string includes the code revision of
the supply run. A batch withheld after a sampled review could therefore be
sampled again with a fresh seed and planned as if its generator had no
record. On September 30, 2026 the review withheld
`function_extracts/1.1.0@8ebc4a99e5a6` with 21 of 58 sampled components
defective; a rerun without the file planned 58 components with acceptance
number 0 instead of the review of every component that rate requires. Each
new sample is another chance, so a batch near the tolerance would eventually
pass.

One decision ledger ([`decisions.py`](decisions.py)) now holds every complete
batch decision:

- `sample-review --authorize-model-calls` refuses before any model call, and
  before it reads the qualification run, when `--decisions` is not given or
  names a file that does not read exactly: missing, empty, not a ledger, a
  torn last line, an unknown record or field, a broken chain, or withheld
  members that do not hash to their frame's digest. A run without model
  calls reads the ledger when it is given one.
- A batch whose exact frame the ledger already decided, accepted or withheld,
  is refused, and so is a batch that holds a component of a withheld frame,
  matched by identity or by package digest. A decided frame proceeds only
  through a full review of every component or after its generator changes so
  that the frame differs. This route has no full-review mode; a full review
  would be a review of each package outside the sampled review.
- Plans read each generator's history from the ledger. The generator is the
  supply line and generator version (`sampling.generator_of`) at any code
  revision, so a recorded rate reaches the next batch an unchanged generator
  writes. A repaired generator declares a new version and starts a new
  history.
- An admissible run appends, in one synced write before it writes its review
  record, each decision on which the reviewer gave a valid verdict (approve
  or reject) on at least one sampled component, in the batch's own calls or
  in the mixed calibration batch, and holds the ledger's exclusive lock from
  its first read. A sampled component without a valid verdict is unknown, not
  defective: the written rule still counts it as defective for its own
  batch's outcome, which only makes that decision stricter, but a batch on
  which every sampled component is unknown (its calls were never made,
  failed, or were refused by the gateway before they reached the model)
  learned nothing about its components. It stays undecided and is listed
  under `unanswered`, and its frame may be sampled again. A measurement or an
  uncalibrated run appends nothing.
- A generator's history counts only complete samples, in which every sampled
  component has a valid verdict (`sampling.GeneratorHistory.from_decisions`),
  and only their rejections as defects. An unknown component therefore never
  enters the defect rate that plans the generator's later batches.
- A run that can decide refuses before its first call when `--call-ceiling`
  does not cover the calibration and every planned call. The planned calls of
  later batches stay reserved, so an earlier batch's retries never leave a
  later batch short of calls.
- `admit --decisions` reads the ledger, never writes it, and refuses before
  it writes anything unless every answered batch decision of the review is
  the ledger's one recorded decision for that exact frame, equal field for
  field and made by this review (same seed, start, reviewer and producer
  family, and for a backfilled entry the same review bytes): a review the
  ledger does not hold, a decision other than the recorded one, a frame the
  ledger holds twice, and an accepted frame that holds a component of a frame
  the ledger withheld are each refused. `reviews.json` names the ledger's
  digest and the entries admission matched. An unanswered decision is
  withheld and admits nothing, so the ledger need not hold it.

Each entry carries its sequence and the SHA-256 of the line before it, the
batch, its generator and outcome, the decision as the written rule returned
it, the plan, the frame and the review run that decided it. The frame is the
digest, size and qualifier revision of the exact population and, for a
withheld batch, every member as identity, store version and package digest.
The members of an accepted frame are not listed: they are admitted, and
qualification given the served bundle (`--known-bundle`) refuses copies of
served packages. A changed, removed or reordered line breaks the chain at the
line after it; the review record of the run that appended the last line keeps
the ledger's digest after that append.

`decisions-backfill` records the decisions of earlier review records. It
rebuilds every frame from the qualification run the review names and checks
it against the digest the review bound before it writes anything. It skips a
review that stopped or was not admissible, never appends a decision twice,
and creates the ledger only when no file exists at its path.

The canonical ledger belongs at
`/home/username/baltor-library/generated-admission/decision-ledger.jsonl`,
beside `decided-identities.txt`, which stays the qualification exclusion list
that `qualify --exclude-identities` reads. The backfill of October 5, 2026 is
[`fixtures/decision-ledger-backfill-2026-10-05.jsonl`](fixtures/decision-ledger-backfill-2026-10-05.jsonl).
It records the 3 answered decisions of the review records of September 29
and 30, 2026:

| Batch | Frame | Outcome | Sample |
|---|---|---|---|
| `program_installs/1.0.0@3e497b809fd8` | 3,910 | accepted | 0 of 58 defective |
| `function_extracts/1.1.0@8ebc4a99e5a6` | 1,767 | withheld | 21 of 58 defective |
| `program_installs/1.0.0@8ebc4a99e5a6` | 189 | withheld | 6 of 48 defective |

The recorded rates of `function_extracts/1.1.0` (21 of 58) and
`program_installs/1.0.0` (6 of 106) are at or above the 5 percent tolerance,
so neither generator version can be sampled into acceptance again; each needs
a repaired generator with a new version. `function_extracts/1.2.0` is that
repair for the function line: the classification of the 21 defects and what
changed are in the
[supply lines README](../supply_lines/README.md#generator-120-of-function_extracts).
The stopped review of September 30, 2026 at 15:26 decided nothing, so its two
batches stay undecided. The September 30 review also withheld
`data_tables/1.1.0@8ebc4a99e5a6` (frame 381) with 0 of 52 sampled tables
decided: the gateway refused all three of its calls for the context window
before they reached the model. With no valid verdict, that decision is not
recorded, `data_tables/1.1.0` has no recorded rate, and its frame may be
sampled again. The 1,675 data tables qualified on October 5, 2026
(`qualification-06c61876-data_tables`: 511 at `872379b1fdb4`, 784 at
`eafa4fe83785` and 380 of the withheld frame at `8ebc4a99e5a6`) all plan the
zero-acceptance sample of 55 or 56.

## Records

| Record | Purpose |
|---|---|
| `component_qualification_policy/v1` | Vocabularies, thresholds, job keys and their measured reasons (`resources/qualification-policy.json`). |
| `component_qualification_self_test/v1` | The known-good and known-wrong results that allowed a run. |
| `component_qualification/v1` | One component: every check's result, the vetting dimensions and the qualifier revision. |
| `component_qualification_run/v1` | Counts by batch, refusal reasons, timings and throughput. |
| `component_sandbox_run/v1` | One sandbox run: engine, limits, interpreter, imports and test counts. |
| `generated_batch_sampling_policy/v1`, `generated_batch_sampling_plan/v1`, `generated_batch_sampling_decision/v1` | The rule, the plan with its operating characteristic, and the decision. |
| `generated_batch_sampled_review/v2` | The seed, exact population digest, samples, planted controls, calibration, verdicts, decisions and admissibility of one review run, and the decision ledger it read and appended to. |
| `generated_batch_decision_ledger/v1`, `generated_batch_decision_entry/v1` | The decision ledger's header, and one complete batch decision with its plan, frame and deciding review, chained by digest. |
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
  --decisions /home/username/baltor-library/generated-admission/decision-ledger.jsonl \
  --calibrate --authorize-model-calls --call-ceiling 120
PYTHONPATH=src:tools python tools/qualify_generated_components.py decisions-backfill \
  --decisions DECISIONS --review REVIEW.json --review REVIEW.json --recorded-at TIME
PYTHONPATH=src:tools python tools/qualify_generated_components.py admit \
  --qualification RUN --review REVIEW.json --store-root STORE --output FOLDER \
  --decisions /home/username/baltor-library/generated-admission/decision-ledger.jsonl \
  --recorded-at DATE
PYTHONPATH=src:tools python tools/qualify_generated_components.py composition \
  --bundle BUNDLE --admitted FOLDER
```

Without `--authorize-model-calls` the review sends nothing and decides
nothing. `--measurement-only REASON` asks an uncalibrated reviewer for
measurement; every decision it records is withheld, `admit` refuses it and
the decision ledger does not record it.

## Checks

```bash
PYTHONPATH=src:tools python -m unittest tools.test_component_qualification \
  tools.test_component_qualification_sampling tools.test_component_qualification_decisions \
  tools.test_component_qualification_excerpts
```

## Existing work: adopted, adapted and rejected

| Project | Decision and reason |
|---|---|
| Library ingestion `sandbox_argv` (bubblewrap, no network) | Adapted: the same engine with home, runtime and removable folders hidden, the package mounted at a neutral path, and resource limits. |
| Licensed import `StaticChecks`, `package_effects` | Adopted for safety scanning and for instruction and configuration effects; not for README or schema words, which describe a remote API. |
| Review panel prechecks: safety rules, secret patterns | Adopted unchanged. |
| Review panel, native criteria and instructions, ledger | Adopted for the sampled review; the pre-check edge is served by the qualification record. The native prompt gained one optional part, a review file's labelled excerpt (`ReviewExcerpt`), which only this route sets, so every other prompt is unchanged. |
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
- An excerpted data file is judged by the reviewer on the rows it shows. A
  defect only in the rows left out is caught by qualification and the
  package's own tests or not at all; qualification does not look for hidden
  or control characters in a data file.
- A `.tsv` data file is declared `application/octet-stream` by its suffix, so
  qualification refuses its package as `binary_file_unverified`: 165 of the
  1,872 data table candidates qualified on October 5, 2026. The excerpt rule
  leaves a declared binary file alone.
- The decision ledger guards the reviews this tool runs. It is a local file:
  a review given a newly created ledger reads no history, so every run must
  name the canonical ledger, and `admit` must be given the same one. A review
  record written by code older than the ledger admits nothing until
  `decisions-backfill` records its decisions.
- Nothing chains the last ledger line to a later one. Its digest is kept only
  in the review record of the run that appended it, or in the backfill's
  report.
- A call's allowance divides the reviewer's declared window, less its output
  allocation, by 1.35, the largest ratio of provider-reported to estimated
  input tokens seen (Kimi K2.6, September 30, 2026: 96,751 estimated, 126,997
  reported). Content that tokenizes more densely could still exceed a
  provider's own window. A sampled package too large for one call with its
  planted control refuses the run before any call; rerun the other batches
  with the same `--seed`. The excerpt rule shortens only large data files, so
  a package whose other files are too large waits for a review that excerpts
  them.
- A run that stops after its first review call and before its append, for
  example when its process is killed, records nothing in the decision ledger.
  The review panel's own ledger keeps that run's calls and verdicts; read it
  before the batch is sampled again.
