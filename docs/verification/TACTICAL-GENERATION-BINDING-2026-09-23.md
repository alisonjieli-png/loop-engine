# Tactical generation provider binding

Date: September 23 to 24, 2026, United States Eastern. Base revision:
`da5db8aa826169d24550b0ba4e7102da125f8b10`. This record implements the frozen
design in the [Tactical discovery and binding proposal](TACTICAL-HERMES-PROVIDER-BINDING-2026-09-23.md).
The proposal keeps its bytes as history.

## Outcome

- The owner's Tactical Engineering model server is reachable under a verified
  TLS trust contract. The key is resolved from the system keyring inside the
  calling process only.
- The candidate generator can select this server through one committed
  provider binding. The binding is built from the existing `ProviderSettings`,
  `CustomEndpoint` and `ModelGateway` contracts. The producer family is
  `google`, with its own reviewed evidence.
- **The output capacity is unknown.** Three recorded model calls did not
  produce a completed response that the server itself cut at a length limit.
  No read-only route states the limit. The generator therefore refuses this
  binding with `output_capacity_unknown` before it reads the credential.
- **No real generation call was made.** The brief makes that call conditional
  on a recorded capacity. The section [What the owner must supply](#what-the-owner-must-supply)
  names the four facts that unblock it.
- End to end, after commit `9f437c05`, the generator command was run with
  the committed binding (digest `9fd0a56e51581501bf23b2d807099d6ee6b3c49fd6546f78ff0fc4997229722a`), a one-method plan pinned to that
  commit (`minimum_cost_unique_assignment`) and `--max-calls 1`. It refused with
  `output_capacity_unknown`, exit code 1. It created no run folder and sent no
  request.

## The server

| Fact | Observation |
|---|---|
| Connect address | `https://ai.tacticalengineering.net:6969/v1`. The DNS answer is `172.11.142.224`, the origin itself |
| Certificate | Cloudflare Origin certificate for `*.iamretarded.net` and `iamretarded.net`. Leaf SHA-256 `0fc69cf1c72abe552e9fb3cfa96db9974d7bd93394c20d219d4c051a1a923901` |
| Same owner | The owner stated that Tactical Engineering and `iamretarded.net` are the same service, owned by them |
| Why not the certificate's own name | `ai.iamretarded.net` resolves to Cloudflare proxy addresses, which do not serve port 6969 |
| Software | TensorRT-LLM server version `1.3.0rc25`. `/server_info` reports `max_batch_size: 1` and `tokens_per_block: 32` |
| Model | `/v1/models` lists one model, `gemma-4-coding-abliterated`, and every response reports it |

## TLS trust contract

`CustomEndpoint` and `ProviderSettings` gain two typed fields beside the
existing `tls_verification` and `tls_ca_file`:

- `tls_server_name` is the name the certificate must prove when it differs
  from the host the URL connects to. Hostname checking stays on.
- `tls_pinned_sha256` is an optional SHA-256 of the leaf certificate. It is
  stored as 64 lower-case hexadecimal characters, and colons and upper case
  are accepted on input.

An endpoint that declares `ca_file`, a server name or a pin has a trust
contract. The adapter opens it through one HTTPS connection class. The TCP
connection goes to the URL host, the handshake names the expected server
name, and the context trusts only the declared anchor. The pin is compared
after the handshake. Every refusal happens inside `connect`, before
`http.client` writes the request line. No header, body or key leaves the
process. The opener for such an endpoint also refuses plain HTTP and follows
no redirect.

| Known-wrong case | Result |
|---|---|
| Wrong pin | `tls_trust_refused`, zero physical requests, the server parses no request |
| Wrong server name, or the connect host used as the name | Same refusal |
| Anchor file missing | Refused before any socket opens: the server accepts no connection |
| Unrelated anchor, or the system store without the anchor | Same refusal after the handshake, before any request |
| `http://` URL with a trust contract, `ca_file` without a file, `skip` with a pin, wildcard or upper-case name | Refused when the endpoint or setting is declared |
| Plain HTTP through a trusted opener | Refused; the plain server accepts no connection |
| A redirect from the verified server to plain HTTP | Ends as `HTTP 303`, one physical request; the plain server accepts no connection |

The gateway reports the code `tls_trust_refused`, and the generator stops a run
on it. Two edits wait for the next starter catalogue re-anchor, because the
catalogue pins the exact bytes of both files as cited sources. The shared
failure-class vocabulary in `provider_failure_classes.py` would class the code
as a configuration fault, so that `decide` stops the route; until then it
treats the code as unclassified and fails the cell. The settings file loader
in `settings_loader.py` would accept the two new keys. Both edits are kept as
[`deferred-cited-source-edits.patch`](../../artifacts/tactical-generation-binding-2026-09-23/deferred-cited-source-edits.patch).
The first run of the full tools suite found the conflict: six catalogue and
review checks failed until the two files were restored.

Live check, before any measurement call: a model listing through this
contract returned `gemma-4-coding-abliterated`, and the same listing with an
all-zero pin was refused with nothing sent. See
[`trust-contract-listing-check-1.json`](../../artifacts/tactical-generation-binding-2026-09-23/trust-contract-listing-check-1.json).

## Provider binding

The binding is
[`tactical-gemma-4-coding-abliterated.json`](../../tools/resources/original-native-generation-providers/tactical-gemma-4-coding-abliterated.json),
record type `original_native_generation_provider_binding/v1`:

```text
original_native_generation_provider_binding/v1
├── provider: one custom provider in the settings file's own shape
│   ├── endpoint, exact model, OpenAI wire, streamed, purpose generation
│   └── TLS: ca_file, expected server name, pinned leaf SHA-256
├── trust_anchor_sha256: the committed Cloudflare Origin CA root
├── producer_family: google
├── family_evidence: path and SHA-256 of the reviewed family record
├── capacity: path and SHA-256 of the capacity record
└── credential_reference: tactical-model-generation, never a value
```

Before any credential is read, the generator checks the following:

- The binding, the trust anchor, the family evidence, the capacity record
  and the review panel are committed unchanged at the plan's source revision.
- The provider parses through the settings loader, and the two TLS identity
  keys through `ProviderSettings` validation. It is a verified HTTPS custom
  endpoint with purpose `generation`. It declares no `credential_env` and no
  output maximum of its own.
- The requested model and family equal the binding's exactly. Aliases are
  not normalized.
- The family is in the review panel's vocabulary. The family evidence and
  the capacity record name this exact provider, endpoint and model.
- The capacity is known.

Only then does the generator resolve the credential reference through
`tools/operator_credentials.py`, build one `CustomEndpoint` and one
`ProviderSpec`, and invoke `ModelGateway` with one route. Failover and
retries stay off. The run record is now `original_native_generation_run/v5`.
It stores a secret-free binding summary with the binding, settings, trust
anchor, family evidence, capacity and panel digests and the credential
reference name. It also records the settings modules' source digests. Resume
refuses any change. The Ollama Cloud path is unchanged: the reviewed panel
installation still decides its family, and its adapter still owns its
credential.

The keyring reference `tactical-model-generation` in
[`operator_credentials.json`](../../tools/operator_credentials.json) names
service `tactical`, account `api-key`, purpose `model-generation` and
requires the prefix `sk-`. The helper resolved it on this workstation. Only
a Boolean result was printed.

## Capacity record

[`capacity-record.json`](../../artifacts/tactical-generation-binding-2026-09-23/capacity-record.json)
has record type `endpoint_output_capacity/v1` and
`maximum_output_tokens: "unknown"`. The ceiling was three recorded model
calls. Each call was streamed, at temperature 0, with `max_tokens`
10,000,000, and asked for more output than any plausible limit.

| Call | Route and request | Result |
|---|---|---|
| 1 | Chat: count upward without stopping | The model stopped by itself after 186 tokens, on token id 106 |
| 2 | Chat: write every number from 1 to 100,000, with a strict system text | The model wrote 1 to 100, an ellipsis and the last three numbers, then stopped after 558 tokens on token id 106 |
| 3 | Completions: the text "1" to "100", one per line, with no chat template | 105,574 tokens streamed in about 776 seconds, about 136 a second. The stream fell into repeating one line, then sent nothing for 300 seconds. The client read timeout closed it. No stop reason, no usage, no `[DONE]` |

The server accepted `max_tokens` 10,000,000 three times without an error or
a stated limit. Acceptance is not evidence of capacity. A later read of
`/metrics`, `/health`, `/version`, `/v1/models`, `/server_info` and the
OpenAPI route list found no sequence, input or output limit
([metadata record](../../artifacts/tactical-generation-binding-2026-09-23/metadata-reads-after-measurement-1.json)).

Call 3 shows that one response can stream at least 105,574 tokens. It is not
a completed response, so it does not qualify a maximum. Why the stream stopped
is not observed. `/server_info` reports `max_batch_size: 1`. If the server kept
that request after the client closed the connection, it would serve no other
request until it is restarted. That state is not observed either way.

## Family evidence

[`family-evidence.json`](../../artifacts/tactical-generation-binding-2026-09-23/family-evidence.json)
records the reviewed relationship between this exact provider, endpoint and
model and the family `google`:

- Observed on this endpoint: completed chat responses stopped on token id
  106, and digits stream one per token.
- Reference: Google's Gemma 4 tokenizer in the Ollama library model
  `gemma4:latest`, read from its GGUF header on this workstation (blob
  `4c27e0f5b5adf02ac956c7322bd2ee7636fe3f45a8512c9aba5385242cb6e09a`). The
  vocabulary has 262,144 entries. Id 106 is `<turn|>`, one
  of the declared end tokens `[1, 106, 50]`. The vocabulary has no
  multi-digit tokens.
- The served name names Gemma 4. `abliterated` names a modification of the
  weights, not another family.

Limitation: a tokenizer and turn format show lineage, not where the weights
came from. The owner has not stated the base checkpoint. Because the producer
family is `google`, a `google` reviewer may not approve this producer's
candidates. The binding tests prove that rule on the prepared candidate. No
`google` reviewer is installed today.

## What the owner must supply

The running `trtllm-serve` instance publishes none of these, and three calls
could not measure them. Any one of the first two makes a successor capacity
record possible:

1. `max_seq_len`, the limit for prompt plus output in one request.
2. The server's behavior when prompt plus `max_tokens` exceeds `max_seq_len`:
   clamp silently, or refuse with the limit stated. A refusal that states the
   limit is a provider-declared maximum under this repository's rules.
3. `max_input_len` and `max_num_tokens`.
4. The KV cache capacity in tokens, or `kv_cache_free_gpu_memory_fraction` and
   the GPU memory it applies to. Call 3 stalled at about 105,900 tokens of
   prompt plus output, which may be a cache limit. This is not observed.

With those facts, a successor record under a new name states the maximum,
and the binding is re-committed with that record's digest. Then the
one-method pilot can run:

```bash
PYTHONPATH=src python -m tools.generate_original_native_candidates \
  --repository . --plan ONE_METHOD_PLAN --plan-sha256 EXACT_PLAN_SHA256 \
  --output /private/run/folder \
  --model gemma-4-coding-abliterated --family google \
  --provider-binding tools/resources/original-native-generation-providers/tactical-gemma-4-coding-abliterated.json \
  --provider-binding-sha256 EXACT_BINDING_SHA256 \
  --max-calls 1 --output-tokens ALLOCATION_WITHIN_CAPACITY \
  --allow-unbounded-total --authorize-model-calls --authorize-writes
```

## Checks

| Check | Result |
|---|---|
| TLS trust against a local TLS server with a throwaway authority (`tools/test_custom_endpoint_tls_trust.py`) | 13 of 13 pass on Python 3.10 and 3.14 |
| Provider binding with fixture transports through the real adapter and gateway (`tools/test_generate_original_native_provider_binding.py`) | 17 of 17 pass |
| Existing generator checks (`tools/test_generate_original_native_candidates.py`) | 33 of 33 pass; the run-version check now refuses version four |
| Custom endpoint self-test and adapter checks | 22 of 22 and 70 of 70 pass |
| Package self-test and conformance gates | 3,385 of 3,385 checks pass and all conformance gates pass when run alone. One run beside the full tools suite reported a terminology gate and a projection check that did not reproduce alone |
| Full tools suite | 1,314 tests: the same 9 failures as the base revision (architecture audit and fresh-instance checks), none new |
| Removed-guard controls ([`check_removed_guards.py`](../../artifacts/tactical-generation-binding-2026-09-23/check_removed_guards.py)) | 21 of 21 detected against the final source ([record](../../artifacts/tactical-generation-binding-2026-09-23/removed-guards-20260924T052546.json)), with no provider call |
| Hardcoding audit against the CI baseline | No new high finding after nine exact allowlist entries with owners and reasons: the `https://` scheme of the trust contract, the `custom` provider kind, the credential variable name and the binding's endpoint |

Each removed-guard control removes one guard in memory, and its named check
then fails. The guards cover the pin, the expected name, hostname checking,
the declared anchor, HTTPS-only declarations, `ca_file` consistency, plain
HTTP, redirects, refusal accounting and classification, and the settings
mapping. They also cover the binding's revision check, credential and
capacity fields, verified HTTPS, model, family, family evidence, capacity
identity, unknown capacity, the stop on TLS refusal and the resume binding.

The measurement script is
[`measure_output_capacity.py`](../../artifacts/tactical-generation-binding-2026-09-23/measure_output_capacity.py).
Each call record keeps the prompt, the request, a digest of the output, its
first and last 200 characters, and the reported usage. No record, event or
file holds the key; the script checks this before it writes.

## Limitations

- These checks qualify the contract and its refusals. They do not qualify
  the model's output quality, a generated package or any approval.
- The capacity and the reason for the third call's stall are unknown.
- The family evidence shows tokenizer lineage, not weights provenance.
- Call 3 used the completions route to avoid the chat template. The
  generator uses the chat route; both reach the same model on the same
  server.
