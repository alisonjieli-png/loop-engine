# Tactical retry and the batch waiting for the panel

Date: September 24, 2026, United States Eastern. This follows the
[block-format batch record](NATIVE-BLOCKS-FORMAT-AND-TACTICAL-BATCH-2026-09-24.md),
which keeps its bytes. Evidence:
[`native-blocks-batch-2026-09-24`](../../artifacts/native-blocks-batch-2026-09-24/README.md).

## Outcome

- **The retry worked.** The one candidate that the prechecks refused for
  invalid Python, `validate_focused_attempt_handoff`, got one more Tactical
  call. Its draft was admitted strictly and prepared. The call used 1,824
  input and 5,019 output tokens in 36 seconds.
- **Eight candidates now pass every native precheck.** They form one
  prepared batch at revision `23c063fa`, with zero calls. The batch holds
  the seven that passed before and the retry.
- **The batch waits for the review panel.** Every available reviewer runs on
  Ollama Cloud, and its weekly allowance is spent. No reviewer call was made.

## How the retry was made

The generator had recorded the first candidate for this method as prepared,
because the invalid Python was found later by the review prechecks. So
`--retry-failed` does not redo it. Instead a one-method plan,
`native-profile-plan-23c063fa-validate-retry.json`, carries the identical
method, pinned to the same revision `23c063fa`. It ran in a detached worktree
at that revision, with the same binding, block format version two, a
32,768-token allocation and a 600-second timeout, under a ceiling of one call.
The original run folder is unchanged.

`merge_pending_batch.py` takes the seven passing candidates from
`tactical-run-native-profile`. It skips that run's candidate for this method
and takes the retry from `tactical-run-validate-retry`. The existing factory
then prepares one batch. `pending-panel-batch/review-prechecks.json` records
the zero-call prechecks: all eight pass.

## Calls

| Producer | Used | Ceiling |
|---|---|---|
| Tactical, today's block-format work | 27 | 40 |
| Ollama Cloud generation | 11, all refused by the spent allowance | 40 |
| Review panel | 1, refused by the spent allowance | none declared |

## Next

When the Ollama weekly allowance resets, run the review command on
`pending-panel-batch/prepared-batch` with a new ledger and record path, and
declared call and token ceilings. The panel rule is unchanged: three
approvals from three families other than the producer's `google`, and any
rejection withholds approval. The Ollama comparison batch reruns with the
frozen plan, format and settings.
