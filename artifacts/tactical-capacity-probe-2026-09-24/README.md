# Tactical capacity probe

September 24, 2026, United States Eastern. Four recorded probe calls under a
ceiling of five, two of them model calls, all through the Tactical binding's
TLS trust contract. No credential is written in any file here.

- `probe.py`: the probe tool. It reads the endpoint from the committed binding
  and writes one secret-free record per run.
- `metadata-read-1.json`: models, server information, metrics, health,
  version and the OpenAPI route list. No model call. The server answered.
- `call-1-chat-max-tokens-10000000.json`: a one-word chat reply with
  `max_tokens` 10,000,000. Accepted without a refusal or a stated limit.
- `call-2-tokenize.json`: the tokenizer route returns only a count and token
  ids. No generation.
- `call-3-kv-cache-events.json`: the documented cache event route returns an
  empty list, so it states no cache size. No generation.
- `call-4-completion-to-65536.json`: a completion asked for exactly 65,536
  tokens ended with `finish_reason` `length` at 65,536 completion tokens after
  a 292-token prompt, with usage and `[DONE]`.
- `capacity-record-verified-65536.json`: `endpoint_output_capacity/v1` with a
  maximum of 65,536 output tokens, basis `verified_completed_length`. It
  supersedes the unknown record of September 23, which keeps its bytes.

The server states no limit, so the declared maximum is the largest output it
was observed to complete. It is not the server's configured limit. The
September 23 stall happened at 105,866 total tokens.
