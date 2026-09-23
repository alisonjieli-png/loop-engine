# Library ingestion runs of September 23, 2026 (package LS1)

Kind: dated evidence. Two real runs of `tools/ingest_outside_material.py`
read outside harness material with provenance and staged it as review-only
candidates in an isolated database. Nothing here is approved, served or
published, and every staged row needs an independent review of its exact
bytes. Candidate counts are internal: a public library number counts
approved, active packages only. Times are UTC.

## What ran

| | Run 1 | Run 2 (the result to use) |
|---|---|---|
| Code | `e6185b3`, no uncommitted change | `0f7ae1f`, no uncommitted change |
| Time | 03:53:11 to 04:37:03 | 04:39:42 to 05:08:32 |
| Sources | 20 curated repositories at pinned commits and the official Model Context Protocol registry, first 3,000 latest entries in the registry's list order | the same |
| Reuse | none | 1,868 files taken from run 1's quarantine after hashing each again against the blob the tree names; none refused |
| Requests | 3,771: GitHub 3,453, HTTPS 318, no pause | 1,903: GitHub 1,585, HTTPS 318, no pause |
| Model calls | 150 of a ceiling of 150, all answered; 45 outlines fell back to the template engine at the ceiling | 187 of a ceiling of 200, all answered |
| Reported usage | every call: 204,465 prompt and 3,960 completion tokens | every call: 260,739 prompt and 4,914 completion tokens |

Both runs had read-only network authority (GitHub through the existing `gh`
login; HTTPS to `registry.modelcontextprotocol.io`, `registry.npmjs.org`,
`pypi.org` and `opencode.ai`) and model authority through Ollama Cloud
(`deepseek-v4-flash:0731`, route `ollama_cloud:/api/chat`) for the outline
engine only, under the owner's direction of September 22, 2026. The key was
read from the environment by the existing client and is in no record.

Run 1 found three things to change, and commit `0f7ae1f` changed them before
run 2: eight Figma skills whose licence binds the reader to Figma's own
terms were outlined, and are now refused; 230 Cursor rule files were
refused because their native frontmatter (`globs: **/*`) is not YAML, and
are now read in Cursor's own format; and a rerun can now reuse verified
pinned bytes. Run 1 is kept beside run 2.

## Counts of run 2

```text
4,790 discovered
├── 741 refused before a candidate existed
│   ├── 502 registry entries whose GitHub repository does not answer
│   ├── 213 registry entries under ai.smithery/, declared copies of other entries
│   ├── 25 registry entries whose status is not active
│   └── 1 file above the size ceiling
└── 4,049 candidates
    ├── by licence evidence: 1,586 verbatim, 2,260 link only, 187 outline only, 16 refused
    ├── 16 refused by licence: 8 licences that forbid derivative works (four
    │   proprietary document skills and their copies inside a collection) and
    │   8 that bind the reader to a provider's own terms
    ├── 187 outline only, and 187 outlines written (149 by the model, 38 by the
    │   template after the model's sentence repeated five source words)
    ├── 589 refused after the licence decision
    │   ├── 511 skills that point at bundled files, folders or modules
    │   ├── 46 registry entries: 10 packages that do not exist at their version,
    │   │   11 templated addresses, 10 without a transport, 7 required arguments
    │   │   without a value, 6 package types not rendered, 2 secret-shaped values
    │   ├── 29 blocked by the safety scan, naming these rules (one item can name
    │   │   two): SkillSpector's recommendation not to install 12, instruction
    │   │   override 6, secret-shaped value 6, remote script piped to a shell 4,
    │   │   destructive command 2, concealment 1
    │   └── 3 bodies below the minimum length
    ├── 0 verbatim copies of a restricted source
    ├── 6 duplicates merged: 1 exact (one registry endpoint under two names)
    │   and 5 near (four pairs of Cursor rules and one pair of Copilot skills)
    └── 3,251 staged: 596 skills, 445 instruction files, 2,210 connection packages
```

Every candidate is counted once:
16 + 187 + 589 + 0 + 1 + 5 + 3,251 = 4,049.

Staging put the 3,251 rows into an isolated catalogue database in 66
atomic populations of at most fifty. Normal search returned none of them,
and 3,221 title probes found their own row among the first three results.
Staging the same run folder again changed nothing: all 66 populations were
already staged. Run 1 staged 3,025 rows in 61 populations the same way.

## Files

| File | What it holds |
|---|---|
| `run-report-1.json`, `run-report-2.json` | `library_ingestion_run_report/v1` of each run: code identity, each source's outcome, every count, requests, engines and model calls. |
| `sources-1.json`, `sources-2.json` | Each source with the repository licence the run verified at the pinned commit, its licence decisions, its refusals by reason and the rows kept from it. |
| `engine-decisions-1.json`, `engine-decisions-2.json` | The `library_engine_selection/v1` decision of each engine slot, made before any engine ran. |
| `duplicates-1.json`, `duplicates-2.json`, `restricted-copies-1.json`, `restricted-copies-2.json` | Duplicate links by kind, merges across repositories, and verbatim copies of restricted sources. |
| `model-calls-1.jsonl`, `model-calls-2.jsonl` | Every model call: model asked and answered, route, prompt digest, reported usage and outcome. No prompt text. |
| `outlines-2.jsonl` | The 187 outlines of run 2: abstract purpose and source identity, never the source text. |
| `staged-index-2.json` | One line per staged row of run 2: identity, kind, title, licence, authoring, source, revision, path, digest, merged sources, declared effects and the number of triage notes. No bodies. |
| `staging-report-1.json`, `staging-report-2.json`, `staging-report-2-rerun.json` | The staging reports, and the rerun that added nothing. |
| `licence-template-verification-1.json` | The 16 stored licence word sets checked against `github/choosealicense.com` at the pinned commit: every file digest matches and every word set reproduces. |

The run folders themselves (quarantine, request logs, batches, populations
and the candidate databases) hold third-party bytes and stay outside the
repository.

## How to repeat

```bash
PYTHONPATH=src python tools/ingest_outside_material.py collect \
  --run-folder RUN_FOLDER --authorize-network-reads \
  --github-request-ceiling 4800 --https-request-ceiling 3000 --maximum-pause-seconds 3700 \
  --upstream-licence-lookups 3000 --package-checks --skillspector-program PATH_TO_SKILLSPECTOR \
  --authorize-model-calls --outline-model deepseek-v4-flash:0731 --model-call-ceiling 200 \
  --reuse-fetched-bytes-from EARLIER_RUN_FOLDER
PYTHONPATH=src python tools/ingest_outside_material.py stage \
  --run-folder RUN_FOLDER --database RUN_FOLDER/candidates.db \
  --namespace library.outside --authorize-isolated-staging
```

The runs used Python 3.12 with datasketch 1.6.5, skills-ref 0.1.0 and
SkillSpector 2.11.2 installed in an environment of their own.

## Limits

- The licence decisions are engineering rules that carry out the owner's
  direction; they are not legal advice.
- A registry entry is link only: its upstream code was not read, and 502
  entries were refused because their GitHub repository does not answer.
- 511 skills wait for the multi-file package contract.
- The near-duplicate merge is by content at a similarity of 0.85. One
  merged pair (a create and an update specification skill) differs in
  purpose; a reviewer can split it.
- The safety scans are triage, and they refuse conservatively. Of the six
  instruction-override blocks, four are skills that tell the reader never to
  follow an instruction found in content and quote one as the example, one
  is a safety guide that quotes an injection attempt, and one is a table
  row naming an option that overrides a default system prompt. The
  remote-script rule also refuses vendor install lines that pipe a
  downloaded installer to a shell, and one line that names the pattern in
  order to forbid it. Telling a quoted example from an instruction belongs
  to the malicious and benign regression set of roadmap step S-6.45.
- Nothing here was loaded by a harness, and nothing here is useful until an
  independent review approves it.
