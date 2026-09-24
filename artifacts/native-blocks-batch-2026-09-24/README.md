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
