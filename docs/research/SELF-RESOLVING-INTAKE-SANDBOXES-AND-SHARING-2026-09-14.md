# Self-resolving intake, sandboxes, and information sharing

This September 14, 2026 research synthesis answers three questions from the
owner. How can Loop Engine understand any folder it is handed, the way a
coworker would, and resolve gaps such as a ZIP archive it cannot open? Does
the engine need a main working sandbox and separate sandboxes for each Loop?
How should Loops share information?

This document is research and design. It does not describe implemented
behavior. Measured facts come from offline probes of committed revision
`e089f60`; external numbers come from other systems, tasks, and evaluators
and do not transfer to Loop Engine without its own experiments.

## The current path in one tree

```text
Task folder handed to a solve
└── Source admission inventory
    ├── Admitted: regular, non-hidden files that decode as UTF-8 text
    │   ├── Model prompt: bounded samples, selected bodies
    │   └── Sandboxed generated code: whole-file copies into inputs/
    └── Excluded: ZIP archives, images, spreadsheets, Parquet, other binary
        └── Reported to the model as an unknown path with no reason
Spawned Practitioner Loop
└── source_kind "text", no source references, returns a JSON summary only
External harness process (OpenCode, Codex, Pi)
└── task text and a fresh empty work folder; no task file is mounted
Independent verifier
└── frozen copy of the attempt, read-only, same model family
```

## Measured facts

| Fact | Evidence |
|---|---|
| A ZIP archive, spreadsheet, and PNG image are excluded as `binary_or_unsupported_encoding`; CSV and ARFF text are admitted. | Probe of `inventory_source_files`; `adaptive_practitioner_source.py:332-354` |
| A request for the excluded `data.zip` returned "unknown paths" with an empty exclusion list. Commit `89553f2` later made the refusal name the matching exclusion and its reason. | Probe output; `adaptive_practitioner_source.py:441-452` |
| Only admitted text files can be selected and copied into the sandbox, although sandbox inputs already accept bytes. | `adaptive_practitioner_project.py:354`; `generated_project.py:540-557` |
| No archive, extraction, or binary-access capability exists. | The Practitioner's ten capabilities |
| Selected inputs are copied whole into memory; the ceiling on this machine measured 9.4 GB. | `supplied_input_ceiling()` |
| 105 of 111 admitted Kaggle competitions keep their data only in ZIP archives; 17 are image, audio, or video; five are 10 GB or larger. | ZIP central-directory census |
| In all 31 sampled OpenML tasks, the delivered dataset contains labels for the held-out rows. | ARFF and split-file probe |
| A spawned run wrote ML-001's audit, but its owner ended with zero artifacts. | `adaptive_practitioner_scope.py:96`, `:172`; ML-001 records |
| A September 10 proposal already required extraction when referenced files are missing and archives are present. It was never implemented on the canonical path. | `docs/architecture/HARNESS-AS-LOOP-NODE-CONSTITUTION.md`, section 11 |

The engine cannot reason its way around these limits. The model can write
extraction code in one line, but the archive never reaches the sandbox where
that code would run. Two correct rules leave a hole between them: only text
may enter a prompt, and only prompt-admissible files may reach code.

## Design principle

The runtime states facts it holds exactly. The model interprets. Sandboxed code
acts. Independent checks accept. Applied to material intake:

1. Separate two permissions: what may enter a model prompt, which stays
   text-only and bounded, and what may reach sandboxed code, which is any
   regular file, read-only and bound to its digest.
2. Record facts about every entry: path, kind, size, SHA-256, strict UTF-8
   result, bounded header bytes, and the output of named detectors and parsers
   with their versions.
3. Leave interpretation to model calls whose claims cite those facts: which
   file holds what, what a column means, whether to extract, stream, sample,
   or convert.
4. Withhold content only with a typed refusal that names the reason.

This follows the owner's rule against hardcoded solution paths. It adds no
filename pattern and no helper that assumes a file layout.

## Option set 1: material intake

| Layer | Options | Runtime owns | Model owns |
|---|---|---|---|
| 1. Inventory facts | Listing, digests, magic-byte detectors (libmagic, Google Magika, Siegfried), archive central directories, table schemas and bounded samples | Facts with the procedure that produced them; probe depth as a configuration with fallbacks | Requests for deeper probes on specific entries |
| 2. Model-directed exploration | Generated code over mounted material; bounded list, window, and search operations that report truncation; a reader call with no tools | Sandbox, bounded output, accounting, checking claims against facts | Code, steps, interpretations |
| 3. Converters | MarkItDown, Docling, unstructured, Marker, MinerU, pandoc, and Tika as Custom Plugins adapters | Qualification, pinned versions, eligibility by detected type | Whether to convert and whether the result is good enough |
| 4. Limits and typed refusals | Path escape, links and special files, overlapping ZIP entries, compression ratio, nesting depth, encryption, incomplete volume sets, unsafe deserialization such as pickle, external references such as HDF5 links, hidden Unicode | Limits from measured capacity or declared authority; streaming byte counters | Requests for a changed effect, with a reason |
| 5. Files too large to copy | Read-only bind mounts, one extraction per task shared read-only, streaming archive members, lazy scans, sampling | Transport, quotas, digests before and after | What to read, extract, or sample |

Safety notes from the sources:

- Python's `tarfile` data filter refuses path escapes but not decompression
  bombs, and CVE-2025-4517 bypassed it. `zipfile` rejects overlapping entries
  after CVE-2024-0450.
- MarkItDown reads ZIP members into memory without size, count, or ratio
  limits, and its README warns against untrusted input.
- DuckDB's documentation says to treat SQL like code; its external access can
  be restricted with `enable_external_access` and `allowed_directories`.
- SQLite files need `trusted_schema=OFF`; pickle-based formats execute code
  when loaded.

Benchmarks usually do intake for the agent. MLE-bench's preparation scripts
unpack archives before an agent starts. Where agents do their own intake,
failures are about identifying data: DSBench names "Inadequate Data
Identification" and "Misinterpretation of Data", and DA-Code reports agents
assuming file names without exploring.

## Option set 2: sandbox topology

| Topology | Description | Gains | Costs |
|---|---|---|---|
| A | One writable task workspace shared by every Loop | No copies; outputs visible immediately | Overwrites and races; untrusted code can change materials; no record of which output was used |
| B | Per-Loop sandbox with copy-in and copy-out (current) | Strong isolation | Copies grow with input size and attempts; the 9.4 GB memory ceiling; unsafe copy-out paths |
| C | Frozen, content-addressed read-only materials; a disposable sandbox per Loop; outputs promoted as typed digest references | Each archive stored once; spawned Loops return references; the verifier mounts the same inputs | More moving parts; large objects need a streaming store |
| D | Snapshot and branch from a prepared state | Cheap alternative attempts | Repeated random state after memory restores; contamination spreads to branches |
| E | Remote sandbox service | Isolation, scale, snapshots | Disk limits, transfer time, spending, data privacy |

Products that run parallel attempts or spawned agents give each one a private
workspace: Codex cloud attempts, Devin's spawned sessions, Cursor cloud subagents,
and Claude Code subagents in worktrees. Claude Code agent teams share one tree,
and their documentation warns that teammates overwrite each other's files.
MLE-bench mounts prepared data read-only and copies submissions out.

**Answer to the owner's question.** Yes to a sandbox per Loop, and yes to a
task-level main area, but the main area should not be a shared writable
folder. It should hold a frozen, read-only store of task materials addressed by
content hash and an append-only store of typed output references.

Recommended default: topology C on the existing local Docker backend.

1. Admission records facts about every file instead of dropping binaries.
   Inline task text becomes material files. Unsafe entries are reported and
   never mounted.
2. The materials are frozen with a digest manifest, checked before each Loop
   runs and again at verification.
3. Each running Loop gets its own container with no network, a read-only root,
   dropped capabilities, and resource limits. Materials and chosen references
   are mounted read-only; scratch space is on disk, not the memory-backed
   `/tmp` of this host.
4. Capture refuses links, device files, and path escapes, hashes while
   streaming, and records a typed reference.
5. The verifier runs in its own sandbox over the same read-only mounts, with no
   host Python user-site hooks.

Ordered fallbacks: a per-Loop copy-on-write overlay when code must edit
materials; materials packaged as an image; streaming copy-in; branching from
promoted prepared layers; gVisor, Kata, Firecracker, or hosted microVMs through
adapters; topology B for small inputs; topology A only for acknowledged
trusted single-Loop sessions.

Existing boundaries to extend rather than duplicate: `WorkspaceSpec` and
`DockerWorkspaceDeclaration` for read-only mounts and a base layer,
`ContextArtifactStore` for digest-addressed bytes (it needs streaming),
`InformationStorageBinding` scopes for visibility, and the unused
`SpawnedTaskManager` visibility and return policies.

## Option set 3: information sharing between Loops

| Question | Recommended option | Reason from the sources |
|---|---|---|
| Reference, copy, or summary | Pass digest references for files and deliverables; copy only small typed values; check summaries and link them to sources | Copying through conversation loses information; unchecked summaries lowered accuracy in DeLM |
| Visibility | `private_loop` for scratch, `allowed_loops` for a spawned Loop's outputs, `run_shared` for the task-level board, `project_shared` for staged candidates | Scopes already exist in `information_access.py` |
| Provenance | W3C PROV relations recorded in Run History: `used`, `wasGeneratedBy`, `wasDerivedFrom` | No new store; evidence attaches to identity |
| Delegated work | An explicit final state for every spawned assignment, with output references | Agent2Agent tasks and durable handles require terminal states |
| Failure history | Fingerprint failures by class, normalized signature, capability version, and input digests; show the latest raw failure and a count | CS-001 pro carried 57 failure entries, 15 distinct |
| Prompt size | Stable prompt prefix, details loaded on demand, filtering in code | Clearing old tool results cut tokens by 84 percent over 100 turns in one report |

A spawned Loop's outputs should return as follows. The spawn request names
input digests, the output contract, and authority. The spawned Loop writes only to
its own scratch and outputs. At publication and exit, the runtime captures,
hashes, and stores each output and records the producer, digest, media type,
input digests, and candidate status. The spawned Loop's result carries references,
never bytes. The owner records the exact digests it consumes. Publication,
completion, verification, acceptance, and promotion stay separate events.

## Option set 4: resolving capability gaps

| Stage | Options | Who may do it |
|---|---|---|
| Detect | Runtime facts at each exclusion or resolver miss; the resolver's existing `escalate_to_novel_build` outcome offered to the model | The owning Loop |
| Classify and probe | Missing operation, missing material or authority, retrieval miss, reasoning error, tool failure; a cheap sandbox probe | The owning Loop, recorded as evidence |
| Build | A task-local script; a typed candidate with contract digests and pinned dependencies; an adapter around a qualified library | The owning Loop in the sandbox; installs need a typed grant |
| Check within the task | Comparison with a reference such as Python `zipfile`, property tests | The owning Loop; the deliverable is still independently evaluated |
| Stage | Existing `CandidateJournal`, `CodeAssetSpec`, and reuse-opportunity records with the gap facts | The owning Loop |
| Qualify | Hidden tests written by another Loop, held-out tasks, planted-fault checks, security checks | An independent reviewer |
| Promote, reuse, measure, retire | Existing `promote_as_loop`; exact-match reuse; ablation reruns; quarantine of anything derived from a poisoned tool | An independent reviewer enacts; Loops collect data |

The strongest external finding: capability a system builds for itself helps
only when the check is independent of the builder. In one study, 96.8 percent
of 222 preserved generated tools passed their builder's own checks and scored
zero on held-out conformance tests. In SkillsBench, self-written skills scored
below using no skills. Building a tool for one task still helps even when
nothing is kept (Live-SWE-agent, 76.0 against 62.0 percent). Models alone
distinguish a missing operation from a reasoning error poorly, which is why
runtime facts at each exclusion matter.

## Recommended sequence

Each step is small, keeps existing behavior available as an option, and has a
discriminating experiment.

1. **Name every exclusion.** Record facts for every entry and report the
   typed reason when a requested path is excluded. Experiment: a detector and
   archive census across the 1,605 admitted tasks with no model calls.
2. **Sandbox-only admission.** Let the model select binary files for sandboxed
   code without sending their bytes to a prompt. Experiment: the 105 ZIP-only
   competitions with the current admission against sandbox-only admission,
   model and evaluator fixed.
3. **Read-only mounts above a size policy.** Experiment: inputs from 1 MB to
   22 GB with 1, 4, and 16 attempts; copies should fail near the memory
   ceiling while mounts stay flat.
4. **Spawned outputs as digest references with owner adoption.** Experiment:
   the share of verified spawned-Loop outputs whose exact digest appears in the final
   output, before and after.
5. **Task-level materials layer, per-Loop scratch, and a separate verifier
   sandbox.** Experiment: integrity canaries that write to materials, escape
   through links, and plant `sitecustomize.py`.
6. **Capability-gap records with independent qualification.** Experiment:
   builder tests against hidden tests and reference comparison, counting bad
   tools wrongly accepted.
7. **Task-owned evaluators.** Seal OpenML held-out labels and score
   predictions with each task's declared metric; carve sealed holdouts for
   Kaggle tabular tasks. Experiment: self-verified against evaluator-verified
   acceptance on the same cells.

## Limits

This synthesis combines documentation research, offline probes, and code
reading. No intake, sandbox, sharing, or capability-gap design here was built
or run live. Published numbers come from other systems and evaluators. Full
notes and dated source lists are kept outside the published tree in the
review's research folders.
