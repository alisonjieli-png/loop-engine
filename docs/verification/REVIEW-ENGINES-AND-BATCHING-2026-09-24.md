# Review engines and batched review for review throughput

Date: September 24, 2026, United States Eastern. Roadmap step S-6.63, the
independent panel of several model families and its measured throughput and
error gate. This record covers the engine and panel changes. The calibration,
the panel run on the overnight candidates and the throughput numbers follow in
a separate dated record. Evidence:
[`review-throughput-2026-09-24`](../../artifacts/review-throughput-2026-09-24/README.md).

## Why

Review is the bottleneck. The owner wants 100,000 approved packages and 1,000
more a day, and every approval needs three families other than the
producer's. The Ollama Cloud allowance is spent, so the reviewers reachable
without it are: google through the owner's Tactical endpoint, openai through
the Codex command line, and anthropic through the Claude command line on the
owner's subscription.

## What changed

```text
Candidate review
├── Reviewer edge
│   ├── command_line, protocol codex_exec_session (new)
│   │   └── the model is pinned with -m {model} and read back from the
│   │       command line's own session record
│   ├── command_line, installation claude_code.subscription (new)
│   │   └── claude -p --safe-mode, the owner's subscription login, no tools
│   └── provider_binding engine (new), installation
│       tactical.gemma-4-coding-abliterated
│       └── the committed Tactical binding, now declaring the review purpose
├── Envelope
│   ├── batched review: several items per call, one verdict per item, each
│   │   bound to its own item's identity and digest
│   ├── a call ceiling per quota group
│   ├── a stop after repeated identical failures
│   └── verdicts collected below the quorum, only with a written reason
└── Adapter from overnight batch candidates to native proposals (new)
```

### The Codex reviewer records which model answered

The `codex exec --json` events carry the answer and the usage but no model.
The new protocol `codex_exec_session` reads the thread identity from the
events, finds the one session record the command line wrote for that thread,
and requires every turn context in it to name the installation's model. The
installation must pin that model with `-m {model}` and must not pass
`--ephemeral`, which suppresses the record; both are refused when the engine is
built. An unreported model is still refused: no record, two records, another
thread, two models or a missing turn context all end in
`model_identity_mismatch`, and the usage is kept. The older protocol
`codex_exec_jsonl` stays and stays refused.

The session record is the command line's own statement of the model it asked
the service for. The service does not report a model to the command line, and
no record in 60 earlier sessions held one. The protocol's name stays in the
installation, so the basis of the reported model is part of every call's
installation digest.

Two probe calls on September 24 reached the service and were refused for the
subscription's usage limit, which lasts until September 29 at 5:24 PM, before
any model response. Their session records name the thread once and the pinned
model `gpt-6-sol`, and the engine's reader returns that model for both real
records. The readback therefore has offline checks and real-record checks,
and no answered call yet. The second probe also showed that
`-c project_doc_max_bytes=0` does not keep the owner's global instruction
pointer (624 characters) out of the request; the command line also adds about
7,100 characters of its own harness framing. That is recorded as a limit of
the Codex reviewer, not changed.

### The Claude reviewer uses the subscription

`claude -p --bare` reads only `ANTHROPIC_API_KEY`, which this machine does not
set, so `claude_code.bare` is disabled with that reason. The new
`claude_code.subscription` runs `claude -p --safe-mode`: every customization
is off, the subscription login works, there are no tools and no session is
kept. The model is pinned with `--model {model}`; the result's model usage
must name only that model. One probe call on September 24 answered `READY`
with model `claude-opus-5-5`. The owner capped this reviewer at 150 review
calls in total; the command's `--quota-group-ceiling claude_subscription=N`
holds each command to what remains.

### The Tactical endpoint as a google reviewer

The new `provider_binding` engine reaches the owner's Tactical endpoint only
through the committed provider binding that the candidate generator already
uses. The binding now declares the review purpose `decide_label` beside
`generation`; its new digest is
`701d978e37f88c60906cf2c668481ce4796a64dc4c2f6dc61549df8f2058ee80`. The
generator's loader takes the purpose and refuses a binding that does not
declare it, with the new code `provider_binding_purpose_undeclared`. Every
refusal comes before the credential is read, and the credential is resolved
inside the review process only. Tactical reviews only items that google did
not produce.

### Batched review

One call can ask a reviewer about up to 12 items of one content profile. The
system part adds the batch answer contract in
`tools/candidate_review/resources/BATCH-ANSWER.md` to the reviewer's
instructions. Each item's material is exactly what its single prompt holds.
The answer is one JSON object whose `verdicts` list holds exactly one verdict
per item, in order, each naming the item's identity and digest. One bad
verdict costs only its own item; a list of another length counts for none.
Items are chosen reviewer by reviewer in the same order as one at a time, so
the rule is unchanged. A verdict is keyed by the item's own member digest, so
a later command reuses it whichever items share the request. The ledger has
two new rows, `candidate_review_batch_dispatch/v1` and
`candidate_review_batch_call/v1`, and the call's usage is recorded once.

### Run limits

- `--quota-group-ceiling GROUP=N` stops one quota group after N calls in a
  command, calibration included, while the others continue.
- `--stop-after-repeated-failures N` stops asking an installation that failed
  the same way N calls in a row. Rate limits and spent allowances do not
  count; they have their own handling.
- `--exclude-installation ID=REASON` keeps an installation out with its
  written reason.
- `--collect-below-quorum REASON` asks each reachable family once although the
  reachable families cannot reach the quorum. The rule is unchanged: such an
  item ends rejected or incomplete, and its verdicts wait in the ledger for the
  missing family, which a later command asks alone.
- `--calibrate-only` runs the calibration and no real candidate.

### The adapter for overnight candidates

`tools/native_proposals_from_overnight_candidates.py` attributes each
overnight candidate to the lane the batch journal records as its writer and to
the idea record of the matrix in effect at that write, then writes one
version-two proposal per candidate whose file kind has a qualified native
placement. Every proposal passes through the factory alone first, so one
refused candidate cannot refuse the others.

## Decisions and reasons

| Decision | Reason |
|---|---|
| Read the Codex model from the session record, and name the protocol so the basis is part of the installation. | The coordinator named pinning plus readback from the structured output or session record. The events carry no model; the session record does, per turn. A requested model is still never substituted for a missing record. |
| Add the review purpose to the existing Tactical binding instead of a second binding. | One binding keeps one trust contract, one capacity record and one credential reference; the loader now checks the purpose, so the declaration is explicit and a purpose that is not declared is refused. |
| Key a batched verdict by the item's own material, not the whole batch. | Composition of a batch is an efficiency choice; a verdict that depended on its companions could never be reused. Whether sharing a request changes verdicts is measured by the calibration, which runs in the same mode. |
| Refuse `--record` with batch sizes above one. | The dated review record's strict reader accepts single calls only. A record version that reads batch calls is the next step; until then the ledger is the record. |
| Collect verdicts below the quorum only with a written reason. | Without the reason the old efficiency rule holds. With it, a rejection decides now and approvals wait for the missing family without being asked again. |
| Converted overnight packages declare the read-only file effect. | The producers wrote effects only in prose, and prose is not typed authority. Reads of the step's files are the narrowest effect a harness needs to follow instructions; reviewers judge whether it covers every requested operation. |
| Place a harness routing file as `AGENTS.md`; do not place subagent files. | `AGENTS.md` is the qualified native entrypoint for routing instructions. A subagent definition lives on an activation path the native profile does not yet qualify. |

## Checks

| Check | What it proves |
|---|---|
| `tools/test_candidate_review_engines.py` | The session protocol counts an answer only for the model its session record names, refuses a missing or disagreeing record, and refuses `--ephemeral` or an unpinned model when the engine is built. |
| `tools/test_candidate_review_binding_engine.py` | The binding engine answers through the real adapter and gateway, the credential reaches only the request header, and every binding refusal comes before the credential. |
| `tools/test_generate_original_native_provider_binding.py` | A binding serves only the purposes it declares. |
| `tools/test_candidate_review_batching.py` | Batch answers bound per item, member keys, batched runs under the unchanged rule, the cursor across batches, the run limits and the new command options, with a mutant control for each new guard. |
| `tools/test_native_proposals_from_overnight_candidates.py` | Attribution by the journal and the matrix in effect, committed attribution only, placement by kind, changed bytes left out, and a factory refusal kept to its own candidate. |

Single-item prompts are byte for byte unchanged: the digests of every
calibration prompt for two installations were the same before and after the
prompt builder was split into reusable parts.
