# Hermes Agent semantic-step qualification

Hermes Agent 0.21.1, from official tag `v2026.9.7`, completed the local
tool-free protocol qualification. This is not a live-provider or full-solve
result. The source is [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent),
under MIT. The release checkout is
`/home/username/loop-engine/embodiments/hermes_agent/runtime/NousResearch-hermes-agent-9949d0d`.
The isolated dependency environment is
`/home/username/loop-engine/embodiments/hermes_agent/runtime/.venv`.
All newly installed packages and caches are inside this repository. The
interpreter is the already installed Python 3.12.13, mounted read-only.

The manifest is `/home/username/loop-engine/embodiments/hermes_agent/harness.json`.
The recipe is `/home/username/loop-engine/src/loop_engine/core/harness_remaining_recipes.py`.
It invokes the original CLI entry point through a private stdin wrapper.
The upstream `-z` argument alone does not merge stdin. Model identity and the
known context capacity are supplied by the engine. Hermes refuses capacities
below 64,000; the adapter does not invent a larger value.

The private configuration has no enabled toolsets, MCP servers, persistent
memory, automatic compression or automatic title generation. The custom
OpenAI-compatible URL points only to the isolated engine broker. It does not
select a local inference model. Real inference, when separately authorized,
must use Ollama Cloud through the canonical gateway. The gateway owns output
allocation, model-call authority, token usage and cost. Missing usage is unknown.

Saved evidence is under
`/home/username/loop-engine/artifacts/harness-expansion-20260909-DNMQ3Y/remaining-recipes/hermes_agent/`:

- `core-text-01/result.json`: one local request, exact private task reached the
  installed agent, and the candidate matched the broker response.
- `core-request-tools-01/result.json`: an intentionally enabled terminal tool
  schema was refused before a model response. One local request.
- `core-response-tools-01/result.json`: injected unknown tool calls did not
  create the forbidden file or yield an accepted candidate. Three local requests.
- `dependency-install.json`: wheel-only dependency preparation and exact versions.
- `source.tar.gz.provenance.json` and `installed-files.json`: source identity and hashes.

All these requests used scripted fixtures with synthetic usage. They establish
local transport and refusal behavior, not model quality. Earlier failures remain:
`text-01` used too small a context capacity; `text-02` returned fixture text but
did not deliver the actual task through stdin and is excluded as qualification.
The final core probes test the corrected transport. Shared full-solve wiring and
live qualification are separate gates tracked by the campaign report.
