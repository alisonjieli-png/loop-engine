# Ollama adapter path review, September 13, 2026

A read-only review of the product's path to an Ollama endpoint, cloud or
local, before the task-database campaign spends a quota-limited provider
on it: `core/custom_endpoint.py` (the parameterised adapter the shared
gateway uses, on the `ollama` and `openai` wires), `core/ollama_client.py`
(the built-in Ollama Cloud adapter), and the classification in
`core/model_gateway.py` that every worker reads. Probe scripts and their
outputs are under
`.loop-engine-dev/fable-review-probe-20260913/agent-review-ollama/` and
`.loop-engine-dev/fable-review-probe-20260913/ollama-live-prep/`. Locality
is descriptive only: an endpoint is a URL, and nothing here treats
`ollama.com` differently from `127.0.0.1:11434`.

## What the live provider said

At 21:47 UTC the local key listed twenty models on Ollama Cloud (HTTP 200
on `/api/tags`, nineteen admissible, `kimi-k3` withheld by policy) and one
sixty-token generation on `gpt-oss:20b` was refused: HTTP 429, "you have
reached your weekly usage limit, add usage credits", with no `Retry-After`
header. So the listing is not readiness, the refusal is an allowance that
resets on the provider's calendar, and the error body carries the account
name and a hexadecimal reference.

## Defects, and what was fixed the same evening

1. **High. The Ollama wire could not stream.** The streamed path read SSE
   `data:` lines only; Ollama's native `/api/chat` streams newline-delimited
   JSON, so `stream: stream` returned "empty_response" for a complete
   answer and `stream: auto` retried a proxy timeout into a retry that could
   never deliver. **Fixed:** the Ollama wire reads NDJSON (a `data:` prefix
   from a re-framing proxy tolerated), joins the content and thinking
   deltas, takes the stop reason and counts from the final `done: true`
   line, and reports a stream that ends without one as incomplete.

2. **High. A spent allowance read as a throttle, and a status could be
   read out of a reference id.** Every 429 was `rate_limited`, which the
   Practitioner retries three times at fifteen seconds and the campaign
   waits on per cell; and the classifier found status codes by substring,
   so a `401` inside a body's hexadecimal reference turned a refusal into
   `authentication_failed`, which stops a route. **Fixed:** the status an
   adapter puts at the front of its error text settles the class before
   any body word can (401/403, 402, 404, 408, 413, 422, 429, 5xx, 504/524);
   a 429 whose body says usage limit, quota, spending limit, or usage
   credits is the new `usage_limit_reached`, an allowance the Practitioner
   does not retry inside a step, the solve terminal names as provider
   unavailable, the escalation vocabulary accepts, and the failure classes
   wait on; `model 'x' not found, try pulling it first` is
   `model_not_found` whether or not a status precedes it; and "key" must be
   a word, so a model named `monkey` is not a missing credential.

3. **Medium. A refusal inside a 200 body was an empty answer, and a page
   that was not JSON was an unclassified failure.** An Ollama or gateway
   `{"error": ...}` with status 200 became `empty_response` (this cell's
   fault), and a login page, WAF challenge, or proxy notice became
   `provider_failed` from a JSON decode error. **Fixed:** an error body is
   classified by its words, or by the status it names (`HTTP 429: ...`),
   and a body that is not a JSON object is `invalid_response_body`, an
   outage-class code, since the provider was not the one answering.

4. **Medium. `Retry-After` was dropped.** Neither adapter read the header,
   so a worker had no stated wait to honour. **Fixed:** both adapters read
   it as seconds or as an HTTP date, put it on the result as
   `retry_after_seconds` (None when unstated, which is not zero) and in the
   error text, and the gateway attempt record carries it; an unreadable
   value is unstated, never guessed.

5. **Medium. A prompt past the context window stopped the route.** A 400
   "maximum context length" refusal was `invalid_request`, a configuration
   fault, so the campaign would have stopped the route for one oversized
   cell; a 413 was unclassified. **Fixed:** context-length wording and 413
   are `context_window_exceeded`, a request-class code that fails the cell
   and keeps the route; 422 is `invalid_request`; 408 is `timeout`.

6. **Medium. The custom endpoint had no think control.** On the Ollama
   wire a reasoning model spends the output ceiling thinking before it
   answers (measured in the built-in client: at 4,096 tokens the JSON came
   back truncated with thinking on and complete with it off), and the
   parameterised adapter could not turn it off. **Fixed:** a `think` field
   (`default`, `off`, `on`; booleans and common spellings accepted) sent
   on the Ollama wire only when declared, recorded in `describe()`.

7. **Low. `auto` streaming forgot what it learned.** Every call paid the
   proxy wall again before streaming. **Fixed:** the mode is remembered per
   endpoint name in the process (never persisted), the result says which
   mode delivered (`delivered_by_stream`), and the memory can be dropped.

8. **Medium. A model listing folded every failure into the configured
   model, and catalog-only discovery then reported the provider as
   working.** `live_models` answered `[model]` for a refused key, a dead
   path, and an empty catalog alike, and `discover_roster(verify_by_use=
   False)` appended the provider to `providers_working` before listing.
   **Fixed:** `live_model_listing()` on both adapters, a record with the
   status, the classified error text, the models named, whether the
   configured model is among them, and the stated wait; `live_models`
   yields the obtained listing or an empty list, as the built-ins do; and
   catalog-only discovery reads a refused listing as a failed provider
   named by its code.

9. **High. A custom endpoint whose declared credential variable was unset
   sent an unauthenticated request, then read the 401 as a wrong
   credential that stops the route with failover forbidden.** The settings
   built the endpoint with an empty key and the adapter had no
   missing-credential branch, unlike the built-ins. **Fixed:** the endpoint
   records `credential_env` (the variable's name, never the key), refuses
   before any request with `missing_credential` when the variable is unset
   under a scheme that needs a key (the probe opened zero requests), and
   the environment declaration accepts `key_env` so the key itself need
   not sit in the declaration.

10. **High. A truncated OpenAI stream was reported as a complete
    answer.** The streamed path never recorded whether a stop reason or
    `[DONE]` arrived, so a connection cut mid-answer produced `ok=True`
    with partial text and unknown usage. **Fixed:** the stream says
    whether it finished; a cut before its stop reason or sentinel is
    `incomplete_response`, as the NDJSON path already reported.

11. **Medium. `IncompleteRead` escaped the adapter**, breaking its
    never-raises contract and crashing `configure` and the guided setup.
    **Fixed:** an HTTP exception inside the body is `incomplete_response`,
    on both the buffered and the streamed path.

12. **Medium. `auto` streaming opened two requests inside one attempt and
    reported one.** A proxy timeout does not cancel the origin's
    generation, so the allowance was spent twice and recorded once.
    **Fixed:** the result and the gateway attempt record carry
    `physical_requests` (two on a fallback, zero on a refusal before
    sending); the attempt contract stays one attempt.

13. **Low. A server that echoes the request put the key in adapter-level
    records.** **Fixed:** the configured key and any bearer token are
    redacted from error text at capture, in both adapters and the listing.

14. **Low. Base URLs that named the API prefix or the chat path composed
    doubled paths** (`/api/api/chat`, `/v1/chat/completions/models`).
    **Fixed:** an `api_root` strips the wire's own suffixes, and the chat
    and listing URLs compose from it.

15. **Low. A 200 body naming an invalid key was unclassified.** **Fixed:**
    "key" as a word beside invalid, incorrect, rejected, revoked, or
    expired is `authentication_failed`.

16. **Low.** `guided_setup` inferred the wire from port 11434, so a hosted
    Ollama URL was offered the OpenAI wire. **Fixed:** the setup asks the
    wire and suggests one from the URL's path. The Practitioner failed a
    step at once on any refusal with no scheduled wait, right for a spent
    weekly allowance and wrong for a stated short one. **Fixed:** a stated
    wait is honoured before a same-route retry, up to sixty seconds, and
    recorded; the recovery reasoner sees the failure class and the stated
    wait as facts. **Left open:** a generic 400 or 422 still stops the
    route on one occurrence, where a per-cell classification with
    escalation on repetition would serve a campaign better.

## Verified sound

Request shapes on both wires (`num_predict` and `temperature` under
`options` for Ollama, `max_tokens` for OpenAI; the declared maximum only,
never a reduced ceiling); the stop-reason and count parsing on complete,
truncated, reasoning-only, `done: false`, and usage-less bodies; the 504
and 524 self-orientation on the OpenAI wire; the classification of every
transport error the probes raised (refused, DNS, timeouts, resets, TLS
EOF, remote disconnect); credential handling (no key in any record, header
authentication names checked, `auth_scheme: none` refuses a key); the
forbidden-model refusal on the custom path.

## What this does not prove

No live generation succeeded, since the weekly allowance is spent; the
NDJSON shape is Ollama's documented one and the fixture's, not an observed
cloud stream. The independent review agent's report, on which findings 9
to 16 rest, is recorded in its probe outputs; every one of its probes was
re-run against the fixed tree. The campaign worker's own handling of `usage_limit_reached`
is the Codex session's file and was not changed: with the vocabulary as it
is, the worker waits the stated ceiling and then suspends with
`provider_wait_suspended` rather than failing cells, which is the right
outcome for a spent weekly allowance; a route-wide pause that returns the
cell unfailed and re-probes with a generation, not a listing, is the
improvement that file still needs.
