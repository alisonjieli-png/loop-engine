# Delimited-block drafts and the first passing Tactical candidates

Date: September 24, 2026, United States Eastern. Revisions: `f18f7da8`
(format version one) and `23c063fa` (format version two and the stop on a
spent allowance). Evidence:
[`native-blocks-batch-2026-09-24`](../../artifacts/native-blocks-batch-2026-09-24/README.md)
and [`native-blocks-format-2026-09-24`](../../artifacts/native-blocks-format-2026-09-24/README.md).

## Outcome

- **The block format fixed the drafts.** Under format version two, 18 of 20
  Tactical calls produced admitted drafts. Under JSON the day before, 0 of 20
  did.
- **Seven candidates pass every native precheck.** These are the first
  generated candidates ready for independent review. They come from a
  successor plan whose layout was preflighted offline.
- **The panel could not decide.** The Ollama Cloud account's weekly usage
  allowance is spent. Every available panel reviewer runs on Ollama, so the
  one panel call was refused and no verdict exists. Nothing is approved.
- **The Ollama comparison batch did not run.** All ten calls were refused
  by the same spent allowance, so no admission rate exists for Ollama yet.

## The format

`--draft-format` chooses how a model answers, and `run.json` names the
choice. JSON stays the default for producers that handle it.

```text
Draft formats
├── json: original_native_file_draft/v1, the existing contract
├── blocks: original_native_file_blocks/v1
│   └── <<<FILE path>>> ... <<<END FILE path>>> for every planned file
└── blocks2: original_native_file_blocks/v2
    ├── opener: <<<path>>> or <<<FILE path>>>
    ├── closer: <<<END path>>> or <<<END FILE path>>>
    └── closer omitted only before the next planned file or END DRAFT,
        and recorded as block_end_omitted
```

Each format has its own prompt resource version. Every block format:

- carries each file with its path and no JSON escaping;
- refuses, each with its own code, an unterminated block, a duplicate path,
  a path escaping the package, an unplanned path, content outside blocks or
  after the END line, a missing header or END line, an empty file and a
  missing planned file;
- may remove one exact enclosing Markdown fence, and records the removal.

Version two also refuses any marker-shaped line inside a file
(`draft_marker_misplaced`), so one file cannot silently take in another. The
admitted draft then passes the same exact draft parser as JSON.

Version two exists because of data. Under version one, the Tactical model
wrote `<<<path>>>` in all five completed answers. It closed most files with
`<<<END FILE path>>>`, one with `<<<END path>>>`, and left out the last END
line. That run was stopped because the same failure repeated.

The generator now also stops a run on `usage_limit_reached` and
`payment_required`. Before this, the Ollama batch dispatched all ten methods
into a spent allowance.

## Calls and admission

| Run | Producer | Format and plan | Calls | Admitted | Usage |
|---|---|---|---|---|---|
| Tactical 1 | `gemma-4-coding-abliterated` | blocks, hundred-file | 6 dispatches: 5 completed, 1 interrupted by the stop | 0 of 5 | 8,282 in, 27,973 out; the interrupted call is unknown |
| Ollama 1 | `minimax-m3` | blocks, hundred-file | 10 | not measured: all refused by the spent allowance | none reported |
| Tactical 2 | same | blocks2, hundred-file | 11, with 1 retry | 10 of 11 | reported for every call |
| Tactical 3 | same | blocks2, native-profile | 9, with 1 retry | 8 of 9 | reported for every call |

The one version-two failure that was not a refusal stopped at the 32,768-token
allocation. Tactical used 26 of its 40-call ceiling. Ollama used 11 of 40: the
ten batch calls and one probe that read the refusal. A second probe was
refused by the adapter's own output ceiling before any request. Each run gave
both producers the same allocation, timeout and plan.

## Prechecks

The hundred-file plan was frozen on September 23, before the native
profile's placement rules. All ten of its candidates were refused. The
refusals came mostly from the plan:

- acceptance data outside the passive folders, in all 10;
- compatibility metadata declared as configuration, and a `claude` style
  without `CLAUDE.md`, in 9;
- plugin and skill activation paths, in 2.

The model's content caused the rest:

- tests importing `tools.MODULE`, in 7;
- one invalid schema;
- one Python syntax error;
- one invalid skill front matter.

The successor plan keeps the eight tool methods and changes only the layout.
Acceptance data moves to `verification/`, compatibility metadata becomes strict
JSON data, a `CLAUDE.md` imports `AGENTS.md`, and the file purposes state the
schema and import rules. Before any model call, synthetic packages with this
layout passed every native precheck. The eight generated candidates then gave
**7 passes and 1 refusal**, for a Python file that does not parse.

## Review panel

The seven passing candidates were put to the panel under its current rule:
three approvals from three families other than the producer's `google`, and
any rejection withholds approval. There was no calibration, because the
native calibration pilot is on hold. The panel made one call. The spent Ollama
allowance refused it, and that stops every Ollama reviewer. So 7 items are
`panel_incomplete`, 0 are approved and 0 are rejected. The Codex reviewer is
ineligible because it does not report its answering model. The record does
not list the Claude reviewer; the likely reason, inferred, is that fewer than
three families remained for a quorum. Nothing was approved by its producer.

## Checks

| Check | Result |
|---|---|
| Generator tests | 45 pass: 13 known-wrong version-one answers, 12 known-wrong version-two answers, and natural and explicit spellings |
| Removed-guard controls | 22 of 22 detected: 12 for version one, 9 for version two, 1 for the spent-allowance stop |
| Tools suite | 1,385 tests. Only the five fresh-instance checks fail, and they also fail at the base revision |
| Hardcoding gate | No new high finding, with one exact entry per new prompt resource |
| Keys | No key and no account handle in any record |

## Unfinished, with reasons

- **The panel verdicts for the seven candidates.** They wait for the Ollama
  weekly allowance to reset, or for a reviewer that does not depend on it.
  Buying credits needs the owner.
- **The Ollama admission-rate comparison.** It waits for the same allowance.
  The plan, format and settings are frozen, so the rerun is one command.
- **The candidate refused for invalid Python.** It could get one more
  attempt within the remaining Tactical allowance.
