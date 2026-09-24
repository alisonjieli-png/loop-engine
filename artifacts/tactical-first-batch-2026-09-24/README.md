# Tactical first generation batch

September 24, 2026, United States Eastern. Original native candidates from
the owner's Tactical server (`gemma-4-coding-abliterated`, family `google`)
through the committed provider binding, under a ceiling of 40 model calls.
Candidates only: nothing here is approved, installed or published.

## Run 1

- `hermes-hundred-file-plan-14722d52.json`: the successor of the frozen
  hundred-file plan, built by its own builder at revision `14722d52`. The ten
  methods and 100 planned files are identical to the original; one source
  digest was refreshed.
- `generation-run/`: the frozen run, its journal, cursor and every saved
  response. Ten model calls, all completed with reported usage: 15,389 input
  and 51,110 output tokens in 356.7 seconds. **No candidate was prepared.**
- `draft-analysis-run-1.json`: why each draft was refused. The model wrapped
  every answer in a Markdown JSON fence, which the system prompt forbids. In
  eight of ten the JSON inside is also invalid: file contents written as raw
  arrays, trailing commas or a bad escape. The other two, for
  `check_tabular_transformation_invariants` and
  `review_json_with_native_claude_plugin`, are valid JSON inside the fence and
  pass the exact draft parser and packaging once the fence is removed.

## What changed after run 1

The generator now admits each answer through the existing
`model_response_admission` Loop before the exact draft parser. Strict JSON is
tried first; the only permitted repair removes one exact enclosing Markdown
JSON fence and is recorded in the completion's `response_admission`. Invalid
JSON, extra keys, text outside the fence and a second fence stay refusals. The
run record is version six and the journal version three.
`check_removed_guards.py` removes each admission guard in memory; all four
controls are detected (`removed-guards-*.json`).
