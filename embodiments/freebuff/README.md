# Freebuff adapter experiment

Freebuff's distributed Linux binary reports version 0.0.172 and displays help
inside the private sandbox. A task startup entered the project-selection UI
and was stopped at its ten-second deadline. It made no request to the scripted
provider. No text roundtrip or Ollama Cloud compatibility was established.

The [official public repository](https://github.com/CodebuffAI/freebuff) is
pinned at `cc9069e251e8fedd5784c688ce78ccfecd76815f`. It has an Apache-2.0
license and its README directs users to the npm `freebuff` package. The public
source identifies Freebuff as a project built on Codebuff.

The npm wrapper for version 0.0.172 declares MIT, names
`CodebuffAI/freebuff-private` as its repository, and disables npm provenance.
Its launcher selects the binary from the official Codebuff release endpoint.
The downloaded archive and package metadata are saved locally. There is no
verified mapping from that compiled binary to the public source revision.

The installed help exposes version, continuation, working-directory, and
login options. It exposes no noninteractive prompt option or custom model
endpoint option. The inspected source uses a hosted Codebuff/Freebuff service
protocol, so the proposed model-broker recipe refuses this project explicitly.
An unavailable recipe is not replaced with another harness.

The public CLI parser explicitly omits prompt and agent override arguments in
Freebuff mode. Its linked headless SDK is `@codebuff/sdk`. That SDK requires a
Codebuff API key and constructs model requests through its hosted `/api/v1`
service. A service base URL is not a documented Ollama Cloud model adapter.
No account, hosted-service impersonation, or alternative harness was used.

The fixture records, written on the machine that ran this work to
`artifacts/harness-expansion-20260909-DNMQ3Y/lightweight-recipes/` and not
distributed with the repository,
contain the version, help, startup timeout, and zero request counts. All
execution used a clean home and an isolated network. No real model was called.
