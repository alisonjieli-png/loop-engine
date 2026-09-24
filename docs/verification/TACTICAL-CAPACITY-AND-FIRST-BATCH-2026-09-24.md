# Tactical capacity and first generation batch

Date: September 24, 2026, United States Eastern. Base revision:
`e9233755`, which carries the
[Tactical provider binding](TACTICAL-GENERATION-BINDING-2026-09-23.md). The
owner authorized using the Tactical server to generate library candidates,
and asked for decisions from collected data rather than questions about
server settings.

## Outcome

- **The server is responsive.** Its metadata routes and a one-word chat
  reply answered in under half a second. The request that stalled on
  September 23 no longer holds it.
- **Capacity is 65,536 output tokens, verified by a completed call.** The
  server states no limit anywhere. The binding now declares the largest
  output the server was observed to complete, with that basis written in
  the record. Commit `14722d52`.
- **The first batch prepared no candidate.** Two runs of the ten-method,
  100-file plan made 20 model calls. Every answer was wrapped in a Markdown
  fence. In 17 of 20 the JSON inside was invalid too. So nothing was
  prechecked or put to the review panel.
- **The generator now admits drafts explicitly.** Between the runs it
  gained the existing response admission Loop. That Loop may remove one exact
  enclosing JSON fence and records it; every other deviation is still
  refused. Commit `6d0b7588`.
- **The server ignores a response JSON Schema.** One probe call showed it,
  so grammar-constrained output is not available on this server as
  configured.
- **Decision:** the next approach is a draft format that does not nest file
  contents inside JSON strings. It is described
  [below](#decision-and-next-step), not built yet.

## Capacity probe

The ceiling for this step was five calls. Four were used, two of them model
calls.
The records are in
[`tactical-capacity-probe-2026-09-24`](../../artifacts/tactical-capacity-probe-2026-09-24/README.md).

| Call | Route | Result |
|---|---|---|
| Metadata, before the calls | models, server information, metrics, health, version, OpenAPI | All answered; no route names a sequence, input or output limit |
| 1 | Chat, a one-word answer, `max_tokens` 10,000,000 | Accepted without a refusal or a stated limit; `READY` in 0.44 seconds |
| 2 | The tokenizer route | Returns only a count and token ids |
| 3 | The KV cache event route | Returns an empty list, so it states no cache size |
| 4 | Completion asked for exactly 65,536 tokens on a counting text that never ends by itself | `finish_reason` `length` at exactly 65,536 completion tokens after a 292-token prompt, with usage and `[DONE]`, in 467 seconds |

TensorRT-LLM did not refuse the oversized `max_tokens` with a stated limit,
so no refusal exists to quote. The successor
[`capacity-record-verified-65536.json`](../../artifacts/tactical-capacity-probe-2026-09-24/capacity-record-verified-65536.json)
declares 65,536 with basis `verified_completed_length`. It supersedes the
unknown record of September 23, which keeps its bytes. It is not the
server's configured limit. The stall of September 23 came at 105,866 total
tokens, and the full allowance plus a prompt of several thousand tokens
stays well below it.

## Batch runs

Both runs used the committed binding and the successor of the frozen
[hundred-file plan](../../artifacts/tactical-first-batch-2026-09-24/README.md),
pinned to the revision under test each time. Both ran under the 40-call
ceiling, with the full 65,536-token allowance per call and no strict total
token ceiling. Usage was reported for every call.

| Run | Revision | Calls | Tokens in and out | Prepared | What the drafts did |
|---|---|---|---|---|---|
| 1 | `14722d52` | 10 | 15,389 and 51,110 | 0 | All 10 fenced. 8 invalid inside the fence: file contents as raw arrays, trailing commas, one bad escape. 2 valid inside the fence |
| 2 | `6d0b7588`, with draft admission | 10 | 15,369 and 61,195 | 0 | All 10 fenced and the fence removed as recorded. 9 invalid JSON. 1 valid but with keys beyond `path` and `content` |

The two drafts from run 1 that were valid inside the fence passed the exact
draft parser and packaging once unwrapped, in an offline check. Run 2 did
not reproduce them, so the model's output varies between runs at
temperature 0. No saved response was turned into a candidate outside the
generator.

The admission step reuses `model_response_admission`. The saved response
keeps the model's original bytes. Each completion records the admission
strategy, the transformation and any schema failure category. Four
removed-guard controls are all detected: the fence repair, the draft
schema, the admitted check and the record.

## Structured output probe

One call asked for a draft whose one file is a JSON document, the exact case
that failed, with `response_format` carrying the draft's JSON Schema. The
server returned HTTP 200 and a fenced answer whose file used a `data` key
instead of `content`. It accepted the field and did not enforce it
([record](../../artifacts/tactical-first-batch-2026-09-24/structured-output-probe-1.json)).

## Decision and next step

Twenty calls repeated one failure: this model does not reliably write file
contents as escaped JSON strings. Repeating the same request is not a new
approach, and the server offers no grammar-constrained output. The next step
is a successor draft contract that carries each file in an explicit
delimited block with no escaping. It needs its own versioned prompt resource,
a strict parser that refuses anything outside the blocks, known-wrong tests
and removed-guard controls. The review path stays the same: the native
factory, prechecks with `--content-profile native-original`, then the
independent panel. There, three approvals must come from families other than
`google`.

## Calls

| Step | Model calls | Other recorded calls |
|---|---|---|
| Capacity probe | 2 | 2 route reads and the metadata read |
| Generation run 1 | 10 | |
| Generation run 2 | 10 | |
| Structured output probe | 1 | |
| **Total** | **23** | |

The generation step used 21 of its 40-call ceiling. No call was retried
automatically, no provider was switched and no key was written anywhere.

## Limitations

- The capacity is verified, not stated by the server. A larger value needs
  a new completed measurement or a stated limit and a successor record.
- Output varies between runs, so two runs do not measure a success rate.
- Nothing here qualifies model quality, a package, or any approval.
