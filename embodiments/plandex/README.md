# Plandex attempted integration

Plandex CLI 2.2.1 is installed at
`/home/username/loop-engine/embodiments/plandex/runtime/plandex`.
The official project is [plandex-ai/plandex](https://github.com/plandex-ai/plandex),
under MIT. Its README says the hosted cloud has been winding down since
October 3, 2025. A new integration must qualify the self-hosted path.

The first isolated help invocation panicked because startup downloads the
o200k tokenizer asset. The public asset was then downloaded into this
repository and supplied through a private tokenizer cache. Help succeeded
without external network. An actual `chat` attempt then entered first-run
account onboarding and failed on EOF. No account was created, no remote
mutation occurred and no model request was sent.

Evidence is under
`/home/username/loop-engine/artifacts/harness-expansion-20260909-DNMQ3Y/remaining-recipes/plandex/`:
`help-01.json`, `text-01/result.json` (the cached help retry),
`startup-01/result.json`, `o200k_base.tiktoken.provenance.json` and release hashes.
The cached help retry is not a successful task invocation.

Plandex requires a configured self-hosted server, account state and exact model
provider configuration before a safe task trial. Its diff review area is not
OS isolation. Custom providers are documented, but an Ollama Cloud broker
recipe for this server/client arrangement has not been qualified. The current
engine does not expose a runnable Plandex semantic embodiment.
