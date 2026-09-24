# Idea matrix and four separate OpenCode generation lanes

Status: first working pipeline, September 24, 2026. This artifact records
the deterministic idea matrix and the first live four-lane generation
run. Nothing here is an approved package, a served item, or a customer
benefit claim. The authoritative task state remains
[roadmap S-6.40 and S-6.53](../../docs/roadmap/roadmap.yaml).

## What was built

1. [tools/harness_idea_matrix.py](../../tools/harness_idea_matrix.py):
   a deterministic crossing of the pinned O*NET 31.0 occupation grid
   with 35 datatypes, 36 operations, and 25 use cases, producing
   **29,625 unique method hypotheses** (typed `harness_idea_record/v1`
   candidate records, each with provenance, a real O*NET task statement,
   a discriminating known-wrong case, and a method signature).
   Deduplication is by method signature: job title, seniority, location,
   language, company, harness and model are applicability facets, not
   new methods, per the S-6.40 rule. Impossible pairs (multiplying a
   person name, inverting log lines) are refused.
2. [tools/opencode_generation_lanes.py](../../tools/opencode_generation_lanes.py):
   four fully separate OpenCode setups, each with its own
   `OPENCODE_CONFIG_DIR`, its own `XDG_DATA_HOME`, its own workspace and
   its own `opencode.jsonc` naming exactly one remote provider. Three
   lanes call Ollama Cloud (`gpt-oss:20b`, `gemma4:31b`,
   `glm-5.3-flash`); one lane calls the owner's Tactical Engineering
   endpoint (`gemma-4-coding-abliterated`). A lane that names any local
   endpoint is refused before a process starts. The Tactical key is
   resolved from the system keyring through the recorded
   `tools/operator_credentials.py` path (reference
   `tactical-model-generation`), only inside the process that makes the
   call. The endpoint's Origin certificate is issued for
   `ai.iamretarded.net` while it is served at
   `ai.tacticalengineering.net`, so the lane runs its own subprocess
   with Node hostname TLS verification disabled, the owner-documented
   trust model for this endpoint; the pinned Origin CA and leaf digest
   remain the trust evidence in the capacity-measurement binding.
3. Known-wrong checks:
   [tools/test_harness_idea_matrix.py](../../tools/test_harness_idea_matrix.py)
   (21 checks) and
   [tools/test_opencode_generation_lanes.py](../../tools/test_opencode_generation_lanes.py)
   (14 checks), all passing, no model calls.

## First live run (one idea, four lanes)

Idea `text-standardization-data-cleaning` (the matrix's first record)
was dispatched to all four lanes: 4 model calls total, 4 candidates
written, 0 approvals, 0 served items.

| Lane | Provider | Model | Outcome |
|---|---|---|---|
| lane-ollama-gpt-oss-20b | Ollama Cloud | gpt-oss:20b | candidate_written |
| lane-ollama-gemma4-31b | Ollama Cloud | gemma4:31b | candidate_written |
| lane-ollama-glm-53-flash | Ollama Cloud | glm-5.3-flash | candidate_written |
| lane-tactical-gemma4 | Tactical | gemma-4-coding-abliterated | candidate_written |

- Ledger: [generation-ledger.jsonl](generation-ledger.jsonl) records each
  dispatch before the provider call and each outcome after it.
- Candidates: [candidates/](candidates/), one per lane, each with its
  SHA-256 recorded in the ledger. The three earlier failed attempts of
  this smoke run (empty-response parsing, fenced output, file-writing
  behavior) were repaired in the tool; their failed records were
  overwritten by successor runs, and the defects and repairs are listed
  here so the history is not silent.
- All lanes answered through their declared remote endpoint. No local
  model was installed, started, or called.

## Boundaries

- Every generated candidate is candidate-only. No item was staged,
  admitted, approved, or served. Independent admission is a separate
  process that a producer never runs on its own bytes.
- The 29,625 hypotheses are ideas, not packages. Review yield,
  approval rate, eligible files per package and customer benefit are
  unmeasured. The sensitivity math in the
  [hundred-thousand supply research](../../docs/research/HUNDRED-THOUSAND-HARNESS-INTELLIGENCE-SUPPLY-2026-09-22.md)
  governs how this population may be counted toward any target.
- Scale runs need a declared call ceiling per lane. This run's ceiling
  was one call per lane and it was not exceeded.
- The full 29,625-idea matrix file lives outside the repository
  (approximately 21 MB rendered); regenerate it with
  `python tools/harness_idea_matrix.py --output <path>`.

## Repair and environment notes

- The matrix first read the wrong JSON key for task statements and
  emitted generic references; fixed to read `task_references` with real
  O*NET task text, and a check now requires a real statement on every
  idea.
- Unknown datatypes were silently accepted by the pair filter; they now
  raise a typed refusal, and a check covers it.
- The first lane-run attempts failed on response parsing (opencode
  emits `text` events, not `message`), on models that wrap output in a
  ```markdown fence, and on models that write a file instead of
  replying. All three behaviors are now handled deterministically.
- The shared checkout's virtual environment held `mcp==1.29.1` while
  `pyproject.toml` pins `mcp==2.2.0`; reinstalling the pinned version
  restored the self-test to 2,665 of 2,667. The two remaining
  self-test gate failures and two conformance gate failures come from
  concurrent sessions' uncommitted edits in this shared checkout
  (verified: the same gates pass on a pristine export of HEAD
  `385c6471`).