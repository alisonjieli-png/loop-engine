# ForgeCode semantic-step qualification

ForgeCode 2.13.21 completed a single-request, tool-free local protocol trial.
This is not a live-provider or full-solve result. The executable is
`/home/username/loop-engine/embodiments/forgecode/runtime/forge`.
The manifest is `/home/username/loop-engine/embodiments/forgecode/harness.json`.
The official source is [tailcallhq/forgecode](https://github.com/tailcallhq/forgecode),
under Apache-2.0. The exact release source and download hashes are under
`/home/username/loop-engine/artifacts/harness-expansion-20260909-DNMQ3Y/remaining-recipes/forgecode/`.

The recipe in `/home/username/loop-engine/src/loop_engine/core/harness_remaining_recipes.py`
uses the original CLI with a private stdin task and an empty native tool list.
It also disables tools globally and sets the output allowance globally, because
the global default overrides the per-agent field in this release. The gateway
remains authoritative for the actual output allowance, routes and accounting.

A newly created private Conversation has a fresh UUID, current creation time,
an explicit engine-supplied title, no prior context and empty pre-run metrics.
The documented `--conversation` argument imports that record. Upstream's
`TitleGenerationHandler` skips an already titled conversation. This removes
the auxiliary title call without patching upstream or substituting a provider
reply. The output decoder checks matching Continue/Finished session identifiers
and requires the candidate to match the actual broker reply.

Final evidence under the release evidence directory:

- `core-seeded-text-01/result.json`: one local request, full private task
  delivered, exact candidate accepted, `max_completion_tokens` set to 128.
- `core-seeded-request-tools-01/result.json`: an intentionally enabled tool
  schema was refused. One local request and no accepted candidate.
- `core-seeded-response-tools-01/result.json`: injected tool calls produced
  no forbidden file and no accepted candidate. Three local requests.

The earlier `core-text-01` and `text-04` attempts made two requests, including
an auxiliary title request. They are not qualification for the selected
single-request profile. The earlier cold-start failures also remain saved;
the CLI can return exit code zero while reporting authentication failure, so
exit code alone is not a success check.

These calls used a local scripted provider in a network-isolated process.
Token usage in those responses is synthetic. Separately authorized real calls
must use Ollama Cloud through the canonical gateway. Shared model-session
wiring and live qualification remain separate campaign gates.
