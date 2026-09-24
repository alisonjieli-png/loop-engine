# Delimited-block batches, September 24, 2026

The plan `hermes-hundred-file-plan-f18f7da8.json` is the hundred-file plan
at revision `f18f7da8`, with ten methods and 100 planned files. Both
producers were run on equal terms:

- the same plan and the same block format, version one;
- an output allocation of 32,768 tokens and a 600-second timeout;
- a ceiling of 40 model calls for each producer.

`summarize_run.py` lists every call of a run with its model, usage and
outcome.

## Tactical, format version one: stopped after the same failure repeated

`tactical-run/` and `tactical-run-summary.json`: six dispatches, five
completed and one interrupted by the operator stop, so its outcome is unknown.
The five completions used 8,282 input and 27,973 output tokens, and none was
admitted. All five failed the same way. The model opened every file with
`<<<path>>>` instead of `<<<FILE path>>>`. It closed most files with
`<<<END FILE path>>>`, one with `<<<END path>>>`, and left the last file
without an END line. The run was stopped because the same failure repeated
unchanged.

Offline, the version-two grammar reads four of the five saved drafts once
their header names version two. It refuses the fifth, which writes one
planned file twice. No saved draft was admitted outside the generator.

## Ollama Cloud, `minimax-m3`: refused by the spent weekly allowance

`ollama-minimax-run/` and `ollama-minimax-run-summary.json`: ten calls, each
refused with `usage_limit_reached` and no usage. The generator then did not
stop on that code; it now does. `ollama-allowance-probe-1.json` was refused by
the adapter's own output ceiling before any request.
`ollama-allowance-probe-2.json` shows the provider's refusal: the weekly usage
limit is reached, and adding credits would be a purchase. The account handle
in that text is redacted.

## Tactical, format version two, hundred-file plan

`hermes-hundred-file-plan-23c063fa.json` and `tactical-run-v2/`: eleven
calls, with complete reported usage. Nine of the first ten answers were
admitted and prepared. The tenth, `review_json_with_native_claude_plugin`,
stopped at the 32,768-token allocation. One allowed retry of it was admitted,
so there are ten candidates from eleven calls.

`review/`: the ten were merged with `merge_prepared_proposals.py` from the
first batch folder and prepared once by the factory, with package digests
unchanged. The native prechecks refused all ten. The layout this plan declares
predates the profile's rules:

- acceptance data in `fixtures/`, refused in all 10;
- compatibility metadata declared as configuration, and a `claude` style
  without `CLAUDE.md`, refused in 9;
- plugin and skill activation paths, refused in 2.

The model's own content added two more kinds of refusal. Seven tests import
`tools.MODULE`. There was also one invalid schema, one Python syntax error and
one invalid skill front matter.

## Tactical, format version two, native-profile plan

`build_native_profile_plan.py` derives `native-profile-plan-23c063fa.json` from
the hundred-file plan. It keeps the eight tool methods and changes only the
layout:

- acceptance data moves to `verification/`;
- compatibility metadata becomes strict JSON data;
- a `CLAUDE.md` imports `AGENTS.md`;
- file purposes state the schema and import rules.

`plan-preflight/`: before any model call, one synthetic package per method,
with fixture content that follows the layout, passed every native precheck.
These are layout fixtures, not candidates.

`tactical-run-native-profile/`: nine calls. Seven of eight answers were
admitted on the first pass. One wrote a planned file twice and was refused as
`draft_path_duplicate`; its one retry was admitted. That gives eight
candidates from nine calls.

`review-native-profile/`: seven of the eight pass every native precheck. One,
`validate_focused_attempt_handoff`, has a Python file that does not parse.

## Review panel

`review-native-profile/review-panel-attempt-1.json`: the seven passing
candidates were put to the panel under its current rule. That rule needs
three approvals from three families other than the producer's `google`, and
any rejection withholds approval. The run had no calibration, because the
native calibration pilot is on hold. The panel made one call. It was refused
with `usage_limit_reached` by the spent Ollama weekly allowance, which stops
every Ollama reviewer. So there are no verdicts: 7 items are
`panel_incomplete` and 0 are approved. The Codex reviewer is ineligible
because it does not report its answering model. The record does not list
the Claude reviewer. The likely reason, inferred and not stated by the
record, is that with every Ollama reviewer stopped fewer than three families
remained, so no item could reach quorum.

## Retry and the batch waiting for the panel

- `native-profile-plan-23c063fa-validate-retry.json` and
  `tactical-run-validate-retry/`: one Tactical call for the method whose
  candidate the prechecks refused for invalid Python. It was admitted strictly
  and prepared. It used 1,824 input and 5,019 output tokens, and the
  original run folder is unchanged.
- `merge_pending_batch.py` and `pending-panel-batch/`: the seven passing
  candidates plus the retry, prepared once by the factory. All eight pass
  every native precheck, with zero calls. The batch waits for the panel until
  the Ollama weekly allowance resets.
- `tactical-run-validate-retry-summary.json`: that call with its model,
  usage and outcome. Tactical used 27 of 40 calls in all.
