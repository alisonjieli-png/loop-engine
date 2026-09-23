# Independent review panel pilot of 22 September 2026

Kind: dated evidence record for roadmap package LS2 (the independent review
panel). It approves nothing and serves nothing. The review decisions of the
pilot are in the dated review record
[`reviews-panel-2026-09-22.json`](../../examples/29_intelligence_service/starter-catalogue/reviews-panel-2026-09-22.json),
beside the catalogue's `reviews.json`, which this work did not edit. The panel
itself is described in its [component guide](../../tools/candidate_review/README.md).

Dates are the owner's local dates, in United States Eastern time. Times in the
ledgers are universal time.

## What was asked

Put 30 of the 74 starter catalogue items that had no verdict to a panel of
independent reviewers from different model families, record every call, and
report throughput, approvals, rejections, disagreements, usage and failures.
The 30 items are the first 30 of the 74 in the order of the SHA-256 digest of
the seed `ls2-pilot-2026-09-22` joined to each identity, so anyone can
reproduce the selection from the record. Claude Code wrote every one of the
74 items, so no reviewer of the Anthropic family was asked about any of them.

## Result in one paragraph

The panel rejected all 30 items. No item reached three approvals from three
model families. 14 of the 30 items drew at least one approval beside the
rejections. The deterministic pre-checks refused none of the 30. The run made
91 calls on the 30 items and 32 calibration calls, every one with its usage
reported, in 658.5 seconds for the whole command. The rejections are specific:
most name a promise the steps do not keep, an overstated sentence about the
cited file, or a declared effect list that does not match the steps. Each one
is written into the record with the reviewer, the criteria it cites and its
reasons, and is the repair list for the next version of each body.

## The two attempts

```text
Pilot of 22 September 2026
├── Attempt 1 (attempt-1/): stopped when the session that ran it reached its limit
│   ├── smoke-1: one item, 4 calls, 88.8 seconds
│   ├── pilot-1-calibration: 4 calibration items, 32 calls, 224.5 seconds
│   ├── pilot-1: 13 of the 30 items reached, 33 calls completed, no end row
│   └── 3 dispatches to the Codex reviewer never received a call row:
│       outcome and usage unknown
└── Attempt 2 (attempt-2/): the same 30 items, the same reviewers, a corrected request
    ├── pilot-2-calibration: 4 items, 32 calls, 197.4 seconds
    ├── pilot-2: 30 items, 91 calls, 460.5 seconds, stop reason completed
    └── the record written again from the stored verdicts, with no model call
        ├── pilot-2-record-calibration: 0 calls, stop reason call_ceiling_reached
        └── pilot-2-record: 0 calls, stop reason completed
```

Attempt 1 is kept, not repeated in place. Its ledger records a defect in what
each reviewer was sent: every written criterion went to every body. The review
sheet judges its two kinds of body differently. A body that restates its cited
file must say what that file says or does; a body of general practice is judged
as practice, and only its one sentence about the cited file must be true. All
74 unreviewed items are general practice. In attempt 1, 26 of the 34
rejections of real items cited the criterion for the other kind of body. None
rested on it alone.

Attempt 2 tells each reviewer the kind of body in the review sheet's own words
and sends only the criteria for that kind (criteria record version 2). The
same change binds each verdict to the exact prompt it answered, so no verdict
of attempt 1 was reused. Attempt 2 also scans the item record and every cited
source for secret-shaped values before anything is sent.

Two later changes were made after attempt 2 ran and before the code was
committed: an installation is asked no more in a run after a failure that
cannot change within the run, such as a refused login, and a gateway reviewer
is unavailable when its credential variable is not set. Neither condition
occurred in attempt 2, so neither changes its calls or decisions.

The first record attempt 2 wrote named the reviewer instructions by an absolute
path on the machine that ran it, and took each reviewer's model version from
the provider listing at the time the record was written instead of from the
calls. Both were corrected in the record builder and its strict reader, and the
record was written again by the same command with the same ledger and a call
and token ceiling of zero. That command read the provider listing again (a
listing, not a model call), reused every stored verdict and made no call. Its
calibration run stopped at the ceiling because MiniMax had given no valid
verdict on the control item, which no call could now replace; the control item
does not decide whether a reviewer is excluded. Its two runs are in the ledger
with no calls, and the review time of the record counts only the runs that
made calls.

## Calibration

Before the real items, every eligible reviewer was asked about three real
bodies with one planted defect each, and about one body an earlier independent
review approved, unchanged. A reviewer that approves a planted defect is not
asked about real items in the same command.

| Reviewer installation | Attempt 1 | Attempt 2 |
|---|---|---|
| `ollama.deepseek-v4-pro` | rejected all 3 planted defects, approved the control | approved the item whose effects list was emptied; excluded from the real run |
| `ollama.qwen3.5-397b` | rejected all 4, including the control | rejected all 4, including the control |
| `codex.gpt-6-sol` | rejected all 4, including the control | rejected all 4, including the control |
| `ollama.minimax-m3` | rejected all 3, approved the control | rejected all 3; its answer on the control was not valid JSON |
| `ollama.kimi-k2.6` | rejected all 4, including the control | rejected all 4, including the control |
| `ollama.glm-5.3` | rejected all 3, approved the control | rejected all 3, approved the control |
| `ollama.mistral-large-3` | rejected all 3, approved the control | rejected all 3, approved the control |
| `ollama.gpt-oss-120b` | rejected all 3, approved the control | rejected all 3, approved the control |

The same reviewer answered the same planted defect differently in two
attempts two hours apart: one sample per item cannot measure how often a
reviewer errs. Three reviewers
rejected the approved control both times. The calibration excludes a reviewer
only for approving a planted defect, so a strict reviewer stays on the panel.

## Attempt 2 decisions

With DeepSeek excluded, the first three families in the declared order asked
every item: Qwen (`qwen3.5:397b`), OpenAI through the Codex command line
(`gpt-6-sol`, `codex-cli 0.155.1`) and MiniMax (`minimax-m3`). Kimi
(`kimi-k2.6`) replaced one invalid Qwen answer.

| Reviewer installation | Approved | Rejected | Blocking findings by criterion |
|---|---:|---:|---|
| `ollama.qwen3.5-397b` | 0 | 29 | effects rule 27, general practice grounding 24, licence and effects 1, required parts 1 |
| `codex.gpt-6-sol` | 1 | 29 | read as a customer 28, general practice grounding 16, effects rule 9 |
| `ollama.minimax-m3` | 13 | 17 | general practice grounding 17, effects rule 9, licence and effects 7, read as a customer 7, required parts 2 |
| `ollama.kimi-k2.6` | 0 | 1 | effects rule 1, general practice grounding 1 |

Examples of what the rejections say, from the record:

- A write made safe to repeat: storing an idempotency key in a database
  transaction cannot make an outside charge or message part of that
  transaction.
- A schema change in compatible steps: once step 6 stops writing the old
  shape, rolling back to code that reads it can lose access to newer rows, so
  the check that promises a lossless rollback at every step is unsupported.
- Classifying a failure before a retry: the steps allow automatic retries with
  no attempt limit.
- Shared state and ordering: a lock local to one process passes the stated
  checks while leaving a race between two copies of a service.
- The licence of every bundled component: the cited class allows an empty
  licence name, so the sentence that every item carries a licence name
  overstates the file.

Many of the effects findings are disputed between reviewers. The sheet's
effects rule counts an effect when a step tells the reader to perform it; the
reviewers disagree about whether "record", "run the check" or "read the log"
tells the reader to perform a file write, a command or a file read. Of the 76
rejecting verdicts on real items, 51 cite an effects criterion and 7 rest on
one alone. A precise effects rule in the
catalogue, with worked examples, would remove that disagreement at its source.

## Comparison of the attempts

[`comparison.json`](comparison.json) is written by
[`compare_attempts.py`](compare_attempts.py) from the two ledgers. On the 53
pairs of one reviewer and one item that both attempts decided on the same
bytes:

| Pairs | Decision in attempt 1 | Decision in attempt 2 |
|---:|---|---|
| 22 real items, Qwen and Codex | rejected (14 of them citing the other kind's criterion) | rejected, citing only criteria that apply |
| 26 calibration items | rejected | rejected |
| 4 calibration items | approved | approved |
| 1 calibration item, DeepSeek, emptied effects list | rejected | approved |

The corrected request removed every citation of the other kind's criterion and
changed no decision on a real item. The rejections of attempt 1 did not depend
on the misapplied criterion.

## Usage, throughput and failures

| Measure | Attempt 1 | Attempt 2 |
|---|---:|---|
| Calls completed | 69 | 123 (91 on items, 32 calibration) |
| Dispatches with no call row (outcome and usage unknown) | 3 | 0 |
| Input tokens reported | 560,075 | 1,154,280 |
| Output tokens reported | 77,761 | 106,936 |
| Calls with unknown usage | 0 | 0 |
| Calls with an answer that was not a valid verdict | 0 | 2 (one Qwen answer with a finding outside the declared shape, one MiniMax answer that was not one JSON object) |
| Output limit reached | 1 (GLM in the smoke run, before its allocation was raised) | 0 |
| Rate limit pauses | 0 | 0 |

Throughput of attempt 2, with three items reviewed at a time: 30 standing
verdicts in the 460.5 second review run, 234.5 items an hour; 164 items an hour
when the 197.4 second calibration is counted. Median seconds per call:
DeepSeek 2.7, Qwen 5.7, MiniMax 7.3, Kimi 9.3, Codex 21.4, GLM 42.2. The review
of one item used about 33,600 tokens on average; the Codex command line adds
its own instructions, so each Codex call used about 17,000 input tokens.

Arithmetic from these measured rates, not a forecast: 10,000 items reviewed
the same way would take about 43 hours at three items at a time and about 336
million tokens, of which about 182 million would go through the Codex command
line. Whether a subscription allows that is not known.

## Model calls and authority

Model calls ran under the owner's authority of 22 September 2026: Ollama Cloud
with the key already in the environment, the Codex command line and the Claude
Code command line, within the existing subscriptions. The Ollama Cloud key was
read only from its environment variable, to be sent in the request header, and
the Codex command line used its own login. No credential was printed, logged
or stored. Every completed call is in a ledger with its model, version, route
or command, usage and outcome; the three dispatches of attempt 1 that never
completed are in its ledger as dispatches, with their outcome and usage
unknown.

The owner named Kimi 3. The repository's model route policy refuses `kimi-k3`
on every route, so its installation is declared and switched off, and the
Kimi family was asked through `kimi-k2.6`.

The Claude Code command line in bare mode reads only `ANTHROPIC_API_KEY`,
which this machine does not set. One probe with a fixed connection prompt, not
a catalogue item, recorded `authentication_unavailable` with no model call
([`claude-code-bare-probe.json`](claude-code-bare-probe.json)). No catalogue
item could have been put to it: Claude Code wrote them all.

## Files

| File | What it holds |
|---|---|
| `attempt-1/ledger.jsonl` | Every run, dispatch, call and verdict of attempt 1, byte for byte as the panel wrote it. |
| `attempt-1/smoke-1-command-summary.json` | The command summary of the one-item smoke run. The pilot-1 command wrote no summary before it stopped. |
| `attempt-1/criteria-v1.json` | The criteria record attempt 1 sent, version 1. The other resources attempt 1 read are byte for byte the committed ones. |
| `attempt-2/ledger.jsonl` | Every run, dispatch, call and verdict of attempt 2. |
| `attempt-2/command-summary.json` | The command summary of attempt 2. |
| `attempt-2/record-rewrite-command-summary.json` | The command summary of writing the record again from the stored verdicts, with no model call. |
| `comparison.json`, `compare_attempts.py` | The comparison of the two attempts and the script that writes it from the ledgers. |
| `claude-code-bare-probe.json` | The one probe of the Claude Code command line. |
| `check-first/` | The new checks of attempt 2's changes, run before each change and failing. `run-identity-checks-before-the-change.txt`, `reviewer-identity-checks-before-the-change.txt`, `reviewer-decided-twice-checks-before-the-change.txt`, `answer-shape-checks-before-the-change.txt` and `precheck-and-licence-checks-before-the-change.txt` hold the checks of repairs made by the adversarial verification that followed the pilot, run the same way before each repair. |
| `source_mutants.py` | Removes each guard from the source in turn, in a scratch copy, and records which checks then fail. |
| `source-mutants-1.json` | The first run. Not valid: the scratch copy lacked a folder that one catalogue item cites, so the unmutated checks already failed and every mutant counted as failing. The script now links every cited folder and runs no mutant against a failing baseline. |
| `source-mutants-2.json` | A run on an intermediate tree, before the record builder's path and version corrections; kept, superseded by the next run. |
| `source-mutants-3.json` | The run on the committed tree. |

## Limits

- One sample per reviewer and item. Model answers vary between calls; the same
  reviewer approved a planted defect in one attempt and rejected it in the
  other.
- The 30 items are one catalogue's general practice bodies written by one
  producer. The rejection rate says nothing about bodies from other sources.
- The calibration set holds three planted defects and one control. It measures
  those defect classes only and cannot estimate an error rate.
- A strict reviewer is never excluded, and one rejection keeps an item a
  candidate. A reviewer whose rejection is mistaken therefore withholds
  approval until the item is reviewed again; this pilot does not measure how
  often that happens.
- The record approves nothing and nothing here is served.
